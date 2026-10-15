"""Tarefas executadas pela fila (RQ). Cada tarefa recebe o job inteiro,
baixa o que precisa, processa, sobe o resultado e avisa o n8n pelo callback."""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from . import align, images, media, storage, thumbnail, tts
from .settings import settings

log = logging.getLogger("fabrica.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BLOCK_GAP_S = 0.35  # respiro entre blocos de narração
CLIP_WORKERS = int(os.environ.get("CLIP_WORKERS", "2"))


# ---------------------------------------------------------------------------
# Infra comum
# ---------------------------------------------------------------------------
def _workdir(job: dict) -> Path:
    d = settings.work_dir / f"{job.get('video_id', 'novideo')}-{job['type']}-{int(time.time() * 1000)}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _callback(job: dict, body: dict) -> bool:
    """Avisa o n8n. Devolve True se o n8n aceitou."""
    url = job.get("callback_url")
    if not url:
        return False
    headers = {"Authorization": f"Bearer {settings.callback_token}"} if settings.callback_token else {}
    host = url.split("/webhook")[0]
    for attempt in range(3):
        try:
            r = httpx.post(url, json=body, headers=headers, timeout=30)
            r.raise_for_status()
            log.info("callback ok: %s job=%s status=%s", host, job.get("type"), body.get("status"))
            return True
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            hint = {401: "falta o header de autenticação", 403: "CALLBACK_TOKEN diferente da credencial do Wait (ou assinatura da URL inválida)",
                    404: "execução não está mais esperando", 409: "execução já terminou (cancelada, expirada ou com erro)"}.get(code, "")
            log.error("callback falhou (tentativa %d): HTTP %s em %s — %s | resposta do n8n: %s",
                      attempt + 1, code, host, hint, exc.response.text[:200].replace("\n", " "))
            if code in (404, 409):
                break  # não adianta tentar de novo
        except Exception as exc:
            log.error("callback falhou (tentativa %d): %s em %s", attempt + 1, exc, host)
        time.sleep(2 * (attempt + 1))
    log.error("callback DESISTIU depois de 3 tentativas: %s (corrija e use POST /jobs/<id>/resend-callback)", host)
    return False


def execute(job: dict) -> dict:
    """Ponto de entrada da fila."""
    started = time.time()
    log.info("job iniciado: %s video=%s key=%s", job["type"], job.get("video_id"), job.get("idempotency_key"))
    wd = _workdir(job)
    handler = HANDLERS[job["type"]]
    try:
        result = handler(job, job.get("input", {}), wd)
        body = {"status": "succeeded", "result": result}
    except Exception as exc:  # o n8n decide se tenta de novo ou troca de provedor
        body = {"status": "failed", "error": str(exc), "trace": traceback.format_exc()[-4000:]}
    finally:
        if os.environ.get("KEEP_WORKDIR") != "1":
            shutil.rmtree(wd, ignore_errors=True)
    body.update({
        "video_id": job.get("video_id"),
        "type": job["type"],
        "idempotency_key": job.get("idempotency_key"),
        "elapsed_s": round(time.time() - started, 1),
    })
    log.info("job %s: %s em %.1fs%s", job["type"], body["status"], body["elapsed_s"],
             f" — {body['error'][:300]}" if body["status"] == "failed" else "")
    _callback(job, body)
    if body["status"] == "failed":
        raise RuntimeError(body["error"])
    return body


def _key(job: dict, name: str) -> str:
    prefix = job.get("input", {}).get("key_prefix") or f"videos/{job.get('video_id', 'novideo')}"
    return f"{prefix.rstrip('/')}/{name}"


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
def h_tts(job: dict, inp: dict, wd: Path) -> dict:
    out = wd / f"{inp.get('name', 'narration')}.mp3"
    words = tts.synthesize(inp["text"], inp["voice"], out, rate=inp.get("rate", "+0%"))
    dur = media.duration(out)
    url = storage.upload(out, _key(job, f"audio/{out.name}"), "audio/mpeg")
    return {"url": url, "duration_s": round(dur, 3), "words": words}


def h_voice(job: dict, inp: dict, wd: Path) -> dict:
    """Narra todos os blocos do video_spec (edge-tts), checa silêncios e devolve o spec atualizado."""
    spec = json.loads(storage.download(inp["spec_url"], wd / "spec.json").read_text("utf-8"))
    voice, rate = inp["voice"], inp.get("rate", "+0%")
    checks, total = [], 0.0
    for b in spec["blocks"]:
        out = wd / "audio" / f"{b['block_id']}.mp3"
        words = []
        for attempt in range(3):  # edge-tts às vezes devolve áudio vazio; tenta de novo
            words = tts.synthesize(b["narration"], voice, out, rate=rate)
            if out.exists() and out.stat().st_size > 1000 and words:
                break
            time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"edge-tts falhou no bloco {b['block_id']}")
        dur = media.duration(out)
        total += dur
        sil = media.silences(out)
        checks.append({"stage": "voice", "name": f"no_long_silence:{b['block_id']}", "passed": not sil,
                       "detail": {"silences": sil}})
        b["audio"] = {
            "url": storage.upload(out, _key(job, f"audio/{out.name}"), "audio/mpeg"),
            "duration_s": round(dur, 3), "offset_s": None, "words": words,
        }
    spec["checks"] = (spec.get("checks") or []) + checks
    spec_path = wd / "spec.voice.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), "utf-8")
    spec_url = storage.upload(spec_path, _key(job, "video_spec.json"), "application/json")
    return {"spec_url": spec_url, "spec": spec, "narration_s": round(total, 2), "checks": checks}


def h_images(job: dict, inp: dict, wd: Path) -> dict:
    """Gera a imagem de cada plano que ainda não tem uma (Cloudflare FLUX ou Gemini), em paralelo."""
    spec = json.loads(storage.download(inp["spec_url"], wd / "spec.json").read_text("utf-8"))
    style = inp.get("style_block", "").strip()
    negative = inp.get("negative_prompt", "").strip()
    model = inp.get("model")
    shots = sorted((s for b in spec["blocks"] for s in b["shots"]), key=lambda s: s["order"])
    todo = [s for s in shots if not (s.get("image") or {}).get("url")]

    def prompt_for(shot: dict, extra: str = "") -> str:
        p = f"{style}\n\nScene: {shot['visual_prompt']}{extra}"
        if negative:
            p += f"\n\nAvoid: {negative}."
        return p + "\nNo text, letters or watermarks in the image."

    def one(shot: dict) -> dict:
        out = wd / "img" / f"{shot['order']:03d}-{shot['shot_id']}.jpg"
        try:
            raw, used = images.generate(prompt_for(shot), model)
            images.to_jpeg(raw, out)
            return {"shot": shot, "path": out, "model": used, "error": None}
        except Exception as exc:
            return {"shot": shot, "path": None, "model": None, "error": str(exc)}

    workers = int(os.environ.get("IMAGE_CONCURRENCY", "3"))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, todo))

    # imagens quase idênticas: refaz uma vez pedindo variação
    seen: list[tuple[int, str]] = []
    for r in results:
        if not r["path"]:
            continue
        h = images.ahash(r["path"])
        if any(images.hamming(h, prev) <= 4 for prev, _ in seen):
            try:
                raw, used = images.generate(prompt_for(r["shot"], " Different camera angle and composition."), model)
                images.to_jpeg(raw, r["path"])
                h = images.ahash(r["path"])
                r["model"] = used
            except Exception:
                pass
        seen.append((h, r["shot"]["shot_id"]))

    failed = []
    for r in results:
        shot = r["shot"]
        if r["path"]:
            url = storage.upload(r["path"], _key(job, f"images/{r['path'].name}"), "image/jpeg")
            shot["image"] = {"url": url, "provider": r["model"]}
        else:
            failed.append({"shot_id": shot["shot_id"], "error": r["error"]})

    # plano sem imagem herda a do plano vizinho para o vídeo não travar (a checagem acusa)
    by_order = {s["order"]: s for s in shots}
    for f in failed:
        shot = next(s for s in shots if s["shot_id"] == f["shot_id"])
        for o in [shot["order"] - 1, shot["order"] + 1, shot["order"] - 2, shot["order"] + 2]:
            nb = by_order.get(o)
            if nb and (nb.get("image") or {}).get("url"):
                shot["image"] = {"url": nb["image"]["url"], "provider": "reused-neighbor"}
                break
    if len(failed) > max(2, len(todo) // 10):
        raise RuntimeError(f"{len(failed)} de {len(todo)} imagens falharam; primeira: {failed[0]['error']}")

    checks = [{"stage": "images", "name": "all_images_generated", "passed": not failed,
               "detail": {"generated": len(todo) - len(failed), "failed": failed}}]
    spec["checks"] = (spec.get("checks") or []) + checks
    spec_path = wd / "spec.images.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), "utf-8")
    spec_url = storage.upload(spec_path, _key(job, "video_spec.json"), "application/json")
    return {"spec_url": spec_url, "spec": spec, "generated": len(todo) - len(failed), "failed": failed, "checks": checks}


def h_align(job: dict, inp: dict, wd: Path) -> dict:
    audio = storage.download(inp["audio_url"], wd / "in_audio")
    words = align.transcribe(audio, inp.get("language"), settings.whisper_model)
    res = {"words": words}
    if inp.get("expected_text"):
        res["match_ratio"] = round(align.text_match_ratio(inp["expected_text"], words), 3)
    return res


def h_kenburns(job: dict, inp: dict, wd: Path) -> dict:
    img = storage.download(inp["image_url"], wd / "img")
    out = media.kenburns(img, wd / "clip.mp4", float(inp["duration_s"]), inp.get("mode", "push_in"),
                         inp.get("text_overlay"))
    return {"url": storage.upload(out, inp.get("out_key") or _key(job, "clips/kenburns.mp4"), "video/mp4")}


def _render_shot(shot: dict, seconds: float, wd: Path) -> Path:
    sid = shot["shot_id"]
    out = wd / "clips" / f"{shot['order']:03d}-{sid}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    clip_url = (shot.get("clip") or {}).get("url")
    image_url = (shot.get("image") or {}).get("url")
    overlay = shot.get("text_overlay")
    if shot["motion"]["mode"] == "ai" and clip_url:
        src = storage.download(clip_url, wd / "src" / f"{sid}.clip")
        return media.fit_clip(src, out, seconds, overlay)
    if not image_url:
        raise ValueError(f"plano {sid} sem imagem")
    img = storage.download(image_url, wd / "src" / f"{sid}.img")
    mode = shot["motion"].get("kenburns") or ("push_in" if shot["order"] % 2 else "pan_right")
    return media.kenburns(img, out, seconds, mode, overlay)


def h_assemble(job: dict, inp: dict, wd: Path) -> dict:
    spec = json.loads(storage.download(inp["spec_url"], wd / "spec.json").read_text("utf-8"))
    blocks = spec["blocks"]

    # 1) narração: blocos em sequência com respiro entre eles
    parts, offset, all_words = [], 0.0, []
    for i, b in enumerate(blocks):
        audio = b.get("audio") or {}
        if not audio.get("url"):
            raise ValueError(f"bloco {b['block_id']} sem áudio")
        wav = media.to_wav(storage.download(audio["url"], wd / "audio" / f"{b['block_id']}.src"),
                           wd / "audio" / f"{b['block_id']}.wav")
        dur = media.duration(wav)
        audio["duration_s"] = round(dur, 3)
        audio["offset_s"] = round(offset, 3)
        b["audio"] = audio
        parts.append(wav)
        all_words += [{"w": w["w"], "s": round(w["s"] + offset, 3), "e": round(w["e"] + offset, 3)}
                      for w in audio.get("words") or []]
        span = dur
        if i < len(blocks) - 1:
            parts.append(media.silence(wd / "audio" / f"gap{i}.wav", BLOCK_GAP_S))
            span += BLOCK_GAP_S
        # 2) tempo de cada plano dentro do bloco (o último plano cobre o respiro)
        times = align.shot_times(b, dur)
        shots = sorted(b["shots"], key=lambda s: s["order"])
        for j, (shot, (s, e)) in enumerate(zip(shots, times)):
            if j == len(shots) - 1:
                e = span
            shot["start_s"], shot["end_s"] = round(offset + s, 3), round(offset + e, 3)
        offset += span
    narration = media.concat_audio(parts, wd / "narration.wav")

    # 3) clipes de cada plano
    all_shots = sorted((s for b in blocks for s in b["shots"]), key=lambda s: s["order"])
    with ThreadPoolExecutor(max_workers=CLIP_WORKERS) as pool:
        # duração em quadros inteiros a partir da linha do tempo global: sem deriva entre vídeo e áudio
        fps = settings.fps
        clips = list(pool.map(
            lambda s: _render_shot(s, (round(s["end_s"] * fps) - round(s["start_s"] * fps)) / fps, wd),
            all_shots))
    video = media.concat_videos(clips, wd / "video_only.mp4")

    # 4) mixagem, loudness e legenda
    music = storage.download(inp["music_url"], wd / "music.src") if inp.get("music_url") else None
    final = media.master(video, narration, wd / "FINAL.mp4", float(inp.get("loudness_lufs", -14)),
                         music, float(inp.get("music_volume_db", -22)))
    srt = media.write_srt(all_words, wd / "FINAL.srt") if all_words else None
    prev = media.preview(final, wd / "preview.mp4")

    final_dur = media.duration(final)
    outputs = {
        "final_url": storage.upload(final, _key(job, "FINAL.mp4"), "video/mp4"),
        "srt_url": storage.upload(srt, _key(job, "FINAL.srt"), "application/x-subrip") if srt else None,
        "preview_url": storage.upload(prev, _key(job, "preview.mp4"), "video/mp4"),
        "duration_s": round(final_dur, 2),
    }
    spec["outputs"] = outputs
    spec["publishing"] = spec.get("publishing") or {}
    spec["publishing"]["chapters"] = [{"t": b["audio"]["offset_s"], "title": b["title"]} for b in blocks]

    checks = _media_checks(final, "assemble", float(inp.get("loudness_lufs", -14)),
                           float(inp.get("min_duration_s", 0)))
    spec["checks"] = (spec.get("checks") or []) + checks
    spec_path = wd / "spec.out.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), "utf-8")
    spec_url = storage.upload(spec_path, _key(job, "video_spec.json"), "application/json")
    return {"outputs": outputs, "spec_url": spec_url, "spec": spec, "checks": checks, "words": all_words}


def h_shorts(job: dict, inp: dict, wd: Path) -> dict:
    final = storage.download(inp["final_url"], wd / "final.mp4")
    words = inp.get("words")
    if words is None and inp.get("spec_url"):
        spec = json.loads(storage.download(inp["spec_url"], wd / "spec.json").read_text("utf-8"))
        words = []
        for b in spec["blocks"]:
            off = b["audio"].get("offset_s") or 0
            words += [{"w": w["w"], "s": w["s"] + off, "e": w["e"] + off} for w in b["audio"].get("words") or []]
    results = []
    for i, c in enumerate(inp["candidates"], 1):
        out = media.vertical_short(final, float(c["start_s"]), float(c["end_s"]), words or [], wd / f"short{i}.mp4")
        dur = media.duration(out)
        results.append({
            "url": storage.upload(out, _key(job, f"shorts/short{i}.mp4"), "video/mp4"),
            "start_s": c["start_s"], "end_s": c["end_s"], "hook": c.get("hook"),
            "duration_s": round(dur, 2), "passed": 15 <= dur <= 60,
        })
    return {"shorts": results}


def h_thumbnail(job: dict, inp: dict, wd: Path) -> dict:
    brand = inp.get("brand") or {}
    results = []
    for i, opt in enumerate(inp["options"], 1):
        bg = storage.download(opt["image_url"], wd / f"bg{i}")
        out = wd / f"thumb{i}.jpg"
        check = thumbnail.render(bg, opt["lines"], out, settings.font_path,
                                 accent=brand.get("secondary", "#F2B705"))
        results.append({"url": storage.upload(out, _key(job, f"thumbs/thumb{i}.jpg"), "image/jpeg"),
                        "lines": opt["lines"], "check": check})
    return {"thumbnails": results}


def _media_checks(path: Path, stage: str, lufs_target: float | None, min_duration: float = 0) -> list[dict]:
    dur = media.duration(path)
    sil = media.silences(path)
    checks = [
        {"stage": stage, "name": "duration", "passed": dur >= min_duration, "detail": {"duration_s": round(dur, 2), "min_s": min_duration}},
        {"stage": stage, "name": "no_long_silence", "passed": not sil, "detail": {"silences": sil}},
    ]
    if lufs_target is not None:
        lufs = media.integrated_lufs(path)
        checks.append({"stage": stage, "name": "loudness", "passed": abs(lufs - lufs_target) <= 1.0,
                       "detail": {"lufs": lufs, "target": lufs_target}})
    if path.suffix == ".mp4":
        black = media.black_frames(path)
        checks.append({"stage": stage, "name": "no_black_frames", "passed": not black, "detail": {"black": black}})
    return checks


def h_checks(job: dict, inp: dict, wd: Path) -> dict:
    src = storage.download(inp["media_url"], wd / ("in" + Path(inp["media_url"]).suffix))
    return {"checks": _media_checks(src, inp.get("stage", "checks"), inp.get("expect_lufs"),
                                    float(inp.get("min_duration_s", 0)))}


HANDLERS = {
    "voice": h_voice,
    "images": h_images,
    "tts": h_tts,
    "align": h_align,
    "kenburns": h_kenburns,
    "assemble": h_assemble,
    "shorts": h_shorts,
    "thumbnail": h_thumbnail,
    "checks": h_checks,
}

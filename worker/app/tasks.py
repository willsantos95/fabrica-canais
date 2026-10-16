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

from . import align, images, media, newsvideo, storage, thumbnail, tts
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


THUMB_VARIATIONS = [
    "",
    " Close-up of the main character's face with a strong, surprised expression.",
    " Dramatic low-angle wide view, strong rim light, bold colors.",
]


def _thumb_backgrounds(spec: dict, style: str, wd: Path, n: int) -> list[tuple[Path, str]]:
    """Fundos das thumbnails: gera pelo provedor de imagens; se falhar, usa os planos do gancho."""
    prompt = (spec.get("thumbnail") or {}).get("image_prompt") or spec.get("topic") or ""
    out: list[tuple[Path, str]] = []
    for i in range(n):
        path = wd / "thumb_bg" / f"bg{i + 1}.jpg"
        try:
            raw, used = images.generate(
                f"{style}\n\nScene: {prompt}{THUMB_VARIATIONS[i % len(THUMB_VARIATIONS)]}\n"
                "No text, letters or watermarks in the image.")
            images.to_jpeg(raw, path)
            out.append((path, used))
        except Exception as exc:
            log.warning("fundo da thumbnail %d não gerado (%s); usando um plano do vídeo", i + 1, exc)
    if len(out) < n:
        shots = sorted((s for b in spec["blocks"] for s in b["shots"] if (s.get("image") or {}).get("url")),
                       key=lambda s: (not s.get("is_hook"), s["order"]))
        for s in shots[: n - len(out)]:
            out.append((storage.download(s["image"]["url"], wd / "thumb_bg" / f"{s['shot_id']}.jpg"), "shot"))
    return out


def h_package(job: dict, inp: dict, wd: Path) -> dict:
    """Shorts, thumbnails e metadados do YouTube a partir do vídeo montado (sem IA de texto)."""
    from . import package

    spec = json.loads(storage.download(inp["spec_url"], wd / "spec.json").read_text("utf-8"))
    cfg = inp.get("config") or {}
    n_shorts = int(inp.get("shorts", (cfg.get("format") or {}).get("shorts_per_video", 3)))
    n_thumbs = int(inp.get("thumbnails", 3))
    final = storage.download(spec["outputs"]["final_url"], wd / "final.mp4")

    # 1) Shorts
    words = []
    for b in spec["blocks"]:
        off = (b.get("audio") or {}).get("offset_s") or 0
        words += [{"w": w["w"], "s": w["s"] + off, "e": w["e"] + off} for w in (b.get("audio") or {}).get("words") or []]
    shorts = []
    for i, c in enumerate(package.select_shorts(spec, n_shorts), 1):
        out = media.vertical_short(final, c["start_s"], c["end_s"], words, wd / f"short{i}.mp4")
        dur = media.duration(out)
        meta = package.short_metadata(c, spec, cfg, i)
        shorts.append({
            "n": i, "url": storage.upload(out, _key(job, f"shorts/short{i}.mp4"), "video/mp4"),
            "start_s": c["start_s"], "end_s": c["end_s"], "hook": c["hook"], "text": c["text"],
            "duration_s": round(dur, 2), "passed": 15 <= dur <= 60, **meta,
        })

    # 2) Thumbnails
    visual = cfg.get("visual") or {}
    brand = visual.get("brand") or {}
    lines = (spec.get("thumbnail") or {}).get("phrases") or []
    if not lines:
        prof = package.profession(spec)
        lines = [prof.upper() if prof else spec.get("chosen_title", "")[:20], "EVERY LEVEL"]
    thumbs = []
    for i, (bg, used) in enumerate(_thumb_backgrounds(spec, visual.get("style_block", ""), wd, n_thumbs), 1):
        out = wd / f"thumb{i}.jpg"
        check = thumbnail.render(bg, lines, out, settings.font_path, accent=brand.get("secondary", "#F2B705"))
        thumbs.append({"n": i, "url": storage.upload(out, _key(job, f"thumbs/thumb{i}.jpg"), "image/jpeg"),
                       "lines": lines, "background": used, "check": check})

    # 3) Metadados
    meta = package.build_metadata(spec, cfg)
    spec["shorts_candidates"] = shorts
    spec.setdefault("thumbnail", {})
    spec["thumbnail"]["options"] = thumbs
    legible = [t["n"] for t in thumbs if t["check"]["passed"]]
    spec["thumbnail"]["chosen"] = (legible or [1])[0] if thumbs else None
    spec.setdefault("publishing", {}).update(meta)

    checks = [
        {"stage": "package", "name": "shorts_ready", "passed": len(shorts) == n_shorts and all(s["passed"] for s in shorts),
         "detail": {"shorts": [{"n": s["n"], "duration_s": s["duration_s"]} for s in shorts], "wanted": n_shorts}},
        {"stage": "package", "name": "thumbnail_legible", "passed": bool(legible), "detail": {"legible": legible}},
        {"stage": "package", "name": "has_chapters", "passed": len(spec["blocks"]) >= 3, "detail": {"chapters": len(spec["blocks"])}},
    ]
    spec["checks"] = (spec.get("checks") or []) + checks
    spec_path = wd / "spec.package.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), "utf-8")
    spec_url = storage.upload(spec_path, _key(job, "video_spec.json"), "application/json")
    return {"spec_url": spec_url, "spec": spec, "shorts": shorts, "thumbnails": thumbs,
            "publishing": meta, "outputs": spec["outputs"], "checks": checks}


def h_clips(job: dict, inp: dict, wd: Path) -> dict:
    """Clipes verticais (TikTok/Reels), um por nível, remontados a partir das imagens
    com o áudio já mixado do vídeo final. Sem custo de API."""
    from . import package

    spec = json.loads(storage.download(inp["spec_url"], wd / "spec.json").read_text("utf-8"))
    cfg = inp.get("config") or {}
    final = storage.download(spec["outputs"]["final_url"], wd / "final.mp4")
    end_card = inp.get("end_card") or package.texts(cfg)["end_card"]
    fps = settings.fps
    shots = sorted((s for b in spec["blocks"] for s in b["shots"]), key=lambda s: s["order"])
    imgs: dict[str, Path] = {}

    def image_of(shot: dict) -> Path:
        if shot["shot_id"] not in imgs:
            imgs[shot["shot_id"]] = storage.download(shot["image"]["url"], wd / "img" / f"{shot['shot_id']}.img")
        return imgs[shot["shot_id"]]

    clips = []
    for c in package.select_clips(spec, float(inp.get("whole_max_s", 75)), float(inp.get("cut_max_s", 60))):
        S, E = c["start_s"], c["end_s"]
        cd = wd / f"clip{c['n']:02d}"
        # planos que aparecem dentro da janela, cortados nas bordas, em quadros inteiros
        parts = []
        for s in shots:
            a, b = max(S, s.get("start_s") or 0), min(E, s.get("end_s") or 0)
            frames = round(b * fps) - round(a * fps)
            if frames <= 0 or not (s.get("image") or {}).get("url"):
                continue
            mode = (s.get("motion") or {}).get("kenburns") or "push_in"
            parts.append(media.vertical_kenburns(image_of(s), cd / f"{s['order']:03d}.mp4", frames / fps, mode))
        if not parts:
            continue
        video = media.concat_videos(parts, cd / "video.mp4")
        dur = media.duration(video)
        words = []
        for b in spec["blocks"]:
            off = (b.get("audio") or {}).get("offset_s") or 0
            for w in (b.get("audio") or {}).get("words") or []:
                ws, we = w["s"] + off, w["e"] + off
                if ws >= S - 0.05 and we <= E + 0.05:
                    words.append({"w": w["w"], "s": max(0.0, ws - S), "e": min(dur, we - S)})
        meta = package.clip_caption(c, spec, cfg)
        ass = media.write_clip_ass(words, meta["header"], dur, end_card, cd / "subs.ass")
        out = media.finish_clip(video, final, S, dur, ass, wd / f"tiktok{c['n']:02d}.mp4")
        clips.append({
            "n": c["n"], "title": c["title"], "start_s": S, "end_s": E,
            "duration_s": round(media.duration(out), 2),
            "url": storage.upload(out, _key(job, f"tiktok/clip{c['n']:02d}.mp4"), "video/mp4"),
            "caption": meta["caption"],
        })
        shutil.rmtree(cd, ignore_errors=True)
        out.unlink(missing_ok=True)
        log.info("clipe %d pronto (%.1fs): %s", c["n"], clips[-1]["duration_s"], c["title"])
    if not clips:
        raise RuntimeError("nenhum clipe gerado (o vídeo não tem tempos de áudio por bloco)")
    return {"clips": clips, "title": spec.get("publishing", {}).get("title") or spec.get("chosen_title")}


def h_youtube_upload(job: dict, inp: dict, wd: Path) -> dict:
    """Envia cada arquivo para a sessão resumable que o n8n abriu. Entrada:
    uploads: [{upload_url, media_url, content_type?, ref?}]"""
    from . import youtube

    # cada envio é independente: uma thumbnail recusada (canal sem verificação, por ex.)
    # não pode impedir os Shorts de subirem
    results = []
    for i, u in enumerate(inp["uploads"], 1):
        ref = u.get("ref") or f"upload{i}"
        try:
            src = storage.download(u["media_url"], wd / f"up{i}{Path(u['media_url'].split('?')[0]).suffix}")
            log.info("enviando ao YouTube: %s (%.1f MB)", ref, src.stat().st_size / 1e6)
            resp = youtube.upload(u["upload_url"], src, u.get("content_type") or youtube.guess_type(src.name))
            src.unlink(missing_ok=True)
            results.append({"ref": ref, "ok": True, "id": resp.get("id"), "response": resp})
            log.info("YouTube: %s enviado (id=%s)", ref, resp.get("id"))
        except Exception as exc:
            log.error("YouTube: %s falhou: %s", ref, exc)
            results.append({"ref": ref, "ok": False, "id": None, "error": str(exc)[:500]})
    if results and not any(r["ok"] for r in results):
        raise RuntimeError("nenhum envio ao YouTube deu certo: " + " | ".join(f"{r['ref']}: {r['error']}" for r in results))
    return {"uploads": results}


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


# ---------------------------------------------------------------------------
# Canal de notícias (Short vertical por notícia e resumo diário horizontal)
# ---------------------------------------------------------------------------
NEWS_GAP_S = 0.25   # respiro entre trechos de narração
NEWS_TAIL_S = 2.3   # cartão final


def _narrate(text: str, voice: str, rate: str, out: Path) -> tuple[Path, list[dict], float]:
    words: list[dict] = []
    for attempt in range(3):  # edge-tts às vezes devolve áudio vazio
        words = tts.synthesize(newsvideo.clean_tts(text), voice, out, rate=rate)
        if out.exists() and out.stat().st_size > 1000 and words:
            break
        time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"edge-tts falhou: {text[:60]}")
    return out, words, media.duration(out)


def _news_scenes(visuals: list[dict], inp: dict, wd: Path, tag: str, checks: list[dict]) -> list[dict]:
    """Imagens 1:1 (IA) e cartões de dados de um trecho. Imagem que falhar vira cartão com a manchete."""
    sport = inp.get("sport") or "futebol"
    color = inp.get("color") or newsvideo.SPORT_COLOR.get(sport, "#F2B705")
    label = newsvideo.SPORT_LABEL.get(sport, sport.upper())
    style = inp.get("image_style") or ""

    def one(i_v: tuple[int, dict]) -> dict:
        i, v = i_v
        name = f"{tag}-{i}"
        if v.get("url"):  # cena já pronta (resumo reaproveitando os Shorts)
            src = storage.download(v["url"], wd / "src" / f"{name}{Path(v['url'].split('?')[0]).suffix or '.img'}")
            return {"path": newsvideo.square(src, wd / "scenes" / f"{name}.jpg"), "kind": "reuse", "motion": v.get("motion")}
        if v.get("type") == "card" or v.get("card"):
            out = newsvideo.render_card(v.get("card") or v, color, wd / "scenes" / f"{name}.png")
            return {"path": out, "kind": "card", "motion": v.get("motion") or "push_in", "card": v.get("card") or v}
        prompt = f"{v.get('prompt', '')}. {style}".strip(". ")
        try:
            raw, provider = images.generate(prompt, inp.get("image_model"), "1:1")
            out = images.to_jpeg(raw, wd / "scenes" / f"{name}.jpg", width=newsvideo.SQ, aspect=1.0)
            return {"path": out, "kind": "image", "provider": provider, "prompt": prompt, "motion": v.get("motion")}
        except Exception as exc:
            log.warning("imagem %s falhou, usando cartão: %s", name, exc)
            checks.append({"stage": "images", "name": f"image_fallback:{name}", "passed": False,
                           "detail": {"error": str(exc)[:300]}})
            out = newsvideo.title_card(inp.get("headline") or "", color, wd / "scenes" / f"{name}.png", label)
            return {"path": out, "kind": "fallback", "motion": "push_in"}

    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(one, enumerate(visuals)))


def _news_render(job: dict, inp: dict, wd: Path, segments: list[dict], layout: str) -> dict:
    """segments: [{narration, scenes: [{path, motion}], panel: Path}] → vídeo final com narração.
    Cada trecho dura o tempo da sua narração; as cenas do trecho dividem esse tempo."""
    voice, rate = inp["voice"], inp.get("rate", "+0%")
    fps = settings.fps
    audio_parts, words, timeline = [], [], []
    t = 0.0
    for i, seg in enumerate(segments):
        mp3, w, dur = _narrate(seg["narration"], voice, rate, wd / "audio" / f"{i:02d}.mp3")
        audio_parts.append(media.to_wav(mp3, wd / "audio" / f"{i:02d}.wav"))
        last = i == len(segments) - 1
        tail = NEWS_TAIL_S if (last and inp.get("end_card")) else 0.0
        gap = NEWS_GAP_S if not last else 0.4
        audio_parts.append(media.silence(wd / "audio" / f"{i:02d}-gap.wav", gap + tail))
        words += [{"w": x["w"], "s": round(x["s"] + t, 3), "e": round(x["e"] + t, 3)} for x in w]
        seg_len = dur + gap + tail
        timeline.append({"start_s": round(t, 3), "end_s": round(t + seg_len, 3), "narration_s": round(dur, 3)})
        t += seg_len
    total = t
    narration = media.concat_audio(audio_parts, wd / "narration.wav")

    motions = ["push_in", "pan_right", "pull_out", "pan_left", "pan_up"]
    clips, k = [], 0
    for i, seg in enumerate(segments):
        S, E = timeline[i]["start_s"], timeline[i]["end_s"]
        scenes = seg["scenes"] or [{"path": seg["fallback"], "motion": "push_in"}]
        # cenas longas demais cansam: repete as cenas do trecho com outro movimento
        per_max = float(inp.get("max_scene_s", 7 if layout == "vertical" else 9))
        n = max(len(scenes), int(-(-(E - S) // per_max)))
        for j in range(n):
            a, b = S + (E - S) * j / n, S + (E - S) * (j + 1) / n
            frames = round(b * fps) - round(a * fps)
            if frames <= 0:
                continue
            sc = scenes[j % len(scenes)]
            mode = sc.get("motion") if j < len(scenes) and sc.get("motion") else motions[k % len(motions)]
            clips.append(newsvideo.scene_clip(sc["path"], seg["panel"], wd / "clips" / f"{k:03d}.mp4",
                                              frames / fps, layout, mode))
            k += 1
    video = media.concat_videos(clips, wd / "video.mp4")
    if layout == "vertical":
        ass = media.write_word_ass(words, wd / "subs.ass")
        newsvideo.add_end_card(ass, total, inp.get("end_card") or [])
        video = newsvideo.burn(video, ass, wd / "video.subs.mp4")
    elif inp.get("end_card"):
        ass = wd / "end.ass"
        ass.write_text("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\n"
                       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
                       "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                       "Alignment, MarginL, MarginR, MarginV, Encoding\n\n[Events]\n"
                       "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n", "utf-8")
        newsvideo.add_end_card(ass, total, inp["end_card"])
        video = newsvideo.burn(video, ass, wd / "video.subs.mp4")
    music = storage.download(inp["music_url"], wd / "music.mp3") if inp.get("music_url") else None
    lufs = float(inp.get("lufs", -14))
    final = media.master(video, narration, wd / "final.mp4", lufs=lufs, music=music,
                         music_db=float(inp.get("music_db", -24)))
    return {"final": final, "words": words, "timeline": timeline, "total": total, "lufs": lufs}


def h_news_short(job: dict, inp: dict, wd: Path) -> dict:
    """Short vertical (1080x1920) de uma notícia. Entrada:
    sport, headline, sources_label, channel_name, voice, rate, image_style, end_card,
    beats: [{narration, visuals: [{type: image, prompt} | {type: card, card: {...}}]}]"""
    sport = inp.get("sport") or "futebol"
    color = inp.get("color") or newsvideo.SPORT_COLOR.get(sport, "#F2B705")
    panel = newsvideo.vertical_panel(inp.get("headline") or "", sport, color, inp.get("channel_name") or "",
                                     inp.get("sources_label") or "", wd / "panel.png")
    checks: list[dict] = []
    beats = inp["beats"]
    scenes = [_news_scenes(b.get("visuals") or ([b["visual"]] if b.get("visual") else []), inp, wd, f"b{i:02d}", checks)
              for i, b in enumerate(beats)]
    fallback = newsvideo.title_card(inp.get("headline") or "", color, wd / "scenes" / "title.png",
                                    newsvideo.SPORT_LABEL.get(sport, sport.upper()))
    segs = [{"narration": b["narration"], "scenes": scenes[i], "panel": panel, "fallback": fallback}
            for i, b in enumerate(beats)]
    r = _news_render(job, inp, wd, segs, "vertical")
    final = r["final"]

    first = next((s["path"] for ss in scenes for s in ss), fallback)
    cov = newsvideo.cover(first, panel, wd / "cover.jpg", "vertical")
    dur = media.duration(final)
    for c in _media_checks(final, "news_short", r["lufs"], float(inp.get("min_duration_s", 20))):
        if c["name"] == "no_long_silence":  # o silêncio do cartão final é esperado
            c["detail"]["silences"] = [x for x in c["detail"]["silences"] if x["start"] < dur - NEWS_TAIL_S - 1.5]
            c["passed"] = not c["detail"]["silences"]
        checks.append(c)
    checks.append({"stage": "news_short", "name": "short_max_duration", "passed": dur <= float(inp.get("max_duration_s", 60)),
                   "detail": {"duration_s": round(dur, 2)}})
    # cenas sobem para o resumo diário reaproveitar sem gerar imagem de novo
    out_beats = []
    for i, b in enumerate(beats):
        ups = []
        for j, s in enumerate(scenes[i]):
            ext = s["path"].suffix
            ups.append({"kind": s["kind"], "card": s.get("card"), "prompt": s.get("prompt"),
                        "url": storage.upload(s["path"], _key(job, f"scenes/b{i:02d}-{j}{ext}"),
                                              "image/png" if ext == ".png" else "image/jpeg")})
        out_beats.append({"narration": b["narration"], "scenes": ups, **r["timeline"][i]})
    spec = {"type": "news_short", "sport": sport, "headline": inp.get("headline"), "beats": out_beats,
            "words": r["words"], "duration_s": round(dur, 2), "checks": checks}
    spec_path = wd / "news_spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), "utf-8")
    return {
        "url": storage.upload(final, _key(job, "short.mp4"), "video/mp4"),
        "cover_url": storage.upload(cov, _key(job, "cover.jpg"), "image/jpeg"),
        "spec_url": storage.upload(spec_path, _key(job, "news_spec.json"), "application/json"),
        "duration_s": round(dur, 2),
        "beats": out_beats,
        "checks": checks,
        "fallback_images": sum(1 for ss in scenes for s in ss if s["kind"] == "fallback"),
    }


def h_news_recap(job: dict, inp: dict, wd: Path) -> dict:
    """Resumo horizontal (1920x1080) de um esporte. Entrada:
    sport, title, channel_name, voice, rate, end_card, thumbnail_lines,
    segments: [{headline, kicker?, narration, visuals: [{url} | {type: card, card} | {type: image, prompt}]}]
    (o primeiro costuma ser a abertura e o último o fechamento, com cartões)."""
    sport = inp.get("sport") or "futebol"
    color = inp.get("color") or newsvideo.SPORT_COLOR.get(sport, "#F2B705")
    label = newsvideo.SPORT_LABEL.get(sport, sport.upper())
    checks: list[dict] = []
    stories = [s for s in inp["segments"] if s.get("story")]
    segs, chapters = [], []
    for i, s in enumerate(inp["segments"]):
        n = stories.index(s) + 1 if s in stories else 0
        counter = f"{n}/{len(stories)}" if n else (inp.get("title") or "")
        panel = newsvideo.horizontal_panel(s.get("headline") or inp.get("title") or "", sport, color,
                                           inp.get("channel_name") or "", counter, wd / "panels" / f"{i:02d}.png",
                                           s.get("kicker") or "")
        fb = newsvideo.title_card(s.get("headline") or "", color, wd / "scenes" / f"t{i:02d}.png", label)
        segs.append({"narration": s["narration"], "panel": panel, "fallback": fb,
                     "scenes": _news_scenes(s.get("visuals") or [], {**inp, "headline": s.get("headline")}, wd, f"s{i:02d}", checks)})
    r = _news_render(job, inp, wd, segs, "horizontal")
    final = r["final"]
    for i, s in enumerate(inp["segments"]):
        chapters.append({"t": round(r["timeline"][i]["start_s"]), "title": s.get("chapter") or s.get("headline") or ""})
    # o YouTube só mostra capítulos se o primeiro começa em 0:00 e há 3+ com 10 s ou mais
    for c in _media_checks(final, "news_recap", r["lufs"], float(inp.get("min_duration_s", 90))):
        if c["name"] == "no_long_silence":
            c["detail"]["silences"] = [x for x in c["detail"]["silences"] if x["start"] < r["total"] - NEWS_TAIL_S - 1.5]
            c["passed"] = not c["detail"]["silences"]
        checks.append(c)

    thumbs = []
    bg = next((x["path"] for sg in segs[1:] + segs[:1] for x in sg["scenes"] if x["kind"] in ("image", "reuse")), None)
    if bg and inp.get("thumbnail_lines"):
        out = wd / "thumb.jpg"
        check = thumbnail.render(bg, inp["thumbnail_lines"], out, settings.font_path, accent=color)
        thumbs.append({"url": storage.upload(out, _key(job, "thumbs/thumb1.jpg"), "image/jpeg"),
                       "lines": inp["thumbnail_lines"], "check": check})
    srt = media.write_srt(r["words"], wd / "recap.srt")
    dur = media.duration(final)
    return {
        "url": storage.upload(final, _key(job, "recap.mp4"), "video/mp4"),
        "srt_url": storage.upload(srt, _key(job, "recap.srt"), "application/x-subrip"),
        "thumbnails": thumbs,
        "chapters": chapters,
        "duration_s": round(dur, 2),
        "checks": checks,
        "fallback_images": sum(1 for sg in segs for x in sg["scenes"] if x["kind"] == "fallback"),
    }


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
    "package": h_package,
    "youtube_upload": h_youtube_upload,
    "clips": h_clips,
    "news_short": h_news_short,
    "news_recap": h_news_recap,
}

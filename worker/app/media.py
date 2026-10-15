"""Operações de mídia com ffmpeg: Ken Burns, montagem, mixagem, legendas,
Shorts verticais e checagens automáticas."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable

from .settings import settings

KB_ZOOM = 0.12  # zoom máximo do Ken Burns (12%)


class MediaError(RuntimeError):
    pass


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise MediaError(f"comando falhou ({cmd[0]}):\n{tail}")
    return proc.stderr


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def _x264() -> list[str]:
    return ["-c:v", "libx264", "-preset", settings.x264_preset, "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", str(settings.fps)]


# ---------------------------------------------------------------------------
# Planos
# ---------------------------------------------------------------------------
def _drawtext(text_file: Path) -> str:
    font = settings.font_path.replace(":", r"\:")
    tf = str(text_file).replace(":", r"\:")
    return (f"drawtext=fontfile='{font}':textfile='{tf}':fontsize=h/11:fontcolor=white:"
            f"borderw=6:bordercolor=black@0.85:x=(w-text_w)/2:y=h*0.08")


def kenburns(image: Path, out: Path, seconds: float, mode: str = "push_in",
             text_overlay: str | None = None) -> Path:
    """Transforma uma imagem parada em um clipe com movimento suave."""
    w, h, fps = settings.width, settings.height, settings.fps
    n = max(1, round(seconds * fps))
    z_max = 1 + KB_ZOOM
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    motions = {
        "push_in": (f"1+{KB_ZOOM}*on/{n}", cx, cy),
        "pull_out": (f"{z_max}-{KB_ZOOM}*on/{n}", cx, cy),
        "pan_left": (f"{z_max}", f"(iw-iw/zoom)*(1-on/{n})", cy),
        "pan_right": (f"{z_max}", f"(iw-iw/zoom)*on/{n}", cy),
        "pan_up": (f"{z_max}", cx, f"(ih-ih/zoom)*(1-on/{n})"),
        "pan_down": (f"{z_max}", cx, f"(ih-ih/zoom)*on/{n}"),
    }
    z, x, y = motions.get(mode, motions["push_in"])
    # Imagem ampliada antes do zoompan reduz o "tremido" do movimento.
    # KB_UPSCALE=2 (padrão, mais suave) ou 1.5 (mais rápido).
    up = float(os.environ.get("KB_UPSCALE", "2"))
    uw, uh = int(w * up) // 2 * 2, int(h * up) // 2 * 2
    vf = (f"scale={uw}:{uh}:force_original_aspect_ratio=increase,crop={uw}:{uh},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={w}x{h}:fps={fps}")
    if text_overlay:
        tf = out.with_suffix(".txt")
        tf.write_text(text_overlay, encoding="utf-8")
        vf += "," + _drawtext(tf)
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(image), "-vf", vf, "-frames:v", str(n),
         *_x264(), "-an", str(out)])
    return out


def fit_clip(src: Path, out: Path, seconds: float, text_overlay: str | None = None) -> Path:
    """Ajusta um clipe de IA ao tamanho, fps e duração do plano (corta ou congela o fim)."""
    w, h = settings.width, settings.height
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={settings.fps},"
          f"tpad=stop_mode=clone:stop_duration={seconds:.3f}")
    if text_overlay:
        tf = out.with_suffix(".txt")
        tf.write_text(text_overlay, encoding="utf-8")
        vf += "," + _drawtext(tf)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-t", f"{seconds:.3f}",
         *_x264(), "-an", str(out)])
    return out


def concat_videos(clips: Iterable[Path], out: Path) -> Path:
    lst = out.with_suffix(".list.txt")
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    return out


# ---------------------------------------------------------------------------
# Áudio
# ---------------------------------------------------------------------------
def to_wav(src: Path, out: Path) -> Path:
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "48000", str(out)])
    return out


def silence(out: Path, seconds: float) -> Path:
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
         "-t", f"{seconds:.3f}", str(out)])
    return out


def concat_audio(parts: Iterable[Path], out: Path) -> Path:
    lst = out.with_suffix(".list.txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    return out


def _loudnorm_measure(src: Path, lufs: float) -> dict:
    err = run(["ffmpeg", "-v", "info", "-i", str(src), "-af",
               f"loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    blob = err[err.rfind("{"): err.rfind("}") + 1]
    return json.loads(blob)


def master(video: Path, narration: Path, out: Path, lufs: float = -14.0,
           music: Path | None = None, music_db: float = -22.0) -> Path:
    """Mistura narração e música (com ducking), normaliza em LUFS e junta ao vídeo."""
    mixed = out.with_name("mix.wav")
    if music:
        fc = (f"[1:a]volume={music_db}dB,aformat=channel_layouts=stereo[m];"
              f"[0:a]aformat=channel_layouts=stereo,asplit=2[v][sc];"
              f"[m][sc]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=400[duck];"
              f"[v][duck]amix=inputs=2:duration=first:normalize=0[a]")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(narration), "-stream_loop", "-1", "-i", str(music),
             "-filter_complex", fc, "-map", "[a]", "-ar", "48000", str(mixed)])
    else:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(narration), "-ac", "2", "-ar", "48000", str(mixed)])

    m = _loudnorm_measure(mixed, lufs)
    af = (f"loudnorm=I={lufs}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(mixed), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest",
         "-movflags", "+faststart", str(out)])
    return out


def preview(src: Path, out: Path) -> Path:
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", "scale=-2:480", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)])
    return out


# ---------------------------------------------------------------------------
# Legendas
# ---------------------------------------------------------------------------
def _ts(t: float, sep: str = ",") -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def caption_lines(words: list[dict], max_chars: int = 42, max_dur: float = 4.0) -> list[tuple[float, float, str]]:
    lines, cur = [], []
    for w in words:
        text = " ".join(x["w"] for x in cur + [w])
        if cur and (len(text) > max_chars or w["e"] - cur[0]["s"] > max_dur):
            lines.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
            cur = []
        cur.append(w)
        if re.search(r"[.!?]$", w["w"]):
            lines.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
            cur = []
    if cur:
        lines.append((cur[0]["s"], cur[-1]["e"], " ".join(x["w"] for x in cur)))
    return lines


def write_srt(words: list[dict], out: Path) -> Path:
    blocks = [f"{i}\n{_ts(s)} --> {_ts(e)}\n{t}\n" for i, (s, e, t) in enumerate(caption_lines(words), 1)]
    out.write_text("\n".join(blocks), encoding="utf-8")
    return out


def _ass_escape(t: str) -> str:
    return t.replace("\\", "").replace("{", "(").replace("}", ")")


def write_word_ass(words: list[dict], out: Path, group: int = 3, font: str = "DejaVu Sans") -> Path:
    """Legenda vertical palavra por palavra: mostra grupos de até 3 palavras,
    com a palavra falada em destaque."""
    head = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: W,{font},86,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,2,2,60,60,520,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    # grupos de até `group` palavras, sem atravessar o fim de uma frase
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == group or re.search(r"[.!?,;:]$", w["w"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)

    events = []
    for ci, chunk in enumerate(chunks):
        nxt = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else None
        for i, w in enumerate(chunk):
            end = chunk[i + 1]["s"] if i + 1 < len(chunk) else w["e"]
            if nxt is not None and i + 1 == len(chunk):
                end = max(end, min(nxt, w["e"] + 0.3))
            parts = [("{\\c&H0000E5FF&}" + _ass_escape(x["w"]).upper() + "{\\c&H00FFFFFF&}") if j == i
                     else _ass_escape(x["w"]).upper() for j, x in enumerate(chunk)]
            events.append(f"Dialogue: 0,{_ts(w['s'], '.')[1:-1]},{_ts(end, '.')[1:-1]},W,,0,0,0,," + " ".join(parts))
    out.write_text(head + "\n".join(events) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Shorts
# ---------------------------------------------------------------------------
def vertical_short(final: Path, start: float, end: float, words: list[dict], out: Path) -> Path:
    """Corta um trecho e monta em 1080x1920: fundo desfocado, vídeo no centro,
    legenda palavra por palavra."""
    dur = end - start
    local = [{"w": w["w"], "s": max(0.0, w["s"] - start), "e": min(dur, w["e"] - start)}
             for w in words if w["s"] >= start - 0.05 and w["e"] <= end + 0.05]
    ass = write_word_ass(local, out.with_suffix(".ass"))
    ass_path = str(ass).replace(":", r"\:")
    fc = ("[0:v]split=2[a][b];"
          "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2[bg];"
          # vídeo em destaque: 1440 de largura com as bordas cortadas, ~75% da cena visível
          "[b]scale=1440:-2,crop=1080:ih[fg];"
          f"[bg][fg]overlay=(W-w)/2:(H-h)/2,ass='{ass_path}'[v]")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(final),
         "-filter_complex", fc, "-map", "[v]", "-map", "0:a", *_x264(), "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", str(out)])
    return out


# ---------------------------------------------------------------------------
# Checagens
# ---------------------------------------------------------------------------
def silences(path: Path, noise_db: float = -40, min_s: float = 1.5) -> list[dict]:
    err = run(["ffmpeg", "-v", "info", "-i", str(path), "-af",
               f"silencedetect=noise={noise_db}dB:d={min_s}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [(float(a), float(b)) for a, b in re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", err)]
    return [{"start": s, "end": e, "duration": d} for s, (e, d) in zip(starts, ends)]


def black_frames(path: Path, min_s: float = 0.5) -> list[dict]:
    err = run(["ffmpeg", "-v", "info", "-i", str(path), "-vf", f"blackdetect=d={min_s}:pix_th=0.10",
               "-an", "-f", "null", "-"])
    return [{"start": float(a), "end": float(b), "duration": float(c)}
            for a, b, c in re.findall(r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)", err)]


def integrated_lufs(path: Path) -> float:
    err = run(["ffmpeg", "-v", "info", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"])
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(found[-1]) if found else float("nan")


# ---------------------------------------------------------------------------
# Clipes verticais para TikTok / Reels (remontados a partir das imagens)
# ---------------------------------------------------------------------------
CLIP_W, CLIP_H, CLIP_FG = 1080, 1920, 1080  # quadro 9:16 com a cena num quadrado no meio
CLIP_FG_Y = 380


def vertical_kenburns(image: Path, out: Path, seconds: float, mode: str = "push_in") -> Path:
    """Um plano em 9:16: fundo desfocado da própria imagem e a cena em movimento
    num quadrado de 1080 px no meio (espaço livre em cima para o título e embaixo para a legenda)."""
    fps = settings.fps
    n = max(1, round(seconds * fps))
    z_max = 1 + KB_ZOOM
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    motions = {
        "push_in": (f"1+{KB_ZOOM}*on/{n}", cx, cy),
        "pull_out": (f"{z_max}-{KB_ZOOM}*on/{n}", cx, cy),
        "pan_left": (f"{z_max}", f"(iw-iw/zoom)*(1-on/{n})", cy),
        "pan_right": (f"{z_max}", f"(iw-iw/zoom)*on/{n}", cy),
        "pan_up": (f"{z_max}", cx, f"(ih-ih/zoom)*(1-on/{n})"),
        "pan_down": (f"{z_max}", cx, f"(ih-ih/zoom)*on/{n}"),
    }
    z, x, y = motions.get(mode, motions["push_in"])
    up = float(os.environ.get("KB_UPSCALE", "2"))
    s = int(CLIP_FG * up) // 2 * 2
    fc = (
        "[0:v]split=2[a][b];"
        f"[a]scale={s}:{s}:force_original_aspect_ratio=increase,crop={s}:{s},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={CLIP_FG}x{CLIP_FG}:fps={fps}[fg];"
        f"[b]scale={CLIP_W}:{CLIP_H}:force_original_aspect_ratio=increase,crop={CLIP_W}:{CLIP_H},"
        f"boxblur=30:3,eq=brightness=-0.18,loop=loop={n}:size=1:start=0,fps={fps}[bg];"
        f"[bg][fg]overlay=0:{CLIP_FG_Y}:shortest=1,trim=end_frame={n}[v]"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(image), "-filter_complex", fc, "-map", "[v]",
         "-frames:v", str(n), *_x264(), "-an", str(out)])
    return out


def write_clip_ass(words: list[dict], header: list[str], total: float, end_card: list[str],
                   out: Path, font: str = "DejaVu Sans", end_s: float = 2.5) -> Path:
    """Legenda palavra por palavra abaixo da cena + título fixo em cima + cartão final."""
    base = write_word_ass(words, out.with_suffix(".words.ass"), font=font).read_text("utf-8")
    head, events = base.split("[Events]", 1)
    # legenda logo abaixo do quadrado da cena (o estilo W fica na parte de baixo)
    head = head.replace(",2,60,60,520,1", ",2,60,60,210,1")
    head = head.rstrip("\n") + (
        f"\nStyle: H,{font},66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,6,2,8,60,60,110,1"
        f"\nStyle: K,{font},54,&H0005B7F2,&H0005B7F2,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,6,2,8,60,60,110,1"
        f"\nStyle: E,{font},78,&H00FFFFFF,&H00FFFFFF,&H00000000,&HC8000000,-1,0,0,0,100,100,0,0,3,18,0,5,80,80,0,1\n\n"
    )
    t0, t_end = _ts(0, ".")[1:-1], _ts(total, ".")[1:-1]
    extra = []
    if header:
        # 1ª linha (destaque amarelo) e 2ª linha (branca) no topo, o clipe todo
        extra.append(f"Dialogue: 1,{t0},{t_end},K,,0,0,0,,{_ass_escape(header[0]).upper()}")
        if len(header) > 1:
            extra.append(f"Dialogue: 1,{t0},{t_end},H,,0,0,0,,\\N{_ass_escape(header[1]).upper()}")
    if end_card:
        s = _ts(max(0.0, total - end_s), ".")[1:-1]
        extra.append(f"Dialogue: 2,{s},{t_end},E,,0,0,0,," + "\\N".join(_ass_escape(x) for x in end_card))
    out.write_text(head + "[Events]" + events.rstrip("\n") + "\n" + "\n".join(extra) + "\n", encoding="utf-8")
    return out


def finish_clip(video: Path, audio_src: Path, start: float, dur: float, ass: Path, out: Path) -> Path:
    """Junta o vídeo dos planos com o trecho do áudio final (narração + música já mixadas) e as legendas."""
    ass_path = str(ass).replace(":", r"\:")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-ss", f"{start:.3f}", "-t", f"{dur:.3f}",
         "-i", str(audio_src), "-filter_complex", f"[0:v]ass='{ass_path}'[v]",
         "-map", "[v]", "-map", "1:a", *_x264(), "-c:a", "aac", "-b:a", "160k",
         "-af", "afade=t=out:st=" + f"{max(0.0, dur - 0.6):.3f}" + ":d=0.6",
         "-shortest", "-movflags", "+faststart", str(out)])
    return out

"""Movimento "estilo canal de animação" para imagens paradas (channels.config.motion).

Cada plano vira 1 a 3 cortes da mesma imagem, com enquadramentos diferentes (geral, close no
centro, close num terço), e cada corte tem um movimento de câmera com aceleração suave (easing)
e, opcionalmente, um balanço bem leve de câmera na mão. Assim os cortes ficam rápidos sem gastar
mais imagens da cota.

config.motion:
  style        "dynamic" liga este módulo (sem ele, o Ken Burns clássico de media.kenburns)
  cut_s        duração alvo de cada corte em segundos (padrão 3.0)
  max_cuts     máximo de cortes por imagem (padrão 3)
  zoom         intensidade do zoom/pan do corte geral (padrão 0.22 = 22%)
  close        zoom dos closes (padrão 1.55)
  shake        balanço leve de câmera (padrão true)
  hud          estilo do texto do plano: "top" (padrão antigo, centralizado no alto) ou
               "badge" (selo no canto superior esquerdo, para contador de dias)
"""
from __future__ import annotations

import os
import random
from pathlib import Path

from . import media
from .settings import settings

# movimentos do corte geral: (zoom inicial, zoom final, centro x/y inicial, centro x/y final)
WIDE_MOVES = {
    "push_in":    (1.00, 1.00, 0.50, 0.50, 0.50, 0.50),  # z1 recebe +zoom
    "pull_out":   (1.00, 1.00, 0.50, 0.50, 0.50, 0.50),
    "pan_right":  (1.00, 1.00, 0.38, 0.50, 0.62, 0.50),
    "pan_left":   (1.00, 1.00, 0.62, 0.50, 0.38, 0.50),
    "pan_up":     (1.00, 1.00, 0.50, 0.62, 0.50, 0.40),
    "pan_down":   (1.00, 1.00, 0.50, 0.40, 0.50, 0.62),
    "diag_in":    (1.00, 1.00, 0.40, 0.42, 0.58, 0.56),
    "diag_out":   (1.00, 1.00, 0.60, 0.58, 0.44, 0.46),
}
# pontos de close (centro x, y): personagem costuma estar no centro ou num terço
CLOSE_POINTS = [(0.50, 0.50), (0.36, 0.52), (0.64, 0.52), (0.50, 0.40)]


def _move_filter(n: int, z0: float, z1: float, x0: float, y0: float, x1: float, y1: float,
                 shake: bool, seed: int) -> str:
    """Expressão do zoompan com easing cosseno e balanço senoidal leve."""
    p = f"((1-cos(PI*on/{max(n - 1, 1)}))/2)"
    z = f"({z0:.4f}+({z1 - z0:.4f})*{p})"
    cx = f"(({x0:.4f}+({x1 - x0:.4f})*{p})*iw)"
    cy = f"(({y0:.4f}+({y1 - y0:.4f})*{p})*ih)"
    sx = sy = "0"
    if shake:
        r = random.Random(seed)
        ax, ay = 0.0022, 0.0030  # amplitude em fração da imagem (bem sutil)
        fx, fy = r.uniform(0.18, 0.28), r.uniform(0.22, 0.34)  # ciclos por segundo
        ph = r.uniform(0, 6.28)
        fps = settings.fps
        sx = f"({ax}*iw*sin(2*PI*{fx}*on/{fps}+{ph:.2f}))"
        sy = f"({ay}*ih*sin(2*PI*{fy}*on/{fps}+{ph + 1.3:.2f}))"
    x = f"clip({cx}-iw/zoom/2+{sx},0,iw-iw/zoom)"
    y = f"clip({cy}-ih/zoom/2+{sy},0,ih-ih/zoom)"
    return f"z='{z}':x='{x}':y='{y}'"


def _render_cut(image: Path, out: Path, seconds: float, move: tuple, shake: bool, seed: int,
                overlay_file: Path | None, hud: str) -> Path:
    w, h, fps = settings.width, settings.height, settings.fps
    n = max(1, round(seconds * fps))
    up = float(os.environ.get("KB_UPSCALE", "2"))
    uw, uh = int(w * up) // 2 * 2, int(h * up) // 2 * 2
    zp = _move_filter(n, *move, shake=shake, seed=seed)
    vf = (f"scale={uw}:{uh}:force_original_aspect_ratio=increase,crop={uw}:{uh},"
          f"zoompan={zp}:d={n}:s={w}x{h}:fps={fps}")
    if overlay_file:
        vf += "," + (badge(overlay_file) if hud == "badge" else media._drawtext(overlay_file))
    out.parent.mkdir(parents=True, exist_ok=True)
    media.run(["ffmpeg", "-y", "-v", "error", "-i", str(image), "-vf", vf, "-frames:v", str(n),
               *media._x264(), "-an", str(out)])
    return out


def badge(text_file: Path) -> str:
    """Selo no canto superior esquerdo (ex.: 'DIA 47'), caixa escura com borda clara."""
    font = settings.font_path.replace(":", r"\:")
    tf = str(text_file).replace(":", r"\:")
    return (f"drawtext=fontfile='{font}':textfile='{tf}':fontsize=h/17:fontcolor=white:"
            f"box=1:boxcolor=0x14161c@0.88:boxborderw=22:x=w*0.035:y=h*0.05:"
            f"borderw=0")


def render_shot(image: Path, out: Path, seconds: float, mode: str, overlay: str | None,
                cfg: dict, seed: int) -> Path:
    """Plano com 1 a 3 cortes da mesma imagem. Os cortes têm duração em quadros inteiros
    e somam exatamente a duração do plano (não desalinha o áudio)."""
    fps = settings.fps
    total = max(1, round(seconds * fps))
    cut_s = float(cfg.get("cut_s", 3.0))
    max_cuts = max(1, int(cfg.get("max_cuts", 3)))
    zoom = float(cfg.get("zoom", 0.22))
    close = float(cfg.get("close", 1.55))
    shake = cfg.get("shake", True)
    hud = cfg.get("hud", "top")
    k = max(1, min(max_cuts, int(seconds / cut_s + 0.35)))
    if total < k * fps:  # cada corte com pelo menos 1 s
        k = max(1, total // fps)

    r = random.Random(seed)
    base = WIDE_MOVES.get(mode) or WIDE_MOVES[r.choice(list(WIDE_MOVES))]
    z0, z1, x0, y0, x1, y1 = base
    if mode == "pull_out":
        z0 = 1 + zoom
    else:
        z1 = 1 + zoom
    moves = [(z0, z1, x0, y0, x1, y1)]
    points = CLOSE_POINTS[:]
    r.shuffle(points)
    for i in range(1, k):
        cx, cy = points[(i - 1) % len(points)]
        drift = r.choice([-0.04, 0.04])
        if i % 2:  # close que aproxima devagar
            moves.append((close, close + 0.10, cx, cy, cx + drift, cy))
        else:      # close que abre devagar
            moves.append((close + 0.12, close, cx + drift, cy, cx, cy))

    overlay_file = None
    if overlay:
        overlay_file = out.with_suffix(".txt")
        overlay_file.write_text(overlay, encoding="utf-8")

    frames = [total // k + (1 if i < total % k else 0) for i in range(k)]
    parts = []
    for i, (mv, nf) in enumerate(zip(moves, frames)):
        parts.append(_render_cut(image, out.with_name(f"{out.stem}.c{i}.mp4"), nf / fps, mv, shake,
                                 seed * 10 + i, overlay_file, hud))
    if len(parts) == 1:
        parts[0].replace(out)
        return out
    media.concat_videos(parts, out)
    for p in parts:
        p.unlink(missing_ok=True)
    return out

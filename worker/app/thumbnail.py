"""Thumbnails 1280x720: imagem de fundo + frase de 2 linhas na metade esquerda,
com teste de legibilidade simulando a miniatura no celular (20% do tamanho)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

W, H = 1280, 720


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _luminance(rgb: tuple[float, float, float]) -> float:
    def ch(v: float) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _fit_font(draw: ImageDraw.ImageDraw, lines: list[str], font_path: str, max_w: int, max_h: int):
    size = 220
    while size > 40:
        font = ImageFont.truetype(font_path, size)
        widths = [draw.textbbox((0, 0), ln, font=font, stroke_width=size // 14)[2] for ln in lines]
        height = sum(draw.textbbox((0, 0), ln, font=font, stroke_width=size // 14)[3] for ln in lines)
        if max(widths) <= max_w and height <= max_h:
            return font
        size -= 8
    return ImageFont.truetype(font_path, size)


def render(background: Path, lines: list[str], out: Path, font_path: str,
           accent: str = "#F2B705", text_color: str = "#FFFFFF") -> dict:
    """Desenha a thumbnail e devolve o resultado da checagem de legibilidade."""
    img = Image.open(background).convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((left, top, left + W, top + H))

    # escurece a metade esquerda para o texto
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for x in range(W):
        sd.line([(x, 0), (x, H)], fill=int(170 * max(0.0, 1 - x / (W * 0.62))))
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, shade)

    draw = ImageDraw.Draw(img)
    lines = [ln.upper() for ln in lines if ln.strip()][:2]
    # frase longa ("ENGINEER LEVELS") fica pequena numa linha só: testa quebrar por palavra
    # e fica com o arranjo que permite a maior letra (no máximo 4 linhas)
    layouts = [lines]
    if lines and len(lines[0].split()) > 1:
        layouts.append(lines[0].split() + lines[1:])
    if len(lines) > 1 and len(lines[1].split()) > 1:
        layouts.append(lines[:1] + lines[1].split())
    best = None
    for lay in layouts:
        if len(lay) > 4:
            continue
        f = _fit_font(draw, lay, font_path, max_w=int(W * 0.54), max_h=int(H * 0.82))
        if not best or f.size > best[1].size:
            best = (lay, f)
    lines, font = best
    stroke = max(4, font.size // 14)
    y = (H - sum(draw.textbbox((0, 0), ln, font=font, stroke_width=stroke)[3] for ln in lines)) // 2
    colors = [_hex(text_color), _hex(accent)]
    boxes = []
    for i, ln in enumerate(lines):
        fill = colors[1] if len(lines) > 1 and i == len(lines) - 1 else colors[0]  # última linha em destaque
        draw.text((56, y), ln, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
        bbox = draw.textbbox((56, y), ln, font=font, stroke_width=stroke)
        boxes.append((bbox, fill))
        y = bbox[3] + 8

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=92)
    return legibility(img, boxes)


def legibility(img: Image.Image, boxes: list, factor: float = 0.2) -> dict:
    """Simula a thumbnail a 20%: a letra precisa ter altura mínima e contraste
    com o fundo ao redor."""
    small_h = []
    contrasts = []
    blurred = img.filter(ImageFilter.GaussianBlur(6))
    for (x0, y0, x1, y1), fill in boxes:
        small_h.append((y1 - y0) * factor)
        region = blurred.crop((max(0, x0 - 20), max(0, y0 - 20), min(img.width, x1 + 20), min(img.height, y1 + 20)))
        bg = tuple(ImageStat.Stat(region).mean)
        contrasts.append(round(contrast(fill, bg), 2))
    ok = bool(boxes) and min(small_h) >= 14 and min(contrasts) >= 3.0
    return {"passed": ok, "min_line_height_px_at_20pct": round(min(small_h or [0]), 1), "contrast": contrasts}


# ---------------------------------------------------------------------------
# Formato "antes e depois" (DIA 1 x DIA 30): tela dividida na diagonal por um raio,
# lado esquerdo claro e tranquilo, lado direito escuro e perigoso, números grandes no topo.
# ---------------------------------------------------------------------------
DISPLAY_FONT = str(Path(__file__).parent / "assets" / "fonts" / "LuckiestGuy-Regular.ttf")


def _cover(path: Path, w: int, h: int) -> Image.Image:
    img = Image.open(path).convert("RGB")
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s) + 1, round(img.height * s) + 1), Image.LANCZOS)
    l, t = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((l, t, l + w, t + h))


def _bolt(top_x: float, bottom_x: float, seed: int = 4) -> list[tuple[float, float]]:
    """Linha em zigue-zague de cima a baixo (o 'raio' que divide a tela)."""
    import random
    r = random.Random(seed)
    pts, n = [], 7
    for i in range(n + 1):
        y = H * i / n
        x = top_x + (bottom_x - top_x) * i / n
        if 0 < i < n:
            x += (28 if i % 2 else -28) + r.uniform(-8, 8)
        pts.append((x, y))
    return pts


def _label(draw: ImageDraw.ImageDraw, cx: float, y: int, word: str, number: str, size: int, num_color: str):
    font = ImageFont.truetype(DISPLAY_FONT, size)
    stroke = max(6, size // 9)
    gap = size // 5
    wb = draw.textbbox((0, 0), word, font=font, stroke_width=stroke)
    nb = draw.textbbox((0, 0), number, font=font, stroke_width=stroke)
    total = (wb[2] - wb[0]) + gap + (nb[2] - nb[0])
    x = cx - total / 2
    boxes = []
    for txt, fill, bb in ((word, "#FFFFFF", wb), (number, num_color, nb)):
        # sombra deslocada para dar volume
        draw.text((x + size * 0.05, y + size * 0.06), txt, font=font, fill=(0, 0, 0), stroke_width=stroke, stroke_fill=(0, 0, 0))
        draw.text((x, y), txt, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
        boxes.append((draw.textbbox((x, y), txt, font=font, stroke_width=stroke), _hex(fill)))
        x += (bb[2] - bb[0]) + gap
    return boxes


def render_split(left_bg: Path, right_bg: Path, left_label: str, right_label: str, out: Path,
                 left_color: str = "#FFD21F", right_color: str = "#FF2D2D", seed: int = 4) -> dict:
    """left_label/right_label no formato 'DIA 1' / 'DIA 30' (palavra + número)."""
    split_top, split_bottom = W * 0.56, W * 0.46
    left = _cover(left_bg, int(W * 0.62), H)
    right = _cover(right_bg, int(W * 0.62), H)
    canvas = Image.new("RGB", (W, H))
    canvas.paste(right, (W - right.width, 0))
    bolt = _bolt(split_top, split_bottom, seed)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), *bolt, (0, H)], fill=255)
    big_left = Image.new("RGB", (W, H))
    big_left.paste(left, (0, 0))
    canvas = Image.composite(big_left, canvas, mask)
    # leve vinheta no lado escuro e brilho no claro
    d = ImageDraw.Draw(canvas)
    d.line(bolt, fill=(0, 0, 0), width=22, joint="curve")
    d.line(bolt, fill=(255, 255, 255), width=12, joint="curve")

    def parts(lbl: str):
        bits = lbl.strip().upper().split()
        return (" ".join(bits[:-1]) or bits[0], bits[-1] if len(bits) > 1 else "")

    size = int(H * 0.18)
    lw, ln = parts(left_label)
    rw, rn = parts(right_label)
    boxes = _label(d, W * 0.25, int(H * 0.05), lw, ln, size, left_color)
    boxes += _label(d, W * 0.76, int(H * 0.05), rw, rn, size, right_color)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "JPEG", quality=92)
    return legibility(canvas, boxes)

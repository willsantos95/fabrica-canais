"""Vídeos do canal de notícias (Lance Rápido).

Cada cena é um quadrado de 1080 px (imagem de IA 1:1 ou cartão de dados desenhado aqui)
em movimento sobre o fundo desfocado da própria cena, com um painel por cima:
- vertical (Short 1080x1920): selo do esporte + manchete em cima, cena no meio,
  legenda palavra por palavra e fontes embaixo;
- horizontal (resumo 1920x1080): painel à esquerda com selo, manchete e contador,
  cena à direita.

As cores do esporte vêm da config do canal (format.sport_colors).
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .media import KB_ZOOM, _ts, _x264, _ass_escape, run
from .settings import settings

SQ = 1080  # lado da cena
SAFE = 840  # no Short a legenda ocupa a faixa de baixo da cena: cartões desenham acima disso
LAYOUTS = {
    # tamanho do quadro e posição da cena
    "vertical": {"w": 1080, "h": 1920, "x": 0, "y": 420},
    "horizontal": {"w": 1920, "h": 1080, "x": 840, "y": 0},
}
INTER = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
SPORT_LABEL = {"futebol": "FUTEBOL", "nba": "NBA", "nfl": "NFL"}
SPORT_COLOR = {"futebol": "#1DB954", "nba": "#F58426", "nfl": "#1E4FD8"}


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------
def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    for path in (INTER.format(weight), INTER.format("Bold"), settings.font_path):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def rgb(c: str) -> tuple[int, int, int]:
    c = (c or "#FFFFFF").lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in str(text or "").split():
        test = f"{cur} {word}".strip()
        if cur and draw.textlength(test, font=f) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def fit(draw: ImageDraw.ImageDraw, text: str, weight: str, max_w: int, max_lines: int,
        start: int, minimum: int = 28) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Maior fonte em que o texto cabe em `max_lines` linhas de `max_w` px."""
    size = start
    while size > minimum:
        f = font(weight, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) <= max_lines and all(draw.textlength(ln, font=f) <= max_w for ln in lines):
            return f, lines
        size -= 4
    f = font(weight, minimum)
    lines = wrap(draw, text, f, max_w)[:max_lines]
    return f, lines


def _lines(draw, xy, lines, f, fill, spacing=1.12, anchor="la", stroke=0) -> int:
    x, y = xy
    step = round(f.size * spacing)
    for ln in lines:
        draw.text((x, y), ln, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))
        y += step
    return y


def badge(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, color: str, size: int = 44) -> int:
    """Selo arredondado na cor do esporte. Devolve o x do fim do selo."""
    f = font("Black", size)
    w = round(draw.textlength(label, font=f))
    pad_x, h = round(size * 0.55), round(size * 1.6)
    draw.rounded_rectangle((x, y, x + w + 2 * pad_x, y + h), radius=h // 2, fill=rgb(color))
    draw.text((x + pad_x, y + h / 2), label, font=f, fill=(255, 255, 255), anchor="lm")
    return x + w + 2 * pad_x


# ---------------------------------------------------------------------------
# Cartões de dados (1080x1080)
# ---------------------------------------------------------------------------
def _card_base(color: str) -> Image.Image:
    c = rgb(color)
    img = Image.new("RGB", (SQ, SQ), (12, 14, 20))
    d = ImageDraw.Draw(img)
    # degradê diagonal escuro com um toque da cor do esporte
    for i in range(SQ):
        t = i / SQ
        d.line([(0, i), (SQ, i)], fill=tuple(round(12 + (v * 0.30 - 12) * t * 0.9) for v in c))
    # faixas diagonais sutis
    stripes = Image.new("L", (SQ, SQ), 0)
    sd = ImageDraw.Draw(stripes)
    for k in range(-SQ, SQ, 90):
        sd.polygon([(k, SQ), (k + 40, SQ), (k + 40 + SQ, 0), (k + SQ, 0)], fill=18)
    img = Image.composite(Image.new("RGB", (SQ, SQ), c), img, stripes)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, SQ, 14), fill=c)
    return img


def render_card(card: dict, color: str, out: Path, sport_label: str = "") -> Path:
    """Cartões: score (placar), stat (número em destaque), list (até 4 itens), fact (frase)."""
    img = _card_base(color)
    d = ImageDraw.Draw(img)
    c = rgb(color)
    white, grey = (255, 255, 255), (190, 196, 206)
    kind = card.get("kind") or "fact"
    M = 90  # margem
    title = str(card.get("title") or "").strip()
    y = 120
    if title:
        f, ls = fit(d, title.upper(), "ExtraBold", SQ - 2 * M, 2, 58)
        y = _lines(d, (M, y), ls, f, c) + 30

    if kind == "score":
        home, away = str(card.get("home") or ""), str(card.get("away") or "")
        hs, as_ = str(card.get("home_score") or ""), str(card.get("away_score") or "")
        cy = max(y + 110, 380)
        fs = font("Black", 230)
        d.text((SQ * 0.28, cy), hs, font=fs, fill=white, anchor="mm")
        d.text((SQ * 0.72, cy), as_, font=fs, fill=white, anchor="mm")
        d.text((SQ / 2, cy), "x", font=font("Bold", 90), fill=grey, anchor="mm")
        for cx, name in ((SQ * 0.28, home), (SQ * 0.72, away)):
            f, ls = fit(d, name.upper(), "ExtraBold", 420, 2, 64)
            _lines(d, (cx, cy + 170), ls, f, white, anchor="ma")
        note = str(card.get("note") or "")
        if note:
            f, ls = fit(d, note, "SemiBold", SQ - 2 * M, 2, 46)
            _lines(d, (SQ / 2, cy + 300), ls, f, grey, anchor="ma")
    elif kind == "stat":
        value = str(card.get("value") or "")
        f = font("Black", 360)
        while f.size > 120 and d.textlength(value, font=f) > SQ - 2 * M:
            f = font("Black", f.size - 20)
        cy = max(y + f.size // 2 + 20, 400)
        d.text((SQ / 2, cy), value, font=f, fill=c, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
        label = str(card.get("label") or "")
        yy = cy + f.size // 2 + 40
        if label:
            fl, ls = fit(d, label.upper(), "ExtraBold", SQ - 2 * M, 2, 76)
            yy = _lines(d, (SQ / 2, yy), ls, fl, white, anchor="ma") + 20
        note = str(card.get("note") or "")
        if note:
            fn, ls = fit(d, note, "Medium", SQ - 2 * M, 2, 46)
            _lines(d, (SQ / 2, yy), ls, fn, grey, anchor="ma")
    elif kind == "list":
        items = [str(x) for x in (card.get("items") or []) if str(x).strip()][:4]
        avail = SAFE - y
        per = avail // max(1, len(items))
        for i, it in enumerate(items):
            top = y + i * per
            d.rounded_rectangle((M, top + 8, M + 70, top + 78), radius=16, fill=c)
            d.text((M + 35, top + 43), str(i + 1), font=font("Black", 46), fill=white, anchor="mm")
            f, ls = fit(d, it, "Bold", SQ - 2 * M - 100, max(1, min(3, per // 62)), 54, 32)
            _lines(d, (M + 100, top + 12), ls, f, white)
    else:  # fact / quote
        text = str(card.get("text") or card.get("value") or "")
        quote = kind == "quote"
        if quote:
            d.text((M - 10, y - 10), "“", font=font("Black", 220), fill=c)
            y += 120
        f, ls = fit(d, text, "ExtraBold", SQ - 2 * M, 5, 80, 40)
        block = len(ls) * round(f.size * 1.12)
        top = max(y, (SAFE - block) // 2 + (40 if not title else 0))
        _lines(d, (M, top), ls, f, white)
        who = str(card.get("source") or card.get("note") or "")
        if who:
            fw = font("SemiBold", 42)
            d.text((M, SAFE + 10), ("— " if quote else "") + who, font=fw, fill=grey)

    if sport_label:
        d.text((SQ - M, 70), sport_label, font=font("Black", 34), fill=c, anchor="rm")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out


def title_card(headline: str, color: str, out: Path, sport_label: str) -> Path:
    """Cartão usado quando a imagem de IA falha (cota do provedor etc.)."""
    return render_card({"kind": "fact", "title": sport_label, "text": headline}, color, out, "")


# ---------------------------------------------------------------------------
# Painéis (PNG transparente por cima da cena)
# ---------------------------------------------------------------------------
def _gradient(img: Image.Image, top: int, bottom: int, alpha_top: int, alpha_bottom: int, axis: str = "y"):
    d = ImageDraw.Draw(img)
    span = max(1, bottom - top)
    for i in range(top, bottom):
        a = round(alpha_top + (alpha_bottom - alpha_top) * (i - top) / span)
        if axis == "y":
            d.line([(0, i), (img.width, i)], fill=(0, 0, 0, a))
        else:
            d.line([(i, 0), (i, img.height)], fill=(0, 0, 0, a))


def vertical_panel(headline: str, sport: str, color: str, channel: str, sources: str, out: Path) -> Path:
    L = LAYOUTS["vertical"]
    img = Image.new("RGBA", (L["w"], L["h"]), (0, 0, 0, 0))
    _gradient(img, 0, L["y"] + 60, 235, 120)
    _gradient(img, L["y"] + SQ - 260, L["y"] + SQ, 0, 150)       # base da cena: legenda legível
    _gradient(img, L["y"] + SQ, L["h"], 170, 220)
    d = ImageDraw.Draw(img)
    x_end = badge(d, 60, 120, SPORT_LABEL.get(sport, sport.upper()), color)
    if channel:
        d.text((x_end + 24, 120 + 35), channel.upper(), font=font("ExtraBold", 34), fill=(225, 228, 235), anchor="lm")
    f, ls = fit(d, headline, "ExtraBold", L["w"] - 120, 3, 70, 44)
    _lines(d, (60, 228), ls, f, (255, 255, 255), spacing=1.1, stroke=2)
    d.rectangle((0, L["y"] + SQ, L["w"], L["y"] + SQ + 10), fill=rgb(color) + (255,))
    if sources:
        fs, ls = fit(d, sources, "SemiBold", L["w"] - 120, 2, 34, 26)
        _lines(d, (60, L["y"] + SQ + 40), ls, fs, (200, 205, 215))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out


def horizontal_panel(headline: str, sport: str, color: str, channel: str, counter: str, out: Path,
                     kicker: str = "") -> Path:
    L = LAYOUTS["horizontal"]
    img = Image.new("RGBA", (L["w"], L["h"]), (0, 0, 0, 0))
    _gradient(img, 0, L["x"] + 160, 230, 0, axis="x")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 12, L["h"]), fill=rgb(color) + (255,))
    x_end = badge(d, 70, 90, SPORT_LABEL.get(sport, sport.upper()), color, 40)
    if counter:
        d.text((x_end + 22, 90 + 32), counter, font=font("ExtraBold", 34), fill=(225, 228, 235), anchor="lm")
    y = 230
    if kicker:
        fk, ls = fit(d, kicker.upper(), "Bold", L["x"] - 140, 1, 34, 24)
        y = _lines(d, (70, y), ls, fk, rgb(color)) + 10
    f, ls = fit(d, headline, "ExtraBold", L["x"] - 140, 5, 76, 40)
    _lines(d, (70, y), ls, f, (255, 255, 255), spacing=1.1, stroke=2)
    if channel:
        d.text((70, L["h"] - 80), channel.upper(), font=font("Black", 36), fill=(225, 228, 235), anchor="ls")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out


# ---------------------------------------------------------------------------
# Vídeo
# ---------------------------------------------------------------------------
def square(src: Path, out: Path) -> Path:
    """Corta o centro em quadrado e salva em 1080 px (imagens 16:9 ou 9:16 também servem)."""
    img = Image.open(src).convert("RGB")
    s = min(img.width, img.height)
    img = img.crop(((img.width - s) // 2, (img.height - s) // 2, (img.width + s) // 2, (img.height + s) // 2))
    img = img.resize((SQ, SQ), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=92)
    return out


def scene_clip(image: Path, panel: Path, out: Path, seconds: float, layout: str = "vertical",
               mode: str = "push_in", zoom: float = KB_ZOOM) -> Path:
    """Cena quadrada em movimento sobre o fundo desfocado, com o painel por cima."""
    L, fps = LAYOUTS[layout], settings.fps
    n = max(1, round(seconds * fps))
    z_max = 1 + zoom
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    motions = {
        "push_in": (f"1+{zoom}*on/{n}", cx, cy),
        "pull_out": (f"{z_max}-{zoom}*on/{n}", cx, cy),
        "pan_left": (f"{z_max}", f"(iw-iw/zoom)*(1-on/{n})", cy),
        "pan_right": (f"{z_max}", f"(iw-iw/zoom)*on/{n}", cy),
        "pan_up": (f"{z_max}", cx, f"(ih-ih/zoom)*(1-on/{n})"),
        "pan_down": (f"{z_max}", cx, f"(ih-ih/zoom)*on/{n}"),
    }
    z, x, y = motions.get(mode, motions["push_in"])
    s = SQ * 2
    fc = (
        "[0:v]split=2[a][b];"
        f"[a]scale={s}:{s}:force_original_aspect_ratio=increase,crop={s}:{s},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={SQ}x{SQ}:fps={fps}[fg];"
        f"[b]scale={L['w']}:{L['h']}:force_original_aspect_ratio=increase,crop={L['w']}:{L['h']},"
        f"boxblur=30:3,eq=brightness=-0.22,loop=loop={n}:size=1:start=0,fps={fps}[bg];"
        f"[bg][fg]overlay={L['x']}:{L['y']}:shortest=1[c];"
        f"[c][1:v]overlay=0:0:shortest=1,trim=end_frame={n}[v]"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(image), "-loop", "1", "-i", str(panel),
         "-filter_complex", fc, "-map", "[v]", "-frames:v", str(n), *_x264(), "-an", str(out)])
    return out


def add_end_card(ass: Path, total: float, lines: list[str], seconds: float = 2.3,
                 font_name: str = "DejaVu Sans") -> Path:
    """Acrescenta o cartão final (texto no centro) a uma legenda .ass existente."""
    if not lines:
        return ass
    text = ass.read_text("utf-8")
    head, events = text.split("[Events]", 1)
    head = head.rstrip("\n") + (
        f"\nStyle: E,{font_name},78,&H00FFFFFF,&H00FFFFFF,&H00000000,&HC8000000,-1,0,0,0,100,100,0,0,3,18,0,5,80,80,0,1\n\n")
    s, e = _ts(max(0.0, total - seconds), ".")[1:-1], _ts(total, ".")[1:-1]
    ev = f"Dialogue: 2,{s},{e},E,,0,0,0,," + "\\N".join(_ass_escape(x) for x in lines)
    ass.write_text(head + "[Events]" + events.rstrip("\n") + "\n" + ev + "\n", encoding="utf-8")
    return ass


def burn(video: Path, ass: Path, out: Path) -> Path:
    ass_path = str(ass).replace(":", r"\:")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", f"ass='{ass_path}'", *_x264(), "-an", str(out)])
    return out


def cover(image: Path, panel: Path, out: Path, layout: str = "vertical") -> Path:
    """Quadro estático (prévia no WhatsApp / capa do resumo)."""
    L = LAYOUTS[layout]
    sc = Image.open(image).convert("RGB")
    bg = sc.resize((max(L["w"], L["h"]), max(L["w"], L["h"])), Image.LANCZOS)
    bg = bg.crop(((bg.width - L["w"]) // 2, (bg.height - L["h"]) // 2,
                  (bg.width - L["w"]) // 2 + L["w"], (bg.height - L["h"]) // 2 + L["h"]))
    bg = bg.filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.78))
    bg.paste(sc.resize((SQ, SQ)), (L["x"], L["y"]))
    bg = Image.alpha_composite(bg.convert("RGBA"), Image.open(panel).convert("RGBA")).convert("RGB")
    out.parent.mkdir(parents=True, exist_ok=True)
    bg.save(out, "JPEG", quality=88)
    return out


def clean_tts(text: str) -> str:
    """Placar "112-108" vira "112 a 108" na narração."""
    return re.sub(r"(\d+)\s*[-x×]\s*(\d+)", r"\1 a \2", str(text or "")).strip()

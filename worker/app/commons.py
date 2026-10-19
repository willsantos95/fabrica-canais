"""Fotos de licença livre do Wikimedia Commons para as notícias (jogador, time, estádio, técnico).

Caminho: artigo da Wikipédia (pt, depois en) → imagem principal do artigo → confere no Commons
se a licença é livre (CC BY, CC BY-SA, CC0, domínio público). Imagem que não está no Commons
(uso justo, ex.: escudos na Wikipédia em inglês) é recusada. Logos, escudos e emblemas também,
mesmo quando livres, porque são marca registrada.

O crédito aparece no rodapé do vídeo (junto das fontes) e na descrição do YouTube.
"""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path

import httpx
from PIL import Image

log = logging.getLogger("fabrica.commons")

UA = {"User-Agent": "FabricaCanais/1.0 (https://relampagodeofertas.shop; noticias esportivas)"}
WIKI_API = "https://{lang}.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
FREE = re.compile(r"^(cc[- ]by(-sa)?([- ]\d(\.\d)?)?|cc0|public domain|pd|domínio público)", re.I)
BLOCK = re.compile(r"logo|crest|badge|escudo|emblem|wordmark|kit[_ ]|uniform|shirt|jersey|map|mapa|diagram", re.I)
SQ = 1080


class PhotoError(RuntimeError):
    pass


def _get(url: str, params: dict) -> dict:
    r = httpx.get(url, params={**params, "format": "json", "formatversion": 2}, headers=UA, timeout=20,
                  follow_redirects=True)
    r.raise_for_status()
    return r.json()


def _page_image(subject: str, lang: str) -> str | None:
    """Nome do arquivo da imagem principal do artigo (ex.: 'Jalen Hurts 2023.jpg')."""
    data = _get(WIKI_API.format(lang=lang), {"action": "query", "titles": subject, "redirects": 1,
                                              "prop": "pageimages", "piprop": "name"})
    for p in (data.get("query") or {}).get("pages") or []:
        if p.get("pageimage"):
            return p["pageimage"]
    # título não bateu: busca o artigo mais provável
    data = _get(WIKI_API.format(lang=lang), {"action": "query", "generator": "search", "gsrsearch": subject,
                                              "gsrlimit": 1, "prop": "pageimages", "piprop": "name"})
    for p in (data.get("query") or {}).get("pages") or []:
        if p.get("pageimage"):
            return p["pageimage"]
    return None


def _commons_info(filename: str) -> dict | None:
    data = _get(COMMONS_API, {"action": "query", "titles": f"File:{filename}", "prop": "imageinfo",
                              "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1400})
    pages = (data.get("query") or {}).get("pages") or []
    if not pages or pages[0].get("missing") or not pages[0].get("imageinfo"):
        return None  # não está no Commons: provavelmente uso justo na Wikipédia, não serve
    return pages[0]["imageinfo"][0]


def _clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def find(subject: str, langs: tuple[str, ...] = ("pt", "en")) -> dict:
    """Devolve {url, author, license, page, file} de uma foto livre do assunto, ou levanta PhotoError."""
    subject = (subject or "").strip()
    if not subject:
        raise PhotoError("sem assunto para a foto")
    reasons = []
    for lang in langs:
        try:
            name = _page_image(subject, lang)
        except Exception as exc:
            reasons.append(f"{lang}: {exc}")
            continue
        if not name:
            reasons.append(f"{lang}: artigo sem imagem")
            continue
        if BLOCK.search(name) or not name.lower().endswith((".jpg", ".jpeg")):
            reasons.append(f"{lang}: {name} não é foto (logo, uniforme, desenho)")
            continue
        info = _commons_info(name)
        if not info:
            reasons.append(f"{lang}: {name} não está no Commons (sem licença livre)")
            continue
        meta = info.get("extmetadata") or {}
        lic = _clean((meta.get("LicenseShortName") or {}).get("value", ""))
        if not FREE.match(lic):
            reasons.append(f"{lang}: licença {lic or 'desconhecida'}")
            continue
        if (info.get("width") or 0) < 500 or (info.get("height") or 0) < 500:
            reasons.append(f"{lang}: foto pequena")
            continue
        author = _clean((meta.get("Artist") or {}).get("value", "")) or "autor desconhecido"
        return {"url": info.get("thumburl") or info["url"], "author": author[:80], "license": lic,
                "page": info.get("descriptionurl"), "file": name, "subject": subject}
    raise PhotoError("; ".join(reasons) or "nada encontrado")


def fetch(subject: str, out: Path) -> dict:
    """Baixa a foto e corta em quadrado (puxando para cima, onde costuma estar o rosto)."""
    meta = find(subject)
    r = httpx.get(meta["url"], headers=UA, timeout=60, follow_redirects=True)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    s = min(img.width, img.height)
    x = (img.width - s) // 2
    y = int((img.height - s) * 0.2)  # retrato: corta mais embaixo que em cima
    img = img.crop((x, y, x + s, y + s)).resize((SQ, SQ), Image.LANCZOS)

    credit = f"Foto: {meta['author']} ({meta['license']}, Wikimedia Commons)"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=92)
    log.info("foto livre: %s → %s (%s)", subject, meta["file"], meta["license"])
    return {**meta, "credit": credit}

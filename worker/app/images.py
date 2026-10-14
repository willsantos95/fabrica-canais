"""Geração das imagens dos planos com o Gemini (Nano Banana).

Fica no worker (e não no n8n) para que ~50 imagens em base64 não passem pelo
histórico de execuções do n8n. A chave vem de GEMINI_API_KEY no .env do worker.
"""
from __future__ import annotations

import base64
import io
import os
import time
from pathlib import Path

import httpx
from PIL import Image

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class ImageError(RuntimeError):
    pass


def _models(preferred: str | None) -> list[str]:
    first = preferred or os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
    fallback = os.environ.get("GEMINI_IMAGE_FALLBACK", "gemini-2.5-flash-image")
    return [first] + ([fallback] if fallback and fallback != first else [])


def _extract(data: dict) -> bytes | None:
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    return None


def generate(prompt: str, model: str | None = None, aspect: str = "16:9", attempts: int = 2) -> tuple[bytes, str]:
    """Devolve (bytes da imagem, modelo usado). Tenta o modelo principal e depois o reserva."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ImageError("GEMINI_API_KEY não configurada no worker")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}},
    }
    last = "sem resposta"
    for m in _models(model):
        for attempt in range(attempts):
            try:
                r = httpx.post(API.format(model=m), json=body, headers={"x-goog-api-key": key}, timeout=180)
                if r.status_code == 429 or r.status_code >= 500:
                    last = f"{m}: HTTP {r.status_code}"
                    time.sleep(5 * (attempt + 1))
                    continue
                if r.status_code >= 400:
                    last = f"{m}: HTTP {r.status_code} {r.text[:300]}"
                    break  # erro de requisição: tenta o próximo modelo
                img = _extract(r.json())
                if img:
                    return img, m
                reason = (r.json().get("candidates") or [{}])[0].get("finishReason") or r.json().get("promptFeedback")
                last = f"{m}: sem imagem ({reason})"
            except httpx.HTTPError as exc:
                last = f"{m}: {exc}"
                time.sleep(3 * (attempt + 1))
    raise ImageError(last)


def to_jpeg(raw: bytes, out: Path, width: int = 1920) -> Path:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=90)
    return out


def ahash(path: Path) -> int:
    """Hash perceptual simples (8x8) para achar imagens repetidas."""
    img = Image.open(path).convert("L").resize((8, 8), Image.BILINEAR)
    px = list(img.getdata())
    avg = sum(px) / len(px)
    return sum(1 << i for i, p in enumerate(px) if p > avg)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")

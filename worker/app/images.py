"""Geração das imagens dos planos.

Provedores, na ordem de IMAGE_PROVIDERS (padrão: "cloudflare,gemini"):
- cloudflare: Workers AI, FLUX.1 schnell. O plano grátis dá 10.000 neurons por dia
  (~170 imagens). Precisa de CF_ACCOUNT_ID e CF_API_TOKEN.
- gemini: Nano Banana pela API do Google AI Studio. Precisa de GEMINI_API_KEY e de
  faturamento ativo (no plano grátis a cota de imagens é zero).

Provedor sem credencial é pulado. Fica no worker (e não no n8n) para que ~50 imagens
em base64 não passem pelo histórico de execuções do n8n.
"""
from __future__ import annotations

import base64
import io
import os
import random
import time
from pathlib import Path

import httpx
from PIL import Image

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
CF_API = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"

# O FLUX do Workers AI devolve imagem quadrada; o vídeo corta o meio em 16:9.
CF_FRAMING = ("Wide cinematic landscape composition. Keep the main subject and all important "
              "elements inside the middle horizontal band of the frame, with empty background "
              "above and below.")


class ImageError(RuntimeError):
    pass


class QuotaError(ImageError):
    """Cota do provedor acabou: não adianta tentar de novo agora."""


# ---------- Cloudflare Workers AI ----------

def _cloudflare(prompt: str, aspect: str) -> tuple[bytes, str]:
    account, token = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not (account and token):
        raise ImageError("cloudflare: CF_ACCOUNT_ID/CF_API_TOKEN não configurados")
    model = os.environ.get("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    steps = int(os.environ.get("CF_STEPS", "4"))
    text = prompt if aspect == "1:1" else f"{prompt}\n{CF_FRAMING}"
    body = {"prompt": text[:2048], "steps": max(1, min(steps, 8)), "seed": random.randint(1, 2**31 - 1)}
    last = "sem resposta"
    for attempt in range(3):
        try:
            r = httpx.post(CF_API.format(account=account, model=model), json=body,
                           headers={"Authorization": f"Bearer {token}"}, timeout=120)
        except httpx.HTTPError as exc:
            last = f"cloudflare: {exc}"
            time.sleep(3 * (attempt + 1))
            continue
        low = r.text.lower()
        if r.status_code >= 400 and any(k in low for k in ("neurons", "daily", "allocation", "3036")):
            raise QuotaError("cloudflare: cota grátis diária de neurons esgotada (renova à 0h UTC, 21h em Brasília)")
        if r.status_code == 429:
            last = f"cloudflare: HTTP 429 {r.text[:200]}"
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code >= 500:
            last = f"cloudflare: HTTP {r.status_code} {r.text[:200]}"
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code >= 400:
            raise ImageError(f"cloudflare: HTTP {r.status_code} {r.text[:300]}")
        if r.headers.get("content-type", "").startswith("image/"):
            return r.content, f"cloudflare:{model.rsplit('/', 1)[-1]}"
        data = r.json()
        img = (data.get("result") or {}).get("image") or data.get("image")
        if img:
            return base64.b64decode(img), f"cloudflare:{model.rsplit('/', 1)[-1]}"
        last = f"cloudflare: sem imagem na resposta ({str(data)[:200]})"
    raise ImageError(last)


# ---------- Gemini ----------

def _gemini_models(preferred: str | None) -> list[str]:
    first = preferred or os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
    fallback = os.environ.get("GEMINI_IMAGE_FALLBACK", "gemini-2.5-flash-image")
    return [first] + ([fallback] if fallback and fallback != first else [])


def _gemini_extract(data: dict) -> bytes | None:
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    return None


def _gemini(prompt: str, model: str | None, aspect: str, attempts: int = 2) -> tuple[bytes, str]:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ImageError("gemini: GEMINI_API_KEY não configurada")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}},
    }
    last = "sem resposta"
    for m in _gemini_models(model):
        for attempt in range(attempts):
            try:
                r = httpx.post(GEMINI_API.format(model=m), json=body, headers={"x-goog-api-key": key}, timeout=180)
                if r.status_code == 429 and "limit: 0" in r.text:
                    raise QuotaError("gemini: sem cota para imagens (plano gratuito, limit: 0). "
                                     "Ative o faturamento do projeto no Google AI Studio.")
                if r.status_code == 429 or r.status_code >= 500:
                    last = f"gemini {m}: HTTP {r.status_code} {r.text[:200]}"
                    time.sleep(5 * (attempt + 1))
                    continue
                if r.status_code >= 400:
                    last = f"gemini {m}: HTTP {r.status_code} {r.text[:300]}"
                    break  # erro de requisição: tenta o próximo modelo
                img = _gemini_extract(r.json())
                if img:
                    return img, m
                reason = (r.json().get("candidates") or [{}])[0].get("finishReason") or r.json().get("promptFeedback")
                last = f"gemini {m}: sem imagem ({reason})"
            except httpx.HTTPError as exc:
                last = f"gemini {m}: {exc}"
                time.sleep(3 * (attempt + 1))
    raise ImageError(last)


# ---------- entrada única ----------

def providers() -> list[str]:
    raw = os.environ.get("IMAGE_PROVIDERS", "cloudflare,gemini")
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


def generate(prompt: str, model: str | None = None, aspect: str = "16:9") -> tuple[bytes, str]:
    """Devolve (bytes da imagem, provedor/modelo usado), tentando os provedores em ordem."""
    errors = []
    for p in providers():
        try:
            if p == "cloudflare":
                return _cloudflare(prompt, aspect)
            if p == "gemini":
                return _gemini(prompt, model, aspect)
            errors.append(f"{p}: provedor desconhecido")
        except ImageError as exc:
            errors.append(str(exc))
    raise ImageError(" | ".join(errors) or "nenhum provedor de imagem configurado (IMAGE_PROVIDERS)")


def to_jpeg(raw: bytes, out: Path, width: int = 1920, aspect: float | None = 16 / 9) -> Path:
    """Salva em JPEG, cortando o centro na proporção do vídeo (imagens quadradas do FLUX)."""
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if aspect and abs(img.width / img.height - aspect) > 0.02:
        if img.width / img.height > aspect:  # larga demais: corta as laterais
            w = round(img.height * aspect)
            x = (img.width - w) // 2
            img = img.crop((x, 0, x + w, img.height))
        else:  # alta demais: corta em cima e embaixo
            h = round(img.width / aspect)
            y = (img.height - h) // 2
            img = img.crop((0, y, img.width, y + h))
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

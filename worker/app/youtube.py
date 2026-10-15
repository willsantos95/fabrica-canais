"""Envio de arquivos ao YouTube por sessão resumable.

O n8n abre a sessão (POST .../upload/youtube/v3/...?uploadType=resumable com a
credencial OAuth dele) e passa só a URL da sessão. A URL já autoriza o envio, então
o worker nunca recebe token do Google e o vídeo não passa pela memória do n8n.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import httpx

log = logging.getLogger("fabrica.youtube")
CHUNK = 8 * 1024 * 1024


class UploadError(RuntimeError):
    pass


def _stream(path: Path, offset: int):
    with open(path, "rb") as fh:
        fh.seek(offset)
        while True:
            data = fh.read(CHUNK)
            if not data:
                break
            yield data


def _status(url: str, size: int) -> tuple[int, int, dict | None]:
    """Pergunta ao Google quanto já chegou. Devolve (código, próximo byte, resposta final)."""
    r = httpx.put(url, headers={"Content-Range": f"bytes */{size}", "Content-Length": "0"}, timeout=60)
    if r.status_code in (200, 201):
        return r.status_code, size, r.json()
    if r.status_code == 308:
        rng = r.headers.get("Range")  # ex.: bytes=0-1048575
        return 308, int(rng.split("-")[1]) + 1 if rng else 0, None
    return r.status_code, 0, None


def upload(url: str, path: Path, content_type: str, attempts: int = 6) -> dict:
    """Envia o arquivo inteiro para a sessão, retomando de onde parou se a conexão cair."""
    size = path.stat().st_size
    offset = 0
    last = ""
    for attempt in range(attempts):
        headers = {"Content-Type": content_type, "Content-Length": str(size - offset)}
        if offset:
            headers["Content-Range"] = f"bytes {offset}-{size - 1}/{size}"
        try:
            r = httpx.put(url, content=_stream(path, offset), headers=headers,
                          timeout=httpx.Timeout(60, write=None, read=600))
            if r.status_code in (200, 201):
                return r.json() if r.content else {}
            if r.status_code in (400, 401, 403, 404, 410):
                # 404/410: a sessão expirou ou foi aberta com outros dados — o n8n precisa abrir outra
                raise UploadError(f"YouTube recusou o envio: HTTP {r.status_code} {r.text[:400]}")
            last = f"HTTP {r.status_code} {r.text[:200]}"
        except httpx.HTTPError as exc:
            last = str(exc)
        log.warning("upload interrompido (%s), tentativa %d; consultando o progresso", last, attempt + 1)
        time.sleep(min(60, 2 ** attempt))
        try:
            code, offset, done = _status(url, size)
            if done is not None:
                return done
            if code not in (308,):
                raise UploadError(f"sessão de upload inválida: HTTP {code} ({last})")
        except httpx.HTTPError as exc:
            last = str(exc)
    raise UploadError(f"upload não terminou depois de {attempts} tentativas: {last}")


def guess_type(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    return {".mp4": "video/mp4", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(
        ext, "application/octet-stream")

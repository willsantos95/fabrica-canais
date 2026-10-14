"""API HTTP do worker. O n8n cria jobs aqui e recebe o resultado pelo callback."""
from __future__ import annotations

import base64
import binascii
import json
import secrets
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from . import pages, storage
from .settings import settings

app = FastAPI(title="Fábrica de Canais · Worker de render", version="0.1.0")

JobType = Literal["voice", "images", "tts", "align", "kenburns", "assemble", "shorts", "thumbnail", "checks"]


def _redis() -> Redis:
    return Redis.from_url(settings.redis_url)


def _queue() -> Queue:
    return Queue(settings.queue_name, connection=_redis(), default_timeout=settings.job_timeout_s)


def auth(authorization: str = Header(default="")) -> None:
    if not settings.api_token:
        raise HTTPException(500, "WORKER_API_TOKEN não configurado")
    expected = f"Bearer {settings.api_token}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(401, "token inválido")


class JobIn(BaseModel):
    video_id: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    callback_url: str | None = None
    idempotency_key: str | None = None


def _status(job: Job) -> dict:
    status = job.get_status(refresh=True)
    body: dict[str, Any] = {"job_id": job.id, "status": str(status.value if hasattr(status, "value") else status)}
    if job.is_finished:
        body["result"] = (job.return_value() or {}).get("result")
    if job.is_failed:
        body["error"] = (job.latest_result().exc_string or "")[-2000:] if job.latest_result() else "falhou"
    return body


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home_page() -> str:
    return pages.home()


@app.get("/privacidade", response_class=HTMLResponse, include_in_schema=False)
def privacy_page() -> str:
    return pages.privacy()


@app.get("/termos", response_class=HTMLResponse, include_in_schema=False)
def terms_page() -> str:
    return pages.terms()


@app.get("/health")
def health() -> dict:
    try:
        redis_ok = bool(_redis().ping())
    except Exception:
        redis_ok = False
    storage_ok = storage.ping()
    ok = redis_ok and storage_ok
    body = {"ok": ok, "redis": redis_ok, "storage": storage_ok, "queue": settings.queue_name}
    if ok:
        body["queued"] = len(_queue())
    return body


@app.post("/jobs/{job_type}", dependencies=[Depends(auth)], status_code=202)
def create_job(job_type: JobType, body: JobIn) -> dict:
    q = _queue()
    job_id = body.idempotency_key
    if job_id:
        try:
            existing = Job.fetch(job_id, connection=q.connection)
            if not existing.is_failed:
                return {**_status(existing), "deduplicated": True}
            existing.delete()
        except NoSuchJobError:
            pass
    payload = {"type": job_type, **body.model_dump()}
    job = q.enqueue("app.tasks.execute", payload, job_id=job_id, result_ttl=7 * 86400, failure_ttl=7 * 86400)
    return {"job_id": job.id, "status": "queued", "deduplicated": False}


@app.get("/jobs/{job_id}", dependencies=[Depends(auth)])
def get_job(job_id: str) -> dict:
    try:
        return _status(Job.fetch(job_id, connection=_redis()))
    except NoSuchJobError:
        raise HTTPException(404, "job não encontrado")


class PresignIn(BaseModel):
    url: str | None = None
    urls: list[str | None] | None = None
    expires_s: int = 172800


@app.post("/files/presign", dependencies=[Depends(auth)])
def presign(body: PresignIn) -> dict:
    """Links temporários (preview no WhatsApp). Aceita `url` ou uma lista `urls`."""
    if body.urls is not None:
        return {"urls": [storage.presign(u, body.expires_s) if u else None for u in body.urls]}
    if not body.url:
        raise HTTPException(400, "envie url ou urls")
    return {"url": storage.presign(body.url, body.expires_s)}


class PutIn(BaseModel):
    key: str = Field(pattern=r"^[A-Za-z0-9._\-/]+$")
    json_body: Any | None = Field(default=None, alias="json")
    base64: str | None = None
    content_type: str | None = None


@app.post("/files/put", dependencies=[Depends(auth)])
def put_file(body: PutIn) -> dict:
    """Grava um JSON ou um arquivo em base64 no armazenamento (usado pelo n8n
    para o video_spec e para as imagens geradas)."""
    if ".." in body.key or body.key.startswith("/"):
        raise HTTPException(400, "chave inválida")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "f"
        if body.json_body is not None:
            path.write_text(json.dumps(body.json_body, ensure_ascii=False), "utf-8")
            ctype = "application/json"
        elif body.base64:
            try:
                path.write_bytes(base64.b64decode(body.base64, validate=True))
            except binascii.Error:
                raise HTTPException(400, "base64 inválido")
            ctype = body.content_type or "application/octet-stream"
        else:
            raise HTTPException(400, "envie json ou base64")
        url = storage.upload(path, body.key, ctype)
        return {"url": url, "bytes": path.stat().st_size}


class GetIn(BaseModel):
    url: str


@app.post("/files/get-json", dependencies=[Depends(auth)])
def get_json(body: GetIn) -> Any:
    """Lê um JSON do armazenamento (ex.: o video_spec atual)."""
    with tempfile.TemporaryDirectory() as tmp:
        try:
            path = storage.download(body.url, Path(tmp) / "f.json")
        except Exception as exc:
            raise HTTPException(404, f"não encontrado: {exc}")
        return json.loads(path.read_text("utf-8"))

"""API HTTP do worker. O n8n cria jobs aqui e recebe o resultado pelo callback."""
from __future__ import annotations

import secrets
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from . import storage
from .settings import settings

app = FastAPI(title="Fábrica de Canais · Worker de render", version="0.1.0")

JobType = Literal["tts", "align", "kenburns", "assemble", "shorts", "thumbnail", "checks"]


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
    url: str
    expires_s: int = 172800


@app.post("/files/presign", dependencies=[Depends(auth)])
def presign(body: PresignIn) -> dict:
    """Link temporário para o preview no WhatsApp."""
    return {"url": storage.presign(body.url, body.expires_s)}

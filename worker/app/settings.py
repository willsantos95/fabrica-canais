"""Configuração do worker, lida das variáveis de ambiente."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    api_token: str = field(default_factory=lambda: _env("WORKER_API_TOKEN", "") or "")
    callback_token: str = field(default_factory=lambda: _env("CALLBACK_TOKEN", "") or "")
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0") or "")
    queue_name: str = field(default_factory=lambda: _env("QUEUE_NAME", "render") or "render")
    job_timeout_s: int = field(default_factory=lambda: int(_env("JOB_TIMEOUT_S", "7200") or 7200))

    # Armazenamento: "s3" (MinIO/S3) ou "local" (testes)
    storage: str = field(default_factory=lambda: _env("STORAGE", "s3") or "s3")
    s3_endpoint: str | None = field(default_factory=lambda: _env("S3_ENDPOINT"))
    s3_public_endpoint: str | None = field(default_factory=lambda: _env("S3_PUBLIC_ENDPOINT"))
    s3_bucket: str = field(default_factory=lambda: _env("S3_BUCKET", "fabrica") or "fabrica")
    s3_access_key: str | None = field(default_factory=lambda: _env("S3_ACCESS_KEY"))
    s3_secret_key: str | None = field(default_factory=lambda: _env("S3_SECRET_KEY"))
    s3_region: str = field(default_factory=lambda: _env("S3_REGION", "us-east-1") or "us-east-1")
    local_root: Path = field(default_factory=lambda: Path(_env("LOCAL_STORAGE_ROOT", "/data/storage") or "/data/storage"))

    work_dir: Path = field(default_factory=lambda: Path(_env("WORK_DIR", "/data/work") or "/data/work"))

    # Vídeo
    width: int = field(default_factory=lambda: int(_env("VIDEO_WIDTH", "1920") or 1920))
    height: int = field(default_factory=lambda: int(_env("VIDEO_HEIGHT", "1080") or 1080))
    fps: int = field(default_factory=lambda: int(_env("VIDEO_FPS", "30") or 30))
    x264_preset: str = field(default_factory=lambda: _env("X264_PRESET", "veryfast") or "veryfast")
    font_path: str = field(default_factory=lambda: _env("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") or "")

    # Whisper
    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL", "small") or "small")


settings = Settings()

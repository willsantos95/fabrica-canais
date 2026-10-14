"""Leitura e escrita de arquivos no MinIO/S3 (ou em disco, nos testes).

Endereços seguem o formato s3://<bucket>/<chave>. URLs http(s) também são
aceitas como entrada (ex.: imagem devolvida direto por um provedor de IA).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .settings import settings


def _s3(endpoint: str | None = None):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=endpoint or settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def parse(url: str) -> tuple[str, str]:
    """Separa s3://bucket/chave em (bucket, chave)."""
    p = urlparse(url)
    if p.scheme != "s3":
        raise ValueError(f"endereço não é s3://: {url}")
    return p.netloc, p.path.lstrip("/")


def url_for(key: str) -> str:
    return f"s3://{settings.s3_bucket}/{key.lstrip('/')}"


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    scheme = urlparse(url).scheme
    if scheme in ("http", "https"):
        with httpx.stream("GET", url, timeout=300, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)
        return dest
    bucket, key = parse(url)
    if settings.storage == "local":
        shutil.copyfile(settings.local_root / bucket / key, dest)
    else:
        _s3().download_file(bucket, key, str(dest))
    return dest


def upload(src: Path, key: str, content_type: str | None = None) -> str:
    url = url_for(key)
    bucket, key = parse(url)
    if settings.storage == "local":
        target = settings.local_root / bucket / key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
    else:
        extra = {"ContentType": content_type} if content_type else None
        _s3().upload_file(str(src), bucket, key, ExtraArgs=extra)
    return url


def presign(url: str, expires_s: int = 172800) -> str:
    """Link temporário para abrir o arquivo (ex.: preview no WhatsApp)."""
    bucket, key = parse(url)
    if settings.storage == "local":
        return str(settings.local_root / bucket / key)
    # A assinatura inclui o host, então assinamos já com o endereço público
    # (assinar não faz chamada de rede).
    client = _s3(settings.s3_public_endpoint)
    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_s
    )


def ensure_bucket() -> None:
    if settings.storage == "local":
        (settings.local_root / settings.s3_bucket).mkdir(parents=True, exist_ok=True)
        return
    client = _s3()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.s3_bucket)


def ping() -> bool:
    try:
        ensure_bucket()
        return True
    except Exception:
        return False

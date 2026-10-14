"""Narração com edge-tts (voz neural da Microsoft, sem custo) com tempo de
cada palavra. A ElevenLabs é chamada pelo n8n; aqui fica só o caminho grátis."""
from __future__ import annotations

import asyncio
from pathlib import Path


async def _synth(text: str, voice: str, rate: str, out: Path) -> list[dict]:
    import edge_tts

    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:  # versões antigas do edge-tts já enviam WordBoundary
        comm = edge_tts.Communicate(text, voice, rate=rate)

    words: list[dict] = []
    with open(out, "wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append({"w": chunk["text"], "s": round(start, 3), "e": round(start + chunk["duration"] / 1e7, 3)})
    return words


def synthesize(text: str, voice: str, out: Path, rate: str = "+0%") -> list[dict]:
    """Gera o MP3 em `out` e devolve [{w, s, e}] em segundos."""
    out.parent.mkdir(parents=True, exist_ok=True)
    return asyncio.run(_synth(text, voice, rate, out))

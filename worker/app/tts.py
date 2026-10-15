"""Narração com edge-tts (voz neural da Microsoft, sem custo) com tempo de
cada palavra. A ElevenLabs é chamada pelo n8n; aqui fica só o caminho grátis."""
from __future__ import annotations

import asyncio
import re
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


def _norm(t: str) -> str:
    return re.sub(r"[^\w]+", "", t.lower())


def restore_punctuation(words: list[dict], text: str) -> list[dict]:
    """O edge-tts devolve as palavras sem pontuação ("somewhere" em vez de
    "somewhere."). Casa cada palavra com o token do texto original, em ordem,
    para a legenda ter pontuação e quebrar linha no fim das frases."""
    tokens = text.split()
    out, ti = [], 0
    for w in words:
        target = _norm(w["w"])
        j = ti
        while j < len(tokens) and j < ti + 4 and _norm(tokens[j]) != target:
            j += 1
        if j < len(tokens) and _norm(tokens[j]) == target:
            out.append({**w, "w": tokens[j]})
            ti = j + 1
        else:
            out.append(w)
    return out


def synthesize(text: str, voice: str, out: Path, rate: str = "+0%") -> list[dict]:
    """Gera o MP3 em `out` e devolve [{w, s, e}] em segundos, com a pontuação do texto."""
    out.parent.mkdir(parents=True, exist_ok=True)
    return restore_punctuation(asyncio.run(_synth(text, voice, rate, out)), text)

"""Narração com edge-tts (voz neural da Microsoft, sem custo) com tempo de
cada palavra. A ElevenLabs é chamada pelo n8n; aqui fica só o caminho grátis."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from pathlib import Path

log = logging.getLogger("fabrica.tts")


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


def _try(text: str, voice: str, out: Path, rate: str, attempts: int) -> tuple[list[dict] | None, str]:
    """Tenta algumas vezes. O serviço grátis da Microsoft às vezes responde sem áudio
    (NoAudioReceived), sobretudo com várias narrações ao mesmo tempo; esperar e repetir resolve."""
    last = ""
    for attempt in range(attempts):
        try:
            words = synthesize(text, voice, out, rate=rate)
            if out.exists() and out.stat().st_size > 1000 and words:
                return words, ""
            last = "áudio vazio"
        except Exception as exc:  # NoAudioReceived, WebSocket fechado, timeout
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(min(5 * (attempt + 1) ** 2, 60))
    return None, last


def synthesize_robust(text: str, voice: str, out: Path, rate: str = "+0%") -> list[dict]:
    """Narra o texto inteiro; se falhar, narra frase por frase e junta os pedaços.
    Se uma frase ainda falhar, o erro diz qual foi, para corrigir o roteiro."""
    from . import media

    words, err = _try(text, voice, out, rate, attempts=4)
    if words:
        return words
    log.warning("edge-tts falhou no texto inteiro (%s); tentando frase por frase", err)
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    parts, all_words, offset = [], [], 0.0
    for i, sent in enumerate(sentences):
        part = out.with_name(f"{out.stem}.{i:03d}.mp3")
        w, err = _try(sent, voice, part, rate, attempts=4)
        if not w:
            raise RuntimeError(f"edge-tts falhou na frase {i + 1}/{len(sentences)} ({err}): {sent[:120]}")
        all_words += [{**x, "s": round(x["s"] + offset, 3), "e": round(x["e"] + offset, 3)} for x in w]
        offset += media.duration(part)
        parts.append(part)
    media.concat_audio(parts, out)
    for p in parts:
        p.unlink(missing_ok=True)
    return all_words

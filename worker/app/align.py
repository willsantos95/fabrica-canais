"""Tempo de cada plano a partir das palavras da narração.

Regra: cada plano começa na primeira palavra do seu `narration_span` e vai até
o início do plano seguinte. Sem palavras com tempo (ex.: voz sem timestamps),
os planos são distribuídos pela duração do bloco na proporção do tamanho do texto.
"""
from __future__ import annotations

import re
from pathlib import Path


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9à-ÿ]+", "", t.lower())


def _find(tokens: list[str], span: list[str], start_at: int) -> int | None:
    if not span:
        return None
    n = len(span)
    for i in range(start_at, len(tokens) - n + 1):
        if tokens[i:i + n] == span:
            return i
    # tolera diferenças pequenas: casa só as 3 primeiras palavras
    head = span[: min(3, n)]
    for i in range(start_at, len(tokens) - len(head) + 1):
        if tokens[i:i + len(head)] == head:
            return i
    return None


def shot_times(block: dict, block_duration: float) -> list[tuple[float, float]]:
    """Devolve (início, fim) de cada plano, em segundos relativos ao bloco."""
    shots = sorted(block["shots"], key=lambda s: s["order"])
    words = (block.get("audio") or {}).get("words") or []
    starts: list[float | None] = []

    if words:
        tokens = [_norm(w["w"]) for w in words]
        cursor = 0
        for shot in shots:
            span = [t for t in (_norm(x) for x in shot["narration_span"].split()) if t]
            idx = _find(tokens, span, cursor)
            if idx is None:
                starts.append(None)
            else:
                starts.append(words[idx]["s"])
                cursor = idx + 1

    if not words or all(s is None for s in starts):
        weights = [max(len(s["narration_span"]), 1) for s in shots]
        total = sum(weights)
        acc, starts = 0.0, []
        for wgt in weights:
            starts.append(acc)
            acc += block_duration * wgt / total

    # primeiro plano cobre o começo do bloco; planos não encontrados herdam a posição média
    starts[0] = 0.0
    for i in range(1, len(starts)):
        if starts[i] is None or starts[i] <= starts[i - 1]:
            nxt = next((s for s in starts[i + 1:] if s is not None and s > (starts[i - 1] or 0)), block_duration)
            starts[i] = (starts[i - 1] + nxt) / 2
    ends = starts[1:] + [block_duration]
    return [(round(s, 3), round(e, 3)) for s, e in zip(starts, ends)]


def transcribe(audio: Path, language: str | None = None, model_name: str = "small") -> list[dict]:
    """Transcrição com tempo por palavra (faster-whisper, em CPU)."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(audio), language=(language or "")[:2] or None, word_timestamps=True)
    words = []
    for seg in segments:
        for w in seg.words or []:
            words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)})
    return words


def text_match_ratio(expected: str, words: list[dict]) -> float:
    """Fração das palavras do roteiro que aparecem na transcrição (checagem de pronúncia)."""
    exp = [t for t in (_norm(x) for x in expected.split()) if t]
    got = set(_norm(w["w"]) for w in words)
    return sum(1 for t in exp if t in got) / len(exp) if exp else 1.0

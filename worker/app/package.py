"""Pacote de publicação sem custo de IA de texto: escolhe os trechos dos Shorts,
monta título, descrição com capítulos e fontes, tags e as opções de thumbnail.

Tudo sai do video_spec (roteiro, fontes, tempos de cada palavra), então não
precisa de outra chamada à OpenAI.
"""
from __future__ import annotations

import re

NUMBER_WORDS = {
    "hundred", "thousand", "million", "billion", "percent", "dollars", "dollar", "euros", "pounds",
    "years", "hours", "salary", "pay", "median", "average", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "twenty", "thirty", "forty", "fifty", "sixty",
    "seventy", "eighty", "ninety",
}
SHORT_MIN_S, SHORT_MAX_S, SHORT_TARGET_S = 25.0, 55.0, 40.0


# ---------------------------------------------------------------------------
# Shorts
# ---------------------------------------------------------------------------
def _sentences(spec: dict) -> list[dict]:
    """Frases com início e fim no tempo do vídeo final, a partir das palavras de cada bloco."""
    out = []
    for bi, b in enumerate(spec["blocks"]):
        audio = b.get("audio") or {}
        off = audio.get("offset_s") or 0.0
        cur: list[dict] = []
        for w in audio.get("words") or []:
            cur.append(w)
            if re.search(r"[.!?][\"')\]]*$", w["w"]):
                out.append({"block": bi, "s": cur[0]["s"] + off, "e": cur[-1]["e"] + off,
                            "text": " ".join(x["w"] for x in cur)})
                cur = []
        if cur:
            out.append({"block": bi, "s": cur[0]["s"] + off, "e": cur[-1]["e"] + off,
                        "text": " ".join(x["w"] for x in cur)})
    return out


def _score(text: str, dur: float) -> float:
    words = re.findall(r"[a-zA-Z$%']+", text.lower())
    facts = sum(1 for w in words if w in NUMBER_WORDS) + text.count("$") + text.count("%")
    question = 2.0 if "?" in text.split(".")[0] else 0.0
    return facts + question - abs(dur - SHORT_TARGET_S) / 10


def select_shorts(spec: dict, n: int = 3) -> list[dict]:
    """Melhor trecho de cada bloco (frases inteiras, 25–55 s, dentro do mesmo bloco) e,
    entre eles, os n melhores espalhados pelo vídeo."""
    sents = _sentences(spec)
    best_by_block: dict[int, dict] = {}
    for i, first in enumerate(sents):
        text, end = [], None
        for s in sents[i:]:
            if s["block"] != first["block"]:
                break
            dur = s["e"] - first["s"]
            if dur > SHORT_MAX_S:
                break
            text.append(s["text"])
            end = s["e"]
            if dur >= SHORT_MIN_S:
                cand = {"block": first["block"], "start_s": round(max(0.0, first["s"] - 0.15), 2),
                        "end_s": round(end + 0.35, 2), "text": " ".join(text)}
                cand["score"] = _score(cand["text"], end - first["s"])
                cur = best_by_block.get(first["block"])
                if not cur or cand["score"] > cur["score"]:
                    best_by_block[first["block"]] = cand
    ranked = sorted(best_by_block.values(), key=lambda c: c["score"], reverse=True)
    chosen: list[dict] = []
    for c in ranked:  # evita dois Shorts de blocos vizinhos quando dá
        if all(abs(c["block"] - x["block"]) > 1 for x in chosen):
            chosen.append(c)
        if len(chosen) == n:
            break
    for c in ranked:
        if len(chosen) == n:
            break
        if c not in chosen:
            chosen.append(c)
    chosen.sort(key=lambda c: c["start_s"])
    for c in chosen:
        c["hook"] = spec["blocks"][c["block"]]["title"]
    return chosen


# ---------------------------------------------------------------------------
# Metadados do YouTube
# ---------------------------------------------------------------------------
def _ts(seconds: float) -> str:
    s = int(round(seconds))
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _clean(text: str) -> str:
    # o YouTube recusa < e > na descrição e no título
    return re.sub(r"[<>]", "", text or "").strip()


def profession(spec: dict) -> str | None:
    m = re.search(r"level of an? (.+?)['’]s career", spec.get("topic") or "", re.I)
    return m.group(1).strip() if m else None


def _first_sentences(text: str, n: int = 2) -> str:
    parts = re.findall(r"[^.!?]+[.!?]+", text or "")
    return " ".join(p.strip() for p in parts[:n]) or (text or "")[:200]


def build_metadata(spec: dict, cfg: dict) -> dict:
    yt = cfg.get("youtube") or {}
    lang = (cfg.get("language") or "en").split("-")[0]
    title = _clean(spec.get("chosen_title") or spec.get("topic") or "")[:100]

    chapters = spec.get("publishing", {}).get("chapters") or [
        {"t": (b.get("audio") or {}).get("offset_s") or 0, "title": b["title"]} for b in spec["blocks"]]
    chapter_lines = []
    for i, c in enumerate(chapters):
        t = 0 if i == 0 else c["t"]  # o primeiro capítulo precisa começar em 0:00
        chapter_lines.append(f"{_ts(t)} {_clean(c['title'])}")

    sources = [f"- {_clean(s.get('title') or s['url'])}: {s['url']}" for s in spec.get("sources") or []]
    prof = profession(spec)
    tags = list(dict.fromkeys(
        [t for t in yt.get("default_tags") or []] +
        ([prof, f"{prof} career", f"{prof} salary", f"how to become a {prof}"] if prof else []) +
        [cfg.get("name", "")]
    ))
    tags = [t for t in tags if t]
    while sum(len(t) + 3 for t in tags) > 480:  # limite do YouTube: 500 caracteres somando as tags
        tags.pop()
    hashtags = " ".join("#" + re.sub(r"[^a-zA-Z0-9]", "", t.title()) for t in ([prof] if prof else []) + ["Careers"])

    hook = _clean(_first_sentences(spec["blocks"][0]["narration"], 2))
    description = "\n".join([
        hook, "",
        "Chapters", *chapter_lines, "",
        "Sources", *sources, "",
        "Numbers vary by country, company and year; check the sources above for the details.", "",
        hashtags,
    ])[:4900]
    return {
        "title": title,
        "description": description,
        "tags": tags,
        "category_id": str(yt.get("category_id") or "27"),
        "language": lang,
        "contains_synthetic_media": bool(yt.get("contains_synthetic_media", False)),
        "made_for_kids": bool(yt.get("made_for_kids", False)),
    }


def short_metadata(short: dict, spec: dict, cfg: dict, idx: int) -> dict:
    hook = _clean(re.sub(r"^Level \d+\s*[-–]\s*", "", short.get("hook") or ""))
    prof = profession(spec)
    base = f"{prof.title()}: {hook}" if prof and hook and prof.lower() not in hook.lower() else (hook or spec.get("chosen_title", ""))
    title = _clean(f"{base} #Shorts")[:100]
    first = _clean(_first_sentences(short.get("text", ""), 1))
    description = f"{first}\n\nFull video: {{{{LONG_URL}}}}\n\n#Shorts #Careers"
    return {"title": title, "description": description[:4900]}

"""Monta o corpo do factory.preparar no formato compacto e confere o tamanho.

Uso num roteiro:  from _compact import save;  save(__file__, CHANNEL, TITLE, PRIORITY, META, SOURCES, BLOCKS, min_words=...)
BLOCKS = [(block_id, title, [source_ids], [(narração, prompt visual em inglês, texto na tela ou None[, {actors, fx}]), ...]), ...]
Grava <arquivo>.json com {channel_slug, title, priority, author, compact} pronto para POST em
/webhook/fabrica-preparar?k=CHAVE_DO_PAINEL.
"""
import json
import sys
from pathlib import Path


def save(path, channel, title, priority, meta, sources, blocks, min_words=1500, max_words=2100):
    ids = {s["id"] for s in sources}
    words = shots = 0
    out_blocks = []
    for bid, btitle, src, items in blocks:
        assert set(src) <= ids, f"{bid}: fonte desconhecida {set(src) - ids}"
        for it in items:
            n, p = it[0], it[1]
            assert n.strip() and p.strip(), f"{bid}: trecho vazio"
            words += len(n.split())
            shots += 1
        out_blocks.append({"block_id": bid, "title": btitle, "source_ids": src, "shots": [list(x) for x in items]})
    body = {"channel_slug": channel, "title": title, "priority": priority, "author": "claude",
            "compact": {"meta": meta, "sources": sources, "blocks": out_blocks}}
    out = Path(path).with_suffix(".json")
    out.write_text(json.dumps(body, ensure_ascii=False, indent=1), "utf-8")
    print(f"{Path(path).name}: {words} palavras, {len(blocks)} blocos, {shots} planos -> {out.name}")
    if not (min_words <= words <= max_words):
        sys.exit(f"tamanho fora da faixa {min_words}-{max_words}")
    return body

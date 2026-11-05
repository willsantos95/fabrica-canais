"""Versão com stickman animado por código de "Fiquei Preso 1 Ano na Antártida".

Mesma narração, fontes e títulos de estacao-antartida.py. Muda só a imagem de cada plano:
- com "actors": a IA gera só o cenário (vazio) e o worker desenha e anima os personagens por cima;
- sem "actors": plano normal da IA (diagramas, objetos, paisagens), com a câmera dinâmica.
actor = {who: you|tomas|nina|bento|extra, action|beats, x (0-1), to?, facing?, delay?}
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _compact import save  # noqa: E402

_spec = importlib.util.spec_from_file_location("base", HERE / "estacao-antartida.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

STATION = "a tiny Antarctic research station of three connected boxy orange modules on stilts, a fuel tank and a tall radio antenna, on a flat endless white ice plateau"
KITCHEN = "the small kitchen of a polar research station, a long table with chairs, shelves and a small frosty window"
MACHINE = "a cramped machine room with a big diesel generator, pipes and gauges on the walls"
BUNKS = "a small bunk room of a polar station, metal bunk beds and a small window"
MEDIC = "a tiny medical room with a cot, a lamp and shelves of bandages"
RUNWAY = "an ice runway marked with small red flags on a flat white plateau"


def A(who, action="idle", x=0.5, **kw):
    return {"who": who, "action": action, "x": x, **kw}


def four(action, xs=(0.2, 0.38, 0.56, 0.74), facing=None):
    out = []
    for who, x in zip(("tomas", "nina", "bento", "you"), xs):
        a = A(who, action, x)
        if facing:
            a["facing"] = facing
        out.append(a)
    return out


# (cenário, actors | None, fx) na mesma ordem dos planos do roteiro original
VIS = [
    # b01
    (None, None, None),
    ("the side of a parked ski-equipped cargo plane on snow with a short metal stair, bright sun, open snow in front", [A("you", "shiver", 0.46)], None),
    (f"wide view of {STATION}, bright polar summer sun, open snow in the foreground", [A("you", "walk", 0.12, to=0.42)], None),
    (MACHINE, [A("you", "point", 0.32, facing=1)], None),
    (f"{KITCHEN}, warm light", [A("tomas", "idle", 0.22), A("nina", "wave", 0.4), A("bento", "cheer", 0.58), A("you", "wave", 0.76)], None),
    (f"{KITCHEN}, a paper wall calendar with February and November circled in red", [A("tomas", "point", 0.32, facing=1), A("you", "idle", 0.72, facing=-1)], None),
    (None, None, None),
    (f"{KITCHEN}, dinner plates on the table", [A("you", "talk", 0.35), A("tomas", "idle", 0.66, facing=-1)], None),
    # b02
    (f"{BUNKS}, bright sunlight coming through the window, a wall clock showing 2 a.m.", [A("you", "sleep", 0.5)], None),
    (f"outside {STATION}, sunny, a radio antenna", [A("tomas", "talk", 0.34), A("you", "idle", 0.62, facing=-1)], None),
    ("a station window looking out onto endless ice, a small table with a glass of water", [A("you", "look_up", 0.42, facing=1)], None),
    (None, None, None),
    (f"{MACHINE}, a water tap next to it", [A("you", "sad", 0.42)], None),
    (None, None, None),
    (f"{RUNWAY}, a tiny plane far away in the bright sky", four("look_up", facing=1), None),
    (f"wide view of {STATION}, empty and silent, wind lines in the snow", [A("you", "sad", 0.3)], None),
    ("a station pantry full of food boxes next to a big fuel tank with a round gauge", [A("bento", "work", 0.3), A("you", "work", 0.66)], None),
    # b03
    (None, None, None),
    ("a flat ice plateau at sunset, the sun touching the horizon, pink and purple sky", [A("you", "look_up", 0.38, facing=1), A("tomas", "look_up", 0.56, facing=1)], None),
    ("a flat ice plateau at sunset, the sun touching the horizon, pink and purple sky", [A("tomas", "idle", 0.2), A("nina", "look_up", 0.38), A("bento", "point", 0.56), A("you", "look_up", 0.74)], None),
    (None, None, None),
    (None, None, None),
    (f"{KITCHEN}, frost covering the window, a mug on the table, night", [A("tomas", "talk", 0.34), A("you", "scared", 0.66, facing=-1)], None),
    (f"green aurora australis waving across a starry night sky above {STATION}", [A("you", "look_up", 0.3, facing=1)], "snow"),
    ("a huge starry night sky with green aurora over a flat ice plateau, wide and empty", [A("you", "look_up", 0.5, scale=0.85)], "snow"),
    # b04
    (None, None, None),
    (f"{BUNKS}, dim light, dark window", [A("you", "sad", 0.46)], None),
    (f"{KITCHEN}, dim light, a cold coffee mug on the table", [A("nina", "sit", 0.36, facing=1), A("you", "idle", 0.76, facing=-1)], None),
    ("a small table with a laptop showing a simple line chart, dim station room", [A("nina", "talk", 0.34), A("you", "idle", 0.66, facing=-1)], None),
    (None, None, None),
    (f"{KITCHEN}, a small oven with a pizza, warm light", [A("bento", "work", 0.2), A("tomas", "cheer", 0.44), A("nina", "cheer", 0.62), A("you", "cheer", 0.8)], None),
    ("a small cozy station room with a glowing screen on the left wall and blankets", four("sit", xs=(0.4, 0.55, 0.7, 0.85), facing=-1), None),
    # b05
    (f"{BUNKS}, total darkness, only a faint red light", [A("you", "scared", 0.5)], None),
    (None, None, None),
    ("a narrow dark station corridor lit by red emergency lights", [A("you", "run", 0.18, to=0.72), A("tomas", "run", 0.04, to=0.46, delay=0.6)], None),
    (f"{MACHINE}, frost forming on the pipes, a wall clock showing 3:20", [A("you", "work", 0.36)], None),
    (None, None, None),
    (None, None, None),
    (None, None, None),
    (f"{MACHINE}, a wall clock, a radio on a shelf, red light", [A("you", "shiver", 0.45)], None),
    ("the inside of a station door covered in frost, snow blowing in", [A("tomas", "shiver", 0.5)], "snow"),
    (f"{MACHINE}, a control panel with a key, lights turning on", [A("you", "x", 0.36, beats=[["work", 3.0], ["cheer", 99]])], None),
    (f"{MACHINE}, warm light, the generator running", [A("you", "sit", 0.36), A("bento", "walk", 0.9, to=0.58, beats=[["walk", 2.0, 0.58], ["idle", 99]])], None),
    # b06
    (MEDIC, [A("tomas", "idle", 0.4), A("nina", "work", 0.6, facing=-1)], None),
    (f"{MEDIC}, night, a basin of warm water on a small table, a wall clock", [A("tomas", "sit", 0.4), A("nina", "work", 0.58, facing=-1)], None),
    ("a radio desk with an old radio and a microphone in a small station room", [A("bento", "talk", 0.34), A("nina", "idle", 0.6, facing=-1)], None),
    (None, None, None),
    (f"{BUNKS}, a dim lamp", [A("tomas", "sad", 0.4), A("you", "idle", 0.66, facing=-1)], None),
    (MEDIC, [A("bento", "cheer", 0.2), A("tomas", "talk", 0.4), A("nina", "idle", 0.58, facing=-1), A("you", "cheer", 0.78)], None),
    (f"{KITCHEN}, pizza on the table, warm light, laughter", four("talk"), None),
    # b07
    (f"{MACHINE}, a big fuel gauge pointing near the red zone", [A("you", "point", 0.38, facing=1)], None),
    ("a station corridor with a closed door with a sign, mattresses on the floor", [A("you", "walk", 0.62, to=0.4)], None),
    ("a small desk with a lamp and a notebook full of crossed out numbers", [A("you", "work", 0.45)], None),
    ("a station corridor with a small window at the end", [A("bento", "point", 0.66, facing=1), A("you", "run", 0.1, to=0.46)], None),
    (None, None, None),
    (None, None, None),
    (f"outside {STATION} in golden sunlight, long shadows", four("cheer"), None),
    ("a sunny station window with warm light pouring in", [A("you", "look_up", 0.5, facing=1)], None),
    # b08
    (RUNWAY + ", bright blue sky", four("look_up", facing=1), None),
    (RUNWAY + ", a tiny airplane in a bright blue sky", [A("you", "point_up", 0.4)], None),
    (RUNWAY + ", a plane approaching in the sky", [A("you", "idle", 0.3, facing=1), A("nina", "cheer", 0.6), A("bento", "cheer", 0.76)], None),
    (None, None, None),
    ("a crate of fresh oranges on the snow next to a parked plane", [A("bento", "cheer", 0.35), A("you", "jump", 0.6, beats=[["jump", 1.1], ["cheer", 99]])], None),
    ("the side of a parked ski-equipped plane on an ice runway, open door", [A("extra", "talk", 0.4), A("you", "idle", 0.66, facing=-1)], None),
    (None, None, None),
    (f"{RUNWAY}, a parked plane with an open door on the right, {STATION} far on the left", [A("tomas", "idle", 0.15), A("bento", "idle", 0.35), A("you", "idle", 0.55, facing=-1), A("nina", "walk", 0.7, to=0.9)], None),
    ("an open plane door on the left and a tiny orange polar station on the right, bright sun on the snow", [A("you", "x", 0.5, beats=[["look_up", 2.0], ["idle", 99]])], None),
]


def build():
    blocks, k = [], 0
    for bid, title, src, items in base.BLOCKS:
        shots = []
        for narr, prompt, overlay in items:
            bg, actors, fx = VIS[k]
            k += 1
            if actors:
                shots.append((narr, bg, overlay, {"actors": actors, **({"fx": fx} if fx else {})}))
            else:
                shots.append((narr, prompt, overlay))
        blocks.append((bid, title, src, shots))
    assert k == len(VIS), (k, len(VIS))
    return blocks


if __name__ == "__main__":
    body = save(__file__, base.CHANNEL, base.TITLE, base.PRIORITY, base.META, base.SOURCES, build(),
                min_words=1350, max_words=1800)
    n = sum(1 for b in body["compact"]["blocks"] for s in b["shots"] if len(s) > 3)
    print(f"planos com stickman: {n}")

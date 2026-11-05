"""Stickman articulado desenhado por código (custo zero, sem IA de vídeo).

O personagem é um esqueleto 2D (quadril, tronco, pescoço, cabeça, braços e pernas com cotovelo e
joelho). Cada ação (andar, parado, tremer de frio, apontar, pular, acenar) é uma função do tempo que
devolve os ângulos das juntas; a troca entre ações é suavizada. O desenho é feito em 2x e reduzido,
para as linhas saírem lisas, e colado em cima do cenário (que na fábrica seria a imagem da IA).

Uso no piloto:  python3 -m app.stickman  (gera /tmp/stickman-piloto.mp4)
"""
from __future__ import annotations

import math
import random
import subprocess
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
SS = 2  # supersampling do personagem

# ---------------------------------------------------------------- aparência ---
@dataclass
class Look:
    scale: float = 1.0
    head_r: float = 46
    torso: float = 92
    neck: float = 8
    upper_arm: float = 54
    forearm: float = 50
    thigh: float = 84
    shin: float = 80
    line: str = "#111111"
    skin: str = "#FFFFFF"
    jacket: str = "#2E7D32"
    jacket_dark: str = "#1F5E24"
    hat: str = "#E65100"
    hat_dark: str = "#B33F00"
    torso_w: float = 56
    sleeve_w: float = 22
    leg_w: float = 8
    outline: float = 4.5
    hat_on: bool = True
    beard: str | None = None     # cor da barba (ex.: "#9E9E9E") ou None
    glasses: bool = False
    hair: str | None = None      # cor do cabelo quando não há gorro
    body: float = 1.0            # largura do tronco (1.0 normal, 1.25 mais cheinho)


# personagens prontos (roteiro usa "who": "you" | "tomas" | "nina" | "bento" | "kid" | "extra")
LOOKS = {
    "you":   dict(jacket="#2E7D32", jacket_dark="#1F5E24", hat="#E65100", hat_dark="#B33F00"),
    "tomas": dict(jacket="#C62828", jacket_dark="#8E1B1B", hat_on=False, beard="#9E9E9E", hair="#9E9E9E", head_r=47),
    "nina":  dict(jacket="#ECEFF1", jacket_dark="#B0BEC5", hat="#6A1B9A", hat_dark="#4A126B"),
    "bento": dict(jacket="#1565C0", jacket_dark="#0D47A1", hat_on=False, glasses=True, hair="#3E2723", body=1.3),
    "kid":   dict(jacket="#FBC02D", jacket_dark="#C49000", hat_on=False, hair="#4E342E", head_r=40, torso=70,
                  thigh=62, shin=58, upper_arm=42, forearm=40),
    "extra": dict(jacket="#546E7A", jacket_dark="#37474F", hat_on=False, hair="#212121"),
}


def look_for(who: str, scale: float) -> "Look":
    return Look(scale=scale, **LOOKS.get(who, LOOKS["extra"]))


# ---------------------------------------------------------------- pose -------
JOINTS = ("lean", "head", "sh_b", "el_b", "sh_f", "el_f", "hip_b", "kn_b", "hip_f", "kn_f")


@dataclass
class Pose:
    lean: float = 0      # inclinação do tronco (graus, + para frente)
    head: float = 0      # inclinação da cabeça
    sh_b: float = -8     # ombro do braço de trás (0 = para baixo, + para frente)
    el_b: float = 8      # cotovelo (+ dobra para frente)
    sh_f: float = 8
    el_f: float = 8
    hip_b: float = -4    # quadril da perna de trás
    kn_b: float = 2      # joelho (+ dobra para trás)
    hip_f: float = 4
    kn_f: float = 2
    lift: float = 0      # altura do pulo (px)
    dx: float = 0        # tremidinha horizontal (px)
    eye_x: float = 0.25  # olhar: -1..1 (relativo à direção)
    eye_y: float = 0.0
    blink: bool = False

    def lerp(self, o: "Pose", k: float) -> "Pose":
        p = Pose()
        for f in ("lean", "head", *JOINTS[2:], "lift", "dx", "eye_x", "eye_y"):
            setattr(p, f, getattr(self, f) * (1 - k) + getattr(o, f) * k)
        p.blink = o.blink if k > 0.5 else self.blink
        return p


def _ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- ações ------
def act_idle(t: float, **_) -> Pose:
    b = math.sin(t * 2 * math.pi * 0.35)
    return Pose(lean=1 + b, head=b * 1.5, sh_b=-6 + b * 2, sh_f=6 - b * 2, el_b=10, el_f=10)


def act_walk(t: float, speed: float = 1.7, **_) -> Pose:
    p = t * 2 * math.pi * speed
    s = math.sin(p)
    return Pose(lean=6, head=-2 + math.sin(2 * p) * 1.2,
                hip_f=26 * s, hip_b=-26 * s,
                kn_f=8 + 34 * max(0.0, math.cos(p)), kn_b=8 + 34 * max(0.0, -math.cos(p)),
                sh_f=-24 * s, sh_b=24 * s, el_f=18 + 8 * max(0, -s), el_b=18 + 8 * max(0, s))


def act_shiver(t: float, **_) -> Pose:
    j = math.sin(t * 2 * math.pi * 14)
    k = math.sin(t * 2 * math.pi * 11 + 1.3)
    return Pose(lean=4 + j * 0.8, head=-4 + k * 2, sh_f=58 + j * 3, el_f=112, sh_b=46 + k * 3, el_b=118,
                hip_f=3, hip_b=-3, kn_f=6, kn_b=6, dx=j * 1.8, eye_x=0.1, eye_y=0.15)


def act_point_up(t: float, **_) -> Pose:
    k = _ease(t / 0.35)
    shake = math.sin(t * 2 * math.pi * 1.2) * 2
    return Pose(lean=-4 * k, head=-14 * k, sh_f=8 + 150 * k + shake, el_f=8 - 6 * k,
                sh_b=-10, el_b=14, eye_x=0.35, eye_y=-0.9 * k)


def act_jump(t: float, dur: float = 1.1, **_) -> Pose:
    u = t / dur
    if u < 0.25:   # agacha
        c = _ease(u / 0.25)
        return Pose(lean=14 * c, hip_f=40 * c, hip_b=34 * c, kn_f=70 * c, kn_b=66 * c,
                    sh_f=-30 * c, sh_b=-40 * c, el_f=10, el_b=10, eye_y=0.2)
    if u < 0.8:    # no ar
        a = (u - 0.25) / 0.55
        return Pose(lean=-2, hip_f=24, hip_b=8, kn_f=50, kn_b=40, sh_f=165, sh_b=150,
                    el_f=-6, el_b=-6, lift=4 * 230 * a * (1 - a), eye_y=-0.4)
    c = 1 - _ease((u - 0.8) / 0.2)  # aterrissa
    return Pose(lean=10 * c, hip_f=30 * c, hip_b=26 * c, kn_f=55 * c, kn_b=50 * c,
                sh_f=40 * c, sh_b=30 * c, el_f=20, el_b=20)


def act_wave(t: float, **_) -> Pose:
    k = _ease(t / 0.3)
    w = math.sin(t * 2 * math.pi * 2.6)
    return Pose(lean=0, head=3 * w * k, sh_f=8 + 142 * k, el_f=8 + (28 + 26 * w) * k,
                sh_b=-6, el_b=10, eye_x=0.0, eye_y=0.0)


def act_run(t: float, **_) -> Pose:
    p = act_walk(t, speed=2.8)
    p.lean = 16
    p.hip_f, p.hip_b = p.hip_f * 1.5, p.hip_b * 1.5
    p.kn_f, p.kn_b = p.kn_f * 1.6, p.kn_b * 1.6
    p.sh_f, p.sh_b = p.sh_f * 1.6, p.sh_b * 1.6
    p.el_f = p.el_b = 80
    p.lift = abs(math.sin(t * 2 * math.pi * 2.8)) * 10
    return p


def act_talk(t: float, **_) -> Pose:
    g = math.sin(t * 2 * math.pi * 0.9)
    h = math.sin(t * 2 * math.pi * 1.7 + 0.6)
    return Pose(lean=2 + g, head=2 * h, sh_f=38 + 14 * g, el_f=70 + 18 * h, sh_b=-4, el_b=12, eye_x=0.35)


def act_work(t: float, **_) -> Pose:
    k = math.sin(t * 2 * math.pi * 2.2)
    return Pose(lean=14, head=10, sh_f=62 + 6 * k, el_f=34 - 6 * k, sh_b=54 - 5 * k, el_b=40 + 6 * k,
                hip_f=8, hip_b=-6, kn_f=10, kn_b=6, eye_x=0.4, eye_y=0.5)


def act_sad(t: float, **_) -> Pose:
    b = math.sin(t * 2 * math.pi * 0.25)
    return Pose(lean=10 + b, head=22, sh_f=4, el_f=6, sh_b=-2, el_b=6, eye_x=0.2, eye_y=0.9)


def act_cheer(t: float, **_) -> Pose:
    b = abs(math.sin(t * 2 * math.pi * 1.6))
    return Pose(lean=-3, head=-6, sh_f=150 + 10 * b, el_f=-10, sh_b=140 + 10 * b, el_b=-10,
                hip_f=6, hip_b=-6, kn_f=10 + 20 * (1 - b), kn_b=10 + 20 * (1 - b), lift=22 * b, eye_y=-0.4)


def act_sit(t: float, **_) -> Pose:
    b = math.sin(t * 2 * math.pi * 0.3)
    return Pose(lean=4 + b, head=2, hip_f=84, hip_b=78, kn_f=84, kn_b=78, sh_f=30, el_f=50,
                sh_b=24, el_b=55, eye_x=0.3)


def act_look_up(t: float, **_) -> Pose:
    k = _ease(t / 0.5)
    b = math.sin(t * 2 * math.pi * 0.4)
    return Pose(lean=-5 * k, head=-16 * k + b, sh_f=6, el_f=10, sh_b=-6, el_b=10, eye_x=0.3, eye_y=-1.0 * k)


def act_point(t: float, **_) -> Pose:
    k = _ease(t / 0.3)
    return Pose(lean=3, head=-2, sh_f=8 + 82 * k, el_f=4, sh_b=-8, el_b=12, eye_x=0.9 * k)


def act_scared(t: float, **_) -> Pose:
    j = math.sin(t * 2 * math.pi * 9)
    return Pose(lean=-8, head=-6 + j, sh_f=118 + 4 * j, el_f=100, sh_b=110 - 4 * j, el_b=104,
                hip_f=10, hip_b=-14, kn_f=18, kn_b=14, dx=j * 2.2, eye_x=0.6, eye_y=-0.2)


def act_sleep(t: float, **_) -> Pose:
    p = act_sit(t)
    p.head, p.lean, p.blink = 26, 14, True
    p.eye_y = 0.6
    return p


ACTIONS = {"idle": act_idle, "walk": act_walk, "run": act_run, "shiver": act_shiver,
           "point_up": act_point_up, "point": act_point, "jump": act_jump, "wave": act_wave,
           "talk": act_talk, "work": act_work, "sad": act_sad, "cheer": act_cheer, "sit": act_sit,
           "look_up": act_look_up, "scared": act_scared, "sleep": act_sleep}


@dataclass
class Beat:
    start: float
    end: float
    action: str
    x0: float          # posição x (fração da largura) no começo
    x1: float | None = None
    facing: int = 1
    params: dict = field(default_factory=dict)


class Timeline:
    """Sequência de ações com transição suave entre uma e outra."""

    def __init__(self, beats: list[Beat], blend: float = 0.28, seed: int = 7):
        self.beats = beats
        self.blend = blend
        self.rnd = random.Random(seed)
        self.blinks = []
        t = self.rnd.uniform(0.5, 2.6)
        while t < beats[-1].end:
            self.blinks.append(t)
            t += self.rnd.uniform(2.2, 4.0)

    def _raw(self, b: Beat, t: float) -> Pose:
        return ACTIONS[b.action](t - b.start, **b.params)

    def at(self, t: float) -> tuple[Pose, float, int]:
        i = next((k for k, b in enumerate(self.beats) if t < b.end), len(self.beats) - 1)
        b = self.beats[i]
        p = self._raw(b, t)
        if i > 0 and t - b.start < self.blend:
            prev = self.beats[i - 1]
            p = self._raw(prev, prev.end - 1e-3).lerp(p, _ease((t - b.start) / self.blend))
        u = (t - b.start) / max(b.end - b.start, 1e-6)
        x = b.x0 if b.x1 is None else b.x0 + (b.x1 - b.x0) * max(0.0, min(1.0, u))
        p.blink = p.blink or any(0 <= t - bt < 0.12 for bt in self.blinks)
        return p, x, b.facing


# ---------------------------------------------------------------- desenho ----
def _dir(a: float) -> tuple[float, float]:
    r = math.radians(a)
    return math.sin(r), math.cos(r)


def skeleton(p: Pose, L: Look, f: int) -> dict:
    """Juntas com o quadril em (0,0). y cresce para baixo; f = 1 olha para a direita."""
    s = L.scale * SS

    def go(pt, a, n):
        dx, dy = _dir(a)
        return pt[0] + dx * n * s * f, pt[1] + dy * n * s

    hip = (0.0, 0.0)
    neck = go(hip, 180 - p.lean, L.torso)
    head = go(neck, 180 - p.lean - p.head, L.neck + L.head_r)
    sh = go(neck, -p.lean, 10)
    j = {"hip": hip, "neck": neck, "head": head, "sh": sh}
    for side in ("b", "f"):
        a = getattr(p, f"sh_{side}") - p.lean * 0.5
        el = go(sh, a, L.upper_arm)
        j[f"el_{side}"], j[f"ha_{side}"] = el, go(el, a + getattr(p, f"el_{side}"), L.forearm)
        h = getattr(p, f"hip_{side}")
        kn = go(hip, h, L.thigh)
        j[f"kn_{side}"], j[f"ft_{side}"] = kn, go(kn, h - getattr(p, f"kn_{side}"), L.shin)
    return j


def _seg(d: ImageDraw.ImageDraw, a, b, w, fill, outline=None, ow=0):
    if outline:
        d.line([a, b], fill=outline, width=int(w + 2 * ow))
        for q in (a, b):
            r = (w + 2 * ow) / 2
            d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=outline)
    d.line([a, b], fill=fill, width=int(w))
    for q in (a, b):
        r = w / 2
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=fill)


def _rot(pts, c, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in pts]


def draw_character(p: Pose, L: Look, f: int) -> tuple[Image.Image, tuple[float, float]]:
    """Devolve a camada RGBA (já reduzida para 1x) e a posição do quadril dentro dela."""
    j = skeleton(p, L, f)
    s = L.scale * SS
    pad = (L.head_r * 2 + 40) * s
    xs = [q[0] for q in j.values()]
    ys = [q[1] for q in j.values()]
    x0, y0 = min(xs) - pad, min(ys) - pad
    w, h = int(max(xs) - x0 + pad), int(max(ys) - y0 + pad)
    w += (-w) % SS
    h += (-h) % SS
    j = {k: (q[0] - x0, q[1] - y0) for k, q in j.items()}
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    o = L.outline * s

    # perna e braço de trás
    _seg(d, j["hip"], j["kn_b"], L.leg_w * s, L.line)
    _seg(d, j["kn_b"], j["ft_b"], L.leg_w * s, L.line)
    _seg(d, j["sh"], j["el_b"], L.sleeve_w * s, L.jacket_dark, L.line, o)
    _seg(d, j["el_b"], j["ha_b"], L.sleeve_w * s * 0.92, L.jacket_dark, L.line, o)
    _hand(d, j["ha_b"], L, s)
    # perna da frente
    _seg(d, j["hip"], j["kn_f"], L.leg_w * s, L.line)
    _seg(d, j["kn_f"], j["ft_f"], L.leg_w * s, L.line)
    for k in ("ft_b", "ft_f"):  # botas
        fx, fy = j[k]
        d.ellipse([fx - 6 * s + 7 * s * f, fy - 5 * s, fx + 9 * s + 7 * s * f, fy + 6 * s], fill=L.line)
    # tronco (parka)
    bottom = (j["hip"][0] + (j["neck"][0] - j["hip"][0]) * -0.12, j["hip"][1] + (j["neck"][1] - j["hip"][1]) * -0.12)
    _seg(d, bottom, j["neck"], L.torso_w * L.body * s, L.jacket, L.line, o)
    zx = (bottom[0] + j["neck"][0]) / 2 + 6 * s * f
    d.line([(zx, j["neck"][1] + 10 * s), (zx - 2 * s * f, bottom[1] - 6 * s)], fill=L.jacket_dark, width=int(3 * s))
    # cabeça
    hx, hy = j["head"]
    r = L.head_r * s
    d.ellipse([hx - r - o, hy - r - o, hx + r + o, hy + r + o], fill=L.line)
    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=L.skin)
    if L.beard:
        _beard(d, (hx, hy), r, p, f, L, s, o)
    _eyes(d, (hx, hy), r, p, f, L, s)
    if L.hat_on:
        _beanie(d, (hx, hy), r, p, f, L, s, o)
    elif L.hair:
        _hair(d, (hx, hy), r, p, f, L, s, o)
    # braço da frente por cima
    _seg(d, j["sh"], j["el_f"], L.sleeve_w * s, L.jacket, L.line, o)
    _seg(d, j["el_f"], j["ha_f"], L.sleeve_w * s * 0.92, L.jacket, L.line, o)
    _hand(d, j["ha_f"], L, s)

    small = img.reduce(SS)
    return small, (-x0 / SS, -y0 / SS)


def _hand(d, q, L, s):
    r = 9 * s
    d.ellipse([q[0] - r - L.outline * s * 0.8, q[1] - r - L.outline * s * 0.8,
               q[0] + r + L.outline * s * 0.8, q[1] + r + L.outline * s * 0.8], fill=L.line)
    d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=L.skin)


def _eyes(d, c, r, p, f, L, s):
    ex = c[0] + p.eye_x * 0.32 * r * f
    ey = c[1] + 0.05 * r + p.eye_y * 0.22 * r
    gap = 0.30 * r
    for k in (-1, 1):
        x = ex + k * gap
        if p.blink:
            d.line([(x - 6 * s, ey), (x + 6 * s, ey)], fill=L.line, width=int(3 * s))
        else:
            er = 5.5 * s
            d.ellipse([x - er, ey - er * 1.2, x + er, ey + er * 1.2], fill=L.line)
        if L.glasses:
            gr = 0.21 * r
            gx = ex + k * gap
            d.ellipse([gx - gr, ey - gr, gx + gr, ey + gr], outline=L.line, width=int(3 * s))
    if L.glasses:
        d.line([(ex - gap + 0.21 * r, ey), (ex + gap - 0.21 * r, ey)], fill=L.line, width=int(3 * s))


def _beard(d, c, r, p, f, L, s, o):
    ang = math.radians(-(p.lean + p.head) * f)
    cx, cy = c
    pts = [(cx + r * 1.0 * math.cos(a), cy + r * 1.0 * math.sin(a)) for a in [math.radians(x) for x in range(28, 153, 6)]]
    pts += [(cx - r * 0.82, cy + r * 0.47), (cx - r * 0.25, cy + r * 0.40), (cx + r * 0.25, cy + r * 0.40), (cx + r * 0.82, cy + r * 0.47)]
    d.polygon(_rot(pts, c, ang), fill=L.beard, outline=L.line, width=int(o * 0.7))


def _hair(d, c, r, p, f, L, s, o):
    ang = math.radians(-(p.lean + p.head) * f)
    cx, cy = c
    pts = [(cx + r * 1.03 * math.cos(a), cy - r * 1.03 * math.sin(a)) for a in [math.radians(x) for x in range(22, 159, 6)]]
    fringe = cy - 0.36 * r
    pts += [(cx - r * 0.93, fringe), (cx - r * 0.35, fringe - 0.06 * r), (cx + r * 0.1 * f, fringe - 0.16 * r),
            (cx + r * 0.6, fringe - 0.04 * r), (cx + r * 0.93, fringe)][::-1]
    d.polygon(_rot(pts, c, ang), fill=L.hair, outline=L.line, width=int(o * 0.8))


def _beanie(d, c, r, p, f, L, s, o):
    ang = math.radians(-(p.lean + p.head) * f)
    cx, cy = c
    band_y = cy - 0.30 * r
    cap = [(cx + r * 1.04 * math.cos(a), band_y - r * 0.98 * math.sin(a)) for a in [i * math.pi / 24 for i in range(25)]]
    band = [(cx - r * 1.08, band_y - 0.05 * r), (cx + r * 1.08, band_y - 0.05 * r),
            (cx + r * 1.10, band_y + 0.30 * r), (cx - r * 1.10, band_y + 0.30 * r)]
    cap, band = _rot(cap, c, ang), _rot(band, c, ang)
    d.polygon(cap, fill=L.hat, outline=L.line, width=int(o))
    d.polygon(band, fill=L.hat_dark, outline=L.line, width=int(o))
    top = _rot([(cx, band_y - r * 1.02)], c, ang)[0]
    pr = 0.24 * r
    d.ellipse([top[0] - pr - o, top[1] - pr - o, top[0] + pr + o, top[1] + pr + o], fill=L.line)
    d.ellipse([top[0] - pr, top[1] - pr, top[0] + pr, top[1] + pr], fill=L.hat)


def place(frame: Image.Image, p: Pose, L: Look, f: int, x: float, ground: float):
    """Cola o personagem com os pés no chão (ou no ar, no pulo) e uma sombra embaixo."""
    layer, (hx, hy) = draw_character(p, L, f)
    j = skeleton(p, L, f)
    foot = max(j["ft_b"][1], j["ft_f"][1]) / SS + 6 * L.scale
    hip_y = ground - foot - p.lift
    px, py = x + p.dx - hx, hip_y - hy
    sh = max(0.35, 1 - p.lift / 260)
    sw = 70 * L.scale * sh
    sd = ImageDraw.Draw(frame, "RGBA")
    sd.ellipse([x - sw, ground - 9 * sh, x + sw, ground + 9 * sh], fill=(10, 20, 40, int(70 * sh)))
    frame.alpha_composite(layer, (int(round(px)), int(round(py))))


# ---------------------------------------------------------------- cenário ----
def antarctic_scene(seed: int = 3):
    """Cenário de teste (na fábrica, seria a imagem da IA): planalto de gelo à noite, aurora e estação."""
    rnd = random.Random(seed)
    sky = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(sky)
    hz = int(H * 0.70)
    for y in range(H):
        if y < hz:
            k = y / hz
            col = (int(8 + 22 * k), int(12 + 30 * k), int(34 + 50 * k))
        else:
            k = (y - hz) / (H - hz)
            col = (int(150 + 60 * k), int(172 + 52 * k), int(205 + 35 * k))
        d.line([(0, y), (W, y)], fill=col)
    for _ in range(260):
        x, y = rnd.randrange(W), rnd.randrange(int(hz * 0.95))
        b = rnd.randint(140, 255)
        rr = rnd.choice([1, 1, 1, 2])
        d.ellipse([x, y, x + rr, y + rr], fill=(b, b, b))
    # estação: três módulos laranja sobre pernas
    sx, sy = int(W * 0.66), hz + 40
    for i, (bw, bh) in enumerate([(230, 110), (190, 120), (210, 105)]):
        x = sx + sum([230, 190, 210][:i]) + i * 14
        top = sy - bh - 46
        for lx in (x + 20, x + bw - 30):
            d.rectangle([lx, sy - 46, lx + 9, sy + 6], fill=(40, 44, 52))
        d.rounded_rectangle([x, top, x + bw, sy - 46], radius=10, fill=(214, 92, 22), outline=(25, 25, 30), width=4)
        for wx in range(x + 22, x + bw - 30, 52):
            d.rectangle([wx, top + 26, wx + 28, top + 52], fill=(255, 214, 120), outline=(25, 25, 30), width=3)
    ax = sx + 120
    d.line([(ax, sy - 160), (ax, sy - 420)], fill=(40, 44, 52), width=6)
    d.line([(ax - 40, sy - 380), (ax + 40, sy - 380)], fill=(40, 44, 52), width=4)
    d.rectangle([sx - 120, sy - 70, sx - 40, sy + 4], fill=(170, 175, 182), outline=(25, 25, 30), width=3)

    # aurora: faixa larga pré-desfocada, deslizada aos poucos a cada quadro
    au = Image.new("RGBA", (W * 2, int(H * 0.6)), (0, 0, 0, 0))
    ad = ImageDraw.Draw(au)
    for band in range(4):
        base = 120 + band * 70
        amp, ph = rnd.uniform(40, 80), rnd.uniform(0, 6.28)
        pts = [(x, base + amp * math.sin(x / 260 + ph) + 25 * math.sin(x / 90 + ph * 2)) for x in range(0, W * 2, 12)]
        for k in range(14):
            a = int(70 - k * 4.5)
            ad.line([(x, y + k * 9) for x, y in pts], fill=(70, 255, 160, max(a, 0)), width=16)
    au = au.filter(ImageFilter.GaussianBlur(18))
    return sky, au, hz


class Snow:
    def __init__(self, n=140, seed=5):
        r = random.Random(seed)
        self.p = [[r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 2.4), r.uniform(18, 60), r.uniform(0, 6.28)] for _ in range(n)]

    def draw(self, d: ImageDraw.ImageDraw, t: float, dt: float):
        for q in self.p:
            q[1] += q[3] * dt
            q[0] += math.sin(t * 0.8 + q[4]) * 12 * dt - 18 * dt
            if q[1] > H:
                q[1], q[0] = -5, (q[0] + 400) % W
            if q[0] < 0:
                q[0] += W
            rr = q[2]
            d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=(255, 255, 255, 200))


def badge(d: ImageDraw.ImageDraw, text: str, font_path: str):
    font = ImageFont.truetype(font_path, int(H / 17))
    x, y = int(W * 0.035), int(H * 0.05)
    l, t, r, b = d.textbbox((x, y), text, font=font)
    pad = 22
    d.rectangle([l - pad, t - pad, r + pad, b + pad], fill=(20, 22, 28, 225))
    d.text((x, y), text, font=font, fill="white")


# ---------------------------------------------------------------- cena da fábrica
def _actor_timeline(a: dict, seconds: float) -> Timeline:
    """actor = {who, action, x, to?, facing?, beats?: [[action, segundos, x_final?], ...]}."""
    x = float(a.get("x", 0.5))
    face = int(a.get("facing") or (1 if float(a.get("to", x)) >= x else -1))
    beats, t = [], float(a.get("delay", 0))
    if t > 0:
        beats.append(Beat(0, t, "idle", x, facing=face))
    if a.get("beats"):
        for i, b in enumerate(a["beats"]):
            act, dur = b[0], float(b[1]) if len(b) > 1 else seconds
            end = seconds if i == len(a["beats"]) - 1 else min(seconds, t + dur)
            x1 = float(b[2]) if len(b) > 2 and b[2] is not None else None
            if x1 is not None and abs(x1 - x) > 1e-3:
                face = 1 if x1 > x else -1
            beats.append(Beat(t, max(end, t + 0.05), act if act in ACTIONS else "idle", x, x1, face))
            x = x1 if x1 is not None else x
            t = end
            if t >= seconds:
                break
    else:
        act = a.get("action", "idle")
        to = a.get("to")
        beats.append(Beat(t, max(seconds, t + 0.05), act if act in ACTIONS else "idle", x,
                          float(to) if to is not None else None, face))
    if beats[-1].end < seconds:
        beats[-1].end = seconds
    return Timeline(beats, seed=sum(map(ord, str(a.get("who", "x")))) * 7 + int(x * 100))


def render_scene(image, out, seconds: float, actors: list[dict], overlay: str | None, cfg: dict | None,
                 seed: int = 0, fx: str | None = None):
    """Plano da fábrica: cenário da IA (sem personagem) com câmera lenta + stickmen animados por cima."""
    from .settings import settings
    from . import media
    cfg = cfg or {}
    w, h, fps = settings.width, settings.height, settings.fps
    n = max(1, round(seconds * fps))
    zoom = float(cfg.get("stick_zoom", 0.06))
    bg = Image.open(image).convert("RGB")
    bw, bh = int(w * (1 + zoom)), int(h * (1 + zoom))
    sc = max(bw / bg.width, bh / bg.height)
    bg = bg.resize((int(bg.width * sc) + 1, int(bg.height * sc) + 1), Image.LANCZOS)
    bg = bg.crop(((bg.width - bw) // 2, (bg.height - bh) // 2, (bg.width - bw) // 2 + bw, (bg.height - bh) // 2 + bh))
    rnd = random.Random(seed)
    sx, sy = rnd.choice([(0, 0), (1, 0), (0, 1), (1, 1), (0.5, 0.5)])
    ex, ey = 1 - sx, 1 - sy
    base_scale = float(cfg.get("stick_scale", 1.45))
    cast = []
    for a in (actors or [])[:5]:
        L = look_for(a.get("who", "you"), base_scale * float(a.get("scale", 1.0)))
        cast.append((a, L, _actor_timeline(a, seconds), h * float(a.get("y", cfg.get("stick_ground", 0.93)))))
    cast.sort(key=lambda c: c[3])  # quem está mais embaixo (mais perto) é desenhado por último
    snow = Snow(n=110, seed=seed) if (fx or cfg.get("fx")) == "snow" else None
    font = settings.font_path
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", *media._x264(), "-an", str(out)],
                            stdin=subprocess.PIPE)
    try:
        for i in range(n):
            t = i / fps
            u = _ease(i / max(n - 1, 1))
            ox = int((bw - w) * (sx + (ex - sx) * u))
            oy = int((bh - h) * (sy + (ey - sy) * u))
            frame = bg.crop((ox, oy, ox + w, oy + h)).convert("RGBA")
            for a, L, tl, ground in cast:
                p, x, f = tl.at(t)
                place(frame, p, L, f, x * w, ground)
            d = ImageDraw.Draw(frame, "RGBA")
            if snow:
                snow.draw(d, t, 1 / fps)
            if overlay:
                if cfg.get("hud", "badge") == "badge":
                    badge(d, overlay, font)
                else:
                    _top_text(d, overlay, font, w)
            proc.stdin.write(frame.convert("RGB").tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode:
        raise RuntimeError(f"stickman: ffmpeg saiu com {proc.returncode}")
    return out


def _top_text(d, text, font_path, w):
    font = ImageFont.truetype(font_path, int(H / 14))
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    x = (w - (r - l)) // 2
    d.text((x, int(H * 0.06)), text, font=font, fill="white", stroke_width=5, stroke_fill="black")


# ---------------------------------------------------------------- render -----
def render_pilot(out: str = "/tmp/stickman-piloto.mp4",
                 font_path: str = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"):
    sky, aurora, hz = antarctic_scene()
    ground = H * 0.93
    L = Look(scale=1.45)
    tl = Timeline([
        Beat(0.0, 3.2, "walk", 0.10, 0.40),
        Beat(3.2, 4.4, "idle", 0.40),
        Beat(4.4, 6.6, "point_up", 0.40),
        Beat(6.6, 8.4, "shiver", 0.40),
        Beat(8.4, 9.5, "jump", 0.40, params={"dur": 1.1}),
        Beat(9.5, 11.5, "wave", 0.40),
    ])
    total = tl.beats[-1].end
    snow = Snow()
    proc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                             "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out],
                            stdin=subprocess.PIPE)
    n = int(total * FPS)
    for i in range(n):
        t = i / FPS
        frame = sky.convert("RGBA")
        off = int((t * 28) % W)
        glow = 0.75 + 0.25 * math.sin(t * 1.3)
        band = aurora.crop((off, 0, off + W, aurora.height))
        if glow < 1:
            a = band.getchannel("A").point(lambda v: int(v * glow))
            band.putalpha(a)
        frame.alpha_composite(band, (0, 0))
        p, x, f = tl.at(t)
        place(frame, p, L, f, x * W, ground)
        d = ImageDraw.Draw(frame, "RGBA")
        snow.draw(d, t, 1 / FPS)
        badge(d, "DIA 171", font_path)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    return out


if __name__ == "__main__":
    print(render_pilot())

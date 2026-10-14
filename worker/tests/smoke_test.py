"""Teste de fumaça do worker, sem rede e sem provedores de IA.

Gera imagens e áudio sintéticos, roda assemble, shorts, thumbnail e checks
direto pela função da fila, com armazenamento local.

    STORAGE=local LOCAL_STORAGE_ROOT=/tmp/fab WORK_DIR=/tmp/fab-work \
    python -m tests.smoke_test ../contracts/examples/demo.video_spec.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from app import storage, tasks
from app.settings import settings

PALETTE = [(31, 111, 235), (242, 183, 5), (46, 160, 67), (207, 34, 46), (130, 80, 223)]


def fake_image(path: Path, i: int, label: str) -> Path:
    img = Image.new("RGB", (1600, 900), PALETTE[i % len(PALETTE)])
    d = ImageDraw.Draw(img)
    for k in range(0, 1600, 80):
        d.line([(k, 0), (k + 400, 900)], fill=(255, 255, 255), width=3)
    d.ellipse((600, 250, 1000, 650), fill=(20, 20, 20))
    d.text((40, 40), label, fill=(255, 255, 255))
    img.save(path)
    return path


def fake_voice(path: Path, text: str, wps: float = 2.6) -> list[dict]:
    """Áudio tonal com 'sílabas' + tempos de palavra plausíveis."""
    words = text.split()
    dur = len(words) / wps + 0.4
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"sine=f=220:d={dur:.2f},volume='0.6*(0.6+0.4*sin(2*PI*5*t))':eval=frame",
                    "-ar", "48000", str(path)], check=True)
    out, t = [], 0.2
    for w in words:
        step = 1 / wps
        out.append({"w": w, "s": round(t, 3), "e": round(t + step * 0.85, 3)})
        t += step
    return out


def main(spec_path: str) -> None:
    storage.ensure_bucket()
    spec = json.loads(Path(spec_path).read_text("utf-8"))
    vid = spec["video_id"]
    tmp = settings.work_dir / "fixtures"
    tmp.mkdir(parents=True, exist_ok=True)

    for b in spec["blocks"]:
        wav = tmp / f"{b['block_id']}.wav"
        words = fake_voice(wav, b["narration"])
        b["audio"] = {"url": storage.upload(wav, f"videos/{vid}/audio/{wav.name}"), "duration_s": None, "words": words}
        for s in b["shots"]:
            img = fake_image(tmp / f"{s['shot_id']}.png", s["order"], s["shot_id"])
            s["image"] = {"url": storage.upload(img, f"videos/{vid}/images/{img.name}"), "provider": "fake"}

    sp = tmp / "spec.json"
    sp.write_text(json.dumps(spec), "utf-8")
    spec_url = storage.upload(sp, f"videos/{vid}/video_spec.json")

    res = tasks.execute({"type": "assemble", "video_id": vid, "input": {"spec_url": spec_url, "loudness_lufs": -14}})
    out = res["result"]
    print("assemble:", json.dumps(out["outputs"], indent=1))
    for c in out["checks"]:
        print(f"  check {c['name']:<16} {'OK' if c['passed'] else 'FALHOU'}  {c['detail']}")

    total = out["outputs"]["duration_s"]
    cand = [{"start_s": 0.0, "end_s": min(total, 20.0), "hook": "teste"}]
    sh = tasks.execute({"type": "shorts", "video_id": vid,
                        "input": {"final_url": out["outputs"]["final_url"], "words": out["words"], "candidates": cand}})
    print("shorts:", sh["result"])

    bg = fake_image(tmp / "thumb_bg.png", 4, "")
    bg_url = storage.upload(bg, f"videos/{vid}/images/thumb_bg.png")
    th = tasks.execute({"type": "thumbnail", "video_id": vid,
                        "input": {"options": [{"image_url": bg_url, "lines": ["DISH PIT", "TO MICHELIN"]}]}})
    print("thumbnail:", th["result"])

    ck = tasks.execute({"type": "checks", "video_id": vid,
                        "input": {"media_url": b["audio"]["url"], "stage": "voice"}})
    print("checks voz:", [(c["name"], c["passed"]) for c in ck["result"]["checks"]])


if __name__ == "__main__":
    main(sys.argv[1])

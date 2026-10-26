"""One-command orchestrator.  This is what GitHub Actions runs.

    python tools/render.py                 # full 1080p30 render + edit + QA
    python tools/render.py --quality m    # fast local 720p30 preview
    python tools/render.py --lightweight  # skip vertical + GIF

Pipeline (all offline in CI):

  storyboard.json
        |
        +--> [assets] committed edge-tts clips -> voice.wav (numpy mix)
        +--> [assets] procedural music        -> music.wav
        +--> [manim]  src/main.py             -> silent.mp4
        +--> [edit]   ASS captions + ducking + loudnorm + grade -> MP4 set
        +--> [qa]     ffprobe + loudness + ffmpeg-skill delivery gate
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.config import BUILD, storyboard  # noqa: E402

from tools import build_music, build_voice  # noqa: E402


def step(n, total, label):
    print(f"\n\033[1;36m[{n}/{total}] {label}\033[0m", flush=True)


def ensure_assets(sb):
    step(1, 5, "voice track + music (offline, deterministic)")
    mix, words = build_voice.offline_load()
    build_voice.write_derived(sb, words)
    build_voice.mix_voice_track(sb, mix)
    build_music.build(sb["duration"], os.path.join(BUILD, "music.wav"))
    print("  words:", len(words), " voice.wav + music.wav ready")


def ensure_manim(quality, fps, silent_arg):
    if silent_arg:
        return silent_arg
    step(2, 5, f"Manim 2D character animation (quality={quality}, fps={fps})")
    for stale in glob.glob(os.path.join(BUILD, "media/videos/main/*/silent.mp4")):
        os.remove(stale)
    env = dict(os.environ, PYTHONPATH=ROOT)
    subprocess.run(
        [sys.executable, "-m", "manim", "render", "-q", quality,
         "--fps", str(fps), "-o", "silent.mp4",
         "--media_dir", os.path.join(BUILD, "media"),
         "src/main.py", "ExplainerScene"],
        cwd=ROOT, env=env, check=True,
    )
    found = sorted(glob.glob(os.path.join(BUILD, "media/videos/main/*/silent.mp4")))
    if not found:
        raise SystemExit("Manim did not produce silent.mp4")
    return found[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quality", default=os.environ.get("HOOSHA_QUALITY", "h"),
                    choices=["l", "m", "h", "p"])
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--silent", default=None, help="reuse an existing Manim render")
    ap.add_argument("--lightweight", action="store_true")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    args = ap.parse_args()

    sb = storyboard()
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "rendered"), exist_ok=True)

    ensure_assets(sb)
    silent = ensure_manim(args.quality, args.fps, args.silent)

    w = args.width or (854 if args.quality == "l" else
                       1280 if args.quality == "m" else 1920)
    h = args.height or (480 if args.quality == "l" else
                        720 if args.quality == "m" else 1080)

    step(3, 5, "edit: ASS captions, audio mix, ducking, -14 LUFS, delivery set")
    cmd = [sys.executable, os.path.join(ROOT, "tools", "edit.py"),
           "--silent", silent, "--width", str(w), "--height", str(h)]
    if args.lightweight:
        cmd.append("--lightweight")
    subprocess.run(cmd, cwd=ROOT, check=True)

    step(4, 5, "QA: ffprobe, loudness, ffmpeg-skill delivery gate")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "qa.py")],
                   cwd=ROOT, check=True)

    step(5, 5, "done")
    print("\nOpen rendered/explainer-1080p.mp4")


if __name__ == "__main__":
    main()

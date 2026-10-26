"""The editing / post-production layer.

Takes Manim's silent render and produces the finished films:

  * burned-in karaoke captions (ASS + Vazirmatn + complex RTL shaping)
  * voice-over + procedural music, side-chain ducked under speech
  * EBU R128 / -14 LUFS loudness, true peak -1 dBTP
  * subtle grade, fade in/out, exact 60.00 s trim
  * delivery set: 1080p master, 720p, 9:16 vertical, GIF preview,
    contact sheet, SRT, QA JSON

This is the "best editing" step: deterministic FFmpeg, no GUI, no cloud,
no human timeline.  Every decision lives in code and can be reviewed in git.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.config import (  # noqa: E402
    ASS_FILE, BUILD, FONTS, RENDERED, SRT_FILE, ffmpeg_binaries, storyboard,
)

FF, FP = ffmpeg_binaries()


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd)[:400])
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def shaping_supported() -> bool:
    try:
        out = subprocess.run(
            [FF, "-hide_banner", "-h", "filter=ass"],
            capture_output=True, text=True,
        ).stdout
        return "shaping" in out
    except Exception:
        return False


def ass_filter(w: int, h: int) -> str:
    """Build the ASS burn-in filter, with the RTL-safe complex shaper."""
    base = f"ass={ASS_FILE}:fontsdir={FONTS}"
    if shaping_supported():
        base += ":shaping=complex"
    return base


def make_master(silent: str, voice: str, music: str, out: str, sb, w, h):
    dur = sb["duration"]
    af = ass_filter(w, h)
    fc = (
        f"[0:v]trim=0:{dur},setpts=PTS-STARTPTS,fps={sb['fps']},"
        f"scale={w}:{h}:flags=lanczos,{af},"
        f"eq=contrast=1.04:saturation=1.07:brightness=0.004,"
        f"fade=t=in:st=0:d=0.55,fade=t=out:st={dur-0.8:.2f}:d=0.8,"
        f"format=yuv420p[v];"
        f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"volume=1.0,asplit=2[voice_main][voice_sc];"
        f"[2:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"volume=0.80[musicsrc];"
        f"[musicsrc][voice_sc]sidechaincompress=threshold=0.025:ratio=9:"
        f"attack=15:release=420[ducked];"
        f"[voice_main][ducked]amix=inputs=2:duration=first:normalize=0[mix];"
        f"[mix]loudnorm=I=-14:TP=-1.0:LRA=11,"
        f"afade=t=in:st=0:d=0.45,afade=t=out:st={dur-0.8:.2f}:d=0.8,"
        f"atrim=0:{dur},asetpts=PTS-STARTPTS[a]"
    )
    cmd = [
        FF, "-y", "-hide_banner", "-loglevel", "error",
        "-i", silent, "-i", voice, "-i", music, "-i", SRT_FILE,
        "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-map", "3:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(sb["fps"]),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-c:s", "mov_text", "-metadata:s:s:0", "language=fas",
        "-movflags", "+faststart", "-t", str(dur), out,
    ]
    try:
        r = run(cmd)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr[-3000:])
        # Some distro FFmpeg builds expose 'ass' but not the 'shaping' option.
        # Retry with a plain ASS burn-in so the render still succeeds.
        print("  ! retrying without explicit shaping=complex")
        af2 = f"ass={ASS_FILE}:fontsdir={FONTS}"
        fc2 = fc.replace(af, af2)
        cmd[cmd.index(fc)] = fc2
        run(cmd)
    print("  master ->", out, os.path.getsize(out), "bytes")


def make_720(master, out):
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", master,
         "-vf", "scale=1280:720:flags=lanczos",
         "-map", "0:v:0", "-map", "0:a:0", "-map", "0:s?",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-c:s", "copy",
         "-movflags", "+faststart", out])


def make_vertical(master, out, dur):
    vf = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=28:2,eq=brightness=-0.08[bgb];"
        "[fg]scale=1080:-2:flags=lanczos[fgv];"
        "[bgb][fgv]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", master,
         "-filter_complex", vf, "-map", "[v]", "-map", "0:a?", "-map", "0:s?",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-c:s", "copy", "-t", str(dur),
         "-movflags", "+faststart", out])


def make_gif(master, out):
    vf = ("fps=12,scale=480:-1:flags=lanczos,split[s0][s1];"
          "[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3")
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", "2", "-t", "6",
         "-i", master, "-vf", vf, "-loop", "0", out])


def make_contact_sheet(master, out):
    vf = "fps=1/10,scale=384:-1:flags=lanczos,tile=3x2:padding=8:margin=8:color=0x0B1220"
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", master,
         "-vf", vf, "-frames:v", "1", out])


def probe(path):
    out = subprocess.run(
        [FP, "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--silent", default=None, help="Manim's silent MP4")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--lightweight", action="store_true",
                    help="skip the 9:16 vertical and GIF exports (fast local preview)")
    args = ap.parse_args()

    sb = storyboard()
    w = args.width or sb["width"]
    h = args.height or sb["height"]
    os.makedirs(RENDERED, exist_ok=True)
    os.makedirs(BUILD, exist_ok=True)

    silent = args.silent
    if silent is None:
        import glob
        found = sorted(glob.glob(os.path.join(BUILD, "media/videos/main/*/silent.mp4")))
        if not found:
            raise SystemExit("No silent render found. Run `make render` first.")
        silent = found[-1]
    voice = os.path.join(BUILD, "voice.wav")
    music = os.path.join(BUILD, "music.wav")
    for p in (silent, voice, music, ASS_FILE):
        if not os.path.exists(p):
            raise SystemExit(f"Missing input: {p}  (run: make voice music manim)")

    master = os.path.join(RENDERED, "explainer-1080p.mp4")
    print("[1/6] master edit (captions + mix + grade + loudness)")
    make_master(silent, voice, music, master, sb, w, h)
    print("[2/6] 720p delivery")
    make_720(master, os.path.join(RENDERED, "explainer-720p.mp4"))
    print("[3/6] 9:16 vertical")
    if not args.lightweight:
        make_vertical(master, os.path.join(RENDERED, "explainer-vertical.mp4"),
                      sb["duration"])
        print("[4/6] GIF preview")
        make_gif(master, os.path.join(RENDERED, "preview.gif"))
    else:
        print("[3/6] + [4/6] skipped (--lightweight)")
    print("[5/6] contact sheet + SRT")
    make_contact_sheet(master, os.path.join(RENDERED, "contact-sheet.png"))
    shutil.copyfile(SRT_FILE, os.path.join(RENDERED, "explainer.srt"))
    print("[6/6] probe")
    info = probe(master)
    print(json.dumps({
        "file": os.path.basename(master),
        "duration": float(info["format"]["duration"]),
        "size_bytes": int(info["format"]["size"]),
        "streams": [
            {k: s.get(k) for k in ("codec_type", "codec_name", "width", "height",
                                   "r_frame_rate", "sample_rate", "channels")}
            for s in info["streams"]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

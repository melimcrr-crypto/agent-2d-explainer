"""Post-render quality assurance.

Checks the *actual rendered pixels and audio*, not our intentions:

  * duration / fps / resolution / codecs / audio stream (ffprobe)
  * integrated loudness and true peak (ffmpeg loudnorm measurement)
  * a caption frame is extracted so a human/agent can eyeball RTL shaping
  * if available, runs ffmpeg-skill's ``check.py`` delivery gate

Writes ``rendered/qa.json``.  Exits 1 on a hard FAIL.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.config import RENDERED, ffmpeg_binaries, storyboard  # noqa: E402

FF, FP = ffmpeg_binaries()


def probe(path):
    out = subprocess.run(
        [FP, "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def measure_loudness(path):
    r = subprocess.run(
        [FF, "-hide_banner", "-nostats", "-i", path,
         "-map", "0:a:0", "-af",
         "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    tail = r.stderr
    hit = re.findall(r"\{\s*\"input_i\".*?\}", tail, re.S)
    if not hit:
        return None
    try:
        return json.loads(hit[-1])
    except Exception:
        return None


def caption_frame(master, out):
    # grab a frame in the middle of scene 2 -- captions should be visible
    subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", "-ss", "11.5",
         "-i", master, "-frames:v", "1", out],
        capture_output=True,
    )


def skill_check(master):
    candidates = [
        os.path.join(ROOT, "build", "ffmpeg-skill", "scripts", "check.py"),
        "/tmp/ffmpeg-skill/scripts/check.py",
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            # check.py shells out to `ffprobe`; make sure the bundled static
            # build is visible even on machines without a system FFmpeg.
            env = dict(os.environ)
            bins = {os.path.dirname(FF), os.path.dirname(FP)}
            env["PATH"] = os.pathsep.join(sorted(bins)) + os.pathsep + env.get("PATH", "")
            r = subprocess.run(
                [sys.executable, path, master, "--platform", "youtube",
                 "--json-brief"],
                capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(path)),
                timeout=180, env=env,
            )
            # check.py prints a human header before the JSON blob; keep both.
            parsed = None
            raw = r.stdout
            brace = raw.find("{")
            if brace >= 0:
                try:
                    parsed = json.loads(raw[brace:])
                except Exception:
                    parsed = None
            return {"tool": "kajisho5/ffmpeg-skill check.py",
                    "exit": r.returncode,
                    "report": parsed,
                    "human": raw[:brace].strip() if brace > 0 else "",
                    "stderr": r.stderr[-500:]}
        except Exception as exc:
            return {"error": str(exc)}
    return {"skipped": "ffmpeg-skill not checked out"}


def main():
    sb = storyboard()
    master = os.path.join(RENDERED, "explainer-1080p.mp4")
    if not os.path.exists(master):
        raise SystemExit("missing " + master)

    info = probe(master)
    fmt = info["format"]
    vids = [s for s in info["streams"] if s["codec_type"] == "video"]
    auds = [s for s in info["streams"] if s["codec_type"] == "audio"]
    v = vids[0] if vids else {}
    dur = float(fmt["duration"])

    loud = measure_loudness(master)
    li = float(loud["input_i"]) if loud and loud.get("input_i") not in (None, "-inf") else None
    tp = float(loud["input_tp"]) if loud and loud.get("input_tp") not in (None, "-inf") else None

    rows = []

    def row(name, ok, value, expected, hard=True):
        rows.append({"check": name, "status": "PASS" if ok else ("FAIL" if hard else "WARN"),
                     "value": value, "expected": expected})

    row("duration", abs(dur - sb["duration"]) <= 0.20, round(dur, 3),
        f"{sb['duration']} +/- 0.20 s")
    valid_sizes = {(854, 480), (1280, 720), (1920, 1080)}
    row("resolution", (v.get("width"), v.get("height")) in valid_sizes,
        f"{v.get('width')}x{v.get('height')}",
        "854x480 (preview) / 1280x720 / 1920x1080")
    row("fps", str(sb["fps"]) in (v.get("r_frame_rate") or ""),
        v.get("r_frame_rate"), str(sb["fps"]))
    row("video codec", v.get("codec_name") == "h264", v.get("codec_name"), "h264")
    row("pixel format", v.get("pix_fmt") == "yuv420p", v.get("pix_fmt"), "yuv420p")
    row("audio stream", len(auds) >= 1, len(auds), ">= 1")
    if auds:
        row("audio codec", auds[0].get("codec_name") == "aac",
            auds[0].get("codec_name"), "aac")
    if li is not None:
        row("integrated loudness", -15.5 <= li <= -12.5, li, "-14 LUFS +/- 1.5")
    if tp is not None:
        row("true peak", tp <= -0.8, tp, "<= -0.8 dBTP")

    caption_frame(master, os.path.join(RENDERED, "caption-check.png"))
    skill = skill_check(master)

    report = {
        "file": os.path.basename(master),
        "duration": dur,
        "size_bytes": int(fmt["size"]),
        "video": {k: v.get(k) for k in ("codec_name", "width", "height",
                                        "r_frame_rate", "pix_fmt", "nb_frames")},
        "audio": [{k: a.get(k) for k in ("codec_name", "sample_rate", "channels")}
                  for a in auds],
        "loudness": {"input_i": li, "input_tp": tp,
                     "input_lra": loud.get("input_lra") if loud else None,
                     "input_thresh": loud.get("input_thresh") if loud else None},
        "checks": rows,
        "ffmpeg_skill": skill,
        "deliverables": sorted(
            f for f in os.listdir(RENDERED) if not f.startswith(".")
        ),
    }
    with open(os.path.join(RENDERED, "qa.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print("\n=== QA ===")
    for r in rows:
        print(f"  {r['status']:<4} {r['check']:<22} {r['value']}")
    print("  deliverables:", ", ".join(report["deliverables"]))
    bad = [r for r in rows if r["status"] == "FAIL"]
    if bad:
        print(f"\n{len(bad)} hard FAIL(s)")
        sys.exit(1)
    print("\nall hard checks passed")


if __name__ == "__main__":
    main()

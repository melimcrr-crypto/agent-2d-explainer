"""Build the Persian voice-over and every timing artifact.

Online mode (default)
---------------------
Uses ``edge-tts`` (free, no API key, Microsoft neural voices) to synthesise one
MP3 per scene, and captures **WordBoundary** events -- real word-level
timestamps -- which drive the karaoke captions and the character's mouth.

    python tools/build_voice.py

Offline / CI mode
-----------------
The synthesized MP3s and all derived timing files are committed to the repo,
so GitHub Actions needs **no network and no TTS service**:

    python tools/build_voice.py --offline

That simply re-mixes the committed clips and re-writes ASS/SRT/visemes from the
committed ``captions/mix.json`` + ``captions/words.json``.

Outputs
-------
assets/audio/voice_NN_<scene>.mp3   small, committed (source audio)
captions/mix.json                   clip -> absolute start offset
captions/words.json                 every word with absolute start/end
captions/lines.json                 words grouped into readable caption lines
captions/fa.ass                     karaoke ASS (RTL, Vazirmatn, shaping=complex)
captions/fa.srt                     plain SRT (soft-subtitle deliverable)
captions/visemes.json               word spans for the Manim mouth updater
build/voice.wav                     mixed, silence-padded 60 s voice track
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.config import (  # noqa: E402
    AUDIO, BUILD, CAPTIONS, ffmpeg_binaries, storyboard,
)

MIX_JSON = os.path.join(CAPTIONS, "mix.json")
WORDS_JSON = os.path.join(CAPTIONS, "words.json")
LINES_JSON = os.path.join(CAPTIONS, "lines.json")
SRT_FILE = os.path.join(CAPTIONS, "fa.srt")
ASS_FILE = os.path.join(CAPTIONS, "fa.ass")
VISEMES = os.path.join(CAPTIONS, "visemes.json")
VOICE_TRACK = os.path.join(BUILD, "voice.wav")

SR = 48000
LEAD = 0.38           # seconds of breathing room before each scene's voice
RATE_LADDER = ["+6%", "+14%", "+22%", "+32%", "+44%", "+55%"]


# --------------------------------------------------------------------------
# ffmpeg helpers
# --------------------------------------------------------------------------
def probe_duration(path: str) -> float:
    _, fp = ffmpeg_binaries()
    out = subprocess.run(
        [fp, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def decode_pcm(path: str) -> np.ndarray:
    ff, _ = ffmpeg_binaries()
    raw = subprocess.run(
        [ff, "-v", "error", "-i", path, "-f", "f32le", "-acodec", "pcm_f32le",
         "-ac", "2", "-ar", str(SR), "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()


# --------------------------------------------------------------------------
# TTS
# --------------------------------------------------------------------------
async def synth(text: str, voice: str, rate: str, out_path: str):
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(out_path, "wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "s": chunk["offset"] / 1e7,
                    "e": (chunk["offset"] + chunk["duration"]) / 1e7,
                    "w": chunk["text"],
                })
    return words


def online_build(sb):
    import shutil

    voice = sb["voice"]
    os.makedirs(AUDIO, exist_ok=True)
    mix, all_words = [], []

    for i, scene in enumerate(sb["scenes"]):
        clip = os.path.join(AUDIO, f"voice_{i:02d}_{scene['id']}.mp3")
        rel = os.path.relpath(clip, ROOT).replace(os.sep, "/")
        budget = scene["duration"] - LEAD - 0.22
        chosen = None
        for rate in RATE_LADDER:
            words = asyncio.run(synth(scene["narration"], voice, rate, clip))
            d = probe_duration(clip)
            print(f"  {scene['id']:<8} rate={rate:<5} dur={d:5.2f}s  budget={budget:5.2f}s")
            if d <= budget:
                chosen = (rate, d, words)
                break
        if chosen is None:
            rate, d, words = RATE_LADDER[-1], probe_duration(clip), words
            print(f"  WARNING: {scene['id']} voice is {d:.2f}s > {budget:.2f}s; "
                  "shorten its narration in storyboard.json")
            chosen = (rate, d, words)
        rate, d, words = chosen
        at = scene["start"] + LEAD
        mix.append({"file": rel, "at": at, "duration": d, "scene": scene["id"], "rate": rate})
        for w in words:
            all_words.append({
                "s": round(at + w["s"], 4),
                "e": round(at + w["e"], 4),
                "w": w["w"],
                "scene": i,
            })
    all_words.sort(key=lambda w: w["s"])
    json.dump(mix, open(MIX_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(all_words, open(WORDS_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return mix, all_words


def offline_load():
    mix = json.load(open(MIX_JSON, encoding="utf-8"))
    words = json.load(open(WORDS_JSON, encoding="utf-8"))
    return mix, words


# --------------------------------------------------------------------------
# mixing (pure numpy -> fully deterministic, no filtergraph)
# --------------------------------------------------------------------------
def mix_voice_track(sb, mix, out_path=VOICE_TRACK):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    total = int(round(sb["duration"] * SR))
    buf = np.zeros((total, 2), dtype=np.float64)
    for item in mix:
        pcm = decode_pcm(os.path.join(ROOT, item["file"]))
        start = int(round(item["at"] * SR))
        end = min(total, start + len(pcm))
        if start >= total:
            continue
        buf[start:end] += pcm[: end - start]
    # gentle safety limiter, then int16
    peak = float(np.max(np.abs(buf))) or 1.0
    if peak > 0.97:
        buf *= 0.97 / peak
    pcm16 = (np.clip(buf, -1, 1) * 32767).astype("<i2")
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm16.tobytes())
    return out_path


# --------------------------------------------------------------------------
# caption line grouping
# --------------------------------------------------------------------------
BREAKERS = set(".!?؟؛،,:؛")


def group_lines(words, sb):
    lines, cur = [], []
    scene_ends = [s["start"] + s["duration"] for s in sb["scenes"]]

    def flush():
        if cur:
            lines.append({
                "start": round(cur[0]["s"] - 0.10, 3),
                "end": round(cur[-1]["e"] + 0.42, 3),
                "text": " ".join(w["w"] for w in cur),
                "words": list(cur),
            })
            cur.clear()

    for w in words:
        limit = scene_ends[w["scene"]] - 0.25
        too_long = cur and (w["e"] - cur[0]["s"] > 4.6 or len(cur) >= 7)
        cross_scene = cur and w["scene"] != cur[-1]["scene"]
        if too_long or cross_scene:
            flush()
        cur.append(w)
        if any(ch in BREAKERS for ch in w["w"]) and len(cur) >= 4:
            flush()
    flush()
    # never overlap the next line
    for i, line in enumerate(lines):
        line["start"] = max(0.0, line["start"])
        if i + 1 < len(lines):
            line["end"] = min(line["end"], lines[i + 1]["start"] - 0.02)
        line["end"] = max(line["end"], line["start"] + 0.4)
    return lines


def ts_ass(t):
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def ts_srt(t):
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


ASS_HEADER = """[Script Info]
Title: Housha - How an AI Agent Edits a Video (Persian, RTL)
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Vazirmatn,58,&H00FFFFFF,&H00B8A08A,&H00101520,&H90000000,-1,0,0,0,100,100,0,0,1,3.4,1.6,2,110,110,74,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(lines):
    out = [ASS_HEADER]
    for ln in lines:
        parts = [r"{\fad(150,150)}"]
        cursor = ln["start"]
        for w in ln["words"]:
            gap = w["s"] - cursor
            if gap > 0.02:
                parts.append(r"{\kf%d}" % max(1, round(gap * 100)))
            dur = max(4, round((w["e"] - w["s"]) * 100))
            parts.append(r"{\kf%d}%s " % (dur, w["w"].replace("{", "(").replace("}", ")")))
            cursor = w["e"]
        text = "".join(parts).strip()
        out.append(
            f"Dialogue: 0,{ts_ass(ln['start'])},{ts_ass(ln['end'])},Default,,0,0,0,,{text}\n"
        )
    open(ASS_FILE, "w", encoding="utf-8").write("".join(out))


def write_srt(lines):
    out = []
    for i, ln in enumerate(lines, 1):
        out.append(
            f"{i}\n{ts_srt(ln['start'])} --> {ts_srt(ln['end'])}\n{ln['text']}\n\n"
        )
    open(SRT_FILE, "w", encoding="utf-8").write("".join(out))


def write_derived(sb, words):
    os.makedirs(CAPTIONS, exist_ok=True)
    lines = group_lines(words, sb)
    json.dump(lines, open(LINES_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump([[w["s"], w["e"]] for w in words],
              open(VISEMES, "w", encoding="utf-8"), indent=1)
    write_ass(lines)
    write_srt(lines)
    # a soft-subtitle copy next to the final films
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="rebuild from committed MP3s/timings (no network)")
    args = ap.parse_args()

    os.makedirs(BUILD, exist_ok=True)
    sb = storyboard()
    if args.offline or os.environ.get("HOOSHA_OFFLINE") == "1":
        mix, words = offline_load()
        print("offline: using committed voice clips and timings")
    else:
        print("online: synthesising with edge-tts (fa-IR-DilaraNeural)")
        mix, words = online_build(sb)
    lines = write_derived(sb, words)
    mix_voice_track(sb, mix)
    print(f"\nwords={len(words)}  caption lines={len(lines)}  "
          f"voice track={VOICE_TRACK} ({sb['duration']:.1f}s)")


if __name__ == "__main__":
    main()

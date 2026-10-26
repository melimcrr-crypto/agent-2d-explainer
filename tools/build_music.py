"""Procedural, licence-free background music.

No samples, no downloads, no API keys, no randomness from the machine: a fixed
chord progression + a soft pulse + a sparse bell arpeggio, synthesised with
numpy.  Therefore the GitHub Actions render is byte-for-byte reproducible.

Output: build/music.wav (stereo, 32 kHz, exactly ``duration`` seconds).
"""

from __future__ import annotations

import os
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.config import BUILD, storyboard  # noqa: E402

SR = 32000

# Am7 - Fmaj7 - G6 - Em7 : calm, slightly curious, loops forever
CHORDS = [
    (220.00, 261.63, 329.63, 392.00),
    (174.61, 220.00, 261.63, 349.23),
    (196.00, 246.94, 293.66, 392.00),
    (164.81, 207.65, 246.94, 329.63),
]


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return np.sin(x * np.pi / 2.0) ** 2


def build(duration: float, out_path: str):
    n = int(round(duration * SR))
    t = np.arange(n, dtype=np.float64) / SR
    buf = np.zeros(n, dtype=np.float64)

    seg = duration / len(CHORDS)
    fade = 2.2
    for ci, chord in enumerate(CHORDS):
        start, end = ci * seg, (ci + 1) * seg
        w = smooth(np.minimum((t - start) / fade, (end - t) / fade))
        for k, f in enumerate(chord):
            vib = 0.55 * np.sin(2 * np.pi * (0.11 + 0.017 * k) * t)
            ph = 2 * np.pi * f * t + vib
            tone = (
                np.sin(ph)
                + 0.32 * np.sin(2 * ph + 0.4)
                + 0.11 * np.sin(3 * ph + 1.1)
            )
            buf += w * tone * (0.052 / len(chord))

    # soft low pulse on every other second
    phase = np.mod(t, 2.0)
    pulse = np.exp(-9.0 * phase) * np.sin(2 * np.pi * 58.0 * t)
    buf += pulse * 0.085

    # sparse bell arpeggio
    step = 0.75
    for j in range(int(duration / step)):
        at = j * step + 0.12
        idx = int(at / seg) % len(CHORDS)
        f = CHORDS[idx][(j * 3 + 1) % 4] * 2.0
        i0 = int(at * SR)
        i1 = min(n, i0 + int(0.42 * SR))
        if i0 >= n:
            break
        tt = t[i0:i1] - at
        env = np.exp(-8.0 * tt)
        bell = (
            np.sin(2 * np.pi * f * tt)
            + 0.30 * np.sin(2 * np.pi * f * 2.01 * tt)
        ) * env
        buf[i0:i1] += bell * 0.028

    # master envelope + gain
    env = smooth(t / 2.4) * smooth((duration - t) / 3.0)
    buf *= env * 0.82
    peak = float(np.max(np.abs(buf))) or 1.0
    buf *= min(1.0, 0.92 / peak)

    left = buf
    right = np.concatenate([np.zeros(int(0.009 * SR)), buf])[:n]
    stereo = np.stack([left, right], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_path


def main():
    sb = storyboard()
    out = os.path.join(BUILD, "music.wav")
    build(sb["duration"], out)
    print("music:", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()

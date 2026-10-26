"""Shared configuration for the Housha 2D explainer.

Everything visual is declared here or in ``storyboard.json`` so an agent can
restyle the whole film by editing one file.  No colours, fonts or sizes are
hard-coded inside the scene code.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
FONTS = os.path.join(ASSETS, "fonts")
AUDIO = os.path.join(ASSETS, "audio")
CAPTIONS = os.path.join(ROOT, "captions")
BUILD = os.path.join(ROOT, "build")
RENDERED = os.path.join(ROOT, "rendered")

FONT_REG = os.path.join(FONTS, "Vazirmatn-Regular.ttf")
FONT_BOLD = os.path.join(FONTS, "Vazirmatn-Bold.ttf")
FONT_FAMILY = "Vazirmatn"
FONT_MONO = "DejaVu Sans Mono"

STORYBOARD = os.path.join(ROOT, "storyboard.json")
VISEMES = os.path.join(CAPTIONS, "visemes.json")
ASS_FILE = os.path.join(CAPTIONS, "fa.ass")
SRT_FILE = os.path.join(CAPTIONS, "fa.srt")
VOICE_FULL = os.path.join(AUDIO, "voice_full.wav")
MUSIC = os.path.join(AUDIO, "music.wav")

# Manim's 16:9 frame is 14.222 x 8 logical units.  Kept as constants so the
# layout stays identical whether we render at 480p (preview) or 1080p (CI).
FRAME_W = 14.222
FRAME_H = 8.0

# Palette (mirrored in storyboard.json -> palette).
BG = "#0B1220"
PANEL = "#141F32"
PANEL_2 = "#1B2B45"
CYAN = "#4CC2FF"
VIOLET = "#8B7CFF"
AMBER = "#FFB86B"
GREEN = "#5CE1A6"
PINK = "#FF8FB1"
INK = "#EAF2FA"
MUTED = "#8AA0B8"
DARK = "#0D1728"


@lru_cache(maxsize=1)
def storyboard() -> dict:
    with open(STORYBOARD, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def visemes() -> list[tuple[float, float]]:
    """Word spans ``(start, end)`` in seconds, used to drive the mouth."""
    if not os.path.exists(VISEMES):
        return ()
    with open(VISEMES, encoding="utf-8") as fh:
        return tuple((float(a), float(b)) for a, b in json.load(fh))


def register_fonts() -> None:
    """Register the bundled Vazirmatn files with Pango (Manim's text engine).

    Pango performs the Arabic/Persian shaping and bidi reordering itself, so
    no manual ``arabic-reshaper`` / ``python-bidi`` step is needed for text
    drawn by Manim.  (Those are only used for the optional ASS/SRT export.)
    """
    from manim import register_font  # imported lazily so tools/ can run w/o manim

    for path in (FONT_REG, FONT_BOLD):
        if os.path.exists(path):
            try:
                register_font(path)
            except Exception:
                pass


def ffmpeg_binaries() -> tuple[str, str]:
    """Return (ffmpeg, ffprobe).

    Prefers a system FFmpeg (GitHub Actions installs one), and falls back to
    the bundled static build.  The static build is important for this project:
    it ships libass + HarfBuzz, which is what makes ``shaping=complex`` work
    for Persian captions.
    """
    import shutil

    ff = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    fp = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe")
    if ff and fp:
        return ff, fp
    try:
        from static_ffmpeg import run as _sfr

        sff, sfp = _sfr.get_or_fetch_platform_executables_else_raise()
        return ff or sff, fp or sfp
    except Exception:
        pass
    try:
        import imageio_ffmpeg

        return ff or imageio_ffmpeg.get_ffmpeg_exe(), fp or "ffprobe"
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("ffmpeg/ffprobe not found; see README") from exc

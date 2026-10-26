#!/usr/bin/env bash
# Local bootstrap.  System FFmpeg + Cairo/Pango are required for Manim.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get install -y ffmpeg libcairo2-dev libpango1.0-dev \
    libpangocairo-1.0-0 libglib2.0-dev pkg-config fontconfig || true
  sudo mkdir -p /usr/share/fonts/truetype/vazirmatn
  sudo cp assets/fonts/Vazirmatn-*.ttf /usr/share/fonts/truetype/vazirmatn/
  sudo fc-cache -f || true
fi

# Guarantee an FFmpeg with libass + HarfBuzz for shaping=complex.
eval "$(python -c "from static_ffmpeg import run; f,p=run.get_or_fetch_platform_executables_else_raise(); print('export FFMPEG_BIN='+f); print('export FFPROBE_BIN='+p)")"

echo "Ready. Run:  make preview     (fast)   or   make render  (full 1080p)"

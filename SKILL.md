---
name: housha-2d-explainer
description: Build or modify a 60-second Persian (RTL) 2D character explainer video entirely in code — Manim character animation, edge-tts Persian voiceover with word-level karaoke captions, procedural music, FFmpeg post-production, and a GitHub Actions render. Use when asked to create, change, restyle or debug an animated educational video, a 2D mascot, RTL captions, or a reproducible video render pipeline.
license: MIT
---

# Housha 2D Explainer

A deterministic, offline-capable, fully code-driven video pipeline. Give the
agent a topic and it edits `storyboard.json`; GitHub Actions renders the MP4.

## When to use

- "Make a 60-second animated explainer (Persian / RTL / 2D character)."
- "Change the narration / titles / colours / scenes."
- "Fix the RTL subtitles / lip sync / loudness / CI render."

## Read first

1. `AGENTS.md` — the full agent contract (read it, do not skip).
2. `storyboard.json` — the single source of truth.
3. `docs/ARCHITECTURE.md` — how the pieces connect.

## Standard workflow

```bash
# 0. inspect
python -m json.tool storyboard.json > /dev/null
cat captions/mix.json

# 1. edit storyboard.json: narration, title, kicker, duration, palette
#    INVARIANT: sum(durations) == 60.0 and starts are contiguous.

# 2. regenerate voice (requires network; free, no API key)
python tools/build_voice.py

# 3. verify locally (fast)
make preview

# 4. QA
python tools/qa.py
# open rendered/caption-check.png and rendered/contact-sheet.png

# 5. full render (or just push: CI does it)
make render
```

## Guardrails

- Never hard-code timing in `src/main.py`; `Beat` budgets come from the storyboard.
- `Housha.tick()` must use captured world-space anchors, never local coordinates.
- Do not call `self.add()`/`self.remove()` inside a Manim updater.
- Keep `assets/audio/voice_*.mp3` and `captions/*.json` committed — CI is offline.
- ASS captions need `shaping=complex` (libass + HarfBuzz). Fall back gracefully.
- No secrets in files or workflow yaml; CI uses only `GITHUB_TOKEN`.
- Do not use Pillow for Persian text without Raqm (double-shaping bug).

## Where things live

| Task | File |
| --- | --- |
| Script / timing / palette | `storyboard.json` |
| 2D character + secondary motion | `src/character.py` |
| Props / diagrams | `src/props.py` |
| Scene sequencing | `src/main.py` |
| TTS + karaoke ASS/SRT/visemes | `tools/build_voice.py` |
| Music | `tools/build_music.py` |
| Final edit (mix, duck, LUFS, exports) | `tools/edit.py` |
| Delivery gate | `tools/qa.py` |
| One-command orchestrator | `tools/render.py` |
| CI | `.github/workflows/render.yml` |

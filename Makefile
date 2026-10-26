.PHONY: help voice music manim edit qa render preview clean push

help:
	@echo "make voice     - re-synthesise Persian voice (needs network, edge-tts)"
	@echo "make offline   - rebuild voice.wav/ass/srt from committed clips (offline)"
	@echo "make music     - regenerate procedural music"
	@echo "make manim     - render the silent 1080p30 Manim animation"
	@echo "make preview   - fast 480p15 local preview (full edit, no vertical/GIF)"
	@echo "make render    - full 1080p30 render + edit + QA (what CI runs)"
	@echo "make qa        - re-run QA on rendered/"

voice:
	python tools/build_voice.py

offline:
	python tools/build_voice.py --offline

music:
	python tools/build_music.py

manim:
	python -m manim render -q h --fps 30 -o silent.mp4 --media_dir build/media src/main.py ExplainerScene

edit:
	python tools/edit.py

qa:
	python tools/qa.py

render:
	python tools/render.py --quality h --fps 30

preview:
	python tools/render.py --quality l --fps 15 --lightweight

clean:
	rm -rf build/media build/voice.wav build/music.wav

push:
	@echo "Set GH_TOKEN and GITHUB_USER, then: bash scripts/publish.sh"

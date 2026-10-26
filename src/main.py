"""Main Manim scene: a 60-second, RTL, 2D character explainer.

    python -m manim render -q h --fps 30 -o silent.mp4 src/main.py ExplainerScene

Single source of truth: ``storyboard.json`` (copy + timing) and
``captions/visemes.json`` (real TTS word spans -> mouth animation).

Design notes
------------
* One continuous Scene, exactly ``storyboard['duration']`` seconds.  No cuts
  between scenes: props fade out/in while the character stays alive, so the
  final edit only has to add audio, captions, fades and delivery presets.
* All continuous motion (breathing, blinking, gaze, visemes, antenna, arms)
  runs from a single updater that reads ``self.renderer.time`` -- the film's
  absolute clock -- so it stays deterministic and frame-accurate.
* ``Beat`` is a tiny budget tracker: every scene spends its allotted seconds
  on animations and waits out the remainder.  That makes the total exact.
"""

from __future__ import annotations

import math

import numpy as np
from manim import (
    Dot,
    FadeIn,
    FadeOut,
    Flash,
    GrowFromEdge,
    Indicate,
    LaggedStart,
    Line,
    Rotate,
    RoundedRectangle,
    Scene,
    Transform,
    VGroup,
    DOWN,
    LEFT,
    RIGHT,
    TAU,
    UP,
)

from src import props as P
from src.character import make_character
from src.config import (
    AMBER,
    BG,
    CYAN,
    GREEN,
    INK,
    MUTED,
    PANEL_2,
    VIOLET,
    register_fonts,
    storyboard,
    visemes,
)

register_fonts()


def _p(x, y):
    return np.array([x, y, 0.0])


class Beat:
    """Keep a scene's animations inside its allotted wall-clock budget."""

    def __init__(self, scene, total):
        self.s = scene
        self.total = float(total)
        self.used = 0.0
        self.start = float(scene.now())

    def play(self, *anims, run_time=0.7):
        self.s.play(*anims, run_time=run_time)
        self.used += run_time

    def wait(self, sec):
        self.s.wait(sec)
        self.used += sec

    def finish(self, out_anims=None, out=0.35):
        """Absorb Manim's per-animation frame rounding into the final wait.

        Manim renders ``ceil(run_time * fps)`` frames for each ``play``, so a
        long chain of short animations slowly drifts late.  Instead of summing
        our own bookkeeping, wait until the *absolute film clock* reaches the
        scene's end (minus the outro).  Error stays under one frame per scene.
        """
        reserved = out if out_anims else 0.0
        target = self.start + self.total - reserved
        rest = target - self.s.now()
        if rest > 1e-6:
            self.s.wait(rest)
            self.used += rest
        if out_anims:
            self.s.play(*out_anims, run_time=out)
            self.used += out


class ExplainerScene(Scene):
    def construct(self):
        sb = storyboard()
        self.sb = sb
        self.spans = visemes()
        self.camera.background_color = BG

        self.add(P.make_backdrop())
        self.bar, self.segs = P.make_top_bar()
        self.add(self.bar)

        self.housha = make_character()
        self.add(self.housha)
        # driver mobject for all continuous character motion
        driver = Dot(radius=0.001).set_opacity(0)
        driver.add_updater(
            lambda m, dt: self.housha.tick(self.now(), self.speech(self.now()))
        )
        self.add(driver)

        self.stage: list = []
        for i, seg in enumerate(sb["scenes"]):
            P.set_step(self.segs, i, [CYAN, CYAN, VIOLET, AMBER, GREEN, CYAN][i])
            self.stage = []
            b = Beat(self, seg["duration"])
            getattr(self, "sc_" + seg["kind"])(seg, b)
            outs = [FadeOut(m) for m in self.stage if m is not None]
            b.finish(outs, out=0.35)
            for m in self.stage:
                if m in self.mobjects:
                    self.remove(m)
            self.stage = []

    # ---------------------------------------------------------------- utils
    def now(self):
        return float(getattr(self.renderer, "time", 0.0))

    def speech(self, t):
        """Mouth-open envelope derived from the real TTS word boundaries."""
        for s, e in self.spans:
            if s <= t <= e:
                return 0.55 + 0.45 * abs(math.sin(t * 17.0))
            if s > t:
                break
        return 0.0

    def show(self, b, mob, rt=0.7, shift=None, lag=None):
        self.stage.append(mob)
        if lag is not None:
            b.play(
                LaggedStart(*[FadeIn(x, shift=shift) for x in mob], lag_ratio=lag),
                run_time=rt,
            )
        else:
            b.play(
                FadeIn(mob, shift=shift) if shift is not None else FadeIn(mob),
                run_time=rt,
            )
        return mob

    def head(self, b, seg, accent):
        return self.show(
            b, P.title_block(seg["title"], seg["kicker"], accent), rt=0.75,
            shift=LEFT * 0.35,
        )

    # --------------------------------------------------------------- scenes
    def sc_intro(self, seg, b):
        self.housha.set_waving(True)
        self.head(b, seg, CYAN)

        labels = ["۱  گوش کردن", "۲  تصمیم گیری", "۳  رندر", "۴  بازبینی"]
        pills = [P.pill(s, [CYAN, VIOLET, AMBER, GREEN][i]) for i, s in enumerate(labels)]
        row = VGroup(*pills).arrange(LEFT, buff=0.30).move_to(_p(2.15, -0.45))
        self.show(b, row, rt=1.8, shift=UP * 0.35, lag=0.16)

        hi = P.txt("همه چیز از یک فایل خام شروع می شود", size=27, color=MUTED)
        hi.move_to(_p(6.80 - hi.width / 2, -1.75))
        self.show(b, hi, rt=0.8, shift=UP * 0.25)

        b.play(Flash(row[0], color=CYAN, line_length=0.25), run_time=0.75)
        b.wait(0.4)
        self.housha.set_waving(False)

    def sc_waveform(self, seg, b):
        self.housha.look_at(1.0, 0.0)
        self.head(b, seg, CYAN)

        bars = P.waveform_bars(42, CYAN)
        self.stage.append(bars)
        b.play(
            LaggedStart(
                *[GrowFromEdge(x, DOWN) for x in bars], lag_ratio=0.012
            ),
            run_time=1.9,
        )

        rows = P.transcript_rows(
            [
                ("00:02.140", "سلام من هوشا هستم"),
                ("00:05.820", "امروز چهار مرحله را می گوییم"),
                ("00:09.310", "سکوت ها نیز حذف می شوند"),
            ],
            CYAN,
        )
        self.show(b, rows, rt=1.7, shift=RIGHT * 0.45, lag=0.12)

        scan = Line(_p(-1.90, -2.62), _p(-1.90, -1.02)).set_stroke(AMBER, width=4)
        self.stage.append(scan)
        self.add(scan)
        b.play(scan.animate.move_to(_p(6.72, -1.82)), run_time=2.0)
        b.play(Indicate(rows[1], color=AMBER), run_time=0.8)
        self.housha.look_at(0.0, 0.0)

    def sc_edl(self, seg, b):
        self.housha.set_pointing(True)
        self.head(b, seg, VIOLET)

        code = P.json_code_card(
            [
                '{',
                '  "source": "raw/interview.mp4",',
                '  "fps": 30, "size": [1920, 1080],',
                '  "segments": [',
                '    {"in": 12.40, "out": 24.86},',
                '    {"in": 41.02, "out": 58.30}',
                '  ]',
                '}',
            ],
            VIOLET,
        )
        self.show(b, code, rt=1.3, shift=LEFT * 0.3)

        chain = [
            P.pill("ASR", CYAN), P.pill("LLM", VIOLET),
            P.pill("EDL", AMBER), P.pill("FFmpeg", GREEN),
        ]
        flow = VGroup(*chain).arrange(LEFT, buff=0.55).move_to(_p(2.15, -2.72))
        self.show(b, flow, rt=1.5, shift=UP * 0.3, lag=0.15)

        b.play(Indicate(code, color=VIOLET, scale_factor=1.03), run_time=1.0)
        b.play(Flash(chain[2], color=AMBER, line_length=0.22), run_time=0.8)
        self.housha.set_pointing(False)

    def sc_timeline(self, seg, b):
        self.head(b, seg, AMBER)

        timeline = P.clip_timeline(AMBER)
        self.show(b, timeline, rt=1.1, shift=UP * 0.3)

        g1 = P.gear(0.52, VIOLET).move_to(_p(6.10, 0.95))
        g2 = P.gear(0.34, CYAN).move_to(_p(5.42, 0.62))
        self.stage.extend([g1, g2])
        b.play(FadeIn(g1), FadeIn(g2), run_time=0.7)
        b.play(Rotate(g1, angle=TAU), Rotate(g2, angle=-TAU), run_time=1.8)

        b.play(
            timeline.playhead.animate.move_to(_p(timeline.timeline_end - 0.1, -0.35)),
            run_time=2.4,
        )

        chips = [
            P.pill("xfade", CYAN), P.pill("captions", VIOLET),
            P.pill("music", GREEN), P.pill("LUT", AMBER),
        ]
        row = VGroup(*chips).arrange(LEFT, buff=0.42).move_to(_p(2.15, -2.45))
        self.show(b, row, rt=1.5, shift=UP * 0.3, lag=0.14)
        b.play(Indicate(timeline, color=AMBER, scale_factor=1.02), run_time=0.8)

    def sc_checklist(self, seg, b):
        self.head(b, seg, GREEN)

        sheet = P.contact_sheet()
        self.show(b, sheet, rt=0.9, shift=DOWN * 0.3)

        rows = P.check_rows(
            [
                "رزولوشن، فریم ریت و کدک",
                "کادر امن پلتفرم",
                "بلندی صدا و پیک واقعی",
                "فریم خالی یا تصویر فریز",
            ],
            GREEN,
        )
        self.show(b, rows, rt=1.7, shift=RIGHT * 0.4, lag=0.12)

        meter = P.loudness_meter(AMBER)
        self.show(b, meter, rt=0.7, shift=UP * 0.25)
        target = RoundedRectangle(corner_radius=0.06, width=3.5, height=0.24)
        target.set_fill(AMBER, opacity=0.95).set_stroke(width=0)
        target.move_to(_p(P.CONTENT_CENTER[0] + 0.35 - 2.25 + 1.75, -1.85))
        b.play(Transform(meter.fillbar, target), run_time=1.3)
        b.play(Flash(rows[2], color=GREEN, line_length=0.2), run_time=0.7)

    def sc_outro(self, seg, b):
        self.housha.set_waving(True)
        self.head(b, seg, CYAN)

        badges = P.step_badges(
            ["گوش کردن", "تصمیم گیری", "رندر", "بازبینی"], CYAN
        )
        self.show(b, badges, rt=1.4, shift=UP * 0.35, lag=0.10)

        cta = P.txt("همه اش با کد، روی گیت هاب", size=30, color=AMBER, bold=True)
        cta.move_to(_p(6.80 - cta.width / 2, -1.15))
        self.show(b, cta, rt=0.85, shift=UP * 0.3)

        sub = P.txt("storyboard.json  →  Manim  →  FFmpeg  →  MP4", size=20, color=MUTED, mono=True)
        sub.move_to(_p(6.80 - sub.width / 2, -1.95))
        self.show(b, sub, rt=0.7, shift=UP * 0.25)
        b.play(Flash(badges, color=CYAN, line_length=0.2), run_time=0.8)

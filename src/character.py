"""Housha - a fully vector 2D character, built from Manim VMobjects.

This is *character animation*, not a slideshow: the mascot breathes, blinks on
a cycle, tracks the board with its eyes, opens its mouth on the real word
timings extracted from the TTS engine (visemes), pulses its antenna and chest
equalizer, sways its arms and can wave or point on cue.

Everything is plain geometry -> rendered by Cairo in headless CI, no browser,
no Chrome, no GPU, no external assets.

IMPORTANT (coordinate system)
-----------------------------
All parts are authored in local coordinates, then the whole group is scaled
and positioned once in ``__init__``.  After that transform we *capture the
world-space anchors* of every animated part.  The per-frame updater only ever
uses those captured world coordinates -- writing local coordinates into a
transformed VGroup would tear the character apart.
"""

from __future__ import annotations

import math

import numpy as np
from manim import (
    Arc,
    Circle,
    Dot,
    Ellipse,
    Line,
    RoundedRectangle,
    VGroup,
    PI,
)

from src.config import (
    AMBER,
    CYAN,
    DARK,
    GREEN,
    INK,
    PANEL_2,
    PINK,
    VIOLET,
)

UP_V = np.array([0.0, 1.0, 0.0])


def _p(x: float, y: float) -> np.ndarray:
    return np.array([x, y, 0.0])


class Housha(VGroup):
    """The mascot.  Call ``tick(t, speech)`` from a scene updater."""

    def __init__(self, scale: float = 0.76, center=(-4.45, -0.10), **kwargs):
        super().__init__(**kwargs)

        # ------------------------------------------------------------------
        # ground shadow (deliberately outside the breathing group)
        # ------------------------------------------------------------------
        self.shadow = Ellipse(width=3.1, height=0.40).set_fill(
            "#000000", opacity=0.34
        ).set_stroke(width=0)
        self.shadow.move_to(_p(0, -2.58))

        fig = VGroup()

        # ------------------------------------------------------------------
        # torso
        # ------------------------------------------------------------------
        self.body = RoundedRectangle(
            corner_radius=0.30, width=2.5, height=2.05
        ).set_fill(PANEL_2, opacity=1).set_stroke(CYAN, width=3)
        self.body.move_to(_p(0, -1.25))

        self.chest = RoundedRectangle(
            corner_radius=0.20, width=1.72, height=1.12
        ).set_fill(DARK, opacity=1).set_stroke(VIOLET, width=2)
        self.chest.move_to(_p(0, -1.24))

        self.chest_bars = VGroup()
        for i in range(7):
            bar = RoundedRectangle(
                corner_radius=0.04, width=0.12, height=0.30 + 0.16 * (i % 3)
            ).set_fill(GREEN if i % 2 else CYAN, opacity=0.85).set_stroke(width=0)
            bar.move_to(_p(-0.60 + i * 0.20, -1.24))
            self.chest_bars.add(bar)

        self.neck = RoundedRectangle(
            corner_radius=0.08, width=0.72, height=0.34
        ).set_fill(PANEL_2, opacity=1).set_stroke(CYAN, width=2)
        self.neck.move_to(_p(0, -0.04))

        self.feet = VGroup()
        for x in (-0.64, 0.64):
            foot = RoundedRectangle(
                corner_radius=0.13, width=0.86, height=0.40
            ).set_fill(PANEL_2, opacity=1).set_stroke(CYAN, width=2)
            foot.move_to(_p(x, -2.40))
            self.feet.add(foot)

        # ------------------------------------------------------------------
        # head
        # ------------------------------------------------------------------
        halo = VGroup()
        for r, op in ((1.95, 0.05), (1.65, 0.06), (1.40, 0.07)):
            halo.add(
                Circle(radius=r).set_fill(VIOLET, opacity=op).set_stroke(width=0)
            )
        halo.move_to(_p(0, 1.15))
        self.halo = halo

        self.head = RoundedRectangle(
            corner_radius=0.55, width=3.0, height=2.16
        ).set_fill(PANEL_2, opacity=1).set_stroke(CYAN, width=4)
        self.head.move_to(_p(0, 1.15))

        self.face = RoundedRectangle(
            corner_radius=0.42, width=2.62, height=1.72
        ).set_fill(DARK, opacity=1).set_stroke(CYAN, width=1.5, opacity=0.35)
        self.face.move_to(_p(0, 1.15))

        self.antenna = Line(_p(0, 2.22), _p(0, 2.86)).set_stroke(CYAN, width=6)
        self.bulb_glow = VGroup()
        for r, op in ((0.38, 0.08), (0.28, 0.12), (0.19, 0.20)):
            self.bulb_glow.add(
                Circle(radius=r).set_fill(AMBER, opacity=op).set_stroke(width=0)
            )
        self.bulb_glow.move_to(_p(0, 3.00))
        self.bulb = Circle(radius=0.16).set_fill(AMBER, opacity=1).set_stroke(
            "#FFF0D6", width=2
        )
        self.bulb.move_to(_p(0, 3.00))

        self.eyes = VGroup()
        for x in (-0.63, 0.63):
            white = Ellipse(width=0.58, height=0.70).set_fill(
                INK, opacity=1
            ).set_stroke(width=0)
            iris = Circle(radius=0.185).set_fill(CYAN, opacity=1).set_stroke(
                "#123047", width=2
            )
            pupil = Circle(radius=0.085).set_fill("#0A1626", opacity=1).set_stroke(
                width=0
            )
            glint = Circle(radius=0.055).set_fill("#FFFFFF", opacity=0.95).set_stroke(
                width=0
            )
            iris.move_to(_p(x + 0.04, 1.38))
            pupil.move_to(_p(x + 0.04, 1.38))
            glint.move_to(_p(x + 0.10, 1.45))
            eye = VGroup(white, iris, pupil, glint)
            eye.move_to(_p(x, 1.42))
            self.eyes.add(eye)

        self.brows = VGroup()
        for x in (-0.63, 0.63):
            brow = RoundedRectangle(
                corner_radius=0.045, width=0.52, height=0.09
            ).set_fill(CYAN, opacity=0.75).set_stroke(width=0)
            brow.move_to(_p(x, 1.92))
            self.brows.add(brow)

        self.cheeks = VGroup()
        for x in (-1.02, 1.02):
            self.cheeks.add(
                Circle(radius=0.13).set_fill(PINK, opacity=0.30).set_stroke(width=0)
                .move_to(_p(x, 0.94))
            )

        self.mouth = RoundedRectangle(
            corner_radius=0.10, width=0.78, height=0.10
        ).set_fill(VIOLET, opacity=0.95).set_stroke(CYAN, width=1.5)
        self.mouth.move_to(_p(0, 0.60))
        self.smile = Arc(
            radius=0.36, start_angle=PI + 0.55, angle=PI - 1.10,
            arc_center=_p(0, 0.78),
        ).set_stroke(CYAN, width=6)

        # arms: thick lines + circular hands; endpoints rewritten each frame
        self.arm_l = Line(_p(-1.22, -0.62), _p(-1.86, -1.62)).set_stroke(CYAN, width=17)
        self.arm_r = Line(_p(1.22, -0.62), _p(1.86, -1.62)).set_stroke(CYAN, width=17)
        self.hand_l = Dot(_p(-1.86, -1.62), radius=0.17).set_fill(
            AMBER, opacity=1
        ).set_stroke("#FFF0D6", width=2)
        self.hand_r = Dot(_p(1.86, -1.62), radius=0.17).set_fill(
            AMBER, opacity=1
        ).set_stroke("#FFF0D6", width=2)

        fig.add(
            halo, self.feet, self.body, self.chest, self.chest_bars, self.neck,
            self.arm_l, self.arm_r, self.head, self.face, self.antenna,
            self.bulb_glow, self.bulb, self.eyes, self.brows, self.cheeks,
            self.smile, self.mouth, self.hand_l, self.hand_r,
        )
        self.figure = fig
        self.add(self.shadow, self.figure)

        # ---- apply the one and only global transform, then capture anchors --
        self.scale(scale)
        self.move_to(_p(center[0], center[1]))
        self._scale = scale
        self._capture()

        # animation state
        self._last_breath = 0.0
        self.waving = False
        self.pointing = False
        self._gaze = np.array([0.0, 0.0, 0.0])
        self._gaze_target = np.array([0.0, 0.0, 0.0])

    # ----------------------------------------------------------------------
    def _capture(self):
        """Remember world-space rest positions/heights after the transform."""
        self._eye_home = [e.get_center().copy() for e in self.eyes]
        self._eye_h = [max(0.05, e.height) for e in self.eyes]
        self._brow_home = [b.get_center().copy() for b in self.brows]
        self._mouth_home = self.mouth.get_center().copy()
        self._bar_home = [b.get_center().copy() for b in self.chest_bars]
        self._shoulder_l = self.arm_l.get_start().copy()
        self._shoulder_r = self.arm_r.get_start().copy()
        self._shadow_centre = self.shadow.get_center().copy()

    # ----------------------------------------------------------------------
    # public control surface (called by the scene, not animated by Manim)
    # ----------------------------------------------------------------------
    def set_waving(self, value: bool) -> "Housha":
        self.waving = bool(value)
        return self

    def set_pointing(self, value: bool) -> "Housha":
        self.pointing = bool(value)
        return self

    def look_at(self, x: float, y: float) -> "Housha":
        self._gaze_target = np.array([x, y, 0.0])
        return self

    # ----------------------------------------------------------------------
    # per-frame update
    # ----------------------------------------------------------------------
    def tick(self, t: float, speech: float = 0.0) -> None:
        """Update all secondary motion.  ``t`` is absolute film time (s)."""
        s = self._scale

        # --- breathing -----------------------------------------------------
        breath = 0.055 * s * math.sin(t * 2.15)
        self.figure.shift(UP_V * (breath - self._last_breath))
        self._last_breath = breath
        bob = UP_V * breath
        self.shadow.stretch_to_fit_width(3.1 * s - 0.18 * s * math.sin(t * 2.15))
        self.shadow.move_to(self._shadow_centre)

        # --- blink cycle ---------------------------------------------------
        phase = (t + 0.9) % 4.15
        if phase < 0.09:
            openness = 0.10
        elif phase < 0.19:
            openness = 0.10 + 0.90 * (phase - 0.09) / 0.10
        else:
            openness = 1.0

        # --- gaze (eased) --------------------------------------------------
        self._gaze += (self._gaze_target - self._gaze) * 0.12
        gaze = np.array([self._gaze[0] * 0.10 * s, self._gaze[1] * 0.06 * s, 0.0])
        for i, eye in enumerate(self.eyes):
            eye.stretch_to_fit_height(max(0.03, self._eye_h[i] * openness))
            eye.move_to(self._eye_home[i] + bob + gaze)
        for i, brow in enumerate(self.brows):
            brow.move_to(
                self._brow_home[i]
                + bob
                + UP_V * (0.10 * s * speech - (1 - openness) * 0.10 * s)
            )

        # --- visemes -------------------------------------------------------
        env = max(0.0, min(1.0, speech))
        wobble = 0.72 + 0.28 * abs(math.sin(t * 18.0))
        h = (0.075 + 0.40 * env * wobble) * s
        w = (0.70 + 0.38 * env) * s
        self.mouth.stretch_to_fit_height(max(0.03, h))
        self.mouth.stretch_to_fit_width(max(0.10, w))
        self.mouth.move_to(self._mouth_home + bob)
        self.mouth.set_opacity(0.98 if env > 0.03 else 0.0)
        self.smile.set_opacity(0.0 if env > 0.03 else 0.85)

        # --- antenna + chest equalizer -------------------------------------
        pulse = 0.5 + 0.5 * math.sin(t * 3.1)
        for i, ring in enumerate(self.bulb_glow):
            ring.set_opacity(0.06 + 0.06 * i + 0.12 * pulse + 0.10 * env)
        for i, bar in enumerate(self.chest_bars):
            target = (0.24 + 0.55 * abs(math.sin(t * (5 + i * 0.7)))
                      * (0.35 + 0.65 * env)) * s
            bar.stretch_to_fit_height(max(0.05, target))
            bar.move_to(self._bar_home[i] + bob)

        # --- arms ----------------------------------------------------------
        sway = 0.10 * math.sin(t * 2.3)
        l_off = np.array([-0.64 - 0.06 * math.sin(t * 2.3), -1.0 - sway, 0.0])
        if self.waving:
            r_off = np.array([0.73, 0.42 + 0.42 * math.sin(t * 8.5), 0.0])
        elif self.pointing:
            r_off = np.array([1.53, 0.07, 0.0])
        else:
            r_off = np.array([0.64 + 0.06 * math.sin(t * 2.3), -1.0 + sway, 0.0])
        sl = self._shoulder_l + bob
        sr = self._shoulder_r + bob
        el = sl + l_off * s
        er = sr + r_off * s
        self.arm_l.put_start_and_end_on(sl, el)
        self.arm_r.put_start_and_end_on(sr, er)
        self.hand_l.move_to(el)
        self.hand_r.move_to(er)


def make_character() -> Housha:
    """Convenience factory with the film's default placement and scale."""
    return Housha(scale=0.76, center=(-4.45, -0.10))

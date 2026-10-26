"""Reusable 2D props for the explainer.

All helpers return plain Manim mobjects / VGroups.  They are intentionally
stateless: the scene decides when to create, animate and remove them.  Text
uses the bundled Vazirmatn font (registered in ``src.config``), and Pango does
the RTL shaping -- no manual reshaping is needed here.
"""

from __future__ import annotations

import math

import numpy as np
from manim import (
    Arc,
    Arrow,
    Circle,
    Dot,
    Line,
    Rectangle,
    RoundedRectangle,
    Text,
    VGroup,
    PI,
    DOWN,
    LEFT,
    RIGHT,
    UP,
)

from src.config import (
    AMBER,
    CYAN,
    DARK,
    FONT_FAMILY,
    FONT_MONO,
    FRAME_H,
    FRAME_W,
    GREEN,
    INK,
    MUTED,
    PANEL,
    PANEL_2,
    VIOLET,
)

CONTENT_CENTER = np.array([2.05, -0.25, 0.0])


def _p(x, y):
    return np.array([x, y, 0.0])


def txt(text, size=30, color=INK, bold=False, mono=False, **kw):
    return Text(
        text,
        font=FONT_MONO if mono else FONT_FAMILY,
        font_size=size,
        color=color,
        weight="BOLD" if bold else "NORMAL",
        **kw,
    )


def card(w, h, fill=PANEL, stroke=CYAN, opacity=1.0, radius=0.22, sw=2.0):
    c = RoundedRectangle(corner_radius=radius, width=w, height=h)
    c.set_fill(fill, opacity=opacity).set_stroke(stroke, width=sw)
    return c


def make_backdrop():
    """Dark stage: a faint dot grid, two soft glows and a bottom hairline."""
    g = VGroup()
    # dot grid
    dots = VGroup()
    for x in np.arange(-6.9, 7.0, 0.72):
        for y in np.arange(-3.6, 3.7, 0.72):
            d = Dot(_p(float(x), float(y)), radius=0.012).set_fill(
                "#2B3D57", opacity=0.55
            ).set_stroke(width=0)
            dots.add(d)
    dots.set_opacity(0.32)
    g.add(dots)
    for cx, cy, r, col, op in (
        (4.9, 2.4, 3.1, VIOLET, 0.055),
        (-4.6, -2.2, 3.4, CYAN, 0.045),
        (1.4, -1.2, 2.4, GREEN, 0.025),
    ):
        for k in (1.0, 0.78, 0.58):
            ring = Circle(radius=r * k).set_fill(col, opacity=op).set_stroke(width=0)
            ring.move_to(_p(cx, cy))
            g.add(ring)
    g.add(
        Line(_p(-7.1, -3.28), _p(7.1, -3.28)).set_stroke(CYAN, width=1).set_opacity(0.18)
    )
    return g


def make_top_bar():
    """Brand mark + six scene progress segments.  Returns (bar, segments)."""
    bar = VGroup()
    brand = txt("HOUSHA  /  AGENT VIDEO PIPELINE", size=19, color=MUTED, mono=True)
    brand.move_to(_p(-4.55, 3.52))
    bar.add(brand)
    tag = txt("FA · 60s · 2D", size=17, color=MUTED, mono=True)
    tag.move_to(_p(-0.55, 3.52))
    bar.add(tag)
    bar.add(
        Line(_p(-7.05, 3.24), _p(7.05, 3.24)).set_stroke(CYAN, width=1).set_opacity(0.20)
    )
    segs = VGroup()
    for i in range(6):
        s = RoundedRectangle(corner_radius=0.035, width=0.53, height=0.075)
        s.set_fill(PANEL_2, opacity=1).set_stroke(width=0)
        s.move_to(_p(3.55 + i * 0.58, 3.52))
        segs.add(s)
    bar.add(segs)
    return bar, segs


def set_step(segs, index, accent=CYAN):
    for i, s in enumerate(segs):
        s.set_fill(accent if i <= index else PANEL_2, opacity=1)


def title_block(title, kicker, accent=CYAN):
    """Right-aligned (RTL) heading block for the content half of the frame."""
    g = VGroup()
    head = txt(title, size=40, color=INK, bold=True)
    if head.width > 8.6:
        head.scale_to_fit_width(8.6)
    head.move_to(_p(6.80 - head.width / 2, 2.62))
    k = txt(kicker, size=21, color=accent, mono=True)
    k.move_to(_p(6.80 - k.width / 2, 2.08))
    rule = Line(_p(4.15, 1.86), _p(6.82, 1.86)).set_stroke(accent, width=3)
    g.add(head, k, rule)
    return g


def waveform_bars(n=42, accent=CYAN, seed=7):
    """An audio waveform made of rounded bars."""
    import random

    rnd = random.Random(seed)
    g = VGroup()
    for i in range(n):
        env = 0.35 + 0.65 * abs(math.sin(i * 0.21))
        h = 0.16 + 1.22 * env * rnd.uniform(0.45, 1.0)
        b = RoundedRectangle(corner_radius=0.035, width=0.095, height=max(0.12, h))
        b.set_fill(accent if i % 5 else AMBER, opacity=0.92).set_stroke(width=0)
        b.move_to(_p(-1.85 + i * 0.205, -1.82))
        g.add(b)
    return g


def transcript_rows(rows, accent=CYAN):
    g = VGroup()
    for i, (tag, text) in enumerate(rows):
        r = card(6.6, 0.56, fill=PANEL, stroke=accent, radius=0.12, sw=1.2)
        r.set_stroke(accent, width=1.2, opacity=0.45)
        r.move_to(_p(CONTENT_CENTER[0] + 0.35, 1.10 - i * 0.76))
        t = txt(text, size=22, color=INK)
        t.move_to(_p(6.45 - t.width / 2, 1.10 - i * 0.76))
        tagt = txt(tag, size=16, color=accent, mono=True)
        tagt.move_to(_p(0.62, 1.10 - i * 0.76))
        g.add(r, t, tagt)
    return g


def json_code_card(lines, accent=VIOLET):
    g = VGroup()
    box = card(7.5, 3.25, fill=DARK, stroke=accent, radius=0.18, sw=2)
    box.move_to(_p(CONTENT_CENTER[0] + 0.35, -0.45))
    g.add(box)
    header = txt("edl.json", size=18, color=accent, mono=True)
    header.move_to(_p(CONTENT_CENTER[0] - 2.85, 0.90))
    g.add(header)
    for i, line in enumerate(lines):
        t = txt(line, size=19, color=INK, mono=True)
        t.move_to(_p(CONTENT_CENTER[0] - 2.85 + t.width / 2, 0.45 - i * 0.48))
        g.add(t)
    return g


def step_badges(labels, accent=CYAN):
    g = VGroup()
    for i, lab in enumerate(labels):
        x = -1.35 + i * 2.30
        c = Circle(radius=0.42).set_fill(PANEL_2, opacity=1).set_stroke(accent, width=2.5)
        c.move_to(_p(x, 0.95))
        n = txt(str(i + 1), size=26, color=accent, bold=True, mono=True)
        n.move_to(_p(x, 0.95))
        l = txt(lab, size=21, color=INK)
        l.move_to(_p(x, 0.22))
        g.add(c, n, l)
        if i < len(labels) - 1:
            a = Arrow(_p(x + 0.48, 0.95), _p(x + 1.82, 0.95), buff=0).set_stroke(
                MUTED, width=2
            )
            g.add(a)
    return g


def clip_timeline(accent=CYAN):
    """A filmstrip: 6 clips of different lengths + a playhead."""
    g = VGroup()
    widths = [1.35, 0.85, 1.75, 1.05, 1.55, 0.95]
    cols = [CYAN, VIOLET, AMBER, GREEN, CYAN, VIOLET]
    x = -1.95
    for w, c in zip(widths, cols):
        r = RoundedRectangle(corner_radius=0.09, width=w, height=0.86)
        r.set_fill(PANEL_2, opacity=1).set_stroke(c, width=2)
        r.move_to(_p(x + w / 2, -0.35))
        g.add(r)
        for k in range(3):
            mark = Line(
                _p(x + 0.18 + k * (w - 0.36) / 2, -0.66),
                _p(x + 0.18 + k * (w - 0.36) / 2, -0.04),
            ).set_stroke(c, width=1.5, opacity=0.35)
            g.add(mark)
        x += w + 0.14
    bar = Line(_p(-1.95, -1.02), _p(x, -1.02)).set_stroke(MUTED, width=2)
    g.add(bar)
    head = VGroup()
    head.add(
        Line(_p(0, 0.62), _p(0, -1.15)).set_stroke(AMBER, width=3)
    )
    head.add(
        Dot(_p(0, 0.68), radius=0.11).set_fill(AMBER, opacity=1).set_stroke(width=0)
    )
    head.move_to(_p(-1.95, -0.35))
    g.add(head)
    g.playhead = head
    g.timeline_end = x
    return g


def gear(radius=0.55, color=VIOLET, teeth=9):
    g = VGroup()
    g.add(Circle(radius=radius * 0.78).set_fill(PANEL_2, opacity=1).set_stroke(color, width=3))
    g.add(Circle(radius=radius * 0.30).set_fill(DARK, opacity=1).set_stroke(color, width=2))
    for i in range(teeth):
        a = 2 * PI * i / teeth
        t = Rectangle(width=radius * 0.30, height=radius * 0.20)
        t.set_fill(color, opacity=0.9).set_stroke(width=0)
        t.rotate(a).move_to(
            _p(radius * 0.86 * math.cos(a), radius * 0.86 * math.sin(a))
        )
        g.add(t)
    return g


def check_rows(items, accent=GREEN):
    g = VGroup()
    for i, label in enumerate(items):
        y = 1.05 - i * 0.92
        box = RoundedRectangle(corner_radius=0.10, width=0.42, height=0.42)
        box.set_fill(PANEL_2, opacity=1).set_stroke(accent, width=2)
        box.move_to(_p(6.35, y))
        tick = VGroup(
            Line(_p(6.20, y), _p(6.31, y - 0.11)),
            Line(_p(6.31, y - 0.11), _p(6.52, y + 0.13)),
        ).set_stroke(accent, width=4)
        t = txt(label, size=24, color=INK)
        t.move_to(_p(5.95 - t.width / 2, y))
        g.add(box, tick, t)
    return g


def contact_sheet(cols=5, rows=2, accent=CYAN):
    g = VGroup()
    for r in range(rows):
        for c in range(cols):
            f = RoundedRectangle(corner_radius=0.05, width=1.15, height=0.66)
            f.set_fill(PANEL_2, opacity=1).set_stroke(accent, width=1, opacity=0.5)
            f.move_to(_p(-1.55 + c * 1.28, 0.25 - r * 0.78))
            # fake thumbnail: horizon + sun
            f.add(
                Line(_p(0, -0.16), _p(0, 0.16)).set_stroke(accent, width=0)
            )
            g.add(f)
    return g


def loudness_meter(accent=AMBER):
    g = VGroup()
    track = RoundedRectangle(corner_radius=0.08, width=4.6, height=0.34)
    track.set_fill(DARK, opacity=1).set_stroke(MUTED, width=1.5)
    track.move_to(_p(CONTENT_CENTER[0] + 0.35, -1.85))
    g.add(track)
    fill = RoundedRectangle(corner_radius=0.06, width=0.1, height=0.24)
    fill.set_fill(accent, opacity=0.95).set_stroke(width=0)
    fill.move_to(_p(CONTENT_CENTER[0] + 0.35 - 2.25, -1.85))
    g.add(fill)
    label = txt("-14 LUFS", size=19, color=accent, mono=True)
    label.move_to(_p(CONTENT_CENTER[0] + 0.35, -2.35))
    g.add(label)
    g.fillbar = fill
    return g


def pill(label, accent=CYAN):
    t = txt(label, size=20, color=INK)
    w = max(1.1, t.width + 0.52)
    bg = RoundedRectangle(corner_radius=0.24, width=w, height=0.56)
    bg.set_fill(PANEL_2, opacity=1).set_stroke(accent, width=2)
    g = VGroup(bg, t)
    return g

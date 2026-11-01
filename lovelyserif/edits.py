"""Per-glyph hand edits for Lovely Serif.

Each edit is a small, documented function operating on the cubic outline
model.  They run *before* the generic corner-softening filter so the fillets
blend the edited geometry in.  The registry maps glyph names (post-rename,
e.g. ``uni6C38`` or ``m``) to a list of edit callables.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Tuple

from .geometry import add, dist, lerp, mul, norm, sub
from .outline import Glyph, Node

Point = Tuple[float, float]
Edit = Callable[[Glyph], Glyph]
REGISTRY: Dict[str, List[Edit]] = {}


def register(*names: str):
    def deco(fn: Edit) -> Edit:
        for n in names:
            REGISTRY.setdefault(n, []).append(fn)
        return fn
    return deco


# --- generic helpers ---------------------------------------------------------

def nearest_node(g: Glyph, pt: Point, max_d: float = 40.0) -> Optional[Tuple[int, int]]:
    best = None; bd = max_d
    for ci, c in enumerate(g.contours):
        for ni, n in enumerate(c):
            d = dist(n.pt, pt)
            if d < bd:
                bd = d; best = (ci, ni)
    return best


def move_node(g: Glyph, near: Point, dx: float, dy: float, handles: bool = True, max_d: float = 40.0) -> bool:
    hit = nearest_node(g, near, max_d)
    if hit is None:
        return False
    n = g.contours[hit[0]][hit[1]]
    n.x += dx; n.y += dy
    if handles:
        if n.hin is not None:
            n.hin = (n.hin[0] + dx, n.hin[1] + dy)
        if n.hout is not None:
            n.hout = (n.hout[0] + dx, n.hout[1] + dy)
    n.tag = "edit"
    return True


def nudge_region(g: Glyph, center: Point, radius: float, dx: float, dy: float, falloff: float = 1.0) -> int:
    """Move every node (and handle) within ``radius`` of ``center`` by a
    displacement that fades out smoothly toward the edge of the region."""
    moved = 0
    def w(p: Point) -> float:
        d = dist(p, center)
        if d >= radius:
            return 0.0
        t = d / radius
        return (1 - t * t) ** falloff
    for c in g.contours:
        for n in c:
            k = w(n.pt)
            if k > 0:
                n.x += dx * k; n.y += dy * k; n.tag = "edit"; moved += 1
            if n.hin is not None:
                kh = w(n.hin)
                if kh > 0:
                    n.hin = (n.hin[0] + dx * kh, n.hin[1] + dy * kh)
            if n.hout is not None:
                kh = w(n.hout)
                if kh > 0:
                    n.hout = (n.hout[0] + dx * kh, n.hout[1] + dy * kh)
    return moved


def scale_region(g: Glyph, center: Point, radius: float, sx: float, sy: float) -> int:
    """Scale nodes around ``center`` (fading out toward the edge of the region)."""
    moved = 0
    def f(p: Point) -> Point:
        d = dist(p, center)
        if d >= radius:
            return p
        k = (1 - (d / radius) ** 2)
        ex = 1 + (sx - 1) * k; ey = 1 + (sy - 1) * k
        return (center[0] + (p[0] - center[0]) * ex, center[1] + (p[1] - center[1]) * ey)
    for c in g.contours:
        for n in c:
            p = f(n.pt)
            if p != n.pt:
                n.x, n.y = p; n.tag = "edit"; moved += 1
            if n.hin is not None:
                n.hin = f(n.hin)
            if n.hout is not None:
                n.hout = f(n.hout)
    return moved


def curve_segment(g: Glyph, near_a: Point, near_b: Point, bulge: float, max_d: float = 30.0) -> bool:
    """Turn the straight segment between the nodes nearest ``near_a`` and
    ``near_b`` into a gentle curve bowing ``bulge`` units to the left of the
    direction of travel (negative = to the right)."""
    ha = nearest_node(g, near_a, max_d); hb = nearest_node(g, near_b, max_d)
    if ha is None or hb is None or ha[0] != hb[0]:
        return False
    c = g.contours[ha[0]]
    n = len(c)
    ia, ib = ha[1], hb[1]
    if (ia + 1) % n == ib:
        a, b = c[ia], c[ib]
    elif (ib + 1) % n == ia:
        a, b = c[ib], c[ia]
    else:
        return False
    d = norm(sub(b.pt, a.pt))
    left = (-d[1], d[0])
    L = dist(a.pt, b.pt)
    a.hout = add(lerp(a.pt, b.pt, 1 / 3), mul(left, bulge))
    b.hin = add(lerp(a.pt, b.pt, 2 / 3), mul(left, bulge))
    a.tag = b.tag = "edit"
    return True


def taper_tip(g: Glyph, tip: Point, extend: float, direction: Optional[Point] = None,
              radius: float = 90.0, bend: float = 0.0) -> bool:
    """Lengthen an acute stroke tip (harai) by ``extend`` units along the
    stroke direction, pulling nearby nodes with a smooth falloff, and
    optionally bending the very end sideways (``bend`` > 0 = to the left of
    the stroke direction)."""
    hit = nearest_node(g, tip, 30.0)
    if hit is None:
        return False
    c = g.contours[hit[0]]; n = c[hit[1]]
    if direction is None:
        prev = c[hit[1] - 1]; nxt = c[(hit[1] + 1) % len(c)]
        # stroke direction = from the mid-point of the neighbours toward the tip
        mid = lerp(prev.pt, nxt.pt, 0.5)
        direction = norm(sub(n.pt, mid))
    d = norm(direction)
    left = (-d[1], d[0])
    nudge_region(g, n.pt, radius, d[0] * extend + left[0] * bend, d[1] * extend + left[1] * bend, falloff=1.5)
    return True


# ---------------------------------------------------------------------------
# Per-glyph parameter overrides for the corner-softening pass
# ---------------------------------------------------------------------------
PARAM_SCALE: Dict[str, float] = {}   # glyph name -> multiplier on the fillet radii


# ---------------------------------------------------------------------------
# Japanese: 永 美 文 (kanji) — longer, softer harai, rounder uroko
# ---------------------------------------------------------------------------

@register("uni6C38")  # 永
def edit_ei(g: Glyph) -> Glyph:
    g = g.copy()
    # left harai (左払い): lengthen the tip and let it taper out like a brush
    taper_tip(g, tip=(38, 4), extend=11, direction=(-0.74, -0.67), radius=110)
    # right harai (右払い): push the flared blade a touch further right and down
    nudge_region(g, center=(950, 10), radius=80, dx=9, dy=-3, falloff=1.4)
    # bottom hook (はね): make the flick a little longer and softer
    nudge_region(g, center=(427, -76), radius=50, dx=-4, dy=-6, falloff=1.2)
    g.notes.append("edit: harai+11/+9, hane")
    PARAM_SCALE[g.name] = 1.25
    return g


@register("uni7F8E")  # 美
def edit_bi(g: Glyph) -> Glyph:
    g = g.copy()
    taper_tip(g, tip=(40, -69), extend=10, direction=(-0.62, -0.78), radius=110)
    nudge_region(g, center=(950, -20), radius=80, dx=9, dy=-3, falloff=1.4)
    g.notes.append("edit: harai+10/+9")
    PARAM_SCALE[g.name] = 1.25
    return g


@register("uni6587")  # 文
def edit_bun(g: Glyph) -> Glyph:
    g = g.copy()
    taper_tip(g, tip=(46, -70), extend=10, direction=(-0.64, -0.77), radius=110)
    nudge_region(g, center=(950, -15), radius=80, dx=9, dy=-3, falloff=1.4)
    # the top dot (点): widen its head slightly so it reads as a brush dot
    scale_region(g, center=(500, 815), radius=70, sx=1.10, sy=1.0)
    g.notes.append("edit: harai+10/+9, dot")
    PARAM_SCALE[g.name] = 1.3
    return g


@register("uni5B57")  # 字
def edit_ji(g: Glyph) -> Glyph:
    g = g.copy()
    PARAM_SCALE[g.name] = 1.25
    g.notes.append("edit: rounder uroko")
    return g


# ---------------------------------------------------------------------------
# Hiragana: あ の り は か す — soft brush exits
# ---------------------------------------------------------------------------

@register("uni3042")  # あ
def edit_a(g: Glyph) -> Glyph:
    g = g.copy()
    # final stroke exits to the left: lengthen and lift the tail very slightly
    nudge_region(g, center=(433, -31), radius=90, dx=-12, dy=2, falloff=1.3)
    g.notes.append("edit: tail-12")
    return g


@register("uni306E")  # の
def edit_no(g: Glyph) -> Glyph:
    g = g.copy()
    # the stroke ends with a blunt cut at the bottom: let it run out and thin
    nudge_region(g, center=(464, 8), radius=80, dx=-14, dy=-2, falloff=1.3)
    g.notes.append("edit: tail-14")
    return g


@register("uni308A")  # り
def edit_ri(g: Glyph) -> Glyph:
    g = g.copy()
    nudge_region(g, center=(368, -62), radius=85, dx=-9, dy=-8, falloff=1.3)
    g.notes.append("edit: tail-9/-8")
    return g


@register("uni306F")  # は
def edit_ha(g: Glyph) -> Glyph:
    g = g.copy()
    # final hook: a touch longer and lifted, like a brush leaving the paper
    nudge_region(g, center=(920, 45), radius=70, dx=8, dy=4, falloff=1.3)
    g.notes.append("edit: hook+8/+4")
    return g


@register("uni304B")  # か
def edit_ka(g: Glyph) -> Glyph:
    g = g.copy()
    b = g.bounds()
    # the right-hand dot: nudge it a little outward for a lighter rhythm
    if b:
        nudge_region(g, center=(b[2] - 40, 560), radius=70, dx=4, dy=3, falloff=1.3)
    g.notes.append("edit: dot+4/+3")
    return g


@register("uni3059")  # す
def edit_su(g: Glyph) -> Glyph:
    g = g.copy()
    b = g.bounds()
    if b:
        # the tail at the bottom: lengthen to the left
        nudge_region(g, center=(b[0] + 120, b[1] + 10), radius=80, dx=-8, dy=-4, falloff=1.3)
    g.notes.append("edit: tail-8/-4")
    return g


# ---------------------------------------------------------------------------
# Latin: a delicate upward sweep at the exit serif of m n h u a d i l r k p q
# ---------------------------------------------------------------------------

def _find_exit_serif(g: Glyph):
    """Locate (contour index, BR index) of the bottom-right foot serif.

    Nanum's feet are drawn (CCW) bottom-left → bottom-right (BR) → top-right (TR)
    → bracket (BRK) → stem.  Returns None if the glyph has no such foot."""
    best = None
    for ci, c in enumerate(g.contours):
        n = len(c)
        for i, nd in enumerate(c):
            if not (-10 <= nd.y <= 22):
                continue
            tr = c[(i + 1) % n]; brk = c[(i + 2) % n]
            if abs(tr.x - nd.x) > 4 or not (18 <= tr.y - nd.y <= 60):
                continue
            if not (brk.y > tr.y + 5 and brk.x < tr.x - 25):
                continue
            if best is None or nd.x > best[2]:
                best = (ci, i, nd.x)
    if best is None:
        return None
    b = g.bounds()
    if b and best[2] < b[2] - 60:   # must be the right-most feature of the glyph
        return None
    return best[0], best[1]


def exit_sweep(g: Glyph, lift: float = 9.0, extend: float = 10.0) -> bool:
    hit = _find_exit_serif(g)
    if hit is None:
        return False
    ci, i = hit
    c = g.contours[ci]; n = len(c)
    br = c[i]; tr = c[(i + 1) % n]; brk = c[(i + 2) % n]
    # extend the foot to the right, lifting its outer corner into a soft flick
    br.x += extend * 0.6
    tr.x += extend; tr.y += lift
    # top edge: bracket → TR becomes a shallow curve that dips, then rises
    span = tr.x - brk.x
    brk.hout = (brk.x + span * 0.45, brk.y - (brk.y - tr.y) * 0.95)
    tr.hin = (tr.x - span * 0.25, tr.y - lift * 0.85)
    # right edge: a slightly convex curve instead of a vertical cut
    tr.hout = (tr.x + 2.0, tr.y - (tr.y - br.y) * 0.45)
    br.hin = (br.x + 2.5, br.y + (tr.y - br.y) * 0.35)
    for nd in (br, tr, brk):
        nd.tag = "edit"
    return True


@register("m", "n", "h", "u", "a", "d", "i", "l", "r", "k", "p", "q", "uniFF4D", "uniFF4E", "uniFF48",
          "uniFF55", "uniFF41", "uniFF44", "uniFF49", "uniFF4C", "uniFF52", "uniFF4B", "uniFF50", "uniFF51")
def edit_exit_sweep(g: Glyph) -> Glyph:
    g = g.copy()
    if exit_sweep(g):
        g.notes.append("edit: exit sweep")
    return g

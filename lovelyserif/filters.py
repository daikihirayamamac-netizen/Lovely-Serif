"""Outline filters that give Lovely Serif its character.

The filters work on the cubic :class:`~lovelyserif.outline.Glyph` model and
are deliberately parametric so that the same "hand" is applied consistently
to thousands of glyphs:

* :func:`soften_corners` — replaces every sharp corner by a small fillet.
  Convex ink corners (stroke ends, the triangular *uroko* serif of Mincho
  horizontals, serif ends in the Latin) get a larger radius than concave
  corners (where strokes meet), and acute tips (the *harai* sweeps) get a
  tiny constant trim so they stay pointed but not needle-sharp.
* :func:`smooth_joins` — makes nearly-smooth joins truly tangent-continuous
  (used for kana, whose brush entries have small tangent breaks).
* :func:`remove_tiny_segments` — merges 1–2 unit flats so they round as one
  corner.
* :func:`remove_overlaps` — boolean union via skia-pathops (TrueType sources).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, List, Optional

from .geometry import (Seg, add, cross, dist, dot, length, lerp, mul, norm,
                       signed_angle, sub)
from .outline import Contour, Glyph, Node, contour_area


@dataclass(frozen=True)
class SoftenParams:
    r_convex: float = 13.0      # fillet radius for convex ink corners (stroke ends, uroko)
    r_concave: float = 6.0      # fillet radius for concave corners (stroke junctions)
    d_tip: float = 9.0          # trim length for acute tips (harai, serif points)
    tip_angle_deg: float = 112.0  # turning angle beyond which a corner counts as a tip
    min_angle_deg: float = 9.0  # ignore turns smaller than this
    soft_angle_deg: float = 32.0  # below this, scale the fillet down (gentle joins)
    handle_factor: float = 1.0  # 1.0 = circular fillet, >1 = squarer
    max_frac: float = 0.42      # fillet trim may not eat more than this fraction of a segment
    min_trim: float = 1.2       # skip fillets smaller than this
    tiny_segment: float = 2.5   # pre-merge straight segments shorter than this


DEFAULT_PARAMS = SoftenParams()


def contour_to_segs(c: Contour) -> List[Seg]:
    segs: List[Seg] = []
    n = len(c)
    for i in range(n):
        a = c[i]; b = c[(i + 1) % n]
        if a.hout is None and b.hin is None:
            segs.append(Seg(a.pt, b.pt))
        else:
            segs.append(Seg(a.pt, b.pt, a.hout if a.hout is not None else a.pt, b.hin if b.hin is not None else b.pt))
    return segs


def segs_to_contour(segs: List[Seg]) -> Contour:
    nodes: Contour = []
    n = len(segs)
    for i, s in enumerate(segs):
        prev = segs[i - 1]
        node = Node(s.p0[0], s.p0[1])
        if prev.kind == "curve":
            node.hin = prev.c2
        if s.kind == "curve":
            node.hout = s.c1
        if s.tag == "fillet" or prev.tag == "fillet":
            node.tag = "fillet"
        nodes.append(node)
    return nodes


def remove_tiny_segments(c: Contour, min_len: float = 2.5) -> Contour:
    """Drop on-curve nodes that are joined to their predecessor by a very short line."""
    if len(c) < 4:
        return c
    out: Contour = [n.copy() for n in c]
    changed = True
    guard = 0
    while changed and len(out) >= 4 and guard < 50:
        changed = False
        guard += 1
        for i in range(len(out)):
            a = out[i - 1]; b = out[i]
            if a.hout is None and b.hin is None and dist(a.pt, b.pt) < min_len:
                # merge b into a: keep a's position, but inherit b's outgoing handle
                a.hout = b.hout
                del out[i]
                changed = True
                break
    return out


def _fillet_params_for(theta: float, p: SoftenParams, convex: bool):
    """Return (trim distance d, handle length factor) for a turning angle theta (radians, abs)."""
    deg = math.degrees(theta)
    if deg < p.min_angle_deg:
        return 0.0, 0.0
    r = p.r_convex if convex else p.r_concave
    if deg > p.tip_angle_deg:
        d = p.d_tip if convex else min(p.d_tip, r)
    else:
        d = r * math.tan(theta / 2.0)
    if deg < p.soft_angle_deg:
        d *= (deg - p.min_angle_deg) / (p.soft_angle_deg - p.min_angle_deg) * 0.8 + 0.2
    return d, 0.0


def soften_corners(glyph: Glyph, params: SoftenParams = DEFAULT_PARAMS, scale: float = 1.0) -> Glyph:
    """Return a copy of ``glyph`` with every sharp corner filleted.

    ``scale`` multiplies all radii (used for small glyphs such as ruby forms
    or to tune per-script strength)."""
    p = params
    if scale != 1.0:
        p = replace(params, r_convex=params.r_convex * scale, r_concave=params.r_concave * scale,
                    d_tip=params.d_tip * scale)
    g = glyph.copy()
    new_contours: List[Contour] = []
    n_fillets = 0
    for contour in g.contours:
        contour = remove_tiny_segments(contour, p.tiny_segment)
        if len(contour) < 3:
            new_contours.append(contour)
            continue
        segs = contour_to_segs(contour)
        n = len(segs)
        fillets: Dict[int, Seg] = {}
        for j in range(n):
            A = segs[j - 1]; B = segs[j]
            tA = A.end_tangent(); tB = B.start_tangent()
            if length(tA) == 0 or length(tB) == 0:
                continue
            theta = signed_angle(tA, tB)
            convex = theta > 0  # ink on the left: a left turn is a convex ink corner
            d, _ = _fillet_params_for(abs(theta), p, convex)
            if d <= 0:
                continue
            lenA = A.length(); lenB = B.length()
            d = min(d, p.max_frac * lenA, p.max_frac * lenB)
            if d < p.min_trim:
                continue
            A.trim_end(d); B.trim_start(d)
            PA = A.p3; PB = B.p0
            tA2 = A.end_tangent(); tB2 = B.start_tangent()
            th = abs(signed_angle(tA2, tB2))
            if th < 1e-3:
                continue
            # circular-arc handle length for the actual radius R = d / tan(th/2)
            R = d / math.tan(th / 2.0)
            h = (4.0 / 3.0) * math.tan(th / 4.0) * R * p.handle_factor
            h = min(h, dist(PA, PB) * 0.75)
            f = Seg(PA, PB, add(PA, mul(tA2, h)), sub(PB, mul(tB2, h)), tag="fillet")
            fillets[j] = f
            n_fillets += 1
        out: List[Seg] = []
        for j in range(n):
            if j in fillets:
                out.append(fillets[j])
            out.append(segs[j])
        new_contours.append(segs_to_contour(out))
    g.contours = new_contours
    if n_fillets:
        g.notes.append(f"soften_corners({n_fillets})")
    return g


def smooth_joins(glyph: Glyph, max_angle_deg: float = 22.0, min_angle_deg: float = 0.3) -> Glyph:
    """Make small tangent breaks between curve segments tangent-continuous."""
    g = glyph.copy()
    count = 0
    for contour in g.contours:
        n = len(contour)
        for i in range(n):
            node = contour[i]
            prev = contour[i - 1]; nxt = contour[(i + 1) % n]
            if node.tag == "fillet":
                continue
            vin = sub(node.pt, node.hin) if node.hin is not None else sub(node.pt, prev.pt)
            vout = sub(node.hout, node.pt) if node.hout is not None else sub(nxt.pt, node.pt)
            if length(vin) < 1e-6 or length(vout) < 1e-6:
                continue
            ang = abs(math.degrees(signed_angle(vin, vout)))
            if ang < min_angle_deg or ang > max_angle_deg:
                continue
            if node.hin is not None and node.hout is not None:
                u = norm(add(norm(vin), norm(vout)))
                node.hin = sub(node.pt, mul(u, length(vin)))
                node.hout = add(node.pt, mul(u, length(vout)))
            elif node.hin is not None:  # curve in, line out: align incoming handle to the line
                u = norm(vout)
                node.hin = sub(node.pt, mul(u, length(vin)))
            elif node.hout is not None:
                u = norm(vin)
                node.hout = add(node.pt, mul(u, length(vout)))
            else:
                continue
            count += 1
    if count:
        g.notes.append(f"smooth_joins({count})")
    return g


def remove_overlaps(glyph: Glyph) -> Glyph:
    """Boolean union of all contours (skia-pathops); also fixes winding direction
    to the PostScript convention (outer contours counter-clockwise)."""
    import pathops
    from fontTools.pens.recordingPen import RecordingPen
    path = pathops.Path()
    glyph.draw(path.getPen())
    before = len(list(path.contours))
    result = pathops.simplify(path, fix_winding=True, keep_starting_points=False)
    rp = RecordingPen()
    result.draw(rp)
    g = Glyph.from_pen_records(glyph.name, rp.value, glyph.width)
    g.unicodes = list(glyph.unicodes); g.source = glyph.source; g.notes = list(glyph.notes)
    # skia yields clockwise outer contours; flip to the CFF convention
    areas = g.signed_areas()
    if areas and sum(areas) < 0:
        g.reverse()
    g.notes.append("remove_overlaps")
    return g


def ensure_ps_direction(glyph: Glyph) -> Glyph:
    """Reverse all contours if the dominant (largest) contour is clockwise."""
    areas = glyph.signed_areas()
    if not areas:
        return glyph
    big = max(range(len(areas)), key=lambda i: abs(areas[i]))
    if areas[big] < 0:
        glyph.reverse()
    return glyph


# ---------------------------------------------------------------------------
# Outline offset (used to harmonise the Latin stroke weight with the kanji)
# ---------------------------------------------------------------------------

def _right_normal(t):
    return (t[1], -t[0])


def _line_intersection(p1, d1, p2, d2):
    """Intersection of lines p1 + s·d1 and p2 + u·d2 (None if parallel)."""
    den = cross(d1, d2)
    if abs(den) < 1e-9:
        return None
    s = cross(sub(p2, p1), d2) / den
    return add(p1, mul(d1, s))


def _offset_seg(seg: Seg, delta: float) -> Seg:
    """Tiller–Hanson offset of a single segment (ink on the left; +delta expands ink)."""
    if seg.kind == "line":
        n = _right_normal(seg.start_tangent())
        return Seg(add(seg.p0, mul(n, delta)), add(seg.p3, mul(n, delta)))
    pts = [seg.p0, seg.c1, seg.c2, seg.p3]
    edges = []
    for a, b in zip(pts, pts[1:]):
        d = sub(b, a)
        if length(d) < 1e-6:
            edges.append(None)
        else:
            edges.append((a, norm(d)))
    # replace degenerate edges by their neighbours' directions
    for i in range(3):
        if edges[i] is None:
            alt = edges[i - 1] if i > 0 and edges[i - 1] is not None else (edges[i + 1] if i < 2 else None)
            if alt is None:
                n = _right_normal(seg.start_tangent())
                return Seg(add(seg.p0, mul(n, delta)), add(seg.p3, mul(n, delta)),
                           add(seg.c1, mul(n, delta)), add(seg.c2, mul(n, delta)))
            edges[i] = (pts[i], alt[1])
    sh = []
    for (a, d) in edges:
        n = _right_normal(d)
        sh.append((add(a, mul(n, delta)), d))
    p0 = sh[0][0]
    p3 = add(pts[3], mul(_right_normal(edges[2][1]), delta))
    c1 = _line_intersection(sh[0][0], sh[0][1], sh[1][0], sh[1][1])
    c2 = _line_intersection(sh[1][0], sh[1][1], sh[2][0], sh[2][1])
    if c1 is None:
        c1 = add(pts[1], mul(_right_normal(edges[0][1]), delta))
    if c2 is None:
        c2 = add(pts[2], mul(_right_normal(edges[2][1]), delta))
    # guard against runaway intersections on nearly-parallel edges
    for q, orig in ((c1, pts[1]), (c2, pts[2])):
        if dist(q, orig) > abs(delta) * 6 + 2:
            n = _right_normal(edges[1][1])
            c1 = add(pts[1], mul(n, delta)); c2 = add(pts[2], mul(n, delta))
            break
    return Seg(p0, p3, c1, c2)


def offset_outline(glyph: Glyph, delta: float, join: str = "round") -> Glyph:
    """Expand (+delta) or contract (−delta) the ink of a glyph by offsetting every
    contour.  Convex corners receive a small round join; the result is cleaned
    with a boolean union so the crossing loops that appear at concave corners
    disappear."""
    g = glyph.copy()
    new_contours: List[Contour] = []
    for contour in g.contours:
        segs = contour_to_segs(contour)
        off = [_offset_seg(s, delta) for s in segs]
        out: List[Seg] = []
        n = len(off)
        for j in range(n):
            A = off[j - 1]; B = off[j]
            if dist(A.p3, B.p0) > 0.05:
                tA = segs[j - 1].end_tangent(); tB = segs[j].start_tangent()
                theta = signed_angle(tA, tB)
                if theta > 0.02 and join == "round" and delta > 0:
                    # convex ink corner: arc around the original vertex
                    V = segs[j].p0
                    R = delta
                    h = (4.0 / 3.0) * math.tan(abs(theta) / 4.0) * R
                    out.append(Seg(A.p3, B.p0, add(A.p3, mul(tA, h)), sub(B.p0, mul(tB, h)), tag="join"))
                else:
                    out.append(Seg(A.p3, B.p0, tag="join"))
            out.append(B)
        new_contours.append(segs_to_contour(out))
    g.contours = new_contours
    g = remove_overlaps(g)
    g.notes = [x for x in g.notes if x != "remove_overlaps"] + [f"offset({delta:+g})"]
    return g

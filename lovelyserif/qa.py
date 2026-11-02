"""Automated outline QA: compares every glyph before/after the design pass.

Flags
-----
self_intersect   a contour crosses itself after the design pass (but not before)
xor              area of (before XOR after) / area(before) above threshold
area             total ink area changed by more than threshold
bbox             bounding box moved by more than threshold (units)
degenerate       zero-length segment or contour with < 3 nodes
direction        outer contour not counter-clockwise (CFF convention)
emptied          glyph had ink before and none after
"""
from __future__ import annotations

from typing import Dict, List

import pathops

from .outline import Glyph


def _path(g: Glyph, contours=None) -> pathops.Path:
    p = pathops.Path()
    pen = p.getPen()
    gg = g if contours is None else Glyph(g.name, g.width, contours)
    gg.draw(pen)
    return p


def _area(p: pathops.Path) -> float:
    return abs(pathops.simplify(p, fix_winding=False).area)


def self_intersecting(g: Glyph) -> List[int]:
    bad = []
    for i, c in enumerate(g.contours):
        if len(c) < 2:
            continue
        p = _path(g, [c])
        s = pathops.simplify(p, fix_winding=False)
        n = len(list(s.contours))
        if n > 1:
            # tiny loops (< 1 unit²) are rasteriser-invisible noise but still a bug
            bad.append(i)
    return bad


def raster(g: Glyph, size: int = 128, upm: int = 1000, ymin: float = -150) -> "np.ndarray":
    """Non-zero winding rasterisation (same fill rule as FreeType / CoreText)."""
    import numpy as np
    from .outline import flatten_contour
    edges = []
    for c in g.contours:
        pts = flatten_contour(c, 12)
        for i in range(len(pts)):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
            if y0 != y1:
                edges.append((x0, y0, x1, y1))
    img = np.zeros((size, size), dtype=bool)
    if not edges:
        return img
    E = np.array(edges)
    scale = size / (upm + 100)
    px = (np.arange(size) + 0.5) / scale - 50
    for r in range(size):
        y = ymin + (r + 0.5) / scale
        y0, y1 = E[:, 1], E[:, 3]
        m = ((y0 <= y) & (y1 > y)) | ((y1 <= y) & (y0 > y))
        if not m.any():
            continue
        e = E[m]
        t = (y - e[:, 1]) / (e[:, 3] - e[:, 1])
        xs = e[:, 0] + t * (e[:, 2] - e[:, 0])
        ds = np.where(e[:, 3] > e[:, 1], 1, -1)
        wind = (ds[None, :] * (xs[None, :] > px[:, None])).sum(axis=1)
        img[r] = wind != 0
    return img


def analyze(name: str, before: Glyph, after: Glyph, hand: bool,
            xor_thr: float = 0.08, area_thr: float = 0.06, bbox_thr: float = 12.0) -> Dict:
    issues: Dict[str, object] = {}
    if not before.contours:
        return issues
    if not after.contours:
        issues["emptied"] = True
        return issues
    rb = raster(before); ra = raster(after)
    nb = int(rb.sum())
    if nb < 4:
        return issues
    xr = float((rb ^ ra).sum()) / nb
    if xr > xor_thr and not hand:
        issues["xor"] = round(xr, 3)
    ar = (float(ra.sum()) - nb) / nb
    if abs(ar) > area_thr and not hand:
        issues["area"] = round(ar, 3)
    bb = before.bounds(); ba = after.bounds()
    drift = max(abs(bb[i] - ba[i]) for i in range(4))
    if drift > bbox_thr and not hand:
        issues["bbox"] = round(drift, 1)
    si_after = self_intersecting(after)
    if si_after:
        si_before = self_intersecting(before)
        if len(si_after) > len(si_before):
            issues["self_intersect"] = si_after
    deg = 0
    for c in after.contours:
        if len(c) < 3:
            deg += 1
        for j in range(len(c)):
            a, b = c[j - 1], c[j]
            if abs(a.x - b.x) < 0.5 and abs(a.y - b.y) < 0.5:
                deg += 1
    if deg:
        issues["degenerate"] = deg
    areas = after.signed_areas()
    if areas:
        big = max(range(len(areas)), key=lambda k: abs(areas[k]))
        if areas[big] < 0:
            issues["direction"] = True
    return issues

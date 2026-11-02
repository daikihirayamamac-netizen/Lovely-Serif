"""Editable cubic outline model.

A glyph outline is a list of closed contours.  A contour is a list of
``Node`` objects; each node is an on-curve point with an optional incoming
handle (``hin``, the second control point of the segment that ends at the
node) and an optional outgoing handle (``hout``, the first control point of
the segment that starts at the node).  A segment with no handles at either
end is a straight line.

All outlines are kept in the PostScript/CFF orientation convention: outer
contours run counter-clockwise, so the ink is always on the *left* of the
direction of travel.  TrueType sources (clockwise outer contours) are
reversed on import and reversed again when quadratic outlines are written.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

from fontTools.pens.basePen import decomposeQuadraticSegment
from fontTools.pens.recordingPen import DecomposingRecordingPen

Point = Tuple[float, float]


@dataclass
class Node:
    x: float
    y: float
    hin: Optional[Point] = None
    hout: Optional[Point] = None
    tag: str = ""  # free-form marker used by filters ("fillet", "edit", ...)

    @property
    def pt(self) -> Point:
        return (self.x, self.y)

    def copy(self) -> "Node":
        return Node(self.x, self.y, self.hin, self.hout, self.tag)


Contour = List[Node]


@dataclass
class Glyph:
    name: str
    width: float = 0
    contours: List[Contour] = field(default_factory=list)
    unicodes: List[int] = field(default_factory=list)
    source: str = ""          # "nanum" | "noto" | "synth"
    notes: List[str] = field(default_factory=list)  # applied filters / edits

    def copy(self) -> "Glyph":
        return Glyph(self.name, self.width, [[n.copy() for n in c] for c in self.contours],
                     list(self.unicodes), self.source, list(self.notes))

    # -- geometry helpers -------------------------------------------------
    def bounds(self) -> Optional[Tuple[float, float, float, float]]:
        xs: List[float] = []
        ys: List[float] = []
        for c in self.contours:
            for n in c:
                xs.append(n.x); ys.append(n.y)
                for h in (n.hin, n.hout):
                    if h is not None:
                        xs.append(h[0]); ys.append(h[1])
        if not xs:
            return None
        return (min(xs), min(ys), max(xs), max(ys))

    def transform(self, sx=1.0, sy=None, dx=0.0, dy=0.0) -> None:
        if sy is None:
            sy = sx
        for c in self.contours:
            for n in c:
                n.x = n.x * sx + dx
                n.y = n.y * sy + dy
                if n.hin is not None:
                    n.hin = (n.hin[0] * sx + dx, n.hin[1] * sy + dy)
                if n.hout is not None:
                    n.hout = (n.hout[0] * sx + dx, n.hout[1] * sy + dy)
        self.width = self.width * sx

    def round(self) -> None:
        for c in self.contours:
            for n in c:
                n.x = float(round(n.x)); n.y = float(round(n.y))
                if n.hin is not None:
                    n.hin = (float(round(n.hin[0])), float(round(n.hin[1])))
                if n.hout is not None:
                    n.hout = (float(round(n.hout[0])), float(round(n.hout[1])))
        self.width = float(round(self.width))

    def cleanup(self, eps: float = 0.6) -> int:
        """Remove degenerate (zero-length) segments and empty contours; returns removed node count."""
        removed = 0
        new_contours = []
        for c in self.contours:
            i = 0
            while len(c) >= 2 and i < len(c):
                a = c[i - 1]; b = c[i]
                if _close(a.pt, b.pt, eps):
                    h1 = a.hout; h2 = b.hin
                    if (h1 is None or _close(h1, a.pt, eps * 2)) and (h2 is None or _close(h2, b.pt, eps * 2)):
                        a.hout = b.hout
                        del c[i]; removed += 1
                        continue
                i += 1
            if len(c) >= 3 or (len(c) == 2 and abs(contour_area(c)) > 4.0):
                new_contours.append(c)
            else:
                removed += len(c)
        self.contours = new_contours
        return removed

    def node_count(self) -> int:
        return sum(len(c) for c in self.contours)

    # -- pen I/O ----------------------------------------------------------
    def draw(self, pen) -> None:
        """Draw cubic outline onto a (segment) pen."""
        for contour in self.contours:
            if not contour:
                continue
            n0 = contour[0]
            pen.moveTo(n0.pt)
            for i in range(len(contour)):
                a = contour[i]
                b = contour[(i + 1) % len(contour)]
                if a.hout is None and b.hin is None:
                    if i == len(contour) - 1:
                        pass  # closePath draws the closing line
                    else:
                        pen.lineTo(b.pt)
                else:
                    c1 = a.hout if a.hout is not None else a.pt
                    c2 = b.hin if b.hin is not None else b.pt
                    pen.curveTo(c1, c2, b.pt)
            pen.closePath()

    @classmethod
    def from_pen_records(cls, name: str, records, width: float = 0) -> "Glyph":
        """Build from a RecordingPen value list (lines, cubics, quadratics)."""
        g = cls(name, width)
        contour: Contour = []
        cur: Optional[Point] = None
        start: Optional[Point] = None
        pending_hin: Optional[Point] = None

        def finish():
            nonlocal contour, pending_hin
            if contour:
                # closing segment handle (curve back to start)
                if pending_hin is not None:
                    contour[0].hin = pending_hin
                # merge duplicated closing point
                if len(contour) > 1 and _close(contour[-1].pt, contour[0].pt) and contour[-1].hout is None and contour[0].hin is None:
                    last = contour.pop()
                    if last.hin is not None:
                        contour[0].hin = last.hin
                g.contours.append(contour)
            contour = []
            pending_hin = None

        for op, args in records:
            if op == "moveTo":
                finish()
                cur = start = args[0]
                contour = [Node(cur[0], cur[1])]
            elif op == "lineTo":
                p = args[0]
                if pending_hin is not None:
                    contour[-1].hin = pending_hin; pending_hin = None
                if cur is not None and _close(p, cur):
                    continue
                contour.append(Node(p[0], p[1]))
                cur = p
            elif op == "curveTo":
                # args: c1, c2, ..., p  (fontTools may pass more than 2 control points; handle 2)
                pts = list(args)
                if len(pts) == 3:
                    c1, c2, p = pts
                elif len(pts) == 2:  # degenerate: treat as quadratic
                    q, p = pts
                    c1 = _lerp(cur, q, 2 / 3); c2 = _lerp(p, q, 2 / 3)
                elif len(pts) == 1:
                    p = pts[0]; c1 = cur; c2 = p
                else:  # split super-bezier approximately: use first and last controls
                    c1, c2, p = pts[0], pts[-2], pts[-1]
                contour[-1].hout = c1
                if _close(p, start) and False:
                    pass
                contour.append(Node(p[0], p[1], hin=c2))
                cur = p
            elif op == "qCurveTo":
                pts = list(args)
                if pts[-1] is None:  # all off-curve, TrueType special case
                    # implied on-curve point between last and first off-curves
                    pts = pts[:-1]
                    implied = _lerp(pts[-1], pts[0], 0.5)
                    pts = pts + [implied]
                    # start a new contour at implied point if we are at a moveTo-less start
                    if cur is None:
                        cur = start = implied
                        contour = [Node(cur[0], cur[1])]
                for q, p in decomposeQuadraticSegment(pts):
                    c1 = _lerp(cur, q, 2 / 3); c2 = _lerp(p, q, 2 / 3)
                    contour[-1].hout = c1
                    contour.append(Node(p[0], p[1], hin=c2))
                    cur = p
            elif op == "closePath" or op == "endPath":
                # drop a trailing node equal to start
                if contour and len(contour) > 1 and _close(contour[-1].pt, contour[0].pt):
                    last = contour.pop()
                    contour[0].hin = last.hin
                finish()
                cur = start = None
        finish()
        g.contours = [c for c in g.contours if len(c) >= 2]
        return g

    @classmethod
    def from_font_glyph(cls, glyphset, name: str, width: float = 0) -> "Glyph":
        rp = DecomposingRecordingPen(glyphset)
        glyphset[name].draw(rp)
        return cls.from_pen_records(name, rp.value, width)

    def reverse(self) -> None:
        for c in self.contours:
            _reverse_contour(c)

    def signed_areas(self) -> List[float]:
        return [contour_area(c) for c in self.contours]


def _close(a: Point, b: Point, eps: float = 1e-6) -> bool:
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def _lerp(a: Point, b: Point, t: float) -> Point:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _reverse_contour(c: Contour) -> None:
    c.reverse()
    for n in c:
        n.hin, n.hout = n.hout, n.hin


def contour_area(c: Contour) -> float:
    """Signed area using a flattened polygon (positive = counter-clockwise)."""
    pts = flatten_contour(c, 8)
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def flatten_contour(c: Contour, steps: int = 8) -> List[Point]:
    pts: List[Point] = []
    n = len(c)
    for i in range(n):
        a = c[i]; b = c[(i + 1) % n]
        if a.hout is None and b.hin is None:
            pts.append(a.pt)
        else:
            c1 = a.hout if a.hout is not None else a.pt
            c2 = b.hin if b.hin is not None else b.pt
            for s in range(steps):
                t = s / steps
                pts.append(cubic_point(a.pt, c1, c2, b.pt, t))
    return pts


def cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    mt = 1 - t
    a = mt * mt * mt; b = 3 * mt * mt * t; c = 3 * mt * t * t; d = t * t * t
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
            a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])

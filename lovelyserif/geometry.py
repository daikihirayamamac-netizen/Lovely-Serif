"""Small vector / Bézier helpers used by the filters."""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from fontTools.misc.bezierTools import approximateCubicArcLength, splitCubicAtT

Point = Tuple[float, float]


def sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])


def mul(a: Point, s: float) -> Point:
    return (a[0] * s, a[1] * s)


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def length(v: Point) -> float:
    return math.hypot(v[0], v[1])


def norm(v: Point) -> Point:
    l = math.hypot(v[0], v[1])
    if l < 1e-12:
        return (0.0, 0.0)
    return (v[0] / l, v[1] / l)


def lerp(a: Point, b: Point, t: float) -> Point:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def rotate(v: Point, ang: float) -> Point:
    c, s = math.cos(ang), math.sin(ang)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def signed_angle(a: Point, b: Point) -> float:
    """Signed angle (radians) turning from direction a to direction b; + = left turn."""
    return math.atan2(cross(a, b), dot(a, b))


class Seg:
    """A line or cubic segment with mutable end points."""
    __slots__ = ("p0", "c1", "c2", "p3", "kind", "tag")

    def __init__(self, p0: Point, p3: Point, c1: Optional[Point] = None, c2: Optional[Point] = None, tag: str = ""):
        self.p0 = p0; self.p3 = p3
        if c1 is None and c2 is None:
            self.kind = "line"; self.c1 = None; self.c2 = None
        else:
            self.kind = "curve"
            self.c1 = c1 if c1 is not None else p0
            self.c2 = c2 if c2 is not None else p3
        self.tag = tag

    def length(self) -> float:
        if self.kind == "line":
            return dist(self.p0, self.p3)
        return approximateCubicArcLength(self.p0, self.c1, self.c2, self.p3)

    def start_tangent(self) -> Point:
        if self.kind == "line":
            return norm(sub(self.p3, self.p0))
        for q in (self.c1, self.c2, self.p3):
            v = sub(q, self.p0)
            if length(v) > 1e-9:
                return norm(v)
        return (0.0, 0.0)

    def end_tangent(self) -> Point:
        if self.kind == "line":
            return norm(sub(self.p3, self.p0))
        for q in (self.c2, self.c1, self.p0):
            v = sub(self.p3, q)
            if length(v) > 1e-9:
                return norm(v)
        return (0.0, 0.0)

    def point_at(self, t: float) -> Point:
        if self.kind == "line":
            return lerp(self.p0, self.p3, t)
        from .outline import cubic_point
        return cubic_point(self.p0, self.c1, self.c2, self.p3, t)

    def trim_start(self, d: float) -> None:
        """Remove the first ``d`` units (arc length) of the segment."""
        if d <= 0:
            return
        if self.kind == "line":
            L = dist(self.p0, self.p3)
            self.p0 = lerp(self.p0, self.p3, min(d / L, 0.95))
            return
        t = self._t_for_length_from_start(d)
        _, second = splitCubicAtT(self.p0, self.c1, self.c2, self.p3, t)
        self.p0, self.c1, self.c2, self.p3 = second

    def trim_end(self, d: float) -> None:
        if d <= 0:
            return
        if self.kind == "line":
            L = dist(self.p0, self.p3)
            self.p3 = lerp(self.p3, self.p0, min(d / L, 0.95))
            return
        t = 1.0 - self._t_for_length_from_end(d)
        first, _ = splitCubicAtT(self.p0, self.c1, self.c2, self.p3, t)
        self.p0, self.c1, self.c2, self.p3 = first

    def _t_for_length_from_start(self, d: float) -> float:
        L = self.length()
        if L <= 1e-9:
            return 0.5
        t = min(max(d / L, 0.01), 0.95)
        for _ in range(3):
            first, _ = splitCubicAtT(self.p0, self.c1, self.c2, self.p3, t)
            l = approximateCubicArcLength(*first)
            t = min(max(t - (l - d) / L, 0.01), 0.95)
        return t

    def _t_for_length_from_end(self, d: float) -> float:
        # returns the parameter length (from the end) as a fraction s so that split at 1-s
        L = self.length()
        if L <= 1e-9:
            return 0.5
        s = min(max(d / L, 0.01), 0.95)
        for _ in range(3):
            _, second = splitCubicAtT(self.p0, self.c1, self.c2, self.p3, 1.0 - s)
            l = approximateCubicArcLength(*second)
            s = min(max(s - (l - d) / L, 0.01), 0.95)
        return s

    def reversed(self) -> "Seg":
        return Seg(self.p3, self.p0, self.c2, self.c1, self.tag)

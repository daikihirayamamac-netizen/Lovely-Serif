"""SVG rendering helpers for previews, comparisons and reports."""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

from fontTools.pens.svgPathPen import SVGPathPen

from .outline import Glyph


def glyph_path_d(glyph: Glyph) -> str:
    pen = SVGPathPen(None)
    glyph.draw(pen)
    return pen.getCommands()


def glyph_svg(glyph: Glyph, size: int = 300, upm: int = 1000, descent: int = 120,
              fill: str = "#111", show_nodes: bool = False, ghost: Optional[Glyph] = None,
              ghost_fill: str = "rgba(220,40,40,0.35)", label: str = "") -> str:
    """Render one glyph (optionally over a ghost of another) as a standalone SVG."""
    s = size / upm
    w = int(max(glyph.width, upm) * s) + 4
    h = int((upm + descent) * s) + 4
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    out.append(f'<g transform="translate(2,{(upm - descent) * s + 2}) scale({s},{-s})">')
    out.append(f'<line x1="0" y1="0" x2="{glyph.width}" y2="0" stroke="#bbb" stroke-width="{1/s}"/>')
    if ghost is not None:
        out.append(f'<path d="{glyph_path_d(ghost)}" fill="{ghost_fill}"/>')
    out.append(f'<path d="{glyph_path_d(glyph)}" fill="{fill}" fill-rule="nonzero"/>')
    if show_nodes:
        r = 2.2 / s
        for c in glyph.contours:
            for n in c:
                col = "#e33" if n.tag != "fillet" else "#27c"
                if n.hin is not None:
                    out.append(f'<line x1="{n.x}" y1="{n.y}" x2="{n.hin[0]}" y2="{n.hin[1]}" stroke="#2a7" stroke-width="{0.7/s}"/>')
                    out.append(f'<circle cx="{n.hin[0]}" cy="{n.hin[1]}" r="{r*0.7}" fill="#2a7"/>')
                if n.hout is not None:
                    out.append(f'<line x1="{n.x}" y1="{n.y}" x2="{n.hout[0]}" y2="{n.hout[1]}" stroke="#2a7" stroke-width="{0.7/s}"/>')
                    out.append(f'<circle cx="{n.hout[0]}" cy="{n.hout[1]}" r="{r*0.7}" fill="#2a7"/>')
                out.append(f'<circle cx="{n.x}" cy="{n.y}" r="{r}" fill="{col}"/>')
    out.append('</g>')
    if label:
        out.append(f'<text x="4" y="{h-6}" font-family="sans-serif" font-size="12" fill="#666">{label}</text>')
    out.append('</svg>')
    return "\n".join(out)


def compare_svg(before: Glyph, after: Glyph, size: int = 320, upm: int = 1000, descent: int = 120,
                title: str = "") -> str:
    """Three panels: before (grey), after (black), overlay with nodes."""
    s = size / upm
    cw = int(max(before.width, after.width, upm) * s) + 8
    ch = int((upm + descent) * s) + 30
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{cw*3}" height="{ch}" viewBox="0 0 {cw*3} {ch}" style="background:#fff">']
    def panel(ix, g, fill, ghost=None, nodes=False, lab=""):
        out.append(f'<g transform="translate({ix*cw+4},{(upm - descent) * s + 22})"><g transform="scale({s},{-s})">')
        out.append(f'<line x1="0" y1="0" x2="{max(g.width,upm)}" y2="0" stroke="#ccc" stroke-width="{1/s}"/>')
        if ghost is not None:
            out.append(f'<path d="{glyph_path_d(ghost)}" fill="none" stroke="#d33" stroke-width="{1.2/s}" stroke-dasharray="{4/s},{3/s}"/>')
        out.append(f'<path d="{glyph_path_d(g)}" fill="{fill}" stroke="none"/>')
        if nodes:
            r = 2.0 / s
            for c in g.contours:
                for n in c:
                    col = "#27c" if n.tag == "fillet" else "#e33"
                    out.append(f'<circle cx="{n.x}" cy="{n.y}" r="{r}" fill="{col}"/>')
        out.append('</g></g>')
        out.append(f'<text x="{ix*cw+6}" y="16" font-family="sans-serif" font-size="13" fill="#555">{lab}</text>')
    panel(0, before, "#777", lab=f"before · {before.node_count()} nodes")
    panel(1, after, "#111", lab=f"after · {after.node_count()} nodes")
    panel(2, after, "rgba(0,0,0,0.10)", ghost=before, nodes=True, lab=title or "overlay (red = original)")
    out.append('</svg>')
    return "\n".join(out)


def text_svg(glyphs: Sequence[Glyph], size: int = 72, upm: int = 1000, fill: str = "#111",
             tracking: float = 0.0, descent: int = 120) -> str:
    s = size / upm
    x = 0.0
    paths = []
    for g in glyphs:
        paths.append(f'<g transform="translate({x*s:.2f},0) scale({s},{-s})"><path d="{glyph_path_d(g)}" fill="{fill}"/></g>')
        x += g.width + tracking
    w = int(x * s) + 8
    h = int((upm + descent) * s) + 8
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           f'<g transform="translate(4,{(upm - descent) * s + 4})">', *paths, '</g></svg>']
    return "\n".join(out)

"""The Lovely Serif build pipeline.

    upstream fonts ──▶ subset Noto Serif JP (layout features kept)
                   ──▶ extract cubic outlines (Noto CFF, Nanum TrueType→cubic)
                   ──▶ assemble: Nanum Latin replaces Noto Latin, fullwidth Latin synthesised
                   ──▶ rename glyphs (AGL / uniXXXX / .vert …)
                   ──▶ design pass: per-glyph edits + corner softening + kana smoothing
                   ──▶ compile OTF (CFF), TTF (glyf via cu2qu), WOFF2, UFO master
                   ──▶ reports (glyph status, coverage, before/after SVGs)
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from fontTools import subset
from fontTools.agl import UV2AGL
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.ttLib.tables.ttProgram import Program

from . import config as C
from . import coverage as COV
from .config import EXCLUDE_CODEPOINTS as COV_EXCLUDE
from .edits import REGISTRY as EDITS, PARAM_SCALE
from .filters import (ensure_ps_direction, offset_outline, remove_overlaps,
                      smooth_joins, soften_corners)
from .outline import Glyph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 1. subset Noto Serif JP
# ---------------------------------------------------------------------------

def subset_noto(path: str, unicodes: Set[int]) -> TTFont:
    font = TTFont(path)
    opts = subset.Options()
    opts.layout_features = list(C.KEEP_FEATURES)
    opts.layout_scripts = ["*"]
    opts.glyph_names = True
    opts.notdef_outline = True
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.name_legacy = True
    opts.hinting = False
    opts.desubroutinize = True
    opts.drop_tables = ["DSIG"]
    opts.passthrough_tables = False
    opts.prune_unicode_ranges = True
    opts.recalc_bounds = True
    opts.recalc_average_width = True
    opts.retain_gids = False
    opts.ignore_missing_unicodes = True
    s = subset.Subsetter(opts)
    s.populate(unicodes=sorted(unicodes))
    s.subset(font)
    return font


# ---------------------------------------------------------------------------
# 2. glyph extraction
# ---------------------------------------------------------------------------

@dataclass
class Master:
    glyphs: Dict[str, Glyph] = field(default_factory=dict)       # by *new* name
    order: List[str] = field(default_factory=list)
    cmap: Dict[int, str] = field(default_factory=dict)
    vmetrics: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # name -> (advanceHeight, vertOriginY)
    category: Dict[str, str] = field(default_factory=dict)
    originals: Dict[str, Glyph] = field(default_factory=dict)      # pre-design outlines
    old_names: Dict[str, str] = field(default_factory=dict)        # new -> old (cidNNNNN)
    uvs: Dict[int, List[Tuple[int, Optional[str]]]] = field(default_factory=dict)
    kerning: Dict[Tuple[str, str], int] = field(default_factory=dict)
    skeleton: Optional[TTFont] = None


def extract_noto(noto: TTFont) -> Tuple[Dict[str, Glyph], Dict[str, Tuple[int, int]]]:
    gs = noto.getGlyphSet()
    hmtx = noto["hmtx"]; vmtx = noto["vmtx"]
    vorg = noto["VORG"]
    default_vorg = vorg.defaultVertOriginY
    glyphs: Dict[str, Glyph] = {}
    vmet: Dict[str, Tuple[int, int]] = {}
    for name in noto.getGlyphOrder():
        g = Glyph.from_font_glyph(gs, name, hmtx[name][0])
        g.name = name; g.source = "noto"
        ensure_ps_direction(g)
        glyphs[name] = g
        vmet[name] = (vmtx[name][0], vorg.VOriginRecords.get(name, default_vorg))
    return glyphs, vmet


def extract_nanum(nanum: TTFont, codepoints: Set[int]) -> Dict[int, Glyph]:
    gs = nanum.getGlyphSet(); cmap = nanum.getBestCmap(); hmtx = nanum["hmtx"]
    out: Dict[int, Glyph] = {}
    for cp in sorted(codepoints):
        gname = cmap.get(cp)
        if gname is None:
            continue
        g = Glyph.from_font_glyph(gs, gname, hmtx[gname][0])
        g.name = gname; g.source = "nanum"; g.unicodes = [cp]
        g.transform(C.NANUM_SCALE)
        if g.contours:
            g = remove_overlaps(g)   # TrueType → PostScript direction, overlaps unioned
        out[cp] = g
    return out


def nanum_kerning(nanum: TTFont) -> Dict[Tuple[str, str], int]:
    """Latin kerning pairs of Nanum Myeongjo as {(leftName, rightName): xAdvance} in 1000 upm."""
    pairs: Dict[Tuple[str, str], int] = {}
    if "GPOS" not in nanum:
        return pairs
    gpos = nanum["GPOS"].table
    for lk in gpos.LookupList.Lookup:
        subtables = lk.SubTable
        if lk.LookupType == 9:
            subtables = [st.ExtSubTable for st in subtables]
        for st in subtables:
            if getattr(st, "LookupType", None) != 2 and lk.LookupType not in (2, 9):
                continue
            if st.Format == 1:
                for g1, ps in zip(st.Coverage.glyphs, st.PairSet):
                    for pvr in ps.PairValueRecord:
                        v = getattr(pvr.Value1, "XAdvance", 0) if pvr.Value1 else 0
                        if v:
                            pairs[(g1, pvr.SecondGlyph)] = int(round(v * C.NANUM_SCALE))
            elif st.Format == 2:
                c1 = st.ClassDef1.classDefs; c2 = st.ClassDef2.classDefs
                by1: Dict[int, List[str]] = {}
                for g in st.Coverage.glyphs:
                    by1.setdefault(c1.get(g, 0), []).append(g)
                by2: Dict[int, List[str]] = {}
                for g, k in c2.items():
                    by2.setdefault(k, []).append(g)
                for k1, rec1 in enumerate(st.Class1Record):
                    for k2, rec2 in enumerate(rec1.Class2Record):
                        v = getattr(rec2.Value1, "XAdvance", 0) if rec2.Value1 else 0
                        if not v or k2 == 0:
                            continue
                        for g1 in by1.get(k1, []):
                            for g2 in by2.get(k2, []):
                                pairs[(g1, g2)] = int(round(v * C.NANUM_SCALE))
    return pairs


# ---------------------------------------------------------------------------
# 3. naming
# ---------------------------------------------------------------------------

def unicode_name(cp: int) -> str:
    if cp in UV2AGL and cp < 0x3000:
        return UV2AGL[cp]
    return f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:04X}"


def _lookups_for_feature(table, tag: str) -> List[int]:
    idx: List[int] = []
    for fr in table.FeatureList.FeatureRecord:
        if fr.FeatureTag == tag:
            idx.extend(fr.Feature.LookupListIndex)
    return idx


def _iter_subtables(lookup):
    for st in lookup.SubTable:
        if lookup.LookupType == 7:
            yield st.ExtSubTable
        else:
            yield st


def derive_names(noto: TTFont) -> Dict[str, str]:
    """Map every cidNNNNN glyph to a readable name."""
    def _rank(cp: int):
        # prefer the "real" character over radicals / compatibility / presentation forms
        secondary = (0x2E80 <= cp <= 0x2FDF) or (0xF900 <= cp <= 0xFAFF) or (0xFE30 <= cp <= 0xFE4F) or (0xFE10 <= cp <= 0xFE1F) or (0x2F800 <= cp <= 0x2FA1F)
        return (secondary, cp)
    cmap = {}
    for t in noto["cmap"].tables:
        if t.isUnicode():
            for cp, gn in t.cmap.items():
                if gn not in cmap or _rank(cp) < _rank(cmap[gn]):
                    cmap[gn] = cp
    # unicode-mapped glyphs: name from the lowest code point
    names: Dict[str, str] = {".notdef": ".notdef"}
    used: Set[str] = {".notdef"}
    for gn in noto.getGlyphOrder():
        if gn in cmap:
            nm = unicode_name(cmap[gn])
            if nm in used:
                k = 2
                while f"{nm}.{k}" in used:
                    k += 1
                nm = f"{nm}.{k}"
            names[gn] = nm; used.add(nm)
    gsub = noto["GSUB"].table
    lookup_tags: Dict[int, str] = {}
    priority = ["vert", "vrt2", "fwid", "hwid", "pwid", "liga", "ccmp", "locl", "jp78", "jp83", "jp90", "jp04",
                "nlck", "hist", "ruby", "expt", "dlig", "aalt"]
    for tag in priority:
        for li in _lookups_for_feature(gsub, tag):
            lookup_tags.setdefault(li, tag)
    # chained contextual lookups delegate to nested lookups
    for li, lk in enumerate(gsub.LookupList.Lookup):
        if li not in lookup_tags:
            continue
        for st in _iter_subtables(lk):
            for attr in ("SubstLookupRecord",):
                pass
            recs = []
            if hasattr(st, "ChainSubRuleSet") and st.ChainSubRuleSet:
                for rs in st.ChainSubRuleSet:
                    for r in rs.ChainSubRule:
                        recs.extend(r.SubstLookupRecord)
            if hasattr(st, "ChainSubClassSet") and st.ChainSubClassSet:
                for cs in st.ChainSubClassSet:
                    if cs is None:
                        continue
                    for r in cs.ChainSubClassRule:
                        recs.extend(r.SubstLookupRecord)
            if hasattr(st, "SubstLookupRecord") and st.SubstLookupRecord:
                recs.extend(st.SubstLookupRecord)
            for rec in recs:
                lookup_tags.setdefault(rec.LookupListIndex, lookup_tags[li])
    for _pass in range(3):
        for li, lk in enumerate(gsub.LookupList.Lookup):
            tag = lookup_tags.get(li)
            if tag is None or tag == "aalt":
                continue
            for st in _iter_subtables(lk):
                mapping = {}
                if lk.LookupType == 1:
                    mapping = st.mapping
                elif lk.LookupType == 3:
                    mapping = {k: v[0] for k, v in st.alternates.items() if v}
                elif lk.LookupType == 2:
                    mapping = {k: v[0] for k, v in st.mapping.items() if len(v) == 1}
                elif lk.LookupType == 4:
                    for first, ligs in st.ligatures.items():
                        for lig in ligs:
                            if lig.LigGlyph in names or first not in names:
                                continue
                            comps = [first] + list(lig.Component)
                            if all(c in names for c in comps):
                                nm = "_".join(names[c] for c in comps)
                                if nm not in used:
                                    names[lig.LigGlyph] = nm; used.add(nm)
                    continue
                for src, dst in mapping.items():
                    if dst in names or src not in names:
                        continue
                    base = names[src]
                    nm = f"{base}.{tag}"
                    k = 2
                    while nm in used:
                        nm = f"{base}.{tag}{k}"; k += 1
                    names[dst] = nm; used.add(nm)
    for gn in noto.getGlyphOrder():
        if gn not in names:
            names[gn] = gn  # keep cidNNNNN
    return names


# ---------------------------------------------------------------------------
# 4. assemble
# ---------------------------------------------------------------------------

def categorize(name: str, cps: List[int], source: str) -> str:
    cp = cps[0] if cps else None
    base = name.split(".")[0]
    if cp is None and base.startswith("uni") and len(base) == 7:
        try:
            cp = int(base[3:], 16)
        except ValueError:
            cp = None
    if cp is None and base.startswith("u") and len(base) >= 6 and base[1:].isalnum():
        try:
            cp = int(base[1:], 16)
        except ValueError:
            cp = None
    if cp is None and base in UV2AGL.values():
        from fontTools.agl import AGL2UV
        cp = AGL2UV.get(base)
    if source == "nanum":
        return "latin"
    if source == "synth":
        return "latin-fw"
    if cp is None:
        return "other"
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF or cp >= 0x20000 or 0x2E80 <= cp <= 0x2FDF or cp in (0x3005, 0x3006, 0x3007):
        return "kanji"
    if 0x3041 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF or 0xFF66 <= cp <= 0xFF9F:
        return "kana"
    if 0x3000 <= cp <= 0x303F or 0xFF01 <= cp <= 0xFF65 or 0xFFE0 <= cp <= 0xFFEF or 0xFE30 <= cp <= 0xFE4F or 0xFE10 <= cp <= 0xFE1F:
        return "punct"
    if cp < 0x0250 or 0x2010 <= cp <= 0x205E or 0x02C6 <= cp <= 0x02DD:
        return "latin-noto"
    if 0x2500 <= cp <= 0x259F:
        return "box"
    return "symbol"



def _contour_bbox(c):
    xs = [n.x for n in c]; ys = [n.y for n in c]
    for n in c:
        for h in (n.hin, n.hout):
            if h is not None:
                xs.append(h[0]); ys.append(h[1])
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_of(contours):
    bbs = [_contour_bbox(c) for c in contours]
    return (min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs))


def _accent_by_difference(comp: Glyph, base: Glyph, base_cp: int) -> List:
    """Accent = Noto precomposed glyph minus Noto base letter (for cedilla / ogonek drawn
    in one contour with the letter).  Slivers along the shared edge are dropped."""
    import pathops
    from fontTools.pens.recordingPen import RecordingPen
    pc = pathops.Path(); comp.draw(pc.getPen())
    pb = pathops.Path(); base.draw(pb.getPen())
    bb_base = _bbox_of(base.contours)
    clip = pathops.Path(); cp_ = clip.getPen()
    top = bb_base[1] + 14   # marks below the letter only (cedilla / ogonek / comma below)
    cp_.moveTo((-1000, -1000)); cp_.lineTo((2000, -1000)); cp_.lineTo((2000, top)); cp_.lineTo((-1000, top)); cp_.closePath()
    try:
        d = pathops.op(pathops.simplify(pc, fix_winding=False), pathops.simplify(pb, fix_winding=False),
                       pathops.PathOp.DIFFERENCE)
        d = pathops.op(d, clip, pathops.PathOp.INTERSECTION)
    except pathops.PathOpsError:
        return []
    rp = RecordingPen(); d.draw(rp)
    g = Glyph.from_pen_records("acc", rp.value)
    from .outline import contour_area
    # keep only the mark itself: pieces that hang below the baseline (cedilla, ogonek, comma) or sit
    # above the letter; long hairline slivers along the shared edge are rejected by their thickness
    keep = []
    for c in g.contours:
        a = abs(contour_area(c))
        bb = _contour_bbox(c)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        thickness = a / max(w, h, 1)
        below = bb[1] < bb_base[1] - 20
        if a > 400 and thickness > 8 and below:
            keep.append(c)
    if not keep or len(keep) > 3:
        return []
    # skia returns clockwise outer contours; flip to the CFF convention
    tmp = Glyph("acc", 0, keep); ensure_ps_direction(tmp)
    return tmp.contours


def compose_accented(m: "Master", noto_glyphs: Dict[str, Glyph], noto_cmap: Dict[int, str],
                     nanum_glyphs: Dict[int, Glyph]) -> int:
    """Rebuild accented Latin letters (À é ñ ü ç ő …) on Nanum Myeongjo base letters.

    Nanum Myeongjo has no precomposed accented letters, so v0.1 fell back to Noto Serif JP's
    heavier Latin for them.  Here the accent contours are lifted out of Noto's precomposed glyph
    (every contour that is not part of Noto's own base letter), re-positioned relative to the
    Nanum base (horizontal centre, and cap-height / x-height difference for marks above) and
    combined with the Nanum base outline."""
    import unicodedata
    count = 0
    for cp in sorted(m.cmap):
        if not (0x00C0 <= cp <= 0x017F):
            continue
        name = m.cmap[cp]
        g = m.glyphs[name]
        if g.source != "noto":
            continue
        dec = unicodedata.decomposition(chr(cp)).split()
        if len(dec) != 2 or dec[0].startswith("<"):
            continue
        base_cp = int(dec[0], 16)
        # recursively decomposed bases (e.g. Ǖ) are out of range here; Ã etc. are direct
        if base_cp not in nanum_glyphs or base_cp not in noto_cmap:
            continue
        noto_comp = noto_glyphs[m.old_names[name]]
        noto_base = noto_glyphs[noto_cmap[base_cp]]
        if not noto_comp.contours or not noto_base.contours:
            continue
        base_bbs = [_contour_bbox(c) for c in noto_base.contours]
        accent = []
        for c in noto_comp.contours:
            bb = _contour_bbox(c)
            if any(max(abs(bb[i] - b[i]) for i in range(4)) < 6 for b in base_bbs):
                continue
            accent.append([n.copy() for n in c])
        merged = False
        bbb = _bbox_of(noto_base.contours)
        def _overlaps_base(c):
            bb = _contour_bbox(c)
            ix = max(0.0, min(bb[2], bbb[2]) - max(bb[0], bbb[0])); iy = max(0.0, min(bb[3], bbb[3]) - max(bb[1], bbb[1]))
            return ix * iy > 0.3 * (bbb[2] - bbb[0]) * (bbb[3] - bbb[1])
        if any(_overlaps_base(c) for c in accent):
            accent = []   # base and mark share one contour (Ç ç): cut the mark out instead
        if not accent or len(accent) > 3:
            accent = _accent_by_difference(noto_comp, noto_base, base_cp)
            merged = True
        if not accent:
            continue
        nb = nanum_glyphs[base_cp].copy()
        if base_cp in (0x69, 0x6A) and len(nb.contours) >= 2:
            # dotless form for í ì î ï ĵ: drop the dot (the topmost contour)
            nb.contours.remove(max(nb.contours, key=lambda c: _contour_bbox(c)[1]))
        # base letter geometry (Noto base without its i/j dot, for a fair centre)
        nbase_contours = noto_base.contours
        if base_cp in (0x69, 0x6A) and len(nbase_contours) >= 2:
            nbase_contours = sorted(nbase_contours, key=lambda c: _contour_bbox(c)[1])[:-1]
        nbb = _bbox_of(nbase_contours)
        lbb = nb.bounds()
        abb = _bbox_of(accent)
        above = abb[1] > (nbb[1] + nbb[3]) / 2
        if above:
            dy = lbb[3] - nbb[3]
            # keep the original gap between letter and accent
        else:
            dy = lbb[1] - nbb[1]
        if dec[1] in ("0328",):  # ogonek hangs from the right foot
            dx = lbb[2] - nbb[2]
        elif dec[1] in ("0327",):  # cedilla centred under the letter
            dx = (lbb[0] + lbb[2]) / 2 - (nbb[0] + nbb[2]) / 2
        else:
            dx = (lbb[0] + lbb[2]) / 2 - (nbb[0] + nbb[2]) / 2
        acc = Glyph("acc", 0, accent)
        acc.transform(1.0, 1.0, dx, dy)
        out = nb.copy()
        out.contours = nb.contours + acc.contours
        out.name = name; out.unicodes = list(g.unicodes); out.source = "nanum"
        if merged:
            out = remove_overlaps(out)
            out.name = name; out.unicodes = list(g.unicodes); out.source = "nanum"
        out.notes = ["composed: nanum base + accent"]
        m.glyphs[name] = out
        m.category[name] = "latin"
        count += 1
    return count


def assemble(noto: TTFont, nanum: TTFont, nanum_glyphs: Dict[int, Glyph]) -> Master:
    m = Master()
    m.skeleton = noto
    noto_glyphs, vmet = extract_noto(noto)
    names = derive_names(noto)
    cmap = noto.getBestCmap()
    rev: Dict[str, List[int]] = {}
    for cp, gn in cmap.items():
        rev.setdefault(gn, []).append(cp)
    order_old = noto.getGlyphOrder()
    replaced = 0
    for old in order_old:
        new = names[old]
        g = noto_glyphs[old]
        cps = sorted(rev.get(old, []))
        # Latin from Nanum?
        nanum_cp = next((cp for cp in cps if cp in nanum_glyphs and cp not in COV.JAPANESE_PRIORITY), None)
        if nanum_cp is not None:
            ng = nanum_glyphs[nanum_cp].copy()
            ng.name = new; ng.unicodes = cps
            g = ng; replaced += 1
        g.name = new; g.unicodes = cps
        m.glyphs[new] = g
        m.order.append(new)
        m.old_names[new] = old
        m.vmetrics[new] = vmet[old]
        m.category[new] = categorize(new, cps, g.source)
        for cp in cps:
            m.cmap[cp] = new
    # Nanum glyphs whose code points Noto Serif JP lacks (Œ œ Ł ł Đ đ Ħ ħ Ŋ ŋ …)
    added = 0
    for cp, ng in sorted(nanum_glyphs.items()):
        if cp in m.cmap or cp in COV_EXCLUDE:
            continue
        new = unicode_name(cp)
        if new in m.glyphs:
            continue
        g = ng.copy(); g.name = new; g.unicodes = [cp]
        m.glyphs[new] = g; m.order.append(new); m.cmap[cp] = new
        m.vmetrics[new] = (1000, C.METRICS["defaultVertOrigin"]); m.category[new] = "latin"
        added += 1
    composed = compose_accented(m, noto_glyphs, cmap, nanum_glyphs)
    # fullwidth ASCII (U+FF01–FF5E) synthesised from the Nanum Latin, centred in the em
    synth = 0
    for cp in range(0xFF01, 0xFF5F):
        ascii_cp = cp - 0xFEE0
        new = m.cmap.get(cp)
        if new is None or ascii_cp not in nanum_glyphs:
            continue
        src = nanum_glyphs[ascii_cp]
        g = src.copy(); g.name = new; g.unicodes = [cp]; g.source = "synth"
        g.transform(1.0, 1.0, (1000 - src.width) / 2.0, 0.0); g.width = 1000
        m.glyphs[new] = g; m.category[new] = "latin-fw"; synth += 1
    # UVS (Ideographic Variation Sequences) from Noto's format-14 cmap
    for t in noto["cmap"].tables:
        if t.format == 14:
            for uvs, entries in t.uvsDict.items():
                lst = []
                for uni, gn in entries:
                    if gn is None:
                        if uni in m.cmap:
                            lst.append((uni, None))
                    elif gn in names:
                        lst.append((uni, names[gn]))
                if lst:
                    m.uvs[uvs] = lst
    # kerning from Nanum (names are AGL names on both sides)
    pairs = nanum_kerning(nanum)
    for (a, b), v in pairs.items():
        if a in m.glyphs and b in m.glyphs and m.glyphs[a].source == "nanum" and m.glyphs[b].source == "nanum":
            m.kerning[(a, b)] = v
    log(f"assembled {len(m.order)} glyphs; {replaced} Latin glyphs from Nanum, {synth} fullwidth synthesised, {composed} accented letters composed, {added} Nanum-only glyphs added, "
        f"{len(m.kerning)} kern pairs, {len(m.uvs)} UVS selectors")
    return m


# ---------------------------------------------------------------------------
# 5. design pass
# ---------------------------------------------------------------------------

def _shape(g: Glyph, cat: str, name: str, mult: float) -> Glyph:
    """Corner softening / smoothing / weight for one glyph; ``mult`` scales every radius."""
    b = g.bounds()
    height = (b[3] - b[1]) if b else 0
    pscale = PARAM_SCALE.get(name, 1.0) * mult
    if cat == "kanji":
        g = soften_corners(g, C.KANJI_PARAMS, min(1.0, max(0.55, height / 800.0)) * pscale)
    elif cat == "kana":
        g = smooth_joins(g, C.KANA_SMOOTH_ANGLE)
        g = soften_corners(g, C.KANA_PARAMS, min(1.0, max(0.55, height / 760.0)) * pscale)
    elif cat in ("latin", "latin-fw"):
        g = soften_corners(g, C.LATIN_PARAMS, pscale)
        if C.LATIN_OFFSET:
            g = offset_outline(g, C.LATIN_OFFSET)
            if cat == "latin":
                # keep the original sidebearings: the ink grew by LATIN_OFFSET on each side
                g.transform(1.0, 1.0, C.LATIN_OFFSET, 0.0)
                g.width += 2 * C.LATIN_OFFSET
    elif cat == "latin-noto":
        g = soften_corners(g, C.LATIN_PARAMS, 1.3 * pscale)
    elif cat == "punct":
        g = soften_corners(g, C.PUNCT_PARAMS, pscale)
    g.round()
    g.cleanup(1.2)
    return g


def design_pass(m: Master) -> Dict[str, dict]:
    from .qa import self_intersecting
    status: Dict[str, dict] = {}
    retried = []
    for name in list(m.glyphs):
        g = m.glyphs[name]
        cat = m.category[name]
        before = g.copy()
        m.originals[name] = before
        edited = False
        if name in EDITS:
            for fn in EDITS[name]:
                g = fn(g)
            edited = any(n.startswith("edit:") for n in g.notes)
            if edited:
                g.notes.append("hand_edit")
            if "edit: exit sweep" in g.notes and cat == "latin":
                g.width += 6  # the foot grew to the right; give it room
        if not g.contours or cat in ("box", "symbol", "other"):
            m.glyphs[name] = g
            status[name] = dict(category=cat, source=g.source, modified=bool(edited), notes=list(g.notes),
                                nodes_before=before.node_count(), nodes_after=g.node_count())
            continue
        base_si = len(self_intersecting(g))
        out = None
        for mult in (1.0, 0.6, 0.35, 0.0):
            cand = _shape(g.copy(), cat, name, mult) if mult else g.copy()
            if mult == 0.0:
                cand.round(); cand.cleanup(1.2)
            if len(self_intersecting(cand)) <= base_si:
                out = cand
                if mult < 1.0:
                    out.notes.append(f"fallback(radius x{mult})")
                    retried.append(name)
                break
        g = out
        m.glyphs[name] = g
        status[name] = dict(category=cat, source=g.source, modified=bool(g.notes), notes=list(g.notes),
                            nodes_before=before.node_count(), nodes_after=g.node_count(), hand_edit=edited)
    if retried:
        log(f"design pass: {len(retried)} glyphs re-shaped with smaller radii to avoid self-intersection: {' '.join(retried[:20])}")
    return status


# ---------------------------------------------------------------------------
# 6. compile
# ---------------------------------------------------------------------------

def _name_strings() -> dict:
    ver = f"{C.VERSION_FIXED:.3f}"
    return dict(
        copyright=C.COPYRIGHT,
        familyName={"en": C.FAMILY, "ja": C.FAMILY_JA},
        styleName={"en": C.STYLE, "ja": "レギュラー"},
        uniqueFontIdentifier=f"{ver};{C.VENDOR_ID};{C.PS_NAME}",
        fullName={"en": f"{C.FAMILY} {C.STYLE}", "ja": f"{C.FAMILY_JA} レギュラー"},
        version=f"Version {ver}",
        psName=C.PS_NAME,
        manufacturer="The Lovely Serif Project",
        designer="The Lovely Serif Project (Latin after Nanum Myeongjo by FONTRIX; Japanese after Noto Serif JP / Source Han Serif by Ryoko Nishizuka)",
        description=C.DESCRIPTION,
        vendorURL="https://github.com/daikihirayamamac-netizen/lovely-serif",
        designerURL="https://github.com/daikihirayamamac-netizen/lovely-serif",
        licenseDescription=C.LICENSE_TEXT,
        licenseInfoURL=C.LICENSE_URL,
        typographicFamily={"en": C.FAMILY, "ja": C.FAMILY_JA},
        typographicSubfamily={"en": C.STYLE, "ja": "レギュラー"},
        sampleText="文字から、美しさを。Beauty in every letter.",
    )


def _layout_xml(skeleton: TTFont, rename: Dict[str, str], tmpdir: str) -> str:
    """Dump GSUB/GPOS/GDEF/BASE of the subset font with glyph names rewritten."""
    tables = [t for t in ("GDEF", "GSUB", "GPOS", "BASE") if t in skeleton]
    path = os.path.join(tmpdir, "layout.ttx")
    skeleton.saveXML(path, tables=tables)
    text = open(path, encoding="utf-8").read()
    text = re.sub(r"\bcid\d{5}\b", lambda mo: rename.get(mo.group(0), mo.group(0)), text)
    out = os.path.join(tmpdir, "layout_renamed.ttx")
    open(out, "w", encoding="utf-8").write(text)
    return out


def _strip_feature(table, tag: str) -> None:
    """Remove a feature (and its lookups if unreferenced) from a GSUB/GPOS table."""
    fl = table.FeatureList
    drop = {i for i, fr in enumerate(fl.FeatureRecord) if fr.FeatureTag == tag}
    if not drop:
        return
    remap: Dict[int, int] = {}
    new_records = []
    for i, fr in enumerate(fl.FeatureRecord):
        if i in drop:
            continue
        remap[i] = len(new_records); new_records.append(fr)
    fl.FeatureRecord = new_records; fl.FeatureCount = len(new_records)
    for sr in table.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [l.LangSys for l in sr.Script.LangSysRecord]:
            if ls is None:
                continue
            ls.FeatureIndex = [remap[i] for i in ls.FeatureIndex if i in remap]
            ls.FeatureCount = len(ls.FeatureIndex)
            if ls.ReqFeatureIndex not in remap and ls.ReqFeatureIndex != 0xFFFF:
                ls.ReqFeatureIndex = 0xFFFF


def _sort_features(table) -> None:
    """Keep FeatureList sorted by tag (required by the spec; OTS warns otherwise)."""
    fl = table.FeatureList
    order = sorted(range(len(fl.FeatureRecord)), key=lambda i: fl.FeatureRecord[i].FeatureTag)
    remap = {old: new for new, old in enumerate(order)}
    fl.FeatureRecord = [fl.FeatureRecord[i] for i in order]
    for sr in table.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [l.LangSys for l in sr.Script.LangSysRecord]:
            if ls is None:
                continue
            ls.FeatureIndex = sorted(remap[i] for i in ls.FeatureIndex)
            if ls.ReqFeatureIndex != 0xFFFF:
                ls.ReqFeatureIndex = remap[ls.ReqFeatureIndex]


def _add_kern_feature(gpos, pairs: Dict[Tuple[str, str], int], glyph_map: Dict[str, int]) -> None:
    from fontTools.otlLib import builder as otl
    from fontTools.ttLib.tables import otTables as ot
    if not pairs:
        return
    pp = {}
    for (a, b), v in pairs.items():
        pp[(a, b)] = (otl.buildValue({"XAdvance": v}), None)
    st = otl.buildPairPosGlyphsSubtable(pp, glyph_map)
    lookup = otl.buildLookup([st])
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    li = gpos.LookupList.LookupCount - 1
    feat = ot.Feature(); feat.FeatureParams = None; feat.LookupListIndex = [li]; feat.LookupCount = 1
    fr = ot.FeatureRecord(); fr.FeatureTag = "kern"; fr.Feature = feat
    gpos.FeatureList.FeatureRecord.append(fr)
    gpos.FeatureList.FeatureCount = len(gpos.FeatureList.FeatureRecord)
    fi = gpos.FeatureList.FeatureCount - 1
    for sr in gpos.ScriptList.ScriptRecord:
        if sr.ScriptTag not in ("DFLT", "latn"):
            continue
        for ls in [sr.Script.DefaultLangSys] + [l.LangSys for l in sr.Script.LangSysRecord]:
            if ls is None:
                continue
            ls.FeatureIndex.append(fi); ls.FeatureCount = len(ls.FeatureIndex)


def _common_tables(fb: FontBuilder, m: Master, is_ttf: bool, tmpdir: str) -> None:
    font = fb.font
    fb.setupCharacterMap(m.cmap)
    # Unicode variation sequences
    if m.uvs:
        cmap = font["cmap"]
        sub14 = CmapSubtable.newSubtable(14)
        sub14.platformID = 0; sub14.platEncID = 5; sub14.language = 0
        sub14.cmap = {}
        sub14.uvsDict = {k: list(v) for k, v in m.uvs.items()}
        cmap.tables.append(sub14)
        cmap.tables.sort(key=lambda t: (t.platformID, t.platEncID, t.format))
    fb.setupHorizontalHeader(ascent=C.METRICS["hheaAscent"], descent=C.METRICS["hheaDescent"], lineGap=C.METRICS["hheaLineGap"])
    fb.setupNameTable(_name_strings(), mac=False)
    fb.setupOS2(
        version=4, usWeightClass=400, usWidthClass=5, fsType=0, achVendID=C.VENDOR_ID,
        sTypoAscender=C.METRICS["typoAscender"], sTypoDescender=C.METRICS["typoDescender"], sTypoLineGap=C.METRICS["typoLineGap"],
        usWinAscent=C.METRICS["winAscent"], usWinDescent=C.METRICS["winDescent"],
        sxHeight=C.METRICS["xHeight"], sCapHeight=C.METRICS["capHeight"],
        fsSelection=0x0040, ulCodePageRange1=(1 << 0) | (1 << 17), ulCodePageRange2=0,
        panose=dict(bFamilyType=2, bSerifStyle=2, bWeight=5, bProportion=3, bContrast=5, bStrokeVariation=4,
                    bArmStyle=5, bLetterForm=2, bMidline=3, bXHeight=4),
        yStrikeoutSize=50, yStrikeoutPosition=258, ySubscriptXSize=650, ySubscriptYSize=600, ySubscriptYOffset=75,
        ySuperscriptXSize=650, ySuperscriptYSize=600, ySuperscriptYOffset=350,
    )
    font["OS/2"].recalcUnicodeRanges(font)
    fb.setupPost(keepGlyphNames=not is_ttf, underlinePosition=C.METRICS["underlinePosition"], underlineThickness=C.METRICS["underlineThickness"])
    head = font["head"]
    head.fontRevision = C.VERSION_FIXED
    head.flags = 0x000B
    head.lowestRecPPEM = 6
    # vertical metrics
    vmet = {}
    for name in m.order:
        adv, origin = m.vmetrics[name]
        b = m.glyphs[name].bounds()
        ymax = b[3] if b else 0
        vmet[name] = (adv, int(round(origin - ymax)))
    fb.setupVerticalMetrics(vmet)
    fb.setupVerticalHeader(ascent=C.METRICS["vheaAscent"], descent=C.METRICS["vheaDescent"], lineGap=C.METRICS["vheaLineGap"])
    if not is_ttf:
        origins = {n: o for n, (a, o) in m.vmetrics.items() if o != C.METRICS["defaultVertOrigin"]}
        fb.setupVerticalOrigins(origins, C.METRICS["defaultVertOrigin"])
    # OpenType layout from Noto (renamed), minus Noto's Latin kerning, plus Nanum's
    rename = {old: new for new, old in m.old_names.items()}
    xml = _layout_xml(m.skeleton, rename, tmpdir)
    font.importXML(xml)
    if "GPOS" in font:
        _strip_feature(font["GPOS"].table, "kern")
        _strip_feature(font["GPOS"].table, "mark")
        _strip_feature(font["GPOS"].table, "mkmk")
        _add_kern_feature(font["GPOS"].table, m.kerning, font.getReverseGlyphMap())
        _sort_features(font["GPOS"].table)
    if "GSUB" in font:
        _sort_features(font["GSUB"].table)
    if is_ttf:
        gasp = newTable("gasp"); gasp.version = 1; gasp.gaspRange = {0xFFFF: 0x000F}
        font["gasp"] = gasp
        # minimal prep program enabling smart dropout control (as gftools fix-nonhinting does)
        prep = newTable("prep"); prep.program = Program()
        prep.program.fromBytecode(bytes([0xB8, 0x01, 0xFF, 0x85, 0xB0, 0x04, 0x8D]))
        font["prep"] = prep
        maxp = font["maxp"]
        maxp.maxStackElements = max(getattr(maxp, "maxStackElements", 0), 64)
        maxp.maxFunctionDefs = max(getattr(maxp, "maxFunctionDefs", 0), 0)
        maxp.maxInstructionDefs = max(getattr(maxp, "maxInstructionDefs", 0), 0)
        maxp.maxSizeOfInstructions = max(getattr(maxp, "maxSizeOfInstructions", 0), 7)
        maxp.maxTwilightPoints = max(getattr(maxp, "maxTwilightPoints", 0), 0)
        maxp.maxStorage = max(getattr(maxp, "maxStorage", 0), 0)
        maxp.maxZones = max(getattr(maxp, "maxZones", 1), 1)


def compile_otf(m: Master, tmpdir: str) -> TTFont:
    fb = FontBuilder(C.UPM, isTTF=False)
    fb.setupGlyphOrder(m.order)
    charstrings = {}
    metrics = {}
    for name in m.order:
        g = m.glyphs[name]
        pen = T2CharStringPen(g.width, None)
        g.draw(pen)
        charstrings[name] = pen.getCharString()
        bp = BoundsPen(None); g.draw(bp)
        lsb = int(round(bp.bounds[0])) if bp.bounds else 0
        metrics[name] = (int(round(g.width)), lsb)
    fb.setupCFF(C.PS_NAME, {"FullName": f"{C.FAMILY} {C.STYLE}", "FamilyName": C.FAMILY, "Weight": C.STYLE,
                            "version": f"{C.VERSION_FIXED:.3f}", "Notice": C.COPYRIGHT[:200], "ItalicAngle": 0,
                            "UnderlinePosition": C.METRICS["underlinePosition"], "UnderlineThickness": C.METRICS["underlineThickness"]},
                charstrings, {})
    fb.setupHorizontalMetrics(metrics)
    _common_tables(fb, m, False, tmpdir)
    return fb.font


def compile_ttf(m: Master, tmpdir: str, max_err: float = 1.0) -> TTFont:
    fb = FontBuilder(C.UPM, isTTF=True)
    fb.setupGlyphOrder(m.order)
    glyf = {}
    for name in m.order:
        g = m.glyphs[name]
        tp = TTGlyphPen(None)
        pen = Cu2QuPen(tp, max_err=max_err, reverse_direction=True)
        g.draw(pen)
        glyf[name] = tp.glyph()
    fb.setupGlyf(glyf)
    metrics = {}
    for name in m.order:
        gl = fb.font["glyf"][name]
        lsb = gl.xMin if hasattr(gl, "xMin") and gl.numberOfContours else 0
        metrics[name] = (int(round(m.glyphs[name].width)), lsb)
    fb.setupHorizontalMetrics(metrics)
    _common_tables(fb, m, True, tmpdir)
    return fb.font


# ---------------------------------------------------------------------------
# 7. UFO export
# ---------------------------------------------------------------------------

def export_ufo(m: Master, path: str) -> None:
    import ufoLib2
    ufo = ufoLib2.Font()
    info = ufo.info
    info.familyName = C.FAMILY; info.styleName = C.STYLE
    info.unitsPerEm = C.UPM; info.versionMajor = 0; info.versionMinor = 100
    info.ascender = C.METRICS["typoAscender"]; info.descender = C.METRICS["typoDescender"]
    info.xHeight = C.METRICS["xHeight"]; info.capHeight = C.METRICS["capHeight"]
    info.copyright = C.COPYRIGHT
    info.openTypeNameLicense = C.LICENSE_TEXT; info.openTypeNameLicenseURL = C.LICENSE_URL
    info.openTypeNameDescription = C.DESCRIPTION
    info.openTypeOS2VendorID = C.VENDOR_ID
    info.openTypeOS2TypoAscender = C.METRICS["typoAscender"]; info.openTypeOS2TypoDescender = C.METRICS["typoDescender"]
    info.openTypeOS2TypoLineGap = 0
    info.openTypeOS2WinAscent = C.METRICS["winAscent"]; info.openTypeOS2WinDescent = C.METRICS["winDescent"]
    info.openTypeHheaAscender = C.METRICS["hheaAscent"]; info.openTypeHheaDescender = C.METRICS["hheaDescent"]; info.openTypeHheaLineGap = 0
    info.openTypeVheaVertTypoAscender = 500; info.openTypeVheaVertTypoDescender = -500; info.openTypeVheaVertTypoLineGap = 0
    info.postscriptFontName = C.PS_NAME
    info.postscriptUnderlinePosition = C.METRICS["underlinePosition"]; info.postscriptUnderlineThickness = C.METRICS["underlineThickness"]
    info.note = ("Lovely Serif master. Generated by lovelyserif/build.py from Nanum Myeongjo (Latin) and "
                 "Noto Serif JP (Japanese); outlines reshaped by lovelyserif/filters.py and lovelyserif/edits.py. "
                 "OpenType layout (vert, palt, …) is transplanted from Noto Serif JP at build time.")
    for name in m.order:
        g = m.glyphs[name]
        ug = ufo.newGlyph(name)
        ug.width = g.width
        ug.unicodes = list(g.unicodes)
        adv, origin = m.vmetrics[name]
        ug.height = adv
        ug.verticalOrigin = origin
        pen = ug.getPen()
        g.draw(pen)
        if g.notes:
            ug.lib["public.markColor"] = "0.95,0.6,0.7,1" if "hand_edit" in g.notes else "0.6,0.8,1,1"
            ug.note = "; ".join(g.notes) + f" | source: {g.source}"
    ufo.lib["public.glyphOrder"] = list(m.order)
    for (a, b), v in m.kerning.items():
        ufo.kerning[(a, b)] = v
    ufo.features.text = ("# OpenType layout for Lovely Serif is transplanted from Noto Serif JP's binary GSUB/GPOS\n"
                         "# at build time (see lovelyserif/build.py: _layout_xml). Kerning pairs are in kerning.plist.\n")
    ufo.save(path, overwrite=True)


# ---------------------------------------------------------------------------
# 8. driver
# ---------------------------------------------------------------------------

def build(upstream: str, out_dir: str, ufo_path: Optional[str] = None, report_dir: Optional[str] = None,
          make_otf: bool = True, make_ttf: bool = True, make_woff2: bool = True) -> Master:
    os.makedirs(out_dir, exist_ok=True)
    tmpdir = os.path.join(out_dir, ".build"); os.makedirs(tmpdir, exist_ok=True)
    target = COV.target_set()
    log(f"target code points: {len(target)}")
    noto = subset_noto(os.path.join(upstream, "NotoSerifJP-Regular.otf"), target)
    log(f"Noto Serif JP subset: {len(noto.getGlyphOrder())} glyphs")
    nanum = TTFont(os.path.join(upstream, "NanumMyeongjo-Regular.ttf"))
    nanum_cps = {cp for cp in COV.latin_set() if cp not in C.EXCLUDE_CODEPOINTS}
    nanum_glyphs = extract_nanum(nanum, nanum_cps)
    log(f"Nanum Myeongjo Latin glyphs extracted: {len(nanum_glyphs)}")
    m = assemble(noto, nanum, nanum_glyphs)
    status = design_pass(m)
    nmod = sum(1 for s in status.values() if s["modified"])
    log(f"design pass: {nmod}/{len(status)} glyphs modified, {len(EDITS)} hand-edited glyph names registered")
    if make_otf:
        otf = compile_otf(m, tmpdir)
        p = os.path.join(out_dir, f"{C.PS_NAME}.otf"); otf.save(p); log(f"wrote {p} ({os.path.getsize(p)//1024} KB)")
    if make_ttf:
        ttf = compile_ttf(m, tmpdir)
        p = os.path.join(out_dir, f"{C.PS_NAME}.ttf"); ttf.save(p); log(f"wrote {p} ({os.path.getsize(p)//1024} KB)")
        if make_woff2:
            w = TTFont(p); w.flavor = "woff2"
            pw = os.path.join(out_dir, f"{C.PS_NAME}.woff2"); w.save(pw); log(f"wrote {pw} ({os.path.getsize(pw)//1024} KB)")
    if ufo_path:
        export_ufo(m, ufo_path); log(f"wrote UFO {ufo_path}")
    if report_dir:
        from .report import write_reports
        write_reports(m, status, report_dir)
    return m

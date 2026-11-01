"""Build reports: glyph status list, coverage check, before/after comparisons."""
from __future__ import annotations

import csv
import json
import os
from collections import Counter
from typing import Dict

from . import coverage as COV
from .render import compare_svg

FEATURED = ["uni6C38", "uni7F8E", "uni6587", "uni5B57", "uni611B", "uni56FD",
            "uni3042", "uni306E", "uni308A", "uni306F", "uni304B", "uni3059",
            "uni30A2", "uni30CE", "uni30EA",
            "m", "n", "a", "e", "g", "B", "R", "k", "y", "ampersand", "two"]


def write_reports(m, status: Dict[str, dict], report_dir: str) -> None:
    os.makedirs(report_dir, exist_ok=True)
    cmp_dir = os.path.join(report_dir, "compare"); os.makedirs(cmp_dir, exist_ok=True)
    # --- glyph status table -------------------------------------------------
    rows = []
    for name in m.order:
        s = status.get(name, {})
        g = m.glyphs[name]
        rows.append(dict(
            glyph=name, unicodes=" ".join(f"U+{c:04X}" for c in g.unicodes), chars="".join(chr(c) for c in g.unicodes if c >= 0x20),
            category=s.get("category", m.category.get(name, "")), source=g.source,
            modified="yes" if s.get("modified") else "no", hand_edit="yes" if s.get("hand_edit") else "no",
            filters="; ".join(s.get("notes", [])), nodes_before=s.get("nodes_before", ""), nodes_after=s.get("nodes_after", "")))
    with open(os.path.join(report_dir, "glyph_status.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    by_cat = Counter(r["category"] for r in rows)
    mod_cat = Counter(r["category"] for r in rows if r["modified"] == "yes")
    hand = [r for r in rows if r["hand_edit"] == "yes"]
    unmod = [r for r in rows if r["modified"] == "no"]
    # --- coverage -------------------------------------------------------------
    cmap = m.cmap
    jis208 = COV.jis_x0208_kanji(); jis213 = COV.jis_kanji()
    kana = [cp for cp in range(0x3041, 0x30FF) if cp in COV.jis_nonkanji() or cp in COV.symbol_set()]
    cov_lines = [
        "# Coverage", "",
        f"| set | present | total |", "|---|---|---|",
        f"| ASCII (U+0020–007E) | {sum(1 for c in range(0x20,0x7F) if c in cmap)} | 95 |",
        f"| Latin-1 Supplement | {sum(1 for c in range(0xA0,0x100) if c in cmap)} | 96 |",
        f"| Hiragana (U+3041–3096, 3099–309F) | {sum(1 for c in list(range(0x3041,0x3097))+list(range(0x3099,0x30A0)) if c in cmap)} | 93 |",
        f"| Katakana (U+30A0–30FF) | {sum(1 for c in range(0x30A0,0x3100) if c in cmap)} | 96 |",
        f"| JIS X 0208 kanji (levels 1+2) | {sum(1 for c in jis208 if c in cmap)} | {len(jis208)} |",
        f"| JIS X 0213 plane-1 kanji (incl. all Jōyō + Jinmeiyō) | {sum(1 for c in jis213 if c in cmap)} | {len(jis213)} |",
        f"| Fullwidth forms (U+FF01–FF5E) | {sum(1 for c in range(0xFF01,0xFF5F) if c in cmap)} | 94 |",
        f"| Halfwidth katakana (U+FF61–FF9F) | {sum(1 for c in range(0xFF61,0xFFA0) if c in cmap)} | 63 |",
        f"| CJK symbols & punctuation (U+3000–303F) | {sum(1 for c in range(0x3000,0x3040) if c in cmap)} | 64 |",
        "", f"Total glyphs: {len(m.order)} · code points mapped: {len(cmap)} · variation sequences: {sum(len(v) for v in m.uvs.values())}",
    ]
    joyo_path = os.path.join(os.path.dirname(report_dir), "data", "joyo.txt")
    if os.path.exists(joyo_path):
        joyo = [ch for ch in open(joyo_path, encoding="utf-8").read() if ord(ch) > 0x2E80]
        missing = [ch for ch in joyo if ord(ch) not in cmap]
        cov_lines.append(f"\nJōyō kanji list ({len(joyo)}): {len(joyo)-len(missing)} present, missing: {''.join(missing) or 'none'}")
    open(os.path.join(report_dir, "coverage.md"), "w", encoding="utf-8").write("\n".join(cov_lines) + "\n")
    # --- summary ---------------------------------------------------------------
    lines = ["# Glyph status summary", "",
             f"Total glyphs: {len(rows)}", "",
             "| category | glyphs | outline-modified | unmodified |", "|---|---|---|---|"]
    for cat, n in sorted(by_cat.items()):
        lines.append(f"| {cat} | {n} | {mod_cat.get(cat,0)} | {n-mod_cat.get(cat,0)} |")
    lines += ["", f"Hand-edited glyphs ({len(hand)}): " + ", ".join(f"{r['glyph']}({r['chars']})" for r in hand), "",
              f"Unmodified glyphs ({len(unmod)}): kept exactly as in the upstream font (empty glyphs, box drawing, geometric symbols, "
              "arrows, math, enclosed symbols, etc.). Full list in glyph_status.csv (column `modified`).", "",
              "Filters legend: soften_corners(n) = n corners filleted · smooth_joins(n) = n tangent breaks smoothed · "
              "remove_overlaps = contours unioned (Nanum TrueType sources) · hand_edit = per-glyph edit from lovelyserif/edits.py"]
    open(os.path.join(report_dir, "glyph_status.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"by_category": by_cat, "modified_by_category": mod_cat, "hand_edited": [r["glyph"] for r in hand],
               "total": len(rows)}, open(os.path.join(report_dir, "summary.json"), "w"), ensure_ascii=False, indent=1)
    # --- before/after SVGs --------------------------------------------------------
    index = ["<!doctype html><meta charset='utf-8'><title>Lovely Serif — before / after</title>",
             "<style>body{font-family:sans-serif;background:#fafafa;margin:24px}figure{margin:0 0 28px}figcaption{color:#555;font-size:13px}</style>",
             "<h1>Lovely Serif — outline comparisons (before = upstream, after = Lovely Serif)</h1>"]
    for name in FEATURED:
        if name not in m.glyphs or name not in m.originals:
            continue
        b = m.originals[name]; a = m.glyphs[name]
        svg = compare_svg(b, a, size=300, title=f"{name} {''.join(chr(c) for c in a.unicodes)} · {' '.join(a.notes)}")
        open(os.path.join(cmp_dir, f"{name}.svg"), "w", encoding="utf-8").write(svg)
        index.append(f"<figure><img src='compare/{name}.svg'><figcaption>{name} {''.join(chr(c) for c in a.unicodes)} — {' · '.join(a.notes)}</figcaption></figure>")
    open(os.path.join(report_dir, "compare.html"), "w", encoding="utf-8").write("\n".join(index))

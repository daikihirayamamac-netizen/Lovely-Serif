#!/usr/bin/env python3
"""Outline QA over the whole font → reports/qa.md (+ reports/qa/*.svg for flagged glyphs).

    python scripts/qa.py            # full font (~2 min)
    python scripts/qa.py --text 永あm   # only these characters
"""
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from fontTools.ttLib import TTFont
from lovelyserif import build as B, coverage as COV
from lovelyserif.qa import analyze
from lovelyserif.render import compare_svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=None)
    ap.add_argument("--upstream", default=os.path.join(ROOT, "sources", "upstream"))
    ap.add_argument("--out", default=os.path.join(ROOT, "reports"))
    ap.add_argument("--max-svg", type=int, default=60)
    a = ap.parse_args()
    cps = {ord(c) for c in a.text} | set(range(0x20, 0x7F)) if a.text else COV.target_set()
    noto = B.subset_noto(os.path.join(a.upstream, "NotoSerifJP-Regular.otf"), cps)
    nanum = TTFont(os.path.join(a.upstream, "NanumMyeongjo-Regular.ttf"))
    ng = B.extract_nanum(nanum, COV.latin_set())
    m = B.assemble(noto, nanum, ng)
    status = B.design_pass(m)
    flagged = {}
    for name in m.order:
        before = m.originals.get(name); after = m.glyphs[name]
        if before is None:
            continue
        iss = analyze(name, before, after, bool(status.get(name, {}).get("hand_edit")))
        if iss:
            flagged[name] = iss
    kinds = {}
    for n, iss in flagged.items():
        for k in iss:
            kinds.setdefault(k, []).append(n)
    qa_dir = os.path.join(a.out, "qa"); os.makedirs(qa_dir, exist_ok=True)
    for f in os.listdir(qa_dir):
        os.remove(os.path.join(qa_dir, f))
    lines = ["# Outline QA", "", f"Glyphs checked: {len(m.order)} · flagged: {len(flagged)}", "",
             "| check | glyphs |", "|---|---|"]
    for k in ["pathops_fail", "emptied", "self_intersect", "direction", "degenerate", "xor", "area", "bbox"]:
        lines.append(f"| {k} | {len(kinds.get(k, []))} |")
    lines.append("")
    structural = ("pathops_fail", "emptied", "self_intersect", "direction", "degenerate")
    order = sorted(flagged, key=lambda n: (not any(k in flagged[n] for k in structural), -float(flagged[n].get("xor", 0))))
    json.dump(flagged, open(os.path.join(a.out, "qa.json"), "w"), ensure_ascii=False, indent=0)
    for i, n in enumerate(order[:400]):
        g = m.glyphs[n]
        lines.append(f"- `{n}` {''.join(chr(c) for c in g.unicodes)} — {json.dumps(flagged[n], ensure_ascii=False)}")
        if i < a.max_svg:
            open(os.path.join(qa_dir, f"{n}.svg"), "w").write(compare_svg(m.originals[n], g, size=220, title=f"{n} {json.dumps(flagged[n])}"))
    open(os.path.join(a.out, "qa.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))
    print(f"top: {order[:30]}")


if __name__ == "__main__":
    main()

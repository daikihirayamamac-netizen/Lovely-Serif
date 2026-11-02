#!/usr/bin/env python3
"""Design lab: build a small test font quickly with parameter overrides.

    python scripts/lab.py --text "文字から美しさを永あのりはmnag" --set KANJI_PARAMS.r_convex=24 --out /tmp/lab.ttf
"""
import argparse, os, sys, dataclasses
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from fontTools.ttLib import TTFont
from lovelyserif import config as C, coverage as COV
from lovelyserif import build as B

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="文字から、美しさを。永あのりはかすABCRmnaegky0123 Beauty in every letter.")
    ap.add_argument("--set", action="append", default=[], help="PARAMS.field=value")
    ap.add_argument("--out", default="/tmp/lab/LovelySerif-Lab.ttf")
    ap.add_argument("--otf", action="store_true")
    ap.add_argument("--upstream", default=os.path.join(ROOT, "sources", "upstream"))
    a = ap.parse_args()
    for s in a.set:
        key, val = s.split("=", 1)
        obj, fld = key.split(".")
        params = getattr(C, obj)
        setattr(C, obj, dataclasses.replace(params, **{fld: type(getattr(params, fld))(val)}))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    cps = {ord(ch) for ch in a.text} | set(range(0x20, 0x7F)) | {0x3001, 0x3002, 0x300C, 0x300D, 0x30FC}
    noto = B.subset_noto(os.path.join(a.upstream, "NotoSerifJP-Regular.otf"), cps)
    nanum = TTFont(os.path.join(a.upstream, "NanumMyeongjo-Regular.ttf"))
    ng = B.extract_nanum(nanum, COV.latin_set())
    m = B.assemble(noto, nanum, ng)
    B.design_pass(m)
    tmp = os.path.join(os.path.dirname(a.out), ".build"); os.makedirs(tmp, exist_ok=True)
    f = B.compile_otf(m, tmp) if a.otf else B.compile_ttf(m, tmp)
    f.save(a.out); print("wrote", a.out)
    return m

if __name__ == "__main__":
    main()

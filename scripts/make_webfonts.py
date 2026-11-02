#!/usr/bin/env python3
"""Create web deliverables from the built TTF.

  fonts/LovelySerif-Regular.woff2        full font (JIS X 0213 plane 1 + symbols)   ~2.1 MB
  fonts/LovelySerif-Regular-std.woff2    web subset: Latin, kana, punctuation, JIS level-1 kanji + all 2,136 Jōyō  ~0.8 MB
  fonts/lovely-serif.css                 ready-to-use @font-face rules (std first, full as fallback via unicode-range)
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from fontTools import subset
from fontTools.ttLib import TTFont
from lovelyserif import coverage as COV

FONTS = os.path.join(ROOT, "fonts")


def level1_kanji():
    out = set()
    for cp in COV.jis_x0208_kanji():
        b = chr(cp).encode("shift_jis")
        if b[0] < 0x98 or (b[0] == 0x98 and b[1] <= 0x72):
            out.add(cp)
    return out


def main():
    src = os.path.join(FONTS, "LovelySerif-Regular.ttf")
    font = TTFont(src)
    cmap = font.getBestCmap()
    std = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | set(range(0x2010, 0x2027)) | set(range(0x2030, 0x2040))
    std |= set(range(0x3000, 0x3040)) | set(range(0x3041, 0x3100)) | set(range(0x31F0, 0x3200))
    std |= set(range(0xFF01, 0xFF66)) | set(range(0xFF66, 0xFFA0)) | set(range(0xFFE0, 0xFFE7))
    std |= {0x2015, 0x2016, 0x2018, 0x2019, 0x201C, 0x201D, 0x2025, 0x2026, 0x2030, 0x2032, 0x2033, 0x203B, 0x2103, 0x2116, 0x2121, 0x2122}
    std |= set(range(0x2190, 0x2194)) | set(range(0x2460, 0x2474)) | {0x25A0, 0x25A1, 0x25B2, 0x25B3, 0x25BC, 0x25BD, 0x25C6, 0x25C7, 0x25CB, 0x25CE, 0x25CF, 0x2605, 0x2606, 0x266A, 0x266D, 0x266F}
    std |= level1_kanji()
    # every Jōyō kanji (34 of them are outside JIS level 1, e.g. 鬱 丼 嘲 曖 𠮟 剝 頰 塡) plus the
    # widely typed JIS forms of the four 2010 variants
    joyo = [ord(c) for c in open(os.path.join(ROOT, "data", "joyo.txt"), encoding="utf-8").read().strip()]
    std |= set(joyo) | {ord(c) for c in "叱剥頬填"}
    std = {cp for cp in std if cp in cmap}
    missing = [chr(cp) for cp in joyo if cp not in std]
    if missing:
        raise SystemExit(f"std subset is missing Jōyō kanji: {''.join(missing)}")
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]; opts.name_languages = ["*"]
    opts.notdef_outline = True; opts.glyph_names = False
    opts.hinting = False
    opts.desubroutinize = True
    s = subset.Subsetter(opts); s.populate(unicodes=sorted(std)); s.subset(font)
    out = os.path.join(FONTS, "LovelySerif-Regular-std.woff2")
    font.flavor = "woff2"; font.save(out)
    print("wrote", out, os.path.getsize(out) // 1024, "KB", len(font.getGlyphOrder()), "glyphs")
    css = """/* Lovely Serif — web font rules. Put the woff2 files next to this CSS (or adjust the paths). */
@font-face {
  font-family: "Lovely Serif";
  src: url("LovelySerif-Regular.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
/* Lighter option: load only the standard subset (Latin, kana, punctuation, JIS level-1 kanji) */
@font-face {
  font-family: "Lovely Serif Std";
  src: url("LovelySerif-Regular-std.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
html { font-family: "Lovely Serif", "Noto Serif JP", "Hiragino Mincho ProN", "Yu Mincho", serif; }
"""
    open(os.path.join(FONTS, "lovely-serif.css"), "w", encoding="utf-8").write(css)
    print("wrote", os.path.join(FONTS, "lovely-serif.css"))


if __name__ == "__main__":
    main()

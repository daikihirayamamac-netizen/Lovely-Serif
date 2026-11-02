#!/usr/bin/env python3
"""Verify the built fonts and write reports/verification.md.

Checks: fontTools structural load + table round-trip, OpenType Sanitizer (ots),
HarfBuzz shaping (vert/vrt2/palt/kern/fwid), FreeType rendering of mixed text
(PIL), name/metadata expectations for macOS Font Book, FontBakery summary.
"""
import io, os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from fontTools.ttLib import TTFont
from lovelyserif import config as C

FONTS = os.path.join(ROOT, "fonts"); REPORTS = os.path.join(ROOT, "reports")
FILES = ["LovelySerif-Regular.otf", "LovelySerif-Regular.ttf", "LovelySerif-Regular.woff2"]
lines = ["# Verification report", "", f"Generated {time.strftime('%Y-%m-%d %H:%M')} by scripts/verify.py", ""]
ok_all = True


def section(t):
    lines.append(""); lines.append(f"## {t}"); lines.append("")


def result(name, ok, detail=""):
    global ok_all
    ok_all = ok_all and ok
    lines.append(f"- {'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""))


section("fontTools: structure")
for fn in FILES:
    p = os.path.join(FONTS, fn)
    try:
        f = TTFont(p)
        tables = sorted(t for t in f.keys() if t != "GlyphOrder")
        n = len(f.getGlyphOrder())
        # force-decompile every table
        for t in tables:
            _ = f[t]
        buf = io.BytesIO(); f.save(buf)
        result(f"{fn} loads, all tables decompile and recompile", True, f"{n} glyphs, {os.path.getsize(p)//1024} KB, tables: {' '.join(tables)}")
    except Exception as e:
        result(f"{fn} loads", False, repr(e))

section("Names / metadata (macOS Font Book)")
f = TTFont(os.path.join(FONTS, "LovelySerif-Regular.otf"))
name = f["name"]
expect = {1: C.FAMILY, 2: C.STYLE, 4: f"{C.FAMILY} {C.STYLE}", 6: C.PS_NAME}
for nid, exp in expect.items():
    got = name.getDebugName(nid)
    result(f"name ID {nid} = {got!r}", got == exp)
ja = {r.nameID: r.toUnicode() for r in name.names if r.platformID == 3 and r.langID == 0x411}
result("Japanese localized family name", ja.get(1) == C.FAMILY_JA, ja.get(1, ""))
os2 = f["OS/2"]
result("OS/2 fsType = 0 (installable, embeddable)", os2.fsType == 0)
result("OS/2 usWeightClass = 400", os2.usWeightClass == 400)
result("OS/2 vendor ID", os2.achVendID == C.VENDOR_ID, os2.achVendID)
result("head.fontRevision", abs(f["head"].fontRevision - C.VERSION_FIXED) < 1e-3, str(f["head"].fontRevision))
result("Vertical metrics follow Noto Serif JP (typo 880/-120, hhea 1151/-286, win 1151/286)",
       (os2.sTypoAscender, os2.sTypoDescender, f["hhea"].ascent, f["hhea"].descent, os2.usWinAscent, os2.usWinDescent) == (880, -120, 1151, -286, 1151, 286))
result("vhea/vmtx present (vertical writing)", "vhea" in f and "vmtx" in f)
lic = name.getDebugName(13) or ""
result("License name record mentions OFL 1.1", "SIL Open Font License, Version 1.1" in lic)
result("No reserved font names used (Nanum / Noto / Source) in family name", not any(x in (name.getDebugName(1) or "") for x in ("Nanum", "Noto", "Source")))

section("OpenType Sanitizer (ots)")
try:
    import ots
    for fn in FILES:
        r = ots.sanitize(os.path.join(FONTS, fn), capture_output=True)
        result(f"ots-sanitize {fn}", r.returncode == 0, (r.stderr or b"").decode().strip()[:200] or "clean")
except Exception as e:
    result("ots available", False, repr(e))

section("HarfBuzz shaping (uharfbuzz)")
try:
    import uharfbuzz as hb
    p = os.path.join(FONTS, "LovelySerif-Regular.otf")
    tt = TTFont(p); go = tt.getGlyphOrder(); cmap = tt.getBestCmap()
    face = hb.Face(hb.Blob.from_file_path(p)); font = hb.Font(face)
    def shape(text, features=None, vertical=False):
        buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
        if vertical:
            buf.direction = "ttb"
        hb.shape(font, buf, features or {})
        return [(go[i.codepoint], (pz.x_advance, pz.y_advance, pz.x_offset, pz.y_offset)) for i, pz in zip(buf.glyph_infos, buf.glyph_positions)]
    h = shape("「永」ー、。"); v = shape("「永」ー、。", vertical=True)
    result("vert: 「」ー、。 use vertical forms in ttb", all(a[0] != b[0] for a, b in zip(h, v) if a[0] != "uni6C38"),
           " ".join(g for g, _ in v))
    result("vertical advance = 1000 (vmtx)", all(adv[1] == -1000 for _, adv in v))
    pa = shape("「永」、", {"palt": True})
    result("palt: proportional punctuation narrows advances", pa[0][1][0] < 1000 and pa[-1][1][0] < 1000, str([g[1][0] for g in pa]))
    k1 = shape("AV To"); k0 = shape("AV To", {"kern": False})
    result("kern: Latin pairs from Nanum Myeongjo applied", k1[0][1][0] < k0[0][1][0], f"A→V {k0[0][1][0]} → {k1[0][1][0]}")
    fw = shape("abc", {"fwid": True})
    result("fwid: ASCII → fullwidth forms", all(g.startswith("uniFF") for g, _ in fw), " ".join(g for g, _ in fw))
    notdef = shape("ก")  # Thai: not covered → .notdef
    result(".notdef for uncovered characters", notdef[0][0] == ".notdef")
    from lovelyserif.config import EXCLUDE_CODEPOINTS
    present_ex = [chr(c) for c in EXCLUDE_CODEPOINTS if c in cmap]
    result("excluded kana (ゑ ヱ ヹ ㋽) are absent from cmap", not present_ex, "".join(present_ex) or "absent")
    joyo = open(os.path.join(ROOT, "data", "joyo.txt"), encoding="utf-8").read().strip()
    result("all 2,136 Jōyō kanji present (full font)", len(joyo) == 2136 and all(ord(c) in cmap for c in joyo),
           "".join(c for c in joyo if ord(c) not in cmap) or "2136/2136")
    stdp = os.path.join(FONTS, "LovelySerif-Regular-std.woff2")
    if os.path.exists(stdp):
        scm = TTFont(stdp).getBestCmap()
        result("all 2,136 Jōyō kanji present (std web subset)", all(ord(c) in scm for c in joyo),
               "".join(c for c in joyo if ord(c) not in scm) or "2136/2136")
    missing = [ch for ch in "文字から美しさを永あのりは𠮟剝頰塡ABCabc012！？、。「」éçüñŒœŁł" if ord(ch) not in cmap]
    result("key characters present in cmap", not missing, "".join(missing) or "all present")
except Exception as e:
    result("HarfBuzz tests", False, repr(e))

section("FreeType rendering (PIL)")
try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    os.makedirs(os.path.join(ROOT, "docs", "screenshots"), exist_ok=True)
    for fn in ["LovelySerif-Regular.ttf", "LovelySerif-Regular.otf"]:
        fnt = ImageFont.truetype(os.path.join(FONTS, fn), 48)
        im = Image.new("L", (1500, 260), 255); d = ImageDraw.Draw(im)
        d.text((20, 40), "文字から、美しさを。Beauty in every letter.", font=fnt, fill=0)
        d.text((20, 120), "やさしく、上品に、美しく。𠮟る・剝がす・頰・塡める ①②③ ｱｲｳ", font=fnt, fill=0)
        a = np.array(im) < 128
        cols = a.any(axis=0).sum()
        result(f"{fn}: FreeType renders mixed text (ink columns {cols})", cols > 800)
        im.save(os.path.join(ROOT, "docs", "screenshots", f"freetype_{fn.split('.')[-1]}.png"))
except Exception as e:
    result("FreeType rendering", False, repr(e))

section("Outline fidelity and spacing")
try:
    import numpy as np
    from lovelyserif.outline import Glyph
    from lovelyserif.qa import raster
    fo = TTFont(os.path.join(FONTS, "LovelySerif-Regular.otf")); ft = TTFont(os.path.join(FONTS, "LovelySerif-Regular.ttf"))
    go, gt = fo.getGlyphSet(), ft.getGlyphSet()
    names = fo.getGlyphOrder(); tnames = ft.getGlyphOrder()   # same order; the TTF has no glyph names (post 3)
    to_t = dict(zip(names, tnames))
    sample = [n for i, n in enumerate(names) if i % 7 == 0] + [n for n in names if fo["hmtx"][n][0] != 1000][:400]
    worst = (0.0, "")
    for n in sample:
        a = raster(Glyph.from_font_glyph(go, n), 96); b = raster(Glyph.from_font_glyph(gt, to_t[n]), 96)
        tot = max(int(a.sum()), 1)
        d = float((a ^ b).sum()) / tot if tot > 20 else 0.0
        if d > worst[0]:
            worst = (d, n)
    result(f"TTF (quadratic) matches OTF (cubic) outlines on {len(sample)} sampled glyphs (cu2qu tolerance 1 unit)", worst[0] < 0.06,
           f"worst pixel difference {worst[0]:.1%} ({worst[1]})")

    # Latin spacing: pairs whose ink touches in Lovely Serif but not in Nanum Myeongjo
    import uharfbuzz as hb
    nanum = TTFont(os.path.join(ROOT, "sources", "upstream", "NanumMyeongjo-Regular.ttf"))
    def profile(font, ch):
        """Per-row (≈2 units) left/right ink extent from a non-zero raster of the glyph."""
        gs = font.getGlyphSet(); gn = font.getBestCmap().get(ord(ch))
        g = Glyph.from_font_glyph(gs, gn, font["hmtx"][gn][0])
        g.transform(1000 / font["head"].unitsPerEm)
        size = 560
        img = raster(g, size)
        scale = size / 1100
        rows = {}
        for r in range(size):
            cols = np.nonzero(img[r])[0]
            if len(cols):
                rows[r] = ((cols[0]) / scale - 50, (cols[-1] + 1) / scale - 50)
        return g.width, rows
    def gaps(font, path, chars):
        face = hb.Face(hb.Blob.from_file_path(path)); hf = hb.Font(face)
        prof = {c: profile(font, c) for c in chars}
        out = {}
        for a in chars:
            for b in chars:
                buf = hb.Buffer(); buf.add_str(a + b); buf.guess_segment_properties(); hb.shape(hf, buf, {})
                adv = buf.glyph_positions[0].x_advance * 1000 / font["head"].unitsPerEm
                wa, ra = prof[a]; wb, rb = prof[b]
                g = min((adv + rb[k][0]) - ra[k][1] for k in ra if k in rb) if any(k in rb for k in ra) else 999
                out[a + b] = g
        return out
    chars = "abcdeghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPRSTUVWXYZ"
    new = gaps(TTFont(os.path.join(FONTS, "LovelySerif-Regular.ttf")), os.path.join(FONTS, "LovelySerif-Regular.ttf"), chars)
    old = gaps(nanum, os.path.join(ROOT, "sources", "upstream", "NanumMyeongjo-Regular.ttf"), chars)
    collide = sorted(p for p in new if new[p] < 0 and old[p] >= 0)
    tighter = sorted(((new[p] - old[p]), p) for p in new)[:5]
    result(f"no new Latin collisions vs Nanum Myeongjo ({len(new)} pairs)", not collide,
           ("new collisions: " + " ".join(collide)) if collide else f"tightest change {tighter[0][0]:+.0f} units ({tighter[0][1]})")
except Exception as e:
    import traceback; traceback.print_exc()
    result("fidelity / spacing checks", False, repr(e))

section("FontBakery (universal profile)")
try:
    r = subprocess.run(["fontbakery", "check-universal", "--no-progress", "--loglevel", "WARN", "-x", "fontdata_namecheck", "-F", os.path.join(FONTS, "LovelySerif-Regular.ttf")],
                       capture_output=True, text=True, timeout=1800)
    out = r.stdout
    open(os.path.join(REPORTS, "fontbakery-universal.txt"), "w", encoding="utf-8").write(out)
    summary = [l.strip() for l in out.splitlines() if l.strip().startswith(("FAIL:", "WARN:", "PASS:", "INFO:", "SKIP:", "ERROR:"))]
    nfail = next((int(s.split(":")[1]) for s in summary if s.startswith("FAIL:")), -1)
    result("fontbakery check-universal: 0 FAIL", nfail == 0, ", ".join(summary))
    lines.append("")
    lines.append("Full log: reports/fontbakery-universal.txt. Remaining WARNs: file size (CJK fonts are large), post table format 3 (no glyph names in the TTF), chws/vchw feature not present, ligature carets, soft hyphen present, typoAscender < Agrave height (identical to Noto Serif JP), combining kana marks not in GDEF mark class.")
except Exception as e:
    result("fontbakery", False, repr(e))

lines.insert(3, f"**Overall: {'all checks passed' if ok_all else 'some checks failed'}**")
open(os.path.join(REPORTS, "verification.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0 if ok_all else 1)

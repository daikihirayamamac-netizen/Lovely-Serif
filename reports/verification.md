# Verification report

Generated 2026-11-02 12:45 by scripts/verify.py
**Overall: all checks passed**


## fontTools: structure

- ✅ LovelySerif-Regular.otf loads, all tables decompile and recompile — 10374 glyphs, 6336 KB, tables: BASE CFF  GDEF GPOS GSUB OS/2 VORG cmap head hhea hmtx maxp name post vhea vmtx
- ✅ LovelySerif-Regular.ttf loads, all tables decompile and recompile — 10374 glyphs, 6966 KB, tables: BASE GDEF GPOS GSUB OS/2 cmap gasp glyf head hhea hmtx loca maxp name post prep vhea vmtx
- ✅ LovelySerif-Regular.woff2 loads, all tables decompile and recompile — 10374 glyphs, 2126 KB, tables: BASE GDEF GPOS GSUB OS/2 cmap gasp glyf head hhea hmtx loca maxp name post prep vhea vmtx

## Names / metadata (macOS Font Book)

- ✅ name ID 1 = 'Lovely Serif'
- ✅ name ID 2 = 'Regular'
- ✅ name ID 4 = 'Lovely Serif Regular'
- ✅ name ID 6 = 'LovelySerif-Regular'
- ✅ Japanese localized family name — ラブリーセリフ
- ✅ OS/2 fsType = 0 (installable, embeddable)
- ✅ OS/2 usWeightClass = 400
- ✅ OS/2 vendor ID — LVLY
- ✅ head.fontRevision — 0.1009979248046875
- ✅ Vertical metrics follow Noto Serif JP (typo 880/-120, hhea 1151/-286, win 1151/286)
- ✅ vhea/vmtx present (vertical writing)
- ✅ License name record mentions OFL 1.1
- ✅ No reserved font names used (Nanum / Noto / Source) in family name

## OpenType Sanitizer (ots)

- ✅ ots-sanitize LovelySerif-Regular.otf — clean
- ✅ ots-sanitize LovelySerif-Regular.ttf — clean
- ✅ ots-sanitize LovelySerif-Regular.woff2 — clean

## HarfBuzz shaping (uharfbuzz)

- ✅ vert: 「」ー、。 use vertical forms in ttb — uniFE41 uni6C38 uniFE42 uni30FC.vert uniFE11 uniFE12
- ✅ vertical advance = 1000 (vmtx)
- ✅ palt: proportional punctuation narrows advances — [500, 1000, 500, 500]
- ✅ kern: Latin pairs from Nanum Myeongjo applied — A→V 733 → 610
- ✅ fwid: ASCII → fullwidth forms — uniFF41 uniFF42 uniFF43
- ✅ .notdef for uncovered characters
- ✅ excluded kana (ゑ ヱ ヹ ㋽) are absent from cmap — absent
- ✅ all 2,136 Jōyō kanji present (full font) — 2136/2136
- ✅ all 2,136 Jōyō kanji present (std web subset) — 2136/2136
- ✅ key characters present in cmap — all present

## FreeType rendering (PIL)

- ✅ LovelySerif-Regular.ttf: FreeType renders mixed text (ink columns 1162)
- ✅ LovelySerif-Regular.otf: FreeType renders mixed text (ink columns 1159)

## Outline fidelity and spacing

- ✅ TTF (quadratic) matches OTF (cubic) outlines on 1882 sampled glyphs (cu2qu tolerance 1 unit) — worst pixel difference 4.4% (uni32E3)
- ✅ no new Latin collisions vs Nanum Myeongjo (2500 pairs) — tightest change -18 units (ym)

## FontBakery (universal profile)

- ✅ fontbakery check-universal: 0 FAIL — ERROR: 0, FAIL: 0, WARN: 10, INFO: 3, SKIP: 39, PASS: 74

Full log: reports/fontbakery-universal.txt. Remaining WARNs: file size (CJK fonts are large), post table format 3 (no glyph names in the TTF), chws/vchw feature not present, ligature carets, soft hyphen present, typoAscender < Agrave height (identical to Noto Serif JP), combining kana marks not in GDEF mark class.

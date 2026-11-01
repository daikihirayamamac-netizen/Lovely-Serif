# Verification report

Generated 2026-11-01 12:00 by scripts/verify.py
**Overall: all checks passed**


## fontTools: structure

- ✅ LovelySerif-Regular.otf loads, all tables decompile and recompile — 10364 glyphs, 6325 KB, tables: BASE CFF  GDEF GPOS GSUB OS/2 VORG cmap head hhea hmtx maxp name post vhea vmtx
- ✅ LovelySerif-Regular.ttf loads, all tables decompile and recompile — 10364 glyphs, 6956 KB, tables: BASE GDEF GPOS GSUB OS/2 cmap gasp glyf head hhea hmtx loca maxp name post prep vhea vmtx
- ✅ LovelySerif-Regular.woff2 loads, all tables decompile and recompile — 10364 glyphs, 2125 KB, tables: BASE GDEF GPOS GSUB OS/2 cmap gasp glyf head hhea hmtx loca maxp name post prep vhea vmtx

## Names / metadata (macOS Font Book)

- ✅ name ID 1 = 'Lovely Serif'
- ✅ name ID 2 = 'Regular'
- ✅ name ID 4 = 'Lovely Serif Regular'
- ✅ name ID 6 = 'LovelySerif-Regular'
- ✅ Japanese localized family name — ラブリーセリフ
- ✅ OS/2 fsType = 0 (installable, embeddable)
- ✅ OS/2 usWeightClass = 400
- ✅ OS/2 vendor ID — LVLY
- ✅ head.fontRevision — 0.100006103515625
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
- ✅ kern: Latin pairs from Nanum Myeongjo applied — A→V 727 → 604
- ✅ fwid: ASCII → fullwidth forms — uniFF41 uniFF42 uniFF43
- ✅ .notdef for uncovered characters
- ✅ key characters present in cmap — all present

## FreeType rendering (PIL)

- ✅ LovelySerif-Regular.ttf: FreeType renders mixed text (ink columns 1159)
- ✅ LovelySerif-Regular.otf: FreeType renders mixed text (ink columns 1155)

## FontBakery (universal profile)

- ✅ fontbakery check-universal: 0 FAIL — ERROR: 0, FAIL: 0, WARN: 10, INFO: 3, SKIP: 39, PASS: 74

Full log: reports/fontbakery-universal.txt. Remaining WARNs: file size (CJK fonts are large), post table format 3 (no glyph names in the TTF), chws/vchw feature not present, ligature carets, soft hyphen present, typoAscender < Agrave height (identical to Noto Serif JP), combining kana marks not in GDEF mark class.

"""Project-wide configuration: names, metrics and design parameters."""
from __future__ import annotations

from .filters import SoftenParams

VERSION = "0.1.1"
VERSION_FIXED = 0.101          # head.fontRevision / name ID 5
FAMILY = "Lovely Serif"
FAMILY_JA = "ラブリーセリフ"
STYLE = "Regular"
PS_NAME = "LovelySerif-Regular"
VENDOR_ID = "LVLY"
UPM = 1000

COPYRIGHT = (
    "Lovely Serif: Copyright 2026 The Lovely Serif Project Authors. "
    "Latin glyphs derived from Nanum Myeongjo, Copyright (c) 2010 NHN Corporation (http://www.nhncorp.com), "
    "font designed by FONTRIX. Japanese glyphs derived from Noto Serif JP (Noto Serif CJK / Source Han Serif), "
    "Copyright 2017-2024 Adobe (http://www.adobe.com/)."
)
LICENSE_TEXT = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "This license is available with a FAQ at: https://openfontlicense.org"
)
LICENSE_URL = "https://openfontlicense.org"
DESCRIPTION = (
    "Lovely Serif is a soft, refined Mincho-style serif for Japanese and English. "
    "Built from Nanum Myeongjo (Latin) and Noto Serif JP (Japanese) with reshaped outlines: "
    "softened corners, rounded stroke ends and brush-like terminals."
)

# Vertical metrics follow Noto Serif JP so the font can replace it 1:1 on a web page.
METRICS = dict(
    typoAscender=880, typoDescender=-120, typoLineGap=0,
    winAscent=1151, winDescent=286,
    hheaAscent=1151, hheaDescent=-286, hheaLineGap=0,
    vheaAscent=500, vheaDescent=-500, vheaLineGap=0,
    xHeight=470, capHeight=737,
    underlinePosition=-100, underlineThickness=50,
    defaultVertOrigin=880,
)

# Scale applied to Nanum Myeongjo outlines (1024 upm -> 1000 upm).
NANUM_SCALE = 1000.0 / 1024.0

# OpenType layout features kept from Noto Serif JP.
KEEP_FEATURES = ["ccmp", "liga", "locl", "vert", "vrt2", "fwid", "hwid", "pwid",
                 "palt", "vpal", "halt", "vhal", "vkrn"]

# --- design parameters -------------------------------------------------------
KANJI_PARAMS = SoftenParams(r_convex=30.0, r_concave=10.0, d_tip=18.0, tip_angle_deg=112.0,
                            handle_factor=1.0, max_frac=0.46)
KANA_PARAMS = SoftenParams(r_convex=28.0, r_concave=9.0, d_tip=18.0, tip_angle_deg=112.0,
                           handle_factor=1.0, max_frac=0.46)
LATIN_PARAMS = SoftenParams(r_convex=14.0, r_concave=7.0, d_tip=9.0, tip_angle_deg=112.0,
                            handle_factor=1.0, max_frac=0.30)  # 0.30 keeps a flat cut on thin ends (no rounded-gothic look)
LATIN_OFFSET = 3.0   # units added to each side of every Latin stroke (stem 60 → 66, hairline 27 → 33)
PUNCT_PARAMS = SoftenParams(r_convex=22.0, r_concave=8.0, d_tip=14.0)
KANA_SMOOTH_ANGLE = 22.0

# Characters deliberately left out of Lovely Serif (owner's decision, 2026-11-02):
# the "we" kana in every form. Text containing them falls back to the next font in the CSS stack.
EXCLUDE_CODEPOINTS = {
    0x3091,  # ゑ HIRAGANA LETTER WE
    0x30F1,  # ヱ KATAKANA LETTER WE
    0x30F9,  # ヹ KATAKANA LETTER VE
    0x32FD,  # ㋽ CIRCLED KATAKANA WE
}

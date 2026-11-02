"""Character coverage for Lovely Serif.

The Japanese kanji set is derived from the JIS X 0208 and JIS X 0213 (plane 1)
code tables through Python's own codecs, so no external data file is needed.
JIS X 0213 plane 1 contains every Jōyō kanji (2,136, including 𠮟, 剝, 頰,
塡) and every Jinmeiyō kanji.
"""
from __future__ import annotations

from typing import Dict, Iterable, Set

# ---------------------------------------------------------------------------
# Latin: everything Nanum Myeongjo can supply in these blocks is taken from it.
LATIN_BLOCKS = [
    (0x0020, 0x007E),  # Basic Latin
    (0x00A0, 0x00FF),  # Latin-1 Supplement
    (0x0100, 0x017F),  # Latin Extended-A
    (0x02C6, 0x02DD),  # spacing modifier letters (ˆ ˇ ˘ ˙ ˚ ˛ ˜ ˝)
    (0x2010, 0x2027),  # general punctuation (dashes, quotes, bullet, ellipsis)
    (0x2030, 0x205E),
    (0x20A0, 0x20CF),  # currency symbols
    (0x2122, 0x2122),  # ™
]
# Punctuation that should keep its Japanese (Noto) design even though Nanum has it.
JAPANESE_PRIORITY = {
    0x00A7, 0x00A8, 0x00B0, 0x00B1, 0x00B4, 0x00B6, 0x00D7, 0x00F7,
    0x2010, 0x2012, 0x2013, 0x2014, 0x2015, 0x2016, 0x2018, 0x2019, 0x201C, 0x201D,
    0x2020, 0x2021, 0x2025, 0x2026, 0x2030, 0x2032, 0x2033, 0x203B, 0x2103,
}

SYMBOL_BLOCKS = [
    (0x2070, 0x209F),  # super/subscripts
    (0x2100, 0x214F),  # letterlike (℃ № ℡ ™ Ω)
    (0x2150, 0x218F),  # number forms (Ⅰ Ⅱ ⅰ ⅱ ⅓ …)
    (0x2190, 0x21FF),  # arrows
    (0x2200, 0x22FF),  # mathematical operators
    (0x2300, 0x23FF),  # misc technical
    (0x2460, 0x24FF),  # enclosed alphanumerics (①②③ ⒜ …)
    (0x2500, 0x257F),  # box drawing
    (0x2580, 0x259F),  # block elements
    (0x25A0, 0x25FF),  # geometric shapes (○●◎□■△▽◇◆☆★ …)
    (0x2600, 0x26FF),  # misc symbols (☆★☎♪♭♯ …)
    (0x2700, 0x27BF),  # dingbats
    (0x2E80, 0x2EFF),  # CJK radicals supplement
    (0x2F00, 0x2FDF),  # Kangxi radicals
    (0x3000, 0x303F),  # CJK symbols & punctuation (　、。〃〄々〆〇〈〉《》「」『』【】〒〓〔〕〖〗〘〙〚〛〜〝〞〟〠〡〰〱〲〳〴〵〶〷〻〼〽〾〿)
    (0x3041, 0x309F),  # hiragana
    (0x30A0, 0x30FF),  # katakana
    (0x3190, 0x319F),  # kanbun
    (0x31F0, 0x31FF),  # katakana phonetic extensions
    (0x3200, 0x32FF),  # enclosed CJK letters & months (㈱ ㊤ ㋐ …)
    (0x3300, 0x33FF),  # CJK compatibility (㍻ ㎝ ㎏ ㍿ …)
    (0xFE10, 0xFE1F),  # vertical forms
    (0xFE30, 0xFE4F),  # CJK compatibility forms
    (0xFF00, 0xFFEF),  # halfwidth & fullwidth forms
    (0x1F100, 0x1F1FF),  # enclosed alphanumeric supplement (🄀 …, Noto has a few)
    (0x1F200, 0x1F2FF),  # enclosed ideographic supplement (🈚 🈯 …)
]


def _range_set(blocks) -> Set[int]:
    s: Set[int] = set()
    for lo, hi in blocks:
        s.update(range(lo, hi + 1))
    return s


def jis_kanji(plane2: bool = False) -> Set[int]:
    """All ideographs encodable in JIS X 0213 plane 1 (⊇ JIS X 0208 ⊇ Jōyō)."""
    out: Set[int] = set()
    ranges = [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x20000, 0x2A6DF)]
    for lo, hi in ranges:
        for cp in range(lo, hi + 1):
            try:
                b = chr(cp).encode("shift_jis_2004")
            except UnicodeEncodeError:
                continue
            if len(b) != 2:
                continue
            lead = b[0]
            in_plane2 = lead >= 0xF0
            if in_plane2 and not plane2:
                continue
            out.add(cp)
    return out


def jis_x0208_kanji() -> Set[int]:
    out: Set[int] = set()
    for cp in range(0x4E00, 0xA000):
        try:
            chr(cp).encode("shift_jis")
        except UnicodeEncodeError:
            continue
        out.add(cp)
    return out


def jis_nonkanji() -> Set[int]:
    """Non-kanji JIS X 0213 plane-1 characters (symbols, kana, etc.) minus Greek/Cyrillic."""
    out: Set[int] = set()
    for cp in list(range(0x00A0, 0x0400)) + list(range(0x2000, 0x33FF)) + list(range(0xFE30, 0xFFF0)):
        if 0x0370 <= cp <= 0x03FF or 0x0400 <= cp <= 0x04FF:
            continue
        try:
            b = chr(cp).encode("shift_jis_2004")
        except UnicodeEncodeError:
            continue
        if len(b) == 2 and b[0] < 0xF0:
            out.add(cp)
    return out


def latin_set() -> Set[int]:
    return _range_set(LATIN_BLOCKS)


def symbol_set() -> Set[int]:
    return _range_set(SYMBOL_BLOCKS)


def target_set() -> Set[int]:
    s = latin_set() | symbol_set() | jis_kanji() | jis_nonkanji()
    # drop Greek / Cyrillic (not a target for Lovely Serif)
    s -= set(range(0x0370, 0x0500))
    s -= set(range(0x0180, 0x0250))   # Latin Extended-B (pinyin letters in JIS X 0213) — no case pairs available
    s -= {0x0000}
    from .config import EXCLUDE_CODEPOINTS
    s -= EXCLUDE_CODEPOINTS
    return s


# A compact Jōyō check-list (2,136 characters) is useful for coverage reports.
# It is generated at build time from the JIS tables + the official 2010 list
# size, and verified against the font's cmap in reports/coverage.md.

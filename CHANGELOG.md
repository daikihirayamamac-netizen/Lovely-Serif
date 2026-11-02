# Changelog

## 0.1.1 (2026-11-02)

Removed
- ゑ ヱ ヹ ㋽ (the "we" kana in all forms) are no longer in the font. Text that contains them falls back to the next font in the CSS stack.

Fixed
- Accented Latin (À–ÿ, Ç ç, Ā ā …) was taken from Noto Serif JP and looked heavier and different from the rest of the Latin. It is now built from the Nanum Myeongjo base letters plus the accent, and gets the same softening and weight as the other letters.
- Œ œ Ł ł Đ đ Ħ ħ Ŋ ŋ Ĳ ĳ Ŧ ŧ ĸ Ŀ ŀ existed in Nanum Myeongjo but were dropped because Noto Serif JP lacks them. They are now included.
- 啻 撻 瀦 茗: corner rounding made a contour cross itself where it touched itself. Any glyph where this happens is now re-shaped with smaller radii automatically.
- 戀: a zero-area two-point contour left by the rounding is removed.
- Thin Latin ends (hyphen, plus, 4, E, L …) were rounded almost into semicircles, a rounded-gothic look. The rounding now keeps a flat cut.
- The Latin weight adjustment ate 3 units of each sidebearing, which tightened all Latin spacing. Advance widths now grow with the ink so the spacing matches Nanum Myeongjo. m n i l k get extra room for the new exit sweep.
- `LovelySerif-Regular-std.woff2` claimed to contain all Jōyō kanji but lacked 34 of them (鬱 丼 嘲 曖 𠮟 剝 頰 塡 …). It now contains all 2,136, checked against `data/joyo.txt`.
- OpenType feature lists are sorted by tag (OTS warning).
- Preview site: vertical-text cards overflowed the screen on phones; the font preload raised a CORS error when the page was opened from disk.

Added
- `scripts/qa.py`: outline QA over every glyph (self-intersection, degenerate segments, direction, emptied glyphs, deformation vs. the source).
- `scripts/verify.py`: TTF vs OTF outline match, Latin spacing collision check over 2,500 pairs, Jōyō coverage, exclusion check.
- `data/joyo.txt`: the 2,136 Jōyō kanji.

## 0.1.0 (2026-11-01)

First Regular build.

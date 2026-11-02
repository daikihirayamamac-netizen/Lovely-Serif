#!/usr/bin/env python3
"""Generate the preview / type-tester site (preview/index.html) from the built font.

    python scripts/make_preview.py                       # → preview/index.html (uses ../fonts/)
    python scripts/make_preview.py --font-url fonts/LovelySerif-Regular.woff2 --out /tmp/site/index.html
"""
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from fontTools.ttLib import TTFont
from lovelyserif import coverage as COV
from lovelyserif import config as C

TEMPLATE_PATH = os.path.join(ROOT, "preview", "template.html")


def artifact_variant(html: str) -> str:
    """Strip the document skeleton (the Artifact host adds its own) and adapt the page contract."""
    import re
    head_end = html.index("<link rel=\"preconnect\"")
    html = "<title>Lovely Serif Preview</title>\n<meta name=\"claude:viewport-fit-sides\" content=\"cover\">\n" + html[head_end:]
    html = html.replace("</head>\n<body>\n", "").replace("\n</body>\n</html>", "")
    html = html.replace(".wrap{max-width:1100px;margin:0 auto;padding:0 16px}",
                        ".wrap{max-width:1100px;margin:0 auto;padding-left:max(16px, env(safe-area-inset-left, 0px));padding-right:max(16px, env(safe-area-inset-right, 0px))}")
    html = html.replace("position:sticky;top:0;", "position:sticky;top:env(safe-area-inset-top, 0px);")
    html = html.replace("--card:#242120;--shadow:0 10px 40px rgba(0,0,0,.4)}}", "--card:#242120;--shadow:0 10px 40px rgba(0,0,0,.4);color-scheme:dark}}")
    html = html.replace("--card:#242120;--shadow:0 10px 40px rgba(0,0,0,.4)}\n", "--card:#242120;--shadow:0 10px 40px rgba(0,0,0,.4);color-scheme:dark}\nbody::before{content:\"\";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top, 0px);z-index:10;background:var(--paper)}\n")
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=os.path.join(ROOT, "fonts", "LovelySerif-Regular.ttf"))
    ap.add_argument("--font-url", default="../fonts/LovelySerif-Regular.woff2")
    ap.add_argument("--compare-url", default="../reports/compare/")
    ap.add_argument("--out", default=os.path.join(ROOT, "preview", "index.html"))
    ap.add_argument("--artifact", action="store_true", help="emit a body-only page for publishing as a claude.ai Artifact")
    a = ap.parse_args()
    f = TTFont(a.font)
    cmap = f.getBestCmap()
    jis208 = sorted(cp for cp in COV.jis_x0208_kanji() if cp in cmap)
    jis213 = sorted(cp for cp in COV.jis_kanji() if cp in cmap)
    hira = "".join(chr(c) for c in range(0x3041, 0x3097) if c in cmap)
    kata = "".join(chr(c) for c in range(0x30A1, 0x30FB) if c in cmap)
    # common kanji wall: the first JIS level-1 rows are ordered by reading; take a sampler of 320
    level1 = []
    for cp in jis208:
        b = chr(cp).encode("shift_jis")
        if b[0] <= 0x98 and (b[0] < 0x98 or b[1] <= 0x72):
            level1.append(cp)
    wall = "".join(chr(c) for c in level1[::9][:360])
    stats = dict(glyphs=len(f.getGlyphOrder()), codepoints=len(cmap), jis208=len(jis208), jis208_total=len(COV.jis_x0208_kanji()),
                 jis213=len(jis213), jis213_total=len(COV.jis_kanji()), version=C.VERSION)
    html = open(TEMPLATE_PATH, encoding="utf-8").read()
    repl = {
        "{{FONT_URL}}": a.font_url, "{{COMPARE_URL}}": a.compare_url, "{{HIRAGANA}}": hira, "{{KATAKANA}}": kata,
        "{{KANJI_WALL}}": wall, "{{STATS}}": json.dumps(stats, ensure_ascii=False), "{{VERSION}}": C.VERSION,
        "{{N_GLYPHS}}": f"{stats['glyphs']:,}", "{{N_CODEPOINTS}}": f"{stats['codepoints']:,}",
        "{{N_JIS208}}": f"{stats['jis208']:,}/{stats['jis208_total']:,}", "{{N_JIS213}}": f"{stats['jis213']:,}/{stats['jis213_total']:,}",
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    if a.artifact:
        html = artifact_variant(html)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(html)
    print("wrote", a.out, stats)


if __name__ == "__main__":
    main()

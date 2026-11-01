#!/usr/bin/env python3
"""Build Lovely Serif.

    python scripts/build.py                # full build → fonts/, sources/LovelySerif-Regular.ufo, reports/
    python scripts/build.py --no-ufo       # skip the UFO export
    python scripts/build.py --quick        # TTF only, no reports (for design iteration)
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lovelyserif import sources
from lovelyserif.build import build


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default=os.path.join(ROOT, "sources", "upstream"))
    ap.add_argument("--out", default=os.path.join(ROOT, "fonts"))
    ap.add_argument("--ufo", default=os.path.join(ROOT, "sources", "LovelySerif-Regular.ufo"))
    ap.add_argument("--reports", default=os.path.join(ROOT, "reports"))
    ap.add_argument("--no-ufo", action="store_true")
    ap.add_argument("--no-reports", action="store_true")
    ap.add_argument("--quick", action="store_true", help="TTF only, no UFO/reports")
    ap.add_argument("--fetch", action="store_true", help="download upstream fonts first")
    a = ap.parse_args()
    if a.fetch or not sources.verify(a.upstream, ["NanumMyeongjo-Regular.ttf", "NotoSerifJP-Regular.otf"]):
        sources.fetch(a.upstream, ["NanumMyeongjo-Regular.ttf", "NotoSerifJP-Regular.otf"])
    build(a.upstream, a.out,
          ufo_path=None if (a.no_ufo or a.quick) else a.ufo,
          report_dir=None if (a.no_reports or a.quick) else a.reports,
          make_otf=not a.quick, make_ttf=True, make_woff2=not a.quick)


if __name__ == "__main__":
    main()

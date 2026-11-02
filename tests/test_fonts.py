"""Fast smoke tests on the built fonts (run after `python scripts/build.py`):

    python -m unittest discover -s tests -v
"""
import os
import unittest

from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "fonts")


def load(name):
    return TTFont(os.path.join(FONTS, name))


class FontSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.otf = load("LovelySerif-Regular.otf")
        cls.ttf = load("LovelySerif-Regular.ttf")
        cls.std = load("LovelySerif-Regular-std.woff2")
        cls.joyo = open(os.path.join(ROOT, "data", "joyo.txt"), encoding="utf-8").read().strip()

    def test_names(self):
        n = self.otf["name"]
        self.assertEqual(n.getDebugName(1), "Lovely Serif")
        self.assertEqual(n.getDebugName(6), "LovelySerif-Regular")
        for bad in ("Nanum", "Noto", "Source"):  # OFL reserved font names
            self.assertNotIn(bad, n.getDebugName(1))

    def test_joyo_complete(self):
        self.assertEqual(len(self.joyo), 2136)
        for font in (self.otf, self.ttf, self.std):
            cmap = font.getBestCmap()
            self.assertEqual([c for c in self.joyo if ord(c) not in cmap], [])

    def test_excluded_kana_absent(self):
        for font in (self.otf, self.ttf, self.std):
            cmap = font.getBestCmap()
            for cp in (0x3091, 0x30F1, 0x30F9, 0x32FD):
                self.assertNotIn(cp, cmap)

    def test_vertical_and_layout(self):
        for t in ("vhea", "vmtx", "GSUB", "GPOS", "GDEF", "BASE"):
            self.assertIn(t, self.otf)
        feats = {fr.FeatureTag for fr in self.otf["GSUB"].table.FeatureList.FeatureRecord}
        self.assertTrue({"vert", "vrt2", "fwid", "hwid", "pwid"} <= feats)

    def test_metrics_match_noto_serif_jp(self):
        os2, hhea = self.otf["OS/2"], self.otf["hhea"]
        self.assertEqual((os2.sTypoAscender, os2.sTypoDescender, hhea.ascent, hhea.descent), (880, -120, 1151, -286))
        self.assertEqual(self.otf["head"].unitsPerEm, 1000)

    def test_latin_and_accents(self):
        cmap = self.otf.getBestCmap()
        for ch in "AaMmÀéñüçŒœŁł":
            self.assertIn(ord(ch), cmap, ch)


if __name__ == "__main__":
    unittest.main()

// Screenshot a local HTML/SVG file or URL with Playwright (Chromium).
//   node scripts/dev/shot.js <file|url> <out.png> [width=1400] [height=900] [fullPage=1]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [,, src, out, w = '1400', h = '900', full = '1'] = process.argv;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  await page.goto(src.startsWith('http') ? src : 'file://' + path.resolve(src), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  await page.screenshot({ path: out, fullPage: full === '1' });
  await browser.close();
})();

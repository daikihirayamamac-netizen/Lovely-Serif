// Regenerate docs/screenshots/{preview-top,chromium-mixed-vertical}.png from the built font.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const root = path.resolve(__dirname, '../..');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: 1.5 });
  await page.goto('file://' + root + '/preview/index.html', { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(400);
  await page.screenshot({ path: root + '/docs/screenshots/preview-top.png', clip: { x: 0, y: 0, width: 1200, height: 900 } });
  const html = `<!doctype html><html lang="ja"><meta charset="utf-8"><style>
  @font-face{font-family:"LS";src:url("file://${root}/fonts/LovelySerif-Regular.woff2")}
  body{font-family:"LS",serif;margin:28px;background:#fff;color:#1a1a1a}h1{font-weight:normal;font-size:56px;margin:0 0 8px}
  .p{font-size:20px;line-height:1.9;max-width:860px}.row{display:flex;gap:36px;margin-top:18px}.v{writing-mode:vertical-rl;height:430px;font-size:21px;line-height:2.1}
  .small{font-size:13px;line-height:1.8;max-width:860px;color:#333}</style><body>
  <h1>Lovely Serif　文字から、美しさを。</h1>
  <div class="p">日常の文章を、もっと美しく、やさしく。静かで、上品で、読むほどに心地よい新しい明朝体です。A refined serif typeface for a more beautiful world — designed for Japanese, with harmony in English.</div>
  <div class="small">常用漢字：憂鬱な薔薇の檸檬、𠮟る・剝がす・頰・塡める。ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789 ！？「」『』【】〒※〜…・ ①②③ ㈱ ℃ ← → ○●◎</div>
  <div class="row"><div class="v">縦書きのテスト。「ことばが、日常をやさしくする。」——二〇二六年、Lovely Serif（ラブリーセリフ）。</div>
  <div class="v" style="font-feature-settings:'vpal' 1">縦書き（vpal）『季節の移ろい』——春夏秋冬、ゆらぎ…。ABC 123</div></div></body></html>`;
  await page.setContent(html, { waitUntil: 'networkidle' }); await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(400);
  await page.screenshot({ path: root + '/docs/screenshots/chromium-mixed-vertical.png', fullPage: true });
  await browser.close();
})();

// Check preview/index.html at phone/tablet widths: horizontal overflow, broken images, console errors.
//   node scripts/dev/mobile_check.js [out390.png]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const page_url = 'file://' + path.resolve(__dirname, '../../preview/index.html');
  const b = await chromium.launch();
  let bad = 0;
  for (const w of [360, 390, 768]) {
    const p = await b.newPage({ viewport: { width: w, height: 800 } });
    const errs = [];
    p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    p.on('pageerror', e => errs.push(String(e)));
    await p.goto(page_url, { waitUntil: 'networkidle' });
    await p.evaluate(() => document.fonts.ready);
    const r = await p.evaluate(() => {
      const de = document.documentElement, W = de.clientWidth, off = [];
      document.querySelectorAll('body *').forEach(el => { const rc = el.getBoundingClientRect(); if (rc.right > W + 1 && rc.width > 0) off.push(el.tagName + '.' + el.className); });
      return { scrollW: de.scrollWidth, W, off: off.slice(0, 10), font: document.fonts.check('20px "Lovely Serif"'), broken: [...document.images].filter(i => !i.naturalWidth).map(i => i.getAttribute('src')) };
    });
    const ok = r.scrollW <= r.W && !r.off.length && !r.broken.length && !errs.length && r.font;
    if (!ok) bad++;
    console.log(ok ? 'OK ' : 'BAD', w, JSON.stringify(r), errs.slice(0, 3));
    if (w === 390 && process.argv[2]) await p.screenshot({ path: process.argv[2] });
    await p.close();
  }
  await b.close();
  process.exit(bad ? 1 : 0);
})();

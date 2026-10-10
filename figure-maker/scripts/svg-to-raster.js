#!/usr/bin/env node
/* svg-to-raster.js —— 把 SVG 转成位图（PNG），供 A 类（Mermaid）直出位图使用
 *
 * 用法：node svg-to-raster.js --in fig.svg --out fig.png [--scale 2] [--width 1200]
 * 说明：用 Playwright Chromium 按 SVG 的固有尺寸（viewBox）截图，scale 控制分辨率倍数。
 *       只依赖 playwright（A 类本来就依赖它做 Mermaid 渲染）。
 */
const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const a = {};
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (k.startsWith('--')) a[k.slice(2)] = (argv[i + 1] && !argv[i + 1].startsWith('--')) ? argv[++i] : true;
  }
  return a;
}

(async () => {
  const a = parseArgs(process.argv);
  if (!a.in || !a.out) { console.error('用法：node svg-to-raster.js --in fig.svg --out fig.png [--scale 2]'); process.exit(2); }
  const svg = fs.readFileSync(a.in, 'utf8');
  const scale = Number(a.scale || 2);           // 默认 2× 提高清晰度（矢量缩放无损）
  // 跨平台解析 Playwright（浏览器目录 + 模块位置）——逻辑**唯一一份**在 pw-env.js
  const { applyBrowserDir, requirePlaywright } = require('./pw-env');
  applyBrowserDir();
  const playwright = requirePlaywright();
  let browser;
  try { browser = await playwright.chromium.launch({ channel: 'chromium' }); }
  catch (e) { browser = await playwright.chromium.launch(); }
  const page = await browser.newPage({ deviceScaleFactor: scale });
  await page.setContent(
    '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:#fff}svg{display:block}</style>' + svg,
    { waitUntil: 'load' });
  const el = await page.$('svg');
  if (!el) { console.error('❌ 输入里没有 <svg> 元素'); await browser.close(); process.exit(1); }
  fs.mkdirSync(path.dirname(path.resolve(a.out)), { recursive: true });
  await el.screenshot({ path: a.out });          // 按 SVG 渲染尺寸截图（含 viewBox 大小）
  await browser.close();
  const kb = (fs.statSync(a.out).size / 1024).toFixed(0);
  console.log(JSON.stringify({ ok: true, out: a.out, kb: Number(kb), scale }));
})().catch((e) => { console.error('❌ svg-to-raster：' + (e && e.message)); process.exit(1); });

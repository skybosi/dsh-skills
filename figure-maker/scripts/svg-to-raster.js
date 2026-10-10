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
// 浏览器目录自动探测：**必须与 render-mermaid.js 保持一致**，否则会出现
  // 「A 类 SVG 能出、PNG/WebP 报 Executable doesn't exist」这种半残状态（实测踩过）。
  if (!process.env.PLAYWRIGHT_BROWSERS_PATH) {
    const cands = ['/tmp/pw-browsers', path.join(require('os').homedir(), 'Library/Caches/ms-playwright')];
    for (const c of cands) { if (fs.existsSync(c)) { process.env.PLAYWRIGHT_BROWSERS_PATH = c; break; } }
  }
  // Playwright 解析：① 常规 node_modules（npm i playwright）② 本机可能装在别处 → 用 PW_MODULES 指定
  let playwright = null;
  try { playwright = require('playwright'); }
  catch (e) {
    const PW = process.env.PW_MODULES || '/tmp/pw/node_modules';
    playwright = require(path.join(PW, 'playwright'));   // 与 render-mermaid.js 同款解析
  }
  // 浏览器目录自动探测：**必须与 render-mermaid.js 保持一致**，否则会出现
  // 「A 类 SVG 能出、PNG/WebP 报 Executable doesn't exist」这种半残状态（实测踩过）。
  if (!process.env.PLAYWRIGHT_BROWSERS_PATH) {
    const cands = ['/tmp/pw-browsers', path.join(require('os').homedir(), 'Library/Caches/ms-playwright')];
    for (const c of cands) { if (fs.existsSync(c)) { process.env.PLAYWRIGHT_BROWSERS_PATH = c; break; } }
  }
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

/** pw-env.js —— Playwright 的**跨平台**解析（Windows / macOS / Linux）。唯一一份。
 *
 *  以前这段逻辑在 render-mermaid.js 与 svg-to-raster.js 里各写一遍（svg-to-raster 里还贴了两遍），
 *  而且候选目录只有 macOS 的 ~/Library/Caches —— **Linux / Windows 上直接失效**，
 *  表现为「A 类 SVG 能出、PNG/WebP 报 Executable doesn't exist」这种半残状态。
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

/** 浏览器目录候选（按平台）；环境变量优先 */
function browserDirs() {
  const home = os.homedir();
  return [
    process.env.PLAYWRIGHT_BROWSERS_PATH,
    path.join(home, 'Library', 'Caches', 'ms-playwright'),                      // macOS
    path.join(home, '.cache', 'ms-playwright'),                                 // Linux
    path.join(process.env.LOCALAPPDATA || path.join(home, 'AppData', 'Local'),  // Windows
              'ms-playwright'),
    '/tmp/pw-browsers',                                                         // 本机 / CI 临时安装
  ].filter(Boolean);
}

/** 候选的 playwright 模块目录（用来读 playwright-core/browsers.json 的版本号） */
function candidateModuleDirs() {
  return [
    process.env.PW_MODULES,
    path.join(__dirname, '..', 'node_modules'),
    path.join(__dirname, '..', '..', 'node_modules'),
    path.join(__dirname, 'node_modules'),
    '/tmp/pw/node_modules',
  ].filter(Boolean);
}

/** 当前安装的 Playwright 期望的 chromium 版本号（读 playwright-core/browsers.json；读不到返回 null） */
function expectedChromiumRev() {
  for (const d of candidateModuleDirs()) {
    const j = path.join(d, 'playwright-core', 'browsers.json');
    try {
      if (!fs.existsSync(j)) continue;
      const b = (JSON.parse(fs.readFileSync(j, 'utf8')).browsers || [])
        .find((x) => x.name === 'chromium');
      if (b && b.revision) return String(b.revision);
    } catch (e) { /* 继续找下一个 */ }
  }
  return null;
}

/** 目录里是否有**可用**的 chromium：只存在目录不够 —— 版本号不对照样报
 *  `Executable doesn't exist`（实测本机 ~/Library/Caches/ms-playwright 只有旧版 1217/1223，
 *  而模块要 1243）。所以按 browsers.json 的版本号校验；拿不到版本号时退回「有没有 chromium* 目录」。 */
function hasUsableChromium(dir, rev) {
  if (!dir || !fs.existsSync(dir)) return false;
  try {
    const names = fs.readdirSync(dir);
    if (!rev) return names.some((n) => /^chromium/.test(n));
    return names.includes('chromium-' + rev) || names.includes('chromium_headless_shell-' + rev);
  } catch (e) {
    return false;
  }
}

/** 探测并设置 PLAYWRIGHT_BROWSERS_PATH；没有可用目录就交给 Playwright 自己找 */
function applyBrowserDir() {
  if (process.env.PLAYWRIGHT_BROWSERS_PATH) return process.env.PLAYWRIGHT_BROWSERS_PATH;
  const rev = expectedChromiumRev();
  for (const d of browserDirs()) {
    if (hasUsableChromium(d, rev)) { process.env.PLAYWRIGHT_BROWSERS_PATH = d; return d; }
  }
  return null;
}

/** 解析 playwright 模块：常规安装 → PW_MODULES → 脚本目录上下级 node_modules → 临时目录 */
function requirePlaywright() {
  const tries = [
    'playwright',
    process.env.PW_MODULES ? path.join(process.env.PW_MODULES, 'playwright') : null,
    path.join(__dirname, '..', 'node_modules', 'playwright'),
    path.join(__dirname, '..', '..', 'node_modules', 'playwright'),
    path.join(__dirname, 'node_modules', 'playwright'),
    '/tmp/pw/node_modules/playwright',
  ].filter(Boolean);
  let lastErr = null;
  for (const t of tries) {
    try { return require(t); } catch (e) { lastErr = e; }
  }
  throw new Error('找不到 playwright 模块。试过：' + tries.join('、') +
    '\n  安装：npm i playwright && npx playwright install chromium' +
    '\n  或指定：PW_MODULES=<node_modules 所在目录>' +
    '\n  最后一个错误：' + (lastErr && lastErr.message));
}

module.exports = { applyBrowserDir, browserDirs, expectedChromiumRev, hasUsableChromium,
                   requirePlaywright };

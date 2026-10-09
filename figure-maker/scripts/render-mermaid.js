#!/usr/bin/env node
/**
 * 配图管线 v2 · A 类结构化图渲染器（Mermaid → SVG）
 *
 * 为什么需要它：新规范要求 A 类输出 Mermaid 源码，但站点与小程序实际取的是
 * `content/courses/<slug>/assets/chapter-N-figure-MM.svg`，所以必须把 Mermaid 渲染成 SVG。
 *
 * 用法（CLI）：
 *   node render-mermaid.js --in fig.mmd --out fig.svg [--title "标题"] [--json 检查结果.json]
 *
 * 除了出图，它还把《布局质量红线》变成**可量化的机器检查**（在浏览器里用 getBBox 实测）：
 *   · 文字重叠：两个 <text> 的 bbox 相交面积 > 阈值
 *   · 文字溢出节点：<text> 的 bbox 不在所属节点 <rect>/<polygon> 内
 *   · 节点挤压：节点 bbox 之间最小间距 < 20px
 *   · 越界：任何元素超出画布 viewBox（等价于「文字跑到图外」）
 * 返回结构里带 checks，供生成器汇总成《布局检查》证据（不靠自述打勾）。
 */
const fs = require('fs');
const path = require('path');

const PW = process.env.PW_MODULES || '/tmp/pw/node_modules';
// Playwright 默认走 "chromium headless shell"，本机只装了完整 Chromium → 指定浏览器官网目录
if (!process.env.PLAYWRIGHT_BROWSERS_PATH) {
  const cands = ['/tmp/pw-browsers', path.join(require('os').homedir(), 'Library/Caches/ms-playwright')];
  for (const c of cands) { if (fs.existsSync(c)) { process.env.PLAYWRIGHT_BROWSERS_PATH = c; break; } }
}
let chromium;
try { ({ chromium } = require('playwright')); }                    // 常规安装
catch (e) { ({ chromium } = require(path.join(PW, 'playwright'))); }  // 本机特殊位置（PW_MODULES）
// 优先用**随 skill 内置**的 mermaid 运行时（这样 skill 独立、无需 npm install）；
// 没有内置时才回退到 node_modules 里的包。
const path0 = require('path'), fs0 = require('fs');
const VENDOR = path0.join(__dirname, 'vendor', 'mermaid.min.js');
const MERMAID_JS = fs0.existsSync(VENDOR) ? VENDOR : require.resolve('mermaid/dist/mermaid.min.js');

const FONT_STACK = 'system-ui, -apple-system, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", Arial, sans-serif';

function parseArgs(argv) {
  const a = { title: '', json: '', curve: '' };
  for (let i = 2; i < argv.length; i += 2) {
    const k = argv[i].replace(/^--/, '');
    a[k] = argv[i + 1];
  }
  return a;
}

/** 在浏览器里渲染 Mermaid 并做几何检查 */
async function renderMermaid(mmd, opts = {}) {
  // channel:'chromium' 明确要求完整 Chromium（headless shell 本机未安装）
  let browser;
  try { browser = await chromium.launch({ channel: 'chromium' }); }
  catch (e) { browser = await chromium.launch(); }
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 1 });
    page.setDefaultTimeout(45000);          // 浏览器侧超时：任何一步卡住都在 45s 内失败退出
    page.setDefaultNavigationTimeout(45000);
    await page.setContent(
      `<!doctype html><html><head><meta charset="utf-8"><style>
         html,body{margin:0;padding:0;background:#FFFFFF;}
         body{font-family:${FONT_STACK};}
         #canvas{display:inline-block;padding:24px 28px;background:#FFFFFF;}
       </style></head><body><div id="canvas"></div></body></html>`,
      { waitUntil: 'load' }
    );
    await page.addScriptTag({ path: MERMAID_JS });
    const result = await page.evaluate(async ({ code, title, curve }) => {
      /* global mermaid */
      // 规范里的 %%{init}%% 指令照旧保留在源码里；这里再把同一套参数设为**默认值**，
      // 保证即使某些版本对指令里的 flowchart 子项解析有差异，也不会退回 mermaid 默认的曲线布局。
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'loose',
        theme: 'base',
        htmlLabels: false,          // 顶层同样关掉（不同版本读的位置不一样）
        themeVariables: {
          fontFamily: 'system-ui, -apple-system, "Noto Sans SC", "PingFang SC", sans-serif',
          fontSize: '14px', lineColor: '#6B7280', primaryTextColor: '#212529',
          // ⚠️ Mermaid 会给每条边画「标签底色矩形」（即使没有标签）→ 箭头拐弯处出现淡紫色块。
          //    这里把标签底色设成全透明，并在事后用 CSS 兜底清掉残留的 .edgeLabel rect / .labelBkg。
          edgeLabelBackground: 'transparent', labelBackground: 'transparent',
        },
        // 曲线默认改为平滑（basis）：用户反馈「折线不好看」；--curve linear 可切回直角折线
        flowchart: { nodeSpacing: 24, rankSpacing: 28, curve: curve || 'basis', padding: 12,
                     // ⚠️ 必须 false：HTML 标签会渲染成 <foreignObject>，浏览器能看、
                     //    但微信小程序 image 组件不支持 → 端上标签会整块丢失
                     htmlLabels: false },
      });
      const id = 'fig' + Math.abs(code.split('').reduce((h, c) => (h * 31 + c.charCodeAt(0)) | 0, 7));
      const { svg } = await mermaid.render(id, code);
      const canvas = document.getElementById('canvas');
      canvas.innerHTML = svg;
      const svgEl = canvas.querySelector('svg');
      svgEl.removeAttribute('style');                       // 去掉 max-width，避免站点里被压缩
      // ⚠️ 关键修复：classDef 的类名 `root` 与 Mermaid 容器类 `.root` **撞名** —— Mermaid 为
      //    classDef root 生成的规则 `#fig… .root path{fill:…!important;stroke:…!important}` 会命中
      //    容器内**所有 path**（包括边路径），于是边被强制填色，拐弯处出现实心色块。
      //    这里把这条规则从 SVG 的 <style> 里删掉（classDef 的节点配色由 .node.<class> 规则负责，不受影响）。
      svgEl.querySelectorAll('style').forEach((stEl) => {
        stEl.textContent = stEl.textContent.replace(/#[\w-]+\s+\.root\s+path\s*\{[^}]*\}/g, '');
      });
      // 兜底：边路径一律不填充 + 边标签底色透明（双保险，用内联 !important）
      svgEl.querySelectorAll('path').forEach((pe) => {
        const cls = pe.getAttribute('class') || '';
        if (/flowchart-link|edge-thickness/.test(cls)) pe.style.setProperty('fill', 'none', 'important');
      });
      svgEl.querySelectorAll('.edgeLabel rect, .edgeLabel .background, rect.background').forEach((re) => {
        re.style.setProperty('fill', 'none', 'important');
        re.style.setProperty('opacity', '0', 'important');
      });
      const st = svgEl.querySelector('style');
      if (st) st.textContent += '\n' +
        // ① 边路径：Mermaid 会把 classDef 的填充色渗到 edge path 上 → 拐弯处出现实心色块，必须 fill:none
        '.edgePaths path,.flowchart-link,path.edge-thickness-normal,path.edge-thickness-thick{fill:none!important;}' +
        // ② 边标签底色矩形（无标签的边也会画）
        '.edgeLabel rect,.edgeLabel .background,.labelBkg,.edgeLabel foreignObject div{fill:none!important;opacity:0!important;background:transparent!important;}' +
        // ③ 箭头标记统一用线的颜色，避免残留主题色
        '.marker path,.marker polygon{fill:#6B7280!important;stroke:#6B7280!important;}';
      svgEl.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

      // ---- 标题（站点/端上直接显示 SVG，标题必须画进图里；规范里「标题不进 Mermaid」照旧遵守） ----
      const vb = svgEl.viewBox.baseVal;
      const W = vb.width, H = vb.height;
      const titleH = title ? 34 : 0;
      if (title) {
        svgEl.setAttribute('viewBox', `0 0 ${W} ${H + titleH}`);
        svgEl.setAttribute('height', H + titleH);
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('transform', `translate(0,${titleH})`);
        while (svgEl.firstChild) g.appendChild(svgEl.firstChild);
        svgEl.appendChild(g);
        const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        t.setAttribute('x', String(W / 2));
        t.setAttribute('y', '22');
        t.setAttribute('text-anchor', 'middle');
        t.setAttribute('font-family', 'system-ui, -apple-system, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", Arial, sans-serif');
        t.setAttribute('font-size', '16');
        t.setAttribute('font-weight', 'bold');
        t.setAttribute('fill', '#212529');
        t.setAttribute('id', 'fig-title');    // ⚠️ 必须给 id：htmlLabels=false 时节点标签也是 <text>，
        t.textContent = title;                //    用 querySelector('text') 会量到节点而不是标题
        svgEl.appendChild(t);
      }
      // 标题比图宽时必须扩画布（否则标题跑到图外 —— 规范红线④），并把图形水平居中
      if (title) {
        await document.fonts.ready;
        const tEl = svgEl.querySelector('#fig-title') || svgEl.querySelector('text');
        const tw = tEl.getComputedTextLength ? tEl.getComputedTextLength() : tEl.getBBox().width;
        const margin = 24;
        const needW = Math.max(W, Math.ceil(tw + margin * 2));
        if (needW > W) {
          const dx = Math.round((needW - W) / 2);
          const gEl = svgEl.querySelector('g');
          if (gEl) gEl.setAttribute('transform', `translate(${dx},${titleH})`);
          svgEl.setAttribute('viewBox', `0 0 ${needW} ${H + titleH}`);
          tEl.setAttribute('x', String(Math.round(needW / 2)));
        }
        svgEl.setAttribute('width', Math.max(W, Math.ceil(tw + margin * 2)));
      } else {
        svgEl.setAttribute('width', W);
      }
      svgEl.setAttribute('height', H + titleH);

      // ---- 机器版布局检查（全部用屏幕空间 getBoundingClientRect：所有元素同一坐标系，
      //      避免 getBBox 的局部坐标把正常布局误判成越界/挤压）----
      const R = (el) => { const b = el.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height, r: b.right, b2: b.bottom }; };
      const inter = (a, b) => Math.max(0, Math.min(a.r, b.r) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.b2, b.b2) - Math.max(a.y, b.y));
      const canvasRect = R(svgEl);   // 屏幕空间实测（已含扩宽后的画布）

      const nodeEls = [...svgEl.querySelectorAll('.node')];
      const nodes = nodeEls.map((n) => {
        const shape = n.querySelector('rect, polygon, circle, ellipse, path');
        const label = n.querySelector('foreignObject, text');
        return { txt: (n.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 22), box: shape ? R(shape) : R(n), labelBox: label ? R(label) : null };
      });
      const textEls = [...svgEl.querySelectorAll('text, foreignObject')].filter((t) => (t.textContent || '').trim().length);
      const textBoxes = textEls.map((t) => ({ box: R(t), txt: (t.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 22) }));

      // ① 文字重叠（相同文字＝同一标签被重复选中，跳过）
      const overlapText = [];
      for (let i = 0; i < textBoxes.length; i++)
        for (let j = i + 1; j < textBoxes.length; j++) {
          const a = textBoxes[i], b = textBoxes[j];
          if (a.txt === b.txt) continue;
          const ar = a.box.w * a.box.h, br = b.box.w * b.box.h;
          if (ar <= 0 || br <= 0) continue;
          const ov = inter(a.box, b.box);
          if (ov / Math.min(ar, br) > 0.12) overlapText.push({ a: a.txt, b: b.txt, ratio: +(ov / Math.min(ar, br)).toFixed(3) });
        }

      // ② 文字溢出节点框（节点内标签必须落在节点形状里，容差 2px）
      const overflow = [];
      for (const n of nodes) {
        if (!n.labelBox) continue;
        const pad = 2;
        const inside = n.labelBox.x >= n.box.x - pad && n.labelBox.r <= n.box.r + pad &&
                       n.labelBox.y >= n.box.y - pad && n.labelBox.b2 <= n.box.b2 + pad;
        if (!inside) overflow.push({ node: n.txt, dxl: +(n.box.x - n.labelBox.x).toFixed(1), dxr: +(n.labelBox.r - n.box.r).toFixed(1), dyt: +(n.box.y - n.labelBox.y).toFixed(1), dyb: +(n.labelBox.b2 - n.box.b2).toFixed(1) });
      }

      // ③ 节点间距（同层水平/垂直最小净距）
      let minGap = Infinity, tight = null;
      for (let i = 0; i < nodes.length; i++)
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i].box, b = nodes[j].box;
          const gx = Math.max(a.x - b.r, b.x - a.r, 0);
          const gy = Math.max(a.y - b.b2, b.y - a.b2, 0);
          const gap = Math.max(gx, gy);
          if (gap < minGap) { minGap = gap; tight = [nodes[i].txt, nodes[j].txt]; }
        }

      // ④ 越界（相对 SVG 画布）
      const outOfCanvas = [];
      for (const n of nodes) {
        if (n.box.x < canvasRect.x - 1 || n.box.y < canvasRect.y - 1 || n.box.r > canvasRect.r + 1 || n.box.b2 > canvasRect.b2 + 1)
          outOfCanvas.push({ el: n.txt, box: { x: +n.box.x.toFixed(1), y: +n.box.y.toFixed(1), r: +n.box.r.toFixed(1), b: +n.box.b2.toFixed(1) } });
      }
      for (const t of textBoxes) {
        if (t.txt.length && (t.box.x < canvasRect.x - 1 || t.box.r > canvasRect.r + 1 || t.box.y < canvasRect.y - 1 || t.box.b2 > canvasRect.b2 + 1))
          outOfCanvas.push({ el: '文字:' + t.txt, box: { x: +t.box.x.toFixed(1), y: +t.box.y.toFixed(1), r: +t.box.r.toFixed(1), b: +t.box.b2.toFixed(1) } });
      }

      return {
        svg: new XMLSerializer().serializeToString(svgEl),
        size: { w: Math.round(svgEl.viewBox.baseVal.width), h: Math.round(svgEl.viewBox.baseVal.height) },
        counts: { texts: textBoxes.length, nodes: nodes.length, edges: svgEl.querySelectorAll('.edgePath, path.flowchart-link').length },
        checks: {
          overlapText,
          overflow,
          outOfCanvas,
          nodeGap: { min: minGap === Infinity ? null : +minGap.toFixed(1), pair: tight },
        },
      };
    }, { code: mmd, title: opts.title || '', curve: opts.curve || '' });
    return result;
  } finally {
    await browser.close();
  }
}

async function main() {
  const a = parseArgs(process.argv);
  if (!a.in) { console.error('用法：node render-mermaid.js --in fig.mmd --out fig.svg [--title 标题] [--json 结果.json]'); process.exit(2); }
  const mmd = fs.readFileSync(a.in, 'utf8');
  const res = await renderMermaid(mmd, { title: a.title, curve: a.curve });
  if (a.out) { fs.mkdirSync(path.dirname(a.out), { recursive: true }); fs.writeFileSync(a.out, res.svg); }
  const c = res.checks;
  const ok = c.overlapText.length === 0 && c.overflow.length === 0 && c.outOfCanvas.length === 0 && (c.nodeGap.min === null || c.nodeGap.min >= 20);
  console.log(JSON.stringify({ out: a.out, size: res.size, counts: res.counts, checks: c, pass: ok }, null, 1));
  if (a.json) fs.writeFileSync(a.json, JSON.stringify(res.checks, null, 1));
  process.exit(ok ? 0 : 1);
}

module.exports = { renderMermaid };
if (require.main === module) main();

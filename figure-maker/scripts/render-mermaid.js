#!/usr/bin/env node
/**
 * figure-maker · A 类结构化图渲染器（Mermaid → SVG）
 *
 * 用法（CLI）：
 *   node render-mermaid.js --in fig.mmd --out fig.svg [--title "标题"] [--curve basis] [--json 检查结果.json]
 *
 * 退出码（**重要**：调用方靠它区分「画不出来」和「画出来但版式不过关」）：
 *   0 = 渲染成功 + 版式检查全绿
 *   1 = 渲染成功，但版式检查未通过（**SVG 已写出**，结果在 --json 里）
 *   2 = 用法错误
 *   3 = 渲染失败（Mermaid 解析/渲染异常，没有产物）
 *
 * 机器版版式检查（在浏览器里用 getBoundingClientRect 实测，全部同一坐标系）：
 *   · 文字重叠 overlapText ：两个文字 bbox 相交面积占比 > 12%
 *   · 文字溢出节点 overflow：节点内标签不在节点形状内（仅对 flowchart 类有意义）
 *   · 节点挤压 nodeGap    ：节点最小净距 < 该图型的阈值（**按图型分级**，非 flowchart 图型不套用 20px）
 *   · 越界 outOfCanvas    ：任何节点/文字超出画布 viewBox
 */
const fs = require('fs');
const path = require('path');

const PW = process.env.PW_MODULES || '/tmp/pw/node_modules';
// Playwright 默认走 "chromium headless shell"，本机可能只装了完整 Chromium → 指定浏览器目录
if (!process.env.PLAYWRIGHT_BROWSERS_PATH) {
  const cands = ['/tmp/pw-browsers', path.join(require('os').homedir(), 'Library/Caches/ms-playwright')];
  for (const c of cands) { if (fs.existsSync(c)) { process.env.PLAYWRIGHT_BROWSERS_PATH = c; break; } }
}
let chromium;
try { ({ chromium } = require('playwright')); }                      // 常规安装
catch (e) { ({ chromium } = require(path.join(PW, 'playwright'))); }  // 本机特殊位置（PW_MODULES）
// 优先用**随 skill 内置**的 mermaid 运行时（skill 独立、无需 npm install）
const VENDOR = path.join(__dirname, 'vendor', 'mermaid.min.js');
const MERMAID_JS = fs.existsSync(VENDOR) ? VENDOR : require.resolve('mermaid/dist/mermaid.min.js');

const FONT_STACK = 'system-ui, -apple-system, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", Arial, sans-serif';

// ---------------------------------------------------------------------------
// 软色板主题：flowchart 靠 classDef 上色，但**时序图 / ER / 类图 / C4 / 甘特 / 饼图
// 等图型没有 classDef**，以前只能吃 Mermaid 默认主题色（米黄/亮蓝），与本 skill 的
// 软色板不一致。这里把同一套 SOFT_COLORS 注入 themeVariables，让 A 类风格统一。
// 注：图内自带的 %%{init}%% 指令会覆盖同名变量，所以已有自定义配色的 spec 不受影响。
// ---------------------------------------------------------------------------
const SOFT_THEME = {
  primaryColor: '#DBEAFE', primaryBorderColor: '#93C5FD', primaryTextColor: '#212529',
  secondaryColor: '#F1F3F5', tertiaryColor: '#F8FBFF',
  lineColor: '#6B7280', textColor: '#212529', mainBkg: '#DBEAFE', nodeBorder: '#93C5FD',
  defaultLinkColor: '#6B7280', clusterBkg: '#F8FBFF', clusterBorder: '#E2E8F0',
  titleColor: '#212529', edgeLabelBackground: 'transparent', labelBackground: 'transparent',
  background: '#FFFFFF',
  // —— 时序图 ——
  actorBkg: '#DBEAFE', actorBorder: '#93C5FD', actorTextColor: '#212529', actorLineColor: '#9CA3AF',
  signalColor: '#4B5563', signalTextColor: '#212529',
  labelBoxBkgColor: '#FEF3C7', labelBoxBorderColor: '#FCD34D', labelTextColor: '#212529',
  loopTextColor: '#212529', noteBkgColor: '#FEF3C7', noteBorderColor: '#FCD34D', noteTextColor: '#212529',
  activationBkgColor: '#C4B5FD', activationBorderColor: '#93C5FD', sequenceNumberColor: '#FFFFFF',
  // —— 类图 / 状态图 ——
  classText: '#212529',
  fillType0: '#DBEAFE', fillType1: '#F1F3F5', fillType2: '#FEF3C7', fillType3: '#D1FAE5',
  fillType4: '#FBE4D5', fillType5: '#E9D5FF', fillType6: '#FECACA', fillType7: '#F8FBFF',
  // —— ER 图 ——
  attributeBackgroundColorOdd: '#F8FBFF', attributeBackgroundColorEven: '#FFFFFF',
  // —— 甘特图 ——
  sectionBkgColor: '#F8FBFF', altSectionBkgColor: '#FFFFFF', sectionBkgColor2: '#F1F3F5',
  taskBkgColor: '#93C5FD', taskBorderColor: '#93C5FD', taskTextColor: '#212529',
  taskTextOutsideColor: '#212529', taskTextDarkColor: '#212529',
  activeTaskBkgColor: '#E9B08A', activeTaskBorderColor: '#E9B08A',
  doneTaskBkgColor: '#E2E8F0', doneTaskBorderColor: '#ADB5BD',
  critBkgColor: '#F87171', critBorderColor: '#F87171', todayLineColor: '#F87171', gridColor: '#F1F3F5',
  // —— 饼图 ——
  pie1: '#93C5FD', pie2: '#86EFAC', pie3: '#E9B08A', pie4: '#C4B5FD', pie5: '#F87171',
  pie6: '#9CA3AF', pie7: '#4B5563', pie8: '#DBEAFE', pie9: '#D1FAE5', pie10: '#FEF3C7',
  pie11: '#FECACA', pie12: '#E9D5FF',
  pieTitleTextColor: '#212529', pieSectionTextColor: '#212529', pieLegendTextColor: '#212529',
  pieStrokeColor: '#FFFFFF', pieOuterStrokeColor: '#FFFFFF', pieOpacity: '0.9',
  // —— 四象限图 ——
  quadrant1Fill: '#DBEAFE', quadrant2Fill: '#F1F3F5', quadrant3Fill: '#F8FBFF', quadrant4Fill: '#FEF3C7',
  quadrant1TextFill: '#212529', quadrant2TextFill: '#212529', quadrant3TextFill: '#212529', quadrant4TextFill: '#212529',
  quadrantPointFill: '#93C5FD', quadrantPointTextFill: '#212529',
  quadrantXAxisTextFill: '#4B5563', quadrantYAxisTextFill: '#4B5563', quadrantTitleFill: '#212529',
  quadrantInternalBorderStrokeFill: '#E2E8F0', quadrantExternalBorderStrokeFill: '#D1D5DB',
  // —— git 图 ——
  git0: '#93C5FD', git1: '#86EFAC', git2: '#E9B08A', git3: '#C4B5FD',
  git4: '#F87171', git5: '#9CA3AF', git6: '#4B5563', git7: '#DBEAFE',
  commitLabelColor: '#212529', commitLabelBackground: '#F8FBFF',
  // —— xychart / 其它 ——
  xyChart: { backgroundColor: '#FFFFFF', titleColor: '#212529', xAxisLabelColor: '#4B5563', xAxisTitleColor: '#4B5563', xAxisTickColor: '#6B7280', xAxisLineColor: '#D1D5DB', yAxisLabelColor: '#4B5563', yAxisTitleColor: '#4B5563', yAxisTickColor: '#6B7280', yAxisLineColor: '#D1D5DB', plotBorderColor: '#E2E8F0' },
};

// 节点最小净距阈值：**按图型分级**。20px 是 flowchart 的口径，套到 block/kanban/mindmap
// 这类本来排版就紧的图型上纯属误报（实测 block-beta 净距 8px、kanban 5px 都被误拦）。
const GAP_MIN = {
  flowchart: 20, graph: 20,
  'stateDiagram-v2': 12, stateDiagram: 12, classDiagram: 12, erDiagram: 12, requirementDiagram: 12,
};
// 节点内标签「溢出节点框」检查只对「节点=矩形/多边形 + 文字」的图型有意义；
// mindmap 的节点形状与文字排布口径不同（实测 1px 级误差被判溢出），故跳过。
const SKIP_OVERFLOW = new Set(['mindmap']);

/** 从 mmd 源码里认图型（跳过 %%{init}%% 指令、注释与空行） */
function diagramType(mmd) {
  const clean = String(mmd).replace(/%%\{[\s\S]*?\}%%/g, '');
  for (const raw of clean.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('%%')) continue;
    const m = line.match(/^([A-Za-z][\w-]*)/);
    return m ? m[1] : 'unknown';
  }
  return 'unknown';
}

/** 图内是否自带 title（C4/gantt/journey/timeline/pie/quadrant/xychart/kanban 支持） */
function hasOwnTitle(mmd) {
  return /^\s*title\s+\S/m.test(String(mmd).replace(/%%\{[\s\S]*?\}%%/g, ''));
}

function parseArgs(argv) {
  const a = {};                       // 未出现的开关就是 undefined，别给 '' 默认值（会被当成路径）
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (!k.startsWith('--')) continue;
    const name = k.replace(/^--/, '');
    const next = argv[i + 1];
    if (next === undefined || next.startsWith('--')) { a[name] = true; }
    else { a[name] = next; i++; }
  }
  return a;
}

/** 扫 mmd 里几类「一定会在图上变成乱码/噪音」的写法，提前给提示（不是错误，不阻断渲染） */
function scanHints(mmd) {
  const hints = [];
  // 先把 %%{init}%% 与 %% 行注释去掉：注释里的东西不会渲染，不该产生提示
  const src = String(mmd).replace(/%%\{[\s\S]*?\}%%/g, '').replace(/^\s*%%.*$/gm, '');
  if (/&#\d+;|&#x[0-9A-Fa-f]+;/.test(src))
    hints.push('标签里出现了 HTML 风格数字实体（如 &#35;）：本渲染器用 htmlLabels:false，实体不会被解码，图上会**原样**显示成 &#35; —— 想写 # 直接写 # 即可');
  if (/(?:^|[^\w&])#\d+;/.test(src))
    hints.push('标签里出现了 Mermaid 实体码（如 #35;）：htmlLabels:false 下同样不解码，会原样显示 —— 想写 # 直接写 #');
  for (const line of src.split('\n')) {
    if (/^\s*(classDef|class|style|linkStyle|click)\b/.test(line)) continue;   // 这些行里的 #RRGGBB 是正常配色
    const m = line.match(/(?:\(|\[|\{)[^)\]}]*?(#[0-9A-Fa-f]{3,8})\b/);
    if (m) {
      hints.push('标签文字里混进了十六进制色号（' + m[1] + '）：配色请用 classDef / style，不要把色号写进文字');
      break;
    }
  }
  return hints;
}

/** 在浏览器里渲染 Mermaid 并做几何检查 */
async function renderMermaid(mmd, opts = {}) {
  const type = diagramType(mmd);
  const gapMin = GAP_MIN[type] === undefined ? null : GAP_MIN[type];
  const warnings = scanHints(mmd);
  for (const w of warnings) process.stderr.write('⚠️  ' + w + '\n');
  // 图内自带标题时不再注入（否则出现两个标题）
  let title = opts.title || '';
  if (title && hasOwnTitle(mmd)) {
    process.stderr.write(`⚠️  图内已含 title（${type}），忽略 --title，避免出现两个标题\n`);
    title = '';
  }
  // channel:'chromium' 明确要求完整 Chromium（headless shell 在部分机器未安装）
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
    const result = await page.evaluate(async ({ code, title, curve, type, gapMin, skipOverflow, softTheme, fontStack, bg }) => {
      /* global mermaid */
      const SVGNS = 'http://www.w3.org/2000/svg';
      // 规范里的 %%{init}%% 指令照旧保留在源码里；这里再把同一套参数设为**默认值**，
      // 保证即使某些版本对指令里的 flowchart 子项解析有差异，也不会退回 mermaid 默认布局。
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'loose',
        theme: 'base',
        htmlLabels: false,          // 顶层同样关掉（不同版本读的位置不一样）
        themeVariables: Object.assign({
          fontFamily: 'system-ui, -apple-system, "Noto Sans SC", "PingFang SC", sans-serif',
          fontSize: '14px',
        }, softTheme),
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
      // ⚠️ classDef 的类名 `root` 与 Mermaid 容器类 `.root` **撞名** —— Mermaid 为
      //    classDef root 生成的规则会命中容器内**所有 path**（包括边路径），于是边被强制填色。
      //    这里把这条规则从 SVG 的 <style> 里删掉。
      svgEl.querySelectorAll('style').forEach((stEl) => {
        stEl.textContent = stEl.textContent.replace(/#[\w-]+\s+\.root\s+path\s*\{[^}]*\}/g, '');
      });
      // 兜底：边路径一律不填充 + 边标签底色透明（双保险，用内联 !important）
      svgEl.querySelectorAll('path').forEach((pe) => {
        const cls = pe.getAttribute('class') || '';
        if (/flowchart-link|edge-thickness/.test(cls)) pe.style.setProperty('fill', 'none', 'important');
      });
      // ⚠️ 选择器里**不能**出现裸的 `rect.background`：Mermaid 的整图背景矩形用的就是这个 class，
      //    一起清掉会导致 SVG 没有白底 —— 在深色主题的站点/查看器里，深色文字 + 透明背景 = 整张图看不见。
      svgEl.querySelectorAll('.edgeLabel rect, .edgeLabel .background, .labelBkg').forEach((re) => {
        re.style.setProperty('fill', 'none', 'important');
        re.style.setProperty('opacity', '0', 'important');
      });
      const st = svgEl.querySelector('style');
      if (st) st.textContent += '\n' +
        // ① 边路径：classDef 的填充色会渗到 edge path 上 → 拐弯处出现实心色块，必须 fill:none
        '.edgePaths path,.flowchart-link,path.edge-thickness-normal,path.edge-thickness-thick{fill:none!important;}' +
        // ② 边标签底色矩形（无标签的边也会画）
        '.edgeLabel rect,.edgeLabel .background,.labelBkg,.edgeLabel foreignObject div{fill:none!important;opacity:0!important;background:transparent!important;}' +
        // ③ 箭头标记统一用线的颜色，避免残留主题色
        '.marker path,.marker polygon{fill:#6B7280!important;stroke:#6B7280!important;}';
      svgEl.setAttribute('xmlns', SVGNS);

      // ---- 标题（站点/端上直接显示 SVG，标题必须画进图里；规范里「标题不进 Mermaid」照旧遵守）
      //      ⚠️ 关键修复：以前注入标题时把 viewBox 强制改成 `0 0 W H+titleH`，**丢掉了原始原点**。
      //      而 Mermaid 给不少图型（时序图 -50,-10；architecture-beta -276,-65；kanban 90,-310）
      //      用的是负原点坐标系 —— 结果带标题的架构图被裁掉左边节点、看板直接变成空白。
      //      现在改为「按标题高度向上扩画布」，原点只按居中偏移量平移，永不裁内容。
      const vb = svgEl.viewBox.baseVal;
      const vbX = vb.x, vbY = vb.y, W = vb.width, H = vb.height;
      let canvasX = vbX, canvasY = vbY, canvasW = W, canvasH = H;
      if (title) {
        const titleH = 34;
        await document.fonts.ready;
        const g = document.createElementNS(SVGNS, 'g');
        while (svgEl.firstChild) g.appendChild(svgEl.firstChild);
        svgEl.appendChild(g);
        const t = document.createElementNS(SVGNS, 'text');
        t.setAttribute('x', '0'); t.setAttribute('y', '0');
        t.setAttribute('text-anchor', 'middle');
        t.setAttribute('font-family', fontStack);
        t.setAttribute('font-size', '16');
        t.setAttribute('font-weight', 'bold');
        t.setAttribute('fill', '#212529');
        t.setAttribute('id', 'fig-title');   // ⚠️ 必须给 id：htmlLabels=false 时节点标签也是 <text>
        t.textContent = title;
        svgEl.appendChild(t);
        const tw = (t.getComputedTextLength ? t.getComputedTextLength() : t.getBBox().width) || 0;
        const margin = 24;
        canvasW = Math.max(W, Math.ceil(tw + margin * 2));
        const dx = Math.round((canvasW - W) / 2);
        g.setAttribute('transform', `translate(${dx},0)`);
        canvasX = vbX - dx;                       // 向左扩，内容水平居中
        canvasY = vbY - titleH;                   // 向上扩出标题行
        canvasH = H + titleH;
        t.setAttribute('x', String(canvasX + canvasW / 2));
        t.setAttribute('y', String(canvasY + 22));
      }
      svgEl.setAttribute('viewBox', `${canvasX} ${canvasY} ${canvasW} ${canvasH}`);
      svgEl.setAttribute('width', canvasW);
      svgEl.setAttribute('height', canvasH);
      // 规范要求「背景纯白」：显式插一块白底（id 不是 class，不会被上面那套清理规则命中），
      // 这样图在深色主题站点里也正常。spec 里给 "background": false 可关闭（透明背景）。
      if (bg) {
        const bgRect = document.createElementNS(SVGNS, 'rect');
        bgRect.setAttribute('id', 'fig-background');
        bgRect.setAttribute('x', String(canvasX)); bgRect.setAttribute('y', String(canvasY));
        bgRect.setAttribute('width', String(canvasW)); bgRect.setAttribute('height', String(canvasH));
        bgRect.setAttribute('fill', '#FFFFFF');
        svgEl.insertBefore(bgRect, svgEl.firstChild);
      }

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
      if (!skipOverflow) {
        for (const n of nodes) {
          if (!n.labelBox) continue;
          const pad = 2;
          const inside = n.labelBox.x >= n.box.x - pad && n.labelBox.r <= n.box.r + pad &&
                         n.labelBox.y >= n.box.y - pad && n.labelBox.b2 <= n.box.b2 + pad;
          if (!inside) overflow.push({ node: n.txt, dxl: +(n.box.x - n.labelBox.x).toFixed(1), dxr: +(n.labelBox.r - n.box.r).toFixed(1), dyt: +(n.box.y - n.labelBox.y).toFixed(1), dyb: +(n.labelBox.b2 - n.box.b2).toFixed(1) });
        }
      }

      // ③ 节点间距（同层水平/垂直最小净距）——只有 gapMin 非 null 的图型才作为红线
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
        size: { w: Math.round(canvasW), h: Math.round(canvasH) },
        counts: { texts: textBoxes.length, nodes: nodes.length, edges: svgEl.querySelectorAll('.edgePath, path.flowchart-link').length },
        checks: {
          diagramType: type,
          gapMin,
          overlapText,
          overflow,
          outOfCanvas,
          nodeGap: { min: minGap === Infinity ? null : +minGap.toFixed(1), pair: tight },
        },
      };
    }, { code: mmd, title, curve: opts.curve || '', type, gapMin, skipOverflow: SKIP_OVERFLOW.has(type),
         softTheme: SOFT_THEME, fontStack: FONT_STACK, bg: opts.bg !== false });
    // 提示在 Node 侧算（要扫源码），挂到 checks 上一起回传
    result.checks.warnings = warnings;
    return result;
  } finally {
    await browser.close();
  }
}

/** 检查结果 → 是否全绿（gapMin 为 null 表示该图型不套间距红线） */
function checksPass(c) {
  return c.overlapText.length === 0 && c.overflow.length === 0 && c.outOfCanvas.length === 0 &&
         (c.gapMin === null || c.gapMin === undefined || c.nodeGap.min === null || c.nodeGap.min >= c.gapMin);
}

async function main() {
  const a = parseArgs(process.argv);
  if (!a.in) {
    console.error('用法：node render-mermaid.js --in fig.mmd --out fig.svg [--title 标题] [--curve basis] [--json 结果.json]');
    process.exit(2);
  }
  let mmd;
  try {
    mmd = fs.readFileSync(a.in, 'utf8');
  } catch (e) {
    console.error('❌ 读不到输入文件：' + a.in);
    process.exit(2);
  }
  let res;
  const bg = !(a.bg === '0' || a.bg === 'false');   // 白底默认开，--bg 0 关
  try {
    res = await renderMermaid(mmd, { title: typeof a.title === 'string' ? a.title : '',
                                     curve: typeof a.curve === 'string' ? a.curve : '', bg });
  } catch (e) {
    const msg = String((e && e.message) || e).split('\n')[0];
    console.error('❌ mermaid 渲染失败：' + msg);
    const st = String((e && e.stack) || '').split('\n').slice(1, 3).join('\n');
    if (st) console.error(st);
    process.exit(3);
  }
  const out = typeof a.out === 'string' ? a.out : '';
  if (out) { fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true }); fs.writeFileSync(out, res.svg); }
  const c = res.checks;
  const ok = checksPass(c);
  console.log(JSON.stringify({ out, size: res.size, counts: res.counts, diagramType: c.diagramType, pass: ok, checks: c }, null, 1));
  if (typeof a.json === 'string' && a.json) fs.writeFileSync(a.json, JSON.stringify(c, null, 1));
  process.exit(ok ? 0 : 1);   // 1 = 检查未过（SVG 已写出）；渲染失败在上面 exit(3)
}

module.exports = { renderMermaid, diagramType, checksPass };
if (require.main === module) main();

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
 *   4 = 图型不支持（例如 zenuml；会打印可替代的写法与骨架）
 *
 * 机器版版式检查（在浏览器里用 getBoundingClientRect 实测，全部同一坐标系）：
 *   · 文字重叠 overlapText ：两个文字 bbox 相交面积占比 > 12%
 *   · 文字溢出节点 overflow：节点内标签不在节点形状内（仅对 flowchart 类有意义）
 *   · 节点挤压 nodeGap    ：节点最小净距 < 该图型的阈值（**按图型分级**，非 flowchart 图型不套用 20px）
 *   · 越界 outOfCanvas    ：任何节点/文字超出画布 viewBox
 */
const fs = require('fs');
const path = require('path');

// 跨平台解析 Playwright（浏览器目录 + 模块位置）——逻辑**唯一一份**在 pw-env.js
const { applyBrowserDir, requirePlaywright } = require('./pw-env');
applyBrowserDir();
const { chromium } = requirePlaywright();
// 优先用**随 skill 内置**的 mermaid 运行时（skill 独立、无需 npm install）
const VENDOR = path.join(__dirname, 'vendor', 'mermaid.min.js');
const MERMAID_JS = fs.existsSync(VENDOR) ? VENDOR : require.resolve('mermaid/dist/mermaid.min.js');

const FONT_STACK = 'system-ui, -apple-system, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", Arial, sans-serif';

// ---------------------------------------------------------------------------
// 软色板主题：flowchart 靠 classDef 上色，但**时序图 / ER / 类图 / C4 / 甘特 / 饼图
// 等图型没有 classDef**，以前只能吃 Mermaid 默认主题色（米黄/亮蓝），与本 skill 的
// 软色板不一致。这里把同一套软色板注入 themeVariables，让 A 类风格统一。
// 注：图内自带的 %%{init}%% 指令会覆盖同名变量，所以已有自定义配色的 spec 不受影响。
//
// 色板**唯一来源是 style.py**：draw.py 会把 style.palette_payload() 写成 JSON 并用
// --palette 传进来，覆盖下面 SLOT 的默认值。SLOT 的默认值只在脱离 draw.py 单独调用本
// 渲染器时兜底 —— 两处各存一份色值必然漂移（改了一边另一边没改，A/B 配色就分裂）。
// ---------------------------------------------------------------------------
const SLOT = {
  // SOFT_COLORS
  // 这几个键与 palette.SOFT_COLORS 同义（**派生色**，不是论文淡色；淡色在 category/input/output/root）
  // —— 以前这里写成淡色，导致「脱离 draw.py 单独调用渲染器」与「走管线（--palette 覆盖）」配色不一致。
  blue: '#84D0EF', red: '#F87171', green: '#9DD1A2', purple: '#F59B9E',
  orange: '#FFC474', grey: '#9CA3AF', dark: '#4B5563',
  // FILL
  neutral: '#F8FBFF', root: '#FCE0E1', category: '#C2E8F7', leaf: '#F3F3F4',
  input: '#FFE2BB', output: '#CCE7CF', warning: '#F2F4C1', error: '#FECACA',
  // STROKE
  stroke_neutral: '#212529', stroke_root: '#212529', stroke_category: '#212529',
  stroke_leaf: '#212529', stroke_input: '#212529', stroke_output: '#212529',
  stroke_warning: '#212529', stroke_error: '#F87171',
  // INK
  ink_title: '#212529', ink_text: '#212529', ink_axis: '#4B5563', ink_tick: '#6B7280',
  // 中性色（与 palette.py 同源；管线经 --palette 覆盖）
  paper: '#FFFFFF', grid: '#F1F3F5', edge_soft: '#E2E8F0', axis_edge: '#D1D5DB',
};

/** 由 SLOT 生成主题（不内联色值，全部走 SLOT，便于被 --palette 覆盖） */
function buildSoftTheme() {
  return {
    primaryColor: SLOT.category, primaryBorderColor: SLOT.blue, primaryTextColor: SLOT.ink_text,
    secondaryColor: SLOT.leaf, tertiaryColor: SLOT.neutral,
    lineColor: SLOT.ink_tick, textColor: SLOT.ink_text, mainBkg: SLOT.category, nodeBorder: SLOT.blue,
    defaultLinkColor: SLOT.ink_tick, clusterBkg: SLOT.neutral, clusterBorder: SLOT.edge_soft,
    titleColor: SLOT.ink_text, edgeLabelBackground: 'transparent', labelBackground: 'transparent',
    background: '#FFFFFF',
    // —— 时序图 ——
    actorBkg: SLOT.category, actorBorder: SLOT.blue, actorTextColor: SLOT.ink_text, actorLineColor: SLOT.grey,
    signalColor: SLOT.dark, signalTextColor: SLOT.ink_text,
    labelBoxBkgColor: SLOT.warning, labelBoxBorderColor: SLOT.stroke_warning, labelTextColor: SLOT.ink_text,
    loopTextColor: SLOT.ink_text, noteBkgColor: SLOT.warning, noteBorderColor: SLOT.stroke_warning, noteTextColor: SLOT.ink_text,
    activationBkgColor: SLOT.purple, activationBorderColor: SLOT.blue, sequenceNumberColor: '#FFFFFF',
    // —— 类图 / 状态图 ——
    classText: SLOT.ink_text,
    fillType0: SLOT.category, fillType1: SLOT.leaf, fillType2: SLOT.warning, fillType3: SLOT.output,
    fillType4: SLOT.input, fillType5: SLOT.root, fillType6: SLOT.error, fillType7: SLOT.neutral,
    // —— ER 图 ——
    attributeBackgroundColorOdd: SLOT.neutral, attributeBackgroundColorEven: '#FFFFFF',
    // —— 甘特图 ——
    sectionBkgColor: SLOT.neutral, altSectionBkgColor: '#FFFFFF', sectionBkgColor2: SLOT.leaf,
    taskBkgColor: SLOT.blue, taskBorderColor: SLOT.blue, taskTextColor: SLOT.ink_text,
    taskTextOutsideColor: SLOT.ink_text, taskTextDarkColor: SLOT.ink_text,
    activeTaskBkgColor: SLOT.orange, activeTaskBorderColor: SLOT.orange,
    doneTaskBkgColor: SLOT.edge_soft, doneTaskBorderColor: SLOT.stroke_leaf,
    critBkgColor: SLOT.red, critBorderColor: SLOT.red, todayLineColor: SLOT.red, gridColor: SLOT.leaf,
    // —— 饼图 ——
    pie1: SLOT.blue, pie2: SLOT.green, pie3: SLOT.orange, pie4: SLOT.purple, pie5: SLOT.red,
    pie6: SLOT.grey, pie7: SLOT.dark, pie8: SLOT.category, pie9: SLOT.output, pie10: SLOT.warning,
    pie11: SLOT.error, pie12: SLOT.root,
    pieTitleTextColor: SLOT.ink_text, pieSectionTextColor: SLOT.ink_text, pieLegendTextColor: SLOT.ink_text,
    pieStrokeColor: '#FFFFFF', pieOuterStrokeColor: '#FFFFFF', pieOpacity: '0.9',
    // —— 四象限图 ——
    quadrant1Fill: SLOT.category, quadrant2Fill: SLOT.leaf, quadrant3Fill: SLOT.neutral, quadrant4Fill: SLOT.warning,
    quadrant1TextFill: SLOT.ink_text, quadrant2TextFill: SLOT.ink_text, quadrant3TextFill: SLOT.ink_text, quadrant4TextFill: SLOT.ink_text,
    quadrantPointFill: SLOT.blue, quadrantPointTextFill: SLOT.ink_text,
    quadrantXAxisTextFill: SLOT.dark, quadrantYAxisTextFill: SLOT.dark, quadrantTitleFill: SLOT.ink_text,
    quadrantInternalBorderStrokeFill: SLOT.edge_soft, quadrantExternalBorderStrokeFill: SLOT.axis_edge,
    // —— git 图 ——
    git0: SLOT.blue, git1: SLOT.green, git2: SLOT.orange, git3: SLOT.purple,
    git4: SLOT.red, git5: SLOT.grey, git6: SLOT.dark, git7: SLOT.category,
    commitLabelColor: SLOT.ink_text, commitLabelBackground: SLOT.neutral,
    // —— xychart / 其它 ——
    xyChart: { backgroundColor: SLOT.paper, titleColor: SLOT.ink_text, xAxisLabelColor: SLOT.dark, xAxisTitleColor: SLOT.dark, xAxisTickColor: SLOT.ink_tick, xAxisLineColor: '#D1D5DB', yAxisLabelColor: SLOT.dark, yAxisTitleColor: SLOT.dark, yAxisTickColor: SLOT.ink_tick, yAxisLineColor: '#D1D5DB', plotBorderColor: '#E2E8F0' },
  };
}

const SOFT_THEME = buildSoftTheme();

/** 用 draw.py 传来的色板覆盖 SLOT，并就地刷新 SOFT_THEME（色板唯一来源在 style.py） */
function applyPalette(palPath) {
  if (!palPath) return;
  let payload;
  try {
    payload = JSON.parse(fs.readFileSync(palPath, 'utf8'));
  } catch (e) {
    console.error('⚠️  读不到色板文件，回退内置默认值：' + palPath);
    return;
  }
  Object.assign(SLOT, payload);
  Object.assign(SOFT_THEME, buildSoftTheme());
}

// 节点最小净距阈值：**按图型分级**。20px 是 flowchart 的口径，套到 block/kanban/mindmap
// 这类本来排版就紧的图型上纯属误报（实测 block-beta 净距 8px、kanban 5px 都被误拦）。
const GAP_MIN = {
  flowchart: 20, graph: 20,
  'stateDiagram-v2': 12, stateDiagram: 12, classDiagram: 12, erDiagram: 12, requirementDiagram: 12,
};
// 节点内标签「溢出节点框」检查只对「节点=矩形/多边形 + 文字」的图型有意义；
// mindmap 的节点形状与文字排布口径不同（实测 1px 级误差被判溢出），故跳过。
const SKIP_OVERFLOW = new Set(['mindmap']);
// 文字重叠红线的按图型豁免：treemap-beta 的名称与数值是两条堆叠的 <text>，
// bbox 天然相接（实测 ratio≈0.13），属结构性误报；明细仍写在 checks.overlapText 里。
const SKIP_OVERLAP = new Set(['treemap-beta']);

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

// Mermaid 里存在、但**内置单文件 bundle 不含**或本渲染器不支持的图型：给出替代写法与骨架
const UNSUPPORTED = {
  zenuml: {
    why: 'ZenUML（内置的单文件 mermaid bundle 不含该图型）',
    use: 'sequenceDiagram',
    skeleton: 'sequenceDiagram\n  autonumber\n  participant C as 客户端\n  participant G as 网关\n  participant S as 订单服务\n  C->>G: submit(orderId)\n  activate G\n  G->>S: pay(orderId)\n  activate S\n  S-->>G: ok\n  deactivate S\n  G-->>C: accepted\n  deactivate G',
  },
};

// 版式检查没过时，按图型给一条可操作的改进建议（这些图型的自带布局本来就容易挤）
const LAYOUT_TIPS = {
  C4Context: 'C4 的自动布局容易把「[Software System] 描述」和关系标签叠在一起：缩短 description / 减少外部系统，或改用 flowchart+subgraph 复刻（TYPES.md 的 arch 分类里有骨架）',
  C4Container: '同上：C4 自动布局偏挤，建议缩短 description 或改用 flowchart+subgraph',
  gitGraph: 'gitGraph 的 commit 标签容易互相压：减少分支/提交数量，或给 mermaid 配置 rotateCommitLabel（本渲染器已默认开启）',
  journey: 'journey 的分段标题可能超出画布（已自动扩画布兜底）；段数过多时建议拆成两张',
  'radar-beta': 'radar-beta 的轴标签可能超出画布（已自动扩画布兜底）；指标过多时建议减少维度',
  'treemap-beta': 'treemap-beta 的叶子标签容易重叠：减少层级或改用 bar/pie 表达占比',
  'stateDiagram-v2': 'note 会作为独立 cluster 参与 dagre 布局：`note left/right of X` **都不保证落位**（实测 right of 也可能落在左侧），'
    + '并会用一条虚线折线连回原状态。想更紧凑：把 note 挂到链路末端的状态、缩短 note 文本，或改用转移标签（`A --> B: 说明`）',
  gantt: 'gantt 的 "today" 线画在"今天"：当样例日期与今天相差很远时它会落到坐标轴之外，'
    + '把日期设在当前时间附近可避免（渲染器已对这类离群元素做了过滤，不会再把画布撑大）',
};

/** 扫 mmd 里几类「一定会在图上变成乱码/噪音」的写法，提前给提示（不是错误，不阻断渲染） */
function scanHints(mmd) {
  const hints = [];
  // 先把 %%{init}%% 与 %% 行注释去掉：注释里的东西不会渲染，不该产生提示
  const src = String(mmd).replace(/%%\{[\s\S]*?\}%%/g, '').replace(/^\s*%%.*$/gm, '')
    .split('\n').filter((l) => !/^\s*(classDef|class|style|linkStyle|click)\b/.test(l)).join('\n');
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
  // 手写 <br/> 把标签切成多行：长短悬殊时节点会被撑成又高又窄，文字在框里左右悬空。
  // 成因是 htmlLabels:false —— Mermaid 只在**空格**处换行，所以英文标签本可交给自动换行，
  // 中文没有空格、必须手写 <br/>，但得断在词/短语边界并让各行长度接近。
  // 长度按「视觉宽度」估：CJK 等全角字符记 2，拉丁字符记 1。
  const visWidth = (s) => s.split('').reduce((n, c) => n + (c.charCodeAt(0) > 0x2E80 ? 2 : 1), 0);
  for (const line of src.split('\n')) {
    if (!/<br\s*\/?>/i.test(line)) continue;
    if (/^\s*(classDef|class|style|linkStyle|click)\b/.test(line)) continue;
    const m = line.match(/[(\[]\s*["']([\s\S]*?)["']\s*[)\]]/);
    if (!m) continue;
    const segs = m[1].split(/<br\s*\/?>/i).map((s) => s.replace(/<[^>]+>/g, '').trim()).filter(Boolean);
    if (segs.length < 4) continue;
    // 首行不参与「长短悬殊」判定：短首行当小标题是常见且合理的写法（如「混合 / 两路信号…」）
    const w = segs.slice(1).map(visWidth);
    const mx = Math.max.apply(null, w), mn = Math.min.apply(null, w);
    if (mx > 0 && mn < mx * 0.45) {
      hints.push('标签被 <br/> 切成 ' + segs.length + ' 行且长短悬殊（最短 ' + mn +
        ' / 最长 ' + mx + ' 视觉宽度）：节点会被撑成又高又窄、文字在框里左右悬空。' +
        '英文标签直接删掉 <br/> 交给 Mermaid 按空格自动换行即可；' +
        '中文没有空格必须手写，但要断在词/短语边界、并让各行长度接近');
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
    const result = await page.evaluate(async ({ code, title, curve, type, gapMin, skipOverflow, skipOverlap, softTheme, fontStack, bg, autofit }) => {
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
      // ⚠️ 必须在 mermaid.render **之前**等字体就绪：Mermaid 布局要测量文本宽度，
      //    字体没加载完就测，量到的宽度会偏；同一份 mmd 两次渲染的曲线控制点就会不同
      //    （几何看着一样，但 SVG 不是逐字节可复现，git diff 全是噪音）。
      await document.fonts.ready;
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
      let tw = 0;                              // 标题宽度：供后面「按可见内容居中」复用
      if (title) {
        const titleH = 34;
        await document.fonts.ready;
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
        tw = (t.getComputedTextLength ? t.getComputedTextLength() : t.getBBox().width) || 0;
        const margin = 24;
        canvasW = Math.max(W, Math.ceil(tw + margin * 2));
        const dx = Math.round((canvasW - W) / 2);
        // ⚠️ 居中只做一次：viewBox 原点左移 dx，内容自然落在画布中央（与纵向的处理方式一致）。
        // 以前这里**同时**给内容组加了 translate(dx)，两处叠加成 2dx —— 标题比图宽时
        // （很常见）内容会被整块推到画布最右边，左边留一大片空白。实测偏移量 = canvasW - W。
        canvasX = vbX - dx;
        canvasY = vbY - titleH;                   // 向上扩出标题行
        canvasH = H + titleH;
        t.setAttribute('x', String(canvasX + canvasW / 2));
        t.setAttribute('y', String(canvasY + 22));
      }
      svgEl.setAttribute('viewBox', `${canvasX} ${canvasY} ${canvasW} ${canvasH}`);
      svgEl.setAttribute('width', canvasW);
      svgEl.setAttribute('height', canvasH);

      // ---- 画布按**可见内容**重新居中 -------------------------------------------
      //  ⚠️ 不能直接信 Mermaid 的 viewBox：它的留白左右不对称（实测 stateDiagram-v2 左 42 / 右 7.5
      //     用户单位；ladder 曾出现左 20 / 右 231）——照着它居中，肉眼就是"内容偏一边"。
      //  这里量一次真实可见内容外框（屏幕坐标 → 用户单位），按内容居中重建画布：
      //  **只改 viewBox/宽高与标题位置，不动内容几何**，所以 diff 很小，也不影响负原点图型。
      {
        const r0 = svgEl.getBoundingClientRect();
        const scale = canvasW / Math.max(1, r0.width);
        // 离群过滤：以 **Mermaid 的 viewBox** 为参照（不是当前画布，避免自反馈）——
        // 完全落在「viewBox 外扩 50%」之外的单个元素不参与画布计算。实测 gantt 会把 "today"
        // 线画到 x≈57866（样例日期在 2026-01，而"今天"是 2026-10，超出轴范围），
        // 不过滤就会生成一张 57890px 宽的图。真正只轻微越界的图型（journey/radar/treemap）
        // 仍在这个范围内，照旧会被纳入。
        const limL = vbX - W * 0.5, limR = vbX + W * 1.5;
        const limT = vbY - H * 0.5, limB = vbY + H * 1.5;
        let cx0 = Infinity, cy0 = Infinity, cx1 = -Infinity, cy1 = -Infinity, seen = 0;
        // ⚠️ 遍历**所有**元素再按「是否真的绘制」过滤：以前用标签白名单，漏了 `<use>`
        //    （gitGraph 的虚线边框就是 <use> 引用的），导致那一侧被算漏、内容贴边。
        svgEl.querySelectorAll('*')
          .forEach((el) => {
            const t0 = el.tagName.toLowerCase();
            if (el.id === 'fig-background' || el.id === 'fig-title') return;
            if (['style', 'defs', 'title', 'desc', 'metadata', 'marker', 'clippath', 'lineargradient',
                 'radialgradient', 'stop', 'filter', 'pattern', 'mask', 'symbol'].includes(t0)) return;
            if (el.closest('defs') || el.closest('marker') || el.closest('clipPath')) return;
            // 容器（<g>/<svg>）不单独量：它们的盒子会把内部**不可见的占位元素**一起算进来
            // （实测 stateDiagram-v2 的 note-cluster 就这样把画布撑宽 35px）。子元素会各自被量到。
            if (['g', 'svg', 'a', 'switch', 'symbol'].includes(t0)) return;
            const cs = getComputedStyle(el);
            if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return;
            // 只统计**真的会绘制**的元素：Mermaid 会给边标签留 `fill:none;stroke:none` 的空矩形
            // （实测 stateDiagram-v2 里有一块 8..228 的空 rect），把它算进外框就会让画布凭空变宽、
            // 内容看着偏一边。文字/图片类不看 fill/stroke。
            const tag = el.tagName.toLowerCase();
            const paints = (tag === 'text' || tag === 'image' || tag === 'foreignobject')
              || cs.fill !== 'none' || cs.stroke !== 'none';
            if (!paints) return;
            if (parseFloat(cs.fillOpacity) === 0 && parseFloat(cs.strokeOpacity) === 0) return;
            const b = el.getBoundingClientRect();
            // 按描边宽度补偿：`<line>` 这种水平/垂直线段的 bbox 厚度是 0，直接按零尺寸丢掉会把
            // 它整条漏掉（实测 gitGraph 的虚线边框就是这么丢的，导致内容贴右边缘）。
            const sw = parseFloat(cs.strokeWidth) || 0;
            const pad = (tag === 'text' || tag === 'image' || tag === 'foreignobject') ? 0 : Math.max(0, sw / 2) + 0.5;
            // 只丢「点对象」（两个维度都≈0）：Mermaid 会留 0×0 的空 tspan / 占位 rect（实测
            // stateDiagram-v2 里就有，会把画布往左撑 40+px）。而水平/垂直线段只有一个维度为 0，必须保留。
            if (b.width <= 0.5 && b.height <= 0.5) return;
            const uL = canvasX + (b.left - r0.left) * scale - pad;
            const uR = canvasX + (b.right - r0.left) * scale + pad;
            const uT = canvasY + (b.top - r0.top) * scale - pad;
            const uB = canvasY + (b.bottom - r0.top) * scale + pad;
            if (uR < limL || uL > limR || uB < limT || uT > limB) return;   // 离群元素
            cx0 = Math.min(cx0, uL); cx1 = Math.max(cx1, uR);
            cy0 = Math.min(cy0, uT); cy1 = Math.max(cy1, uB);
            seen++;
          });
        if (seen > 0 && cx1 > cx0 && cy1 > cy0) {
          const M = 10, titleH = title ? 34 : 0;
          const contentW = cx1 - cx0, contentH = cy1 - cy0;
          const newW = Math.ceil(Math.max(contentW, tw || 0) + M * 2);
          const newH = Math.ceil(contentH + titleH + M * 2);
          canvasX = cx0 - (newW - contentW) / 2;                       // 内容水平居中
          canvasY = cy0 - titleH - M;                                  // 标题占一行 + 上边距
          canvasW = newW; canvasH = newH;
          svgEl.setAttribute('viewBox', `${canvasX} ${canvasY} ${canvasW} ${canvasH}`);
          svgEl.setAttribute('width', canvasW);
          svgEl.setAttribute('height', canvasH);
          const tEl = svgEl.querySelector('#fig-title');
          if (tEl) {
            tEl.setAttribute('x', String(Math.round(canvasX + canvasW / 2)));
            tEl.setAttribute('y', String(Math.round(canvasY + titleH / 2 + 6)));
          }
        }
      }
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
        if (n.box.w <= 0.5 && n.box.h <= 0.5) continue;     // 未布局/占位节点不算越界
        if (n.box.x < canvasRect.x - 1 || n.box.y < canvasRect.y - 1 || n.box.r > canvasRect.r + 1 || n.box.b2 > canvasRect.b2 + 1)
          outOfCanvas.push({ el: n.txt, box: { x: +n.box.x.toFixed(1), y: +n.box.y.toFixed(1), r: +n.box.r.toFixed(1), b: +n.box.b2.toFixed(1) } });
      }
      for (const t of textBoxes) {
        // ⚠️ 与 B 类检查同一口径：**未布局的零尺寸文本对象**（journey / treemap 里实测都是 0×0）
        //    不是真的"跑到画布外"，不能报越界 —— 否则会误判成红线，还会让自动扩画布白忙。
        if (t.box.w <= 0.5 || t.box.h <= 0.5) continue;
        if (t.txt.length && (t.box.x < canvasRect.x - 1 || t.box.r > canvasRect.r + 1 || t.box.y < canvasRect.y - 1 || t.box.b2 > canvasRect.b2 + 1))
          outOfCanvas.push({ el: '文字:' + t.txt, box: { x: +t.box.x.toFixed(1), y: +t.box.y.toFixed(1), r: +t.box.r.toFixed(1), b: +t.box.b2.toFixed(1) } });
      }

      // ⑤ 自动扩画布：Mermaid 有些图型（journey / radar-beta / treemap-beta …）会把自己的一部分画到
      //    viewBox 之外 —— 内容会被裁掉。这里按实测 bbox 向外扩画布，保证内容完整，并把「原本越界了多少」
      //    如实记进 checks.canvasFitted（不是静默修好，也不是假装没发生）。
      let canvasFitted = null;
      if (autofit && outOfCanvas.length) {
        const scale = canvasW / Math.max(1, canvasRect.w);
        const degX = canvasRect.w * 1.5, degY = canvasRect.h * 1.5;   // 忽略退化对象（3D 刻度那种）
        let dl = 0, dr = 0, dt = 0, db = 0;
        for (const b of nodes.map(n => n.box).concat(textBoxes.map(t => t.box))) {
          if (!b || b.w <= 0 || b.h <= 0) continue;
          if (b.x + b.w < canvasRect.x - degX || b.x > canvasRect.r + degX) continue;
          if (b.b2 < canvasRect.y - degY || b.y > canvasRect.b2 + degY) continue;
          dl = Math.max(dl, canvasRect.x - b.x);
          dr = Math.max(dr, b.r - canvasRect.r);
          dt = Math.max(dt, canvasRect.y - b.y);
          db = Math.max(db, b.b2 - canvasRect.b2);
        }
        const M = 6;
        dl = dl > 0 ? (dl + M) * scale : 0; dr = dr > 0 ? (dr + M) * scale : 0;
        dt = dt > 0 ? (dt + M) * scale : 0; db = db > 0 ? (db + M) * scale : 0;
        if (dl || dr || dt || db) {
          canvasX -= dl; canvasW += dl + dr;
          canvasY -= dt; canvasH += dt + db;
          svgEl.setAttribute('viewBox', `${canvasX} ${canvasY} ${canvasW} ${canvasH}`);
          svgEl.setAttribute('width', canvasW);
          svgEl.setAttribute('height', canvasH);
          const bgEl = svgEl.querySelector('#fig-background');
          if (bgEl) {
            bgEl.setAttribute('x', canvasX); bgEl.setAttribute('y', canvasY);
            bgEl.setAttribute('width', canvasW); bgEl.setAttribute('height', canvasH);
          }
          const tEl = svgEl.querySelector('#fig-title');
          if (tEl) tEl.setAttribute('x', String(canvasX + canvasW / 2));
          canvasFitted = { left: +dl.toFixed(1), right: +dr.toFixed(1), top: +dt.toFixed(1), bottom: +db.toFixed(1) };
        }
      }

      return {
        svg: new XMLSerializer().serializeToString(svgEl),
        size: { w: Math.round(canvasW), h: Math.round(canvasH) },
        counts: { texts: textBoxes.length, nodes: nodes.length, edges: svgEl.querySelectorAll('.edgePath, path.flowchart-link').length },
        checks: {
          diagramType: type,
          gapMin,
          // 免重叠红线的图型把清单置空，但原始明细另存 overlapTextExempt —— **不隐藏数据**，
          // 只是不再当红线（draw.py 与 checksPass 都按 overlapText 长度判定）。
          // ⚠️ skipOverlap 必须由外部传参：page.evaluate 的回调跑在浏览器上下文，
          //    取不到 Node 作用域里的 SKIP_OVERLAP（踩过：直接引用导致 A 类全部渲染失败）。
          overlapText: skipOverlap ? [] : overlapText,
          overlapTextExempt: skipOverlap && overlapText.length ? overlapText : undefined,
          overflow,
          outOfCanvas,          // 扩画布**之前**的越界清单（保留原始信号）
          canvasFitted,         // 非 null 表示已自动扩过画布，值为四边扩了多少（user unit）
          nodeGap: { min: minGap === Infinity ? null : +minGap.toFixed(1), pair: tight },
        },
      };
    }, { code: mmd, title, curve: opts.curve || '', type, gapMin, skipOverflow: SKIP_OVERFLOW.has(type),
         skipOverlap: SKIP_OVERLAP.has(type),
         softTheme: SOFT_THEME, fontStack: FONT_STACK, bg: opts.bg !== false, autofit: opts.autofit !== false });
    // 提示在 Node 侧算（要扫源码），挂到 checks 上一起回传
    result.checks.warnings = warnings;
    return result;
  } finally {
    await browser.close();
  }
}

/** 检查结果 → 是否全绿（gapMin 为 null 表示该图型不套间距红线） */
function checksPass(c) {
  // 自动扩过画布 → 越界内容已经全部可见，不再算红线（原始越界数量仍在 checks.outOfCanvas 里可查）
  const outBad = c.canvasFitted ? 0 : c.outOfCanvas.length;
  return c.overlapText.length === 0 && c.overflow.length === 0 && outBad === 0 &&
         (c.gapMin === null || c.gapMin === undefined || c.nodeGap.min === null || c.nodeGap.min >= c.gapMin);
}

async function main() {
  const a = parseArgs(process.argv);
  if (!a.in) {
    console.error('用法：node render-mermaid.js --in fig.mmd --out fig.svg [--title 标题] [--curve basis] [--json 结果.json] [--palette 色板.json]');
    process.exit(2);
  }
  // 色板覆盖必须在渲染前完成：draw.py 传的是 style.palette_payload()
  applyPalette(typeof a.palette === 'string' ? a.palette : '');
  let mmd;
  try {
    mmd = fs.readFileSync(a.in, 'utf8');
  } catch (e) {
    console.error('❌ 读不到输入文件：' + a.in);
    process.exit(2);
  }
  let res;
  const bg = !(a.bg === '0' || a.bg === 'false');   // 白底默认开，--bg 0 关
  const autofit = !(a.autofit === '0' || a.autofit === 'false');
  try {
    res = await renderMermaid(mmd, { title: typeof a.title === 'string' ? a.title : '',
                                     curve: typeof a.curve === 'string' ? a.curve : '', bg, autofit });
  } catch (e) {
    const t = diagramType(mmd);
    if (UNSUPPORTED[t]) {
      console.error('❌ 不支持该图型：' + UNSUPPORTED[t].why);
      console.error('   → 建议改用 `' + UNSUPPORTED[t].use + '`，骨架如下（可直接放进 spec 的 mmd）：');
      console.error(UNSUPPORTED[t].skeleton.split('\n').map(l => '     ' + l).join('\n'));
      process.exit(4);            // 4 = 图型不支持（与渲染失败 3 区分开）
    }
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
  if (!ok && LAYOUT_TIPS[c.diagramType]) {
    c.tip = LAYOUT_TIPS[c.diagramType];
    console.error('💡 ' + c.tip);
  }
  console.log(JSON.stringify({ out, size: res.size, counts: res.counts, diagramType: c.diagramType, pass: ok, checks: c }, null, 1));
  if (typeof a.json === 'string' && a.json) fs.writeFileSync(a.json, JSON.stringify(c, null, 1));
  process.exit(ok ? 0 : 1);   // 1 = 检查未过（SVG 已写出）；渲染失败在上面 exit(3)
}

module.exports = { renderMermaid, diagramType, checksPass };
if (require.main === module) main();

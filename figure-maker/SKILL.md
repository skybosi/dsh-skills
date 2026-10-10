---
name: figure-maker
description: Use when the user wants to draw or update a figure — flowcharts, sequence/architecture diagrams, or data/statistical/scientific charts (说「画张图」「画个流程图」「画个时序图」「改成柱状图」「出一张热力图」「画个生存曲线」). 91 catalog entries (24 Mermaid structural families + 67 Matplotlib data types incl. research/bio), fixed soft palette, machine layout self-checks, multi-format output (svg/png/webp/pdf). Fully standalone — depends on nothing but this skill directory.
whenToUse: 用户要**画图/生成图表**（结构图、流程图、时序图、架构图、数据图、统计图、论文图）时说「画一张」「来张柱状图/热力图/流程图/时序图」「把这个数据画出来」时，先加载本 skill。仅生成 AI 生图提示词的需求请用 gen-image / article-cover-designer。
---

# figure-maker · 确定性的矢量图绘制

把**描述**变成**可复现的矢量图**。核心是**确定性**（同一 spec 出同一张图）与**版式兜底**（机器检查文字重叠、越界）。
**独立性**：只依赖本目录（`scripts/` + 内置 mermaid 运行时），在任意工作目录都能用。

## 分工（重要，别搞反）

- **你（模型）负责**：听懂要画什么 → **选型**（属于哪个场景、哪个图型）→ 写 `params`/`mmd` → **看图验收**。
- **脚本负责**：确定性出图 + 版式自检 + 格式转换。**不要手写 SVG，也不要自己算坐标。**

## 第一步永远是选型：先分类，再路由

图型有 91 个条目（24 个 Mermaid 图族 + 67 种数据图），**不要靠记忆挑**，按下面三步走：

| 情况 | 动作 |
|---|---|
| 用户**点名**了图型或场景（"画个时序图""要热力图"） | 直接 `--example <图型>` 拿骨架，或抄 `specs/b__<图型>.json` |
| 用户**只给描述**（"把这段流程画出来""多组实验的波动"） | `--recommend "<描述>"` → 取第 1 个候选；第 2、3 个作为备选 |
| 描述跨了好几个场景 / 你拿不准 | `--list`（14 个分类）扫一眼，再 `--recommend` 收窄 |
| 需要程序化选型 | `--catalog --json`（含分类、关键词、参数键、示例 spec 路径） |

```bash
S=<本 skill 目录>/scripts/draw.py
python3 $S --recommend "画个接口调用的先后顺序"   # → sequenceDiagram，并打印可直接保存的 spec
python3 $S --list trend                        # 只列「趋势与曲线」这一类
python3 $S --example line_band                 # 该图型的真实骨架（取自 specs/）
```

**14 个场景分类**：`flow` 流程与决策 · `interaction` 交互与时序 · `state` 状态与生命周期 ·
`model` 数据与领域模型 · `arch` 架构与上下文 · `plan` 计划与协作 · `compare` 对比与构成 ·
`trend` 趋势与曲线 · `dist` 分布与统计 · `relate` 相关与拟合 · `field` 场与矩阵 ·
`eval` 评估与性能 · `math` 优化与几何 · `bio` 生医与统计推断。
完整目录（含每个图型的参数键与样例）见 **[TYPES.md](./TYPES.md)**。

> 选型心法：**先定类（结构图是 A 类，数据图是 B 类）→ 再定场景分类 → 再定图型**。
> 结构/关系一类优先考虑 Mermaid（A 类）里有没有现成图族（时序/状态/ER/类图/甘特/看板…），
> 只有"数据 → 图形"的定量表达才用 B 类。

## 支持的图型（按类）

| 类 | 数量 | 渲染器 | spec 里给什么 | 产物格式 |
|---|---|---|---|---|
| **A 类 · 结构/关系图** | 24 个 Mermaid 图族（`type` 填 6 个入口名中任意一个） | Mermaid（内置运行时） | `mmd` 源码 | svg / png / webp |
| **B 类 · 数据/统计/科研图** | 67 种 | Matplotlib | `params` | svg / png / webp / pdf / eps / ps / jpeg / tiff |

A 类不限于 24 个图族 —— 凡 Mermaid v11 支持的图型都能画（`flowchart` `sequenceDiagram` `stateDiagram-v2`
`classDiagram` `erDiagram` `architecture-beta` `C4Context` `gantt` `kanban` `journey` `requirementDiagram`
`timeline` `mindmap` `gitGraph` `block-beta` `packet-beta` `pie` `quadrantChart` `xychart-beta` `sankey-beta`
`treemap-beta` `radar-beta` …）。**明确不可用**：`zenuml`（内置 bundle 不含该图型）、泳道图（Mermaid 没有，用 `subgraph` 近似）。

## 快速开始（独立，零配置）

```bash
python3 $S --doctor                               # 自检依赖（缺什么/怎么装）
python3 $S --list                                 # 按场景分类列出全部图型
python3 $S --recommend "一句话描述"                 # 选型 + 输出可跑骨架
python3 $S --example grouped_bar > spec.json      # 打真实骨架 → 改参数即可
python3 $S spec.json                              # 出图（默认 out/<id>.svg）
python3 $S spec.json -o out/fig.png               # 格式由**扩展名**决定：svg/png/webp/pdf/eps/jpeg/tiff
python3 $S spec.json --check                      # 版式检查当红线（不过关 → 退出码 1）
python3 $S --batch specs/                         # 批量：把目录下所有 *.json 都画出来
```

**验收习惯**：出图后**一定看图**（`read_image` 或图片查看器）。机器检查只保证"不重叠/不越界"，
**语义对不对（数据、标签、图型选得合不合适）只有看图才知道**。

## 最终产出（只有两样）

| 产物 | 说明 |
|---|---|
| **图** | `svg` / `png` / `webp` / `pdf` / …（由输出扩展名或 `--format` 决定） |
| **元信息** | **与图同目录、去掉扩展名** → `out/fig.webp` ⇒ `out/fig.meta.json`；内容：`id` `type` `format` `output` `bytes` `width_px/height_px` `layout{…}` `spec`（原始描述，可复现）`generated_at` `figure_maker` |

```jsonc
// out/fig.meta.json
{
  "id": "demo-bar", "type": "bar", "format": "webp", "bytes": 29494,
  "width_px": 800.0, "height_px": 450.0, "generated_at": "2026-10-10T00:12:34",
  "figure_maker": "figure-maker/1.1",
  "layout": { "overlap": 0, "outOfCanvas": 0, "overflow": 0, "nodeGap": 28, "gapMin": 20, "passed": true },
  "spec": { /* 原始 spec 原样回填 → 任何时候都能重画出一模一样的图 */ }
}
```

## spec 格式

**B 类 · 数据图**（选图型 + 给数据；**参数键用 `--example`/TYPES.md 查，不要猜**）

```json
{
  "id": "demo-bar", "type": "bar", "output": "out/demo-bar.svg",
  "width_in": 8.0, "height_in": 4.5,
  "params": { "title": "各方案吞吐对比", "labels": ["基线", "优化 A", "优化 B"],
              "values": [12.4, 18.1, 25.7], "ylabel": "tokens/s" }
}
```
> `bar` 的类目键是 **`labels`**（`categories` 也兼容）；分组柱用 `categories` + `groups[{label, values}]`。

**A 类 · 结构图**（给 Mermaid 源码，skill 不替你编图）

```json
{
  "id": "demo-flow", "type": "flow", "output": "out/demo-flow.svg",
  "title": "数据处理流程",
  "mmd": "flowchart TD\n  A[输入] --> B{质量合格?}\n  B -->|是| C[训练]\n  B -->|否| D[清洗]\n  D --> B"
}
```

常用可选字段：`width_in`（默认 8.0）、`height_in`（默认 4.5）、`output`（省略则 `out/<id>.svg`）、
`curve`（Mermaid 曲线：basis 默认 / linear / step…）、`scale`（A 类转位图的清晰度倍数，默认 2）、
`background`（**仅 A 类**：默认 `true` 给 SVG 加纯白底；`false` = 透明底，用于必须叠在深色底上的场合）。
嵌套参数（`panels[]` `series[]` `groups[]` `curves[]` `bins[]` `items[]` …）见 [docs/SPEC-REFERENCE.md](./docs/SPEC-REFERENCE.md)。

## 输出格式

| 格式 | 适用 | 说明 |
|---|---|---|
| **`svg`**（默认） | 文档 / 站点 / 任意缩放，**首选** | 矢量；B 类文字转曲（不依赖对方字体） |
| **`png`** | 微信 / 幻灯片 / 不支持 SVG 的场景 | 位图，B 类 `dpi` 默认 300；A 类默认 2× 清晰度 |
| **`webp`** | 网页、体积敏感 | 内部走 PNG → Pillow（matplotlib 原生不支持 webp），实测比 PNG 小 30–40% |
| **`pdf`** | 印刷 / 投稿 | B 类矢量；A 类不支持（会明确报错，不会静默写错文件） |
| `eps` `ps` `jpeg` `tiff` | 其它下游 | 仅 B 类 |

## 风格规范（保持一致才好看）

- **软色板**：`style.py` 的 `SOFT_COLORS`（蓝/绿/橙/紫/红/灰 + 深灰）；**≤4 个语义色**，同义同色；顺序色图由 `_soft_cmap` 从同一色板生成
- **无阴影、无渐变**；去掉上/右边框；网格是**极浅虚线**；背景纯白
- **字体**：系统无衬线（`PingFang SC` / `Noto Sans SC` / `Microsoft YaHei`）；字号下限 9px
- **A 类**：`htmlLabels: false`（部分渲染环境不支持 foreignObject）、曲线默认平滑 `basis`、
  软色板已注入 `themeVariables`（时序图/ER/类图/甘特/饼图也有统一配色）；`classDef` **不要命名为 `root`**（与 Mermaid 容器类撞名会让所有路径被填充，渲染器已额外兜底清除）
- **A 类 SVG 自带白底**（`<rect id="fig-background">`）：规范要求背景纯白，也避免图被贴到深色主题页面时"整张看不见"
- **3D**：可用（`surface3d` / `scatter3d`）但**不是首选** —— 定量表达优先用 `contourf`（填充等高线）等二维画法

## 版式红线（机器检查）

| 指标 | 阈值 | 怎么查 |
|---|---|---|
| 文字重叠 | **0** | `--check`（像素空间比较；已过滤 1×1 占位文本、轴外刻度、隐藏轴、3D 退化对象） |
| 文字越界（出画布） | **0** | 同上；右缘 x 与 y 都要看 |
| A 类节点间距 | **按图型分级**：flowchart ≥20px；状态/类/ER/需求图 ≥12px；其它图型不套用 | 渲染器内部判定，结果写进 meta 的 `layout.gapMin/nodeGap` |
| 长标签折行 | 无"标点开头/结尾"的丑折行 | 目视；中文按视觉宽度折行 |

**检查语义**：默认**只告警不拦截**（结果写进 `meta.layout`，stdout 打印「通过 / 有告警」）；
加 `--check` 才当红线（不过关退出码 1）。A 类渲染器的退出码约定：`0` 全绿 / `1` 已出图但版式不过 / `2` 用法错误 / `3` 渲染失败。

## 常见的坑（都踩过，照着避）

1. **`width_in` 可能被自动放大**：柱子多/类目长/子图多时脚本会加宽画布防重叠（`out/*.meta.json` 里的 `width_px` 才是实际值）；要精确尺寸就用 `bar` 之外的横向表达或减少类目
2. **A 类图内已有 `title` 时不要再传 spec 的 `title`**（C4/gantt/pie/quadrant/xychart/kanban 自带 title 语法）—— 渲染器会用图内标题并打印忽略提示，避免出现两个标题
3. **带标题时画布会向上扩一行**（不再裁切内容；时序图/architecture-beta/kanban 这类负原点坐标系已修好）
4. **数值标签**：先按符号分（正数在上、负数在下）并夹在值域内，否则负值/大值会跑到画布外
5. **长类目名/长系列名**：值标注放进柱内（白字）或只标每类最大值；图例移到留白区；实在放不下就换图型
6. **多子图**：画布宽度随列数放大（每子图建议 ≥2.9 英寸），否则中文标题必被挤或越右缘
7. **`annotate(...)` + `arrowprops` 在双轴（twin axis）上 bbox 会退化成上万像素** → 用 `text` + `scatter` 代替（已修）
8. **公式标签**：图里不要塞 LaTeX 源码，先转成可读文本（`$p$` → `p`、`\times` → `×`、下标转 Unicode）再折行
9. **标签里不要写 `#` 开头的"实体码/色号"**：`htmlLabels:false` 下 Mermaid 的实体码（`#35;`）与 HTML 数字实体（`&#35;`）
   **都不会被解码**，图上会原样显示成 `&#35;` / `&#EF4444` 这种噪音（真实踩过：ladder 样例把配色色号写进了标签）。
   想写 `#` 就直接写 `#`；要配色请用 `classDef` / `style`。渲染器会检测并给出提示（写进 `meta.warnings`）
10. **量纲不同别共用一根轴**：用 `twin_axis` 或 `multi_subplot`；跨轴比"交点"没有意义（`twin_axis` 的 `mark_crossing` 默认关闭）

## 依赖与安装

| 用途 | 需要 | 安装 |
|---|---|---|
| **自检** | — | `python3 scripts/draw.py --doctor` |
| B 类（数据图） | Python 3.8+ + `matplotlib` `numpy` | `python3 -m venv .venv && .venv/bin/pip install matplotlib numpy` |
| `webp` 输出 | `Pillow`（含 libwebp） | `.venv/bin/pip install Pillow` |
| A 类（结构图） | Node.js + Playwright Chromium | `npm i -g playwright && npx playwright install chromium`，并 `export PLAYWRIGHT_BROWSERS_PATH=<浏览器目录>` |
| A 类运行时（mermaid） | **已内置** v11.17.2，无需安装 | `scripts/vendor/mermaid.min.js` |

> 只用 B 类时**完全不需要 Node**；只用 A 类时**不需要 Python 绘图库**。

## 维护（改图型/改文档的标准动作）

| 想做什么 | 动作 |
|---|---|
| 加/改图型 | 在 `scripts/drawers.py` 加 `draw_<name>()` 并登记到 `DRAWERS`；在 `scripts/catalog.py` 的 `B_TYPES` 里补一行（分类/场景/关键词/示例）|
| 加 A 类图族 | 在 `catalog.py` 的 `A_FAMILIES` 里加一行（含起手骨架，用 `--recommend` 直接给用户） |
| 重生成样例 | `python3 scripts/build_examples.py`（写 `docs/examples/*.svg`） |
| 重生成文档 | `python3 scripts/build_docs.py`（写 `TYPES.md` + 刷新 `README.md` 画廊） |
| 回归自测 | `python3 scripts/draw.py --batch specs/ --check`（73 个示例 spec 应全绿） |

## 当前状态

- ✅ 91 个条目全部可用：24 个 Mermaid 图族 + 67 种数据图（含科研/生医/3D）
- ✅ 选型层：`--recommend` / `--list <分类>` / `--catalog --json` / `--example`
- ✅ 73 个示例 spec + 73 张样例图（`specs/` 与 `docs/examples/`），`--batch --check` 全绿
- ✅ A 类：标题不再裁切、退出码分级（渲染失败 vs 版式不过）、按图型分级阈值、软色板注入主题
- ✅ B 类：`heatmap` 色阶按数据取值域、`twin_axis` 标签可配、`heatmap_panels` 面板标签生效、`bar` 兼容 `categories`
- ⚠️ 未做：聚类热图的 dendrogram、泳道图、ZenUML（见 TYPES.md「不支持 / 有替代写法」）

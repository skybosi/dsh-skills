---
name: figure-maker
description: Use when the user wants to draw or update a figure — flowcharts, architecture diagrams, or data charts (说「画张图」「画个流程图」「改成柱状图」「出一张热力图」). 53 figure types (6 Mermaid structural + 45 Matplotlib data), fixed soft palette, machine layout self-checks, multi-format output (svg/png/webp/pdf). Fully standalone — depends on nothing but this skill directory.
whenToUse: 用户要**画图/生成图表**（流程图、结构图、数据图）时说「画一张」「来张柱状图/热力图/流程图」「把这个数据画出来」时，先加载本 skill。仅生成 AI 生图提示词的需求请用 gen-image / article-cover-designer。
---

# figure-maker · 确定性的矢量图绘制

把**描述**变成**可复现的矢量图**：流程图 / 结构图 / 数据图。核心是**确定性**（同一 spec 出同一张图）
与**版式兜底**（机器检查文字重叠、越界），而不是让模型去写 SVG 或算坐标。

**独立性**：本 skill 只依赖自己目录里的脚本 + 内置运行时，**不依赖任何仓库、路径或项目约定**。
在任意工作目录都能使用。

## 分工（重要，别搞反）

- **你（模型）负责"描述 → spec"**：听懂要画什么 → 选图型 → 写 `params`（标题、标签、数据、轴）或 `mmd`（结构图源码）→ **看图验收**。
- **脚本负责"确定性出图 + 自检"**：渲染、布局测量、格式转换。**不要手写 SVG，也不要自己算坐标。**

## 支持的图型（53 种）

详见 [TYPES.md](./TYPES.md)（每种图型的用法/常用参数键）。

| 类 | 种数 | 渲染器 | 怎么描述 | 例子 |
|---|---|---|---|---|
| **A 结构图** | 6 | Mermaid（内置运行时） | spec 里给 `mmd`（Mermaid 源码） | `flow` `graph` `tree` `nn_diagram` `ladder` `timeline` |
| **B 数据图** | 45 | Matplotlib | spec 里给 `params` | `bar` `grouped_bar` `multi_bar` `multi_curve` `loglog` `matrix` `heatmap` `heatmap_panels` `scatter_fit/classes/boundary/panels/rich` `roc` `learning_curve` `boxplot` `kde` `pie` `normal_dist` `cdf` `pmf_pdf` `hist_fit` `vector2d` `function_curve` `tangent_secant` `limit` `differential` `gradient_descent` `contour_quiver` `optimizer_paths` `multi_panel_gd` `regularization_path` `roofline` `elbow` `area_line` `stacked_bar` `twin_axis` `multi_subplot` `scatter_matrix` `tensor_blocks` `tensor_cube_panels` `matrix_mul_panels` … |
| **3D 图型** | — | ❌ **不支持** | 会被明确拒绝 | `surface3d` `multi_normal` → 改用分面等高线 / 多子图 |

## 快速开始（独立，零配置）

```bash
S=<本 skill 目录>/scripts/draw.py          # 例如 ~/.dsh/skills/figure-maker/scripts/draw.py

python3 $S --doctor                               # 自检依赖（缺什么/怎么装）
python3 $S --list                                 # 列出全部图型
python3 $S --example grouped_bar > spec.json      # 生成该图型的示例 spec → 改参数即可
python3 $S spec.json                              # 出图（默认 out/<id>.svg）
python3 $S spec.json -o out/fig.png               # 格式由**扩展名**决定：svg/png/webp/pdf/eps/jpeg/tiff
python3 $S spec.json --format webp                # 也可显式指定格式
python3 $S spec.json --check                      # 出图 + 版式检查（重叠/越界不过关 → 退出码 1）
python3 $S --batch specs/                         # 批量：把目录下所有 *.json 都画出来
```

**验收习惯**：出图后**一定看图**（图片查看器或 `read_image`）。机器检查只能保证不重叠/不越界，
**语义对不对（数据、标签、图型选得合不合适）只有看图才知道**。

## 最终产出（只有两样）

**图** + **元信息**。没有第三种产物 —— 不生成项目文件、不碰任何构建/发布流程。

| 产物 | 说明 |
|---|---|
| **图** | `svg` / `png` / `webp` / `pdf` / …（由输出扩展名或 `--format` 决定） |
| **元信息** | **与图同目录、去掉扩展名** → `out/fig.webp` ⇒ `out/fig.meta.json`；内容：`id` `type` `format` `output` `bytes` `width_px/height_px`（A 类）`layout{overlap,outOfCanvas,passed}` `spec`（原始描述，可复现）`generated_at` `figure_maker` 版本 |

```jsonc
// out/fig.meta.json（示例：与图同目录）
{
  "id": "demo-bar", "type": "bar", "format": "webp",
  "output": "/abs/path/out/fig.webp", "bytes": 29494, "width_px": 800.0, "height_px": 450.0,
  "generated_at": "2026-10-10T00:12:34", "figure_maker": "figure-maker/1.0",
  "layout": { "overlap": 0, "outOfCanvas": 0, "passed": true },
  "spec": { /* 原始 spec，原样回填 → 任何时候都能重画出一模一样的图 */ }
}
```

## spec 格式

**B 类 · 数据图**（选图型 + 给数据）

```json
{
  "id": "demo-bar",
  "type": "bar",
  "output": "out/demo-bar.svg",
  "width_in": 8.0,
  "height_in": 4.5,
  "params": {
    "title": "各方案吞吐对比",
    "categories": ["基线", "优化 A", "优化 B"],
    "values": [12.4, 18.1, 25.7],
    "ylabel": "tokens/s"
  }
}
```

**A 类 · 结构图**（给 Mermaid 源码，skill 不替你编图）

```json
{
  "id": "demo-flow",
  "type": "flow",
  "output": "out/demo-flow.svg",
  "title": "数据处理流程",
  "mmd": "flowchart TD\n  A[输入] --> B{质量合格?}\n  B -->|是| C[训练]\n  B -->|否| D[清洗]\n  D --> B\n  C --> E[部署]"
}
```

常用可选字段：`width_in`（默认 8.0）、`height_in`（默认 4.5）、`output`（省略则 `out/<id>.svg`）。
各图型的 `params` 键见 **[docs/SPEC-REFERENCE.md](./docs/SPEC-REFERENCE.md)**（按图型查字段 + 可复制骨架），
选型与频次参考见 [TYPES.md](./TYPES.md)；不确定时先 `--example <type>` 打一份骨架。

## 输出格式（可指定）

| 格式 | 适用 | 说明 |
|---|---|---|
| **`svg`**（默认） | 文档 / 站点 / 任意缩放，**首选** | 矢量、文字转曲（不依赖对方字体） |
| **`png`** | 微信 / 幻灯片 / 不支持 SVG 的场景 | 位图，`dpi` 默认 300 |
| **`webp`** | 网页、体积敏感 | 内部走 **PNG → Pillow**（matplotlib 原生不支持 webp），实测**比 PNG 小 30–40%** |
| **`pdf`** | 印刷 / 投稿 | 矢量 |
| `eps` `ps` `jpeg` `tiff` | 其它下游 | 支持 |
| **多格式一次出** | 一份内容两种用途 | `from style import save_as; save_as(fig, 'out/fig', ('svg','png','webp'))` |

**两类都支持 `svg` / `png` / `webp`**（B 类另支持 `pdf`/`eps`/`jpeg`/`tiff`）：格式 = 输出文件的扩展名，或 `--format`。
A 类转位图由 skill 自带的 `scripts/svg-to-raster.js`（Playwright 截图，默认 2× 清晰度）完成 ✓；
A 类给别的格式（如 `pdf`）会**明确报错**，不会静默写错文件。

## 风格规范（保持一致才好看）

- **软色板**：`style.py` 的 `SOFT_COLORS`（蓝/绿/橙/紫/红/灰）；**≤4 个语义色**，同义同色
- **无 3D、无阴影、无渐变**；去掉上/右边框；网格是**极浅虚线**；背景纯白
- **字体**：系统无衬线（`PingFang SC` / `Noto Sans SC` / `Microsoft YaHei`）；字号下限 9px
- **A 类（Mermaid）**：`htmlLabels: false`（部分渲染环境不支持 foreignObject）、平滑曲线
  `curve: basis`、`classDef` **不要命名为 `root`**（与 Mermaid 容器类撞名会让所有路径被填充）

## 版式红线（机器检查，应全绿）

| 指标 | 阈值 | 怎么查 |
|---|---|---|
| 文字重叠 | **0** | `--check`（像素空间比较，已过滤 1×1 占位文本 / 轴外刻度 / 隐藏轴） |
| 文字越界（出画布） | **0** | 同上；注意**右缘 x** 与 y 都要看（只看 y 会误判成"假阳性"） |
| A 类节点间距 | 建议 ≥20px | **已接入 `--check`**（读 `render-mermaid.js --json` 的结果）＋出图后目视 |
| 长标签折行 | 无"标点开头/结尾"的丑折行 | 目视；中文按**视觉宽度**折行（CJK 约 14px/字，ASCII 约 7.6px/字符） |

## 常见的坑（都踩过，照着避）

1. **长类目名/长系列名**：值标注放不进柱上方 → 放进柱内（白字）或**只标每类最大值**；图例移到轴下方；
   实在放不下就换图型（竖柱 → 横向 `barh`）
2. **多子图**：画布宽度要随列数放大（每子图建议 ≥2.9 英寸），否则中文标题必被挤或越右缘
3. **`annotate(...)` 的 bbox 在双轴（twin axis）上会退化成上万像素** → 误报越界；用 `text` + `scatter` 代替
4. **Mermaid**：`%%{init}%%` 里的 `flowchart.curve` 不生效，必须在 `mermaid.initialize()` 里设默认值
5. **公式标签**：图里不要塞 LaTeX 源码，先转成可读文本（`$p$` → `p`、`\times` → `×`、下标转 Unicode）再折行
6. **数值标签**：先按符号分（正数在上、负数在下）并夹在值域内，否则负值/大值会跑到画布外
7. **量纲不同别共用一根轴**：用 `twin_axis` 或 `multi_subplot`

## 依赖与安装

| 用途 | 需要 | 安装 |
|---|---|---|
| **自检** | — | `python3 scripts/draw.py --doctor` |
| B 类（数据图） | Python 3.8+ + `matplotlib` `numpy` | `python3 -m venv .venv && .venv/bin/pip install matplotlib numpy` |
| `webp` 输出 | `Pillow`（含 libwebp，多数发行版自带） | `.venv/bin/pip install Pillow` |
| A 类（结构图） | Node.js + Playwright Chromium | `npm i -g playwright && npx playwright install chromium`，并 `export PLAYWRIGHT_BROWSERS_PATH=<浏览器目录>` |
| A 类运行时（mermaid） | **已内置**，无需安装 | `scripts/vendor/mermaid.min.js` 随 skill 提供 |

> 只用 B 类时**完全不需要 Node**；只用 A 类时**不需要 Python 绘图库**。

## 本 skill 的来源

从一个**真实内容生产管线**抽象而来：那份管线用同一套风格与检查产出过 **1,015 张**教学插图
（约 57% 结构图 + 43% 数据图）。这里是把它**去项目化**后的独立版本 —— 图型清单、风格规范、
版式红线与踩坑记录都来自那批图的实测经验，但**不依赖那个管线本身**。

## 当前状态（如实标注）

- ✅ 独立入口 `draw.py`：`--list` / `--example` / 出图 / `--format` / `--check` / `--batch`
- ✅ 实测：`bar`、`grouped_bar` → svg / png / **webp** / pdf 四种格式（文件头逐一校验 ✓）；`flow`（A 类，内置 mermaid）→ SVG ✓
- ✅ 版式检查**真的会拦**：构造拥挤图 → `--check` 退出码 **1** ✓
- ✅ 51 种图型样例图 + `docs/EXAMPLES.md`（每种一张 SVG + 可复现 spec）
- ✅ 3D 图型（`surface3d` / `multi_normal`）**明确拒绝**并给替代建议
- ⏳ 待补：`specs/` 目录下的全量示例文件（暂可用 `--example <type>` 即时生成）
- ✅ A 类也能直出位图：`svg` / `png` / `webp`（`svg-to-raster.js`，2× 清晰度；webp 比 png 小约 37%）
- ✅ A 类的布局检查已接入 `--check`（与 B 类同一条退出码约定）

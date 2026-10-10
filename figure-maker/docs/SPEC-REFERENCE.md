# spec 参考：顶层字段 · 骨架 · 嵌套参数

> 每个图型的**参数键**（由 `drawers.py` 源码自动抽取）见 [TYPES.md](../TYPES.md)；
> 本文件讲"所有图型共用的写法"和**嵌套结构**。不确定就先 `python3 scripts/draw.py --example <图型>`。

## 1. 通用顶层字段

| 字段 | 必需 | 说明 |
|---|---|---|
| `id` | 建议 | 标识；缺省时输出名用 `fig` |
| `type` | **必需** | 图型名（B 类见 TYPES.md；A 类填 `flow`/`graph`/`tree`/`nn_diagram`/`ladder`/`timeline` 任一） |
| `output` | 可选 | 输出路径（缺省 `out/<id>.svg`）；**扩展名决定格式** |
| `width_in` / `height_in` | 可选 | 画布尺寸（默认 8.0 × 4.5 英寸）。⚠️ 类目多/柱子多/子图多时脚本会**自动加宽**，实际值看 `meta.json` 的 `width_px` |
| `params` | B 类必需 | 数据与标签 |
| `mmd` | A 类必需 | Mermaid 源码（`type` 填任一 A 类名即可） |
| `title` | A 类可选 | 图标题（B 类标题写在 `params.title`）。⚠️ 图内自带 `title` 时会忽略这个字段 |
| `curve` | A 类可选 | Mermaid 曲线：`basis`（默认）/ `linear` / `step` / `monotoneX`… |
| `scale` | A 类可选 | 转位图的清晰度倍数（默认 2） |
| `background` | A 类可选 | 默认 `true`：给 SVG 插入纯白底（`<rect id="fig-background">`），避免贴到深色主题页面时看不见；`false` = 透明底 |

## 2. 两个最小可跑骨架

**B 类 · 数据图**

```json
{
  "id": "demo-bar", "type": "bar", "output": "out/demo-bar.svg",
  "width_in": 8.0, "height_in": 4.5,
  "params": { "title": "各方案吞吐对比", "labels": ["基线", "优化 A", "优化 B"],
              "values": [12.4, 18.1, 25.7], "ylabel": "tokens/s" }
}
```

**A 类 · 结构图**（内容由你写的 `mmd` 决定）

```json
{
  "id": "demo-flow", "type": "flow", "output": "out/demo-flow.svg",
  "title": "数据处理流程",
  "mmd": "flowchart TD\n  A[输入] --> B{质量合格?}\n  B -->|是| C[训练]\n  B -->|否| D[清洗]\n  D --> B"
}
```

运行：`python3 scripts/draw.py spec.json --check` → 得到 **图** + `<同名>.meta.json`。

## 3. 通用 `params` 约定（所有 B 类）

| 键 | 含义 |
|---|---|
| `title` / `xlabel` / `ylabel` / `zlabel` | 标题与轴标签（缺省空字符串） |
| `color` | 软色板键名：`blue` `green` `orange` `purple` `red` `grey` `dark`（也接受 `#RRGGBB`） |
| `logx` / `logy` / `log` | 对数轴开关 |
| `grid` | `false` 关网格 |
| `colorbar` / `colorbar_label` | 色条开关与标签 |
| `annot` / `annot_fmt` | 数值标注开关与格式（如 `"%.2f"`） |
| `vmin` / `vmax` / `cmap` | 热力图/场图的色阶范围与色图（`blue` `warm` `green` `grey` `diverging`） |
| `metrics_loc` | 指标框位置：`upper left` / `upper right` / `lower left` / `lower right` |

> 随机性一律固定种子：`violin`/`box_jitter`/`scatter_panels` 的抖动点用 `default_rng(7)`，**同一 spec 永远出同一张图**。

## 4. 嵌套结构速查（写数据的地方）

| 结构 | 用在哪 | 字段 |
|---|---|---|
| `series[]` | 多曲线/多组：`line_band` `ecdf` `radar` `kde` `multi_curve` `loglog` | `label` · `mean`/`y`/`values`/`seeds`（多次实验，自动算均值±std）· `std`/`lo`/`hi` · `color` · `fill` |
| `groups[]` | 分组数据：`errorbar` `violin` `box_jitter` `km` `scatter3d` `fit_comparison` `boxplot` | `label` · `values`/`data` · `errors`（误差棒）· `times`+`events`（生存）· `x`/`y`/`z`（3D）· `color` |
| `categories`/`labels` + `values` | `bar` `pie` `waterfall` 类目轴 | `labels`（`categories` 兼容）· `values[]` |
| `panels[]` | 多面板：`panels` `multi_bar` `multi_subplot` `heatmap_panels` `scatter_panels` `scatter_matrix` `fit_comparison` `scatter_boundary` `multi_panel_gd` | `kind`（`panels` 专用：`line`/`bar`/`scatter`/`area`）· `title` · `x`/`y` · `values`/`labels` · `series[]` · `data` · `x_min`/`x_max` · `func` |
| `curves[]` | 函数/曲线：`multi_curve` `loglog` `kde` | `label` · `func`（表达式）或 `x`/`y` · `x_min`/`x_max` · `color` · `mean`/`std`/`weight`（kde） |
| `items[]` | 行式数据：`waterfall`（`label`+`value`）· `forest`（`label`+`estimate`+`lo`+`hi`） | 见上 |
| `bins[]` | `calibration` | `conf` · `acc` · `count`（也接受 `conf[]`/`acc[]`/`counts[]`） |
| `lanes[]` · `steps[]` · `edges[]` | 泳道图：`swimlane` | `lanes[{id, label, color?}]` · `steps[{id, lane, label, col?, color?}]`（同列并行用 `col` 指定）· `edges[["a","b"]]` · `direction`（`LR` 泳道横排 / `TD` 竖排）· `step_width` / `row_height` |
| `layers[]` · `layer_labels[]` | 神经网络结构：`nn_single`（神经元级，含跨层连线）· `nn_twin` 的 `left{}` / `right{}`（每个各带 `layers` / `layer_labels` / `title`） | `layers: [4, 6, 8, 6, 3]`（每层神经元数）· `layer_labels: ["输入层", "隐藏层 1", …]` |
| `blocks[]` · `edges[]` · `rails[]` · `frames[]` | 通用块图 / 分层架构图：`block_diagram`（模型架构、系统分层、数据管道同用一套） | `blocks[{id, row, col, span?, dx?, label, shape?, role?, h?, size?, label_side?}]` · `edges[{from, to, label?, arrows?, style?, from_side?, to_side?, spread?}]` · `rails[{side, left/right, from?, to, offset?}]`（跳连 / 残差这类绕行通道）· `frames[{col, rows, label?, label_side?}]`（分组框 + 侧标签，如 N×） |
| `folded[]` / `stacks[]` | `flamegraph` | `"a;b;c 12"` 或嵌套 `{name, value, children[]}` |
| `band{}` / `summary{}` | `fit_band`（`x`/`y`/`lo`/`hi`）· `forest`（`estimate`/`lo`/`hi`） | 见上 |
| `points[]` | `roofline`（`intensity`/`flops`/`label`）· `scatter_boundary`（`[x, y, 组别]`） | 见上 |
| `vectors[]` / `paths[]` / `classes[]` / `centers[]` | `vector2d` · `optimizer_paths` · `scatter_classes` | `x`/`y`/`label`/`color`/`lr` |
| 3D 专用 | `surface3d` `scatter3d` | `func`（`X`/`Y` 表达式）· `data[][]` · `view[elev, azim]` · `zoom` · `wireframe` |

表达式里可用的函数/常量（白名单，安全求值）：`x` `X` `Y` `np` `log` `log2` `log10` `exp` `sqrt` `abs` `pow`
`sin` `cos` `tan` `arcsin` `arccos` `arctan` `sinh` `cosh` `tanh` `sign` `floor` `ceil` `minimum` `maximum`
`where` `clip` `linspace` `deg2rad` `rad2deg` `sum` `mean` `sigmoid` `relu` `step` `erf` `gaussian` `pi` `e`。

## 5. 逐图型参数键

见 [TYPES.md](../TYPES.md)（每个图型一行：场景 · 关键词 · 参数键 · 示例 spec 路径）。
`参数键` 一列由源码自动抽取，**不会和实现漂移**。

## 6. 方案模板（`specs/templates/`）

写技术方案文档时，不必从零写 spec —— 这里放了三份**完整的真实方案图**，直接 `--example` 取出来改：

| 模板 | 内容 | 取用 |
|---|---|---|
| `tech-flow` | 订单履约主流程：6 个子域、20+ 节点、异常与补偿闭环（`flowchart TD` + `classDef` 语义分类） | `python3 scripts/draw.py --example tech-flow > spec.json` |
| `tech-arch` | 订单中台技术架构：客户端 / 接入 / 应用服务 / 中间件 / 存储 / 外部依赖 六层，含跨层数据流与异步链路 | `--example tech-arch` |
| `tech-swimlane` | 订单履约跨系统职责：用户 / 订单 / 库存 / 支付 / 履约 5 泳道、12 步（B 类 `swimlane`） | `--example tech-swimlane` |
| `two_tower` | 双塔检索模型：两列并行编码 → 跨列汇总（`block_diagram` 的 `span` 跨列块） | `--example two_tower` |
| `service_layers` | 订单系统分层架构：同步链路 + 异步链路 + 跨列调用 | `--example service_layers` |

> 模板是**普通 spec**，`--batch specs/` 不会扫到它们（在子目录里），样例画廊也仍是 98 张；
> 出图：`python3 scripts/draw.py spec.json --check`。⚠️ TD 方向的复杂流程图会很高（3000+ px），
> 放进方案文档建议改 `flowchart LR` 或按子域拆成两张。

## 7. 检查与元信息

- 默认：出图 + 版式检查（**不拦截**），结果写进 `meta.layout`，stdout 打印「通过 / 有告警」
- `--check`：把检查当红线，不过关退出码 1
- `meta.layout` 字段：`overlap`（文字重叠数）· `outOfCanvas`（越界数）· `overflow`（A 类：文字溢出节点框）·
  `nodeGap`/`gapMin`（A 类节点最小净距与该图型阈值）· `diagramType`（A 类识别到的 Mermaid 图族）· `passed`

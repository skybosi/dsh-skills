# figure-maker（独立 skill）

把**描述**变成**确定性的矢量图**：流程图 / 结构图 / 数据图。
**独立**：只依赖本目录（`scripts/` + 内置 mermaid 运行时），不依赖任何仓库或项目。

## 能力一览

- 支持 **51 种图型**：**6 种 A 类结构图**（Mermaid）+ **45 种 B 类数据图**（Matplotlib）
- 输出格式：**`svg`（默认）/ `png` / `webp`（比 PNG 小 30–40%）** —— 两类图都支持；B 类另支持 `pdf`/`eps`/`jpeg`/`tiff`
- 产物只有两样：**图** + **同目录的元信息**（`fig.meta.json`：类型/格式/尺寸/版式检查/原始 spec）
- 版式兜底：出图即做机器检查（文字重叠 0、越界 0），不过关退出码 1
- 3D 图型（`surface3d` / `multi_normal`）**明确拒绝**并给二维替代建议
- A 类不限于 6 种：**凡 Mermaid 支持的图型都能画**（状态机、时序图、类图、ER、甘特…，见 [TYPES.md](TYPES.md)）

## 快速开始

```bash
S=~/.dsh/skills/figure-maker/scripts/draw.py
python3 $S --doctor                            # 先自检依赖（缺什么会告诉你）
python3 $S --list                              # 列出全部图型
python3 $S --example grouped_bar > spec.json    # 生成示例 spec
python3 $S spec.json -o out/fig.webp            # 出图（格式由扩展名决定）
python3 $S spec.json --check                    # 版式检查（不过关退出码 1）
python3 $S --batch specs/                       # 批量出图
```

## 全部样例（51 种，每种一张，均可一键复现）

> 每张样例都由同名 spec **原样生成**：`python3 scripts/draw.py specs/<文件名> -o out/fig.svg`

| # | 类 | 图型 | 说明 |
|---|---|---|---|
| 1 | A | [`flow`](#flow) | Why finetune: pretraining builds the base, f |
| 2 | A | [`graph`](#graph) | 三大推荐范式：基于内容 / 协同过滤 / 混合 |
| 3 | A | [`ladder`](#ladder) | 运算符优先级（从上到下递减） |
| 4 | A | [`nn_diagram`](#nn_diagram) | MLP 三层全连接网络结构 |
| 5 | A | [`timeline`](#timeline) | 六章学习链路总览 |
| 6 | A | [`tree`](#tree) | Finetuning taxonomy: by scope and by objecti |
| 7 | B | [`area_line`](#area_line) | 相位旋转：SDR 掉到负值 |
| 8 | B | [`bar`](#bar) | Trainable parameter ratio by LoRA rank r |
| 9 | B | [`boxplot`](#boxplot) | 四个班级成绩分布（箱线图） |
| 10 | B | [`cdf`](#cdf) | 累积分布函数 F(x) = P(X ≤ x) |
| 11 | B | [`contour_quiver`](#contour_quiver) | 梯度指向函数上升最快的方向，负梯度是下降方向 |
| 12 | B | [`differential`](#differential) | 微分 dy 与增量 Delta y——线性近似 |
| 13 | B | [`elbow`](#elbow) | 肘部法则：K 与惯性（inertia） |
| 14 | B | [`fit_comparison`](#fit_comparison) | 欠拟合 / 恰到好处 / 过拟合三连对比 |
| 15 | B | [`function_curve`](#function_curve) | Finetuning vs Prompting trade-off curve |
| 16 | B | [`gradient_descent`](#gradient_descent) | 梯度下降：沿负梯度方向逐步逼近最低点 |
| 17 | B | [`grouped_bar`](#grouped_bar) | HyDE 的收益与风险同源 |
| 18 | B | [`heatmap`](#heatmap) | 反事实归因：准确率 0.950 |
| 19 | B | [`heatmap_panels`](#heatmap_panels) | 三种注意力热力图：编码器自注意力 / 解码器因果自注意力 / 交叉注意力 |
| 20 | B | [`hist_fit`](#hist_fit) | 2000 个身高样本的密度直方图 + 理论正态曲线 |
| 21 | B | [`kde`](#kde) | 双峰分布的核密度估计（300×N(0,1) + 200×N(3,1.2)） |
| 22 | B | [`learning_curve`](#learning_curve) | 序列反转任务训练 Loss 曲线 |
| 23 | B | [`limit`](#limit) | 函数值随 x 逼近某点而趋于极限 |
| 24 | B | [`loglog`](#loglog) | 每候选代价：三档差 8 个数量级 |
| 25 | B | [`matrix`](#matrix) | Instruction data formats: field structure an |
| 26 | B | [`matrix_mul_panels`](#matrix_mul_panels) | @ 矩阵乘（行×列点积） vs * 逐元素乘（形状不匹配 → 报错） |
| 27 | B | [`multi_bar`](#multi_bar) | 重叠：覆盖率触顶后成本继续翻倍 |
| 28 | B | [`multi_curve`](#multi_curve) | Precision@K 与 Recall@K 权衡曲线 |
| 29 | B | [`multi_panel_gd`](#multi_panel_gd) | 不同学习率下的梯度下降轨迹 |
| 30 | B | [`multi_subplot`](#multi_subplot) | 平稳序列与随机游走对比 |
| 31 | B | [`nn_twin`](#nn_twin) | 单层感知机 vs 多层神经网络（含隐藏层） |
| 32 | B | [`normal_dist`](#normal_dist) | NF4 quantile points vs standard normal distr |
| 33 | B | [`optimizer_paths`](#optimizer_paths) | 优化器下降轨迹对比：SGD → Adam 在狭长山谷中的表现 |
| 34 | B | [`pie`](#pie) | 编程语言使用占比 |
| 35 | B | [`pmf_pdf`](#pmf_pdf) | PMF（离散，柱高之和=1） vs PDF（连续，面积=1） |
| 36 | B | [`regularization_path`](#regularization_path) | Ridge vs Lasso 系数收缩对比 |
| 37 | B | [`roc`](#roc) | 输入过滤是 ROC 上的一个点（示意） |
| 38 | B | [`roofline`](#roofline) | Roofline 性能模型 (H100 FP16) |
| 39 | B | [`scatter_boundary`](#scatter_boundary) | 线性可分 vs 线性不可分（XOR 问题） |
| 40 | B | [`scatter_classes`](#scatter_classes) | 网格搜索示意 |
| 41 | B | [`scatter_fit`](#scatter_fit) | 最小二乘拟合：使数据点到直线的竖直距离平方和最小 |
| 42 | B | [`scatter_matrix`](#scatter_matrix) | 协方差与相关性：正相关、负相关、不相关 |
| 43 | B | [`scatter_panels`](#scatter_panels) | K-means 迭代：① 随机初始化 → ② 按最近中心分配 → ③ 更新中心到簇均值 |
| 44 | B | [`scatter_rich`](#scatter_rich) | 散点图：颜色=年龄、大小=体重偏离 60kg 的程度 |
| 45 | B | [`stacked_bar`](#stacked_bar) | 权重每减半，KV 容量翻倍 |
| 46 | B | [`tangent_secant`](#tangent_secant) | 割线逼近切线——导数即切线斜率 |
| 47 | B | [`tensor_blocks`](#tensor_blocks) | 0~3 维张量：标量 / 向量 / 矩阵 / 三维张量 |
| 48 | B | [`tensor_cube_panels`](#tensor_cube_panels) | 多变量输入：三维张量（批量×时间步×特征）与「通道混合 vs 通道独立」 |
| 49 | B | [`twin_axis`](#twin_axis) | 免费 batch 区：柱=吞吐，线=TPOT |
| 50 | B | [`vector2d`](#vector2d) | 余弦相似度 vs 皮尔逊相关系数（二维空间对比） |
| 51 | B | [`venn2`](#venn2) | 两路失手的重叠决定混合的上限 |

---

## A 类 · 结构图（Mermaid，6 种）

<a id="flow"></a>
**[`flow`](docs/examples/flow.svg)** — Why finetune: pretraining builds the base, finetuning adds domain expertise

![flow](docs/examples/flow.svg)

<sub>spec：<code>specs/a__flow.json</code></sub>

<a id="graph"></a>
**[`graph`](docs/examples/graph.svg)** — 三大推荐范式：基于内容 / 协同过滤 / 混合

![graph](docs/examples/graph.svg)

<sub>spec：<code>specs/a__graph.json</code></sub>

<a id="ladder"></a>
**[`ladder`](docs/examples/ladder.svg)** — 运算符优先级（从上到下递减）

![ladder](docs/examples/ladder.svg)

<sub>spec：<code>specs/a__ladder.json</code></sub>

<a id="nn_diagram"></a>
**[`nn_diagram`](docs/examples/nn_diagram.svg)** — MLP 三层全连接网络结构

![nn_diagram](docs/examples/nn_diagram.svg)

<sub>spec：<code>specs/a__nn_diagram.json</code></sub>

<a id="timeline"></a>
**[`timeline`](docs/examples/timeline.svg)** — 六章学习链路总览

![timeline](docs/examples/timeline.svg)

<sub>spec：<code>specs/a__timeline.json</code></sub>

<a id="tree"></a>
**[`tree`](docs/examples/tree.svg)** — Finetuning taxonomy: by scope and by objective

![tree](docs/examples/tree.svg)

<sub>spec：<code>specs/a__tree.json</code></sub>

---

## B 类 · 数据图（Matplotlib，45 种）

<a id="area_line"></a>
**[`area_line`](docs/examples/area_line.svg)** — 相位旋转：SDR 掉到负值

![area_line](docs/examples/area_line.svg)

<sub>spec：<code>specs/b__area_line.json</code></sub>

<a id="bar"></a>
**[`bar`](docs/examples/bar.svg)** — Trainable parameter ratio by LoRA rank r

![bar](docs/examples/bar.svg)

<sub>spec：<code>specs/b__bar.json</code></sub>

<a id="boxplot"></a>
**[`boxplot`](docs/examples/boxplot.svg)** — 四个班级成绩分布（箱线图）

![boxplot](docs/examples/boxplot.svg)

<sub>spec：<code>specs/b__boxplot.json</code></sub>

<a id="cdf"></a>
**[`cdf`](docs/examples/cdf.svg)** — 累积分布函数 F(x) = P(X ≤ x)

![cdf](docs/examples/cdf.svg)

<sub>spec：<code>specs/b__cdf.json</code></sub>

<a id="contour_quiver"></a>
**[`contour_quiver`](docs/examples/contour_quiver.svg)** — 梯度指向函数上升最快的方向，负梯度是下降方向

![contour_quiver](docs/examples/contour_quiver.svg)

<sub>spec：<code>specs/b__contour_quiver.json</code></sub>

<a id="differential"></a>
**[`differential`](docs/examples/differential.svg)** — 微分 dy 与增量 Delta y——线性近似

![differential](docs/examples/differential.svg)

<sub>spec：<code>specs/b__differential.json</code></sub>

<a id="elbow"></a>
**[`elbow`](docs/examples/elbow.svg)** — 肘部法则：K 与惯性（inertia）

![elbow](docs/examples/elbow.svg)

<sub>spec：<code>specs/b__elbow.json</code></sub>

<a id="fit_comparison"></a>
**[`fit_comparison`](docs/examples/fit_comparison.svg)** — 欠拟合 / 恰到好处 / 过拟合三连对比

![fit_comparison](docs/examples/fit_comparison.svg)

<sub>spec：<code>specs/b__fit_comparison.json</code></sub>

<a id="function_curve"></a>
**[`function_curve`](docs/examples/function_curve.svg)** — Finetuning vs Prompting trade-off curve

![function_curve](docs/examples/function_curve.svg)

<sub>spec：<code>specs/b__function_curve.json</code></sub>

<a id="gradient_descent"></a>
**[`gradient_descent`](docs/examples/gradient_descent.svg)** — 梯度下降：沿负梯度方向逐步逼近最低点

![gradient_descent](docs/examples/gradient_descent.svg)

<sub>spec：<code>specs/b__gradient_descent.json</code></sub>

<a id="grouped_bar"></a>
**[`grouped_bar`](docs/examples/grouped_bar.svg)** — HyDE 的收益与风险同源

![grouped_bar](docs/examples/grouped_bar.svg)

<sub>spec：<code>specs/b__grouped_bar.json</code></sub>

<a id="heatmap"></a>
**[`heatmap`](docs/examples/heatmap.svg)** — 反事实归因：准确率 0.950

![heatmap](docs/examples/heatmap.svg)

<sub>spec：<code>specs/b__heatmap.json</code></sub>

<a id="heatmap_panels"></a>
**[`heatmap_panels`](docs/examples/heatmap_panels.svg)** — 三种注意力热力图：编码器自注意力 / 解码器因果自注意力 / 交叉注意力

![heatmap_panels](docs/examples/heatmap_panels.svg)

<sub>spec：<code>specs/b__heatmap_panels.json</code></sub>

<a id="hist_fit"></a>
**[`hist_fit`](docs/examples/hist_fit.svg)** — 2000 个身高样本的密度直方图 + 理论正态曲线

![hist_fit](docs/examples/hist_fit.svg)

<sub>spec：<code>specs/b__hist_fit.json</code></sub>

<a id="kde"></a>
**[`kde`](docs/examples/kde.svg)** — 双峰分布的核密度估计（300×N(0,1) + 200×N(3,1.2)）

![kde](docs/examples/kde.svg)

<sub>spec：<code>specs/b__kde.json</code></sub>

<a id="learning_curve"></a>
**[`learning_curve`](docs/examples/learning_curve.svg)** — 序列反转任务训练 Loss 曲线

![learning_curve](docs/examples/learning_curve.svg)

<sub>spec：<code>specs/b__learning_curve.json</code></sub>

<a id="limit"></a>
**[`limit`](docs/examples/limit.svg)** — 函数值随 x 逼近某点而趋于极限

![limit](docs/examples/limit.svg)

<sub>spec：<code>specs/b__limit.json</code></sub>

<a id="loglog"></a>
**[`loglog`](docs/examples/loglog.svg)** — 每候选代价：三档差 8 个数量级

![loglog](docs/examples/loglog.svg)

<sub>spec：<code>specs/b__loglog.json</code></sub>

<a id="matrix"></a>
**[`matrix`](docs/examples/matrix.svg)** — Instruction data formats: field structure and three common formats

![matrix](docs/examples/matrix.svg)

<sub>spec：<code>specs/b__matrix.json</code></sub>

<a id="matrix_mul_panels"></a>
**[`matrix_mul_panels`](docs/examples/matrix_mul_panels.svg)** — @ 矩阵乘（行×列点积） vs * 逐元素乘（形状不匹配 → 报错）

![matrix_mul_panels](docs/examples/matrix_mul_panels.svg)

<sub>spec：<code>specs/b__matrix_mul_panels.json</code></sub>

<a id="multi_bar"></a>
**[`multi_bar`](docs/examples/multi_bar.svg)** — 重叠：覆盖率触顶后成本继续翻倍

![multi_bar](docs/examples/multi_bar.svg)

<sub>spec：<code>specs/b__multi_bar.json</code></sub>

<a id="multi_curve"></a>
**[`multi_curve`](docs/examples/multi_curve.svg)** — Precision@K 与 Recall@K 权衡曲线

![multi_curve](docs/examples/multi_curve.svg)

<sub>spec：<code>specs/b__multi_curve.json</code></sub>

<a id="multi_panel_gd"></a>
**[`multi_panel_gd`](docs/examples/multi_panel_gd.svg)** — 不同学习率下的梯度下降轨迹

![multi_panel_gd](docs/examples/multi_panel_gd.svg)

<sub>spec：<code>specs/b__multi_panel_gd.json</code></sub>

<a id="multi_subplot"></a>
**[`multi_subplot`](docs/examples/multi_subplot.svg)** — 平稳序列与随机游走对比

![multi_subplot](docs/examples/multi_subplot.svg)

<sub>spec：<code>specs/b__multi_subplot.json</code></sub>

<a id="nn_twin"></a>
**[`nn_twin`](docs/examples/nn_twin.svg)** — 单层感知机 vs 多层神经网络（含隐藏层）

![nn_twin](docs/examples/nn_twin.svg)

<sub>spec：<code>specs/b__nn_twin.json</code></sub>

<a id="normal_dist"></a>
**[`normal_dist`](docs/examples/normal_dist.svg)** — NF4 quantile points vs standard normal distribution

![normal_dist](docs/examples/normal_dist.svg)

<sub>spec：<code>specs/b__normal_dist.json</code></sub>

<a id="optimizer_paths"></a>
**[`optimizer_paths`](docs/examples/optimizer_paths.svg)** — 优化器下降轨迹对比：SGD → Adam 在狭长山谷中的表现

![optimizer_paths](docs/examples/optimizer_paths.svg)

<sub>spec：<code>specs/b__optimizer_paths.json</code></sub>

<a id="pie"></a>
**[`pie`](docs/examples/pie.svg)** — 编程语言使用占比

![pie](docs/examples/pie.svg)

<sub>spec：<code>specs/b__pie.json</code></sub>

<a id="pmf_pdf"></a>
**[`pmf_pdf`](docs/examples/pmf_pdf.svg)** — PMF（离散，柱高之和=1） vs PDF（连续，面积=1）

![pmf_pdf](docs/examples/pmf_pdf.svg)

<sub>spec：<code>specs/b__pmf_pdf.json</code></sub>

<a id="regularization_path"></a>
**[`regularization_path`](docs/examples/regularization_path.svg)** — Ridge vs Lasso 系数收缩对比

![regularization_path](docs/examples/regularization_path.svg)

<sub>spec：<code>specs/b__regularization_path.json</code></sub>

<a id="roc"></a>
**[`roc`](docs/examples/roc.svg)** — 输入过滤是 ROC 上的一个点（示意）

![roc](docs/examples/roc.svg)

<sub>spec：<code>specs/b__roc.json</code></sub>

<a id="roofline"></a>
**[`roofline`](docs/examples/roofline.svg)** — Roofline 性能模型 (H100 FP16)

![roofline](docs/examples/roofline.svg)

<sub>spec：<code>specs/b__roofline.json</code></sub>

<a id="scatter_boundary"></a>
**[`scatter_boundary`](docs/examples/scatter_boundary.svg)** — 线性可分 vs 线性不可分（XOR 问题）

![scatter_boundary](docs/examples/scatter_boundary.svg)

<sub>spec：<code>specs/b__scatter_boundary.json</code></sub>

<a id="scatter_classes"></a>
**[`scatter_classes`](docs/examples/scatter_classes.svg)** — 网格搜索示意

![scatter_classes](docs/examples/scatter_classes.svg)

<sub>spec：<code>specs/b__scatter_classes.json</code></sub>

<a id="scatter_fit"></a>
**[`scatter_fit`](docs/examples/scatter_fit.svg)** — 最小二乘拟合：使数据点到直线的竖直距离平方和最小

![scatter_fit](docs/examples/scatter_fit.svg)

<sub>spec：<code>specs/b__scatter_fit.json</code></sub>

<a id="scatter_matrix"></a>
**[`scatter_matrix`](docs/examples/scatter_matrix.svg)** — 协方差与相关性：正相关、负相关、不相关

![scatter_matrix](docs/examples/scatter_matrix.svg)

<sub>spec：<code>specs/b__scatter_matrix.json</code></sub>

<a id="scatter_panels"></a>
**[`scatter_panels`](docs/examples/scatter_panels.svg)** — K-means 迭代：① 随机初始化 → ② 按最近中心分配 → ③ 更新中心到簇均值

![scatter_panels](docs/examples/scatter_panels.svg)

<sub>spec：<code>specs/b__scatter_panels.json</code></sub>

<a id="scatter_rich"></a>
**[`scatter_rich`](docs/examples/scatter_rich.svg)** — 散点图：颜色=年龄、大小=体重偏离 60kg 的程度

![scatter_rich](docs/examples/scatter_rich.svg)

<sub>spec：<code>specs/b__scatter_rich.json</code></sub>

<a id="stacked_bar"></a>
**[`stacked_bar`](docs/examples/stacked_bar.svg)** — 权重每减半，KV 容量翻倍

![stacked_bar](docs/examples/stacked_bar.svg)

<sub>spec：<code>specs/b__stacked_bar.json</code></sub>

<a id="tangent_secant"></a>
**[`tangent_secant`](docs/examples/tangent_secant.svg)** — 割线逼近切线——导数即切线斜率

![tangent_secant](docs/examples/tangent_secant.svg)

<sub>spec：<code>specs/b__tangent_secant.json</code></sub>

<a id="tensor_blocks"></a>
**[`tensor_blocks`](docs/examples/tensor_blocks.svg)** — 0~3 维张量：标量 / 向量 / 矩阵 / 三维张量

![tensor_blocks](docs/examples/tensor_blocks.svg)

<sub>spec：<code>specs/b__tensor_blocks.json</code></sub>

<a id="tensor_cube_panels"></a>
**[`tensor_cube_panels`](docs/examples/tensor_cube_panels.svg)** — 多变量输入：三维张量（批量×时间步×特征）与「通道混合 vs 通道独立」

![tensor_cube_panels](docs/examples/tensor_cube_panels.svg)

<sub>spec：<code>specs/b__tensor_cube_panels.json</code></sub>

<a id="twin_axis"></a>
**[`twin_axis`](docs/examples/twin_axis.svg)** — 免费 batch 区：柱=吞吐，线=TPOT

![twin_axis](docs/examples/twin_axis.svg)

<sub>spec：<code>specs/b__twin_axis.json</code></sub>

<a id="vector2d"></a>
**[`vector2d`](docs/examples/vector2d.svg)** — 余弦相似度 vs 皮尔逊相关系数（二维空间对比）

![vector2d](docs/examples/vector2d.svg)

<sub>spec：<code>specs/b__vector2d.json</code></sub>

<a id="venn2"></a>
**[`venn2`](docs/examples/venn2.svg)** — 两路失手的重叠决定混合的上限

![venn2](docs/examples/venn2.svg)

<sub>spec：<code>specs/b__venn2.json</code></sub>

---

## 不支持（规范禁用 3D）

| 图型 | 建议替代 |
|---|---|
| `surface3d` | 分面等高线（`contour_quiver`）或 `heatmap` 多面板 |
| `multi_normal` | 二维等高线 + `multi_subplot` 展示不同参数 |

## 前置依赖

**一条命令自检**：`python3 scripts/draw.py --doctor`

| 用途 | 需要 | 安装 | 不装会怎样 |
|---|---|---|---|
| B 类（数据图） | **Python 3.8+** + `matplotlib` + `numpy` | `pip install matplotlib numpy` | B 类 45 种图**全部不可用** |
| webp 输出 | `Pillow` | `pip install Pillow` | 只有 **webp** 不可用（png/svg 正常） |
| A 类（结构图） | **Node.js** + Playwright + Chromium | `npm i -g playwright && npx playwright install chromium`（或用 `PW_MODULES`/`PLAYWRIGHT_BROWSERS_PATH` 指定现有安装） | A 类（Mermaid 结构图）**不可用** |
| A 类 mermaid 运行时 | **已内置**（3.4 MB） | 无需安装 | — |

## 其它文档

- [SKILL.md](SKILL.md) —— 何时用 / 工作流 / 风格规范 / 版式红线 / 常见坑
- [docs/SPEC-REFERENCE.md](docs/SPEC-REFERENCE.md) —— **按图型查参数字段** + 可复制骨架
- [TYPES.md](TYPES.md) —— 图型目录（频次与常用参数键，作选型参考）

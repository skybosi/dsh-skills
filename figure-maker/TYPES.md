# 支持的图型目录

| 类 | 数量 | 说明 |
|---|---|---|
| **A 类 · 结构图** | 6 种（实为 Mermaid 全能） | 你给 `mmd` 源码，脚本负责渲染 |
| **B 类 · 数据图** | 45 种 | 你给 `params` 数据，Matplotlib 绘制 |
| **3D** | 2 种 | **明确拒绝**（规范禁 3D），给二维替代建议 |

## A 类还能画什么（重点）

A 类走「**你给 Mermaid 源码、脚本负责渲染**」，所以**凡 Mermaid 支持的图型都能画**，不限于下面 6 种：

| 想画什么 | Mermaid 写法 | `type` 填什么 |
|---|---|---|
| 状态机 / 状态转移图 | `stateDiagram-v2` | 任一 A 类名（如 `flow`） |
| 时序图 | `sequenceDiagram` | 同上 |
| 类图 | `classDiagram` | 同上 |
| ER 图 | `erDiagram` | 同上 |
| 甘特图 | `gantt` | 同上 |
| 饼图（Mermaid 版） | `pie` | 同上 |

> 实测：TCP 状态转移图（`stateDiagram-v2`）就是这样画出来的。

## A 类 · 结构图（6 种）

| 图型 | 样例说明 | 样例 |
|---|---|---|
| `flow` | Why finetune: pretraining builds the bas | [SVG](docs/examples/flow.svg) |
| `graph` | 三大推荐范式：基于内容 / 协同过滤 / 混合 | [SVG](docs/examples/graph.svg) |
| `tree` | Finetuning taxonomy: by scope and by obj | [SVG](docs/examples/tree.svg) |
| `nn_diagram` | MLP 三层全连接网络结构 | [SVG](docs/examples/nn_diagram.svg) |
| `ladder` | 运算符优先级（从上到下递减） | [SVG](docs/examples/ladder.svg) |
| `timeline` | 六章学习链路总览 | [SVG](docs/examples/timeline.svg) |

## B 类 · 数据图（45 种）

| 图型 | 必需参数键（示例中出现） | 样例说明 |
|---|---|---|
| `area_line` | `title` · `xlabel` · `ylabel` · `x` · `y` | 相位旋转：SDR 掉到负值 |
| `bar` | `title` · `values` · `labels` · `ylabel` | Trainable parameter ratio by LoR |
| `boxplot` | `title` · `ylabel` · `groups` | 四个班级成绩分布（箱线图） |
| `cdf` | `title` · `mean` · `std` | 累积分布函数 F(x) = P(X ≤ x) |
| `contour_quiver` | `title` · `xlabel` · `ylabel` · `grid` | 梯度指向函数上升最快的方向，负梯度是下降方向 |
| `differential` | `title` · `xlabel` · `ylabel` · `func` · `x0` · `dx` | 微分 dy 与增量 Delta y——线性近似 |
| `elbow` | `title` · `xlabel` · `ylabel` · `values` · `k` · `elbow_k` | 肘部法则：K 与惯性（inertia） |
| `fit_comparison` | `title` · `panels` | 欠拟合 / 恰到好处 / 过拟合三连对比 |
| `function_curve` | `title` · `func` · `x_min` · `x_max` · `xlabel` · `ylabel` | Finetuning vs Prompting trade-of |
| `gradient_descent` | `title` · `xlabel` · `ylabel` | 梯度下降：沿负梯度方向逐步逼近最低点 |
| `grouped_bar` | `title` · `ylabel` · `categories` · `groups` | HyDE 的收益与风险同源 |
| `heatmap` | `title` · `data` · `labels` | 反事实归因：准确率 0.950 |
| `heatmap_panels` | `title` · `ncols` · `colorbar` · `colorbar_label` · `panels` | 三种注意力热力图：编码器自注意力 / 解码器因果自注意力 / 交 |
| `hist_fit` | `title` · `xlabel` · `ylabel` · `bins` · `func` · `data` | 2000 个身高样本的密度直方图 + 理论正态曲线 |
| `kde` | `title` · `xlabel` · `ylabel` · `curves` | 双峰分布的核密度估计（300×N(0,1) + 200×N(3, |
| `learning_curve` | `title` · `train` · `valid` · `x` · `xlabel` · `ylabel` | 序列反转任务训练 Loss 曲线 |
| `limit` | `title` · `xlabel` · `ylabel` · `func` · `x0` | 函数值随 x 逼近某点而趋于极限 |
| `loglog` | `title` · `xlabel` · `ylabel` · `curves` | 每候选代价：三档差 8 个数量级 |
| `matrix` | `title` · `data` | Instruction data formats: field  |
| `matrix_mul_panels` | `title` | @ 矩阵乘（行×列点积） vs * 逐元素乘（形状不匹配 → 报 |
| `multi_bar` | `title` · `panels` | 重叠：覆盖率触顶后成本继续翻倍 |
| `multi_curve` | `title` · `xlabel` · `ylabel` · `curves` | Precision@K 与 Recall@K 权衡曲线 |
| `multi_panel_gd` | `title` · `panels` | 不同学习率下的梯度下降轨迹 |
| `multi_subplot` | `title` · `panels` | 平稳序列与随机游走对比 |
| `nn_twin` | `title` · `left` · `right` | 单层感知机 vs 多层神经网络（含隐藏层） |
| `normal_dist` | `title` · `mean` · `std` · `fill_sigma` | NF4 quantile points vs standard  |
| `optimizer_paths` | `title` · `paths` | 优化器下降轨迹对比：SGD → Adam 在狭长山谷中的表现 |
| `pie` | `title` · `values` · `labels` | 编程语言使用占比 |
| `pmf_pdf` | `title` · `n` · `p` | PMF（离散，柱高之和=1） vs PDF（连续，面积=1） |
| `regularization_path` | `title` · `alphas` · `coefs` | Ridge vs Lasso 系数收缩对比 |
| `roc` | `title` · `xlabel` · `ylabel` · `auc` · `fpr` · `tpr` | 输入过滤是 ROC 上的一个点（示意） |
| `roofline` | `title` · `peak_flops` · `bandwidth` · `xlabel` · `ylabel` · `points` | Roofline 性能模型 (H100 FP16) |
| `scatter_boundary` | `title` · `panels` | 线性可分 vs 线性不可分（XOR 问题） |
| `scatter_classes` | `title` · `classes` · `centers` · `xlabel` · `ylabel` | 网格搜索示意 |
| `scatter_fit` | `title` · `x` · `y` · `slope` · `intercept` · `xlabel` | 最小二乘拟合：使数据点到直线的竖直距离平方和最小 |
| `scatter_matrix` | `title` · `panels` | 协方差与相关性：正相关、负相关、不相关 |
| `scatter_panels` | `title` · `ncols` · `panels` | K-means 迭代：① 随机初始化 → ② 按最近中心分配 → |
| `scatter_rich` | `title` · `xlabel` · `ylabel` · `colorbar_label` · `x` · `y` | 散点图：颜色=年龄、大小=体重偏离 60kg 的程度 |
| `stacked_bar` | `title` · `ylabel` · `categories` · `series` | 权重每减半，KV 容量翻倍 |
| `surface3d` | `title` · `xlabel` · `ylabel` · `func` | 二元函数 z=x²+y² 的等高线图（碗形曲面） |
| `tangent_secant` | `title` · `xlabel` · `ylabel` · `func` · `x0` | 割线逼近切线——导数即切线斜率 |
| `tensor_blocks` | `title` | 0~3 维张量：标量 / 向量 / 矩阵 / 三维张量 |
| `tensor_cube_panels` | `title` | 多变量输入：三维张量（批量×时间步×特征）与「通道混合 vs 通 |
| `twin_axis` | `title` · `xlabel` · `ylabel` · `line_x` · `line_y` · `bar_x` | 免费 batch 区：柱=吞吐，线=TPOT |
| `vector2d` | `title` · `lim` · `vectors` | 余弦相似度 vs 皮尔逊相关系数（二维空间对比） |
| `venn2` | `title` · `labels` · `intersection` | 两路失手的重叠决定混合的上限 |

## 不支持（规范禁用 3D）

| 图型 | 建议替代 |
|---|---|
| `surface3d` | 分面等高线（`contour_quiver`）或 `heatmap` 多面板 |
| `multi_normal` | 二维等高线 + `multi_subplot` 对比不同参数 |

> 频次参考来自一个真实教学插图管线的 1,015 张图统计；本 skill 不依赖那个管线。

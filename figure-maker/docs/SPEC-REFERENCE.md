# spec 参考（52 种图型）

> 想画某个图型时先看这里：**顶层字段** + 该类图型的 **`params` 键** + 一段可复制的骨架。
> 完整可运行示例见 [`specs/`](../specs/)。

## 通用顶层字段

| 字段 | 必需 | 说明 |
|---|---|---|
| `id` | 建议 | 标识；缺省时输出名用 `fig` |
| `type` | **必需** | 图型名（见下表） |
| `output` | 可选 | 输出路径（缺省 `out/<id>.svg`）；**扩展名决定格式** |
| `width_in` / `height_in` | 可选 | 画布尺寸（默认 8.0 × 4.5 英寸） |
| `params` | B 类必需 | 数据与标签（见下表） |
| `mmd` | A 类必需 | Mermaid 源码（`type` 填任一 A 类名即可） |
| `title` | A 类可选 | 图标题（B 类标题写在 `params.title`） |

## 按图型查参数

### A 类 · 结构图（给 `mmd`）（6 种）

| 图型 | `params` 键 | 可直接抄的 spec |
|---|---|---|
| `flow` | （A 类给 `mmd`，无 params） | [`specs/a__flow.json`](../specs/a__flow.json) |
| `graph` | （A 类给 `mmd`，无 params） | [`specs/a__graph.json`](../specs/a__graph.json) |
| `ladder` | （A 类给 `mmd`，无 params） | [`specs/a__ladder.json`](../specs/a__ladder.json) |
| `nn_diagram` | （A 类给 `mmd`，无 params） | [`specs/a__nn_diagram.json`](../specs/a__nn_diagram.json) |
| `timeline` | （A 类给 `mmd`，无 params） | [`specs/a__timeline.json`](../specs/a__timeline.json) |
| `tree` | （A 类给 `mmd`，无 params） | [`specs/a__tree.json`](../specs/a__tree.json) |

### B 类 · 数据图（给 `params`）（46 种）

| 图型 | `params` 键 | 可直接抄的 spec |
|---|---|---|
| `area_line` | `title` · `xlabel` · `ylabel` · `x` · `y` | [`specs/b__area_line.json`](../specs/b__area_line.json) |
| `bar` | `title` · `values` · `labels` · `ylabel` | [`specs/b__bar.json`](../specs/b__bar.json) |
| `boxplot` | `title` · `ylabel` · `groups` | [`specs/b__boxplot.json`](../specs/b__boxplot.json) |
| `cdf` | `title` · `mean` · `std` | [`specs/b__cdf.json`](../specs/b__cdf.json) |
| `contour_quiver` | `title` · `xlabel` · `ylabel` · `grid` | [`specs/b__contour_quiver.json`](../specs/b__contour_quiver.json) |
| `differential` | `title` · `xlabel` · `ylabel` · `func` · `x0` · `dx` | [`specs/b__differential.json`](../specs/b__differential.json) |
| `elbow` | `title` · `xlabel` · `ylabel` · `values` · `k` · `elbow_k` | [`specs/b__elbow.json`](../specs/b__elbow.json) |
| `fit_comparison` | `title` · `panels` | [`specs/b__fit_comparison.json`](../specs/b__fit_comparison.json) |
| `function_curve` | `title` · `func` · `x_min` · `x_max` · `xlabel` · `ylabel` | [`specs/b__function_curve.json`](../specs/b__function_curve.json) |
| `gradient_descent` | `title` · `xlabel` · `ylabel` | [`specs/b__gradient_descent.json`](../specs/b__gradient_descent.json) |
| `grouped_bar` | `title` · `ylabel` · `categories` · `groups` | [`specs/b__grouped_bar.json`](../specs/b__grouped_bar.json) |
| `heatmap` | `title` · `data` · `labels` | [`specs/b__heatmap.json`](../specs/b__heatmap.json) |
| `heatmap_panels` | `title` · `ncols` · `colorbar` · `colorbar_label` · `panels` | [`specs/b__heatmap_panels.json`](../specs/b__heatmap_panels.json) |
| `hist_fit` | `title` · `xlabel` · `ylabel` · `bins` · `func` · `data` | [`specs/b__hist_fit.json`](../specs/b__hist_fit.json) |
| `kde` | `title` · `xlabel` · `ylabel` · `curves` | [`specs/b__kde.json`](../specs/b__kde.json) |
| `learning_curve` | `title` · `train` · `valid` · `x` · `xlabel` · `ylabel` | [`specs/b__learning_curve.json`](../specs/b__learning_curve.json) |
| `limit` | `title` · `xlabel` · `ylabel` · `func` · `x0` | [`specs/b__limit.json`](../specs/b__limit.json) |
| `loglog` | `title` · `xlabel` · `ylabel` · `curves` | [`specs/b__loglog.json`](../specs/b__loglog.json) |
| `matrix` | `title` · `data` | [`specs/b__matrix.json`](../specs/b__matrix.json) |
| `matrix_mul_panels` | `title` | [`specs/b__matrix_mul_panels.json`](../specs/b__matrix_mul_panels.json) |
| `multi_bar` | `title` · `panels` | [`specs/b__multi_bar.json`](../specs/b__multi_bar.json) |
| `multi_curve` | `title` · `xlabel` · `ylabel` · `curves` | [`specs/b__multi_curve.json`](../specs/b__multi_curve.json) |
| `multi_panel_gd` | `title` · `panels` | [`specs/b__multi_panel_gd.json`](../specs/b__multi_panel_gd.json) |
| `multi_subplot` | `title` · `panels` | [`specs/b__multi_subplot.json`](../specs/b__multi_subplot.json) |
| `nn_twin` | `title` · `left` · `right` | [`specs/b__nn_twin.json`](../specs/b__nn_twin.json) |
| `normal_dist` | `title` · `mean` · `std` · `fill_sigma` | [`specs/b__normal_dist.json`](../specs/b__normal_dist.json) |
| `optimizer_paths` | `title` · `paths` | [`specs/b__optimizer_paths.json`](../specs/b__optimizer_paths.json) |
| `pie` | `title` · `values` · `labels` | [`specs/b__pie.json`](../specs/b__pie.json) |
| `pmf_pdf` | `title` · `n` · `p` | [`specs/b__pmf_pdf.json`](../specs/b__pmf_pdf.json) |
| `regularization_path` | `title` · `alphas` · `coefs` | [`specs/b__regularization_path.json`](../specs/b__regularization_path.json) |
| `roc` | `title` · `xlabel` · `ylabel` · `auc` · `fpr` · `tpr` | [`specs/b__roc.json`](../specs/b__roc.json) |
| `roofline` | `title` · `peak_flops` · `bandwidth` · `xlabel` · `ylabel` · `points` | [`specs/b__roofline.json`](../specs/b__roofline.json) |
| `scatter_boundary` | `title` · `panels` | [`specs/b__scatter_boundary.json`](../specs/b__scatter_boundary.json) |
| `scatter_classes` | `title` · `classes` · `centers` · `xlabel` · `ylabel` | [`specs/b__scatter_classes.json`](../specs/b__scatter_classes.json) |
| `scatter_fit` | `title` · `x` · `y` · `slope` · `intercept` · `xlabel` · `ylabel` · `grid` | [`specs/b__scatter_fit.json`](../specs/b__scatter_fit.json) |
| `scatter_matrix` | `title` · `panels` | [`specs/b__scatter_matrix.json`](../specs/b__scatter_matrix.json) |
| `scatter_panels` | `title` · `ncols` · `panels` | [`specs/b__scatter_panels.json`](../specs/b__scatter_panels.json) |
| `scatter_rich` | `title` · `xlabel` · `ylabel` · `colorbar_label` · `x` · `y` · `c` · `s` · `cmap` | [`specs/b__scatter_rich.json`](../specs/b__scatter_rich.json) |
| `stacked_bar` | `title` · `ylabel` · `categories` · `series` | [`specs/b__stacked_bar.json`](../specs/b__stacked_bar.json) |
| `surface3d` | `title` · `xlabel` · `ylabel` · `func` | [`specs/b__surface3d.json`](../specs/b__surface3d.json) |
| `tangent_secant` | `title` · `xlabel` · `ylabel` · `func` · `x0` | [`specs/b__tangent_secant.json`](../specs/b__tangent_secant.json) |
| `tensor_blocks` | `title` | [`specs/b__tensor_blocks.json`](../specs/b__tensor_blocks.json) |
| `tensor_cube_panels` | `title` | [`specs/b__tensor_cube_panels.json`](../specs/b__tensor_cube_panels.json) |
| `twin_axis` | `title` · `xlabel` · `ylabel` · `line_x` · `line_y` · `bar_x` · `bar_y` | [`specs/b__twin_axis.json`](../specs/b__twin_axis.json) |
| `vector2d` | `title` · `lim` · `vectors` | [`specs/b__vector2d.json`](../specs/b__vector2d.json) |
| `venn2` | `title` · `labels` · `intersection` | [`specs/b__venn2.json`](../specs/b__venn2.json) |

## 一段完整示例（B 类）

```json
{
  "id": "demo-bar", "type": "bar", "output": "out/demo-bar.svg",
  "width_in": 8.0, "height_in": 4.5,
  "params": { "title": "各方案吞吐对比",
    "categories": ["基线", "优化 A"], "values": [12.4, 18.1], "ylabel": "tokens/s" }
}
```

运行：`python3 scripts/draw.py spec.json --check` → 得到 `图` + `fig.meta.json`

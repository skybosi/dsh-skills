#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配图管线 v2 · B 类数据图绘制函数（严格按《统一视觉规范》与《布局质量红线》）

覆盖 agent-systems 用到的 6 种图型；新增图型时在这里加函数，并登记到 DRAWERS。
每个函数：sig = (params: dict, out_path: str, width_in, height_in)
  · 只从 style.SOFT_COLORS 取色
  · 文字一律用数据坐标或 transAxes（禁止 fig.text 精确定位）
  · 图例可能压数据时移到图外
"""
import math

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from style import SOFT_COLORS, soft, new_fig, save, check_layout, report_and_exit, INK

# 允许在 manifest 的 func 表达式里出现的名字（安全求值，不用 eval 裸跑）
_MATH = {
    "x": None, "np": np, "log": np.log, "log2": np.log2, "log10": np.log10,
    "exp": np.exp, "sqrt": np.sqrt, "abs": np.abs, "pow": np.power, "pi": math.pi, "e": math.e,
    # ⚠️ 必须含三角函数：manifest 的 func 里大量出现 sin/cos（缺了会 NameError → 整张图产不出）
    "sin": np.sin, "cos": np.cos, "tan": np.tan, "arcsin": np.arcsin, "arccos": np.arccos,
    "arctan": np.arctan, "arctan2": np.arctan2, "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
    "sign": np.sign, "floor": np.floor, "ceil": np.ceil, "minimum": np.minimum,
    "maximum": np.maximum, "where": np.where, "clip": np.clip, "linspace": np.linspace,
    "deg2rad": np.deg2rad, "rad2deg": np.rad2deg, "sum": np.sum, "mean": np.mean,
    # 常见激活/工具函数：manifest 里出现 sigmoid 共 11 处（漏了会让整张图产不出）
    "sigmoid": lambda v: 1.0 / (1.0 + np.exp(-v)), "relu": lambda v: np.maximum(0, v),
    "step": lambda v: np.where(v >= 0, 1.0, 0.0), "erf": np.vectorize(math.erf),
    "gaussian": lambda v, m=0.0, s=1.0: np.exp(-0.5 * ((v - m) / s) ** 2) / (s * np.sqrt(2 * np.pi)),
}


def _eval_func(expr, xs):
    """把 manifest 的 func 表达式（如 0.99**x、log(x)/log(20)）在 xs 上求值。"""
    env = dict(_MATH)
    env["x"] = xs
    return eval(compile(expr, "<func>", "eval"), {"__builtins__": {}}, env)  # noqa: S307（白名单环境）


def _finish(fig, out_path, checks_path=None):
    chk = check_layout(fig)
    save(fig, out_path)
    plt.close(fig)
    return chk


# ---------------------------------------------------------------- multi_curve
def draw_multi_curve(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    for c in p.get("curves", []):
        color = soft(c.get("color"))
        if "func" in c:
            x0 = float(c.get("x_min", 0)); x1 = float(c.get("x_max", 10))
            xs = np.linspace(x0, x1, 400)
            ys = _eval_func(c["func"], xs)
        else:
            xs = np.asarray(c.get("x", []), dtype=float); ys = np.asarray(c.get("y", []), dtype=float)
        ax.plot(xs, ys, color=color, linewidth=2.2, label=c.get("label", ""),
                marker="o" if "x" in c and len(c.get("x", [])) <= 24 else None,
                markersize=4.5, markerfacecolor="white", markeredgewidth=1.4)
    ax.set_title(p.get("title", ""), pad=12)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    n = len(p.get("curves", []))
    ax.legend(loc="best" if n <= 3 else "upper right", ncol=1 if n <= 4 else 2)
    ax.margins(x=0.04)
    return _finish(fig, out_path)


# --------------------------------------------------------------------- loglog
def draw_loglog(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    for c in p.get("curves", []):
        color = soft(c.get("color"))
        if "func" in c:
            x0 = float(c.get("x_min", 1)); x1 = float(c.get("x_max", 100))
            xs = np.logspace(np.log10(x0), np.log10(x1), 200) if x0 > 0 else np.linspace(x0, x1, 200)
            ys = _eval_func(c["func"], xs)
        else:
            xs = np.asarray(c.get("x", []), dtype=float); ys = np.asarray(c.get("y", []), dtype=float)
        ax.plot(xs, ys, color=color, linewidth=2.2, marker="o", markersize=4.5,
                markerfacecolor="white", markeredgewidth=1.4, label=c.get("label", ""))
    ax.set_xscale("log")
    ax.set_title(p.get("title", ""), pad=12)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.legend(loc="lower right" if len(p.get("curves", [])) <= 4 else "best")
    return _finish(fig, out_path)


# ---------------------------------------------------------------------- venn2
def draw_venn2(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    labels = list(p.get("labels", ["", ""]))
    while len(labels) < 2:
        labels.append("")
    r = 1.0
    d = 1.05
    ax.add_patch(Circle((-d / 2, 0), r, facecolor=SOFT_COLORS["blue"], alpha=0.35,
                        edgecolor=SOFT_COLORS["blue"], linewidth=1.5))
    ax.add_patch(Circle((d / 2, 0), r, facecolor=SOFT_COLORS["orange"], alpha=0.35,
                        edgecolor=SOFT_COLORS["orange"], linewidth=1.5))
    # 左/右独占区文字：数据坐标（圆内），并限制宽度避免溢出
    ax.text(-d / 2 - 0.42, 0.55, labels[0], ha="center", va="center", fontsize=12, color=INK["text"], wrap=True)
    ax.text(d / 2 + 0.42, 0.55, labels[1], ha="center", va="center", fontsize=12, color=INK["text"], wrap=True)
    inter = p.get("intersection", "")
    if inter:
        ax.text(0, -0.06, inter, ha="center", va="center", fontsize=11, color=INK["axis"], wrap=True)
    ax.set_title(p.get("title", ""), pad=12)
    ax.set_xlim(-2.15, 2.15); ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal"); ax.axis("off")
    return _finish(fig, out_path)


# ------------------------------------------------------------------- twin_axis
def draw_twin_axis(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    bx = np.asarray(p.get("bar_x", []), dtype=float); by = np.asarray(p.get("bar_y", []), dtype=float)
    lx = np.asarray(p.get("line_x", []), dtype=float); ly = np.asarray(p.get("line_y", []), dtype=float)
    ax.bar(bx, by, width=(bx[1] - bx[0]) * 0.55 if len(bx) > 1 else 2,
           color=SOFT_COLORS["blue"], edgecolor=SOFT_COLORS["blue"], label="写成本（条）")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel("写成本", color=INK["axis"])
    ax2 = ax.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.plot(lx, ly, color=SOFT_COLORS["red"], linewidth=2.2, marker="o", markersize=4.5,
             markerfacecolor="white", markeredgewidth=1.4, label="损失成本（线）")
    ax2.set_ylabel("损失成本", color=INK["axis"])
    ax2.grid(False)

    # 交点：仅当两条曲线在采样点上交叉/最接近处标注（数据来自 manifest，不臆造）
    if len(bx) == len(lx) and len(by) == len(ly):
        k = int(np.argmin(np.abs(by - ly)))
        # ⚠️ 不要用 annotate+arrowprops：实测其 Text bbox 会退化成高 13000+px（越界误报+重叠）
        ax2.scatter([lx[k]], [ly[k]], s=90, facecolor="none", edgecolor=SOFT_COLORS["red"],
                    linewidth=2, zorder=5)
        ax2.text(0.98, 0.06, "交点约 f=%g" % lx[k], transform=ax2.transAxes,
                 fontsize=10.5, color=INK["axis"], ha="right", va="bottom")
    # 顶部留余量：右轴最上面的刻度标签贴着画布上沿时会顶出去（实测溢出 11px）
    ax.set_ylim(0, float(max(by.max(), 1)) * 1.14)
    ax2.set_ylim(0, float(max(ly.max(), 1)) * 1.14)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", ncol=2, fontsize=10)
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


# -------------------------------------------------------------------- heatmap
def draw_heatmap(p, out_path, width_in=8.0, height_in=4.5):
    data = np.asarray(p.get("data", []), dtype=float)
    labels = list(p.get("labels", []))
    fig, ax = new_fig(width_in, height_in)
    cmap = matplotlib_colors = None
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#F8FBFF", SOFT_COLORS["blue"]])
    im = ax.imshow(data, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
    ax.set_yticks(range(data.shape[0]))
    ax.set_yticklabels(["写事务 %d" % (i + 1) for i in range(data.shape[0])])
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, str(int(data[i, j])), ha="center", va="center",
                    fontsize=11, color=INK["text"])
    ax.set_title(p.get("title", ""), pad=12)
    ax.set_ylabel("写入者")
    ax.grid(False)
    ax.set_xticks(np.arange(-0.5, len(labels), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, data.shape[0], 1), minor=True)
    ax.grid(which="minor", color="#FFFFFF", linewidth=1.6)
    ax.tick_params(which="minor", length=0)
    return _finish(fig, out_path)


# ---------------------------------------------------------------- grouped_bar
def draw_grouped_bar(p, out_path, width_in=8.0, height_in=4.5):
    cats = list(p.get("categories", []))
    groups = list(p.get("groups", []))
    colors = [SOFT_COLORS["blue"], SOFT_COLORS["green"], SOFT_COLORS["orange"], SOFT_COLORS["purple"]]
    # 纵向：类目多/名字长就要更宽，否则刻度与值标注必然互压（实测 3 张 grouped_bar 栽在这）
    long_cat = max((len(str(c)) for c in cats), default=0)
    need_w = max(width_in, 0.62 * len(cats) * max(1, len(groups)) + 1.2 * (long_cat / 6.0))
    fig, ax = new_fig(round(need_w, 1), height_in)
    n = len(groups); w = 0.8 / max(1, n)
    x = np.arange(len(cats))
    store = []
    for gi, g in enumerate(groups):
        vals = np.asarray(g.get("values", []), dtype=float)
        pos = x - 0.4 + w * (gi + 0.5)
        ax.bar(pos, vals, width=w * 0.92, color=colors[gi % len(colors)],
               edgecolor=colors[gi % len(colors)], label=g.get("label", ""))
        # 值标注防挤压（规范：过密只标关键点）：
        #   · 24 个标注挤在窄条上一定重叠 → 每个类目只标**最大值**那根
        #   · 除此之外按系列交替上下偏移，避免相邻系列贴在一起
        store.append((pos, vals, gi))
    dense = len(cats) * max(1, n) > 6
    _long_cats = any(len(str(c)) > 8 for c in cats)
    vmax = max([float(v) for _, vs, _ in store for v in vs] or [1.0])
    for pos, vals, gi in store:
        for k, (xi, v) in enumerate(zip(pos, vals)):
            if _long_cats and float(v) > 0:
                ax.text(xi, float(v) - vmax * 0.03, ("%.2f" % v).rstrip("0").rstrip("."),
                        ha="center", va="top", fontsize=9, color="#FFFFFF", zorder=4)
                continue
            if dense:
                # 每个类目只标最大的一根（其余省略）
                cat_vals = [float(store[j][1][k]) for j in range(len(store))]
                if float(v) < max(cat_vals) - 1e-12:
                    continue
                ax.text(xi, float(v) + vmax * 0.02, ("%.2f" % v).rstrip("0").rstrip("."),
                        ha="center", va="bottom", fontsize=9.5, color=INK["tick"])
            else:
                off = vmax * (0.02 if gi % 2 == 0 else 0.06)
                ax.text(xi, float(v) + off, ("%.2f" % v).rstrip("0").rstrip("."),
                        ha="center", va="bottom", fontsize=10, color=INK["tick"])
    ax.set_xticks(x); _tick_labels(ax, cats, width_in)
    # 值域要同时容纳正负（原来只按 max 算，负值柱的标注会掉到画布外）
    allv = [float(v) for g in groups for v in g.get("values", [])] or [0.0]
    lo, hi = min(0.0, min(allv)), max(0.0, max(allv))
    span = (hi - lo) or 1.0
    ax.set_ylim(lo - span * 0.12, hi + span * 0.18)
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc="upper left", ncol=n)
    return _finish(fig, out_path)


DRAWERS = {
    "multi_curve": draw_multi_curve,
    "loglog": draw_loglog,
    "venn2": draw_venn2,
    "twin_axis": draw_twin_axis,
    "heatmap": draw_heatmap,
    "grouped_bar": draw_grouped_bar,
}


def render(chart_type, params, out_path, width_in=8.0, height_in=4.5):
    if chart_type not in DRAWERS:
        raise SystemExit("未知 B 类图型：%s" % chart_type)
    return DRAWERS[chart_type](params, out_path, width_in, height_in)


# ============================ 第二批：覆盖其余高频图型 ============================
# 全部遵守同一套规范：SOFT_COLORS 取色 / 去顶右框 / 极浅虚线网格 / 文字只放在数据或轴坐标 /
# 图例可能压数据就移到图外；返回 style.check_layout() 的结果供《布局检查》引用。

def _panel_width(ncols, each=2.9, minimum=8.0):
    """多子图横向空间：每个子图至少 each 英寸，否则中文标题会被挤掉（用户反馈「显得有点挤」）。"""
    return max(minimum, round(each * max(1, int(ncols)), 1))


def _suptitle(fig, title, top=0.90):
    """多子图的主标题：**必须**关掉 autolayout 并显式留出顶部空间。

    原来用 fig.suptitle(title, y=1.02) + figure.autolayout=True —— autolayout 不为主标题留位，
    标题会被画布裁掉（用户截图发现：顶部文字不完整）。
    """
    fig.set_layout_engine("none")
    # h_pad 不够时，两行子图的**子图标题**会顶出画布（实测 4 张 multi_subplot 越界）
    fig.tight_layout(rect=[0, 0, 1, top], h_pad=2.4, w_pad=1.8)
    fig.suptitle(title, y=0.97, fontsize=14, fontweight="bold", color=INK["title"])


def _wrap_cjk(text, per_line=12):
    """按字数硬折行（优先在标点处断）：用于子图标题与长刻度标签，避免右缘越界。"""
    t = str(text)
    if len(t) <= per_line:
        return t
    out, cur = [], ""
    for ch in t:
        cur += ch
        if len(cur) >= per_line and (ch in "，,、：:；;）)」』→" or len(cur) >= per_line + 5):
            out.append(cur); cur = ""
    if cur:
        out.append(cur)
    return "\n".join(out)


def _tick_labels(ax, labels, axes_width_in=7.0):
    """刻度标签防挤压：按**子图宽度**算步长（每标签约需 26px），不够就抽稀 + 旋转。

    之前固定「每 2 个留 1 个」，在 20+ 柱子的窄子图里仍然互相重叠（实测 64 对）。
    """
    n = len(labels)
    longest = max((sum(14.0 if ord(ch) > 0x2E80 else 7.6 for ch in str(lb)) for lb in labels), default=20)
    max_labels = max(2, int(axes_width_in * 96 / max(18.0, longest + 10)))   # 按最长标签宽度算
    if longest > 120:                       # 超长标签（整句中文/公式）：强制隔位，否则必压邻居（实测 53%）
        max_labels = min(max_labels, max(1, n // 2))
    stride = max(1, -(-n // max_labels))          # 向上取整
    keep = [lb if i % stride == 0 else "" for i, lb in enumerate(labels)]
    rot = 45 if (n > 6 or longest > 45) else 0
    wrapped = [_wrap_cjk(lb, 10) if len(str(lb)) > 12 else str(lb) for lb in keep]
    ax.set_xticklabels(wrapped, fontsize=9 if (n > 6 or longest > 45) else 10.5, rotation=rot,
                       ha="right" if rot else "center", linespacing=1.15)


def _legend_below(fig, ax, handles, labels, ncol=2, bottom=0.20):
    """图例放轴下方：必须关掉 autolayout 并留出底部空间，否则图例会掉出画布（实测越界）。"""
    fig.set_layout_engine("none")
    fig.tight_layout(rect=[0, bottom, 1, 0.96])
    ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=ncol, frameon=False)


def _labels_on_bars(ax, xs, vals, fmt="%.2f", thresh=12, cats_hint=None, force_inside=False):
    """柱上标值：按**符号**放（正值在上、负值在下），并夹在值域内 —— 否则负值/大值会跑到画布外。

    cats_hint    ：类目名列表（manifest 里的原始标签）。**优先用它**判断"长类目" ——
                   不能只读 ax 的刻度标签：设置刻度前调用时会读到空，判断恒为 False（曾因此漏判）。
    force_inside ：强制把值标注放进柱内（刻度被旋转、标签会伸进绘图区时用）。
    """
    if len(xs) > thresh or not len(vals):
        return
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return
    lo, hi = min(0.0, min(vals)), max(0.0, max(vals))
    span = (hi - lo) or 1.0
    # 类目名很长（折行后会顶到上方）时，把值标注放进柱内（白字）
    if cats_hint:
        long_cats = any(len(str(lb)) > 8 for lb in cats_hint)
    else:
        long_cats = any(len(str(t.get_text())) > 8 for t in (ax.get_xticklabels() or []))
    for x, v in zip(xs, vals):
        up = v >= 0
        if not isinstance(v, (int, float)) and len(str(v)) > 10:
            continue                                              # 整句标签不画在柱上（会压刻度）
        if (long_cats and float(v) > span * 0.22) or (force_inside and float(v) > span * 0.16):
            ax.text(x, float(v) - span * 0.03, (fmt % v).rstrip("0").rstrip("."), ha="center",
                    va="top", fontsize=9.5, color="#FFFFFF", zorder=4)
            continue
        y = min(max(v + (span * 0.03 if up else -span * 0.03), lo - span * 0.02), hi + span * 0.02)
        ax.text(x, y, (fmt % v).rstrip("0").rstrip("."), ha="center",
                va="bottom" if up else "top", fontsize=10, color=INK["tick"])


def draw_bar(p, out_path, width_in=8.0, height_in=4.5):
    vals = [float(v) for v in p.get("values", [])]
    labels = [str(x) for x in p.get("labels", [])] or [str(i + 1) for i in range(len(vals))]
    fig, ax = new_fig(max(width_in, 0.75 * len(vals) + 1.0), height_in)
    xs = np.arange(len(vals))
    ax.bar(xs, vals, width=0.62, color=SOFT_COLORS["blue"], edgecolor=SOFT_COLORS["blue"])
    ax.set_xticks(xs); _tick_labels(ax, labels, width_in)
    ax.set_ylabel(p.get("ylabel", "")); ax.set_xlabel(p.get("xlabel", ""))
    lo, hi = min(0.0, min(vals) if vals else 0.0), max(0.0, max(vals) if vals else 1.0)
    sp = (hi - lo) or 1.0
    ax.set_ylim(lo - sp * 0.10, hi + sp * 0.18) if lo < 0 else ax.set_ylim(0, (hi or 1) * 1.16)
    ax.set_title(p.get("title", ""), pad=12)
    _labels_on_bars(ax, xs, vals)
    return _finish(fig, out_path)


def draw_matrix(p, out_path, width_in=8.0, height_in=4.5):
    """matrix 在本库里是**表格**（表头 + 若干行文本），不是热力图。"""
    data = p.get("data", [])
    if not data:
        raise SystemExit("matrix 无 data")
    ncol = max(len(r) for r in data)
    fig, ax = new_fig(width_in, max(2.4, 1.1 + 0.52 * len(data)))
    ax.axis("off")
    colw = [1.0 / ncol] * ncol
    tbl = ax.table(cellText=[[str(c) for c in row] for row in data], cellLoc="left",
                   colWidths=colw, loc="upper center", bbox=[0.0, 0.06, 1.0, 0.86])
    tbl.auto_set_font_size(False); tbl.set_fontsize(10.5)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#E2E8F0"); cell.set_linewidth(0.8)
        if r == 0:
            cell.set_facecolor(SOFT_COLORS["blue"]); cell.set_text_props(color=INK["text"], weight="bold")
        else:
            cell.set_facecolor("#FFFFFF" if r % 2 else "#F8FBFF")
    ax.set_title(p.get("title", ""), pad=10)
    return _finish(fig, out_path)


def draw_function_curve(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    x0 = float(p.get("x_min", 0)); x1 = float(p.get("x_max", 10))
    xs = np.linspace(x0, x1, 400)
    ax.plot(xs, _eval_func(p.get("func", "x"), xs), color=SOFT_COLORS["blue"], linewidth=2.2)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_stacked_bar(p, out_path, width_in=8.0, height_in=4.5):
    cats = [str(c) for c in p.get("categories", [])]
    series = p.get("series", [])
    fig, ax = new_fig(width_in, height_in)
    xs = np.arange(len(cats)); bottom = np.zeros(len(cats))
    for i, s in enumerate(series):
        v = np.asarray(s.get("values", []), dtype=float)
        col = soft(s.get("color")) if s.get("color") else [SOFT_COLORS["blue"], SOFT_COLORS["green"],
                                                           SOFT_COLORS["orange"], SOFT_COLORS["purple"]][i % 4]
        ax.bar(xs, v, bottom=bottom, width=0.6, color=col, edgecolor=col, label=s.get("label", ""))
        bottom = bottom + v
    ax.set_xticks(xs); _tick_labels(ax, cats, width_in)
    ax.set_ylabel(p.get("ylabel", "")); ax.set_title(p.get("title", ""), pad=12)
    _h, _l = ax.get_legend_handles_labels()
    _legend_below(fig, ax, _h, _l, ncol=min(len(series), 4), bottom=0.30)
    return _finish(fig, out_path)


def draw_normal_dist(p, out_path, width_in=8.0, height_in=4.5):
    mu = float(p.get("mean", 0)); sd = float(p.get("std", 1)) or 1.0
    fig, ax = new_fig(width_in, height_in)
    xs = np.linspace(mu - 4 * sd, mu + 4 * sd, 400)
    ys = np.exp(-0.5 * ((xs - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
    ax.plot(xs, ys, color=SOFT_COLORS["blue"], linewidth=2.2)
    if p.get("fill_sigma"):
        for k, col in ((1, SOFT_COLORS["green"]), (2, SOFT_COLORS["orange"])):
            m = np.abs(xs - mu) <= k * sd
            ax.fill_between(xs[m], ys[m], color=col, alpha=0.35)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    ax.annotate("μ=%.4g" % mu, xy=(mu, ys.max()), xytext=(0.02, 0.9), textcoords="axes fraction",
                fontsize=11, color=INK["axis"])
    return _finish(fig, out_path)


def draw_scatter_fit(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    xs = np.asarray(p.get("x", []), dtype=float); ys = np.asarray(p.get("y", []), dtype=float)
    ax.scatter(xs, ys, s=42, color=SOFT_COLORS["blue"], edgecolor="white", linewidth=0.8, zorder=3, label="样本")
    k = float(p.get("slope", 1)); b = float(p.get("intercept", 0))
    gx = np.linspace(xs.min(), xs.max(), 50)
    ax.plot(gx, k * gx + b, color=SOFT_COLORS["red"], linewidth=2.2, label="拟合 y=%.3gx+%.3g" % (k, b))
    if p.get("grid") is False:
        ax.grid(False)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc="upper left")
    return _finish(fig, out_path)


def draw_roc(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    fpr = np.asarray(p.get("fpr", []), dtype=float); tpr = np.asarray(p.get("tpr", []), dtype=float)
    ax.plot([0, 1], [0, 1], linestyle="--", color=SOFT_COLORS["grey"], linewidth=1.4, label="随机猜测")
    ax.plot(fpr, tpr, color=SOFT_COLORS["blue"], linewidth=2.4, marker="o", markersize=4.5,
            markerfacecolor="white", markeredgewidth=1.4, label="ROC（AUC=%.3g）" % float(p.get("auc", 0)))
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc="lower right")
    return _finish(fig, out_path)


def draw_learning_curve(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    xs = np.asarray(p.get("x", []), dtype=float)
    ax.plot(xs, np.asarray(p.get("train", []), dtype=float), color=SOFT_COLORS["blue"],
            linewidth=2.2, label="训练损失")
    ax.plot(xs, np.asarray(p.get("valid", []), dtype=float), color=SOFT_COLORS["red"],
            linewidth=2.2, label="验证损失")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc="upper right")
    return _finish(fig, out_path)


def draw_boxplot(p, out_path, width_in=8.0, height_in=4.5):
    groups = p.get("groups", [])
    fig, ax = new_fig(width_in, height_in)
    data = [np.asarray(g.get("data", []), dtype=float) for g in groups]
    bp = ax.boxplot(data, patch_artist=True, widths=0.5,
                    medianprops=dict(color=INK["text"], linewidth=1.4),
                    boxprops=dict(linewidth=1.2), whiskerprops=dict(color=SOFT_COLORS["grey"]),
                    capprops=dict(color=SOFT_COLORS["grey"]), flierprops=dict(markersize=4))
    for i, box in enumerate(bp["boxes"]):
        col = [SOFT_COLORS["blue"], SOFT_COLORS["green"], SOFT_COLORS["orange"], SOFT_COLORS["purple"]][i % 4]
        box.set_facecolor(col); box.set_edgecolor(col)
    ax.set_xticks(range(1, len(groups) + 1)); ax.set_xticklabels([g.get("label", "") for g in groups])
    ax.set_ylabel(p.get("ylabel", "")); ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_vector2d(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    lim = float(p.get("lim", 5))
    # 长中文标签内联必然互压 → 改为图例按颜色对应（短标签仍内联）
    for i, v in enumerate(p.get("vectors", [])):
        col = soft(v.get("color"))
        vx, vy = float(v["x"]), float(v["y"])
        ax.annotate("", xy=(vx, vy), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="-|>", color=col, linewidth=2.2),
                    label=v.get("label", ""))
        if len(str(v.get("label", ""))) <= 4:
            ax.text(vx * 1.06, vy * 1.06, v.get("label", ""), color=col, fontsize=10)
    ax.axhline(0, color=INK["tick"], linewidth=0.8); ax.axvline(0, color=INK["tick"], linewidth=0.8)
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    # ⚠️ annotate(label=…) 不会注册进图例 handles（会导致「图例是空的、文字全没了」）→ 用代理句柄
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=soft(v.get("color")), lw=2.4, marker=">", markersize=6,
                      label=str(v.get("label", "")))
               for v in p.get("vectors", []) if len(str(v.get("label", ""))) > 4]
    if handles:
        ax.legend(handles=handles, loc="upper left", fontsize=9.5, framealpha=0.9)
    return _finish(fig, out_path)


def draw_multi_bar(p, out_path, width_in=8.0, height_in=4.5):
    panels = p.get("panels", [])
    n = len(panels) or 1
    fig, axes = plt.subplots(1, n, figsize=(_panel_width(n), height_in * (1 if n <= 2 else 1.15)), squeeze=False)
    for i, pn in enumerate(panels):
        ax = axes[0][i]
        vals = [float(v) for v in pn.get("values", [])]
        labels = [str(x) for x in pn.get("labels", [])] or [str(j + 1) for j in range(len(vals))]
        xs = np.arange(len(vals))
        col = soft(pn.get("color")) if pn.get("color") else SOFT_COLORS["blue"]
        ax.bar(xs, vals, width=0.6, color=col, edgecolor=col)
        _labels_on_bars(ax, xs, vals, thresh=8, cats_hint=labels,
                    force_inside=(len(labels) > 6 or max((sum(14.0 if ord(ch) > 0x2E80 else 7.6 for ch in str(lb)) for lb in labels), default=0) > 45))
        ax.set_xticks(xs); _tick_labels(ax, labels, width_in / max(1, n))
        ax.set_title(pn.get("title", ""), fontsize=12, pad=8)
        if pn.get("ylabel"):
            ax.set_ylabel(pn["ylabel"])
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_multi_subplot(p, out_path, width_in=8.0, height_in=4.5):
    panels = p.get("panels", [])
    n = len(panels) or 1
    rows = 1 if n <= 4 else 2
    cols = int(np.ceil(n / rows))
    fig, axes = plt.subplots(rows, cols, figsize=(_panel_width(cols), height_in * rows * 1.38), squeeze=False)
    for i, pn in enumerate(panels):
        ax = axes[i // cols][i % cols]
        x0 = float(pn.get("x_min", 0)); x1 = float(pn.get("x_max", 10))
        xs = np.linspace(x0, x1, 400)
        col = soft(pn.get("color")) if pn.get("color") else SOFT_COLORS["blue"]
        ax.plot(xs, _eval_func(pn.get("func", "x"), xs), color=col, linewidth=2.0)
        # 长标题必须折行：实测「交叉熵梯度：错误时保持较大」右边缘 822 > 画布 800（真越界）
        ax.set_title(_wrap_cjk(pn.get("title", ""), 8), fontsize=9.5, pad=5, loc="left")
    for j in range(n, rows * cols):
        axes[j // cols][j % cols].axis("off")
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_scatter_boundary(p, out_path, width_in=8.0, height_in=4.5):
    panels = p.get("panels", [])
    n = len(panels) or 1
    fig, axes = plt.subplots(1, n, figsize=(_panel_width(n), height_in), squeeze=False)
    for i, pn in enumerate(panels):
        ax = axes[0][i]
        for pt in pn.get("points", []):
            if len(pt) < 3:
                continue
            col = soft(pt[2])
            ax.scatter(float(pt[0]), float(pt[1]), s=46, color=col, edgecolor="white", linewidth=0.8, zorder=3)
        b = pn.get("boundary") or {}
        # 兼容两种写法：{x:[…], y:[…]}（推荐）或 [x0, y0, x1, y1]（两点式）。
        # ⚠️ 以前只认字典 → 传列表会被**静默忽略**：图上看不到边界线，而布局检查仍然"通过"。
        bx = by = None
        if isinstance(b, dict) and b.get("x") is not None and b.get("y") is not None:
            bx, by = b["x"], b["y"]
        elif isinstance(b, (list, tuple)) and len(b) == 4:
            bx, by = [b[0], b[2]], [b[1], b[3]]
        elif b:
            print('  ⚠️ scatter_boundary：boundary 写法无法识别（%r）→ 未绘制边界线' % (b,))
        if bx is not None and by is not None:
            ax.plot(bx, by, color=SOFT_COLORS["grey"], linewidth=1.8, linestyle="--", zorder=4)
        ax.set_title(pn.get("title", ""), fontsize=12, pad=8)
        ax.set_xlabel(pn.get("xlabel", ""), fontsize=11); ax.set_ylabel(pn.get("ylabel", ""), fontsize=11)
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_scatter_classes(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    allx, ally = [], []
    for c in p.get("classes", []):
        col = soft(c.get("color"))
        xs = [float(v) for v in c.get("x", [])]; ys = [float(v) for v in c.get("y", [])]
        allx += xs; ally += ys
        ax.scatter(xs, ys, s=46, color=col, edgecolor="white", linewidth=0.8, label=c.get("label", ""), zorder=3)
    for c in p.get("centers", []):
        ax.scatter([float(c["x"])], [float(c["y"])], marker="*", s=240, color=SOFT_COLORS["red"],
                   edgecolor="white", linewidth=1, zorder=4, label="中心")
    # 参数跨度超过两个数量级 → 用对数轴（C/gamma 网格这类图）
    if allx and max(allx) / max(1e-9, min(allx)) > 100:
        ax.set_xscale("log")
    if ally and max(ally) / max(1e-9, min(ally)) > 100:
        ax.set_yscale("log")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc="best", fontsize=10)
    return _finish(fig, out_path)


def draw_fit_comparison(p, out_path, width_in=8.0, height_in=4.5):
    panels = p.get("panels", [])
    n = len(panels) or 1
    fig, axes = plt.subplots(1, n, figsize=(_panel_width(n), height_in), squeeze=False)
    for i, pn in enumerate(panels):
        ax = axes[0][i]
        sx = [float(v) for v in pn.get("scatter_x", [])]; sy = [float(v) for v in pn.get("scatter_y", [])]
        ax.scatter(sx, sy, s=40, color=SOFT_COLORS["blue"], edgecolor="white", linewidth=0.8, zorder=3)
        if pn.get("curve_func") and sx:
            gx = np.linspace(min(sx), max(sx), 200)
            ax.plot(gx, _eval_func(pn["curve_func"], gx), color=SOFT_COLORS["red"], linewidth=2.0, zorder=2)
        ax.set_title(pn.get("title", ""), fontsize=12, pad=8)
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_heatmap_panels(p, out_path, width_in=8.0, height_in=4.5):
    panels = p.get("panels", [])
    n = len(panels) or 1
    ncols = int(p.get("ncols", n)) or n
    rows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(rows, ncols, figsize=(_panel_width(ncols), max(3.4, height_in * rows / max(1, ncols) * 2.4)), squeeze=False)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("soft", ["#F8FBFF", SOFT_COLORS["blue"], SOFT_COLORS["purple"]])
    last = None
    for i, pn in enumerate(panels):
        ax = axes[i // ncols][i % ncols]
        last = ax.imshow(np.asarray(pn.get("data", []), dtype=float), cmap=cmap, aspect="auto")
        ax.set_title(pn.get("title", ""), fontsize=11.5, pad=8)
        ax.grid(False)
        for lbl in pn.get("labels", [])[:0]:
            pass
    for j in range(n, rows * ncols):
        axes[j // ncols][j % ncols].axis("off")
    if p.get("colorbar") and last is not None:
        fig.set_layout_engine("none")
        fig.tight_layout(rect=[0, 0.03, 0.84, 0.93], w_pad=1.8)     # 给色条留出右侧空间（实测需更大）
        cb = fig.colorbar(last, ax=axes.ravel().tolist(), shrink=0.85, pad=0.03)
        cb.set_label(p.get("colorbar_label", ""), color=INK["axis"], fontsize=11)
        cb.outline.set_edgecolor("#E2E8F0")
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def _mlp(ax, layers, labels, title):
    """画一个小型全连接示意图（层圆点 + 连线）"""
    ax.axis("off")
    n = len(layers)
    xs = np.linspace(0.12, 0.88, n)
    pos = []
    for li, cnt in enumerate(layers):
        cnt = max(1, int(cnt))
        ys = np.linspace(0.18, 0.82, cnt + 2)[1:-1] if cnt > 1 else [0.5]
        pos.append([(xs[li], y) for y in ys])
    for li in range(n - 1):
        for (x1, y1) in pos[li]:
            for (x2, y2) in pos[li + 1]:
                ax.plot([x1, x2], [y1, y2], color="#E2E8F0", linewidth=0.9, zorder=1)
    for li, layer in enumerate(pos):
        col = [SOFT_COLORS["orange"], SOFT_COLORS["blue"], SOFT_COLORS["green"]][li % 3]
        for (x, y) in layer:
            ax.add_patch(Circle((x, y), 0.030, facecolor=col, edgecolor="white", linewidth=1.1, zorder=3))
        if li < len(labels):
            lab = str(labels[li]).replace("\n", " ")
            lab = lab if len(lab) <= 6 else lab[:6] + "\n" + lab[6:12]      # 手动折行，避免横向互压
            ax.text(xs[li], 0.055, lab, ha="center", va="bottom", fontsize=8.5, color=INK["axis"], linespacing=1.2)
    ax.set_title(title, fontsize=12, pad=8)
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(0, 1.06)


def draw_nn_twin(p, out_path, width_in=8.0, height_in=4.5):
    left = p.get("left", {}); right = p.get("right", {})
    fig, axes = plt.subplots(1, 2, figsize=(_panel_width(2), height_in), squeeze=False)
    _mlp(axes[0][0], left.get("layers", []), left.get("layer_labels", []), left.get("title", ""))
    _mlp(axes[0][1], right.get("layers", []), right.get("layer_labels", []), right.get("title", ""))
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_scatter_panels(p, out_path, width_in=8.0, height_in=4.5):
    """KMeans 过程示意：每格若干高斯簇 + 可选中心点"""
    panels = p.get("panels", [])
    n = len(panels) or 1
    ncols = int(p.get("ncols", n)) or n
    rows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(rows, ncols, figsize=(_panel_width(ncols), height_in * rows), squeeze=False)
    rng = np.random.default_rng(7)
    for i, pn in enumerate(panels):
        ax = axes[i // ncols][i % ncols]
        for cl in pn.get("clusters", []):
            cnt = int(cl.get("n", 20)); cx = float(cl.get("cx", 0)); cy = float(cl.get("cy", 0))
            sp = float(cl.get("spread", 0.3)); col = soft(cl.get("color"))
            ax.scatter(rng.normal(cx, sp, cnt), rng.normal(cy, sp, cnt), s=26, color=col,
                       alpha=0.85, edgecolor="white", linewidth=0.6)
        for c in pn.get("centers", []) or []:
            ax.scatter([float(c.get("x", c.get("cx")))], [float(c.get("y", c.get("cy")))],
                       marker="*", s=200, color=SOFT_COLORS["red"], edgecolor="white", linewidth=1, zorder=4)
        ax.set_title(pn.get("title", ""), fontsize=11.5, pad=8)
        ax.set_xticks([]); ax.set_yticks([])
    for j in range(n, rows * ncols):
        axes[j // ncols][j % ncols].axis("off")
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


DRAWERS.update({
    "bar": draw_bar,
    "matrix": draw_matrix,
    "function_curve": draw_function_curve,
    "stacked_bar": draw_stacked_bar,
    "normal_dist": draw_normal_dist,
    "scatter_fit": draw_scatter_fit,
    "roc": draw_roc,
    "learning_curve": draw_learning_curve,
    "boxplot": draw_boxplot,
    "vector2d": draw_vector2d,
    "multi_bar": draw_multi_bar,
    "multi_subplot": draw_multi_subplot,
    "scatter_boundary": draw_scatter_boundary,
    "scatter_classes": draw_scatter_classes,
    "fit_comparison": draw_fit_comparison,
    "heatmap_panels": draw_heatmap_panels,
    "nn_twin": draw_nn_twin,
    "scatter_panels": draw_scatter_panels,
})


# ==================== 第三批：长尾图型（含 3 种「只有标题」的概念示意图）====================
# 规范一致：SOFT_COLORS 取色 / 无 3D 坐标轴 / 无阴影渐变 / 文字只放数据或轴坐标。

def draw_area_line(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    xs = np.asarray(p.get("x", []), dtype=float); ys = np.asarray(p.get("y", []), dtype=float)
    ax.plot(xs, ys, color=SOFT_COLORS["blue"], linewidth=2.4, marker="o", markersize=5,
            markerfacecolor="white", markeredgewidth=1.4)
    ax.fill_between(xs, ys, ys.min() if len(ys) else 0, color=SOFT_COLORS["blue"], alpha=0.22)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_roofline(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    peak = float(p.get("peak_flops", 100)); bw = float(p.get("bandwidth", 1))
    xs = np.logspace(-2, 4, 300)
    ax.plot(xs, np.minimum(bw * xs, peak), color=SOFT_COLORS["purple"], linewidth=2.2, label="roofline")
    for i, pt in enumerate(p.get("points", [])):
        ax.scatter(float(pt.get("intensity", 1)), float(pt.get("flops", 1)), s=52,
                   color=SOFT_COLORS["blue"], edgecolor="white", linewidth=0.9, zorder=3)
        off = (8, 8) if i % 2 == 0 else (8, -16)
        ax.annotate(pt.get("label", ""), (float(pt.get("intensity", 1)), float(pt.get("flops", 1))),
                    textcoords="offset points", xytext=off, fontsize=10, color=INK["axis"])
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_elbow(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    ks = np.asarray(p.get("k", []), dtype=float); vs = np.asarray(p.get("values", []), dtype=float)
    ax.plot(ks, vs, color=SOFT_COLORS["blue"], linewidth=2.2, marker="o", markersize=5,
            markerfacecolor="white", markeredgewidth=1.4)
    ek = p.get("elbow_k")
    if ek is not None and len(ks):
        i = int(np.argmin(np.abs(ks - float(ek))))
        ax.scatter([ks[i]], [vs[i]], s=150, facecolor="none", edgecolor=SOFT_COLORS["red"], linewidth=2, zorder=4)
        ax.annotate("拐点 K=%g" % ks[i], (ks[i], vs[i]), textcoords="offset points", xytext=(8, 10),
                    fontsize=11, color=INK["axis"])
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_tangent_secant(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    xs = np.linspace(float(p.get("x0", 1)) - 2.2, float(p.get("x0", 1)) + 2.2, 300)
    ys = _eval_func(p.get("func", "x**2"), xs)
    ax.plot(xs, ys, color=SOFT_COLORS["blue"], linewidth=2.2, label="f(x)")
    x0 = float(p.get("x0", 1)); y0 = float(_eval_func(p.get("func", "x**2"), np.array([x0]))[0])
    h = 1e-5
    k = float((_eval_func(p.get("func", "x**2"), np.array([x0 + h]))[0] - y0) / h)
    gx = np.array([x0 - 1.4, x0 + 1.4])
    ax.plot(gx, y0 + k * (gx - x0), color=SOFT_COLORS["red"], linewidth=1.8, label="切线（斜率 %.3g）" % k)
    x1 = x0 + 1.2
    y1 = float(_eval_func(p.get("func", "x**2"), np.array([x1]))[0])
    ax.plot([x0, x1], [y0, y1], color=SOFT_COLORS["green"], linewidth=1.8, linestyle="--", label="割线")
    ax.scatter([x0], [y0], s=55, color=SOFT_COLORS["red"], zorder=4)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12); ax.legend(loc="best")
    return _finish(fig, out_path)


def draw_limit(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    x0 = float(p.get("x0", 1)); f = p.get("func", "x**2 + 0.5")
    xs = np.linspace(x0 - 2, x0 + 2, 400)
    ax.plot(xs, _eval_func(f, xs), color=SOFT_COLORS["blue"], linewidth=2.2)
    y0 = float(_eval_func(f, np.array([x0]))[0])
    ax.scatter([x0], [y0], s=70, facecolor="white", edgecolor=SOFT_COLORS["red"], linewidth=2, zorder=4)
    ax.annotate("x→%.4g 时 f(x)→%.4g" % (x0, y0), (x0, y0), textcoords="offset points",
                xytext=(10, 12), fontsize=11, color=INK["axis"])
    ax.axvline(x0, color=SOFT_COLORS["grey"], linewidth=1, linestyle=":")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_differential(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    x0 = float(p.get("x0", 1)); dx = float(p.get("dx", 0.5)); f = p.get("func", "x**2 + 0.5")
    xs = np.linspace(x0 - 1.6, x0 + 1.6, 300)
    ax.plot(xs, _eval_func(f, xs), color=SOFT_COLORS["blue"], linewidth=2.2, label="f(x)")
    y0 = float(_eval_func(f, np.array([x0]))[0])
    h = 1e-5
    k = float((_eval_func(f, np.array([x0 + h]))[0] - y0) / h)
    gx = np.array([x0 - 0.3, x0 + dx + 0.3])
    ax.plot(gx, y0 + k * (gx - x0), color=SOFT_COLORS["red"], linewidth=1.8, linestyle="--", label="切线（dy）")
    x1 = x0 + dx; y1 = float(_eval_func(f, np.array([x1]))[0])
    ax.annotate("", xy=(x1, y1), xytext=(x1, y0 + k * dx),
                arrowprops=dict(arrowstyle="<->", color=SOFT_COLORS["green"], linewidth=1.8))
    ax.annotate("Δy−dy", (x1, (y1 + y0 + k * dx) / 2), textcoords="offset points", xytext=(6, 0),
                fontsize=11, color=INK["axis"])
    ax.scatter([x0, x1], [y0, y1], s=50, color=SOFT_COLORS["blue"], zorder=4)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12); ax.legend(loc="upper left")
    return _finish(fig, out_path)


def draw_gradient_descent(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    xs = np.linspace(-3, 3, 400)
    ax.plot(xs, xs ** 2, color=SOFT_COLORS["blue"], linewidth=2.2, label="损失函数")
    x = 2.6; path = [x]
    for _ in range(12):
        x = x - 0.25 * 2 * x
        path.append(x)
    ax.plot(path, [v ** 2 for v in path], color=SOFT_COLORS["red"], linewidth=1.6,
            marker="o", markersize=4.5, markerfacecolor="white")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12); ax.legend(loc="upper center")
    return _finish(fig, out_path)


def draw_contour_quiver(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    xs = np.linspace(-2.5, 2.5, 26); ys = np.linspace(-2.5, 2.5, 26)
    X, Y = np.meshgrid(xs, ys)
    Z = X ** 2 + Y ** 2
    cs = ax.contour(X, Y, Z, levels=10, colors=[SOFT_COLORS["blue"]], linewidths=1.1)
    ax.clabel(cs, inline=True, fontsize=9, fmt="%.0f")
    ax.quiver(X, Y, 2 * X, 2 * Y, color=SOFT_COLORS["grey"], scale=48, width=0.0035, alpha=0.9)
    ax.scatter([0], [0], s=60, color=SOFT_COLORS["red"], zorder=4)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    if p.get("grid") is False:
        ax.grid(False)
    return _finish(fig, out_path)


def draw_cdf(p, out_path, width_in=8.0, height_in=4.5):
    from math import erf
    fig, ax = new_fig(width_in, height_in)
    mu = float(p.get("mean", 0)); sd = float(p.get("std", 1)) or 1
    xs = np.linspace(mu - 4 * sd, mu + 4 * sd, 400)
    cdf = np.array([0.5 * (1 + erf((v - mu) / (sd * np.sqrt(2)))) for v in xs])
    ax.plot(xs, cdf, color=SOFT_COLORS["blue"], linewidth=2.2)
    ax.axhline(0.5, color=SOFT_COLORS["grey"], linewidth=1, linestyle="--")
    ax.annotate("P(X≤μ)=0.5", (mu, 0.5), textcoords="offset points", xytext=(8, -14),
                fontsize=11, color=INK["axis"])
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", "累积概率"))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_pmf_pdf(p, out_path, width_in=8.0, height_in=4.5):
    from math import comb
    fig, ax = new_fig(width_in, height_in)
    n = int(p.get("n", 6)); pr = float(p.get("p", 0.5))
    ks = np.arange(0, n + 1)
    pmf = np.array([comb(n, int(k)) * pr ** k * (1 - pr) ** (n - k) for k in ks], dtype=float)
    ax.bar(ks, pmf, width=0.55, color=SOFT_COLORS["blue"], edgecolor=SOFT_COLORS["blue"], label="二项 PMF")
    xs = np.linspace(-0.5, n + 0.5, 300)
    mu = n * pr; sd = np.sqrt(n * pr * (1 - pr)) or 1
    ax.plot(xs, np.exp(-0.5 * ((xs - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi)),
            color=SOFT_COLORS["red"], linewidth=2, label="正态近似")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12); ax.legend(loc="best")
    return _finish(fig, out_path)


def draw_hist_fit(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    data = np.asarray(p.get("data", []), dtype=float)
    if not len(data):
        raise SystemExit("hist_fit 无 data")
    ax.hist(data, bins=int(p.get("bins", 30)), density=True, color=SOFT_COLORS["blue"],
            edgecolor="white", linewidth=0.6, label="样本直方图")
    xs = np.linspace(data.min(), data.max(), 300)
    ax.plot(xs, _eval_func(p.get("func", "1"), xs), color=SOFT_COLORS["red"], linewidth=2.2, label="拟合密度")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12); ax.legend(loc="best")
    return _finish(fig, out_path)


def draw_pie(p, out_path, width_in=8.0, height_in=4.5):
    vals = [float(v) for v in p.get("values", [])]
    labels = [str(x) for x in p.get("labels", [])]
    fig, ax = new_fig(width_in, height_in)
    cols = [SOFT_COLORS["blue"], SOFT_COLORS["green"], SOFT_COLORS["orange"], SOFT_COLORS["purple"],
            SOFT_COLORS["red"], SOFT_COLORS["grey"]]
    ax.pie(vals, labels=labels, colors=cols[:len(vals)], autopct="%1.0f%%", startangle=90,
           textprops=dict(color=INK["text"], fontsize=11),
           wedgeprops=dict(edgecolor="white", linewidth=1.4))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_kde(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    curves = p.get("curves", [])
    xs = np.linspace(min(float(c.get("mean", 0)) - 4 * float(c.get("std", 1)) for c in curves),
                     max(float(c.get("mean", 0)) + 4 * float(c.get("std", 1)) for c in curves), 400)
    total = sum(float(c.get("weight", 1)) for c in curves) or 1
    mix = np.zeros_like(xs)
    for i, c in enumerate(curves):
        mu = float(c.get("mean", 0)); sd = float(c.get("std", 1)) or 1; w = float(c.get("weight", 1)) / total
        y = w * np.exp(-0.5 * ((xs - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        mix += y
        ax.plot(xs, y, color=[SOFT_COLORS["blue"], SOFT_COLORS["green"], SOFT_COLORS["orange"]][i % 3],
                linewidth=1.8, linestyle="--", label="分量 %d" % (i + 1))
    ax.plot(xs, mix, color=SOFT_COLORS["red"], linewidth=2.4, label="混合密度")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12); ax.legend(loc="best")
    return _finish(fig, out_path)


def draw_optimizer_paths(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    xs = np.linspace(-4, 4, 200); ys = np.linspace(-1.2, 3.4, 200)
    X, Y = np.meshgrid(xs, ys)
    Z = 0.12 * X ** 2 + Y ** 2
    ax.contour(X, Y, Z, levels=12, colors=[SOFT_COLORS["grey"]], linewidths=1.0)
    for i, path in enumerate(p.get("paths", [])):
        lr = float(path.get("lr", 0.05))
        col = soft(path.get("color")) if path.get("color") else [SOFT_COLORS["blue"], SOFT_COLORS["green"],
                                                                 SOFT_COLORS["orange"], SOFT_COLORS["purple"]][i % 4]
        x, y, pts = -3.6, 3.0, []
        for _ in range(22):
            pts.append((x, y))
            x = x - lr * 0.24 * x
            y = y - lr * 2 * y
        px, py = zip(*pts)
        ax.plot(px, py, color=col, linewidth=1.8, marker="o", markersize=3.5, label=path.get("label", ""))
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=10)
    return _finish(fig, out_path)


def draw_multi_panel_gd(p, out_path, width_in=8.0, height_in=4.5):
    panels = p.get("panels", [])
    n = len(panels) or 1
    fig, axes = plt.subplots(1, n, figsize=(_panel_width(n), height_in), squeeze=False)
    for i, pn in enumerate(panels):
        ax = axes[0][i]
        xs = np.linspace(-3, 3, 300)
        ax.plot(xs, xs ** 2, color=SOFT_COLORS["blue"], linewidth=2)
        lr = float(pn.get("lr", 0.1)); x = 2.7; path = [x]
        for _ in range(14):
            x = x - lr * 2 * x
            path.append(max(-3.2, min(3.2, x)))
        ax.plot(path, [v ** 2 for v in path], color=SOFT_COLORS["red"], linewidth=1.6,
                marker="o", markersize=4, markerfacecolor="white")
        ax.set_title(pn.get("title", "lr=%g" % lr), fontsize=11.5, pad=8)
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_scatter_matrix(p, out_path, width_in=8.0, height_in=4.5):
    panels = p.get("panels", [])
    n = len(panels) or 1
    fig, axes = plt.subplots(1, n, figsize=(_panel_width(n), height_in), squeeze=False)
    for i, pn in enumerate(panels):
        ax = axes[0][i]
        col = soft(pn.get("color"))
        ax.scatter([float(v) for v in pn.get("x", [])], [float(v) for v in pn.get("y", [])],
                   s=34, color=col, edgecolor="white", linewidth=0.6, alpha=0.9)
        ax.set_title(pn.get("title", ""), fontsize=11.5, pad=8)
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_regularization_path(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    alphas = np.asarray(p.get("alphas", []), dtype=float)
    coefs = np.asarray(p.get("coefs", []), dtype=float)
    cols = [SOFT_COLORS["blue"], SOFT_COLORS["green"], SOFT_COLORS["orange"], SOFT_COLORS["purple"], SOFT_COLORS["red"]]
    for i in range(coefs.shape[0] if coefs.ndim == 2 else 0):
        ax.plot(alphas, coefs[i], color=cols[i % len(cols)], linewidth=2, marker="o", markersize=4,
                markerfacecolor="white", label="系数 %d" % (i + 1))
    ax.set_xscale("log")
    ax.set_xlabel(p.get("xlabel", "正则强度 α（对数轴）")); ax.set_ylabel(p.get("ylabel", "系数大小"))
    ax.set_title(p.get("title", ""), pad=12); ax.legend(loc="best", fontsize=10)
    return _finish(fig, out_path)


def draw_scatter_rich(p, out_path, width_in=8.0, height_in=4.5):
    fig, ax = new_fig(width_in, height_in)
    sc = ax.scatter([float(v) for v in p.get("x", [])], [float(v) for v in p.get("y", [])],
                    c=[float(v) for v in p.get("c", [])], s=[float(v) for v in p.get("s", [])] or 40,
                    cmap="Blues", edgecolor="white", linewidth=0.6, alpha=0.92)
    cb = fig.colorbar(sc, ax=ax, shrink=0.9, pad=0.02)
    cb.set_label(p.get("colorbar_label", ""), color=INK["axis"], fontsize=11)
    cb.outline.set_edgecolor("#E2E8F0")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_tensor_blocks(p, out_path, width_in=8.0, height_in=4.5):
    """0~3 维张量示意（纯 2D 图元，不用 3D 轴）"""
    fig, axes = plt.subplots(1, 4, figsize=(_panel_width(4), height_in * 0.72), squeeze=False)
    titles = ["0 维：标量", "1 维：向量", "2 维：矩阵", "3 维：三维张量"]
    for i, ax in enumerate(axes[0]):
        ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_title(titles[i], fontsize=11.5, pad=6)
        if i == 0:
            ax.add_patch(Circle((0.5, 0.5), 0.1, facecolor=SOFT_COLORS["blue"], edgecolor="white"))
            ax.text(0.5, 0.3, "a", ha="center", fontsize=12, color=INK["text"])
        elif i == 1:
            for k in range(4):
                ax.add_patch(Rectangle((0.1 + k * 0.2, 0.42), 0.16, 0.16,
                                       facecolor=SOFT_COLORS["blue"], edgecolor="white"))
            ax.text(0.5, 0.3, "shape (4,)", ha="center", fontsize=10.5, color=INK["axis"])
        elif i == 2:
            for r in range(3):
                for c in range(3):
                    ax.add_patch(Rectangle((0.2 + c * 0.2, 0.24 + r * 0.18), 0.16, 0.15,
                                           facecolor=SOFT_COLORS["green"], edgecolor="white"))
            ax.text(0.5, 0.1, "shape (3, 3)", ha="center", fontsize=10.5, color=INK["axis"])
        else:
            for d in range(3):
                off = d * 0.06
                for r in range(2):
                    for c in range(2):
                        ax.add_patch(Rectangle((0.28 + c * 0.16 + off, 0.34 + r * 0.15 + off), 0.13, 0.12,
                                               facecolor=SOFT_COLORS["orange"], edgecolor="white", alpha=0.95))
            ax.text(0.5, 0.12, "shape (d, h, w)", ha="center", fontsize=10.5, color=INK["axis"])
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_matrix_mul_panels(p, out_path, width_in=8.0, height_in=4.5):
    """@ 矩阵乘 vs * 逐元素乘（示意图）"""
    fig, axes = plt.subplots(1, 2, figsize=(_panel_width(2), height_in * 0.8), squeeze=False)
    a = axes[0][0]; a.axis("off"); a.set_xlim(0, 1); a.set_ylim(0, 1)
    a.set_title("@ 矩阵乘：行 × 列 点积", fontsize=12, pad=8)
    def grid(ax, x0, y0, rows, cols, color, cw=0.12, ch=0.11):
        for r in range(rows):
            for c in range(cols):
                ax.add_patch(Rectangle((x0 + c * cw, y0 - r * ch), cw * 0.92, ch * 0.9,
                                       facecolor=color, edgecolor="white"))
    grid(a, 0.06, 0.80, 2, 3, SOFT_COLORS["blue"])
    a.text(0.44, 0.62, "@", fontsize=18, color=INK["text"])
    grid(a, 0.50, 0.80, 3, 2, SOFT_COLORS["green"])
    a.text(0.76, 0.62, "=", fontsize=18, color=INK["text"])
    grid(a, 0.82, 0.80, 2, 2, SOFT_COLORS["orange"])
    a.text(0.5, 0.22, "(2,3) @ (3,2) → (2,2)", ha="center", fontsize=11, color=INK["axis"])
    b = axes[0][1]; b.axis("off"); b.set_xlim(0, 1); b.set_ylim(0, 1)
    b.set_title("* 逐元素乘：形状必须一致", fontsize=12, pad=8)
    grid(b, 0.10, 0.80, 2, 3, SOFT_COLORS["blue"])
    b.text(0.52, 0.62, "*", fontsize=18, color=INK["text"])
    grid(b, 0.60, 0.80, 2, 2, SOFT_COLORS["red"])
    b.text(0.5, 0.30, "(2,3) * (2,2) → 报错", ha="center", fontsize=11.5, color=SOFT_COLORS["red"])
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_tensor_cube_panels(p, out_path, width_in=8.0, height_in=4.5):
    """三维张量（批量×时间步×特征）+ 通道混合 / 通道独立 两种做法"""
    fig, ax = new_fig(width_in, height_in * 0.85)
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    for d in range(4):
        off = d * 0.22
        for t in range(3):
            ax.add_patch(Rectangle((1.0 + t * 0.62 + off, 2.2 + off), 0.55, 0.5,
                                   facecolor=SOFT_COLORS["blue"], edgecolor="white", alpha=0.95))
    ax.text(2.6, 1.5, "三维张量：批量 × 时间步 × 特征", ha="center", fontsize=11.5, color=INK["text"])
    for i, (title, lines, col) in enumerate([
        ("通道混合", ["3 条序列拼成一个张量", "进同一个模型做注意力混合"], SOFT_COLORS["green"]),
        ("通道独立", ["3 条序列各自进模型", "各自输出后再汇总"], SOFT_COLORS["purple"]),
    ]):
        x0 = 5.2 + i * 2.4
        ax.add_patch(Rectangle((x0, 3.0), 2.1, 1.5, facecolor=col, alpha=0.16, edgecolor=col, linewidth=1.4))
        ax.text(x0 + 1.05, 4.15, title, ha="center", fontsize=12, color=INK["text"])
        for j, line in enumerate(lines):
            ax.text(x0 + 1.05, 3.72 - j * 0.32, line, ha="center", fontsize=10, color=INK["axis"])
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


DRAWERS.update({
    "area_line": draw_area_line, "roofline": draw_roofline, "elbow": draw_elbow,
    "tangent_secant": draw_tangent_secant, "limit": draw_limit, "differential": draw_differential,
    "gradient_descent": draw_gradient_descent, "contour_quiver": draw_contour_quiver,
    "cdf": draw_cdf, "pmf_pdf": draw_pmf_pdf, "hist_fit": draw_hist_fit, "pie": draw_pie,
    "kde": draw_kde, "optimizer_paths": draw_optimizer_paths, "multi_panel_gd": draw_multi_panel_gd,
    "scatter_matrix": draw_scatter_matrix, "regularization_path": draw_regularization_path,
    "scatter_rich": draw_scatter_rich, "tensor_blocks": draw_tensor_blocks,
    "matrix_mul_panels": draw_matrix_mul_panels, "tensor_cube_panels": draw_tensor_cube_panels,
})

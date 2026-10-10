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
# ⚠️ 必须**先**导入 style：它在模块顶层设置 MPLCONFIGDIR（否则 matplotlib 会去写 ~/.matplotlib，
#    在沙箱里直接报 “not a writable directory” 并退化到临时目录重建字体缓存）。
from style import SOFT_COLORS, FILL, soft, new_fig, save, check_layout, report_and_exit, INK
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon

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


def _soft_cmap(name="blue"):
    """连续软色板（白→浅→主色→深），色标**只用规范色板里的颜色**，不用 matplotlib 默认色图。"""
    from matplotlib.colors import LinearSegmentedColormap
    ramps = {
        "blue":      ["#FFFFFF", "#DBEAFE", SOFT_COLORS["blue"], SOFT_COLORS["purple"]],
        "warm":      ["#FFFFFF", "#FEF3C7", SOFT_COLORS["orange"], SOFT_COLORS["red"]],
        "green":     ["#FFFFFF", "#D1FAE5", SOFT_COLORS["green"], SOFT_COLORS["dark"]],
        "grey":      ["#FFFFFF", "#F1F3F5", SOFT_COLORS["grey"], SOFT_COLORS["dark"]],
        "diverging": [SOFT_COLORS["blue"], "#FFFFFF", SOFT_COLORS["orange"]],
    }
    key = name if name in ramps else "blue"
    return LinearSegmentedColormap.from_list("soft_" + key, ramps[key])


def _finish(fig, out_path, checks_path=None):
    import warnings
    with warnings.catch_warnings():
        # matplotlib 对「figure.autolayout + gridspec（KM/校准/多面板）」会警告 tight_layout 可能不准。
        # 我们紧接着就用 check_layout() 在**像素空间实测**文字位置 —— 比这条警告可靠得多，所以只静音这一条。
        warnings.filterwarnings("ignore", message=".*not compatible with tight_layout.*")
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
    bar_label = p.get("bar_label") or p.get("label_left") or "柱（左轴）"
    line_label = p.get("line_label") or p.get("label_right") or "线（右轴）"
    ax.bar(bx, by, width=(bx[1] - bx[0]) * 0.55 if len(bx) > 1 else 2,
           color=SOFT_COLORS["blue"], edgecolor=SOFT_COLORS["blue"], label=bar_label)
    ax.set_xlabel(p.get("xlabel", ""))
    ax.set_ylabel(p.get("ylabel_left") or p.get("ylabel") or bar_label, color=INK["axis"])
    ax2 = ax.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.plot(lx, ly, color=SOFT_COLORS["red"], linewidth=2.2, marker="o", markersize=4.5,
             markerfacecolor="white", markeredgewidth=1.4, label=line_label)
    ax2.set_ylabel(p.get("ylabel_right") or line_label, color=INK["axis"])
    ax2.grid(False)

    # 「两轴最接近点」只在**显式要求**时标注：两条轴量纲不同，跨轴比大小本身没有意义
    # （老版本默认就标「交点约 f=…」，样例里给出的是毫无意义的 f=0）。需要时给 mark_crossing: true。
    if p.get("mark_crossing") and len(bx) == len(lx) and len(by) == len(ly):
        k = int(np.argmin(np.abs(by - ly)))
        # ⚠️ 不要用 annotate+arrowprops：实测其 Text bbox 会退化成高 13000+px（越界误报+重叠）
        ax2.scatter([lx[k]], [ly[k]], s=90, facecolor="none", edgecolor=SOFT_COLORS["red"],
                    linewidth=2, zorder=5)
        ax2.text(0.98, 0.06, "%s=%g 处两轴最接近" % (p.get("xlabel") or "x", lx[k]), transform=ax2.transAxes,
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
    """二维强度图：计数 / 相关性 / 注意力 / 混淆都能画。

    ⚠️ 老版本把色阶写死成 `vmin=0, vmax=1` 的二值色板 —— 传 0~10 的计数矩阵时
    值 2 和值 8 会渲染成**完全相同的颜色**（色阶信息全丢）；y 轴刻度还写死成「写事务 N」。
    现在：色阶按数据取值域、轴标签由参数给、默认不留硬编码文案。
    """
    data = np.asarray(p.get("data", []), dtype=float)
    if not data.size:
        raise SystemExit("heatmap 无 data")
    fig, ax = new_fig(width_in, height_in)
    lo = float(p.get("vmin", np.min(data))); hi = float(p.get("vmax", np.max(data)))
    if hi <= lo:
        hi = lo + 1.0
    cmap_key = p.get("cmap") or ("diverging" if lo < 0 else "blue")
    im = ax.imshow(data, cmap=_soft_cmap(cmap_key), vmin=lo, vmax=hi, aspect="auto")
    x_labels = list(p.get("x_labels") or p.get("labels") or [])
    y_labels = list(p.get("y_labels") or [])
    ax.set_xticks(range(data.shape[1]))
    if x_labels:
        ax.set_xticklabels([str(x) for x in x_labels])
    ax.set_yticks(range(data.shape[0]))
    if y_labels:
        ax.set_yticklabels([str(x) for x in y_labels])
    if p.get("annot", True):
        fmt = p.get("annot_fmt") or ("%g" if float(np.max(np.abs(data))) >= 10 or lo < 0 else "%.2f")
        fs = max(8.0, min(11.0, 130.0 / max(data.shape)))
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                ax.text(j, i, fmt % data[i, j], ha="center", va="center", fontsize=fs, color=INK["text"])
    ax.set_title(p.get("title", ""), pad=12)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.grid(False)
    ax.set_xticks(np.arange(-0.5, data.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-0.5, data.shape[0], 1), minor=True)
    ax.grid(which="minor", color="#FFFFFF", linewidth=1.6)
    ax.tick_params(which="minor", length=0)
    if p.get("colorbar"):
        cb = fig.colorbar(im, ax=ax, shrink=0.9, pad=0.02)
        cb.set_label(p.get("colorbar_label", ""), color=INK["axis"], fontsize=11)
        cb.outline.set_edgecolor("#E2E8F0")
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
    ax.set_xticks(x); _tick_labels(ax, cats)          # 用实际轴宽
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


def _tick_labels(ax, labels, axes_width_in=None):
    """刻度标签防挤压：按**子图宽度**算步长（每标签约需 26px），不够就抽稀 + 旋转。

    之前固定「每 2 个留 1 个」，在 20+ 柱子的窄子图里仍然互相重叠（实测 64 对）。
    """
    if axes_width_in is None:
        try:
            axes_width_in = float(ax.figure.get_size_inches()[0])
        except Exception:
            axes_width_in = 7.0
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
    # labels 是正式键；categories 只是别名 —— 以前文档里的示例写 categories 会被**静默忽略**
    # （刻度变成 1/2/3），这里做兼容，两种写法都对。
    labels = [str(x) for x in (p.get("labels") or p.get("categories") or [])] or [str(i + 1) for i in range(len(vals))]
    fig, ax = new_fig(max(width_in, 0.75 * len(vals) + 1.0), height_in)
    xs = np.arange(len(vals))
    ax.bar(xs, vals, width=0.62, color=SOFT_COLORS["blue"], edgecolor=SOFT_COLORS["blue"])
    ax.set_xticks(xs); _tick_labels(ax, labels)      # 用实际轴宽（图会被自动加宽）
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
    ax.set_xticks(xs); _tick_labels(ax, cats)         # 用实际轴宽
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
        # ⚠️ 以前这里是一段 `for lbl in pn.get("labels", [])[:0]: pass` 的空切片死循环：
        #    面板标签被静默忽略。现在真正把它们写到刻度上。
        xl = list(pn.get("x_labels") or pn.get("labels") or [])
        yl = list(pn.get("y_labels") or [])
        if xl:
            ax.set_xticks(range(len(xl))); ax.set_xticklabels([str(x) for x in xl], fontsize=9)
        if yl:
            ax.set_yticks(range(len(yl))); ax.set_yticklabels([str(y) for y in yl], fontsize=9)
        if pn.get("values") is not None and p.get("annot"):
            d = np.asarray(pn.get("data", []), dtype=float)
            for i in range(d.shape[0]):
                for j in range(d.shape[1]):
                    ax.text(j, i, "%g" % d[i, j], ha="center", va="center", fontsize=8, color=INK["text"])
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
        # 对数轴上相邻点的标签很容易撞在一起 → 四向轮换 + 按方向对齐（原来只有上下两向）
        off = [(10, 16), (10, -30), (-10, 16), (-10, -30)][i % 4]   # 偏移要够大，对数轴上小偏移仍会压
        ax.annotate(pt.get("label", ""), (float(pt.get("intensity", 1)), float(pt.get("flops", 1))),
                    textcoords="offset points", xytext=off, fontsize=10, color=INK["axis"],
                    ha="left" if off[0] > 0 else "right")
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


# =====================================================================================
# 第四批：科研 / 研发图型
#   规范与前三批一致：只用 SOFT_COLORS 取色、去顶右框、极浅虚线网格、无阴影渐变；
#   文字只放数据坐标或轴坐标；返回 style.check_layout() 结果供 --check 与 meta 使用。
#   随机性一律用固定种子（default_rng(7)），保证「同一 spec 出同一张图」。
# =====================================================================================

_CYCLE = ("blue", "green", "orange", "purple", "red", "grey", "dark")


def _cyc(i, key=None):
    """按语义循环取软色板颜色（同义同色）。"""
    return soft(key) if key else SOFT_COLORS[_CYCLE[i % len(_CYCLE)]]


def _band(ax, x, lo, hi, color, alpha=0.20):
    """波动带 / 置信带（均值 ± std、CI 区间统一走这里）。"""
    ax.fill_between(x, lo, hi, color=color, alpha=alpha, linewidth=0, zorder=2)


def _metric_box(ax, pairs, loc="upper left", fontsize=10):
    """把指标（R²/MAE/ECE/N…）写进图内固定角落，避免压数据。"""
    txt = "\n".join("%s = %s" % (k, v) for k, v in pairs)
    pos = {"upper left": (0.02, 0.98, "left", "top"), "upper right": (0.98, 0.98, "right", "top"),
           "lower right": (0.98, 0.04, "right", "bottom"), "lower left": (0.02, 0.04, "left", "bottom")}[loc]
    ax.text(pos[0], pos[1], txt, transform=ax.transAxes, ha=pos[2], va=pos[3], fontsize=fontsize,
            color=INK["axis"], linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#FFFFFF", edgecolor="#E2E8F0",
                      linewidth=0.8, alpha=0.92))


def _tag_panels(axes, tags=None):
    """论文组图的面板标签 (a)(b)(c)…（左上角、加粗）。"""
    letters = "abcdefghijklmnopqrstuvwxyz"
    for i, ax in enumerate(axes):
        t = tags[i] if tags and i < len(tags) else "(%s)" % letters[i % 26]
        ax.text(-0.02, 1.06, t, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=11, fontweight="bold", color=INK["title"])


def _eval_func2(expr, X, Y):
    """二维表达式（等高线/曲面）：X、Y（也接受小写 x、y）都在白名单环境里。"""
    env = dict(_MATH)
    env["X"] = env["x"] = X
    env["Y"] = env["y"] = Y
    return eval(compile(expr, "<func2>", "eval"), {"__builtins__": {}}, env)  # noqa: S307（白名单）


def _text_px(text, fontsize=10.0):
    """粗估一段文字的显示宽度（px）：CJK 约 14px/字、ASCII 约 7.6px/字符（同 _tick_labels 的口径）。"""
    return sum(14.0 if ord(ch) > 0x2E80 else 7.6 for ch in str(text)) * (float(fontsize) / 12.0)


def _series_xy(s, i):
    """统一解析一条 series 的 (x, mean, std)。支持 mean/std、seeds（多次实验）、lo/hi。"""
    y = s.get("mean") or s.get("y") or s.get("values")
    if y is None and s.get("seeds"):
        arr = np.asarray(s["seeds"], dtype=float)
        y = arr.mean(axis=0)
        if s.get("std") is None:
            s = dict(s); s["std"] = arr.std(axis=0, ddof=1) if arr.shape[0] > 1 else np.zeros(arr.shape[1])
    if y is None:
        raise SystemExit("series 需要 mean/y/values 或 seeds")
    y = np.asarray(y, dtype=float)
    x = np.asarray(s.get("x"), dtype=float) if s.get("x") is not None else np.arange(len(y))
    return x, y


def draw_line_band(p, out_path, width_in=8.0, height_in=4.5):
    """均值 ± 波动带（多 seed / 多次实验 / 置信区间）——论文里最常见的曲线画法。

    params: x[] · series[{label, mean[]|y[]|seeds[[…]], std[]|lo[]|hi[], color}] · xlabel · ylabel
    """
    fig, ax = new_fig(width_in, height_in)
    for i, s in enumerate(p.get("series", [])):
        col = _cyc(i, s.get("color"))
        x, y = _series_xy(s, i)
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]
        lo = hi = None
        if s.get("std") is not None:
            sd = np.asarray(s["std"], dtype=float)[:n]
            lo, hi = y - sd, y + sd
        elif s.get("lo") is not None and s.get("hi") is not None:
            lo, hi = np.asarray(s["lo"], dtype=float)[:n], np.asarray(s["hi"], dtype=float)[:n]
        if lo is not None:
            _band(ax, x, lo, hi, col)
        ax.plot(x, y, color=col, linewidth=2.2, label=s.get("label", ""))
        if not p.get("no_markers") and n <= 24:
            ax.plot(x, y, linestyle="none", marker="o", markersize=4.5, markerfacecolor="white",
                    markeredgecolor=col, markeredgewidth=1.4)
    if p.get("logx"):
        ax.set_xscale("log")
    if p.get("logy"):
        ax.set_yscale("log")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    if any(s.get("label") for s in p.get("series", [])):
        ax.legend(loc=p.get("legend", "best"), fontsize=10)
    return _finish(fig, out_path)


def draw_errorbar(p, out_path, width_in=8.0, height_in=4.5):
    """均值 ± 误差棒：kind='bar'（默认分组柱）或 'line'（折线带误差）。

    params: labels/categories[] · groups[{label, values[], errors[], color}] · ylabel · kind
    """
    cats = [str(c) for c in (p.get("labels") or p.get("categories") or [])]
    groups = p.get("groups", [])
    if not groups:
        raise SystemExit("errorbar 需要 groups[{label, values, errors}]")
    if not cats:
        cats = [str(i + 1) for i in range(len(groups[0].get("values", [])))]
    kind = p.get("kind", "bar")
    xs = np.arange(len(cats))
    if kind == "line":
        fig, ax = new_fig(width_in, height_in)
        for i, g in enumerate(groups):
            col = _cyc(i, g.get("color"))
            v = np.asarray(g.get("values", []), dtype=float)
            e = np.asarray(g.get("errors", np.zeros_like(v)), dtype=float)
            ax.errorbar(xs[:len(v)], v, yerr=e, color=col, linewidth=2.2, marker="o", markersize=5,
                        markerfacecolor="white", markeredgewidth=1.4, capsize=4, label=g.get("label", ""))
    else:
        fig, ax = new_fig(max(width_in, 0.8 * len(cats) * max(1, len(groups)) + 1.5), height_in)
        n = len(groups); w = 0.8 / max(1, n)
        for i, g in enumerate(groups):
            col = _cyc(i, g.get("color"))
            v = np.asarray(g.get("values", []), dtype=float)
            e = np.asarray(g.get("errors", np.zeros_like(v)), dtype=float)
            ax.bar(xs[:len(v)] - 0.4 + w * (i + 0.5), v, width=w * 0.92, color=col, edgecolor=col,
                   yerr=e, capsize=3, error_kw=dict(ecolor=INK["tick"], linewidth=1.1),
                   label=g.get("label", ""))
    ax.set_xticks(xs); _tick_labels(ax, cats)
    ax.set_ylabel(p.get("ylabel", "")); ax.set_xlabel(p.get("xlabel", ""))
    if kind != "line":
        vals = [float(v) for g in groups for v in g.get("values", [])] or [1.0]
        base = float(p.get("y_min", 0.0))
        ax.set_ylim(base, max(vals) * 1.30)          # 顶部留白给图例，柱子从 0（或指定值）起
    ax.set_title(p.get("title", ""), pad=12)
    if any(g.get("label") for g in groups):
        ax.legend(loc=p.get("legend", "upper left"), ncol=min(len(groups), 4), fontsize=10)
    return _finish(fig, out_path)


def draw_parity(p, out_path, width_in=8.0, height_in=4.5):
    """预测 vs 实测（parity plot）+ y=x 参考线 + R²/MAE/RMSE —— 回归类论文标配。

    params: predicted[] · actual[] · groups[{label, predicted[], actual[], color}] · log
    """
    fig, ax = new_fig(width_in, height_in)
    groups = p.get("groups") or [{"label": p.get("label", "样本"), "predicted": p.get("predicted", []),
                                  "actual": p.get("actual", [])}]
    allp, alla = [], []
    for i, g in enumerate(groups):
        col = _cyc(i, g.get("color"))
        pr = np.asarray(g.get("predicted", []), dtype=float)
        ac = np.asarray(g.get("actual", []), dtype=float)
        n = min(len(pr), len(ac)); pr, ac = pr[:n], ac[:n]
        ax.scatter(ac, pr, s=42, color=col, edgecolor="white", linewidth=0.8, zorder=3,
                   label=g.get("label", ""))
        allp.append(pr); alla.append(ac)
    pr = np.concatenate(allp) if allp else np.array([])
    ac = np.concatenate(alla) if alla else np.array([])
    if len(pr):
        lo, hi = float(min(pr.min(), ac.min())), float(max(pr.max(), ac.max()))
        pad = (hi - lo) * 0.06 or 1.0
        lo, hi = lo - pad, hi + pad
        ax.plot([lo, hi], [lo, hi], color=SOFT_COLORS["grey"], linestyle="--", linewidth=1.4,
                label="y = x", zorder=2)
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
        if p.get("log"):
            ax.set_xscale("log"); ax.set_yscale("log")
        rmse = float(np.sqrt(np.mean((pr - ac) ** 2)))
        mae = float(np.mean(np.abs(pr - ac)))
        sst = float(np.sum((ac - ac.mean()) ** 2)) or 1e-12
        r2 = 1.0 - float(np.sum((pr - ac) ** 2)) / sst
        unit = (" " + p["unit"]) if p.get("unit") else ""
        _metric_box(ax, [("N", "%d" % len(pr)), ("R²", "%.4f" % r2),
                         ("MAE", "%.3g%s" % (mae, unit)), ("RMSE", "%.3g%s" % (rmse, unit))],
                    loc=p.get("metrics_loc", "upper left"))
    ax.set_xlabel(p.get("xlabel", "实测值")); ax.set_ylabel(p.get("ylabel", "预测值"))
    ax.set_title(p.get("title", ""), pad=12)
    if any(g.get("label") for g in groups):
        ax.legend(loc="lower right", fontsize=10)
    return _finish(fig, out_path)


def draw_calibration(p, out_path, width_in=8.0, height_in=4.5):
    """校准 / 可靠性曲线（模型置信度 vs 实际正确率）+ ECE，可选下方样本量柱。

    params: bins[{conf, acc, count}] 或 conf[]/acc[]/counts[] · show_hist（默认 true）
    """
    bins = list(p.get("bins") or [])
    if not bins:
        conf = p.get("conf") or p.get("confs") or []
        acc = p.get("acc") or p.get("accs") or []
        cnt = p.get("count") or p.get("counts") or [1] * len(conf)
        bins = [{"conf": c, "acc": a, "count": n} for c, a, n in zip(conf, acc, cnt)]
    if not bins:
        raise SystemExit("calibration 需要 bins 或 conf/acc 序列")
    conf = np.array([float(b.get("conf", b.get("confidence", 0))) for b in bins])
    acc = np.array([float(b.get("acc", b.get("accuracy", 0))) for b in bins])
    cnt = np.array([float(b.get("count", 1)) for b in bins])
    show_hist = p.get("show_hist", True)
    if show_hist:
        fig, axes = plt.subplots(2, 1, figsize=(width_in, height_in), sharex=True,
                                 gridspec_kw=dict(height_ratios=[3, 1], hspace=0.12))
        ax, axh = axes[0], axes[1]
    else:
        fig, ax = new_fig(width_in, height_in); axh = None
    w = 0.9 / max(1, len(conf))
    ax.bar(conf, acc, width=w, color=SOFT_COLORS["blue"], edgecolor="#FFFFFF", linewidth=0.8,
           zorder=2, label="实际正确率")
    ax.plot([0, 1], [0, 1], color=SOFT_COLORS["grey"], linestyle="--", linewidth=1.4,
            zorder=3, label="理想校准")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_ylabel(p.get("ylabel", "实际正确率"))
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc="upper left", fontsize=10)
    total = float(cnt.sum()) or 1.0
    ece = float(np.sum(cnt / total * np.abs(acc - conf)))
    mce = float(np.max(np.abs(acc - conf)))
    _metric_box(ax, [("ECE", "%.4f" % ece), ("MCE", "%.4f" % mce), ("N", "%d" % int(total))],
                loc=p.get("metrics_loc", "lower right"))
    if axh is not None:
        axh.bar(conf, cnt, width=w, color=SOFT_COLORS["grey"], edgecolor="#FFFFFF", linewidth=0.6)
        axh.set_ylabel("样本量", fontsize=10)
        axh.set_xlabel(p.get("xlabel", "预测置信度"))
    else:
        ax.set_xlabel(p.get("xlabel", "预测置信度"))
    return _finish(fig, out_path)


def draw_confusion(p, out_path, width_in=8.0, height_in=4.5):
    """混淆矩阵：normalize='row'（默认，行归一化）/ 'all' / 'none'，可显示各类准确率。

    params: matrix[[…]] · labels[] · normalize · annot_fmt · cmap · colorbar
    """
    m = np.asarray(p.get("matrix", p.get("data", [])), dtype=float)
    if not m.size:
        raise SystemExit("confusion 需要 matrix")
    labels = [str(x) for x in p.get("labels", [])] or [str(i + 1) for i in range(m.shape[0])]
    mode = p.get("normalize", "row")
    if mode == "row":
        denom = m.sum(axis=1, keepdims=True); z = m / np.where(denom == 0, 1, denom)
    elif mode == "all":
        z = m / (m.sum() or 1)
    else:
        z = m
    fig, ax = new_fig(width_in, height_in)
    im = ax.imshow(z, cmap=_soft_cmap(p.get("cmap", "blue")), vmin=0, vmax=float(z.max()) or 1, aspect="auto")
    fmt = p.get("annot_fmt") or ("%.2f" if mode != "none" else "%g")
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = z[i, j]
            ax.text(j, i, fmt % v, ha="center", va="center", fontsize=10,
                    color="#FFFFFF" if v > 0.6 * (z.max() or 1) else INK["text"])
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=10)
    ax.set_yticks(range(m.shape[0])); ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel(p.get("xlabel", "预测")); ax.set_ylabel(p.get("ylabel", "真实"))
    ax.set_title(p.get("title", ""), pad=12)
    ax.grid(False)
    if mode == "row":
        accs = np.diag(z)
        acc = float(np.average(accs, weights=[max(1.0, float(v)) for v in m.sum(axis=1)]))
        note = "准确率 %.4f ｜ 宏平均召回 %.4f" % (acc, float(accs.mean()))
        # 指标默认写进标题行：塞进图内会与角落格子的数值互相压（实测 overlap=1）
        if p.get("metrics_in_figure"):
            _metric_box(ax, [("准确率", "%.4f" % acc), ("宏平均召回", "%.4f" % float(accs.mean()))],
                        loc=p.get("metrics_loc", "lower right"), fontsize=9)
        else:
            ax.set_title((p.get("title", "") + " ｜ " + note).strip(" ｜"), pad=12)
    if p.get("colorbar"):
        cb = fig.colorbar(im, ax=ax, shrink=0.9, pad=0.02)
        cb.set_label(p.get("colorbar_label", ""), color=INK["axis"], fontsize=11)
        cb.outline.set_edgecolor("#E2E8F0")
    return _finish(fig, out_path)


def draw_violin(p, out_path, width_in=8.0, height_in=4.5):
    """小提琴图（分布形态对比），可叠原始散点与箱线。

    params: groups[{label, data[]|values[], color}] · ylabel · show_points · show_box
    """
    groups = p.get("groups", [])
    if not groups:
        raise SystemExit("violin 需要 groups[{label, data}]")
    fig, ax = new_fig(width_in, height_in)
    data = [np.asarray(g.get("data", g.get("values", [])), dtype=float) for g in groups]
    pos = np.arange(1, len(data) + 1)
    vp = ax.violinplot(data, positions=pos, widths=0.72, showextrema=False, showmedians=False)
    for i, body in enumerate(vp["bodies"]):
        col = _cyc(i, groups[i].get("color"))
        body.set_facecolor(col); body.set_edgecolor(col); body.set_alpha(0.55); body.set_linewidth(1.2)
    if p.get("show_box", True):
        bp = ax.boxplot(data, positions=pos, widths=0.12, patch_artist=True, showfliers=False,
                        medianprops=dict(color=INK["text"], linewidth=1.3),
                        whiskerprops=dict(color=SOFT_COLORS["grey"]),
                        capprops=dict(color=SOFT_COLORS["grey"]))
        for b in bp["boxes"]:
            b.set_facecolor("#FFFFFF"); b.set_edgecolor(SOFT_COLORS["grey"])
    if p.get("show_points"):
        rng = np.random.default_rng(7)                      # 固定种子 → 图可复现
        for i, d in enumerate(data):
            if not len(d):
                continue
            ax.scatter(pos[i] + rng.uniform(-0.12, 0.12, len(d)), d, s=12, alpha=0.55,
                       color=SOFT_COLORS["dark"], edgecolor="none", zorder=4)
    ax.set_xticks(pos); _tick_labels(ax, [str(g.get("label", i + 1)) for i, g in enumerate(groups)])
    ax.set_ylabel(p.get("ylabel", "")); ax.set_xlabel(p.get("xlabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


DRAWERS.update({
    "line_band": draw_line_band, "errorbar": draw_errorbar, "parity": draw_parity,
    "calibration": draw_calibration, "confusion": draw_confusion, "violin": draw_violin,
})


def draw_ecdf(p, out_path, width_in=8.0, height_in=4.5):
    """经验累积分布（ECDF）：不对分布形态做任何假设，直接比多组数据。

    params: series/groups[{label, data[]|values[], color}] · xlabel · ylabel · mark_quantiles[]
    """
    groups = p.get("series") or p.get("groups") or []
    if not groups:
        raise SystemExit("ecdf 需要 series/groups[{label, data}]")
    fig, ax = new_fig(width_in, height_in)
    for i, g in enumerate(groups):
        col = _cyc(i, g.get("color"))
        d = np.sort(np.asarray(g.get("data", g.get("values", [])), dtype=float))
        if not len(d):
            continue
        y = np.arange(1, len(d) + 1) / len(d)
        ax.step(d, y, where="post", color=col, linewidth=2.2, label=g.get("label", ""))
        if p.get("show_points") and len(d) <= 60:
            ax.plot(d, y, linestyle="none", marker="o", markersize=3.4, color=col, alpha=0.7)
    for q in (p.get("mark_quantiles") or []):
        ax.axhline(float(q), color=SOFT_COLORS["grey"], linestyle="--", linewidth=1.0)
        ax.text(ax.get_xlim()[0], float(q), " P%d" % round(float(q) * 100), fontsize=9,
                color=INK["tick"], va="bottom", ha="left")
    ax.set_ylim(0, 1.02)
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", "累积概率 F(x)"))
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc=p.get("legend", "lower right"), fontsize=10)
    return _finish(fig, out_path)


def draw_radar(p, out_path, width_in=8.0, height_in=4.5):
    """雷达图（多指标多方案对比）：轴按维度均分，默认从正上方顺时针。

    params: axes[] · series[{label, values[], color, fill}] · ymax · fill
    """
    labels = [str(a) for a in p.get("axes", [])]
    series = p.get("series", [])
    if not labels or not series:
        raise SystemExit("radar 需要 axes[] 与 series[{label, values}]")
    fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(width_in, height_in))
    ang = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    ang += ang[:1]
    ax.set_theta_offset(np.pi / 2); ax.set_theta_direction(-1)
    vmax = 0.0
    for i, s in enumerate(series):
        col = _cyc(i, s.get("color"))
        v = np.asarray(s.get("values", []), dtype=float)
        if len(v) != len(labels):
            raise SystemExit("radar：series[%d].values 长度(%d) 必须等于 axes 数量(%d)" % (i, len(v), len(labels)))
        vmax = max(vmax, float(v.max()))
        vv = np.concatenate([v, v[:1]])
        ax.plot(ang, vv, color=col, linewidth=2.0, label=s.get("label", ""), zorder=3)
        if s.get("fill", p.get("fill", True)):
            ax.fill(ang, vv, color=col, alpha=0.16, zorder=2)
    top = float(p.get("ymax") or 0) or (vmax * 1.15 or 1.0)
    ax.set_ylim(0, top)
    ax.set_yticks([top * 0.25, top * 0.5, top * 0.75])
    # 环形刻度标签会和轴标签抢位置（实测 overlap=1）→ 不标数字，只在角落给出量程
    ax.set_yticklabels([])
    ax.text(0.995, -0.03, "量程 0–%.3g" % top, transform=ax.transAxes, ha="right", va="top",
            fontsize=9.5, color=INK["tick"])
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels, fontsize=10.5, color=INK["text"])
    ax.grid(color="#F1F3F5", linewidth=0.8)
    ax.spines["polar"].set_color("#E2E8F0")
    ax.set_title(p.get("title", ""), pad=22)
    if any(s.get("label") for s in series):
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=min(len(series), 3),
                  fontsize=10, frameon=False)
    return _finish(fig, out_path)


def draw_flamegraph(p, out_path, width_in=8.0, height_in=4.5):
    """火焰图：**宽度 = 耗时占比，深度 = 调用层级**（自顶向下，父帧横向包住子帧）。

    params: folded["a;b;c 12", …] 或 stacks[{name, value, children[]}] ·
            show_root · hide_root（旧名，等价）· labels · value_labels · axis · sortby · min_label_ratio

    ⚠️ 与上一版的区别（上一版看着"怪"的三个原因）：
      1. 隐藏 root 时还给它留了一整行 → 图上方一大片空白；现在行号从 0 起算，紧贴标题
      2. 窄帧的标签被硬截成 "dat…" / "opt…"；现在**放不下就不画**（不再出现残缺文字），
         放得下且开了 value_labels 时显示 "42.5 (20%)"
      3. 没有刻度/量纲提示；axis=true 时给出 0–100% 轴，value_labels 给绝对值+百分比
    """
    def from_folded(lines):
        root = {"name": "all", "value": 0.0, "children": {}}
        for line in lines:
            line = str(line).strip()
            if not line:
                continue
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue
            path, val = [x for x in parts[0].split(";") if x], float(parts[1])
            root["value"] += val
            node = root
            for seg in path:
                node = node["children"].setdefault(seg, {"name": seg, "value": 0.0, "children": {}})
                node["value"] += val
        return root

    if p.get("folded"):
        root = from_folded(p["folded"])
    elif p.get("stacks"):
        def norm(n, idx=0):
            kids = {("%s#%d" % (c.get("name", ""), i)): norm(c, i) for i, c in enumerate(n.get("children") or [])}
            val = float(n.get("value", 0) or 0) or sum(k["value"] for k in kids.values())
            return {"name": str(n.get("name", "")), "value": val, "children": kids}
        root = {"name": "all", "value": sum(float(x.get("value", 0)) for x in p["stacks"]),
                "children": {("%s#%d" % (x.get("name", ""), i)): norm(x, i) for i, x in enumerate(p["stacks"])}}
    else:
        raise SystemExit("flamegraph 需要 folded 或 stacks")

    total = root["value"] or 1.0
    show_root = bool(p.get("show_root", not p.get("hide_root", True)))
    sortby = p.get("sortby", "value")
    frames = []

    def layout(node, x0, depth):
        frames.append((node["name"], x0, node["value"], depth))
        kids = list(node["children"].values())
        if sortby == "value":
            kids.sort(key=lambda k: -k["value"])
        elif sortby == "name":
            kids.sort(key=lambda k: str(k["name"]))
        cx = x0
        for c in kids:
            layout(c, cx, depth + 1)
            cx += c["value"]

    layout(root, 0.0, 0)
    depth0 = 0 if show_root else 1                      # 隐藏 root 时不留空行（修掉顶部大片空白）
    vis = [f for f in frames if f[3] >= depth0]
    n_rows = max(1, max(f[3] for f in vis) - depth0 + 1)
    row_h = float(p.get("row_height", 0.86))
    show_total = p.get("show_total", True)
    fig_h = max(float(height_in), 0.46 * n_rows + 0.85)
    fig, ax = new_fig(width_in, fig_h)
    ax.set_xlim(0, total)
    bottom = (n_rows - 1) + row_h + (0.62 if show_total else 0.10)
    ax.set_ylim(bottom, -0.10)
    depth_cols = ["blue", "green", "orange", "purple", "grey", "red", "dark"]
    # 用户单位 → 像素的粗略换算：按轴宽估（画布留边约 12%）
    px_per_unit = (float(width_in) * 0.88 * 96.0) / total
    min_ratio = float(p.get("min_label_ratio", 0.0))
    for name, x0, w, d in vis:
        row = d - depth0
        col = SOFT_COLORS[depth_cols[(max(1, d) - 1) % len(depth_cols)]]
        ax.add_patch(Rectangle((x0, row), w, row_h, facecolor=col, edgecolor="#FFFFFF", linewidth=0.8))
        if not p.get("labels", True) or not name:
            continue
        avail = w * px_per_unit - 10
        tname = str(name)
        need = _text_px(tname, 9.0)
        if p.get("value_labels"):
            vt = "%.4g (%d%%)" % (w, round(w / total * 100))
            if need + _text_px(vt, 8.0) + 14 <= avail:
                ax.text(x0 + w / 2, row + row_h * 0.30, tname, ha="center", va="center", fontsize=9, color=INK["text"])
                ax.text(x0 + w / 2, row + row_h * 0.66, vt, ha="center", va="center", fontsize=8, color=INK["axis"])
                continue
        if need <= avail and w / total >= min_ratio:
            ax.text(x0 + w / 2, row + row_h / 2, tname, ha="center", va="center", fontsize=9, color=INK["text"])
    if p.get("axis"):
        ax.set_xticks([0, total * 0.25, total * 0.5, total * 0.75, total])
        ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
        ax.set_xlabel(p.get("xlabel", "占总量比例"))
    else:
        ax.set_xticks([])
    ax.set_yticks([])
    for sp in ("left", "bottom"):
        ax.spines[sp].set_visible(False)
    if show_total:
        unit = (" " + str(p["unit"])) if p.get("unit") else ""
        ax.text(0, bottom - 0.34, "%s合计 %.4g%s（每帧宽度 = 占总量比例）"
                % (str(p.get("total_label", "") + " " if p.get("total_label") else ""), root["value"], unit),
                ha="left", va="center", fontsize=9.5, color=INK["tick"])
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_panels(p, out_path, width_in=8.0, height_in=4.5):
    """论文组图：多面板 + (a)(b)(c) 标签 + 可选共享轴（每格可以是 line/bar/scatter/area）。

    params: panels[{kind, title, x, y, values, labels, series[], xlabel, ylabel, color, legend}] ·
            ncols · tags[] · sharex · sharey · each_in
    """
    panels = p.get("panels", [])
    if not panels:
        raise SystemExit("panels 需要 panels[]")
    n = len(panels)
    ncols = int(p.get("ncols") or (n if n <= 3 else 3))
    rows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(rows, ncols, squeeze=False, sharex=bool(p.get("sharex")), sharey=bool(p.get("sharey")),
                             figsize=(_panel_width(ncols, each=float(p.get("each_in", 3.0))),
                                      height_in * rows * (1.05 if rows == 1 else 1.25)))
    flat = [axes[i][j] for i in range(rows) for j in range(ncols)]
    for i, pn in enumerate(panels):
        ax = flat[i]
        kind = pn.get("kind", "line")
        col = _cyc(i, pn.get("color"))
        if kind == "bar":
            vals = [float(v) for v in pn.get("values", [])]
            labs = [str(x) for x in (pn.get("labels") or pn.get("categories") or [])] or [str(k + 1) for k in range(len(vals))]
            ax.bar(np.arange(len(vals)), vals, width=0.62, color=col, edgecolor=col)
            ax.set_xticks(np.arange(len(vals))); _tick_labels(ax, labs, 3.0)
        elif kind == "scatter":
            ax.scatter(pn.get("x", []), pn.get("y", []), s=28, color=col, edgecolor="white", linewidth=0.7)
        elif kind == "area":
            xs = np.asarray(pn.get("x", []), dtype=float); ys = np.asarray(pn.get("y", []), dtype=float)
            ax.plot(xs, ys, color=col, linewidth=2.0)
            ax.fill_between(xs, ys, float(ys.min()) if len(ys) else 0, color=col, alpha=0.22)
        else:
            x = np.asarray(pn.get("x", []), dtype=float)
            if pn.get("series"):
                for si, s in enumerate(pn["series"]):
                    sc = _cyc(si, s.get("color"))
                    ax.plot(np.asarray(s.get("x", x), dtype=float), s.get("y", []), color=sc,
                            linewidth=2.0, label=s.get("label", ""))
                if pn.get("legend", True):
                    ax.legend(fontsize=9, loc="best")
            else:
                ax.plot(x, pn.get("y", []), color=col, linewidth=2.0)
            if pn.get("logx"):
                ax.set_xscale("log")
            if pn.get("logy"):
                ax.set_yscale("log")
        ax.set_title(pn.get("title", ""), fontsize=11, pad=6)
        if pn.get("xlabel"):
            ax.set_xlabel(pn["xlabel"], fontsize=10)
        if pn.get("ylabel"):
            ax.set_ylabel(pn["ylabel"], fontsize=10)
        ax.grid(pn.get("grid", True))
    for j in range(n, len(flat)):
        flat[j].axis("off")
    _tag_panels(flat[:n], p.get("tags"))
    _suptitle(fig, p.get("title", ""))
    return _finish(fig, out_path)


def draw_waterfall(p, out_path, width_in=8.0, height_in=4.5):
    """瀑布图：从起点逐项累加的增量分解（特征贡献 / 成本归因 / 预算变化）。

    params: items[{label, value}] · start · show_total · ylabel · value_fmt
    """
    items = p.get("items", [])
    if not items:
        raise SystemExit("waterfall 需要 items[{label, value}]")
    labels = [str(it.get("label", "")) for it in items]
    vals = [float(it.get("value", 0)) for it in items]
    show_total = p.get("show_total", True)
    start = float(p.get("start", 0.0))
    fmt = p.get("value_fmt", "%.3g")
    n = len(vals) + (1 if show_total else 0)
    fig, ax = new_fig(max(width_in, 1.15 * n + 1.2), height_in)
    run = start
    lows, highs = [0.0], [] 
    for i, v in enumerate(vals):
        bottom = run if v >= 0 else run + v
        ax.bar(i, v, bottom=bottom, width=0.62, color=(SOFT_COLORS["green"] if v >= 0 else SOFT_COLORS["red"]),
               edgecolor="#FFFFFF", linewidth=0.8)
        if i:
            ax.plot([i - 1 + 0.31, i - 0.31], [run, run], color=SOFT_COLORS["grey"], linestyle="--", linewidth=1.0, zorder=1)
        lows.append(min(bottom, bottom + v)); highs.append(max(bottom, bottom + v))
        run += v
    span = (max(highs + [run, 0.0]) - min(lows + [run, 0.0])) or 1.0
    run2 = start
    for i, v in enumerate(vals):
        top = run2 + v if v >= 0 else run2
        ax.text(i, top + span * 0.02 if v >= 0 else top - span * 0.02, fmt % v, ha="center",
                va="bottom" if v >= 0 else "top", fontsize=9.5, color=INK["tick"])
        run2 += v
    if show_total:
        ax.bar(n - 1, run, width=0.62, color=SOFT_COLORS["dark"], edgecolor="#FFFFFF", linewidth=0.8)
        ax.text(n - 1, run + span * 0.02, fmt % run, ha="center", va="bottom", fontsize=9.5, color=INK["tick"])
        labels = labels + [p.get("total_label", "总计")]
    ax.axhline(0, color=INK["tick"], linewidth=0.8)
    ax.set_xticks(np.arange(n)); _tick_labels(ax, labels)
    ax.set_ylabel(p.get("ylabel", ""))
    ax.set_ylim(min(lows + [0.0, run]) - span * 0.10, max(highs + [0.0, run]) + span * 0.16)
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_contourf(p, out_path, width_in=8.0, height_in=4.5):
    """填充等高线（z=f(x,y)）：二维表达曲面 / 损失景观 / 参数扫描，比 3D 更易读。

    params: func（表达式，变量 X/Y 或 x/y）或 data[][] · x_min/x_max/y_min/y_max · levels · colorbar
    """
    x0 = float(p.get("x_min", -3)); x1 = float(p.get("x_max", 3))
    y0 = float(p.get("y_min", -3)); y1 = float(p.get("y_max", 3))
    n = int(p.get("n", 120))
    xs = np.linspace(x0, x1, n); ys = np.linspace(y0, y1, n)
    X, Y = np.meshgrid(xs, ys)
    if p.get("data") is not None:
        Z = np.asarray(p["data"], dtype=float)
        X, Y = np.meshgrid(np.linspace(x0, x1, Z.shape[1]), np.linspace(y0, y1, Z.shape[0]))
    else:
        Z = np.asarray(_eval_func2(p.get("func", "X**2 + Y**2"), X, Y), dtype=float)
    fig, ax = new_fig(width_in, height_in)
    levels = int(p.get("levels", 12))
    cf = ax.contourf(X, Y, Z, levels=levels, cmap=_soft_cmap(p.get("cmap", "blue")))
    if p.get("lines", True):
        ax.contour(X, Y, Z, levels=levels, colors="#FFFFFF", linewidths=0.5, alpha=0.55)
    if p.get("mark_min"):
        k = int(np.argmin(Z)); ax.scatter([X.ravel()[k]], [Y.ravel()[k]], s=70, marker="*",
                                          color=SOFT_COLORS["red"], edgecolor="white", linewidth=0.8, zorder=5)
        ax.text(X.ravel()[k], Y.ravel()[k], " min=%.4g" % Z.ravel()[k], fontsize=9.5, color=INK["text"], va="bottom")
    ax.set_xlabel(p.get("xlabel", "x")); ax.set_ylabel(p.get("ylabel", "y"))
    ax.set_title(p.get("title", ""), pad=12)
    if p.get("colorbar", True):
        cb = fig.colorbar(cf, ax=ax, shrink=0.92, pad=0.02)
        cb.set_label(p.get("colorbar_label", ""), color=INK["axis"], fontsize=11)
        cb.outline.set_edgecolor("#E2E8F0")
    return _finish(fig, out_path)


DRAWERS.update({
    "ecdf": draw_ecdf, "radar": draw_radar, "flamegraph": draw_flamegraph,
    "panels": draw_panels, "waterfall": draw_waterfall, "contourf": draw_contourf,
})


def draw_spectrum(p, out_path, width_in=8.0, height_in=4.5):
    """信号 / 频谱 / 谱图：可直接给 (freq, 幅值)，也可给时域 signal + sample_rate 自动 FFT。

    params: x/freq[] · y/amplitude[] ｜ 或 signal[] + sample_rate · top_peaks（自动标峰值）· logy
    """
    if p.get("signal") is not None:
        sig = np.asarray(p["signal"], dtype=float)
        fs = float(p.get("sample_rate", len(sig)))
        n = len(sig)
        f = np.fft.rfftfreq(n, d=1.0 / fs)
        A = np.abs(np.fft.rfft(sig - sig.mean())) * 2.0 / max(1, n)
    else:
        f = np.asarray(p.get("x", p.get("freq", [])), dtype=float)
        A = np.asarray(p.get("y", p.get("amplitude", [])), dtype=float)
    if not len(f) or not len(A):
        raise SystemExit("spectrum 需要 x/y 或 signal")
    fig, ax = new_fig(width_in, height_in)
    col = soft(p.get("color")) if p.get("color") else SOFT_COLORS["blue"]
    ax.plot(f, A, color=col, linewidth=1.8)
    if p.get("fill"):
        ax.fill_between(f, A, 0, color=col, alpha=0.18, linewidth=0)
    topk = int(p.get("top_peaks", 0))
    if topk > 0 and len(A) >= 3:
        idx = [i for i in range(1, len(A) - 1) if A[i] > A[i - 1] and A[i] >= A[i + 1]]
        idx.sort(key=lambda i: -A[i])
        for i in idx[:topk]:
            ax.annotate("%.4g @ %.4g" % (A[i], f[i]), xy=(f[i], A[i]), xytext=(0, 9),
                        textcoords="offset points", ha="center", fontsize=9, color=INK["axis"])
            ax.scatter([f[i]], [A[i]], s=28, facecolor="none", edgecolor=SOFT_COLORS["red"], linewidth=1.4, zorder=4)
    if p.get("logy"):
        ax.set_yscale("log")
    if p.get("logx"):
        ax.set_xscale("log")
    ax.set_xlabel(p.get("xlabel", "频率")); ax.set_ylabel(p.get("ylabel", "幅值"))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_residual(p, out_path, width_in=8.0, height_in=4.5):
    """残差诊断图：残差 vs 拟合值 + 0 线 + ±2σ（异方差 / 系统性偏差一眼看出）。

    params: fitted[] · residual[] ｜ 或 x[]+y[]+slope+intercept（自动算）· sigma · band
    """
    fitted = p.get("fitted"); resid = p.get("residual")
    if resid is None:
        x = np.asarray(p.get("x", []), dtype=float); y = np.asarray(p.get("y", []), dtype=float)
        if not len(x) or not len(y):
            raise SystemExit("residual 需要 fitted/residual 或 x/y(+slope/intercept)")
        k = float(p.get("slope", 1)); b = float(p.get("intercept", 0))
        fitted = k * x + b
        resid = y - np.asarray(fitted, dtype=float)
    fitted = np.asarray(fitted, dtype=float); resid = np.asarray(resid, dtype=float)
    sigma = float(p.get("sigma") or (resid.std(ddof=1) if len(resid) > 1 else 1.0)) or 1.0
    fig, ax = new_fig(width_in, height_in)
    if p.get("band", True):
        ax.axhspan(-2 * sigma, 2 * sigma, color=SOFT_COLORS["blue"], alpha=0.10, zorder=1)
    ax.axhline(0, color=INK["tick"], linewidth=1.0, zorder=2)
    for kk, ls in ((2, "--"), (3, ":")):
        ax.axhline(kk * sigma, color=SOFT_COLORS["grey"], linestyle=ls, linewidth=1.0, zorder=2)
        ax.axhline(-kk * sigma, color=SOFT_COLORS["grey"], linestyle=ls, linewidth=1.0, zorder=2)
    ax.scatter(fitted, resid, s=40, color=SOFT_COLORS["blue"], edgecolor="white", linewidth=0.8, zorder=3)
    inside = float(np.mean(np.abs(resid) <= 2 * sigma)) if len(resid) else 0.0
    _metric_box(ax, [("N", "%d" % len(resid)), ("σ", "%.3g" % sigma),
                     ("±2σ 内", "%.1f%%" % (inside * 100))], loc=p.get("metrics_loc", "upper right"))
    ax.set_xlabel(p.get("xlabel", "拟合值")); ax.set_ylabel(p.get("ylabel", "残差"))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_fit_band(p, out_path, width_in=8.0, height_in=4.5):
    """散点 + 拟合线 + 置信/预测带（论文里比单纯一条拟合线更严谨）。

    params: x[] · y[] · band[{x, lo, hi}] ｜ 或 slope/intercept/se/t（解析生成带）· log
    """
    x = np.asarray(p.get("x", []), dtype=float); y = np.asarray(p.get("y", []), dtype=float)
    if not len(x) or not len(y):
        raise SystemExit("fit_band 需要 x/y")
    fig, ax = new_fig(width_in, height_in)
    ax.scatter(x, y, s=42, color=SOFT_COLORS["blue"], edgecolor="white", linewidth=0.8, zorder=3,
               label=p.get("label", "样本"))
    band = p.get("band") or {}
    col = soft(p.get("color")) if p.get("color") else SOFT_COLORS["red"]
    if band:
        bx = np.asarray(band.get("x", []), dtype=float)
        ax.plot(bx, band.get("y", band.get("fit", [])), color=col, linewidth=2.2, zorder=4)
        if band.get("lo") is not None and band.get("hi") is not None:
            _band(ax, bx, np.asarray(band["lo"], dtype=float), np.asarray(band["hi"], dtype=float), col)
    else:
        k = float(p.get("slope", 1)); b = float(p.get("intercept", 0))
        bx = np.linspace(x.min(), x.max(), 120)
        yhat = k * bx + b
        ax.plot(bx, yhat, color=col, linewidth=2.2, zorder=4, label="拟合 y=%.3gx+%.3g" % (k, b))
        if p.get("se") is not None:
            t = float(p.get("t", 1.96)); xbar = x.mean(); sxx = float(np.sum((x - xbar) ** 2)) or 1e-12
            half = t * float(p["se"]) * np.sqrt(1.0 / len(x) + (bx - xbar) ** 2 / sxx)
            _band(ax, bx, yhat - half, yhat + half, col)
    if p.get("log"):
        ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(p.get("xlabel", "")); ax.set_ylabel(p.get("ylabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc=p.get("legend", "best"), fontsize=10)
    return _finish(fig, out_path)


def draw_box_jitter(p, out_path, width_in=8.0, height_in=4.5):
    """箱线 + 原始散点抖动：小样本时**必须**这样画，否则箱线会掩盖真实分布。

    params: groups[{label, data[]|values[], color}] · ylabel · jitter · show_box
    """
    groups = p.get("groups", [])
    if not groups:
        raise SystemExit("box_jitter 需要 groups[{label, data}]")
    fig, ax = new_fig(width_in, height_in)
    data = [np.asarray(g.get("data", g.get("values", [])), dtype=float) for g in groups]
    pos = np.arange(1, len(data) + 1)
    if p.get("show_box", True):
        bp = ax.boxplot(data, positions=pos, widths=0.5, patch_artist=True, showfliers=False,
                        medianprops=dict(color=INK["text"], linewidth=1.4),
                        whiskerprops=dict(color=SOFT_COLORS["grey"]),
                        capprops=dict(color=SOFT_COLORS["grey"]))
        for i, box in enumerate(bp["boxes"]):
            c = _cyc(i, groups[i].get("color"))
            box.set_facecolor(c); box.set_edgecolor(c); box.set_alpha(0.45)
    rng = np.random.default_rng(7)                     # 固定种子 → 可复现
    jit = float(p.get("jitter", 0.14))
    for i, d in enumerate(data):
        if not len(d):
            continue
        ax.scatter(pos[i] + rng.uniform(-jit, jit, len(d)), d, s=float(p.get("size", 16)),
                   color=SOFT_COLORS["dark"], alpha=0.55, edgecolor="none", zorder=4)
    ax.set_xticks(pos); _tick_labels(ax, [str(g.get("label", i + 1)) for i, g in enumerate(groups)])
    ax.set_ylabel(p.get("ylabel", "")); ax.set_xlabel(p.get("xlabel", ""))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_km(p, out_path, width_in=8.0, height_in=4.5):
    """Kaplan-Meier 生存曲线（含删失标记与可选风险表）。

    params: groups[{label, times[], events[]（1=事件 0=删失）, color}] · at_risk（默认 true）·
            risk_times[] · xlabel · ylabel
    """
    groups = p.get("groups", [])
    if not groups:
        raise SystemExit("km 需要 groups[{label, times, events}]")
    curves = []
    for g in groups:
        t = np.asarray(g.get("times", []), dtype=float)
        e = np.asarray(g.get("events", np.ones_like(t)), dtype=float)
        order = np.argsort(t); t, e = t[order], e[order]
        xs, ys = [0.0], [1.0]
        s = 1.0
        for tu in np.unique(t):
            mask = t == tu
            d = int(np.sum(e[mask] == 1)); r = int(np.sum(t >= tu))
            if d > 0 and r > 0:
                s *= 1.0 - d / r
                xs.append(float(tu)); ys.append(s)
        curves.append((g, np.asarray(xs), np.asarray(ys)))
    show_risk = p.get("at_risk", True)
    if show_risk:
        fig, axes = plt.subplots(2, 1, figsize=(width_in, height_in), sharex=True,
                                 gridspec_kw=dict(height_ratios=[3.2, 1], hspace=0.12))
        ax, axr = axes[0], axes[1]
    else:
        fig, ax = new_fig(width_in, height_in); axr = None
    tmax = 0.0
    for i, (g, xs, ys) in enumerate(curves):
        col = _cyc(i, g.get("color"))
        ax.step(xs, ys, where="post", color=col, linewidth=2.2, label=g.get("label", ""))
        tmax = max(tmax, float(xs[-1]) if len(xs) else 0.0)
        # 删失标记：在删失时刻的生存概率处画一条小竖线
        tt = np.asarray(g.get("times", []), dtype=float)
        ee = np.asarray(g.get("events", np.ones_like(tt)), dtype=float)
        for tc in tt[ee == 0]:
            sv = float(ys[max(0, np.searchsorted(xs, tc, side="right") - 1)])
            ax.plot([tc, tc], [sv, sv + 0.03], color=col, linewidth=1.2, zorder=4)
        if len(xs) > 1 and g.get("median", True):
            below = np.where(ys <= 0.5)[0]
            if len(below):
                ax.plot([0, xs[below[0]]], [0.5, 0.5], color=col, linestyle=":", linewidth=1.0, alpha=0.7)
                ax.plot([xs[below[0]], xs[below[0]]], [0, 0.5], color=col, linestyle=":", linewidth=1.0, alpha=0.7)
    ax.set_ylim(0, 1.02); ax.set_ylabel(p.get("ylabel", "生存概率"))
    ax.set_title(p.get("title", ""), pad=12)
    ax.legend(loc=p.get("legend", "lower left"), fontsize=10)
    if axr is not None:
        rts = p.get("risk_times") or list(np.linspace(0, tmax, 5))
        ng = max(1, len(curves))
        base_w = (rts[1] - rts[0]) * 0.72 if len(rts) > 1 else max(1.0, tmax * 0.12)
        w = base_w / ng
        show_n = ng * len(rts) <= 12
        for i, (g, _xs, _ys) in enumerate(curves):
            tt = np.asarray(g.get("times", []), dtype=float)
            counts = [int(np.sum(tt >= rt)) for rt in rts]
            col = _cyc(i, g.get("color"))
            xpos = np.asarray(rts, dtype=float) + (i - (ng - 1) / 2.0) * w   # 多组必须错开
            axr.bar(xpos, counts, width=w * 0.86, color=col, alpha=0.75,
                    edgecolor="#FFFFFF", linewidth=0.6, label=g.get("label", ""))
            if show_n:
                for xp, c in zip(xpos, counts):
                    axr.text(xp, c, "%d" % c, ha="center", va="bottom", fontsize=8, color=INK["tick"])
        axr.set_ylabel("风险人数", fontsize=10)
        axr.set_ylim(0, max(1, max(int(np.sum(np.asarray(g2.get("times", []), dtype=float) >= 0))
                                   for g2 in groups)) * 1.35)
        axr.set_xlabel(p.get("xlabel", "时间"))
    else:
        ax.set_xlabel(p.get("xlabel", "时间"))
    return _finish(fig, out_path)


def draw_forest(p, out_path, width_in=8.0, height_in=4.5):
    """森林图：效应量 + 置信区间（可带汇总菱形），适合 meta 分析 / 亚组对比。

    params: items[{label, estimate, lo, hi}] · null（默认 1）· log · summary{estimate, lo, hi} · annotate
    """
    items = p.get("items", [])
    if not items:
        raise SystemExit("forest 需要 items[{label, estimate, lo, hi}]")
    labels = [str(it.get("label", "")) for it in items]
    est = np.array([float(it.get("estimate", 0)) for it in items])
    lo = np.array([float(it.get("lo", it.get("estimate", 0))) for it in items])
    hi = np.array([float(it.get("hi", it.get("estimate", 0))) for it in items])
    summ = p.get("summary")
    n = len(items) + (1 if summ else 0)
    fig, ax = new_fig(width_in, max(2.4, 0.42 * n + 1.4))
    ys = np.arange(len(items))[::-1]
    for i, yy in enumerate(ys):
        col = _cyc(i) if p.get("color_each") else SOFT_COLORS["blue"]
        ax.plot([lo[i], hi[i]], [yy, yy], color=col, linewidth=1.8, zorder=2)
        ax.scatter([est[i]], [yy], s=60, color=col, edgecolor="white", linewidth=0.9, zorder=3)
        if p.get("annotate", True):
            ax.text(hi.max() + (hi.max() - lo.min()) * 0.04, yy,
                    "%.3g [%.3g, %.3g]" % (est[i], lo[i], hi[i]), va="center", fontsize=9, color=INK["axis"])
    null = float(p.get("null", 1.0))
    ax.axvline(null, color=SOFT_COLORS["grey"], linestyle="--", linewidth=1.2, zorder=1)
    if summ:
        sy = -1.0
        poly = [[float(summ.get("lo", summ.get("estimate", 0))), sy],
                [float(summ.get("estimate", 0)), sy + 0.32],
                [float(summ.get("hi", summ.get("estimate", 0))), sy],
                [float(summ.get("estimate", 0)), sy - 0.32]]
        ax.add_patch(Polygon(poly, closed=True, facecolor=SOFT_COLORS["purple"],
                             edgecolor=SOFT_COLORS["purple"], alpha=0.85, zorder=3))
        ys = np.append(ys, sy); labels = labels + [p.get("summary_label", "合并效应")]
    ax.set_yticks(ys); ax.set_yticklabels(labels, fontsize=10)
    ax.axhline(ys.min() - 0.6, color="#E2E8F0", linewidth=0.8)
    ax.set_ylim(ys.min() - 0.9, ys.max() + 0.6)
    if p.get("log", True):
        ax.set_xscale("log")
    ax.set_xlabel(p.get("xlabel", "效应量（OR / HR，95% CI）"))
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


def draw_volcano(p, out_path, width_in=8.0, height_in=4.5):
    """火山图：差异表达 / 差异分析（log2FC vs −log10 p）。

    params: log2fc[] · pvalue[] · fc_threshold · p_threshold · label_top · names[]
    """
    fc = np.asarray(p.get("log2fc", p.get("fc", [])), dtype=float)
    pv = np.asarray(p.get("pvalue", p.get("p", [])), dtype=float)
    if not len(fc) or not len(pv):
        raise SystemExit("volcano 需要 log2fc 与 pvalue")
    y = -np.log10(np.clip(pv, 1e-300, None))
    fct = float(p.get("fc_threshold", 1.0)); pt = float(p.get("p_threshold", 0.05))
    up = (fc >= fct) & (pv <= pt); dn = (fc <= -fct) & (pv <= pt); ns = ~(up | dn)
    fig, ax = new_fig(width_in, height_in)
    ax.scatter(fc[ns], y[ns], s=26, color=SOFT_COLORS["grey"], alpha=0.65, edgecolor="none", label="不显著")
    ax.scatter(fc[dn], y[dn], s=32, color=SOFT_COLORS["blue"], alpha=0.85, edgecolor="white", linewidth=0.4, label="下调")
    ax.scatter(fc[up], y[up], s=32, color=SOFT_COLORS["red"], alpha=0.85, edgecolor="white", linewidth=0.4, label="上调")
    ax.axhline(-np.log10(pt), color=SOFT_COLORS["grey"], linestyle="--", linewidth=1.0)
    ax.axvline(fct, color=SOFT_COLORS["grey"], linestyle="--", linewidth=1.0)
    ax.axvline(-fct, color=SOFT_COLORS["grey"], linestyle="--", linewidth=1.0)
    names = list(p.get("names") or [])
    topk = int(p.get("label_top", 0))
    if topk and names:
        score = np.where(up | dn, y * np.abs(fc), -1.0)
        offs = [(6, 5), (6, -13), (-6, 5), (-6, -13), (6, 15), (-6, 15)]
        for rank, i in enumerate(np.argsort(-score)[:topk]):
            dx, dy = offs[rank % len(offs)]
            ax.annotate(str(names[i]), (fc[i], y[i]), xytext=(dx, dy), textcoords="offset points",
                        ha="left" if dx > 0 else "right", fontsize=9, color=INK["axis"])
    ax.set_xlabel(p.get("xlabel", "log2 fold change")); ax.set_ylabel(p.get("ylabel", "−log10 p"))
    ax.set_title(p.get("title", ""), pad=12)
    # 图例默认放左下：右上角是上调点 + 基因名标注的地盘（实测会压住标签）
    ax.legend(loc=p.get("legend", "lower left"), fontsize=10)
    return _finish(fig, out_path)


def _cluster_tree(mat):
    """平均连接（UPGMA）层次聚类，纯 numpy 实现：返回 (叶序, merges, sizes)。

    merges[k] = (a, b, dist)，新簇 id = n + k；sizes[c] = 该簇叶子数。
    """
    n = len(mat)
    if n < 2:
        return list(range(n)), [], {i: 1 for i in range(n)}
    if n == 2:
        d = float(np.linalg.norm(mat[0] - mat[1]))
        return [0, 1], [(0, 1, d)], {0: 1, 1: 1, 2: 2}
    D = {i: {} for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            d = float(np.linalg.norm(mat[i] - mat[j]))
            D[i][j] = d; D[j][i] = d
    members = {i: [i] for i in range(n)}
    sizes = {i: 1 for i in range(n)}
    active = list(range(n)); nxt = n; merges = []
    while len(active) > 1:
        best = None
        for ai in range(len(active)):
            for bi in range(ai + 1, len(active)):
                a, b = active[ai], active[bi]
                d = D[a][b]
                if best is None or d < best[0]:
                    best = (d, a, b)
        d, a, b = best
        merges.append((a, b, d))
        members[nxt] = members[a] + members[b]
        sizes[nxt] = sizes[a] + sizes[b]
        D.setdefault(nxt, {})
        for k in active:
            if k in (a, b):
                continue
            dd = 0.5 * (D[a][k] + D[b][k])       # 平均连接
            D[nxt][k] = dd; D[k][nxt] = dd
        active = [k for k in active if k not in (a, b)] + [nxt]
        nxt += 1
    return members[active[0]], merges, sizes


def _dendro_segments(merges, order):
    """把 merges 转成折线：返回 [(leaf1, dist1, leaf2, dist2), …]，leaf 坐标 = 叶序 + 0.5。"""
    rank = {leaf: i for i, leaf in enumerate(order)}
    span = {leaf: (rank[leaf], rank[leaf]) for leaf in order}
    hgt = {leaf: 0.0 for leaf in order}
    segs = []
    for k, (a, b, d) in enumerate(merges):
        ca = (span[a][0] + span[a][1] + 1) / 2.0
        cb = (span[b][0] + span[b][1] + 1) / 2.0
        segs.append((ca, hgt[a], ca, d))
        segs.append((cb, hgt[b], cb, d))
        segs.append((ca, d, cb, d))
        nid = len(order) + k
        span[nid] = (min(span[a][0], span[b][0]), max(span[a][1], span[b][1]))
        hgt[nid] = d
    return segs


def draw_clustered_heatmap(p, out_path, width_in=8.0, height_in=4.5):
    """表达矩阵热图：可选 z-score、按层次聚类重排行列、**可选画 dendrogram 聚类树**。

    params: data[][] · row_labels[] · col_labels[] · zscore（'row'|'col'|'none'）·
            cluster（'rows'|'both'|'none'）· dendrogram（true 时画树）· colorbar · cmap
    """
    d = np.asarray(p.get("data", []), dtype=float)
    if not d.size:
        raise SystemExit("clustered_heatmap 需要 data[][]")
    mode = p.get("zscore", "row")
    if mode == "row":
        mu = d.mean(axis=1, keepdims=True); sd = d.std(axis=1, keepdims=True)
        z = (d - mu) / np.where(sd == 0, 1, sd)
    elif mode == "col":
        mu = d.mean(axis=0, keepdims=True); sd = d.std(axis=0, keepdims=True)
        z = (d - mu) / np.where(sd == 0, 1, sd)
    else:
        z = d
    cl = p.get("cluster", "rows")
    want_tree = bool(p.get("dendrogram"))
    rows = list(range(d.shape[0])); cols = list(range(d.shape[1]))
    row_segs = col_segs = None
    if cl in ("rows", "both") and d.shape[0] >= 2:
        order, merges, _sizes = _cluster_tree(d)        # 聚类用原始矩阵（不是 z-score 后的）
        rows = order
        if want_tree:
            row_segs = _dendro_segments(merges, order)
    if cl == "both" and d.shape[1] >= 2:
        order_c, merges_c, _sz = _cluster_tree(d.T)
        cols = order_c
        if want_tree:
            col_segs = _dendro_segments(merges_c, order_c)
    z = z[np.ix_(rows, cols)]
    rl = [str(x) for x in p.get("row_labels", [])]
    clab = [str(x) for x in p.get("col_labels", [])]
    rl = [rl[i] for i in rows] if len(rl) == d.shape[0] else []
    clab = [clab[i] for i in cols] if len(clab) == d.shape[1] else []
    v = float(np.max(np.abs(z))) or 1.0
    cmap = _soft_cmap(p.get("cmap", "diverging"))

    if row_segs or col_segs:
        # 2×2：左上留空，右上是列树，左下是行树，右下是热图
        fig = plt.figure(figsize=(width_in, height_in))
        gs = fig.add_gridspec(2, 2, width_ratios=[0.15 if row_segs else 0.001, 1],
                              height_ratios=[0.16 if col_segs else 0.001, 1],
                              wspace=0.22 if row_segs else 0.02, hspace=0.03)
        fig.set_layout_engine("none")
        ax = fig.add_subplot(gs[1, 1])
        axr = fig.add_subplot(gs[1, 0]) if row_segs else None
        axc = fig.add_subplot(gs[0, 1]) if col_segs else None
    else:
        fig, ax = new_fig(width_in, height_in)
        axr = axc = None

    im = ax.imshow(z, cmap=cmap, vmin=-v, vmax=v, aspect="auto")
    ax.set_xticks(range(z.shape[1]))
    if clab:
        ax.set_xticklabels(clab, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(z.shape[0]))
    if rl:
        ax.set_yticklabels(rl, fontsize=9)   # 标签留在热图左侧的槽位里（放右侧会和色条重叠）
    ax.grid(False)
    ax.set_xlabel(p.get("xlabel", ""))
    if p.get("ylabel") and axr is None:
        ax.set_ylabel(p["ylabel"], fontsize=10)
    if axr is not None:
        for (l1, d1, l2, d2) in row_segs:
            axr.plot([d1, d2], [l1, l2], color=INK["tick"], linewidth=0.9)
        axr.set_ylim(z.shape[0], 0)
        axr.invert_xaxis()                        # 距离大的根在左侧
        axr.axis("off")
    if axc is not None:
        for (l1, d1, l2, d2) in col_segs:
            axc.plot([l1, l2], [d1, d2], color=INK["tick"], linewidth=0.9)
        axc.set_xlim(0, z.shape[1])
        axc.axis("off")
    if axc is not None:
        fig.suptitle(p.get("title", ""), y=0.985, fontsize=14, fontweight="bold", color=INK["title"])
    else:
        ax.set_title(p.get("title", ""), pad=12)
    if p.get("colorbar", True):
        # ⚠️ 必须挂在**热图轴**上：挂到列树轴上会把色条压成一条细缝，刻度标签互相重叠
        cb = fig.colorbar(im, ax=ax, shrink=0.92, pad=0.02)
        cb.set_label(p.get("colorbar_label", "z-score" if mode != "none" else ""), color=INK["axis"], fontsize=11)
        cb.outline.set_edgecolor("#E2E8F0")
    if row_segs or col_segs:
        # 关掉 autolayout 后必须自己留边距，否则底部 xlabel 会掉到画布外
        fig.subplots_adjust(left=0.04, right=0.90, top=0.92, bottom=0.18)
    return _finish(fig, out_path)


def _prep_3d(ax, p):
    """3D 轴统一去灰底、浅网格（默认 3D 会带一块难看的灰背景）。

    3D 投影后刻度文字很容易互相压，所以刻度数量压到 ≤4 个、字号降到 9。
    """
    from matplotlib.ticker import MaxNLocator
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor((1.0, 1.0, 1.0, 1.0))
        axis.pane.set_edgecolor("#E2E8F0")
        axis.set_major_locator(MaxNLocator(4))
    ax.tick_params(labelsize=9)
    try:                                     # 收缩 3D 盒子：投影后的刻度文字最容易顶出画布
        ax.set_box_aspect(None, zoom=float(p.get("zoom", 0.86)))
    except Exception:
        pass
    ax.grid(True, color="#F1F3F5", linewidth=0.8)
    if p.get("view"):
        ax.view_init(elev=float(p["view"][0]), azim=float(p["view"][1]))


def _grid_xyz(p):
    x0 = float(p.get("x_min", -3)); x1 = float(p.get("x_max", 3))
    y0 = float(p.get("y_min", -3)); y1 = float(p.get("y_max", 3))
    n = int(p.get("n", 60))
    X, Y = np.meshgrid(np.linspace(x0, x1, n), np.linspace(y0, y1, n))
    if p.get("data") is not None:
        Z = np.asarray(p["data"], dtype=float)
    else:
        Z = np.asarray(_eval_func2(p.get("func", "X**2 + Y**2"), X, Y), dtype=float)
    return X, Y, Z


def draw_surface3d(p, out_path, width_in=8.0, height_in=4.5):
    """三维曲面 z=f(x,y)。**可选图型**：默认规范用 contourf 做二维表达，需要立体感时再用它。

    params: func（X/Y 表达式）或 data[][] · x_min/x_max/y_min/y_max · cmap · wireframe · view[elev, azim]
    """
    X, Y, Z = _grid_xyz(p)
    fig = plt.figure(figsize=(width_in, height_in))
    ax = fig.add_subplot(111, projection="3d")
    cmap = _soft_cmap(p.get("cmap", "blue"))
    if p.get("wireframe"):
        ax.plot_wireframe(X, Y, Z, color=SOFT_COLORS["blue"], linewidth=0.6, rstride=2, cstride=2)
        mappable = None
    else:
        mappable = ax.plot_surface(X, Y, Z, cmap=cmap, linewidth=0, antialiased=True,
                                   alpha=float(p.get("alpha", 0.96)))
    _prep_3d(ax, p)
    ax.set_xlabel(p.get("xlabel", "x")); ax.set_ylabel(p.get("ylabel", "y"))
    ax.set_zlabel(p.get("zlabel", "z"))
    ax.set_title(p.get("title", ""), pad=10)
    if mappable is not None and p.get("colorbar", True):
        cb = fig.colorbar(mappable, ax=ax, shrink=0.62, pad=0.08)
        cb.set_label(p.get("colorbar_label", ""), color=INK["axis"], fontsize=10)
        cb.outline.set_edgecolor("#E2E8F0")
    return _finish(fig, out_path)


def draw_scatter3d(p, out_path, width_in=8.0, height_in=4.5):
    """三维散点（可按类别分组或按数值着色）。

    params: x[]/y[]/z[] + c[]（数值着色）｜ 或 groups[{label, x[], y[], z[], color}] · view · size
    """
    fig = plt.figure(figsize=(width_in, height_in))
    ax = fig.add_subplot(111, projection="3d")
    mappable = None
    if p.get("groups"):
        for i, g in enumerate(p["groups"]):
            col = _cyc(i, g.get("color"))
            ax.scatter(g.get("x", []), g.get("y", []), g.get("z", []), s=float(p.get("size", 36)),
                       color=col, edgecolor="white", linewidth=0.5, label=g.get("label", ""), depthshade=False)
        if any(g.get("label") for g in p["groups"]):
            ax.legend(loc="upper left", fontsize=9)
    else:
        c = p.get("c")
        mappable = ax.scatter(p.get("x", []), p.get("y", []), p.get("z", []), s=float(p.get("size", 36)),
                              c=c, cmap=(_soft_cmap(p.get("cmap", "blue")) if c is not None else None),
                              color=(None if c is not None else (soft(p.get("color")) if p.get("color") else SOFT_COLORS["blue"])),
                              edgecolor="white", linewidth=0.5, depthshade=False)
    _prep_3d(ax, p)
    ax.set_xlabel(p.get("xlabel", "x")); ax.set_ylabel(p.get("ylabel", "y")); ax.set_zlabel(p.get("zlabel", "z"))
    ax.set_title(p.get("title", ""), pad=10)
    if mappable is not None and p.get("colorbar", True):
        cb = fig.colorbar(mappable, ax=ax, shrink=0.62, pad=0.08)
        cb.set_label(p.get("colorbar_label", ""), color=INK["axis"], fontsize=10)
        cb.outline.set_edgecolor("#E2E8F0")
    return _finish(fig, out_path)


DRAWERS.update({
    "spectrum": draw_spectrum, "residual": draw_residual, "fit_band": draw_fit_band,
    "box_jitter": draw_box_jitter, "km": draw_km, "forest": draw_forest, "volcano": draw_volcano,
    "clustered_heatmap": draw_clustered_heatmap, "surface3d": draw_surface3d, "scatter3d": draw_scatter3d,
})


def draw_swimlane(p, out_path, width_in=8.0, height_in=4.5):
    """泳道图（跨职能流程图）：Mermaid 没有这个图型，这里用 matplotlib 原生画。

    params: lanes[{id, label, color}] · steps[{id, lane, label, col?, color?}] ·
            edges[[from, to]] · direction（'LR' 泳道横排 / 'TD' 泳道竖排）· step_width · row_height

    布局规则（确定性，不用随机）：步骤按数组顺序排成列（可用 col 指定同列并行），泳道决定行；
    连线用直角折线箭头，跨泳道时自动拐弯。
    """
    lanes = list(p.get("lanes") or [])
    steps = list(p.get("steps") or [])
    if not lanes or not steps:
        raise SystemExit("swimlane 需要 lanes[] 与 steps[]")
    lane_idx = {}
    for i, ln in enumerate(lanes):
        lane_idx[str(ln.get("id", ln.get("label", i)))] = i
    direction = str(p.get("direction", "LR")).upper()
    # 列号：显式 col 优先，否则按出现顺序递增
    col_of = []
    nxt = 0
    for st in steps:
        c = st.get("col")
        if c is None:
            c = nxt
        col_of.append(int(c))
        nxt = max(nxt, int(c) + 1)
    ncol = max(col_of) + 1 if col_of else 1
    nrow = len(lanes)
    if direction == "TD":
        nu, nv = nrow, ncol                       # 泳道当作列（u），步骤沿 v 向下
    else:
        nu, nv = ncol, nrow                       # 泳道当作行（v），步骤沿 u 向右
    fig, ax = new_fig(max(width_in, 1.05 * nu + 1.6), max(height_in, 0.72 * nv + 1.4))
    if direction == "TD":
        ax.set_xlim(-0.5, nu - 0.5); ax.set_ylim(nv - 0.5, -1.05)   # 顶部留给泳道名
    else:
        ax.set_xlim(-1.05, nu - 0.5); ax.set_ylim(nv - 0.5, -0.5)   # 左侧留给泳道名
    ax.axis("off")
    band = FILL["neutral"]
    for i, ln in enumerate(lanes):
        col = soft(ln.get("color")) if ln.get("color") else None
        fc = ("#FFFFFF" if i % 2 else band) if col is None else col
        if direction == "TD":
            ax.add_patch(Rectangle((i - 0.5, -0.5), 1.0, nv, facecolor=fc, edgecolor="#E2E8F0", linewidth=0.8))
            ax.text(i, -0.34, str(ln.get("label", "")), ha="center", va="bottom", fontsize=10.5,
                    color=INK["title"], fontweight="bold")
        else:
            ax.add_patch(Rectangle((-0.5, i - 0.5), nu, 1.0, facecolor=fc, edgecolor="#E2E8F0", linewidth=0.8))
            ax.text(-0.56, i, str(ln.get("label", "")), ha="right", va="center", fontsize=10.5,
                    color=INK["title"], fontweight="bold")
    # 步骤方块
    sw = float(p.get("step_width", 0.72))
    sh = min(0.62, float(p.get("row_height", 0.62)))
    centers = {}
    for k, st in enumerate(steps):
        li = lane_idx.get(str(st.get("lane")))
        if li is None:
            raise SystemExit("swimlane：step %r 的 lane 不在 lanes 里" % st.get("id"))
        col = soft(st.get("color")) if st.get("color") else SOFT_COLORS["blue"]
        if direction == "TD":
            u, vv = li, col_of[k]
        else:
            u, vv = col_of[k], li
        ax.add_patch(Rectangle((u - sw / 2, vv - sh / 2), sw, sh, facecolor=col, edgecolor="#FFFFFF",
                               linewidth=1.0, zorder=3))
        ax.text(u, vv, str(st.get("label", st.get("id", ""))), ha="center", va="center", fontsize=9.5,
                color=INK["text"], zorder=4)
        centers[str(st.get("id", k))] = (u, vv)
    # 连线（直角折线 + 箭头）
    for e in (p.get("edges") or []):
        if len(e) < 2:
            continue
        a, b = centers.get(str(e[0])), centers.get(str(e[1]))
        if a is None or b is None:
            continue
        same_lane = abs(a[1] - b[1]) < 1e-9
        forward = (b[0] > a[0]) if direction != "TD" else (b[1] > a[1])
        start = (a[0] + sw / 2, a[1]) if (forward and direction != "TD") else \
                ((a[0], a[1] + sh / 2) if (forward and direction == "TD") else a)
        end = (b[0] - sw / 2, b[1]) if (forward and direction != "TD") else \
              ((b[0], b[1] - sh / 2) if (forward and direction == "TD") else b)
        props = dict(arrowstyle="-|>", color=INK["tick"], linewidth=1.3, shrinkA=0, shrinkB=2)
        if not same_lane:      # 跨泳道才需要直角拐弯；同泳道直连，避免退化折线
            props["connectionstyle"] = ("angle,angleA=-90,angleB=180,rad=6" if direction == "TD"
                                        else "angle,angleA=0,angleB=90,rad=6")
        ax.annotate("", xy=end, xytext=start, arrowprops=props, zorder=2)
    ax.set_title(p.get("title", ""), pad=12)
    return _finish(fig, out_path)


DRAWERS.update({"swimlane": draw_swimlane})   # 定义在本文件末尾，注册放在最后

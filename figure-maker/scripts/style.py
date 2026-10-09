#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配图管线 v2 · 统一样式层（严格按《统一视觉规范》）

只要画 B 类数据图就必须走这里：setup_soft_style() + SOFT_COLORS + save() + check_layout()。
check_layout() 把《布局质量红线》做成**可量化检查**（量文字 bbox：重叠 / 越出画布），
结果写进 JSON，供《布局检查》表引用 —— 不靠自述打勾。
"""
import json
import os

# matplotlib 会往系统缓存写字体缓存；沙箱里常不可写 → 指到本目录下的 .mplcache（已 gitignore）
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".mplcache"))
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.text import Text

# ---- 规范色板（唯一来源，禁止 Matplotlib 默认色）----
SOFT_COLORS = {
    "blue":   "#93C5FD",
    "red":    "#F87171",
    "green":  "#86EFAC",
    "purple": "#C4B5FD",
    "orange": "#E9B08A",
    "grey":   "#9CA3AF",
    "dark":   "#4B5563",
}
# 语义填充/描边（A 类结构图用；B 类少量场景也用）
FILL = {
    "neutral":  "#F8FBFF", "root": "#E9D5FF", "category": "#DBEAFE", "leaf": "#F1F3F5",
    "input": "#FBE4D5", "output": "#D1FAE5", "warning": "#FEF3C7", "error": "#FECACA",
}
STROKE = {
    "neutral":  "#93C5FD", "root": "#C4B5FD", "category": "#93C5FD", "leaf": "#ADB5BD",
    "input": "#E9B08A", "output": "#86EFAC", "warning": "#FCD34D", "error": "#F87171",
}
INK = {"title": "#212529", "text": "#212529", "axis": "#4B5563", "tick": "#6B7280"}

# 旧 manifest 里的饱和色 → 新色板（规范：颜色只能从 SOFT_COLORS 取；数据本身不动）
LEGACY_COLOR_MAP = {
    "#10B981": "green", "#3B82F6": "blue", "#F59E0B": "orange", "#EF4444": "red",
    "#8B5CF6": "purple", "#9CA3AF": "grey", "#1F2937": "dark", "#4B5563": "dark",
    "#6B7280": "grey", "#0EA5E9": "blue", "#22C55E": "green", "#EAB308": "orange",
}


def setup_soft_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Noto Sans SC", "PingFang SC", "Microsoft YaHei", "Arial"],
        "font.size": 12,
        "figure.facecolor": "#FFFFFF",
        "axes.facecolor": "#FFFFFF",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.edgecolor": "#D1D5DB",
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.color": "#F1F3F5",
        "grid.linewidth": 0.8,
        "grid.linestyle": "--",
        "axes.axisbelow": True,
        "xtick.color": INK["tick"],
        "ytick.color": INK["tick"],
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.frameon": False,
        "legend.fontsize": 11,
        "legend.labelcolor": "#374151",
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK["title"],
        "axes.labelsize": 12,
        "axes.labelcolor": INK["axis"],
        "figure.autolayout": True,
        "mathtext.default": "regular",
        "svg.fonttype": "path",      # 文字转曲：不依赖字体、站点/端上一致
    })


def soft(which_or_hex):
    """manifest 里的颜色 → 规范色板；已是色板键则原样返回。"""
    if not which_or_hex:
        return SOFT_COLORS["blue"]
    if which_or_hex in SOFT_COLORS:
        return SOFT_COLORS[which_or_hex]
    key = LEGACY_COLOR_MAP.get(str(which_or_hex).upper())
    return SOFT_COLORS.get(key, SOFT_COLORS["blue"])


def new_fig(width_in=8.0, height_in=4.5):
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    return fig, ax


def save(fig, out_path, title=None, fmt=None, dpi=300):
    """统一保存。**格式由扩展名决定**，也可用 fmt 显式指定：
        save(fig, 'out/fig.svg')   # 矢量（默认，文字转曲）
        save(fig, 'out/fig.png')   # 位图（文档/幻灯片，dpi 可调）
        save(fig, 'out/fig.webp')  # 网页友好：内部走 PNG → Pillow（matplotlib 原生不支持 webp）
        save(fig, 'out/fig.pdf')   # 印刷
    """
    ext = (os.path.splitext(out_path)[1] or '').lstrip('.').lower()
    fmt = (fmt or ext or 'svg').lower()
    if fmt == 'jpg':
        fmt = 'jpeg'
    if fmt not in ('svg', 'png', 'pdf', 'eps', 'ps', 'jpeg', 'tif', 'tiff', 'webp'):
        raise ValueError('不支持的输出格式：%s' % fmt)
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    if fmt == 'webp':
        try:
            import io
            from PIL import Image
        except ImportError:
            raise RuntimeError('输出 webp 需要 Pillow：pip install Pillow')
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, facecolor="#FFFFFF")
        buf.seek(0)
        Image.open(buf).convert('RGB').save(out_path, 'WEBP', quality=95, method=6)
        return out_path
    fig.savefig(out_path, format=fmt, dpi=dpi, facecolor="#FFFFFF")
    return out_path


def save_as(fig, out_base, formats=('svg',), dpi=300):
    """一次输出多种格式：save_as(fig, 'out/fig', ('svg','png','webp'))"""
    return [save(fig, '%s.%s' % (out_base, f), fmt=f, dpi=dpi) for f in formats]


def _bbox_of(t, renderer):
    try:
        b = t.get_window_extent(renderer=renderer)
        inv = t.figure.transFigure.inverted()
        (x0, y0), (x1, y1) = inv.transform([[b.x0, b.y0], [b.x1, b.y1]])
        return {"x": min(x0, x1), "y": min(y0, y1), "w": abs(x1 - x0), "h": abs(y1 - y0)}
    except Exception:
        return None


def check_layout(fig, overlap_ratio=0.12, min_px=2.5):
    """机器版布局检查（B 类）：文字重叠、文字越出画布。全部在**像素空间**里算。

    ⚠️ matplotlib 的 findobj(Text) 会同时返回「真实文本」和一堆 1×1 的**占位对象**
    （每个刻度一个，extent 恒为原点附近）；不按尺寸过滤就会报出海量假重叠。
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.canvas.get_width_height()

    # 轴范围外的刻度标签（matplotlib 仍会创建对象，渲染时被裁剪）不算越界
    clipped = set()
    for a in fig.get_axes():
        if not a.axison:                      # axis('off')：整条轴的刻度/标签都不渲染，不能算越界
            for axis in (a.xaxis, a.yaxis):
                for tick in list(axis.get_major_ticks()) + list(axis.get_minor_ticks()):
                    if tick.label1 is not None:
                        clipped.add(id(tick.label1))
            continue
        for axis in (a.xaxis, a.yaxis):
            lo, hi = axis.get_view_interval()
            if hi < lo:
                lo, hi = hi, lo
            for tick in list(axis.get_major_ticks()) + list(axis.get_minor_ticks()):
                lb = tick.label1
                if lb is None:
                    continue
                if not lb.get_visible() or not (lo <= tick.get_loc() <= hi):
                    clipped.add(id(lb))          # 次刻度/轴外刻度：渲染时被裁剪，不算越界

    texts = []
    seen = set()
    for t in fig.findobj(Text):
        if not t.get_visible() or id(t) in clipped:
            continue
        s = (t.get_text() or "").strip()
        if not s:
            continue
        try:
            b = t.get_window_extent(renderer=r)
        except Exception:
            continue
        if b.width < min_px or b.height < min_px:       # 占位对象：跳过
            continue
        key = (round(b.x0, 1), round(b.y0, 1), s)
        if key in seen:
            continue
        seen.add(key)
        texts.append({"t": s[:26], "x": b.x0, "y": b.y0, "w": b.width, "h": b.height})

    overlap = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i], texts[j]
            ix = max(0.0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
            iy = max(0.0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
            inter = ix * iy
            if inter <= 0:
                continue
            ratio = inter / max(1e-9, min(a["w"] * a["h"], b["w"] * b["h"]))
            if ratio > overlap_ratio:
                overlap.append({"a": a["t"], "b": b["t"], "ratio": round(ratio, 3)})

    out = []
    for it in texts:
        if it["x"] < -min_px or it["y"] < -min_px or it["x"] + it["w"] > W + min_px or it["y"] + it["h"] > H + min_px:
            out.append({"t": it["t"], "box_px": {k: round(it[k], 1) for k in ("x", "y", "w", "h")}})

    return {"canvas_px": [W, H], "texts": len(texts), "overlap": overlap, "outOfCanvas": out}


def report_and_exit(checks, out_path):
    """把检查结果打到 stdout（末尾一行 JSON），供 run_course.py 收集。"""
    ok = not checks["overlap"] and not checks["outOfCanvas"]
    print("CHECK " + json.dumps({"out": out_path, "pass": ok, "checks": checks}, ensure_ascii=False))
    return 0 if ok else 1

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

# ---- 色板：**唯一来源在 palette.py**（纯数据 + 标准库，无 matplotlib 依赖）----
# 见 palette.py 顶部说明：把色值抽出去是为了让 --list / --recommend / --example 这些
# 不该依赖 matplotlib 的路径也能共用同一套色值（A 类骨架里的 classDef 颜色就从这里取）。
from palette import (AXIS_EDGE, EDGE_SOFT, FILL, GRID, INK, PAPER, ROLES, SOFT_COLORS,  # noqa: F401
                     STROKE, _PAPER_TINT, shade as _shade)                              # noqa: F401

# 版面常量：所有 B 类图统一用「内容紧致 + 固定留白」保存，
# 根治「贴边 / 太挤 / 一侧留白过大」（实测曾出现底部只剩 2px）。
PAD_IN = 0.12          # 紧致留白（英寸）


def role_colors(role):
    """按语义角色取 (填充色, 描边色)。角色未登记直接报错，不静默退化。"""
    slot = ROLES.get(role)
    if slot is None:
        raise SystemExit("未登记的语义角色：%s（可选：%s）" % (role, "、".join(sorted(ROLES))))
    return FILL[slot], STROKE[slot]


def palette_payload():
    """给 A 类 JS 渲染器的色板载荷（扁平：SOFT_COLORS + FILL + STROKE 带 stroke_ 前缀）。

    A 类走 render-mermaid.js，同色板原本在 JS 里另存了一份 —— 两处定义必然漂移
    （改了一边另一边没改，A/B 配色就会分裂）。现在由 draw.py 把本函数的返回值写成
    临时 JSON 传给渲染器，**Python 侧是唯一来源**；JS 内置的默认值只在脱离 draw.py
    单独调用渲染器时兜底。
    """
    d = dict(SOFT_COLORS)
    d.update(FILL)
    d.update({"stroke_" + k: v for k, v in STROKE.items()})
    d.update({"ink_" + k: v for k, v in INK.items()})
    d.update({"paper": PAPER, "grid": GRID, "edge_soft": EDGE_SOFT, "axis_edge": AXIS_EDGE})
    return d

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
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.edgecolor": AXIS_EDGE,
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.color": GRID,
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
    # 让输出**逐字节可复现**：
    #   svg.hashsalt 固定 → Matplotlib 生成的元素 id（id="m406f77eea2"）不再随机；
    #   metadata Date=None → 不再写入 <dc:date>当前时间</dc:date>。
    # 否则同一 spec 每次的 SVG 字节都不同：人眼一样，但 git diff / CI 全是噪音。
    import matplotlib as _mpl
    _mpl.rcParams['svg.hashsalt'] = 'figure-maker'
    _meta = {'Date': None}
    if fmt == 'webp':
        try:
            import io
            from PIL import Image
        except ImportError:
            raise RuntimeError('输出 webp 需要 Pillow：pip install Pillow')
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, facecolor=PAPER, metadata=_meta,
                        bbox_inches='tight', pad_inches=PAD_IN)
        buf.seek(0)
        Image.open(buf).convert('RGB').save(out_path, 'WEBP', quality=95, method=6)
        return out_path
    fig.savefig(out_path, format=fmt, dpi=dpi, facecolor=PAPER, metadata=_meta,
                    bbox_inches='tight', pad_inches=PAD_IN)
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


def missing_glyphs(text, prop=None):
    """返回字符串里**渲染时没有字形**的字符 —— 这些字符会画成"豆腐块"（□）。

    ⚠️ 必须用**文本对象自己的 FontProperties** 来判定：字体是按字符回退的，
    自己另挑一个字体（findfont(第一个家族)）会得出完全相反的结论 ——
    实测这样会把中文全判成缺字形、又漏掉真的缺字形的 ∿。
    真实踩过：PingFang SC 里 U+223F 码位存在但指向 notdef，画出来就是方框。
    """
    from matplotlib import font_manager as _fm
    from matplotlib.ft2font import FT2Font
    if prop is None:
        prop = _fm.FontProperties(family=plt.rcParams.get("font.sans-serif") or "sans-serif")
    try:
        path = _fm.findfont(prop)          # 与渲染同一条解析路径
        cmap = FT2Font(path).get_charmap()
    except Exception:                      # 解析不出来就不下结论，避免误报
        return []
    return sorted({ch for ch in str(text) if ch not in "\n\t " and not cmap.get(ord(ch), 0)})


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

    # 缺字形的字符画出来是「豆腐块」，肉眼极易漏看（实测 PingFang SC 对 U+223F 就是如此）
    glyph_bad = {}

    texts = []
    seen = set()
    for t in fig.findobj(Text):
        if not t.get_visible() or id(t) in clipped:
            continue
        s = (t.get_text() or "").strip()
        if s:
            _miss = missing_glyphs(s, t.get_fontproperties())
            if _miss:
                glyph_bad[s[:26]] = _miss
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
    degenerate = 0
    # matplotlib 3D 等场景会留下「窗口坐标在画布外上万像素」的**退化文本对象**（永远画不出来、
    # 也看不见）。这类不该算越界 —— 实测 surface3d 的两个 z 轴刻度就会以 x≈-12023 / x≈50148 出现。
    # 判据：整体偏出画布超过 1.5 个画布尺寸 → 视为退化对象，只计数不报错。
    dx, dy = W * 1.5, H * 1.5
    for it in texts:
        if (it["x"] + it["w"] < -dx or it["x"] > W + dx or it["y"] + it["h"] < -dy or it["y"] > H + dy):
            degenerate += 1
            continue
        if it["x"] < -min_px or it["y"] < -min_px or it["x"] + it["w"] > W + min_px or it["y"] + it["h"] > H + min_px:
            out.append({"t": it["t"], "box_px": {k: round(it[k], 1) for k in ("x", "y", "w", "h")}})

    return {"canvas_px": [W, H], "texts": len(texts), "overlap": overlap,
            "outOfCanvas": out, "degenerateTexts": degenerate,
              "missingGlyphs": glyph_bad}


def report_and_exit(checks, out_path):
    """把检查结果打到 stdout（末尾一行 JSON），供 run_course.py 收集。"""
    ok = not checks["overlap"] and not checks["outOfCanvas"]
    print("CHECK " + json.dumps({"out": out_path, "pass": ok, "checks": checks}, ensure_ascii=False))
    return 0 if ok else 1

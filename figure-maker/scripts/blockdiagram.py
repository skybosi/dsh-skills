"""blockdiagram.py —— 通用「块图 / 分层架构图」渲染器（B 类图型 `block_diagram`）。

**刻意不含任何模型/领域概念**，只有 5 个正交原语，任意分层/堆叠式架构都由它们组合出来：

  1. `blocks[]`  网格上的方块：形状、语义配色角色、标签；列宽/行高由内容自动推
  2. `edges[]`   正交连线：可选多箭头「喇叭」（多头/扇入）、虚线、边标签、指定进出边
  3. `rails[]`   侧边通道：跳连 / 残差这类「绕行」连接
  4. `frames[]`  分组框 + 侧标签：模块边界、重复次数标注（N×）
  5. `shape:"text"` 的 block：纯文字（如 "Inputs"、"Output Probability"）

版面**完全由内容推导**（列宽 = 该列最宽块的文字宽度，行高 = 该行最高块 + 行距），
不存在「按某张论文原图实测间距」这类常量 —— 所以换个架构不需要改一行代码。

params:
  · title        可选
  · blocks[]     每项：
        id           唯一标识（edges/rails 用它引用）
        row          行号，0 在最下
        col          列号（整数，默认 0）
        dx           可选，相对本列中心的水平偏移（单位 = 本列宽）
        span         可选，横跨几列（默认 1；共享层 / 汇总节点用）
        label        文字，`\\n` 换行
        shape        box（默认，圆角方框）| circle | ellipse | sine | text
        role         语义配色角色（style.ROLES：attention/ffn/norm/embedding/project/output/block）
        color        可选，覆盖填充色（取 SOFT_COLORS 名或 hex）
        w / h        可选，覆盖宽 / 高（单位同版面单位）
        size         可选，circle / sine / ellipse 的尺寸
        label_side   可选，sine / ellipse 的文字放哪侧：left|right|top|bottom
  · edges[]      {from, to, label?, style=solid|dashed, arrows=1, from_side?, to_side?, spread?}
  · rails[]      {side=left|right, from?, to, offset?}   from 省略则从该列最下方的块起
  · frames[]     {col=0, rows=[起行, 止行], label?, label_side=left|right|top, pad?}
"""

from __future__ import annotations

import math

from style import INK, SOFT_COLORS, new_fig, role_colors, soft

# ---- 版面单位（由内容推导；最终按内容外框定画布比例）----
LINE = 0.30        # 每行文字占高
PAD_Y = 0.16       # 盒子上下内边距
PAD_X = 0.22       # 盒子左右内边距
ROW_GAP = 0.24     # 行距
COL_GAP = 0.62     # 列距
RAIL_OFF = 0.34    # 侧边通道离块边缘的距离
FAN_H = 0.26       # 「喇叭」总线离目标块底边的距离
FS = 11.0          # 块内字号（pt）
FS_SMALL = 9.2     # 边标签 / 侧标签
FS_TITLE = 12.5    # 标题
LW_BOX = 1.5
LW_EDGE = 1.3
EDGE_C = INK["axis"]
TEXT_C = INK["text"]


def _n_lines(label) -> int:
    return str(label).count("\n") + 1


def _sine_glyph(ax, cx, cy, r, color):
    """波形图标（振荡 / 信号 / 位置编码这类「连续量」的通用画法）。"""
    import numpy as np
    t = np.linspace(0.0, 1.0, 80)
    ax.plot(cx + (t - 0.5) * 2 * r * 0.86, cy + np.sin(t * 2 * math.pi) * r * 0.62,
            color=color, linewidth=1.7, solid_capstyle="round", zorder=4)


def render_block_diagram(p, out_path, width_in=8.0, finish=None, text_px=None):
    """绘制通用块图。`finish` / `text_px` 由 drawers.py 注入（避免循环导入）。"""
    from matplotlib.patches import Circle, Ellipse, FancyBboxPatch

    blocks = [dict(b) for b in (p.get("blocks") or [])]
    if not blocks:
        raise SystemExit("block_diagram：params.blocks 不能为空")
    if text_px is None:                      # 独立调用时的兜底（口径同 drawers._text_px）
        def text_px(t, fs=FS):
            return sum(14.0 if ord(c) > 0x2E80 else 7.6 for c in str(t)) * (fs / 12.0)

    by_id = {}
    for b in blocks:
        if b.get("id"):
            if b["id"] in by_id:
                raise SystemExit("block_diagram：block id 重复：%s" % b["id"])
            by_id[b["id"]] = b

    def _w_of(b):
        if b.get("w"):
            return float(b["w"])
        if b.get("shape") in ("circle", "sine"):
            return float(b.get("size", 0.62))
        if b.get("shape") == "ellipse":
            return float(b.get("size", 0.92))
        lines = str(b.get("label", "")).split("\n")
        return max(text_px(ln, FS) for ln in lines) / 100.0 + PAD_X * 2

    def _h_of(b):
        if b.get("h"):
            return float(b["h"])
        if b.get("shape") in ("circle", "sine"):
            return float(b.get("size", 0.62))
        if b.get("shape") == "ellipse":
            return float(b.get("size", 0.92)) * 0.72
        if b.get("shape") == "text":
            return LINE * _n_lines(b.get("label", ""))
        return PAD_Y * 2 + LINE * _n_lines(b.get("label", ""))

    # ---- 行：自下而上；行高 = 该行最高块 ----
    rows = {}
    for b in blocks:
        rows.setdefault(int(b.get("row", 0)), []).append(b)
    nrow = max(rows) + 1
    row_h = {r: max(_h_of(b) for b in bs) for r, bs in rows.items()}
    yc, y_cursor = {}, 0.0
    for r in range(nrow):
        h = row_h.get(r, PAD_Y * 2 + LINE)
        yc[r] = y_cursor + h / 2.0
        y_cursor += h + ROW_GAP
    content_h = y_cursor - ROW_GAP

    # ---- 列：列宽 = 该列最宽块（圆圈 / 波形这类小图元不参与定宽，避免把列撑开）----
    col_ids = sorted({int(b.get("col", 0)) for b in blocks})
    col_w = {}
    for c in col_ids:
        in_col = [b for b in blocks if int(b.get("col", 0)) == c and int(b.get("span", 1)) == 1]
        if not in_col:                      # 该列只有跨列块：给一个最小宽度兜底
            in_col = [b for b in blocks if int(b.get("col", 0)) == c] or [{"label": ""}]
        wide = [b for b in in_col if b.get("shape") not in ("circle", "sine", "ellipse")]
        col_w[c] = max([_w_of(b) for b in (wide or in_col)])
    xc, x_cursor = {}, 0.0
    for c in col_ids:
        xc[c] = x_cursor + col_w[c] / 2.0
        x_cursor += col_w[c] + COL_GAP
    content_w = x_cursor - COL_GAP

    # ---- 每个块的实际方框 ----
    pos = {}
    for b in blocks:
        c, r = int(b.get("col", 0)), int(b.get("row", 0))
        span = max(1, int(b.get("span", 1)))
        if span > 1:                        # 横跨多列：宽度 = 首列左缘到末列右缘
            c2 = min(max(col_ids), c + span - 1)
            bx0 = xc[c] - col_w[c] / 2
            bx1 = xc[c2] + col_w[c2] / 2
            w, cx = bx1 - bx0, (bx0 + bx1) / 2
        else:
            w = _w_of(b) if b.get("shape") in ("circle", "sine", "ellipse") else col_w[c]
            cx = xc[c] + float(b.get("dx", 0.0)) * col_w[c]
        h = _h_of(b)
        cy = yc[r]
        pos[id(b)] = {"x0": cx - w / 2, "x1": cx + w / 2, "y0": cy - h / 2, "y1": cy + h / 2,
                      "cx": cx, "cy": cy, "w": w, "h": h}

    def box_of(ref):
        b = by_id.get(ref)
        if b is None:
            raise SystemExit("block_diagram：引用了不存在的 block id：%s" % ref)
        return pos[id(b)]

    fig_h = content_h + 0.5 + (0.55 if p.get("title") else 0.0)
    fig, ax = new_fig(width_in, width_in * fig_h / (content_w + 0.5))
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
    ax.set_xlim(-0.25, content_w + 0.25)      # 粗估范围：仅仅为了让 transData 先可用
    ax.set_ylim(-0.25, fig_h - 0.25)
    ax.set_aspect("equal")
    ax.axis("off")

    def arrow(x0, y0, x1, y1, dashed=False):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=EDGE_C, linewidth=LW_EDGE,
                                    shrinkA=0, shrinkB=0, zorder=2,
                                    linestyle=(0, (4, 3)) if dashed else "solid"))

    def line(x0, y0, x1, y1, dashed=False):
        ax.plot([x0, x1], [y0, y1], color=EDGE_C, linewidth=LW_EDGE, zorder=2,
                linestyle=(0, (4, 3)) if dashed else "solid", solid_capstyle="round")

    # ---- 分组框（先画，压在块下面）----
    for fr in (p.get("frames") or []):
        c = int(fr.get("col", 0))
        r0, r1 = int(fr.get("rows", [0, nrow - 1])[0]), int(fr.get("rows", [0, nrow - 1])[1])
        pad = float(fr.get("pad", 0.22))
        fw = col_w[c] + pad * 2
        fx0, fx1 = xc[c] - fw / 2, xc[c] + fw / 2
        fy0 = yc[r0] - row_h[r0] / 2 - pad
        fy1 = yc[r1] + row_h[r1] / 2 + pad
        ax.add_patch(FancyBboxPatch((fx0, fy0), fx1 - fx0, fy1 - fy0,
                                    boxstyle="round,pad=0,rounding_size=0.10",
                                    facecolor=SOFT_COLORS["grey"], alpha=0.18,
                                    edgecolor=INK["axis"], linewidth=1.2, zorder=0.5))
        if fr.get("label"):
            side = str(fr.get("label_side", "left"))
            # 该列若在同一侧有侧通道，标签要放到通道**外侧**（否则压线）
            rail_xs = []
            for rl in (p.get("rails") or []):
                if str(rl.get("side", "left")) != side or not rl.get("to"):
                    continue
                tb = by_id.get(rl["to"])
                if tb is None or int(tb.get("col", 0)) != c:
                    continue
                off = float(rl.get("offset", RAIL_OFF))
                rail_xs.append(xc[c] - col_w[c] / 2 - off if side == "left" else xc[c] + col_w[c] / 2 + off)
            if rail_xs:
                edge = min(rail_xs) if side == "left" else max(rail_xs)
                tx = edge - 0.22 if side == "left" else edge + 0.22
            else:
                tx = fx0 - 0.46 if side == "left" else (fx1 + 0.46 if side == "right" else xc[c])
            ty = (fy0 + fy1) / 2.0 if side in ("left", "right") else fy1 + 0.14
            ha = {"left": "right", "right": "left"}.get(side, "center")
            ax.text(tx, ty, str(fr["label"]), ha=ha, va="center",
                    fontsize=FS_SMALL, color=TEXT_C, zorder=4)

    # ---- 连线 ----
    for e in (p.get("edges") or []):
        a, b = box_of(e["from"]), box_of(e["to"])
        dashed = str(e.get("style", "solid")).lower() == "dashed"
        fs_ = str(e.get("from_side", "")) or None
        ts_ = str(e.get("to_side", "")) or None
        n_arrow = max(1, int(e.get("arrows", 1)))
        spread = float(e.get("spread", min(0.42, b["w"] * 0.30)))
        same_col = abs(a["cx"] - b["cx"]) < 1e-6
        same_row = abs(a["cy"] - b["cy"]) < 1e-6
        # 同行水平直连（⊕ 与位置编码、并列模块之间这类）
        if same_row and float(b.get("dx", 0)) != float(a.get("dx", 0)):
            if b["cx"] > a["cx"]:
                arrow(a["x1"], a["cy"], b["x0"], b["cy"], dashed)
            else:
                arrow(a["x0"], a["cy"], b["x1"], b["cy"], dashed)
            continue
        # 起点
        if fs_ == "right":
            x0, y0 = a["x1"], a["cy"]
        elif fs_ == "left":
            x0, y0 = a["x0"], a["cy"]
        elif fs_ == "bottom":
            x0, y0 = a["cx"], a["y0"]
        else:
            x0, y0 = a["cx"], a["y1"]
        # 终点：侧向进入。跨列时必须**绕到目标列的外侧**再进去 ——
        # 直接在本列中心下降会穿过本列自己的方块（实测编码器→解码器那条线就穿了一整块）。
        if ts_ in ("left", "right"):
            ex = b["x0"] if ts_ == "left" else b["x1"]
            if abs(a["cx"] - b["cx"]) > 1e-6:
                ch = ex - 0.36 if ts_ == "left" else ex + 0.36
                y_route = max(a["y1"], b["cy"]) + 0.30
                line(x0, y0, x0, y_route)
                line(x0, y_route, ch, y_route)
                line(ch, y_route, ch, b["cy"])
                arrow(ch, b["cy"], ex, b["cy"], dashed)
            else:
                line(x0, y0, x0, b["cy"])
                arrow(x0, b["cy"], ex, b["cy"], dashed)
            continue
        if ts_ == "top":
            line(x0, y0, b["cx"], y0)
            arrow(b["cx"], y0, b["cx"], b["y1"], dashed)
            continue
        # 终点：默认进入底边（目标在下则进入顶边）
        up = b["y0"] >= y0
        if not same_col:
            y_route = (b["y0"] - 0.30) if up else (b["y1"] + 0.30)
            line(x0, y0, x0, y_route)
            line(x0, y_route, b["cx"], y_route)
            x0, y0 = b["cx"], y_route
        end_y = b["y0"] if up else b["y1"]
        # 汇入点：源列位置落在目标块横向范围内时就从那儿进（多路扇入时不会挤在中心一个点），
        # 否则仍进中心 —— 普通块不受影响（源列 x 一定在它范围之外）。
        x_end = x0 if (b["x0"] + 0.15 <= x0 <= b["x1"] - 0.15) else b["cx"]
        if n_arrow > 1:
            bus_y = end_y - FAN_H if up else end_y + FAN_H
            line(x0, y0, x0, bus_y)
            offs = [(-spread + 2 * spread * i / (n_arrow - 1)) for i in range(n_arrow)]
            line(x0 + min(offs), bus_y, x0 + max(offs), bus_y)
            for o in offs:
                arrow(x0 + o, bus_y, x0 + o, end_y, dashed)
        else:
            arrow(x0, y0, x0 if same_col else x_end, end_y, dashed)
        if e.get("label"):
            ly = (y0 + end_y) / 2.0
            lx = x0 + 0.10 if same_col else (x0 + x_end) / 2.0
            ax.text(lx, ly, str(e["label"]), ha="center", va="center", fontsize=FS_SMALL,
                    color=TEXT_C, zorder=4,
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.92))

    # ---- 侧边通道（跳连 / 残差）----
    for rl in (p.get("rails") or []):
        tgt = box_of(rl["to"])
        side = str(rl.get("side", "left"))
        c = int(by_id[rl["to"]].get("col", 0))
        rx = (xc[c] - col_w[c] / 2 - float(rl.get("offset", RAIL_OFF))) if side == "left" \
            else (xc[c] + col_w[c] / 2 + float(rl.get("offset", RAIL_OFF)))
        if rl.get("from"):
            src = box_of(rl["from"])
            line(src["x0"] if side == "left" else src["x1"], src["cy"], rx, src["cy"])
            y_from = src["cy"]
        else:                                   # 没给起点：从该列最下方的块底边起
            c0 = [b for b in blocks if int(b.get("col", 0)) == c]
            lowest = min(c0, key=lambda b: pos[id(b)]["y0"])
            y_from = pos[id(lowest)]["y0"] - 0.30
        line(rx, y_from, rx, tgt["cy"])
        arrow(rx, tgt["cy"], tgt["x0"] if side == "left" else tgt["x1"], tgt["cy"])

    # ---- 方块本体 ----
    for b in blocks:
        g = pos[id(b)]
        shape = str(b.get("shape", "box"))
        fill, stroke = role_colors(b["role"]) if b.get("role") else (SOFT_COLORS["blue"], INK["axis"])
        if b.get("color"):
            fill = soft(b["color"])
        if shape == "text":
            ax.text(g["cx"], g["cy"], str(b.get("label", "")), ha="center", va="center",
                    fontsize=FS, color=TEXT_C, zorder=4, linespacing=1.35)
        elif shape in ("circle", "sine"):
            ax.add_patch(Circle((g["cx"], g["cy"]), g["w"] / 2, facecolor=fill,
                                edgecolor=stroke, linewidth=LW_BOX, zorder=3))
            if shape == "sine":
                _sine_glyph(ax, g["cx"], g["cy"], g["w"] / 2 * 0.62, stroke)
            else:
                ax.text(g["cx"], g["cy"], str(b.get("label", "")), ha="center", va="center",
                        fontsize=FS + 1.5, color=TEXT_C, zorder=4)
        elif shape == "ellipse":
            ax.add_patch(Ellipse((g["cx"], g["cy"]), g["w"], g["h"], facecolor=fill,
                                 edgecolor=stroke, linewidth=LW_BOX, zorder=3))
        else:
            ax.add_patch(FancyBboxPatch((g["x0"], g["y0"]), g["w"], g["h"],
                                        boxstyle="round,pad=0,rounding_size=0.09",
                                        facecolor=fill, edgecolor=stroke,
                                        linewidth=LW_BOX, zorder=3))
            ax.text(g["cx"], g["cy"], str(b.get("label", "")), ha="center", va="center",
                    fontsize=FS, color=TEXT_C, zorder=4, linespacing=1.35)
        # 小图元的文字放侧边（放里面会压到图形上）
        if b.get("label") and shape in ("sine", "ellipse"):
            side = str(b.get("label_side", "left"))
            tx = g["x0"] - 0.08 if side == "left" else (g["x1"] + 0.08 if side == "right" else g["cx"])
            ha = {"left": "right", "right": "left"}.get(side, "center")
            if side in ("left", "right"):
                ty, va = g["cy"], "center"
            else:
                ty = g["y0"] - 0.08 if side == "bottom" else g["y1"] + 0.08
                va = "top" if side == "bottom" else "bottom"
            ax.text(tx, ty, str(b["label"]), ha=ha, va=va, fontsize=FS_SMALL,
                    color=TEXT_C, zorder=4, linespacing=1.3)

    if p.get("title"):
        # 标题比图宽时折成两行：否则画布宽度被标题主导，高窄的架构图会被压成一团
        ttl = str(p["title"])
        if text_px(ttl, FS_TITLE) / 100.0 > content_w * 1.15 and "\n" not in ttl:
            seps = [" · ", " ｜ ", " | ", "：", ": ", "，", "（", "(", " "]
            mid, cut = len(ttl) // 2, None
            for sep in seps:
                i = ttl.find(sep, max(0, mid - 12))
                if i > 0:
                    cut = (i, len(sep)); break
            if cut:
                ttl = ttl[:cut[0]].rstrip() + "\n" + ttl[cut[0] + cut[1]:].lstrip()
        ax.text(content_w / 2, fig_h - 0.26 + (0.0 if "\n" not in ttl else 0.16), ttl,
                ha="center", va="center", fontsize=FS_TITLE, fontweight="bold",
                color=INK["title"], zorder=5, linespacing=1.4)

    # ---- 量一次**真实外框**（含所有文字/侧标签/通道），据此定画布 ----
    #  不这么做的话，侧边通道与侧标签会落在坐标范围之外被裁掉（文字宽度事先算不准）。
    fig.canvas.draw()
    inv = ax.transData.inverted()
    ex0 = ey0 = float("inf")
    ex1 = ey1 = float("-inf")
    renderer = fig.canvas.get_renderer()
    for art in ax.get_children():
        if not art.get_visible():
            continue
        # 坐标区自己的背景 patch / 四边框铺满整个 axes，不是「内容」，必须排除 ——
        # 否则量出来的外框恒等于画布本身（实测把高度从 11.8 撑到 12.6，图被压成一团）。
        if art is getattr(ax, "patch", None) or type(art).__name__ == "Spine":
            continue
        try:
            bb = art.get_window_extent(renderer)
        except Exception:
            continue
        if bb.width <= 0 or bb.height <= 0:
            continue
        (bx0, by0), (bx1, by1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
        ex0, ey0 = min(ex0, bx0), min(ey0, by0)
        ex1, ey1 = max(ex1, bx1), max(ey1, by1)
    M = 0.20
    span_w, span_h = (ex1 - ex0) + 2 * M, (ey1 - ey0) + 2 * M
    ax.set_xlim(ex0 - M, ex1 + M)
    ax.set_ylim(ey0 - M, ey1 + M)
    fig.set_size_inches(width_in, width_in * span_h / span_w)

    return finish(fig, out_path)

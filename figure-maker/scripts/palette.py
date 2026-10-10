"""palette.py —— 色板**唯一来源**（纯数据 + 标准库；**不依赖 matplotlib**）。

为什么单独一个模块：`--list` / `--recommend` / `--example` 这些**不该依赖 matplotlib** 的路径
也要用到同一套色值（例如 A 类骨架 mmd 里的 `classDef` 颜色）。以前那些地方只能把 hex 复制一份，
改色板时必然漂移；现在所有色值只在**这一个文件**里出现：

    style.py    → 从这里取（B 类绘图、A 类主题载荷 palette_payload()）
    catalog.py  → 从这里取（A 类骨架 mmd 的 classDef 颜色）
    render-mermaid.js → 运行时通过 --palette 接收同一份（JS 里的默认值只是脱离管线时的兜底）

色系取自 Vaswani et al. 2017《Attention Is All You Need》Figure 1 原图；论文只有「淡色填充」一层，
本 skill 需要两层（FILL = 大面积填充 / SOFT_COLORS = 描边与系列色），故由淡色按 HLS 明度压暗一档派生。
"""
import colorsys


def shade(hex_color, l_factor=0.84):
    """同色系压暗一档，派生「描边 / 系列色」层。"""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    r2, g2, b2 = colorsys.hls_to_rgb(hh, max(0.0, min(1.0, ll * l_factor)), ss)
    return "#%02X%02X%02X" % (round(r2 * 255), round(g2 * 255), round(b2 * 255))


# 论文原图实测的淡色（SOFT_COLORS 与 FILL 都从这里取）
_PAPER_TINT = {
    "blue":   "#C2E8F7",   # Feed Forward 天蓝
    "green":  "#CCE7CF",   # Softmax 淡绿
    "orange": "#FFE2BB",   # Multi-Head Attention 蜜桃橙
    "purple": "#FCE0E1",   # Embedding 粉
}

SOFT_COLORS = {k: shade(v) for k, v in _PAPER_TINT.items()}
SOFT_COLORS.update({
    "red":    "#F87171",   # 论文色板无红，保留原值承担「错误 / 告警」语义
    "grey":   "#9CA3AF",   # 论文色板无「中性系列灰」这一角色，保留原值
    "dark":   "#4B5563",   # 无对应色，保留
})

# 语义填充 / 描边。论文原图统一是「淡色填充 + 深色描边」，故 STROKE 走深色而非同色系深一号。
FILL = {
    "neutral":  "#F8FBFF", "root": _PAPER_TINT["purple"], "category": _PAPER_TINT["blue"],
    "leaf": "#F3F3F4", "input": _PAPER_TINT["orange"], "output": _PAPER_TINT["green"],
    "warning": "#F2F4C1", "error": "#FECACA",
    "muted": "#D0D4E2",       # 论文「Linear」淡紫灰：比 leaf 更冷一档的中性填充
}
STROKE = {
    "neutral":  "#212529", "root": "#212529", "category": "#212529", "leaf": "#212529",
    "input": "#212529", "output": "#212529", "warning": "#212529", "error": "#F87171",
    "muted": "#212529",
}
INK = {"title": "#212529", "text": "#212529", "axis": "#4B5563", "tick": "#6B7280"}

# 非语义的中性色（也必须有唯一来源：以前散落在 drawers.py / render-mermaid.js 里当字面量）
PAPER = "#FFFFFF"        # 画布 / 描边留白（节点外描边、色块间隙）
GRID = "#F1F3F5"         # 极浅虚线网格
EDGE_SOFT = "#E2E8F0"    # 浅边框（分组框、色条轮廓、分隔线）
AXIS_EDGE = "#D1D5DB"    # 坐标轴线 / 外框

# 语义角色 → FILL / STROKE 槽位。这一层只做映射，**不新增任何色值**：
# 同一语义角色在所有结构图里必须同色。新增结构图时先在这里登记角色，不要在 drawer 里内联 hex。
ROLES = {
    "attention": "input",      # 注意力类子层
    "ffn":       "category",   # 前馈 / 变换类子层
    "norm":      "warning",    # 归一化、残差合并等粘合操作
    "embedding": "root",       # 嵌入 / 查表层
    "project":   "muted",      # 线性投影等中性组件（论文用淡紫灰）
    "output":    "output",     # 输出分布 / Softmax
    "block":     "leaf",       # 容器 / 背景框
}

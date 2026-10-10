#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""catalog.py —— 图型目录与**选型路由**的唯一来源（single source of truth）

为什么需要它：图型一多，「选哪张图」就成了比「怎么画」更大的问题。这里把 70+ 个图型
按**场景分类**组织，并给每个图型配上中文/英文关键词，于是：

  python3 draw.py --list                    # 按分类列出图型（不再是一张 70 行平铺清单）
  python3 draw.py --recommend "画接口调用顺序"   # 按描述打分，推荐最合适的图型 + 可跑骨架
  python3 draw.py --catalog --json           # 机器可读目录（给 agent 做选型）

参数键不手写：`params_of()` 直接从 drawers.py 源码里抽 `p.get("…")`，避免文档与实现漂移。
"""
import os
import re

from palette import FILL as _FILL, INK as _INK   # 骨架 mmd 的颜色也走同一色板（无 matplotlib 依赖）

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 场景分类：id / 类(A|B) / 名称 / 什么时候用 / 该类的通用关键词
# ---------------------------------------------------------------------------
CATEGORIES = [
    ("flow",        "A/B", "流程与决策",     "业务流程、算法流程、判定分支与回退",     ["流程图", "流程", "判定", "分支", "审批", "步骤", "flowchart"]),
    ("interaction", "A", "交互与时序",     "接口调用顺序、消息交互、上下游协作",     ["时序图", "调用链", "交互", "消息", "顺序", "sequence"]),
    ("state",       "A", "状态与生命周期", "订单/任务/连接的状态迁移",               ["状态机", "状态", "迁移", "生命周期", "state"]),
    ("model",       "A", "数据与领域模型", "ER 关系图、类图、业务关系图",            ["ER", "关系图", "数据模型", "类图", "领域模型", "业务关系", "实体"]),
    ("arch",        "A", "架构与上下文",   "系统架构、分层、部署、C4 上下文",        ["架构图", "架构", "分层", "部署", "上下文", "C4", "系统图"]),
    ("plan",        "A", "计划与协作",     "排期、看板、旅程、需求、里程碑、分支流",  ["甘特", "排期", "看板", "旅程", "需求", "里程碑", "时间线", "思维导图", "git"]),
    ("compare",     "B", "对比与构成",     "类目之间比大小、构成占比、增量分解",     ["对比", "比较", "排名", "占比", "构成", "柱状图", "饼图", "雷达", "瀑布"]),
    ("trend",       "B", "趋势与曲线",     "随自变量变化、多 run 均值±波动、指标曲线", ["趋势", "曲线", "折线", "变化", "收敛", "损失", "误差棒", "谱图"]),
    ("dist",        "B", "分布与统计",     "分布形态、分位数、经验分布、离散概率",   ["分布", "直方图", "密度", "箱线", "小提琴", "分位数", "CDF"]),
    ("relate",      "B", "相关与拟合",     "两变量关系、拟合、残差、相关性矩阵",     ["散点", "相关", "拟合", "回归", "残差", "预测", "parity"]),
    ("field",       "B", "场与矩阵",       "热力图、混淆矩阵、张量、网络结构、等高线、3D 曲面", ["热力图", "矩阵", "混淆", "张量", "网络结构", "等高线", "曲面", "3D", "注意力"]),
    ("eval",        "B", "评估与性能",     "模型质量与工程性能（ROC/校准/火焰图）",  ["评估", "ROC", "AUC", "校准", "性能", "火焰图", "roofline", "加速比"]),
    ("math",        "B", "优化与几何",     "梯度下降、切线/极限、向量与微分示意",     ["梯度", "优化", "切线", "极限", "微分", "向量", "几何"]),
    ("bio",         "B", "生医与统计推断", "生存曲线、森林图、火山图、组学热图",     ["生存", "KM", "森林图", "效应量", "火山图", "组学", "临床"]),
]

# ---------------------------------------------------------------------------
# A 类：**图族**而不是「6 个入口名」。列的是 Mermaid 图族 → 该图族用哪个 type 名 + 起手骨架。
# （6 个 A 类入口名彼此等价，所以骨架里统一给一个能跑的名字。）
# 条目：(spec_type, mermaid 关键字, 分类, 场景说明, 关键词, 起手 mmd)
# ---------------------------------------------------------------------------
A_FAMILIES = [
    ("flow", "flowchart", "flow", "业务流程 / 算法流程 / 判定与回退（最通用）",
     ["流程", "流程图", "判定", "分支", "算法", "步骤", "swimlane"],
     "flowchart TD\n  A[输入] --> B{判断}\n  B -->|是| C[处理]\n  B -->|否| D[回退]\n  D --> B\n  C --> E[结束]"),
    ("graph", "flowchart", "model", "关系网络 / 拓扑（无方向的连接关系）",
     ["关系图", "网络图", "拓扑图", "依赖图", "关系网络"],
     "flowchart LR\n  A[节点 A] --- B[节点 B]\n  B --- C[节点 C]\n  A --- C"),
    ("flow", "sequenceDiagram", "interaction", "接口调用链 / 消息时序（含 alt 分支、Note、激活块）",
     ["时序图", "调用链", "交互", "接口", "消息", "sequence"],
     "sequenceDiagram\n  autonumber\n  participant C as 客户端\n  participant G as 网关\n  participant S as 服务\n  C->>G: 请求\n  G->>S: 转发\n  alt 命中缓存\n    S-->>G: 缓存结果\n  else 未命中\n    S-->>G: 回源结果\n  end\n  G-->>C: 响应\n  Note over S: 兜底逻辑"),
    ("flow", "stateDiagram-v2", "state", "状态机 / 状态迁移（支持复合状态与 note）",
     ["状态机", "状态", "迁移", "生命周期", "工单", "订单状态"],
     "stateDiagram-v2\n  [*] --> 待处理\n  待处理 --> 处理中: 开始\n  待处理 --> 已取消: 超时\n  处理中 --> 已完成: 结束\n  已完成 --> [*]\n  note right of 待处理: 超时由定时任务触发"),
    ("flow", "erDiagram", "model", "ER 图 / 数据模型 / 业务实体关系（含主外键与基数）",
     ["ER", "ER图", "数据模型", "表关系", "实体", "业务关系", "基数"],
     "erDiagram\n  USER ||--o{ ORDER : places\n  ORDER ||--|{ ORDER_ITEM : contains\n  USER {\n    string id PK\n    string name\n  }\n  ORDER {\n    string id PK\n    string user_id FK\n  }"),
    ("flow", "classDiagram", "model", "类图 / 领域模型（属性、方法、多重度、依赖）",
     ["类图", "领域模型", "对象", "类", "继承", "多重度"],
     "classDiagram\n  class Order {\n    +String id\n    +pay() bool\n  }\n  class OrderItem {\n    +String sku\n    +int qty\n  }\n  Order \"1\" *-- \"n\" OrderItem"),
    ("flow", "architecture-beta", "arch", "图标化系统架构图（组件/部署，带云图标）",
     ["架构图", "图标化", "组件图", "部署图", "云架构"],
     "architecture-beta\n  group api(cloud)[接入层]\n  service gw(server)[网关] in api\n  service svc(server)[服务] in api\n  service db(database)[数据库]\n  gw:R -- L:svc\n  svc:R -- L:db"),
    ("flow", "C4Context", "arch", "C4 上下文/容器图（人-系统-外部系统关系）",
     ["C4", "上下文图", "系统上下文", "外部系统"],
     "C4Context\n  title 系统上下文\n  Person(user, \"用户\", \"说明\")\n  System(sys, \"本系统\", \"说明\")\n  System_Ext(ext, \"外部系统\", \"说明\")\n  Rel(user, sys, \"使用\")\n  Rel(sys, ext, \"调用\")"),
    ("flow", "flowchart", "arch", "C4 风格架构图（人/本系统/外部系统 + 关系，用 flowchart 复刻，比 C4Context 可控）",
     ["C4 架构图", "C4 上下文图", "C4", "上下文图", "系统上下文", "外部系统", "架构上下文"],
     "flowchart LR\n  U([用户]) --> S[本系统]\n  S --> E1[外部系统 A]\n  S --> E2[外部系统 B]\n"
     "  classDef person fill:%s,stroke:%s,stroke-width:1.5px,color:%s,rx:6,ry:6;\n"
     "  classDef sys fill:%s,stroke:%s,stroke-width:1.5px,color:%s,rx:6,ry:6;\n"
     "  classDef ext fill:%s,stroke:%s,stroke-width:1.5px,color:%s,rx:6,ry:6;\n"
     "  class U person;\n  class S sys;\n  class E1,E2 ext;" % (
         _FILL["input"], _INK["text"], _INK["text"],
         _FILL["category"], _INK["text"], _INK["text"],
         _FILL["leaf"], _INK["text"], _INK["text"])),
    ("flow", "flowchart", "arch", "分层架构图（subgraph 当泳道/分层，最稳的架构画法）",
     ["分层架构", "分层图", "泳道", "子系统", "模块图"],
     "flowchart LR\n  subgraph 接入层\n    LB[负载均衡] --> GW[网关]\n  end\n  subgraph 服务层\n    OS[订单服务] --> PS[支付服务]\n  end\n  subgraph 存储层\n    DB[(MySQL)]\n    RD[(Redis)]\n  end\n  GW --> OS\n  OS --> DB\n  OS --> RD"),
    ("flow", "gantt", "plan", "排期 / 甘特图（依赖、里程碑、进度状态）",
     ["甘特", "排期", "进度", "里程碑", "gantt"],
     "gantt\n  title 迭代排期\n  dateFormat YYYY-MM-DD\n  section 设计\n    需求评审 :done, a1, 2026-01-05, 2d\n  section 开发\n    接口实现 :active, a2, after a1, 5d\n  section 发布\n    灰度 :milestone, after a2, 0d"),
    ("flow", "kanban", "plan", "看板（待办/进行中/已完成）",
     ["看板", "任务板", "kanban", "待办"],
     "kanban\n  待办\n    [任务 A]\n  进行中\n    [任务 B]\n  已完成\n    [任务 C]"),
    ("flow", "journey", "plan", "用户旅程 / 体验地图（分阶段 + 评分）",
     ["旅程", "体验", "用户旅程", "journey"],
     "journey\n  title 用户旅程\n  section 浏览\n    进入首页: 5: 用户\n  section 下单\n    提交订单: 3: 用户, 系统"),
    ("flow", "requirementDiagram", "plan", "需求与验证追踪（需求-元素-验证方法）",
     ["需求", "需求追踪", "验证", "requirement"],
     "requirementDiagram\n  requirement req1 {\n    id: 1\n    text: \"同一订单只生效一次\"\n    risk: high\n    verifymethod: test\n  }\n  element svc {\n    type: service\n  }\n  svc - satisfies -> req1"),
    ("timeline", "timeline", "plan", "时间线 / 演进史 / 里程碑脉络",
     ["时间线", "演进", "历史", "里程碑", "timeline"],
     "timeline\n  title 系统演进\n  2024 : 单体上线\n  2025 : 拆分服务\n       : 引入缓存\n  2026 : 全链路灰度"),
    ("flow", "mindmap", "plan", "思维导图 / 能力拆解",
     ["思维导图", "脑图", "拆解", "mindmap"],
     "mindmap\n  root((主题))\n    分支一\n      子项 A\n      子项 B\n    分支二\n      子项 C"),
    ("flow", "gitGraph", "plan", "Git 分支与合并流（发布/热修流程）",
     ["git", "分支", "合并", "发布流", "gitflow"],
     "gitGraph\n  commit id: \"init\"\n  branch develop\n  commit id: \"feat\"\n  checkout main\n  merge develop tag: \"v1.0.0\""),
    ("flow", "block-beta", "plan", "块图（矩阵式布局，适合分层/分组摆放）",
     ["块图", "布局", "block"],
     "block-beta\n  columns 3\n  A[\"A\"] B[\"B\"] C[\"C\"]\n  D[\"D\"] E[\"E\"] F[\"F\"]"),
    ("flow", "packet-beta", "plan", "协议/报文结构（字段位宽）",
     ["协议", "报文", "字段", "位宽", "packet"],
     "packet-beta\n  0-15: \"源端口\"\n  16-31: \"目的端口\"\n  32-63: \"序列号\""),
    ("flow", "pie", "plan", "饼图（Mermaid 版，占比）",
     ["饼图", "占比", "pie"],
     "pie showData\n  title 占比\n  \"A\" : 45\n  \"B\" : 30\n  \"C\" : 25"),
    ("flow", "quadrantChart", "plan", "四象限优先级（成本×收益、影响×难度）",
     ["象限", "优先级", "四象限", "quadrant"],
     "quadrantChart\n  title 优先级\n  x-axis 成本低 --> 成本高\n  y-axis 影响小 --> 影响大\n  quadrant-1 尽快做\n  quadrant-2 排期做\n  quadrant-3 有空再说\n  quadrant-4 别做\n  事项 A: [0.25, 0.85]\n  事项 B: [0.8, 0.4]"),
    ("flow", "xychart-beta", "plan", "简单柱+线指标图（Mermaid 版，轻量）",
     ["指标", "柱线", "xychart", "趋势图"],
     "xychart-beta\n  title \"P99 延迟 (ms)\"\n  x-axis [v1.0, v1.1, v1.2]\n  y-axis \"P99\" 0 --> 400\n  bar [320, 210, 150]\n  line [320, 210, 150]"),
    ("flow", "sankey-beta", "plan", "流量/去向归因（桑基图）",
     ["桑基", "流量", "归因", "sankey"],
     "sankey-beta\n\nRequest,CacheHit,620\nRequest,Origin,380\nOrigin,SlowQuery,90\nOrigin,FastQuery,290"),
    ("flow", "treemap-beta", "plan", "树图 / 面积占比（层级构成）",
     ["树图", "treemap", "面积"],
     "treemap-beta\n\"根\"\n    \"A\": 30\n    \"B\": 20\n    \"C\": 50"),
    ("flow", "radar-beta", "plan", "雷达图（Mermaid 版，多指标对比）",
     ["雷达", "多指标", "radar"],
     "radar-beta\n  title 健康度\n  axis a[\"错误率\"], b[\"延迟\"], c[\"吞吐\"]\n  curve s1[\"改造前\"]{80, 70, 60}\n  curve s2[\"改造后\"]{40, 35, 90}"),

    # —— 以下 3 个图族此前**有 spec 与样例、却没登记进目录**（用户/模型发现不了），本次补登 ——
    ("flow", "flowchart", "flow", "优先级 / 依赖阶梯（自上而下逐级递减）",
     ["优先级", "阶梯", "依赖顺序", "运算符", "逐级递减"],
     "flowchart TD\n  A[\"① 括号\"] --> B[\"② 乘除\"] --> C[\"③ 加减\"] --> D[\"④ 比较与逻辑\"]"),
    ("flow", "flowchart", "field", "神经网络结构示意（Mermaid 版：输入-隐藏-输出逐层堆叠）",
     ["神经网络结构", "网络结构图", "MLP", "全连接网络", "层级堆叠"],
     "flowchart TD\n  I[输入层] --> H1[隐藏层 1] --> H2[隐藏层 2] --> O[输出层]"),
    ("flow", "flowchart", "model", "分类体系 / 层级树（taxonomy：逐级细分）",
     ["分类体系", "层级树", "taxonomy", "树形图", "细分"],
     "flowchart TD\n  R[总类] --> A[按维度一]\n  R --> B[按维度二]\n  A --> A1[子类 A1]\n  B --> B1[子类 B1]"),
]
# A 类每个图族的样例 basename —— 与 A_FAMILIES 一一对应。
# 为什么不能按 type 命名样例：25 个 A 类条目只共用 3 个 spec type（flow/graph/timeline），
# 按 type 命名会互相覆盖，实测 25 个图族只能落下 6 张样例。
# 故样例按「图族」命名；flowchart 的 4 个不同场景各占一个键。
A_EXAMPLE_KEYS = [
    "flowchart",             # 业务流程（最通用）
    "flowchart_relation",    # 关系网络 / 拓扑
    "sequenceDiagram",
    "stateDiagram-v2",
    "erDiagram",
    "classDiagram",
    "architecture-beta",
    "C4Context",
    "flowchart_c4",          # C4 风格的 flowchart 复刻
    "flowchart_layered",     # 分层架构（subgraph 当泳道）
    "gantt",
    "kanban",
    "journey",
    "requirementDiagram",
    "timeline",
    "mindmap",
    "gitGraph",
    "block-beta",
    "packet-beta",
    "pie_mermaid",         # 与 B 类 Matplotlib 的 `pie` 区分
    "quadrantChart",
    "xychart-beta",
    "sankey-beta",
    "treemap-beta",
    "radar-beta",
    "ladder",                # 优先级 / 依赖阶梯
    "nn_diagram",            # 神经网络结构（Mermaid）
    "tree",                  # 分类体系 / 层级树
]
assert len(A_EXAMPLE_KEYS) == len(A_FAMILIES), 'A_EXAMPLE_KEYS 必须与 A_FAMILIES 等长'


# ---------------------------------------------------------------------------
# B 类：type -> (分类, 场景说明, 关键词, specs 文件名)
# ---------------------------------------------------------------------------
B_TYPES = {
    # —— compare 对比与构成 ——
    "bar": ("compare", "单一维度的类目比大小 / 排名", ["柱状图", "对比", "排名", "bar"], "b__bar.json"),
    "grouped_bar": ("compare", "多方案在不同类目上的分组对比", ["分组柱", "多方案对比", "grouped"], "b__grouped_bar.json"),
    "stacked_bar": ("compare", "构成占比随时间/类目变化（堆叠）", ["堆叠", "构成", "占比"], "b__stacked_bar.json"),
    "multi_bar": ("compare", "多个子图并排的多组柱（跨组对比）", ["多子图柱", "并排", "panel bar"], "b__multi_bar.json"),
    "pie": ("compare", "整体构成占比（类别少时）", ["饼图", "占比", "构成", "pie"], "b__pie.json"),
    "swimlane": ("flow", "泳道图 / 跨职能流程图（原生绘制，最可控）", ["泳道图", "跨职能", "swimlane", "泳道", "责任分工"], "b__swimlane.json"),
    "waterfall": ("compare", "增量分解 / 特征贡献（瀑布图）", ["瀑布", "增量", "贡献", "归因", "waterfall"], "b__waterfall.json"),
    "radar": ("compare", "多指标多方案雷达对比", ["雷达", "多指标", "蜘蛛", "radar"], "b__radar.json"),
    "venn2": ("compare", "两个集合的交并关系", ["韦恩", "交集", "重叠", "venn"], "b__venn2.json"),
    "matrix": ("compare", "文本表格（参数/结果对照表）", ["表格", "对照表", "table", "matrix"], "b__matrix.json"),
    # —— trend 趋势与曲线 ——
    "multi_curve": ("trend", "多条曲线/函数对比（含自定义表达式）", ["多条曲线", "对比曲线", "函数", "curve"], "b__multi_curve.json"),
    "function_curve": ("trend", "单函数曲线（表达式驱动）", ["函数曲线", "表达式", "function"], "b__function_curve.json"),
    "area_line": ("trend", "带填充的趋势线（强调累积/幅度）", ["面积图", "填充", "趋势"], "b__area_line.json"),
    "line_band": ("trend", "多 run / 多 seed 的均值 ± 标准差（波动带）", ["误差带", "波动带", "标准差", "置信区间", "多次实验", "多次运行", "均值", "seeds", "band", "±"], "b__line_band.json"),
    "errorbar": ("trend", "均值 ± 误差棒（柱或折线带误差）", ["误差棒", "errorbar", "标准差", "mean±std"], "b__errorbar.json"),
    "learning_curve": ("trend", "训练/验证损失（学习曲线）", ["学习曲线", "损失", "训练", "loss"], "b__learning_curve.json"),
    "twin_axis": ("trend", "两个量纲不同的指标共图（双轴）", ["双轴", "双 Y", "量纲", "twin"], "b__twin_axis.json"),
    "loglog": ("trend", "跨数量级的关系（双对数）", ["对数", "loglog", "数量级", "幂律"], "b__loglog.json"),
    "elbow": ("trend", "肘部法则 / 拐点识别", ["肘部", "拐点", "K 值", "elbow"], "b__elbow.json"),
    "regularization_path": ("trend", "正则路径 / 系数收缩", ["正则", "收缩", "系数", "lasso"], "b__regularization_path.json"),
    "spectrum": ("trend", "信号 / 频谱 / 谱图（可标峰值）", ["频谱", "信号", "谱图", "FFT", "峰"], "b__spectrum.json"),
    "multi_subplot": ("trend", "多个子图并排（函数/序列逐格对比）", ["多子图", "并排子图", "子图对比", "subplot"], "b__multi_subplot.json"),
    "panels": ("trend", "论文多面板组图（(a)(b)(c) 标签、共享轴）", ["多面板", "组图", "子图", "(a)(b)", "paper"], "b__panels.json"),
    # —— dist 分布与统计 ——
    "normal_dist": ("dist", "正态分布密度（可填充 ±σ）", ["正态", "高斯", "密度"], "b__normal_dist.json"),
    "cdf": ("dist", "累积分布（理论）", ["CDF", "累积分布", "分位"], "b__cdf.json"),
    "ecdf": ("dist", "经验累积分布（实测数据对比）", ["ECDF", "经验分布", "累积"], "b__ecdf.json"),
    "pmf_pdf": ("dist", "离散 PMF vs 连续 PDF", ["PMF", "PDF", "二项", "离散概率"], "b__pmf_pdf.json"),
    "hist_fit": ("dist", "直方图 + 理论密度拟合", ["直方图", "分布拟合", "hist"], "b__hist_fit.json"),
    "kde": ("dist", "核密度估计（可多峰混合）", ["核密度", "KDE", "密度估计"], "b__kde.json"),
    "boxplot": ("dist", "分组分布对比（箱线图）", ["箱线图", "分位数", "离群", "boxplot"], "b__boxplot.json"),
    "box_jitter": ("dist", "箱线 + 原始散点抖动（样本量小必用）", ["抖动", "散点+箱线", "jitter", "小样本"], "b__box_jitter.json"),
    "violin": ("dist", "分布形态对比（小提琴图）", ["小提琴", "分布形态", "violin"], "b__violin.json"),
    # —— relate 相关与拟合 ——
    "scatter_fit": ("relate", "散点 + 线性拟合", ["散点", "拟合", "回归", "最小二乘", "相关性", "相关关系"], "b__scatter_fit.json"),
    "scatter_classes": ("relate", "多类别散点（可带中心点、对数轴）", ["分类散点", "聚类", "类别"], "b__scatter_classes.json"),
    "scatter_boundary": ("relate", "分类边界（线性可分 / 不可分）", ["决策边界", "XOR", "可分"], "b__scatter_boundary.json"),
    "scatter_panels": ("relate", "多面板散点（迭代过程可视化）", ["多面板散点", "迭代", "簇"], "b__scatter_panels.json"),
    "scatter_rich": ("relate", "颜色/大小编码的散点（第三四维）", ["气泡图", "颜色编码", "大小编码"], "b__scatter_rich.json"),
    "scatter_matrix": ("relate", "相关性/协方差矩阵式散点对比", ["相关矩阵", "相关性分析", "协方差", "散点矩阵"], "b__scatter_matrix.json"),
    "fit_comparison": ("relate", "欠拟合/合适/过拟合等拟合对比", ["欠拟合", "过拟合", "拟合对比"], "b__fit_comparison.json"),
    "fit_band": ("relate", "拟合 + 置信/预测带", ["置信带", "预测带", "拟合区间"], "b__fit_band.json"),
    "parity": ("relate", "预测 vs 实测 parity（含 R²/MAE/RMSE）", ["parity", "预测对比", "一致性", "误差指标"], "b__parity.json"),
    "residual": ("relate", "残差诊断图（残差 vs 拟合值 + ±2σ）", ["残差", "诊断", "异方差"], "b__residual.json"),
    "scatter3d": ("relate", "三维散点（可选：按类别着色）", ["3D 散点", "三维散点", "scatter3d"], "b__scatter3d.json"),
    # —— field 场与矩阵 ——
    "heatmap": ("field", "二维热力图（计数/强度，带数值标注）", ["热力图", "heatmap", "强度"], "b__heatmap.json"),
    "heatmap_panels": ("field", "多面板热力图（含色条）", ["多面板热力图", "注意力", "attention"], "b__heatmap_panels.json"),
    "confusion": ("field", "混淆矩阵（计数/行归一化）", ["混淆矩阵", "confusion", "分类结果"], "b__confusion.json"),
    "clustered_heatmap": ("field", "表达矩阵热图（行列 z-score + 层次聚类重排，不画树）", ["聚类热图", "表达矩阵", "组学", "z-score", "热图重排"], "b__clustered_heatmap.json"),
    "nn_twin": ("field", "神经网络结构示意（单层 vs 多层）", ["网络结构", "MLP", "全连接", "神经元", "网络示意图"], "b__nn_twin.json"),
    "nn_single": ("field", "单个神经网络结构（神经元级全连接图，不做左右对比）", ["神经网络", "神经元", "全连接网络", "MLP", "网络结构图"], "b__nn_single.json"),
    "tensor_blocks": ("field", "0~3 维张量示意", ["张量", "维度", "tensor"], "b__tensor_blocks.json"),
    "tensor_cube_panels": ("field", "三维张量 + 通道混合/独立做法对比", ["张量示意", "通道混合"], "b__tensor_cube_panels.json"),
    "matrix_mul_panels": ("field", "矩阵乘 vs 逐元素乘示意", ["矩阵乘", "逐元素", "broadcast"], "b__matrix_mul_panels.json"),
    "contour_quiver": ("field", "等高线 + 梯度场", ["等高线", "梯度场", "quiver"], "b__contour_quiver.json"),
    "contourf": ("field", "填充等高线 / 损失曲面（二维替代 3D）", ["填充等高线", "损失曲面", "色阶", "contourf"], "b__contourf.json"),
    "surface3d": ("field", "三维曲面 z=f(x,y)（可选；默认规范建议先用 contourf 做二维表达）", ["3D 曲面", "曲面", "surface", "三维"], "b__surface3d.json"),
    # —— eval 评估与性能 ——
    "roc": ("eval", "ROC 曲线与 AUC", ["ROC", "AUC", "分类阈值"], "b__roc.json"),
    "calibration": ("eval", "校准/可靠性曲线（含 ECE）", ["校准", "可靠性", "ECE", "confidence"], "b__calibration.json"),
    "flamegraph": ("eval", "火焰图（perf/耗时归因，层级占比）", ["火焰图", "性能剖析", "perf", "火焰"], "b__flamegraph.json"),
    "roofline": ("eval", "Roofline 性能模型（算力/带宽上界）", ["roofline", "性能模型", "上界"], "b__roofline.json"),
    # —— math 优化与几何 ——
    "gradient_descent": ("math", "梯度下降轨迹示意", ["梯度下降", "轨迹"], "b__gradient_descent.json"),
    "multi_panel_gd": ("math", "不同学习率的下降轨迹对比", ["学习率", "下降轨迹", "轨迹对比"], "b__multi_panel_gd.json"),
    "optimizer_paths": ("math", "优化器路径对比（SGD/Adam…）", ["优化器", "路径", "adam", "sgd"], "b__optimizer_paths.json"),
    "tangent_secant": ("math", "割线逼近切线（导数含义）", ["切线", "割线", "导数"], "b__tangent_secant.json"),
    "limit": ("math", "极限逼近示意", ["极限", "逼近"], "b__limit.json"),
    "differential": ("math", "微分 dy 与增量 Δy", ["微分", "增量", "线性近似"], "b__differential.json"),
    "vector2d": ("math", "二维向量 / 夹角 / 相似度", ["向量", "夹角", "余弦"], "b__vector2d.json"),
    # —— bio 生医与统计推断 ——
    "km": ("bio", "Kaplan-Meier 生存曲线（含删失与风险表）", ["生存曲线", "KM", "Kaplan", "删失", "生存分析"], "b__km.json"),
    "forest": ("bio", "森林图 / 效应量与置信区间", ["森林图", "效应量", "OR", "HR", "置信区间", "meta"], "b__forest.json"),
    "volcano": ("bio", "火山图（差异表达：log2FC vs -log10 p）", ["火山图", "差异表达", "volcano", "p 值"], "b__volcano.json"),
}

_NON_PARAM_KEYS = {'mmd', 'params', 'id', 'type', 'output', 'width_in', 'height_in', 'title', 'curve', 'scale'}


def params_of(chart_type):
    """从 drawers.py 源码里抽该图型的顶层 params 键（避免文档与实现漂移）。"""
    path = os.path.join(HERE, 'drawers.py')
    try:
        src = open(path, encoding='utf-8').read()
    except OSError:
        return []
    m = re.search(r'^def draw_%s\(.*?(?=^def |\Z)' % re.escape(chart_type), src, re.M | re.S)
    if not m:
        return []
    keys = set(re.findall(r'\bp\.get\(\s*["\']([\w_]+)["\']', m.group(0)))
    keys |= set(re.findall(r'\bp\[\s*["\']([\w_]+)["\']\s*\]', m.group(0)))
    return sorted(keys - _NON_PARAM_KEYS)


def b_types_implemented():
    """实际实现了 draw_* 的 B 类图型（以代码为准）。"""
    try:
        src = open(os.path.join(HERE, 'drawers.py'), encoding='utf-8').read()
    except OSError:
        return []
    return sorted(set(re.findall(r'^def draw_(\w+)', src, re.M)))


def entries(include_planned=True):
    """展平成统一的条目列表（A 图族 + B 图型）。"""
    out = []
    for _i, (spec_type, mermaid, cat, scene, kws, tmpl) in enumerate(A_FAMILIES):
        _key = A_EXAMPLE_KEYS[_i]
        out.append({'kind': 'A', 'type': spec_type, 'mermaid': mermaid, 'category': cat,
                    'scene': scene, 'keywords': kws, 'params': [], 'mmd': tmpl,
                    'example': 'specs/a__%s.json' % _key, 'example_key': _key,
                    'planned': False})
    impl = set(b_types_implemented())
    for t, (cat, scene, kws, spec) in B_TYPES.items():
        out.append({'kind': 'B', 'type': t, 'mermaid': None, 'category': cat, 'scene': scene,
                    'keywords': kws, 'params': params_of(t), 'mmd': None,
                    'example': ('specs/' + spec) if spec else None, 'example_key': t,
                    'planned': t not in impl})
    return out


def category_name(cid):
    for c in CATEGORIES:
        if c[0] == cid:
            return c[2]
    return cid


def recommend(text, limit=3):
    """按描述打分：**只取最长命中关键词**为主分，额外命中只给小加成。

    为什么不做「所有关键词累加」：`架构图` 与 `架构` 会被同一条目重复命中，
    累加后反而让关键词堆得多的条目胜出（实测「系统分层架构图」被 architecture-beta 抢走）。
    """
    text = (text or '').strip().lower()
    if not text:
        return []
    scored = []
    for e in entries():
        if e['planned']:
            continue
        hits = [kw for kw in e['keywords'] if len(kw) >= 2 and kw.lower() in text]
        score = 0
        if hits:
            best = max(hits, key=len)
            score += 12 + min(len(best), 8)          # 关键词越长越具体
            score += min(3 * (len(hits) - 1), 6)     # 额外命中：最多 +6
        cname = category_name(e['category']).lower()
        if cname and cname in text:
            score += 8
        if e['mermaid'] and e['mermaid'].lower() in text:
            score += 15
        if score:
            scored.append((score, e, hits))
    scored.sort(key=lambda x: (-x[0], x[1]['kind'], x[1]['type']))
    return scored[:limit]

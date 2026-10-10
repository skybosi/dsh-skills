"""fonts.py —— 字体家族**唯一来源** + 字体自检探针（纯数据 + 标准库；matplotlib 只在探针里按需 import）。

为什么要单独一个文件（而不是把列表写在 style.py 里）：
`--doctor` 要做中文字体自检，而 `style.py` 顶层就 `import matplotlib` —— 缺 matplotlib 时
import 会直接炸，doctor 也就拿不到家族列表。列表抽到这里后，两条路径共用同一份。

⚠️ 三个实测约束（都踩过，别改回去）：

1. **matplotlib 取「列表里第一个能解析到的家族」，且不做逐字符回退**。
   所以顺序必须是「首选 → 各平台真实存在的 CJK 兜底 → 纯拉丁字体」，
   **绝不能把 Arial / DejaVu 这类无 CJK 字形的家族排在 CJK 之前**；
   也不能指望"把中文家族追加在末尾"兜住 —— 实测追加到 Arial 之后无效，
   中文照样落到 Arial 上画成豆腐块（□）。

2. **同一个字体文件在不同 matplotlib 版本下可能注册成不同家族名**。
   实测本机 `/System/Library/AssetsV2/.../PingFang.ttc`：matplotlib 3.11 注册出 `PingFang SC`，
   3.10 只注册出 **`PingFang HK`** —— 于是同一台机器、同一份 spec，B 类数据图的中文会从
   "正常"变成"整库豆腐块"。所以 `PingFang HK` 必须紧跟在 `PingFang SC` 后面（同一字体的另一个名字）。

3. **兜底家族要按「对本库真实语料的字形覆盖」挑，不能只看"是不是中文家族"**。
   用 `specs/b__*.json` 里真实出现的 562 个字符（含 460 个汉字）逐个家族量过：

   | 家族 | 缺字形 | 说明 |
   |---|---|---|
   | `Arial Unicode MS` | **0** | 覆盖最全（含 ² ŷ ₁ ₂ − 与简体专用字） |
   | `STHeiti` | `₁ ₂` | 缺下标 |
   | `PingFang HK` | `稳 迟` | ⚠️ HK 字体天然缺**简体专用码位**（它只有繁体 穩/遲） |
   | `Hiragino Sans GB` | `² ŷ ₁ ₂ −` | 缺常用科学符号 |
   | `Songti SC` | `² ŷ ₁ ₂ −` | 同上 |
   | `PingFang SC` | — | 本机 matplotlib 3.10 解析不到（见第 2 条） |

   所以顺序是：**平台原生的简中字体优先**（Linux `Noto Sans SC` / macOS `PingFang SC` /
   Windows `Microsoft YaHei`），它们不在时退到 `Arial Unicode MS`（本机实测 0 缺字），
   再往后才是 `Hiragino Sans GB` / `PingFang HK` 这些"看着像中文家族、实则缺符号或简体字"的兜底。

   另外：matplotlib 默认用 U+2212 画负号（`axes.unicode_minus`），这正是"负刻度变方框"的来源 ——
   该开关已在 style.py 关掉，见那边的说明。

用户可用环境变量 `FIGURE_MAKER_FONT` 指定一个家族名，插到列表最前（最高优先级）。
"""
import os

# 首选（跨平台按平台原生简中字体排：Linux / macOS / Windows），随后按"实测覆盖度"排兜底
FONT_FAMILIES = [
    "Noto Sans SC",        # Linux 常见 / 官网推荐
    "PingFang SC",         # macOS 首选（新版 macOS 是"按需下载"，可能不在）
    "Microsoft YaHei",     # Windows
    "Arial Unicode MS",    # 兜底一号：本库语料实测 0 缺字（含 ² ŷ ₁ ₂ − 与简体专用字）
    "Hiragino Sans GB",    # macOS 自带简中（缺 ² ŷ ₁ ₂ −）
    "PingFang HK",         # PingFang 在 matplotlib 3.10 下的名字（缺 稳 迟 等简体专用字）
    "Heiti SC",            # macOS 自带黑体
    "STHeiti",             # 同上的另一个名字（缺下标 ₁ ₂）
    "Arial",               # 纯拉丁兜底（无 CJK：只应作为最后手段）
    "DejaVu Sans",         # matplotlib 自带（无 CJK：保证 findfont 不报"家族找不到"）
]

# 自检样本分两档：
#   CORE  = 没有就**画不出中文**，属红线（中文 + 全角标点，specs 里最常用的就是这些）
#   EXTRA = 真实 spec 里出现过的符号，缺了只**点名的图**会报错，属提醒（不误报成"字体不可用"）
PROBE_CORE = "中文图型示例（含全角标点，。：；）"
PROBE_EXTRA = "−²₁αβθ≤×≈"


def families():
    """实际使用的家族列表：环境变量指定者优先。"""
    pref = (os.environ.get("FIGURE_MAKER_FONT") or "").strip()
    return ([pref] + FONT_FAMILIES) if pref else list(FONT_FAMILIES)


def resolve(fams=None):
    """返回 (家族名, 字体文件路径) —— 即 matplotlib 真正会用的那个；都解析不到返回 (None, None)。"""
    try:
        from matplotlib import font_manager as fm
    except Exception:                     # 没装 matplotlib：探针不成立，返回"未知"交给调用方
        return None, None
    for fam in (fams or families()):
        try:
            p = fm.findfont(fam, fallback_to_default=False)
        except Exception:
            continue
        if p and os.path.exists(p):
            return fam, p
    return None, None


def missing(text=PROBE_CORE, font_path=None):
    """返回 text 里**渲染时没有字形**的字符（这些字符会画成豆腐块 □）。"""
    if font_path is None:
        _fam, font_path = resolve()
    if not font_path:
        return list(dict.fromkeys(ch for ch in text if not ch.isspace()))
    try:
        from matplotlib.ft2font import FT2Font
        cmap = FT2Font(font_path).get_charmap()
    except Exception:
        return []                          # 探针失效时不下结论，避免误报
    return sorted({ch for ch in str(text) if not ch.isspace() and not cmap.get(ord(ch), 0)})


def probe():
    """给 --doctor 用的自检结果：core 缺 = 字体不可用；extra 缺 = 只影响用到这些符号的图。"""
    fam, path = resolve()
    return {"family": fam, "path": path,
            "missing": missing(PROBE_CORE, path),
            "missing_extra": missing(PROBE_EXTRA, path),
            "override": (os.environ.get("FIGURE_MAKER_FONT") or "").strip() or None,
            "families": families()}

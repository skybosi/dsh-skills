# dsh-skills

DeepSeek Harness（DSH）的**技能集合**。**一个目录 = 一个 skill**，安装即把目录拷进 `~/.dsh/skills/`。

## 安装（任选其一）

```bash
# ① 装单个技能
cp -R figure-maker ~/.dsh/skills/

# ② 装全部技能
for d in */; do [ -f "$d/SKILL.md" ] && cp -R "$d" ~/.dsh/skills/; done
```

装好后在 DSH 里直接说要做什么即可自动触发（或显式说「用 <skill 名>」）。

## 技能清单

| 技能 | 能做什么 | 前置依赖 |
|---|---|---|
| [**figure-maker**](figure-maker/) | 由**描述(spec)** 生成确定性矢量图：**91 个条目**（24 个 Mermaid 图族 + 67 种 Matplotlib 数据/统计/科研图，含生医统计与 3D）｜带**场景分类 + 选型路由**：`--recommend "一句话描述"` 直接给候选图型与可跑骨架，`--list` 按 14 个分类列全部图型｜输出 `svg`/`png`/`webp`（B 类另支持 `pdf`/`eps`/`jpeg`/`tiff`），产物 = **图 + `<名字>.meta.json`**，出图即做版式检查（重叠/越界/节点间距） | B 类：Python + matplotlib + numpy（webp 另需 Pillow）<br>A 类：Node.js + Playwright Chromium（mermaid 运行时已内置） |

> 每个技能目录里的 `README.md` 是该技能的能力说明（含样例图），`SKILL.md` 是给模型执行的规范。

## 约定（新增技能时）

- 一个目录一个技能，目录名 = skill 名，必须含 `SKILL.md`（frontmatter：`name` / `description` / `whenToUse`）
- 技能应当**自包含**：脚本与运行时随目录走，不依赖特定仓库

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_docs.py —— 从 `scripts/catalog.py`（图型目录的唯一来源）生成文档，避免文档与实现漂移。

  python3 scripts/build_docs.py            # 生成 TYPES.md + 刷新 README.md 的画廊区块

生成物：
  · TYPES.md            —— 整篇生成（分类目录 + 每类图型的场景/关键词/参数键/样例 + A 类骨架）
  · README.md           —— 只替换 <!-- GALLERY:START --> … <!-- GALLERY:END --> 之间的画廊
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import catalog  # noqa: E402

REL_EX = 'docs/examples/%s.svg'


def _exists(rel):
    return os.path.exists(os.path.join(SKILL, rel))


def _spec_path(e):
    return e['example'] if e['example'] else None


def types_md():
    ents = catalog.entries()
    a_ents = [e for e in ents if e['kind'] == 'A']
    b_ents = [e for e in ents if e['kind'] == 'B']
    L = []
    L.append('# 图型目录与选型')
    L.append('')
    L.append('> 本文件由 `scripts/build_docs.py` 从 `scripts/catalog.py` 生成，**不要手改**（改目录请改 catalog.py 后重跑）。')
    L.append('>')
    L.append('> 选型命令：`python3 scripts/draw.py --recommend "用一句话描述你要画的图"`：')
    L.append('> `--list` 按 14 个场景分类列图型：`--catalog --json` 给机器读；`--example <图型>` 打真实骨架。')
    L.append('')
    L.append('| 类 | 数量 | 渲染器 | spec 里给什么 | 产物格式 |')
    L.append('|---|---|---|---|---|')
    L.append('| **A 类 · 结构/关系图** | %d 个 Mermaid 图族（%d 个入口名等价） | Mermaid（内置运行时） | `mmd` 源码 | svg / png / webp |'
             % (len(a_ents), 6))
    L.append('| **B 类 · 数据/统计/科研图** | %d 种 | Matplotlib | `params` | svg / png / webp / pdf / eps / ps / jpeg / tiff |' % len(b_ents))
    L.append('')
    L.append('## 场景分类总览')
    L.append('')
    L.append('| 分类 id | 类 | 数量 | 什么时候用 |')
    L.append('|---|---|---|---|')
    for cid, klass, name, when, _kw in catalog.CATEGORIES:
        n = sum(1 for e in ents if e['category'] == cid)
        L.append('| `%s` | %s | %d | %s |' % (cid, klass, n, when))
    L.append('')
    L.append('## A 类 · Mermaid 图族')
    L.append('')
    L.append('A 类的 6 个入口名（`flow` `graph` `tree` `nn_diagram` `ladder` `timeline`）**彼此等价**：')
    L.append('`type` 填任意一个都行，真正决定画什么的是 `mmd` 里的第一行图型关键字。')
    L.append('')
    for cid, klass, name, when, _kw in catalog.CATEGORIES:
        items = [e for e in a_ents if e['category'] == cid]
        if not items:
            continue
        L.append('### %s（%s）' % (name, cid))
        L.append('')
        L.append('| Mermaid 图族 | spec 的 type | 场景 | 关键词 |')
        L.append('|---|---|---|---|')
        for e in items:
            L.append('| `%s` | `%s` | %s | %s |' % (e['mermaid'], e['type'], e['scene'], ' · '.join(e['keywords'])))
        L.append('')
    L.append('## B 类 · 数据图（%d 种）' % len(b_ents))
    L.append('')
    L.append('`参数键` 一列由 `drawers.py` 源码自动抽取（`p.get("…")`），不会和实现漂移；')
    L.append('嵌套结构（`panels[]` `series[]` `groups[]` `curves[]` 等）见 [docs/SPEC-REFERENCE.md](docs/SPEC-REFERENCE.md)。')
    L.append('')
    for cid, klass, name, when, _kw in catalog.CATEGORIES:
        items = [e for e in b_ents if e['category'] == cid]
        if not items:
            continue
        L.append('### %s（%s）—— %s' % (name, cid, when))
        L.append('')
        L.append('| 图型 | 场景 | 关键词 | 参数键 | 样例 |')
        L.append('|---|---|---|---|---|')
        for e in items:
            ex = _spec_path(e)
            exl = '[spec](%s)' % ex if ex else '—'      # TYPES.md 在 skill 根目录 → 用根相对路径
            key = e.get('example_key') or e['type']
            svg = REL_EX % key
            imgl = '[SVG](%s)' % svg if _exists(svg) else '—'
            L.append('| `%s` | %s | %s | %s | %s · %s |'
                     % (e['type'], e['scene'], ' · '.join(e['keywords']),
                        ' · '.join('`%s`' % p for p in e['params']) or '—', exl, imgl))
        L.append('')
    L.append('## A 类起手骨架（可直接抄进 `mmd`）')
    L.append('')
    for e in a_ents:
        L.append('**%s** —— %s（spec 的 `type` 填 `%s`）' % (e['mermaid'], e['scene'], e['type']))
        L.append('')
        L.append('```mermaid')
        L.append(e['mmd'])
        L.append('```')
        L.append('')
    L.append('## 替代写法 / 已知边界（都能出图，但换写法更稳）')
    L.append('')
    L.append('| 想要 | 现状 | 建议 |')
    L.append('|---|---|---|')
    L.append('| 泳道图（跨职能流程） | ✅ 已支持：B 类 `swimlane`（`lanes` + `steps` + `edges`，原生绘制，布局可控） | 直接 `--example swimlane` |')
    L.append('| 聚类树（dendrogram） | ✅ 已支持：`clustered_heatmap` 给 `dendrogram: true`（平均连接层次聚类 + 行/列树） | 需要更专业的树请用 scipy/seaborn |')
    L.append('| 桑基图 `sankey-beta` | ⚠️ 内置 Mermaid 的 sankey **只接受 ASCII 节点名**：源/目标含中文（即使加引号）都会解析失败 | 节点名用英文（数值与结构不受影响）；或用 B 类 `waterfall` / `stacked_bar` 表达构成与流向 |')
    L.append('| ZenUML | ❌ 内置的单文件 mermaid bundle 不含该图型 | 渲染器会**直接给出** `sequenceDiagram` 骨架（alt/loop/par/Note 都支持） |')
    L.append('| C4 上下文 / 容器图 | ⚠️ 能出图，但 Mermaid 的 C4 自动布局容易把描述文字和关系标签叠在一起（会告警 + 给建议） | 用 `flowchart` 复刻 C4 风格（见上方 arch 分类的骨架），或缩短 description |')
    L.append('| gitGraph | ⚠️ commit 标签多时容易互相压 | 减少分支/提交，或拆图 |')
    L.append('| radar-beta / treemap-beta / journey | ✅ 越界已由**自动扩画布**兜底（越界量记在 `meta.layout.canvasFitted`） | 维度/层级过多时仍建议减少 |')
    L.append('| 3D 曲面 | ⚠️ 可用（`surface3d` / `scatter3d`）但不是首选：本 skill 的视觉规范是二维软色板 | 优先 `contourf`（填充等高线） |')
    L.append('')
    return '\n'.join(L) + '\n'


def gallery_md():
    ents = catalog.entries()
    a_ents = [e for e in ents if e['kind'] == 'A']
    b_ents = [e for e in ents if e['kind'] == 'B']
    L = []
    L.append('<!-- GALLERY:START -->')
    L.append('> 本区块由 `scripts/build_docs.py` 生成；示例图用 `python3 scripts/build_examples.py` 重新生成。')
    L.append('')
    L.append('## 能力一览')
    L.append('')
    L.append('- **%d 个条目**：%d 个 Mermaid 图族（结构/关系图）+ %d 种 Matplotlib 数据图（含科研与生医常用图）'
             % (len(ents), len(a_ents), len(b_ents)))
    L.append('- 输出：**svg（默认）/ png / webp** 两类都支持；B 类另支持 `pdf` / `eps` / `ps` / `jpeg` / `tiff`')
    L.append('- 产物只有两样：**图** + **同目录的元信息**（`<名字>.meta.json`：类型/格式/尺寸/版式检查/原始 spec）')
    L.append('- 机器版式自检：文字重叠 0、越界 0；A 类还按图型分级检查节点间距（`--check` 可当红线）')
    L.append('- **选型不靠记清单**：`--recommend "一句话描述"` 直接给候选图型 + 可跑骨架；`--list` 按 14 个场景分类列全部图型')
    L.append('')
    n_img = sum(1 for e in ents if _exists(REL_EX % (e.get('example_key') or e['type'])))
    L.append('## 全部条目（%d 个；其中 %d 张带样例图）' % (len(ents), n_img))
    L.append('')
    L.append('> 样例由同名 spec 原样生成：`python3 scripts/build_examples.py --only <图型>`')
    L.append('')
    L.append('| # | 类 | 场景分类 | 图型 | 说明 |')
    L.append('|---|---|---|---|---|')
    i = 0
    for cid, klass, name, when, _kw in catalog.CATEGORIES:
        for e in [x for x in ents if x['category'] == cid]:
            i += 1
            label = e['mermaid'] if e['kind'] == 'A' else e['type']
            L.append('| %d | %s | %s | [`%s`](#%s) | %s |' % (i, e['kind'], name, label, label.lower(), e['scene'][:46]))
    L.append('')
    a_ex = [e['example_key'] for e in a_ents
            if e.get('example_key') and _exists(REL_EX % e['example_key'])]
    if a_ex:
        L.append('### A 类样例图（%d 张，来自 specs/a__*.json）' % len(a_ex))
        L.append('')
        for t in a_ex:
            L.append('<a id="a-%s"></a>' % t)
            L.append('**`%s`**' % t)
            L.append('')
            L.append('![%s](%s)' % (t, REL_EX % t))
            L.append('')
            L.append('<sub>spec：<code>specs/a__%s.json</code></sub>' % t)
            L.append('')
    for cid, klass, name, when, _kw in catalog.CATEGORIES:
        items = [e for e in ents if e['category'] == cid]
        if not items:
            continue
        L.append('### %s · %s（%s）' % (klass, name, when))
        L.append('')
        for e in items:
            label = e['mermaid'] if e['kind'] == 'A' else e['type']
            L.append('<a id="%s"></a>' % label.lower())
            L.append('**`%s`** —— %s' % (label, e['scene']))
            L.append('')
            svg = REL_EX % (e.get('example_key') or e['type'])
            if e['kind'] == 'B' and _exists(svg):
                L.append('![%s](%s)' % (label, svg))
                L.append('')
            if e['kind'] == 'B':
                L.append('<sub>spec：<code>%s</code> ｜ 参数键：%s</sub>' % (_spec_path(e) or '—', ' · '.join(e['params']) or '—'))
            else:
                _k = e.get('example_key') or e['type']
                extra = ('样例图：[`%s`](#a-%s) ｜ ' % (REL_EX % _k, _k)) if _exists(REL_EX % _k) else ''
                L.append('<sub>A 类：`mmd` 里写 `%s`，spec 的 `type` 填 `%s`（骨架见 [TYPES.md](TYPES.md)） ｜ %s</sub>'
                         % (e['mermaid'], e['type'], extra.rstrip(' ｜ ')))
            L.append('')
    L.append('<!-- GALLERY:END -->')
    return '\n'.join(L)


def render_readme():
    """返回「按当前 catalog.py 渲染出来的 README 全文」（只替换 GALLERY 区块，其余原样保留）。"""
    p = os.path.join(SKILL, 'README.md')
    if not os.path.exists(p):
        return None
    s = open(p, encoding='utf-8').read()
    start, end = '<!-- GALLERY:START -->', '<!-- GALLERY:END -->'
    block = gallery_md()
    if start in s and end in s:
        return s[:s.index(start)] + block + s[s.index(end) + len(end):]
    return s + '\n' + block + '\n'


def render_all():
    """生成物全文：{文件名: 内容}。生成器与检查器共用同一份渲染逻辑，避免两边不一致。"""
    return {'TYPES.md': types_md(), 'README.md': render_readme()}


def check_docs():
    """返回与磁盘内容不一致的生成物文件名列表（空列表 = 文档与 catalog.py 同步）。"""
    drift = []
    for name, content in render_all().items():
        if content is None:
            continue
        path = os.path.join(SKILL, name)
        cur = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if cur != content:
            drift.append(name)
    return drift


def update_readme():
    content = render_readme()
    if content is None:
        return False
    open(os.path.join(SKILL, 'README.md'), 'w', encoding='utf-8').write(content)
    return True


def main():
    ap = argparse.ArgumentParser(description='从 catalog.py 生成 TYPES.md / README 画廊')
    ap.add_argument('--check', action='store_true',
                    help='只检查生成物是否与 catalog.py 同步（不一致退出码 1，不写文件）')
    a = ap.parse_args()
    if a.check:
        drift = check_docs()
        if drift:
            print('❌ 生成类文档与 catalog.py 不一致：%s' % '、'.join(drift))
            print('   修复：python3 scripts/build_docs.py')
            return 1
        print('✅ 生成类文档与 catalog.py 一致（TYPES.md / README.md）')
        return 0
    open(os.path.join(SKILL, 'TYPES.md'), 'w', encoding='utf-8').write(types_md())
    print('✅ TYPES.md 已生成')
    if update_readme():
        print('✅ README.md 画廊区块已刷新')
    return 0


if __name__ == '__main__':
    sys.exit(main())

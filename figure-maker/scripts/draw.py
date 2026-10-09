#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""draw.py —— 由**描述(spec)** 出图（独立：只用本 skill 目录里的脚本）

产物只有两样：**某个格式的图**  +  **元信息**（同目录 `fig.meta.json`：类型/格式/尺寸/字节数/版式检查/原始 spec/时间）

用法
  python3 scripts/draw.py --list                      # 列出支持的图型（B 类 + A 类）
  python3 scripts/draw.py --example bar               # 打印该图型的示例 spec
  python3 scripts/draw.py spec.json                   # 出图（输出路径取 spec.output，默认 out/<id>.svg）
  python3 scripts/draw.py spec.json -o out/f.png      # 指定输出：**格式由扩展名决定** svg/png/webp/pdf…
  python3 scripts/draw.py spec.json --format webp     # 显式指定格式
  python3 scripts/draw.py spec.json --check           # 出图后跑版式检查（重叠/越界），不过关退出码 1
  python3 scripts/draw.py --batch specs/              # 批量：画出目录下所有 *.json

spec 结构
  B 类（数据图，Matplotlib）
    { "id": "fig1", "type": "grouped_bar", "output": "out/fig1.svg",
      "width_in": 8.0, "height_in": 4.5,
      "params": { "title": "…", "categories": [...], "groups": [{"label":"…","values":[...]}], "ylabel": "…" } }
  A 类（结构图，Mermaid）—— 直接给 Mermaid 源码，skill 不替你编图
    { "id": "flow1", "type": "flow", "output": "out/flow1.svg",
      "title": "流程标题", "mmd": "flowchart TD\\n  A[开始] --> B{判断}\\n  B -->|是| C[结束]" }

依赖：B 类需 matplotlib + numpy；A 类需 Node + Playwright Chromium（见 SKILL.md「依赖与安装」）
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# matplotlib 的缓存写到临时目录：否则会在 skill 目录里生成 .mplcache/（污染分发内容）
import tempfile
os.environ.setdefault('MPLCONFIGDIR', os.path.join(tempfile.gettempdir(), 'figure-maker-mpl'))

A_TYPES = ['flow', 'graph', 'tree', 'nn_diagram', 'ladder', 'timeline']
X_TYPES = {'surface3d': '3D 曲面', 'multi_normal': '多元正态 3D'}
FORMATS = ['svg', 'png', 'pdf', 'webp', 'eps', 'ps', 'jpeg', 'tiff']


def b_types():
    """B 类图型 = drawers.py 里的 draw_* 函数名（去掉前缀），再加上通用入口 render 支持的别名。"""
    try:
        import drawers
    except ImportError as e:
        return []
    names = sorted(n[len('draw_'):] for n in dir(drawers) if n.startswith('draw_'))
    return names


def do_list():
    bs = b_types()
    print('A 类（Mermaid 结构图，%d 种，spec 里给 mmd 源码）：' % len(A_TYPES))
    for t in A_TYPES:
        print('   %s' % t)
    print('\nB 类（Matplotlib 数据图，%d 种，spec 里给 params）：' % len(bs))
    for i in range(0, len(bs), 4):
        print('   ' + '  '.join('%-20s' % x for x in bs[i:i + 4]))
    print('\n不支持（规范禁用 3D）：%s' % '、'.join('%s（%s）' % (k, v) for k, v in X_TYPES.items()))
    print('\n输出格式：%s（由输出扩展名决定，或用 --format 指定）' % ' / '.join(FORMATS))


def do_example(t):
    ex = {
        'id': 'demo-' + t, 'type': t, 'output': 'out/demo-%s.svg' % t,
        'params': {'title': '示例：%s' % t, 'xlabel': 'x', 'ylabel': 'y',
                   'categories': ['甲', '乙', '丙', '丁'],
                   'groups': [{'label': '组 1', 'values': [3, 5, 2, 4]},
                              {'label': '组 2', 'values': [4, 2, 6, 3]}]}
    } if t not in A_TYPES else {
        'id': 'demo-' + t, 'type': t, 'output': 'out/demo-%s.svg' % t, 'title': '示例：%s' % t,
        'mmd': 'flowchart TD\n  A[输入] --> B{判断}\n  B -->|是| C[处理]\n  B -->|否| D[结束]\n  C --> D'
    }
    print(json.dumps(ex, ensure_ascii=False, indent=2))



def write_meta(out, spec, checks=None, extra=None):
    """写出**元信息**（sidecar）：<out>.meta.json

    产物只有两样：**图** + **元信息**。元信息用于复现与追溯：
      id / type / format / 输出路径 / 字节数 / 尺寸 / 版式检查结果 / 原始 spec / 生成时间 / 工具版本
    """
    import datetime
    meta = {
        'id': spec.get('id'),
        'type': spec.get('type'),
        'format': os.path.splitext(out)[1].lstrip('.').lower(),
        'output': os.path.abspath(out),
        'bytes': os.path.getsize(out) if os.path.exists(out) else 0,
        'generated_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'figure_maker': 'figure-maker/1.0',
        'spec': spec,
    }
    if checks:
        meta['layout'] = {
            'overlap': len(checks.get('overlap') or []),
            'outOfCanvas': len(checks.get('outOfCanvas') or []),
            'passed': not (checks.get('overlap') or checks.get('outOfCanvas')),
        }
    if extra:
        meta.update(extra)
    # A 类：从 SVG 头里取尺寸
    try:
        head = open(out, encoding='utf-8', errors='ignore').read(400)
        import re as _re
        mw = _re.search(r'width="([\d.]+)', head)
        mh = _re.search(r'height="([\d.]+)', head)
        if mw and mh:
            meta['width_px'] = float(mw.group(1)); meta['height_px'] = float(mh.group(1))
    except Exception:
        pass
    # 元信息命名：与图**同目录**、去掉扩展名 → out/fig.webp ⇒ out/fig.meta.json
    # （同一 basename 的多种格式会共用一份元信息，以最后生成的为准 —— 这是刻意的简化）
    mp = os.path.splitext(out)[0] + '.meta.json'
    with open(mp, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return mp

def render_a(spec, out):
    """A 类（Mermaid）：渲染 SVG；需要位图时自动转 PNG/WebP。

    产物格式支持：svg（默认）/ png / webp（png 由 Playwright 截图，webp 再由 Pillow 转）。
    返回渲染器的布局检查结果（render-mermaid.js --json），供 --check 与元信息使用。
    """
    ext = os.path.splitext(out)[1].lstrip('.').lower() or 'svg'
    if ext not in ('svg', 'png', 'webp'):
        raise SystemExit('❌ A 类（Mermaid）支持 svg / png / webp；不支持 .%s' % ext)
    mmd = spec.get('mmd') or (spec.get('params') or {}).get('mmd')
    if not mmd:
        raise SystemExit('A 类 spec 需要 "mmd" 字段（Mermaid 源码）；本 skill 不替你编图 ✗')
    js = os.path.join(HERE, 'render-mermaid.js')
    raster = os.path.join(HERE, 'svg-to-raster.js')
    if not os.path.exists(js):
        raise SystemExit('缺少 scripts/render-mermaid.js（A 类渲染器）')
    tmpdir = tempfile.mkdtemp(prefix='figure-maker-')
    mmd_path = os.path.join(tmpdir, 'fig.mmd')
    svg_path = out if ext == 'svg' else os.path.join(tmpdir, 'fig.svg')
    json_path = os.path.join(tmpdir, 'checks.json')
    open(mmd_path, 'w', encoding='utf-8').write(mmd)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True)
    cmd = ['node', js, '--in', mmd_path, '--out', svg_path, '--json', json_path]
    if spec.get('title'):
        cmd += ['--title', spec['title']]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write((r.stdout or '') + (r.stderr or ''))
        raise SystemExit('A 类渲染失败（检查 Node 与 Playwright 是否可用）')

    checks = None
    try:
        checks = json.load(open(json_path, encoding='utf-8'))
    except Exception:
        checks = None

    if ext == 'png':
        rr = subprocess.run(['node', raster, '--in', svg_path, '--out', out, '--scale', str(spec.get('scale') or 2)],
                            capture_output=True, text=True)
        if rr.returncode != 0:
            sys.stderr.write((rr.stdout or '') + (rr.stderr or ''))
            raise SystemExit('A 类转 PNG 失败（svg-to-raster.js）')
    elif ext == 'webp':
        png_path = os.path.join(tmpdir, 'fig.png')
        rr = subprocess.run(['node', raster, '--in', svg_path, '--out', png_path, '--scale', str(spec.get('scale') or 2)],
                            capture_output=True, text=True)
        if rr.returncode != 0:
            raise SystemExit('A 类转 PNG 失败（svg-to-raster.js）')
        try:
            from PIL import Image
        except ImportError:
            raise SystemExit('输出 webp 需要 Pillow：pip install Pillow')
        Image.open(png_path).convert('RGB').save(out, 'WEBP', quality=95, method=6)
    return checks


def render_b(spec, out):
    import drawers
    from style import setup_soft_style, report_and_exit
    t = spec['type']
    if not hasattr(drawers, 'draw_' + t) and not hasattr(drawers, 'render'):
        raise SystemExit('未知图型：%s（用 --list 看支持列表）' % t)
    setup_soft_style()
    checks = drawers.render(t, spec.get('params') or {}, out,
                            width_in=float(spec.get('width_in') or 8.0),
                            height_in=float(spec.get('height_in') or 4.5))
    return checks



def do_doctor():
    """自检运行环境：两类图各自需要什么、缺什么、怎么装。"""
    import platform, shutil, subprocess as sp
    ok = lambda b: '✅' if b else '❌'
    py = platform.python_version()
    mods = {}
    for m in ('matplotlib', 'numpy', 'PIL'):
        try:
            mod = __import__(m); mods[m] = getattr(mod, '__version__', '?')
        except ImportError:
            mods[m] = None
    node = shutil.which('node')
    node_v = sp.run([node, '-v'], capture_output=True, text=True).stdout.strip() if node else ''
    pw = False
    if node:
        probe = ("try{require('playwright');console.log('ok')}catch(e){"
                 "try{require(require('path').join(process.env.PW_MODULES||'/tmp/pw/node_modules','playwright'));console.log('ok')}"
                 "catch(e2){console.log('no')}}")
        pw = sp.run([node, '-e', probe], capture_output=True, text=True).stdout.strip() == 'ok'
    mermaid = os.path.exists(os.path.join(HERE, 'vendor', 'mermaid.min.js'))
    print('figure-maker 环境自检')
    print('  Python            %s %s' % (py, ok(mods['matplotlib'] and mods['numpy'])))
    print('  matplotlib        %s' % (mods['matplotlib'] or '未安装 → pip install matplotlib'))
    print('  numpy             %s' % (mods['numpy'] or '未安装 → pip install numpy'))
    print('  Pillow（webp）     %s' % (mods['PIL'] or '未安装 → pip install Pillow（可选：只影响 webp 输出）'))
    print('  Node.js           %s %s' % (node_v or '未安装', ok(bool(node))))
    print('  Playwright 模块    %s' % ('可用' if pw else '未找到 → npm i -g playwright 或设 PW_MODULES'))
    print('  Chromium 浏览器    %s' % ('见 PLAYWRIGHT_BROWSERS_PATH' if pw else '→ npx playwright install chromium'))
    print('  mermaid 运行时      %s' % ('已内置' if mermaid else '缺失'))
    print('')
    print('  → B 类（45 种数据图）需要：Python + matplotlib + numpy（webp 另需 Pillow）')
    print('  → A 类（Mermaid 结构图）需要：Node.js + Playwright Chromium（mermaid 已内置）')
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('spec', nargs='?')
    ap.add_argument('-o', '--out')
    ap.add_argument('--format', choices=FORMATS)
    ap.add_argument('--check', action='store_true', help='出图后跑版式检查（不通过则退出码 1）')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--doctor', action='store_true', help='自检依赖环境')
    ap.add_argument('--example', metavar='TYPE')
    ap.add_argument('--batch', metavar='DIR', help='批量：画出该目录下所有 *.json spec')
    a = ap.parse_args()

    if a.doctor:
        return do_doctor()
    if a.list:
        do_list(); return 0
    if a.example:
        do_example(a.example); return 0
    if a.batch:
        import glob
        specs = sorted(glob.glob(os.path.join(a.batch, '*.json')))
        if not specs:
            raise SystemExit('目录里没有 spec：%s' % a.batch)
        ok = fail = 0
        for sp in specs:
            spec = json.load(open(sp, encoding='utf-8'))
            t = spec.get('type')
            out = a.out or spec.get('output') or os.path.join('out', '%s.svg' % (spec.get('id') or os.path.basename(sp)[:-5]))
            if a.format:
                out = os.path.splitext(out)[0] + '.' + a.format
            try:
                if t in X_TYPES:
                    raise RuntimeError('规范禁用 3D')
                if t in A_TYPES:
                    checks = render_a(spec, out)
                else:
                    checks = render_b(spec, out)
                    if a.check and not _quick_ok(checks):
                        raise RuntimeError('版式检查未通过')
                write_meta(out, spec, locals().get('checks'))
                print('✅ %-40s %s (+ .meta.json)' % (os.path.basename(sp), out)); ok += 1
            except Exception as e:
                print('❌ %-40s %s' % (os.path.basename(sp), e)); fail += 1
        print('\n批量完成：成功 %d ｜ 失败 %d' % (ok, fail))
        return 1 if fail else 0
    if not a.spec:
        ap.print_help(); return 2

    spec = json.load(open(a.spec, encoding='utf-8'))
    t = spec.get('type')
    if t in X_TYPES:
        raise SystemExit('❌ 规范禁用 3D 图（%s）：请改用分面等高线 / 多子图等二维表达' % t)
    out = a.out or spec.get('output') or os.path.join('out', '%s.svg' % (spec.get('id') or 'fig'))
    if a.format:
        out = os.path.splitext(out)[0] + '.' + a.format

    if t in A_TYPES:
        checks = render_a(spec, out)
        mp = write_meta(out, spec, checks)
        ok = _quick_ok(checks) if checks else True
        print('✅ 图：%s' % out)
        print('   元信息：%s ｜ 版式检查：%s' % (mp, '通过' if ok else '有告警（加 --check 看详情）'))
        if a.check and not ok:
            return 1
        return 0

    checks = render_b(spec, out)
    mp = write_meta(out, spec, checks)
    ok = _quick_ok(checks)
    print('✅ 图：%s' % out)
    print('   元信息：%s ｜ 版式检查：%s' % (mp, '通过' if ok else '有告警（加 --check 看详情）'))
    if not a.check:
        return 0
    from style import report_and_exit
    return report_and_exit(checks, out)


def _quick_ok(checks):
    if not checks:
        return True
    for k in ('overlap', 'outOfCanvas', 'overlapText'):
        v = checks.get(k) if isinstance(checks, dict) else None
        if v:
            return False
    return True


if __name__ == '__main__':
    sys.exit(main())

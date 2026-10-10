#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""draw.py —— 由**描述(spec)** 出图（figure-maker 的唯一入口，独立：只用本 skill 目录里的脚本）

产物只有两样：**某个格式的图**  +  **元信息**（同目录 `fig.meta.json`：类型/格式/尺寸/字节数/版式检查/原始 spec/时间）

用法
  python3 scripts/draw.py --list                      # 列出支持的图型（A 类 + B 类）
  python3 scripts/draw.py --doctor                    # 自检依赖
  python3 scripts/draw.py --example bar               # 打印该图型的**真实示例 spec**（取自 specs/）
  python3 scripts/draw.py spec.json                   # 出图（输出路径取 spec.output，默认 out/<id>.svg）
  python3 scripts/draw.py spec.json -o out/f.png      # 指定输出：**格式由扩展名决定** svg/png/webp/pdf…
  python3 scripts/draw.py spec.json --format webp     # 显式指定格式
  python3 scripts/draw.py spec.json --check           # 把版式检查当红线（不过关退出码 1）
  python3 scripts/draw.py --batch specs/              # 批量：画出目录下所有 *.json

版式检查语义（两类一致）
  默认：出图 + 检查，**不拦截**（结果写进 meta.json 的 layout 字段，stdout 打印「通过 / 有告警」）
  --check：检查不过关 → 退出码 1

spec 结构
  B 类（数据图，Matplotlib）
    { "id": "fig1", "type": "grouped_bar", "output": "out/fig1.svg",
      "width_in": 8.0, "height_in": 4.5,
      "params": { "title": "…", "categories": [...], "groups": [{"label":"…","values":[...]}], "ylabel": "…" } }
  A 类（结构图，Mermaid）—— 直接给 Mermaid 源码，skill 不替你编图
    { "id": "flow1", "type": "flow", "output": "out/flow1.svg",
      "title": "流程标题", "mmd": "flowchart TD\\n  A[开始] --> B{判断}\\n  B -->|是| C[结束]" }
  可选：curve（Mermaid 曲线：basis/linear/step…）、scale（A 类转位图的清晰度倍数，默认 2）

依赖：B 类需 matplotlib + numpy；A 类需 Node + Playwright Chromium（见 SKILL.md「依赖与安装」）
"""
import argparse
import json
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SPECS = os.path.join(SKILL, 'specs')
sys.path.insert(0, HERE)

# matplotlib 的缓存写到临时目录：否则会在 skill 目录里生成 .mplcache/（污染分发内容）
os.environ.setdefault('MPLCONFIGDIR', os.path.join(tempfile.gettempdir(), 'figure-maker-mpl'))

A_TYPES = ['flow', 'graph', 'tree', 'nn_diagram', 'ladder', 'timeline']
FORMATS = ['svg', 'png', 'pdf', 'webp', 'eps', 'ps', 'jpeg', 'jpg', 'tiff', 'tif']
A_FORMATS = ('svg', 'png', 'webp')


def b_types():
    """B 类图型 = drawers.py 里的 draw_* 函数名（去掉前缀）。返回 (names, err)。"""
    try:
        import drawers  # noqa: F401
    except ImportError as e:
        return None, str(e)
    import drawers
    names = sorted(n[len('draw_'):] for n in dir(drawers) if n.startswith('draw_'))
    return names, None


def do_list(category=None):
    """按**场景分类**列出图型（不再是一张平铺清单）。"""
    import catalog
    bs, err = b_types()
    groups = {}
    for cid, klass, name, when, _kws in catalog.CATEGORIES:
        groups[cid] = (klass, name, when, [])
    for e in catalog.entries():
        if category and e['category'] != category:
            continue
        if e['category'] in groups:
            groups[e['category']][3].append(e)
    print('figure-maker 图型目录（按场景分类；共 %d 个条目）\n' % sum(len(g[3]) for g in groups.values()))
    for cid, klass, name, when, items in catalog.CATEGORIES:
        if category and cid != category:
            continue
        items = groups[cid][3]
        if not items:
            continue
        print('■ %s · %s（%s）—— %s' % (klass, name, cid, when))
        for e in items:
            label = e['mermaid'] if e['kind'] == 'A' else e['type']
            tag = ('A 类（spec 的 type 填 %s）' % e['type']) if e['kind'] == 'A' else ('B 类' + ('  ⏳未实现' if e['planned'] else ''))
            print('   %-24s %-34s %s' % (label, e['scene'][:32], tag))
        print('')
    if category:
        return
    if bs is None:
        print('⚠️  B 类（Matplotlib 数据图）当前不可用：未安装 matplotlib/numpy（%s）' % err)
        _pip = 'Scripts\\pip.exe' if os.name == 'nt' else 'bin/pip'
        _py = 'python' if os.name == 'nt' else 'python3'
        print('    安装：%s -m venv .venv && .venv/%s install matplotlib numpy' % (_py, _pip))
    print('方案模板（完整真实方案图，可直接抄改）：--example tech-flow / tech-arch / tech-swimlane')
    print('选型：python3 draw.py --recommend "用一句话描述你要画的图"')
    print('骨架：python3 draw.py --example <图型>    目录：python3 draw.py --catalog --json')
    print('输出格式：A 类 %s ｜ B 类 %s' % ('/'.join(A_FORMATS), ' / '.join(FORMATS)))


def do_recommend(text):
    """按用户描述推荐图型，并给出**可直接保存运行**的 spec 骨架。"""
    import catalog
    hits = catalog.recommend(text, limit=3)
    if not hits:
        print('没有匹配到图型。用 `--list` 看分类，或用更具体的词（例如「时序图」「热力图」「生存曲线」）。')
        return 1
    print('🔎 「%s」→ 推荐 %d 个候选：\n' % (text, len(hits)))
    for i, (score, e, matched) in enumerate(hits, 1):
        print('%d) [%s · %s] %s' % (i, e['kind'], catalog.category_name(e['category']),
                                    (e['mermaid'] or e['type'])))
        print('   场景：%s' % e['scene'])
        if e['kind'] == 'A':
            print('   写法：A 类，spec 里给 mmd 源码（type 填 %s）' % e['type'])
            spec = {'id': 'demo-%s' % e['mermaid'].lower(), 'type': e['type'],
                    'output': 'out/demo-%s.svg' % e['mermaid'].lower(), 'mmd': e['mmd']}
            print('   —— 可直接保存为 spec.json ——')
            for line in json.dumps(spec, ensure_ascii=False, indent=2).splitlines():
                print('   ' + line)
        else:
            print('   参数键：%s' % (' · '.join(e['params']) or '（见 SPEC-REFERENCE）'))
            print('   抄骨架：python3 draw.py --example %s    # 对应 %s' % (e['type'], e['example'] or '—'))
        if matched:
            print('   命中词：%s' % '、'.join(matched[:6]))
        print('')
    print('都不合适？用 --list 看 14 个场景分类，或直接点名图型（--example <type>）。')
    return 0


def do_catalog(as_json=False):
    """打印机器可读目录（含分类、关键词、参数键、示例 spec 路径），供 agent 选型。"""
    import catalog
    data = {
        'skill': 'figure-maker',
        'version': 'figure-maker/1.1',
        'categories': [{'id': c[0], 'class': c[1], 'name': c[2], 'when': c[3]} for c in catalog.CATEGORIES],
        'types': catalog.entries(),
    }
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        for c in data['categories']:
            n = sum(1 for e in data['types'] if e['category'] == c['id'])
            print('%-12s %s（%s）%2d 个：%s' % (c['id'], c['name'], c['class'], n, c['when']))
        print('\n共 %d 个条目（%d 已实现 / %d 规划中）' % (
            len(data['types']),
            sum(1 for e in data['types'] if not e['planned']),
            sum(1 for e in data['types'] if e['planned'])))
    return 0



def do_example(t):
    """打印该图型的**真实示例 spec**（直接取 specs/ 下的同名文件），没有则退回最小骨架。"""
    for pre in ('a__', 'b__'):
        p = os.path.join(SPECS, pre + t + '.json')
        if os.path.exists(p):
            spec = json.load(open(p, encoding='utf-8'))
            spec['output'] = 'out/demo-%s.svg' % t
            print(json.dumps(spec, ensure_ascii=False, indent=2))
            return
    # 方案模板（完整的真实方案图，不是最小骨架）：specs/templates/<name>.json
    tp = os.path.join(SPECS, 'templates', t + '.json')
    if os.path.exists(tp):
        spec = json.load(open(tp, encoding='utf-8'))
        spec['output'] = 'out/%s.svg' % t          # 模板保持自己的输出名，方便直接出图
        print(json.dumps(spec, ensure_ascii=False, indent=2))
        return
    if t in A_TYPES:
        ex = {'id': 'demo-' + t, 'type': t, 'output': 'out/demo-%s.svg' % t, 'title': '示例：%s' % t,
              'mmd': 'flowchart TD\n  A[输入] --> B{判断}\n  B -->|是| C[处理]\n  B -->|否| D[结束]\n  C --> D'}
    else:
        ex = {'id': 'demo-' + t, 'type': t, 'output': 'out/demo-%s.svg' % t,
              'params': {'title': '示例：%s' % t}}
    print(json.dumps(ex, ensure_ascii=False, indent=2))


def _layout_summary(checks):
    """把渲染器的检查结果规范化成 meta.layout（两类图型同一口径）。"""
    if not isinstance(checks, dict):
        return None
    def cnt(*keys):
        return sum(len(checks[k]) for k in keys if isinstance(checks.get(k), (list, tuple)))
    gap = (checks.get('nodeGap') or {}).get('min')
    gap_min = checks.get('gapMin')
    gap_ok = (gap_min is None) or (gap is None) or (gap >= gap_min)
    n_overlap = cnt('overlap', 'overlapText')
    fitted = checks.get('canvasFitted')
    bad_glyph = checks.get('missingGlyphs') or {}
    if bad_glyph:
        print('❌ 字形缺失（会画成豆腐块 □）：%s' % '；'.join(
            '%s → %s' % (k, ''.join(v)) for k, v in list(bad_glyph.items())[:3]))
        print('   本机用于绘图的字体解析不到这些字符。三种解法：')
        print('   1) 装一个中文字体（推荐 Noto Sans SC）：python3 scripts/draw.py --doctor 会给出建议')
        print('   2) 指定家族名：FIGURE_MAKER_FONT="Hiragino Sans GB" python3 scripts/draw.py ...')
        print('   3) 换掉这些字符（例如把全角括号/特殊符号改成 ASCII）')
    n_out = 0 if fitted else cnt('outOfCanvas')       # 自动扩画布后，越界内容已可见 → 不算红线
    out = {
        'overlap': n_overlap,
        'outOfCanvas': n_out,
        'overflow': cnt('overflow'),
        'nodeGap': gap,
        'gapMin': gap_min,
        'diagramType': checks.get('diagramType'),
        'passed': (n_overlap + n_out + cnt('overflow')) == 0 and gap_ok,
    }
    if fitted:
        out['canvasFitted'] = fitted
        out['outOfCanvasBeforeFit'] = cnt('outOfCanvas')
    return out


def _image_size(path, fmt):
    """尽量读出像素尺寸：SVG 读 width/height 属性；PNG 读 IHDR（不依赖任何第三方库）。"""
    try:
        if fmt == 'svg':
            head = open(path, encoding='utf-8', errors='ignore').read(600)
            import re as _re
            mw = _re.search(r'width="([\d.]+)', head)
            mh = _re.search(r'height="([\d.]+)', head)
            if mw and mh:
                return round(float(mw.group(1))), round(float(mh.group(1)))
        elif fmt == 'png':
            with open(path, 'rb') as f:
                head = f.read(24)
            if head[:8] == b'\x89PNG\r\n\x1a\n' and head[12:16] == b'IHDR':
                return struct.unpack('>II', head[16:24])
    except Exception:
        pass
    return None


def write_meta(out, spec, checks=None, extra=None):
    """写出**元信息**（sidecar）：<out>.meta.json

    产物只有两样：**图** + **元信息**。元信息用于复现与追溯：
      id / type / format / 输出路径 / 字节数 / 尺寸 / 版式检查结果 / 原始 spec / 生成时间 / 工具版本
    """
    import datetime
    fmt = os.path.splitext(out)[1].lstrip('.').lower()
    meta = {
        'id': spec.get('id'),
        'type': spec.get('type'),
        'format': fmt,
        'output': os.path.abspath(out),
        'bytes': os.path.getsize(out) if os.path.exists(out) else 0,
        'generated_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'figure_maker': 'figure-maker/1.1',
        'spec': spec,
    }
    lay = _layout_summary(checks)
    if lay:
        meta['layout'] = lay
    warns = checks.get('warnings') if isinstance(checks, dict) else None
    if warns:
        meta['warnings'] = warns
    if extra:
        meta.update(extra)
    size = _image_size(out, fmt)
    if size:
        meta['width_px'], meta['height_px'] = size
    # 元信息命名：与图**同目录**、去掉扩展名 → out/fig.webp ⇒ out/fig.meta.json
    # （同一 basename 的多种格式会共用一份元信息，以最后生成的为准 —— 这是刻意的简化）
    mp = os.path.splitext(out)[0] + '.meta.json'
    with open(mp, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return mp


def render_a(spec, out):
    """A 类（Mermaid）：渲染 SVG；需要位图时自动转 PNG/WebP。

    产物格式支持：svg（默认）/ png / webp（png 由 Playwright 截图，webp 再由 Pillow 转）。
    返回渲染器的版式检查结果（render-mermaid.js --json），供 --check 与元信息使用。

    render-mermaid.js 退出码：0=全绿；1=**已出图但版式不过**（此时 SVG 一定存在）；
    2=用法错误；3=渲染失败。以前把 1 也当成「渲染失败」，于是稍微拥挤的图会被整张丢掉，
    还会留下一个没有 meta 的孤儿 SVG —— 现已区分。
    """
    ext = os.path.splitext(out)[1].lstrip('.').lower() or 'svg'
    if ext not in A_FORMATS:
        raise SystemExit('❌ A 类（Mermaid）支持 %s；不支持 .%s' % (' / '.join(A_FORMATS), ext))
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
    # 色板唯一来源在 style.py；写成 JSON 交给渲染器，JS 侧不再自存一份（否则两处必然漂移）
    from style import palette_payload
    pal_path = os.path.join(tmpdir, 'palette.json')
    with open(pal_path, 'w', encoding='utf-8') as fh:
        json.dump(palette_payload(), fh, ensure_ascii=False)
    cmd = ['node', js, '--in', mmd_path, '--out', svg_path, '--json', json_path,
           '--palette', pal_path]
    if spec.get('title'):
        cmd += ['--title', spec['title']]
    if spec.get('curve'):
        cmd += ['--curve', str(spec['curve'])]
    if spec.get('background') is False:
        cmd += ['--bg', '0']
    if spec.get('autofit') is False:
        cmd += ['--autofit', '0']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 4:
        sys.stderr.write(r.stderr or '')
        raise SystemExit('A 类不支持该图型（见上面的替代写法）')
    if r.returncode not in (0, 1):
        sys.stderr.write((r.stdout or '') + (r.stderr or ''))
        raise SystemExit('A 类渲染失败（Mermaid 解析/渲染错误；检查 Node 与 Playwright 是否可用）')
    if r.stderr:
        sys.stderr.write(r.stderr)
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
            sys.stderr.write((rr.stdout or '') + (rr.stderr or ''))
            raise SystemExit('A 类转 PNG 失败（svg-to-raster.js）')
        try:
            from PIL import Image
        except ImportError:
            raise SystemExit('输出 webp 需要 Pillow：pip install Pillow')
        Image.open(png_path).convert('RGB').save(out, 'WEBP', quality=95, method=6)
    return checks


def _has_matplotlib(py):
    try:
        r = subprocess.run([py, '-c', 'import matplotlib, numpy'], capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def _find_python_with_matplotlib():
    """当前解释器没有 matplotlib 时，找一个装了的（skill 内 .venv / DSH 运行时 / 常见路径 / python3.x）。"""
    import glob as _g, shutil as _sh
    cands = []
    if os.environ.get('FIGURE_MAKER_PYTHON'):
        cands.append(os.environ['FIGURE_MAKER_PYTHON'])
    cands.append(os.path.join(SKILL, '.venv', 'bin', 'python'))
    for name in ('python3.13', 'python3.12', 'python3.11', 'python3.10', 'python3'):
        p = _sh.which(name)
        if p:
            cands.append(p)
    cands += ['/opt/homebrew/bin/python3', '/usr/local/bin/python3',
              os.path.expanduser('~/miniconda3/bin/python'), os.path.expanduser('~/anaconda3/bin/python')]
    cands += sorted(_g.glob(os.path.expanduser('~/.dsh/dsh-runtimes/*/dependencies/python/bin/python3')))
    seen = set()
    for c in cands:
        if not c or c in seen or not os.path.exists(c):
            continue
        seen.add(c)
        try:
            if os.path.realpath(c) == os.path.realpath(sys.executable):
                continue
        except OSError:
            pass
        if _has_matplotlib(c):
            return c
    return None


def _maybe_reexec():
    """B 类需要 matplotlib：当前解释器没有时自动换一个装了的重跑（幂等，可用 --no-reexec 关）。"""
    if os.environ.get('FIGURE_MAKER_REEXEC') == '1' or os.environ.get('FIGURE_MAKER_NO_REEXEC') == '1':
        return
    try:
        import matplotlib  # noqa: F401
        return
    except ImportError:
        pass
    py = _find_python_with_matplotlib()
    if not py:
        return
    sys.stderr.write('ℹ️  当前解释器（%s）没有 matplotlib，改用：%s\n' % (sys.executable, py))
    env = dict(os.environ, FIGURE_MAKER_REEXEC='1')
    os.execve(py, [py, os.path.abspath(__file__)] + sys.argv[1:], env)


def render_b(spec, out):
    import drawers
    from style import setup_soft_style
    t = spec['type']
    setup_soft_style()
    checks = drawers.render(t, spec.get('params') or {}, out,
                            width_in=float(spec.get('width_in') or 8.0),
                            height_in=float(spec.get('height_in') or 4.5))
    return checks


def do_doctor():
    """自检运行环境：两类图各自需要什么、缺什么、怎么装。"""
    import platform, shutil, subprocess as sp
    ok = lambda b: '✅' if b else '❌'  # noqa: E731
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
    bs, _err = b_types()
    print('figure-maker 环境自检')
    print('  Python            %s' % py)
    print('  matplotlib        %s %s' % (mods['matplotlib'] or '未安装 → pip install matplotlib', ok(mods['matplotlib'])))
    print('  numpy             %s %s' % (mods['numpy'] or '未安装 → pip install numpy', ok(mods['numpy'])))
    print('  Pillow（webp）     %s %s' % (mods['PIL'] or '未安装 → pip install Pillow（可选：只影响 webp 输出）', ok(mods['PIL'])))
    print('  Node.js           %s %s' % (node_v or '未安装', ok(bool(node))))
    print('  Playwright 模块    %s' % ('可用' if pw else '未找到 → npm i playwright 或设 PW_MODULES'))
    print('  Chromium 浏览器    %s' % ('见 PLAYWRIGHT_BROWSERS_PATH' if pw else '→ npx playwright install chromium'))
    print('  mermaid 运行时      %s' % ('已内置' if mermaid else '缺失'))
    print('  B 类图型数         %s' % ('%d 种' % len(bs) if bs is not None else '不可用（缺 matplotlib）'))
    # 中文字体自检：缺字形会把中文画成豆腐块（渲染器能检出，但装机自检更该先拦住）
    try:
        import fonts as _fonts
        p = _fonts.probe()
        note = '（由 FIGURE_MAKER_FONT 指定）' if p['override'] else ''
        if p['family'] and not p['missing']:
            print('  中文字体           %s ✅%s' % (p['family'], note))
        elif p['family']:
            print('  中文字体           %s ❌ 缺中文字形：%s' % (p['family'], ''.join(p['missing'])))
            print('                     → 该字体画不出中文，会变成豆腐块 □')
            print('                     → 装 Noto Sans SC，或 FIGURE_MAKER_FONT=<某个含中文的家族名>')
        else:
            print('  中文字体           ❌ 列表里一个家族都解析不到')
            print('                     → 装一个中文字体（推荐 Noto Sans SC）后重跑本自检')
        if p['family'] and p['missing_extra']:
            # 不误报成"字体不可用"：这些符号只在真用到它们的图里才成问题
            print('  符号字形          ⚠️ %s 缺：%s' % (p['family'], ''.join(p['missing_extra'])))
            print('                     → 只影响图里真用到这些符号的图（渲染器会报"字形缺失"）；'
                  '可用 FIGURE_MAKER_FONT 换一个覆盖更全的字体')
    except Exception as e:                      # 自检失败不该让 doctor 崩掉
        print('  中文字体           ⚠️ 无法自检（%s）' % e)
    try:
        import build_docs
        drift = build_docs.check_docs()
        print('  文档同步           %s' % ('✅ TYPES.md / README.md 与 catalog.py 一致'
                                          if not drift else
                                          '❌ 漂移：%s（跑 python3 scripts/build_docs.py 修复）' % '、'.join(drift)))
    except Exception as e:                      # 校验失败不该让自检崩掉
        print('  文档同步           ⚠️ 无法校验（%s）' % e)
    print('')
    print('  → B 类（数据图）需要：Python + matplotlib + numpy（webp 另需 Pillow）')
    print('  → A 类（Mermaid 结构图）需要：Node.js + Playwright Chromium（mermaid 已内置）')
    return 0


def _quick_ok(checks):
    """检查结果是否全绿（两类图型同一口径；gapMin 为 None 表示该图型不套间距红线）。

    ⚠️ 「字形缺失」算**红线**：缺字形的字符会被画成豆腐块 □ —— 版式上既不重叠也不越界，
    肉眼一扫还以为是排版问题，很容易蒙混过关（实测本机整库 69 张数据图的中文全变方框，
    而当时的 _quick_ok 只看 overlap / outOfCanvas，--check 照样"全绿"）。
    """
    if not isinstance(checks, dict):
        return True
    for k in ('overlap', 'overlapText', 'overflow'):
        if checks.get(k):
            return False
    if checks.get('missingGlyphs'):
        return False
    if checks.get('outOfCanvas') and not checks.get('canvasFitted'):
        return False
    gap = (checks.get('nodeGap') or {}).get('min')
    gap_min = checks.get('gapMin')
    if gap_min is not None and gap is not None and gap < gap_min:
        return False
    return True


def _run_one(spec, out, check=False):
    t = spec.get('type')
    checks = render_a(spec, out) if t in A_TYPES else render_b(spec, out)
    mp = write_meta(out, spec, checks)
    ok = _quick_ok(checks)
    # 提示由渲染器自己打到 stderr（这里转发过），此处只回传计数，避免同一句提示出现两次
    warns = (checks or {}).get('warnings') or [] if isinstance(checks, dict) else []
    return mp, ok, warns


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('spec', nargs='?')
    ap.add_argument('-o', '--out')
    ap.add_argument('--format', choices=FORMATS)
    ap.add_argument('--check', action='store_true', help='把版式检查当红线（不过关则退出码 1）')
    ap.add_argument('--list', nargs='?', const='', metavar='CATEGORY', help='按场景分类列图型（可只列某个分类，如 --list trend）')
    ap.add_argument('--recommend', metavar='DESC', help='按一句描述推荐图型并给出可跑骨架')
    ap.add_argument('--catalog', action='store_true', help='打印图型目录（配 --json 输出机器可读目录）')
    ap.add_argument('--json', action='store_true', help='配合 --catalog 使用：输出 JSON')
    ap.add_argument('--no-reexec', action='store_true', help='B 类缺少 matplotlib 时不要自动换解释器')
    ap.add_argument('--check-docs', action='store_true',
                    help='只检查生成类文档（TYPES.md / README.md）是否与 catalog.py 同步，不一致退出码 1')
    ap.add_argument('--doctor', action='store_true', help='自检依赖环境')
    ap.add_argument('--example', metavar='TYPE')
    ap.add_argument('--batch', metavar='DIR', help='批量：画出该目录下所有 *.json spec')
    a = ap.parse_args()

    if a.no_reexec:
        os.environ['FIGURE_MAKER_NO_REEXEC'] = '1'
    # B 类才需要 matplotlib：先看一眼 spec 的 type，需要且当前解释器没有就换个解释器重跑
    _need_types = []
    if a.spec and os.path.exists(a.spec):
        try:
            _need_types.append(json.load(open(a.spec, encoding='utf-8')).get('type'))
        except Exception:
            pass
    elif a.batch:
        import glob as _g
        for _f in _g.glob(os.path.join(a.batch, '*.json')):
            try:
                _need_types.append(json.load(open(_f, encoding='utf-8')).get('type'))
            except Exception:
                pass
    if any(t and t not in A_TYPES for t in _need_types):
        _maybe_reexec()

    if a.check_docs:
        import build_docs
        drift = build_docs.check_docs()
        if drift:
            print('❌ 生成类文档与 catalog.py 不一致：%s' % '、'.join(drift))
            print('   修复：python3 scripts/build_docs.py')
            return 1
        print('✅ 生成类文档与 catalog.py 一致（TYPES.md / README.md）')
        return 0
    if a.doctor:
        return do_doctor()
    if a.catalog:
        return do_catalog(as_json=a.json)
    if a.list is not None:
        do_list(a.list or None); return 0
    if a.recommend:
        return do_recommend(a.recommend)
    if a.example:
        do_example(a.example); return 0
    if a.batch:
        import glob
        specs = sorted(glob.glob(os.path.join(a.batch, '*.json')))
        if not specs:
            raise SystemExit('目录里没有 spec：%s' % a.batch)
        if a.out:
            raise SystemExit('--batch 与 -o 不能同时用（所有 spec 会写到同一个文件）')
        ok = fail = 0
        for sp in specs:
            spec = json.load(open(sp, encoding='utf-8'))
            t = spec.get('type')
            out = spec.get('output') or os.path.join('out', '%s.svg' % (spec.get('id') or os.path.basename(sp)[:-5]))
            if a.format:
                out = os.path.splitext(out)[0] + '.' + a.format
            try:
                mp, good, _w = _run_one(spec, out, check=a.check)
                if a.check and not good:
                    raise RuntimeError('版式检查未通过（见 %s）' % mp)
                print('✅ %-40s %s (+ %s)%s' % (os.path.basename(sp), out, os.path.basename(mp),
                                                '' if good else '  ❌ 版式不通过（见上方提示）')); ok += 1
            except SystemExit as e:
                print('❌ %-40s %s' % (os.path.basename(sp), e)); fail += 1
            except Exception as e:
                print('❌ %-40s %s' % (os.path.basename(sp), e)); fail += 1
        print('\n批量完成：成功 %d ｜ 失败 %d' % (ok, fail))
        return 1 if fail else 0
    if not a.spec:
        ap.print_help(); return 2

    spec = json.load(open(a.spec, encoding='utf-8'))
    out = a.out or spec.get('output') or os.path.join('out', '%s.svg' % (spec.get('id') or 'fig'))
    if a.format:
        out = os.path.splitext(out)[0] + '.' + a.format
    mp, ok, warns = _run_one(spec, out, check=a.check)
    print('✅ 图：%s' % out)
    print('   元信息：%s ｜ 版式检查：%s%s'
          % (mp, '通过' if ok else '不通过（加 --check 时退出码 1；明细见 meta.layout）',
             '' if not warns else ' ｜ ⚠️ 渲染提示 %d 条（见 meta.warnings）' % len(warns)))
    if a.check and not ok:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

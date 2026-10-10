#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_examples.py —— 用 specs/ 里的 spec **重新生成** docs/examples/ 的样例图（画廊）。

  python3 scripts/build_examples.py                 # 生成全部
  python3 scripts/build_examples.py --only bar,km   # 只生成指定图型
  python3 scripts/build_examples.py --check         # 同时跑版式检查（有告警会打印）

产物：docs/examples/<type>.svg（每种图型一张，README 的画廊直接引用它们）
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--specs', default=os.path.join(SKILL, 'specs'))
    ap.add_argument('--out', default=os.path.join(SKILL, 'docs', 'examples'))
    ap.add_argument('--only', default='', help='逗号分隔的图型名')
    ap.add_argument('--check', action='store_true', help='同时做版式检查')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    only = {x.strip() for x in a.only.split(',') if x.strip()}
    import draw as D
    # 样例名冲突检测：两个 spec 映射到同一个 <key>.svg 会互相覆盖
    # （真实踩过：A 类图族 `pie` 与 B 类 `pie` 同名，样例被后者覆盖）
    _seen = {}
    ok = bad = warn = 0
    for name in sorted(os.listdir(a.specs)):
        if not name.endswith('.json'):
            continue
        spec = json.load(open(os.path.join(a.specs, name), encoding='utf-8'))
        t = spec.get('type')
        # A 类样例按「图族」命名，不按 type：25 个 A 类条目只共用 3 个 type
        # （flow/graph/timeline），按 type 命名会互相覆盖、只能落下 6 张。
        # 约定：A 类 spec 名为 a__<key>.json，样例即 <key>.svg。
        key = name[3:-5] if (t in D.A_TYPES and name.startswith('a__')) else t
        if only and t not in only and key not in only:
            continue
        if key in _seen:
            print('❌ 样例名冲突：%s 与 %s 都映射到 %s.svg（改其中之一的 key）'
                  % (name, _seen[key], key))
            bad += 1
            continue
        _seen[key] = name
        out = os.path.join(a.out, '%s.svg' % key)
        try:
            checks = D.render_a(spec, out) if t in D.A_TYPES else D.render_b(spec, out)
            # 缺字形 = 样例被写坏（中文/符号变成豆腐块 □），必须算**失败**，不能只算"告警"：
            # 真实踩过：本机 matplotlib 解析不到中文字体，整库 69 张数据图的中文全变方框，
            # 而这里照样打印 ✅、报「告警 0，失败 0」、退出码 0 —— 静默产出损坏样例。
            glyph = (checks or {}).get('missingGlyphs') or {} if isinstance(checks, dict) else {}
            good = D._quick_ok(checks)
            if glyph:
                print('❌ %-24s 缺字形（画出来是豆腐块 □）：%s'
                      % (t, '；'.join('%s → %s' % (k, ''.join(v)) for k, v in list(glyph.items())[:3])))
                print('   → 本机缺中文字体。装 Noto Sans SC，或用 '
                      'FIGURE_MAKER_FONT="Hiragino Sans GB" 指定家族名后重跑 '
                      '（python3 scripts/draw.py --doctor 可自检）')
                bad += 1
                continue
            warn += 0 if good else 1
            print('%s %-24s → %s' % ('✅' if good else '⚠️ ', t, os.path.relpath(out, SKILL)))
            ok += 1
        except SystemExit as e:
            print('❌ %-24s %s' % (t, e)); bad += 1
    print('\n生成 %d 张（不通过 %d，失败 %d）' % (ok, warn, bad))
    if bad:
        print('⚠️ 有样例生成失败/被写坏 —— 失败项对应的 <名字>.svg 可能是损坏文件，'
              '修好环境后重跑；不要把损坏样例提交进仓库。')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

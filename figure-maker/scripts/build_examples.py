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
    ok = bad = warn = 0
    for name in sorted(os.listdir(a.specs)):
        if not name.endswith('.json'):
            continue
        spec = json.load(open(os.path.join(a.specs, name), encoding='utf-8'))
        t = spec.get('type')
        if only and t not in only:
            continue
        out = os.path.join(a.out, '%s.svg' % t)
        try:
            checks = D.render_a(spec, out) if t in D.A_TYPES else D.render_b(spec, out)
            good = D._quick_ok(checks)
            warn += 0 if good else 1
            print('%s %-24s → %s' % ('✅' if good else '⚠️ ', t, os.path.relpath(out, SKILL)))
            ok += 1
        except SystemExit as e:
            print('❌ %-24s %s' % (t, e)); bad += 1
    print('\n生成 %d 张（告警 %d，失败 %d）' % (ok, warn, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

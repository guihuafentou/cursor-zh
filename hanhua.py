#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor 简体中文汉化器 (cursor-zh)
原理：Cursor 自研界面不走官方语言包，直接安全替换 workbench.glass.main.js 与
workbench.desktop.main.js 中的显示字符串（命令面板、设置条目等分布在两个文件）。
只改显示文本，跳过所有比较位/枚举映射/逻辑字段/nls 本地化位，绝不碰运行逻辑。
用法：
  python hanhua.py                # 自动定位 Cursor 并汉化（自动备份）
  python hanhua.py --path "D:\\cursor\\resources\\app"   # 指定 Cursor app 目录
  python hanhua.py --restore      # 还原英文原版
  python hanhua.py --dry-run      # 预览将替换多少处（不写文件）
  python hanhua.py --report       # 只输出词表命中报告（不写入）
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ---- 词表文件与目标文件 ----
WORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'words.json')
TARGET_RELS = [
    os.path.join('out', 'vs', 'workbench', 'workbench.glass.main.js'),
    os.path.join('out', 'vs', 'workbench', 'workbench.desktop.main.js'),
]
BACKUP_SUFFIX = '.bak'

# ---- 常见 Cursor 安装位置（自动探测，支持 Windows / macOS） ----
CANDIDATE_ROOTS = [
    r'C:\Users\%USERNAME%\AppData\Local\Programs\cursor\resources\app',
    r'C:\Users\%USERNAME%\AppData\Local\Programs\Cursor\resources\app',
    r'C:\Program Files\Cursor\resources\app',
    r'C:\Program Files (x86)\Cursor\resources\app',
    r'D:\cursor\resources\app',
    '/Applications/Cursor.app/Contents/Resources/app',
    os.path.expanduser('~/Applications/Cursor.app/Contents/Resources/app'),
]

BLOCKLIST = [
    'Es=jr?Se?"Repository":Lr?"Team":"Personal"',
]

DANG_BEFORE = re.compile(
    r'(===|!==|==|!=)\s*$'
    r'|\.\w+\(\s*$'
    r'|\[\s*"?$'
    r'|\]="?$'
)
DANG_AFTER = re.compile(r'^\s*:')
NLS_CALL = re.compile(r'\b[atAe]{1,2}\(\d+,\s*"$')
SAFE_POS = re.compile(
    r'(label|title|description|placeholder|aria-label|accessibleLabel|ctaLabel|children|text|content|'
    r'name|tooltip|header|sectionTitle|message|hint|hintText|searchPlaceholder|primaryLabel|'
    r'groupLabel|kindLabel|actionTitle|defaultLabel|protectionDescription|showLocalhostLinks|'
    r'openWebLinks|automation|protection|subtitle):"$'
    r'|(\?"|:"|return"|\|\|"|\?\?"|="$'
)


def find_target(path=None):
    if path:
        for rel in TARGET_RELS:
            t = os.path.join(path, rel)
            if os.path.exists(t):
                return t
        raise SystemExit(f'未找到目标文件: {os.path.join(path, TARGET_RELS[0])}')
    for root in CANDIDATE_ROOTS:
        root = root.replace('%USERNAME%', os.environ.get('USERNAME', 'Administrator'))
        for rel in TARGET_RELS:
            t = os.path.join(root, rel)
            if os.path.exists(t):
                return t
    raise SystemExit('未自动找到 Cursor，请用 --path 指定 Cursor 的 resources\\app 目录')


def is_safe(data, start, end):
    for bl in BLOCKLIST:
        if bl in data[max(0, start - 80):start + len(bl) + 40]:
            return False
    before = data[max(0, start - 30):start]
    if DANG_BEFORE.search(before):
        return False
    if NLS_CALL.search(before):
        return False
    if DANG_AFTER.match(data[end:end + 6]):
        prev = data[max(0, start - 2):start]
        if not prev.endswith('?'):
            return False
    ctx = data[max(0, start - 30):start + 1]
    if not SAFE_POS.search(ctx):
        return False
    return True


def apply_global(data, words):
    total = 0
    for english, chinese in words.items():
        pattern = re.compile('"' + re.escape(english) + '"')
        matches = list(pattern.finditer(data))
        replaced = 0
        new_data = []
        last = 0
        for m in matches:
            if is_safe(data, m.start(), m.end()):
                new_data.append(data[last:m.start()])
                new_data.append('"' + chinese + '"')
                last = m.end()
                replaced += 1
        new_data.append(data[last:])
        data = ''.join(new_data)
        total += replaced
    return data, total


def apply_anchor(data, words):
    total = 0
    for english, chinese in words.items():
        n = data.count(english)
        if n:
            data = data.replace(english, chinese)
            total += n
    return data, total


def apply_d_calls(data, words):
    total = 0
    for key, chinese in words.items():
        pattern = re.compile(r'"' + re.escape(key) + r'","([^"]*)"')
        matches = list(pattern.finditer(data))
        for m in matches:
            old = m.group(0)
            new = '"%s","%s"' % (key, chinese)
            data = data.replace(old, new, 1)
            total += 1
    return data, total


def check_syntax(target):
    node = shutil.which('node') or shutil.which('node.exe')
    if not node:
        print('警告: 未找到 node，跳过语法验证')
        return True
    r = subprocess.run([node, '--check', target], capture_output=True, text=True)
    if r.returncode != 0:
        print('语法验证失败:', r.stderr[:500])
        return False
    return True


def process_file(target, words, dry):
    with open(target, encoding='utf-8') as f:
        data = f.read()
    bak = target + BACKUP_SUFFIX
    if not os.path.exists(bak):
        shutil.copy2(target, bak)
        print('已备份英文原版 ->', bak)
    data, n_global = apply_global(data, words['global'])
    data, n_anchor = apply_anchor(data, words['anchor'])
    n_dcalls = 0
    if 'd_calls' in words:
        data, n_dcalls = apply_d_calls(data, words['d_calls'])
    total = n_global + n_anchor + n_dcalls
    print(f'  {os.path.basename(target)}: global {n_global} + anchor {n_anchor} + d_calls {n_dcalls} = {total}')
    if dry:
        return total
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tf:
        tf.write(data)
        tmp = tf.name
    ok = check_syntax(tmp)
    os.unlink(tmp)
    if not ok:
        print('  语法验证未通过，未写入')
        return 0
    with open(target, 'w', encoding='utf-8') as f:
        f.write(data)
    return total


def main():
    ap = argparse.ArgumentParser(description='Cursor 汉化器')
    ap.add_argument('--path', help='Cursor 的 resources\\app 目录')
    ap.add_argument('--restore', action='store_true', help='还原英文原版')
    ap.add_argument('--dry-run', action='store_true', help='只统计不写入')
    ap.add_argument('--report', action='store_true', help='输出词表命中报告')
    args = ap.parse_args()
    target = find_target(args.path)
    root = target
    for _ in range(len(TARGET_RELS[0].split(os.sep))):
        root = os.path.dirname(root)
    targets = [os.path.join(root, rel) for rel in TARGET_RELS if os.path.exists(os.path.join(root, rel))]
    if args.restore:
        ok = False
        for t in targets:
            bak = t + BACKUP_SUFFIX
            if os.path.exists(bak):
                shutil.copy2(bak, t)
                print('已还原英文原版 ->', os.path.basename(t))
                ok = True
        if not ok:
            print('未找到备份文件，无法还原')
        return
    with open(WORDS_FILE, encoding='utf-8') as f:
        words = json.load(f)
    dc = len(words.get('d_calls', {}))
    print(f'词表: global {len(words["global"])} 条, anchor {len(words["anchor"])} 条, d_calls {dc} 条')
    grand = 0
    for t in targets:
        grand += process_file(t, words, args.dry_run or args.report)
    print(f'合计替换: {grand}')
    if not (args.dry_run or args.report):
        print('汉化完成，请重启 Cursor 生效；还原: python hanhua.py --restore')


if __name__ == '__main__':
    main()

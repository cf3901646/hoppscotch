#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

def fix_placeholder_spaces(text):
    # 规则1：蒙古文字符直接紧跟 {（无空格）
    # 匹配模式：[蒙古文]{  ->  [蒙古文] {
    text = re.sub(r'([\u0400-\u04FF])(\{)', r'\1 \2', text)
    
    # 规则2：} 直接紧跟蒙古文字符（无空格）
    # 匹配模式：}{[蒙古文]  ->  } [蒙古文]
    # 注意：} 和蒙古文之间没有任何字符（不是 \s*，是精确的0个）
    text = re.sub(r'(\})([\u0400-\u04FF])', r'\1 \2', text)
    
    return text

def process_file(filepath, fix_newline=False):
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    fixed = fix_placeholder_spaces(original)
    
    newline_added = False
    if fix_newline and not fixed.endswith('\n'):
        fixed += '\n'
        newline_added = True
        print("  [OK] 补充末尾换行符")
    
    if fixed == original and not newline_added:
        print("  [--] 无需修改")
        return 0
    
    changes = 0
    orig_lines = original.splitlines()
    fixed_lines = fixed.splitlines()
    for i, (ol, fl) in enumerate(zip(orig_lines, fixed_lines), 1):
        if ol != fl:
            print(f"  L{i}: {ol.strip()}")
            print(f"    -> {fl.strip()}")
            changes += 1
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write(fixed)
    
    return changes


def verify_remaining(filepath):
    """验证是否还有 无空格 紧贴问题"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 精确检查：蒙古文直接跟{（无空格）
    p1 = re.findall(r'[\u0400-\u04FF]\{', content)
    # 精确检查：}直接跟蒙古文（无空格）
    p2 = re.findall(r'\}[\u0400-\u04FF]', content)
    
    return len(p1) + len(p2), p1[:3], p2[:3]


if __name__ == '__main__':
    base = r"C:\Users\Administrator\.gemini\antigravity\scratch\hoppscotch"
    
    files_to_fix = [
        (os.path.join(base, r"packages\hoppscotch-common\locales\mn.json"), False),
        (os.path.join(base, r"packages\hoppscotch-sh-admin\locales\mn.json"), False),
        (os.path.join(base, r"packages\hoppscotch-common\languages.json"), True),
    ]
    
    total_changes = 0
    for filepath, fix_newline in files_to_fix:
        print(f"\n[FILE] {os.path.relpath(filepath, base)}")
        changes = process_file(filepath, fix_newline)
        total_changes += changes
        print(f"  共修改 {changes} 行")
    
    print(f"\n[DONE] 全部完成！总共修改 {total_changes} 处")
    
    print("\n=== 验证结果 ===")
    for filepath, _ in files_to_fix[:2]:
        remaining, s1, s2 = verify_remaining(filepath)
        name = os.path.relpath(filepath, base)
        if remaining == 0:
            print(f"  [PASS] {name}: 无问题")
        else:
            print(f"  [FAIL] {name}: 还有 {remaining} 处")
            if s1: print(f"    蒙文->'{{': {s1}")
            if s2: print(f"    '}}'->蒙文: {s2}")

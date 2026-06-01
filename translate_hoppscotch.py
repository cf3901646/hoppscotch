# -*- coding: utf-8 -*-
import os
import json
import re
import time
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 第一组路径：hoppscotch-common
COMMON_EN_PATH = os.path.join(BASE_DIR, "packages", "hoppscotch-common", "locales", "en.json")
COMMON_MN_PATH = os.path.join(BASE_DIR, "packages", "hoppscotch-common", "locales", "mn.json")
COMMON_LANGS_PATH = os.path.join(BASE_DIR, "packages", "hoppscotch-common", "languages.json")

# 第二组路径：hoppscotch-sh-admin
ADMIN_EN_PATH = os.path.join(BASE_DIR, "packages", "hoppscotch-sh-admin", "locales", "en.json")
ADMIN_MN_PATH = os.path.join(BASE_DIR, "packages", "hoppscotch-sh-admin", "locales", "mn.json")
ADMIN_LANGS_PATH = os.path.join(BASE_DIR, "packages", "hoppscotch-sh-admin", "languages.json")

# 匹配占位符的正则表达式（Hoppscotch 采用单花括号 {name} 及 HTML 标记 <a>）
PLACEHOLDER_REGEX = re.compile(r'\{[^{}]+\}|\<[^<>]+\>')

def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def inflate_dict(d, sep='.'):
    result = {}
    for path, val in d.items():
        parts = path.split(sep)
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = val
    return result

def translate_batch(texts, sl="en", tl="mn"):
    if not texts:
        return []

    all_placeholders = []
    protected_lines = []
    
    for text in texts:
        if not isinstance(text, str) or not text.strip():
            protected_lines.append(text)
            continue
            
        placeholders = []
        def replace_match(match):
            placeholder = match.group(0)
            placeholders.append(placeholder)
            return f" __VAR_{len(placeholders) - 1}__ "
            
        protected = PLACEHOLDER_REGEX.sub(replace_match, text)
        all_placeholders.append(placeholders)
        protected_lines.append(protected)

    combined_text = "\n".join([line if line else "" for line in protected_lines])

    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": sl,
        "tl": tl,
        "dt": "t",
        "q": combined_text
    }
    
    encoded_query = urllib.parse.urlencode(params)
    full_url = f"{url}?{encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    translated_lines = []
    try:
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data and data[0]:
                translated_combined = "".join([part[0] for part in data[0] if part[0]])
                translated_lines = translated_combined.split("\n")
    except Exception as e:
        print(f"批量翻译异常，回退原英文。错误信息: {e}")
        return texts

    if len(translated_lines) != len(texts):
        print(f"行数不匹配: 期望 {len(texts)} 行，实际得到 {len(translated_lines)} 行。回退单行翻译...")
        return [translate_single(t, sl, tl) for t in texts]

    final_results = []
    for idx, trans_line in enumerate(translated_lines):
        orig_text = texts[idx]
        if not isinstance(orig_text, str) or not orig_text.strip():
            final_results.append(orig_text)
            continue
            
        placeholders = all_placeholders[idx]
        restored = trans_line
        for i, placeholder in enumerate(placeholders):
            var_pattern = re.compile(rf"\s*__VAR_{i}__\s*|\s*__VAR_{i}__\s*|__VAR_{i}__", re.IGNORECASE)
            restored = var_pattern.sub(placeholder, restored)
            
        restored = restored.replace("  ", " ").strip()
        final_results.append(restored if restored else orig_text)
        
    return final_results

def translate_single(text, sl="en", tl="mn"):
    if not isinstance(text, str) or not text.strip():
        return text
        
    placeholders = []
    def replace_match(match):
        placeholder = match.group(0)
        placeholders.append(placeholder)
        return f" __VAR_{len(placeholders) - 1}__ "
        
    protected = PLACEHOLDER_REGEX.sub(replace_match, text)

    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": sl,
        "tl": tl,
        "dt": "t",
        "q": protected
    }
    
    try:
        encoded_query = urllib.parse.urlencode(params)
        full_url = f"{url}?{encoded_query}"
        req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data and data[0]:
                res = "".join([part[0] for part in data[0] if part[0]])
                for i, placeholder in enumerate(placeholders):
                    var_pattern = re.compile(rf"\s*__VAR_{i}__\s*|__VAR_{i}__", re.IGNORECASE)
                    res = var_pattern.sub(placeholder, res)
                return res.strip()
    except Exception as e:
        print(f"单行翻译出错: {e}")
    return text

def process_translation(en_path, mn_path):
    print(f"开始翻译: {en_path} -> {mn_path}")
    if not os.path.exists(en_path):
        print(f"错误: 找不到源文件 {en_path}")
        return False

    with open(en_path, "r", encoding="utf-8") as f:
        en_data = json.load(f)

    flat_data = flatten_dict(en_data)
    keys = list(flat_data.keys())
    values = list(flat_data.values())

    print(f"总计检测到 {len(keys)} 个词条。")
    BATCH_SIZE = 30
    translated_values = []

    for i in range(0, len(values), BATCH_SIZE):
        batch_vals = values[i:i+BATCH_SIZE]
        print(f"进度: {i}/{len(values)}")
        translated_batch = translate_batch(batch_vals)
        translated_values.extend(translated_batch)
        time.sleep(0.35)

    mn_flat_data = dict(zip(keys, translated_values))
    mn_data = inflate_dict(mn_flat_data)

    os.makedirs(os.path.dirname(mn_path), exist_ok=True)
    with open(mn_path, "w", encoding="utf-8") as f:
        json.dump(mn_data, f, ensure_ascii=False, indent=2)
        
    print(f"翻译保存成功: {mn_path}\n")
    return True

def register_language(langs_path):
    print(f"正在配置注册文件: {langs_path}")
    if not os.path.exists(langs_path):
        print(f"跳过: 未找到 {langs_path}")
        return

    with open(langs_path, "r", encoding="utf-8") as f:
        langs = json.load(f)

    # 检查是否已经注册
    if any(item.get("code") == "mn" for item in langs):
        print("蒙古语在注册文件中已存在。")
        return

    new_lang = {
        "code": "mn",
        "file": "mn.json",
        "iso": "mn-MN",
        "name": "Монгол"
    }

    # 按照字母表顺序插入到合适位置 (ko 之后，nl 之前)
    insert_index = 0
    for idx, lang in enumerate(langs):
        if lang["code"] == "nl":
            insert_index = idx
            break
            
    if insert_index > 0:
        langs.insert(insert_index, new_lang)
    else:
        langs.append(new_lang)

    with open(langs_path, "w", encoding="utf-8") as f:
        json.dump(langs, f, ensure_ascii=False, indent=2)
    print("蒙古语语言注册成功！")

def main():
    print("==================================================")
    print("开始自动生成 Hoppscotch 蒙古语翻译文件及其注册机制...")
    print("==================================================")

    # 1. 翻译 hoppscotch-common 包
    process_translation(COMMON_EN_PATH, COMMON_MN_PATH)
    register_language(COMMON_LANGS_PATH)

    # 2. 翻译 hoppscotch-sh-admin 包
    process_translation(ADMIN_EN_PATH, ADMIN_MN_PATH)
    register_language(ADMIN_LANGS_PATH)

    print("==================================================")
    print("Hoppscotch 蒙古语翻译自动化全部完成！")
    print("==================================================")

if __name__ == "__main__":
    main()

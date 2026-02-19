"""
验证模块（无状态，纯函数）
"""

import json
import re
from cache import Cache


def verify_citations(bibtex_content: str) -> str:
    cache = Cache()
    """
    验证BibTeX引用

    返回:
    {
      "valid": bool,           # 全部匹配
      "matched": [...],        # 匹配的引用（包含完整BibTeX）
      "mismatched": [...],     # 不匹配的引用（包含原因）
      "not_found": [...]        # 未找到的引用
    }
    """
    # 提取所有引用键
    keys = re.findall(r'@\w+\{([^,]+),', bibtex_content)

    matched = []
    mismatched = []
    not_found = []

    for key in keys:
        cached = cache.get(key)

        if not cached:
            # 未找到
            not_found.append({
                "key": key,
                "message": "此引用不在缓存中"
            })
            continue

        # 获取缓存的BibTeX
        cached_bibtex = cached.get("bibtex", "")

        # 从输入内容中提取完整BibTeX条目（通过匹配@Type{key,到下一个@或文件结束）
        input_bibtex = _extract_entry_by_key_simple(bibtex_content, key)

        # 比较（仅做空格和换行替换）
        if _normalize_for_compare(input_bibtex) == _normalize_for_compare(cached_bibtex):
            # 匹配成功，返回完整BibTeX
            matched.append({
                "key": key,
                "title": cached.get("title", ""),
                "bibtex": cached_bibtex
            })
        else:
            # 不匹配
            mismatched.append({
                "key": key,
                "title": cached.get("title", ""),
                "reason": "BibTeX内容不一致",
                "cached_bibtex": cached_bibtex,
                "input_bibtex": input_bibtex
            })

    return json.dumps({
        "valid": len(mismatched) == 0 and len(not_found) == 0,
        "total": len(keys),
        "matched_count": len(matched),
        "mismatched_count": len(mismatched),
        "not_found_count": len(not_found),
        "matched": matched,
        "mismatched": mismatched,
        "not_found": not_found
    }, ensure_ascii=False, indent=2)


def _extract_entry_by_key_simple(content: str, key: str) -> str:
    """从内容中提取指定键的完整BibTeX条目"""
    # 找到@Type{key,的开始位置
    pattern = re.compile(r'(@\w+\{' + re.escape(key) + r',)', re.IGNORECASE)
    match = pattern.search(content)

    if not match:
        return ""

    start = match.start()

    # 找到条目结束的位置（下一个@开头或文件结尾）
    # 简化：从start开始找，找到闭合大括号
    brace_count = 0
    in_entry = False

    for i in range(start, len(content)):
        if content[i] == '@' and not in_entry:
            in_entry = True

        if in_entry:
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return content[start:i+1]

    return ""


def _normalize_for_compare(s: str) -> str:
    """仅做空格和换行替换"""
    return re.sub(r'\s+', ' ', s).strip()

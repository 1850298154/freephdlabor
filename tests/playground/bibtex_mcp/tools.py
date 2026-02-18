"""
BibTeX 验证工具模块（无状态，纯函数）
"""

import json
import re
from api import search
from cache import Cache


cache = Cache()


def search_and_cache(query: str, limit: int = 5) -> str:
    """搜索论文并缓存"""
    papers = search(query, limit)

    for paper in papers:
        cache.add(paper["bibtex"], paper)

    results = [{
        "title": p["title"],
        "bibtex": p["bibtex"],
        "abstract": p["abstract"],
        "authors": p["authors"],
        "venue": p["venue"],
        "year": p["year"],
        "url": p["url"]
    } for p in papers]

    return json.dumps({
        "query": query,
        "count": len(results),
        "papers": results
    }, ensure_ascii=False, indent=2)


def verify_citations(bibtex_content: str) -> str:
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
    import re

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

        # 比较BibTeX内容是否一致
        cached_bibtex = cached.get("bibtex", "")

        # 从输入内容中提取这篇引用的完整BibTeX条目
        input_entry = _extract_entry_by_key(bibtex_content, key)
        if not input_entry:
            mismatched.append({
                "key": key,
                "title": cached.get("title", ""),
                "reason": "输入内容中未找到此BibTeX条目"
            })
            continue

        # 比较
        if _bibtex_equal(input_entry, cached_bibtex):
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
                "cached_bibtex": cached_bibtex[:100] + "..." if len(cached_bibtex) > 100 else cached_bibtex,
                "input_bibtex": input_entry[:100] + "..." if len(input_entry) > 100 else input_entry
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


def _extract_entry_by_key(content: str, key: str) -> str:
    """从内容中提取指定键的完整BibTeX条目"""
    # 简化方法：用字符串分割
    lines = content.split('\n')
    start_marker = '@Article{' + key + ','

    for line in lines:
        if line.strip().startswith(start_marker):
            return line.strip()

    return ""


def _bibtex_equal(bibtex1: str, bibtex2: str) -> bool:
    """比较两个BibTeX是否相等（忽略空格和换行）"""
    normalize = lambda s: re.sub(r'\s+', ' ', s).strip().replace('\n', ' ')
    return normalize(bibtex1) == normalize(bibtex2)

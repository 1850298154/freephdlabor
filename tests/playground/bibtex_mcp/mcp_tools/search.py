"""
搜索和缓存模块（无状态，纯函数）
"""

import json
from api import search
from cache import Cache


def search_and_cache(query: str, limit: int = 5) -> str:
    """搜索论文并缓存"""
    cache = Cache()
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

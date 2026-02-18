"""
工具函数（无状态）
"""

import json
from api import search
from cache import Cache


cache = Cache()


def search_bibtex(query: str, limit: int = 5) -> str:
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
    """验证BibTeX引用"""
    result = cache.verify(bibtex_content)
    return json.dumps(result, ensure_ascii=False, indent=2)

"""
从Semantic Scholar API直接获取现成BibTeX - 最简实现
https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/get_graph_paper_relevance_search

用法:
    python bibtex_from_api.py "attention is all you need"
"""

import requests
import json
import sys

def get_bibtex(query, limit=5):
    """从Semantic Scholar获取BibTeX"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"  # 5分钟 1000次
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,citationStyles"
    }
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()

    results = []
    for paper in data.get("data", []):
        bibtex = paper.get("citationStyles", {}).get("bibtex")
        if bibtex:
            results.append(bibtex)
    return results

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "transformer"
    for bibtex in get_bibtex(query):
        print(bibtex)
        print("-" * 60)

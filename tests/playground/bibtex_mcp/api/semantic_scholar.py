"""
Semantic Scholar API 调用模块
"""

import requests
import sys
import os
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException
from typing import Dict, Any

# 添加父目录到路径以支持直接运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


@sleep_and_retry
@limits(calls=Config.RATE_LIMIT_CALLS, period=Config.RATE_LIMIT_PERIOD)
@retry(
    stop=stop_after_attempt(Config.RETRY_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=Config.RETRY_WAIT_MIN, max=Config.RETRY_WAIT_MAX),
    retry=retry_if_exception_type((RequestException, requests.HTTPError))
)
def search_papers(query: str, limit: int = 5) -> list[Dict[str, Any]]:
    """
    从Semantic Scholar搜索论文

    Args:
        query: 搜索关键词
        limit: 返回结果数量

    Returns:
        论文列表，包含标题、作者、BibTeX等信息
    """
    headers = {}
    if Config.S2_API_KEY:
        headers["X-API-KEY"] = Config.S2_API_KEY

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,citationStyles,abstract,authors,venue,year,url,externalIds"
    }

    resp = requests.get(
        Config.SEMANTIC_SCHOLAR_URL,
        params=params,
        timeout=30,
        headers=headers
    )
    resp.raise_for_status()
    data = resp.json()

    papers = []
    for item in data.get("data", []):
        papers.append({
            "title": item.get("title", ""),
            "abstract": item.get("abstract", ""),
            "authors": [a.get("name", "") for a in item.get("authors", [])],
            "venue": item.get("venue", ""),
            "year": item.get("year", ""),
            "url": item.get("url", ""),
            "arxiv_id": item.get("externalIds", {}).get("ArXiv", ""),
            "bibtex": item.get("citationStyles", {}).get("bibtex", "")
        })

    return papers

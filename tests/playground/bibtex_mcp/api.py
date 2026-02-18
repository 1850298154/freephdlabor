"""
Semantic Scholar API 调用（无状态函数）
"""

import requests
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException
from config import API_URL, API_KEY


@sleep_and_retry
@limits(calls=1, period=1)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((RequestException, requests.HTTPError))
)
def search(query: str, limit: int = 5) -> list[dict]:
    """搜索论文"""
    headers = {}
    if API_KEY:
        headers["X-API-KEY"] = API_KEY

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,citationStyles,abstract,authors,venue,year,url"
    }

    resp = requests.get(API_URL, params=params, timeout=30, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    papers = []
    for item in data.get("data", []):
        bibtex = item.get("citationStyles", {}).get("bibtex", "")
        if bibtex:
            papers.append({
                "title": item.get("title", ""),
                "abstract": item.get("abstract", ""),
                "authors": [a.get("name", "") for a in item.get("authors", [])],
                "venue": item.get("venue", ""),
                "year": item.get("year", ""),
                "url": item.get("url", ""),
                "bibtex": bibtex
            })

    return papers

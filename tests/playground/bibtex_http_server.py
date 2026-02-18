"""
BibTeX HTTP API Server - 网络请求版本

启动方式:
    python bibtex_http_server.py

服务运行在: http://localhost:8000

API端点:
    POST /api/bibtex
        - 请求体: {"query": "search terms", "limit": 3}
        - 返回: {"results": [...], "bibtex": [...]}

    GET /api/health
        - 健康检查
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests
import time
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="BibTeX API", version="1.0.0")

# 添加CORS支持（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 请求/响应模型 ============
class BibTeXRequest(BaseModel):
    query: str
    limit: int = 3


class BibTeXResponse(BaseModel):
    query: str
    results: list[dict]
    bibtex: list[str]


# ============ 限流 + 重试 ============
# 1分钟最多5次请求（Semantic Scholar免费限制约100/5分钟）
@sleep_and_retry
@limits(calls=5, period=60)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((RequestException, requests.HTTPError))
)
def fetch_bibtex_from_api(query: str, limit: int = 3) -> tuple[list[dict], list[str]]:
    """从Semantic Scholar获取BibTeX（带重试和限流）"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    headers = {}

    S2_API_KEY = os.getenv("S2_API_KEY")
    if S2_API_KEY:
        headers["X-API-KEY"] = S2_API_KEY

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,citationStyles,abstract,authors,venue,year"
    }

    resp = requests.get(url, params=params, timeout=30, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    papers = []
    bibtex_list = []

    for paper in data.get("data", []):
        papers.append({
            "title": paper.get("title"),
            "authors": [a.get("name") for a in paper.get("authors", [])],
            "venue": paper.get("venue"),
            "year": paper.get("year"),
            "abstract": paper.get("abstract", "")[:200] + "..." if paper.get("abstract") else "",
        })

        bibtex = paper.get("citationStyles", {}).get("bibtex")
        if bibtex:
            bibtex_list.append(bibtex)

    return papers, bibtex_list


# ============ API端点 ============
@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "BibTeX API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/bibtex": "Search for BibTeX entries",
            "GET /api/health": "Health check",
            "GET /docs": "API documentation"
        }
    }


@app.get("/api/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "bibtex-api",
        "timestamp": time.time()
    }


@app.post("/api/bibtex", response_model=BibTeXResponse)
async def get_bibtex(request: BibTeXRequest):
    """获取BibTeX"""
    try:
        papers, bibtex_list = fetch_bibtex_from_api(request.query, request.limit)
        return BibTeXResponse(
            query=request.query,
            results=papers,
            bibtex=bibtex_list
        )
    except requests.HTTPError as e:
        raise HTTPException(status_code=429, detail=f"Rate limited or API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


# ============ 启动服务器 ============
if __name__ == "__main__":
    # 启动参数可在 .env 文件中配置:
    # HOST=0.0.0.0
    # PORT=8000

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║           BibTeX HTTP API Server                          ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  服务地址: http://{host}:{port}                         ║
    ║  API文档: http://{host}:{port}/docs                     ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  POST /api/bibtex                                        ║
    ║    Body: {{"query": "attention", "limit": 3}}            ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(app, host=host, port=port)

"""
BibTeX MCP Server 配置
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """全局配置"""

    # 服务器配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))

    # API配置
    SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    S2_API_KEY = os.getenv("S2_API_KEY", "")

    # 缓存配置
    CACHE_FILE = os.getenv("BIBTEX_CACHE_FILE", ".bibtex_cache.json")

    # 限流配置（1分钟最多5次）
    RATE_LIMIT_CALLS = 5
    RATE_LIMIT_PERIOD = 60

    # 重试配置
    RETRY_MAX_ATTEMPTS = 3
    RETRY_WAIT_MIN = 1
    RETRY_WAIT_MAX = 4

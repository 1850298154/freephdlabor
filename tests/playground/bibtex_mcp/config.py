"""
配置
"""

import os
from dotenv import load_dotenv

load_dotenv()


HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
CACHE_FILE = ".bibtex_cache.json"
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
API_KEY = os.getenv("S2_API_KEY", "")

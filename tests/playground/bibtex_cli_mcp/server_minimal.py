"""
BibTeX MCP Server - 单文件版

功能：搜索论文 + 验证引用 + 跨进程限流
安装：pip install mcp requests
配置：见底部 mcp_config
"""

import os
import time
import json
import re
import requests
from pathlib import Path
from mcp.server import FastMCP


# ==================== 配置 ====================
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
API_KEY = os.getenv("S2_API_KEY", "")
CACHE_FILE = Path(__file__).parent / ".bibtex.json"
QUEUE_FILE = Path(__file__).parent / "request_queue.json"

mcp = FastMCP("bibtex-server")


# ==================== 简化的限流器 ====================
class RateLimiter:
    """跨进程文件队列限流器（确保每秒一次）"""

    def __init__(self, queue_file: str):
        self.queue_file = Path(queue_file)
        self.lock_file = self.queue_file.with_suffix('.lock')
        if not self.queue_file.exists():
            self._write([])

    def wait(self) -> str:
        """等待轮次，返回请求ID"""
        # 获取锁
        while True:
            try:
                fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                # 检查死锁（30秒超时）
                if self.lock_file.exists():
                    age = time.time() - self.lock_file.stat().st_mtime
                    if age > 30:
                        try: os.remove(self.lock_file)
                        except: pass
                time.sleep(0.01)

        try:
            # 读取队列
            queue = self._read()
            now = time.time()

            # 清理过期请求（60秒）
            queue = [r for r in queue if now - r['created'] < 60]

            # 计算下次时间
            last = queue[-1]['time'] if queue else 0
            next_time = max(now, last) + 1.0

            # 生成ID
            req_id = f"req_{os.getpid()}_{now}"

            # 加入队列
            queue.append({'id': req_id, 'time': next_time, 'created': now})
            self._write(queue)

            # 释放锁
            self._unlock()

            # 等待
            wait = next_time - now
            if wait > 0:
                time.sleep(wait)

            return req_id
        except:
            self._unlock()
            raise

    def done(self, req_id: str):
        """完成请求"""
        if not self._lock(): return
        try:
            queue = self._read()
            queue = [r for r in queue if r['id'] != req_id]
            self._write(queue)
        finally:
            self._unlock()

    def _lock(self) -> bool:
        """获取锁"""
        for _ in range(10):
            try:
                os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return True
            except:
                time.sleep(0.1)
        return False

    def _unlock(self):
        """释放锁"""
        try: os.remove(self.lock_file)
        except: pass

    def _read(self) -> list:
        """读取队列"""
        try:
            with open(self.queue_file) as f:
                return json.load(f)
        except:
            return []

    def _write(self, data: list):
        """写入队列（原子）"""
        tmp = self.queue_file.with_suffix('.tmp')
        with open(tmp, 'w') as f:
            json.dump(data, f)
        tmp.replace(self.queue_file)


limiter = RateLimiter(str(QUEUE_FILE))


# ==================== 缓存 ====================
class Cache:
    """简单缓存"""
    _data = {}
    def __new__(cls):
        if not cls._data and CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    cls._data = json.load(f)
            except: pass
        return super().__new__(cls)

    @classmethod
    def get(cls, key): return cls._data.get(key)

    @classmethod
    def add(cls, bibtex: str, info: dict):
        if '{' in bibtex:
            key = bibtex.split('{')[1].split(',')[0].strip()
            if key:
                cls._data[key] = info
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cls._data, f, ensure_ascii=False, indent=2)


# ==================== API ====================
def search_papers(query: str, limit: int = 5) -> list:
    """搜索论文"""
    req_id = limiter.wait()
    try:
        headers = {"X-API-KEY": API_KEY} if API_KEY else {}
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,citationStyles,abstract,authors,venue,year,url"
        }
        resp = requests.get(API_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()

        papers = []
        for item in resp.json().get("data", []):
            bibtex = item.get("citationStyles", {}).get("bibtex", "")
            if bibtex:
                papers.append({
                    "title": item.get("title", ""),
                    "abstract": item.get("abstract", ""),
                    "authors": [a["name"] for a in item.get("authors", [])],
                    "venue": item.get("venue", ""),
                    "year": item.get("year", ""),
                    "url": item.get("url", ""),
                    "bibtex": bibtex
                })
        return papers
    finally:
        limiter.done(req_id)


# ==================== MCP 工具 ====================
@mcp.tool()
def search_bibtex_and_abstract(query: str, limit: int = 5) -> str:
    """搜索论文并缓存"""
    papers = search_papers(query, limit)
    for p in papers:
        Cache.add(p["bibtex"], p)

    return json.dumps({
        "query": query,
        "count": len(papers),
        "papers": [{
            "title": p["title"],
            "bibtex": p["bibtex"],
            "abstract": p["abstract"],
            "authors": p["authors"],
            "venue": p["venue"],
            "year": p["year"],
            "url": p["url"]
        } for p in papers]
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def verify_citations(bibtex_content: str) -> str:
    """验证引用"""
    keys = re.findall(r'@\w+\{([^,]+),', bibtex_content)
    matched, mismatched, not_found = [], [], []

    for key in keys:
        cached = Cache.get(key)
        if not cached:
            not_found.append({"key": key, "reason": "未找到"})
        else:
            title = re.search(r'title\s*=\s*[{"]([^}"]+)[}"]', bibtex_content)
            if title and title.group(1).lower() in cached["title"].lower():
                matched.append({"key": key, "title": cached["title"]})
            else:
                mismatched.append({"key": key, "cached_title": cached["title"]})

    return json.dumps({
        "valid": not mismatched and not not_found,
        "total": len(keys),
        "matched": len(matched),
        "mismatched": len(mismatched),
        "not_found": len(not_found),
        "details": {"matched": matched, "mismatched": mismatched, "not_found": not_found}
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    print(f"BibTeX MCP Server | API Key: {'已设置' if API_KEY else '未设置'}", file=sys.stderr)
    mcp.run(transport="stdio")


# ==================== MCP 配置 ====================
"""
{
  "mcpServers": {
    "bibtex": {
      "command": "python",
      "args": ["D:\\zyt\\git_ln\\freephdlabor\\tests\\playground\\bibtex_cli_mcp\\server.py"],
      "env": {"S2_API_KEY": "s2k-Fa0SA2LjDGWZ1iYaHgpwp7GqUQHrHkmv05EWFh9v"},
      "type": "stdio"
    }
  }
}
"""

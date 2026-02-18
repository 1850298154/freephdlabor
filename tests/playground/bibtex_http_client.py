"""
BibTeX HTTP Client - 测试API服务器

用法:
    python bibtex_http_client.py "attention is all you need"
"""

import requests
import sys


def get_bibtex(api_url: str, query: str, limit: int = 3):
    """调用BibTeX API"""
    url = f"{api_url.rstrip('/')}/api/bibtex"
    payload = {"query": query, "limit": limit}

    print(f"请求: POST {url}")
    print(f"参数: {payload}\n")

    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main():
    # API配置（可在ccswitch中配置）
    API_URL = os.getenv("BIBTEX_API_URL", "http://localhost:8000")

    # 从命令行获取查询参数
    query = sys.argv[1] if len(sys.argv) > 1 else "transformer"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    # 测试健康检查
    print("=" * 60)
    print("健康检查...")
    print("=" * 60)
    health_resp = requests.get(f"{API_URL}/api/health", timeout=5)
    print(f"状态: {health_resp.json()['status']}\n")

    # 获取BibTeX
    print("=" * 60)
    print(f"搜索: {query}")
    print("=" * 60)

    result = get_bibtex(API_URL, query, limit)

    print(f"\n找到 {len(result['results'])} 篇论文:\n")

    for i, paper in enumerate(result["results"], 1):
        print(f"{i}. {paper['title']}")
        print(f"   作者: {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
        print(f"   年份: {paper['year']}, 会议/期刊: {paper['venue']}")
        print()

    print("=" * 60)
    print("BibTeX:")
    print("=" * 60)
    for bibtex in result["bibtex"]:
        print(bibtex)
        print("-" * 60)


if __name__ == "__main__":
    import os
    main()

"""
测试脚本 - 验证 BibTeX CLI MCP Server 是否正常工作

使用方法：
python test_server.py
"""

import sys
import time
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_import():
    """测试模块导入"""
    try:
        from server import search_papers, Cache, mcp
        print("[OK] 模块导入成功")
        return True
    except Exception as e:
        print(f"[FAIL] 模块导入失败: {e}")
        return False

def test_cache():
    """测试缓存功能"""
    try:
        from server import Cache
        cache = Cache()
        print("[OK] 缓存初始化成功")
        return True
    except Exception as e:
        print(f"[FAIL] 缓存初始化失败: {e}")
        return False

def test_api_key():
    """测试 API Key 是否设置"""
    import os
    api_key = os.getenv("S2_API_KEY", "")
    if api_key:
        print(f"[OK] API Key 已设置: {api_key[:20]}...")
        return True
    else:
        print("[WARN] API Key 未设置（将使用默认限制）")
        return True  # 不是错误，只是警告

def test_search():
    """测试搜索功能"""
    try:
        from server import search_papers

        print("\n正在测试搜索功能（请稍候）...")
        time.sleep(1)  # 遵循速率限制

        papers = search_papers("attention", limit=1)

        if papers:
            print(f"[OK] 搜索成功：找到 {len(papers)} 篇论文")
            print(f"  标题: {papers[0]['title'][:50]}...")
            return True
        else:
            print("[WARN] 搜索成功但未找到论文")
            return True
    except Exception as e:
        print(f"[FAIL] 搜索失败: {e}")
        print("  可能原因：API 速率限制、网络问题或 API Key 无效")
        return False

def test_mcp_tools():
    """测试 MCP 工具定义"""
    try:
        from server import search_bibtex_and_abstract, verify_citations_with_mismatches

        # 检查工具是否正确装饰
        if hasattr(search_bibtex_and_abstract, '__wrapped__'):
            print("[OK] search_bibtex_and_abstract 工具定义正确")
        else:
            print("[WARN] search_bibtex_and_abstract 可能未正确装饰")

        if hasattr(verify_citations_with_mismatches, '__wrapped__'):
            print("[OK] verify_citations_with_mismatches 工具定义正确")
        else:
            print("[WARN] verify_citations_with_mismatches 可能未正确装饰")

        return True
    except Exception as e:
        print(f"[FAIL] MCP 工具测试失败: {e}")
        return False

def main():
    print("=" * 60)
    print("BibTeX CLI MCP Server 测试")
    print("=" * 60)

    results = []

    print("\n1. 测试模块导入...")
    results.append(test_import())

    print("\n2. 测试缓存功能...")
    results.append(test_cache())

    print("\n3. 测试 API Key...")
    results.append(test_api_key())

    print("\n4. 测试 MCP 工具...")
    results.append(test_mcp_tools())

    print("\n5. 测试搜索功能（需要网络连接）...")
    results.append(test_search())

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("[OK] 所有测试通过，服务器已准备就绪！")
    elif passed >= total - 1:
        print("[WARN] 大部分测试通过，服务器基本可用")
        print("  搜索功能可能因 API 限制暂时不可用，请稍后重试")
    else:
        print("[FAIL] 多个测试失败，请检查配置")

    print("=" * 60)

if __name__ == "__main__":
    main()

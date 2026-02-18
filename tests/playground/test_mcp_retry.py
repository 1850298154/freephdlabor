"""测试MCP服务器的重试和限流功能"""

import asyncio
from bibtex_mcp_client import get_bibtex


async def test_rate_limit():
    """测试限流 - 连续请求6次，前5次应该成功，第6次会被限流"""
    print("=== 测试限流：连续请求6次 ===")
    for i in range(6):
        try:
            print(f"\n第 {i+1} 次请求...")
            result = await get_bibtex("test", limit=1)
            print(f"[OK] 成功")
        except Exception as e:
            print(f"[FAIL] 失败: {e}")


async def test_retry():
    """测试重试 - 请求一个不存在的URL（如果配置了的话）"""
    print("\n=== 测试重试 ===")
    # 这里测试正常请求，看重试逻辑是否正确处理
    try:
        result = await get_bibtex("nonexistent_paper_xyz123", limit=1)
        print("请求完成（可能没有结果）")
    except Exception as e:
        print(f"异常: {e}")


if __name__ == "__main__":
    asyncio.run(test_rate_limit())
    # asyncio.run(test_retry())

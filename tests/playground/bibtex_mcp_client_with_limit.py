"""
BibTeX MCP Client - 连接到MCP服务器获取BibTeX（带限流测试）

启动方式:
    python bibtex_mcp_client_with_limit.py "attention is all you need"

或者测试限流:
    python bibtex_mcp_client_with_limit.py --test-rate-limit
"""

import asyncio
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def get_bibtex(query: str, limit: int = 3) -> str:
    """通过MCP服务器获取BibTeX"""
    # 配置MCP服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=["tests/playground/bibtex_mcp_server_with_limit.py"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化会话
            await session.initialize()

            # 调用 get_bibtex 工具
            result = await session.call_tool(
                "get_bibtex",
                arguments={"query": query, "limit": limit}
            )

            # 返回结果
            return result.content[0].text


async def test_rate_limit():
    """测试限流功能"""
    print("=== 测试限流：连续请求7次（前5次快速，第6次等待）===")
    print("配置: 每分钟最多5次请求\n")

    for i in range(7):
        start_time = time.time()
        try:
            print(f"[{i+1}/7] 请求中...")
            result = await get_bibtex("test", limit=1)
            elapsed = time.time() - start_time
            print(f"[{i+1}/7] 成功 (耗时 {elapsed:.2f}秒)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[{i+1}/7] 失败 (耗时 {elapsed:.2f}秒): {e}")
        print()


async def main():
    """主函数"""
    if "--test-rate-limit" in sys.argv:
        await test_rate_limit()
    else:
        query = sys.argv[1] if len(sys.argv) > 1 else "transformer"
        print(f"搜索: {query}")
        print("-" * 60)

        result = await get_bibtex(query)

        print("-" * 60)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())

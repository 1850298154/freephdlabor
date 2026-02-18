"""
BibTeX MCP Client - 连接到MCP服务器获取BibTeX

启动方式:
    python bibtex_mcp_client.py "attention is all you need"
"""

import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def get_bibtex(query: str, limit: int = 3) -> str:
    """通过MCP服务器获取BibTeX"""
    # 配置MCP服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=["tests/playground/bibtex_mcp_server.py"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化会话
            await session.initialize()

            # 获取可用工具
            tools = await session.list_tools()
            print(f"可用工具: {[t.name for t in tools.tools]}")

            # 调用 get_bibtex 工具
            result = await session.call_tool(
                "get_bibtex",
                arguments={"query": query, "limit": limit}
            )

            # 返回结果
            return result.content[0].text


async def main():
    """主函数"""
    query = sys.argv[1] if len(sys.argv) > 1 else "transformer"
    print(f"搜索: {query}")
    print("-" * 60)

    result = await get_bibtex(query)

    print("-" * 60)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

"""通过 stdio 启动并调用同目录的 MCP Server。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_client() -> None:
    server_script = Path(__file__).with_name("server.py")
    params = StdioServerParameters(command=sys.executable, args=[str(server_script)])

    async with (
        stdio_client(params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        print("Tools:", [tool.name for tool in tools.tools])

        result = await session.call_tool("search_notes", {"query": "LangGraph"})
        print("Tool result:", result.content)

        resource = await session.read_resource("notes://catalog")
        print("Resource:", resource.contents[0].text)


def main() -> None:
    asyncio.run(run_client())


if __name__ == "__main__":
    main()

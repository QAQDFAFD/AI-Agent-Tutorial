"""一个只读的本地 MCP Server。"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ai-agent-tutorial")

NOTES = {
    "agent-loop": "Agent Loop 是判断、行动、观察、再判断的受控循环。",
    "langgraph": "LangGraph 用 State、Node 和 Edge 编排可恢复工作流。",
    "rag": "RAG 先检索相关依据，再让模型基于有限证据生成回答。",
}


@mcp.tool()
def search_notes(query: str) -> list[dict[str, str]]:
    """搜索公开教学笔记；只读，不访问用户私人文件。"""
    return [
        {"id": note_id, "text": text}
        for note_id, text in NOTES.items()
        if query.lower() in note_id.lower() or query.lower() in text.lower()
    ]


@mcp.resource("notes://catalog")
def note_catalog() -> str:
    """返回可用公开笔记的 ID。"""
    return "\n".join(sorted(NOTES))


if __name__ == "__main__":
    mcp.run(transport="stdio")


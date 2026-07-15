# Demo 08：MCP Server / Client

对应[第 09 章](../../docs/09-mcp.md)。无需模型或 API Key。

```bash
uv run python -m demos.08_mcp.client
```

Client 通过 stdio 启动 Server，先发现工具，再调用 `search_notes`，最后读取 `notes://catalog` resource。


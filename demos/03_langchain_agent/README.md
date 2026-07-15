# Demo 03：LangChain `create_agent`

对应[第 04 章](../../docs/04-langchain-agent.md)。需要 `OPENAI_API_KEY`。

```bash
cp .env.example .env
uv run python -m demos.03_langchain_agent.main
```

Demo 使用两个边界明确的只读工具，并通过 `ToolStrategy(SupportAnswer)` 保证最终输出符合 Pydantic schema。


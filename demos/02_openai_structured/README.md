# Demo 02：结构化输出

对应[第 02 章](../../docs/02-models-prompts-structured-output.md)。无 Key 时运行本地分类，有 Key 时调用 `client.responses.parse(..., text_format=TicketDecision)`。

```bash
cp .env.example .env
uv run python -m demos.02_openai_structured.main
```

本地规则不是 LLM 替代品，它的作用是说明：无论决策来自规则还是模型，上层都只接收同一份经过验证的 `TicketDecision`。

`tool_calling.py` 是 Demo 01 手写循环的"真实模型版"（需要 API Key）：

```bash
uv run python -m demos.02_openai_structured.tool_calling
```

对照 `demos/01_agent_loop/main.py` 阅读，可以看到 allowlist、Pydantic 校验和 observation 回传在真实 Responses API 协议下的写法。


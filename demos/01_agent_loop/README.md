# Demo 01：手写 Agent Loop

对应[第 01 章](../../docs/01-agent-foundations.md)和[第 03 章](../../docs/03-tools-and-actions.md)。无需 API Key。

```bash
uv run python -m demos.01_agent_loop.main
```

请重点读 `run_agent()`，它展示模型决策、工具 allowlist、Pydantic 参数校验、observation 回传、trace 和最大步数。`RuleBasedModel` 只是可预测的模型替身，可换成任意真实模型适配器。


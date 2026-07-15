# Demo 07：Router + Specialists

对应[第 08 章](../../docs/08-multi-agent.md)。无需 API Key。

```bash
uv run python -m demos.07_multi_agent.main
```

Router 只输出 `Delegation`，专家只返回 `AgentResult`。先把路由和通信合同测稳，再决定是否用 LLM 替换其中某个函数。


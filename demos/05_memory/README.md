# Demo 05：短期记忆与 thread 隔离

对应[第 06 章](../../docs/06-memory-and-context.md)。无需 API Key。

```bash
uv run python -m demos.05_memory.main
```

同一个 `thread_id` 会沿用 checkpoint，不同 thread 不共享状态。`InMemorySaver` 只适合教学和测试，生产请使用持久化 checkpointer。


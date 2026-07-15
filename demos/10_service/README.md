# Demo 10：FastAPI 服务

对应[第 12 章](../../docs/12-production.md)。无需 API Key。

```bash
uv run uvicorn demos.10_service.app:app --reload
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"thread_id":"demo-1","message":"LangGraph 是什么？"}'
```

`/chat/stream` 提供 SSE 事件流版本，可用 `curl -sN` 观察 `agent_started / tool_called / tool_finished / final` 事件。

内存 thread 计数只用于教学；多进程生产部署必须换成 Redis/PostgreSQL，并增加认证、限流和持久化 trace。


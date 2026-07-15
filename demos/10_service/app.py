"""带并发上限、超时、thread 状态和 SSE 事件流的教学版 FastAPI 服务。"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="AI Agent Tutorial Service", version="0.1.0")
MODEL_CONCURRENCY = asyncio.Semaphore(4)
THREAD_LOCK = asyncio.Lock()
THREAD_TURNS: dict[str, int] = defaultdict(int)


class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    message: str = Field(min_length=1, max_length=2_000)


class ChatResponse(BaseModel):
    thread_id: str
    turn: int
    answer: str
    source_ids: list[str] = Field(default_factory=list)


async def local_agent(message: str) -> tuple[str, list[str]]:
    """可替换为 graph.ainvoke；这里保持离线和可测试。"""
    await asyncio.sleep(0)  # 明确让出事件循环
    if "LangGraph" in message:
        return "LangGraph 用 State、Node 和 Edge 编排有状态工作流。", ["tutorial-langgraph"]
    if "Agent" in message or "智能体" in message:
        return "Agent 是目标驱动的受控循环：判断、行动、观察并更新状态。", ["tutorial-agent"]
    return "我能回答本教程中的 Agent 与 LangGraph 基础问题。", []


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        async with MODEL_CONCURRENCY:
            answer, source_ids = await asyncio.wait_for(local_agent(request.message), timeout=3)
        async with THREAD_LOCK:
            THREAD_TURNS[request.thread_id] += 1
            turn = THREAD_TURNS[request.thread_id]
        return ChatResponse(
            thread_id=request.thread_id,
            turn=turn,
            answer=answer,
            source_ids=source_ids,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Agent execution timed out") from exc


async def agent_events(message: str) -> AsyncIterator[str]:
    """把一次运行拆成对用户有意义的事件流；生产中可换成 graph.astream 的真实事件。"""

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    yield sse("agent_started", {"message_length": len(message)})
    await asyncio.sleep(0.1)  # 模拟模型/工具耗时，让前端能观察到事件间隔
    yield sse("tool_called", {"tool": "local_agent"})
    answer, source_ids = await local_agent(message)
    yield sse("tool_finished", {"source_ids": source_ids})
    yield sse("final", {"answer": answer})


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """SSE 端点：用户看到“正在查询”这类进度，比转圈图标更安心。"""
    return StreamingResponse(agent_events(request.message), media_type="text/event-stream")


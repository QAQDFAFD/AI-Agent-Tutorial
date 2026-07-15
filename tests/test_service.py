import importlib

import pytest

service = importlib.import_module("demos.10_service.app")


@pytest.mark.asyncio
async def test_chat_keeps_thread_turn_count():
    thread_id = "pytest-thread"
    first = await service.chat(service.ChatRequest(thread_id=thread_id, message="Agent 是什么？"))
    second = await service.chat(service.ChatRequest(thread_id=thread_id, message="LangGraph 呢？"))
    assert first.turn == 1
    assert second.turn == 2
    assert second.source_ids == ["tutorial-langgraph"]


@pytest.mark.asyncio
async def test_stream_emits_ordered_events_and_final_answer():
    events = [chunk async for chunk in service.agent_events("LangGraph 是什么？")]
    names = [chunk.split("\n", 1)[0].removeprefix("event: ") for chunk in events]
    assert names == ["agent_started", "tool_called", "tool_finished", "final"]
    assert "LangGraph" in events[-1]


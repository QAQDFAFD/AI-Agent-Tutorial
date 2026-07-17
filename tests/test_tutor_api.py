import json

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from tutor.api.app import create_app
from tutor.config import Settings


class FakeAgent:
    async def astream(self, payload, config=None, stream_mode=None):
        yield (
            "updates",
            {
                "model": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "search_tutorial",
                                    "args": {"query": "checkpoint"},
                                    "id": "c1",
                                }
                            ],
                        )
                    ]
                }
            },
        )
        source = {
            "chapter_id": "05",
            "chapter_title": "05｜LangGraph",
            "heading": "Checkpoint",
            "anchor": "checkpoint",
            "text": "...",
            "score": 0.9,
        }
        yield (
            "updates",
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps([source], ensure_ascii=False),
                            name="search_tutorial",
                            tool_call_id="c1",
                        )
                    ]
                }
            },
        )
        yield (
            "messages",
            (AIMessageChunk(content="Checkpoint 让图可恢复"), {"langgraph_node": "model"}),
        )


def _settings() -> Settings:
    return Settings(_env_file=None, openai_api_key="")


def _events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_chapters_listing_and_content():
    with TestClient(create_app(_settings(), agent=FakeAgent())) as client:
        listing = client.get("/api/chapters").json()
        assert any(item["id"] == "05" for item in listing)
        detail = client.get("/api/chapters/05").json()
        assert "<h2" in detail["html"]
        assert "/assets/diagrams/" in detail["html"]  # 相对图片路径已改写
        assert client.get("/api/chapters/nope").status_code == 404


def test_demo_page_renders_code_and_rejects_traversal():
    with TestClient(create_app(_settings(), agent=FakeAgent())) as client:
        detail = client.get("/api/demos/01_agent_loop").json()
        assert detail["title"] == "demos/01_agent_loop"
        assert "language-python" in detail["html"] or "<code" in detail["html"]
        assert "main.py" in detail["html"]
        assert client.get("/api/demos/..%2Fdocs").status_code == 404
        assert client.get("/api/demos/nope").status_code == 404


def test_chapter_demo_links_rewritten_to_demo_route():
    with TestClient(create_app(_settings(), agent=FakeAgent())) as client:
        html = client.get("/api/chapters/01").json()["html"]
        assert 'href="#/demo/01_agent_loop"' in html
        assert "../demos/" not in html


def test_chat_streams_expected_event_sequence():
    with (
        TestClient(create_app(_settings(), agent=FakeAgent())) as client,
        client.stream(
            "POST", "/api/chat", json={"thread_id": "t-1", "message": "checkpoint 是什么"}
        ) as response,
    ):
        body = "".join(response.iter_text())
    names = [name for name, _ in _events(body)]
    assert names == ["tool_call", "sources", "token", "final"]
    sources = dict(_events(body))["sources"]
    assert sources[0]["chapter_id"] == "05"


def test_chat_disabled_without_api_key():
    with TestClient(create_app(_settings())) as client:
        response = client.post("/api/chat", json={"thread_id": "t", "message": "hi"})
        assert response.status_code == 503
        assert client.get("/api/health").json()["chat_enabled"] is False

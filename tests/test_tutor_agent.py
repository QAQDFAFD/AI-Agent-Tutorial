import json
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from tests.test_tutor_rag import CHUNKS, FakeEmbeddingClient
from tutor.agent.graph import build_agent
from tutor.agent.tools import make_tools
from tutor.config import Settings
from tutor.ingest.loader import Chapter
from tutor.rag.retriever import Retriever

CHAPTERS = [Chapter("05", "05｜LangGraph", Path("docs/x.md"), "")]


class ScriptedChatModel(BaseChatModel):
    responses: list[AIMessage]

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        message = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        return ChatResult(generations=[ChatGeneration(message=message)])


def _retriever() -> Retriever:
    return Retriever.build(FakeEmbeddingClient(), CHUNKS, top_k=2)


def test_search_tool_returns_json_with_sources():
    tools = make_tools(_retriever(), CHAPTERS)
    search = next(tool for tool in tools if tool.name == "search_tutorial")
    payload = json.loads(search.invoke({"query": "checkpoint 恢复"}))
    assert payload[0]["chapter_id"] == "05"
    assert {"chapter_id", "chapter_title", "heading", "anchor", "text", "score"} <= set(payload[0])


def test_agent_calls_tool_then_answers():
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "search_tutorial", "args": {"query": "checkpoint"}, "id": "c1"}
                ],
            ),
            AIMessage(content="Checkpoint 让图可恢复（第 05 章）。"),
        ]
    )
    agent = build_agent(Settings(_env_file=None), _retriever(), CHAPTERS, model=model)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "checkpoint 是什么？"}]},
        config={"configurable": {"thread_id": "t1"}},
    )
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert tool_messages and tool_messages[0].name == "search_tutorial"
    assert "第 05 章" in result["messages"][-1].content

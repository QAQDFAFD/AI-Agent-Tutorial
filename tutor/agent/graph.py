"""组装教学 Agent：标准工具调用形态，遵循教程第 4 章自身的选型建议。"""

from __future__ import annotations

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from tutor.agent.prompts import SYSTEM_PROMPT
from tutor.agent.tools import make_tools
from tutor.config import Settings
from tutor.ingest.loader import Chapter
from tutor.rag.retriever import Retriever


def build_agent(settings: Settings, retriever: Retriever, chapters: list[Chapter], model=None):
    if model is None:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.request_timeout_seconds,
        )
    return create_agent(
        model=model,
        tools=make_tools(retriever, chapters),
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )

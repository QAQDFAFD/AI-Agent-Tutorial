"""教学 Agent 的两个只读工具。search_tutorial 返回 JSON 字符串，便于 API 层可靠解析。"""

from __future__ import annotations

import json

from langchain.tools import tool

from tutor.ingest.loader import Chapter
from tutor.rag.retriever import Retriever

MAX_SNIPPET_CHARS = 800


def make_tools(retriever: Retriever, chapters: list[Chapter]) -> list:
    @tool
    def search_tutorial(query: str) -> str:
        """检索教程正文并返回相关片段（JSON）。回答任何教程内容问题前必须先调用；
        query 使用具体的中文关键词，例如 "checkpoint 恢复" 而不是整句复述。"""
        hits = retriever.search(query)
        payload = [
            {
                "chapter_id": hit.chunk.chapter_id,
                "chapter_title": hit.chunk.chapter_title,
                "heading": hit.chunk.heading,
                "anchor": hit.chunk.anchor,
                "text": hit.chunk.text[:MAX_SNIPPET_CHARS],
                "score": round(hit.score, 3),
            }
            for hit in hits
        ]
        return json.dumps(payload, ensure_ascii=False)

    @tool
    def get_outline() -> str:
        """返回教程全部章节编号与标题（JSON）。回答学习路线、教程结构类问题时调用。"""
        payload = [{"chapter_id": chapter.id, "title": chapter.title} for chapter in chapters]
        return json.dumps(payload, ensure_ascii=False)

    return [search_tutorial, get_outline]

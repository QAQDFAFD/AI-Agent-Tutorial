"""HTTP 端点：章节内容 + SSE 聊天。引用来源从工具真实返回值提取，不信模型口述。"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator
from pathlib import Path

import markdown as md
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.errors import GraphRecursionError

from tutor.api.schemas import ChapterContent, ChapterSummary, ChatRequest
from tutor.ingest.chunker import slugify
from tutor.ingest.loader import Chapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _rewrite_links(html: str) -> str:
    html = html.replace('src="../assets/', 'src="/assets/').replace('src="assets/', 'src="/assets/')
    # demos 目录链接改写为站内 Demo 源码查看页
    html = re.sub(r'href="(?:\.\./)?demos/([\w-]+)/[\w.-]*"', r'href="#/demo/\1"', html)

    def to_route(match: re.Match) -> str:
        name = match.group(1)
        numbered = re.match(r"^(\d{2})-", name)
        return f'href="#/chapter/{numbered.group(1) if numbered else name}"'

    return re.sub(
        r'href="(?!https?://)(?:\.\./)?(?:docs/)?([\w.-]+?)\.md(?:#[^"]*)?"', to_route, html
    )


def render_chapter_html(chapter: Chapter) -> str:
    renderer = md.Markdown(
        extensions=["tables", "fenced_code", "toc"],
        extension_configs={"toc": {"slugify": lambda value, separator: slugify(value)}},
    )
    return _rewrite_links(renderer.convert(chapter.markdown))


def render_demo_html(demo_name: str, demo_dir: Path) -> str:
    """把一个 Demo 目录（README + *.py）拼成 Markdown 再渲染，与章节页共用一套样式。"""
    sections = []
    readme = demo_dir / "README.md"
    if readme.exists():
        sections.append(readme.read_text(encoding="utf-8"))
    else:
        sections.append(f"# demos/{demo_name}")
    for path in sorted(demo_dir.glob("*.py")):
        code = path.read_text(encoding="utf-8").rstrip()
        # 文件名用行内代码包裹，防止 __init__.py 的下划线被解析成斜体；
        # 用四个反引号做围栏，避免源码 docstring 里的 ``` 提前闭合代码块
        sections.append(f"## `{path.name}`\n\n````python\n{code}\n````")
    renderer = md.Markdown(
        extensions=["tables", "fenced_code", "toc"],
        extension_configs={"toc": {"slugify": lambda value, separator: slugify(value)}},
    )
    return _rewrite_links(renderer.convert("\n\n".join(sections)))


@router.get("/demos/{demo_name}")
async def read_demo(demo_name: str, request: Request) -> ChapterContent:
    # 白名单式校验目录名，杜绝路径穿越
    if not re.fullmatch(r"[\w-]+", demo_name):
        raise HTTPException(status_code=404, detail="示例不存在")
    demo_dir = request.app.state.settings.demos_dir / demo_name
    if not demo_dir.is_dir():
        raise HTTPException(status_code=404, detail="示例不存在")
    return ChapterContent(
        id=demo_name,
        title=f"demos/{demo_name}",
        html=render_demo_html(demo_name, demo_dir),
    )


@router.get("/health")
async def health(request: Request) -> dict:
    return {"status": "ok", "chat_enabled": request.app.state.agent is not None}


@router.get("/chapters")
async def list_chapters(request: Request) -> list[ChapterSummary]:
    return [ChapterSummary(id=c.id, title=c.title) for c in request.app.state.chapters]


@router.get("/chapters/{chapter_id}")
async def read_chapter(chapter_id: str, request: Request) -> ChapterContent:
    chapter = next((c for c in request.app.state.chapters if c.id == chapter_id), None)
    if chapter is None:
        raise HTTPException(status_code=404, detail="章节不存在")
    return ChapterContent(id=chapter.id, title=chapter.title, html=render_chapter_html(chapter))


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chunk_text(message: AIMessageChunk) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


def _extract_sources(message: ToolMessage) -> list[dict]:
    try:
        data = json.loads(message.content) if isinstance(message.content, str) else []
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [
        {key: item[key] for key in ("chapter_id", "chapter_title", "heading", "anchor")}
        for item in data
        if isinstance(item, dict) and "chapter_id" in item
    ]


async def _stream_chat(state, payload: ChatRequest) -> AsyncIterator[str]:
    config = {
        "configurable": {"thread_id": payload.thread_id},
        "recursion_limit": state.settings.agent_recursion_limit,
    }
    seen: list[dict] = []
    try:
        async with asyncio.timeout(state.settings.request_timeout_seconds):
            stream = state.agent.astream(
                {"messages": [{"role": "user", "content": payload.message}]},
                config=config,
                stream_mode=["updates", "messages"],
            )
            async for mode, event in stream:
                if mode == "messages":
                    chunk, _metadata = event
                    if isinstance(chunk, AIMessageChunk) and not chunk.tool_call_chunks:
                        delta = _chunk_text(chunk)
                        if delta:
                            yield _sse("token", {"delta": delta})
                    continue
                for update in event.values():
                    for message in update.get("messages", []):
                        if isinstance(message, AIMessage) and message.tool_calls:
                            for call in message.tool_calls:
                                summary = json.dumps(call["args"], ensure_ascii=False)[:200]
                                yield _sse(
                                    "tool_call", {"tool": call["name"], "input_summary": summary}
                                )
                        if isinstance(message, ToolMessage) and message.name == "search_tutorial":
                            fresh = [s for s in _extract_sources(message) if s not in seen]
                            if fresh:
                                seen.extend(fresh)
                                yield _sse("sources", fresh)
        yield _sse("final", {"ok": True})
    except TimeoutError:
        yield _sse("error", {"message": "回答超时，请稍后重试，或把问题问得更具体一些。"})
    except GraphRecursionError:
        yield _sse("error", {"message": "这个问题太复杂了，请拆成更小的问题再问我。"})
    except Exception:
        logger.exception("chat run failed")
        yield _sse("error", {"message": "服务暂时出错了，请稍后重试。"})


@router.post("/chat")
async def chat(request: Request, payload: ChatRequest) -> StreamingResponse:
    state = request.app.state
    if state.agent is None:
        reason = state.chat_disabled_reason or "聊天功能不可用"
        raise HTTPException(
            status_code=503,
            detail=f"{reason}。请参考附录 A 配置 OPENAI_API_KEY 后重启服务。",
        )
    return StreamingResponse(_stream_chat(state, payload), media_type="text/event-stream")

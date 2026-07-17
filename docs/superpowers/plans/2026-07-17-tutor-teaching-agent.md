# 教学 Agent（tutor）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建顶层 `tutor/` 生产级应用：教程阅读站点 + 基于 create_agent 的 RAG 教学助手（SSE 流式、章节引用可跳转）。

**Architecture:** 分层包结构 config / ingest / rag / agent / api / web；应用工厂 + lifespan 装配；EmbeddingClient 协议 + 缓存装饰器；引用来源从工具真实返回值确定性提取。

**Tech Stack:** FastAPI、LangChain 1.x `create_agent`（LangGraph runtime）、OpenAI Embeddings、numpy、python-markdown、pydantic-settings、原生 HTML/JS。

## Global Constraints

- Python 3.11+；测试全部无需 API Key 与网络（`uv run pytest` 一条命令通过）
- 沿用 `.env` 现有变量：`OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL`；tutor 特有项用 `TUTOR_` 前缀
- ruff 规则（E/F/I/UP/B/SIM，line-length 100）必须通过
- 不引入 Node 工具链、向量数据库；新依赖仅 `pydantic-settings`、`markdown`、`numpy`
- 对外错误不泄漏堆栈；异常细节仅进服务端日志
- `search_tutorial` 工具返回 JSON 字符串（非 Python repr），以便 API 层可靠解析 sources

---

### Task 1: 脚手架与配置层

**Files:**
- Modify: `pyproject.toml`（新增依赖）、`.gitignore`（加 `var/`）
- Create: `tutor/__init__.py`、`tutor/config.py`、各子包 `__init__.py`
- Test: `tests/test_tutor_config.py`

**Interfaces:**
- Produces: `tutor.config.Settings`（字段见下，全部组件构造时接收该对象）

- [ ] **Step 1:** `uv add pydantic-settings markdown numpy`；`.gitignore` 追加 `var/`
- [ ] **Step 2:** 写失败测试：

```python
# tests/test_tutor_config.py
from pathlib import Path

from tutor.config import Settings


def test_settings_defaults_and_env_mapping(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("TUTOR_EMBEDDING_MODEL", "test-embed")
    settings = Settings(_env_file=None)
    assert settings.openai_model == "test-model"
    assert settings.tutor_embedding_model == "test-embed"
    assert settings.docs_dir == Path("docs")
    assert settings.top_k == 4
```

- [ ] **Step 3:** 实现：

```python
# tutor/config.py
"""集中配置：所有组件只依赖 Settings 对象，不直接读环境变量。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "gpt-5.6"
    tutor_embedding_model: str = "text-embedding-3-small"

    docs_dir: Path = Path("docs")
    assets_dir: Path = Path("assets")
    cache_dir: Path = Path("var")

    top_k: int = 4
    max_message_length: int = 2000
    agent_recursion_limit: int = 10
    request_timeout_seconds: float = 60.0
```

- [ ] **Step 4:** `uv run pytest tests/test_tutor_config.py -q` 通过；commit `feat(tutor): scaffold package and settings`

### Task 2: ingest 层（loader + chunker）

**Files:**
- Create: `tutor/ingest/loader.py`、`tutor/ingest/chunker.py`
- Test: `tests/test_tutor_ingest.py`

**Interfaces:**
- Produces: `Chapter(id, title, path, markdown)`；`load_chapters(docs_dir) -> list[Chapter]`；`Chunk(chapter_id, chapter_title, heading, anchor, text)`；`split_chapter(chapter) -> list[Chunk]`；`slugify(heading) -> str`（api 层渲染锚点复用）

- [ ] **Step 1:** 失败测试（直接跑真实 docs/）：

```python
# tests/test_tutor_ingest.py
from pathlib import Path

from tutor.ingest.chunker import slugify, split_chapter
from tutor.ingest.loader import load_chapters


def test_load_chapters_covers_numbered_and_appendix():
    chapters = load_chapters(Path("docs"))
    ids = [chapter.id for chapter in chapters]
    assert "00" in ids and "13" in ids and "setup" in ids and "glossary" in ids
    ch05 = next(chapter for chapter in chapters if chapter.id == "05")
    assert "LangGraph" in ch05.title


def test_split_chapter_keeps_metadata_and_limits_size():
    chapters = load_chapters(Path("docs"))
    ch05 = next(chapter for chapter in chapters if chapter.id == "05")
    chunks = split_chapter(ch05)
    assert all(chunk.chapter_id == "05" for chunk in chunks)
    assert any("Checkpoint" in chunk.heading for chunk in chunks)
    assert all(len(chunk.text) <= 1600 for chunk in chunks)
    assert all(chunk.anchor == slugify(chunk.heading) for chunk in chunks)


def test_slugify_keeps_chinese():
    assert slugify("5.5 Checkpoint：可恢复的关键") == "55-checkpoint可恢复的关键"
```

- [ ] **Step 2:** 实现 loader：

```python
# tutor/ingest/loader.py
"""把 docs/*.md 读成 Chapter 列表；只扫顶层，spec/计划子目录自然排除。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chapter:
    id: str
    title: str
    path: Path
    markdown: str


def _chapter_id(path: Path) -> str:
    match = re.match(r"^(\d{2})-", path.name)
    return match.group(1) if match else path.stem


def _chapter_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def load_chapters(docs_dir: Path) -> list[Chapter]:
    chapters = []
    for path in sorted(docs_dir.glob("*.md")):
        markdown = path.read_text(encoding="utf-8")
        chapters.append(
            Chapter(
                id=_chapter_id(path),
                title=_chapter_title(markdown, path.stem),
                path=path,
                markdown=markdown,
            )
        )
    return chapters
```

- [ ] **Step 3:** 实现 chunker（按 `##` 切块、码块内不误切、长块按段落再切、slugify 保留中文并与前端锚点约定一致）：

```python
# tutor/ingest/chunker.py
"""章节切块：每块保留章节/小节出处，供检索引用精确到块级。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .loader import Chapter

MAX_CHUNK_CHARS = 1200


@dataclass(frozen=True)
class Chunk:
    chapter_id: str
    chapter_title: str
    heading: str
    anchor: str
    text: str


def slugify(heading: str) -> str:
    """锚点 slug：小写、空白转连字符、保留中文与字母数字。api 渲染与前端跳转共用。"""
    slug = re.sub(r"\s+", "-", heading.strip().lower())
    return re.sub(r"[^\w\u4e00-\u9fff-]", "", slug)


def _split_long(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        if current and len(current) + len(paragraph) + 2 > max_chars:
            parts.append(current.strip())
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current.strip():
        parts.append(current.strip())
    return parts


def split_chapter(chapter: Chapter) -> list[Chunk]:
    sections: list[tuple[str, list[str]]] = [(chapter.title, [])]
    in_code = False
    for line in chapter.markdown.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("## "):
            sections.append((line[3:].strip(), []))
            continue
        if not in_code and line.startswith("# "):
            continue  # H1 已作为章节标题元数据
        sections[-1][1].append(line)

    chunks: list[Chunk] = []
    for heading, lines in sections:
        text = "\n".join(lines).strip()
        if not text:
            continue
        for part in _split_long(text):
            chunks.append(
                Chunk(
                    chapter_id=chapter.id,
                    chapter_title=chapter.title,
                    heading=heading,
                    anchor=slugify(heading),
                    text=part,
                )
            )
    return chunks
```

- [ ] **Step 4:** 测试通过后 commit `feat(tutor): ingest layer (loader + chunker)`

### Task 3: rag 层（embeddings 缓存 / index / retriever）

**Files:**
- Create: `tutor/rag/embeddings.py`、`tutor/rag/index.py`、`tutor/rag/retriever.py`
- Test: `tests/test_tutor_rag.py`

**Interfaces:**
- Produces: `EmbeddingClient`（Protocol：`embed(texts) -> list[list[float]]`）；`OpenAIEmbeddingClient(settings)`；`CachedEmbeddingClient(inner, cache_path, model_tag)`；`VectorIndex(chunks, vectors).search(vector, top_k)`；`Hit(chunk, score)`；`Retriever.build(embeddings, chunks, top_k)`、`Retriever.search(query, top_k=None) -> list[Hit]`

- [ ] **Step 1:** 失败测试（FakeEmbeddingClient 用 crc32 字符二元组哈希，确定性且中文友好）：

```python
# tests/test_tutor_rag.py
import math
import zlib
from pathlib import Path

from tutor.ingest.chunker import Chunk
from tutor.rag.embeddings import CachedEmbeddingClient
from tutor.rag.retriever import Retriever


def _vec(text: str, dim: int = 128) -> list[float]:
    values = [0.0] * dim
    for i in range(len(text) - 1):
        values[zlib.crc32(text[i : i + 2].encode()) % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(list(texts))
        return [_vec(text) for text in texts]


CHUNKS = [
    Chunk("05", "LangGraph", "Checkpoint", "checkpoint", "checkpointer 保存快照，thread 可恢复执行"),
    Chunk("07", "RAG", "切块", "切块", "把长文档切成小块，检索时带出处引用"),
    Chunk("10", "安全", "幂等", "幂等", "写操作使用幂等键防止重复退款"),
]


def test_retriever_hits_expected_chunk():
    retriever = Retriever.build(FakeEmbeddingClient(), CHUNKS, top_k=2)
    hits = retriever.search("checkpointer 怎么恢复 thread")
    assert hits[0].chunk.chapter_id == "05"


def test_cached_client_skips_repeat_calls(tmp_path: Path):
    inner = FakeEmbeddingClient()
    cache_path = tmp_path / "cache.json"
    client = CachedEmbeddingClient(inner, cache_path, model_tag="fake")
    first = client.embed(["你好", "世界"])
    again = client.embed(["你好", "世界"])
    assert first == again
    assert len(inner.batches) == 1  # 第二次全部命中缓存

    fresh = CachedEmbeddingClient(FakeEmbeddingClient(), cache_path, model_tag="fake")
    assert fresh.embed(["你好"])[0] == first[0]  # 磁盘缓存跨实例生效
```

- [ ] **Step 2:** 实现三个模块：

```python
# tutor/rag/embeddings.py
"""Embedding 客户端协议、OpenAI 实现与磁盘缓存装饰器。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol

from tutor.config import Settings


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingClient:
    def __init__(self, settings: Settings):
        from openai import OpenAI

        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self._model = settings.tutor_embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]


class CachedEmbeddingClient:
    """按 sha256(model_tag + text) 缓存到 JSON 文件；只有未命中的文本才调用 inner。"""

    def __init__(self, inner: EmbeddingClient, cache_path: Path, *, model_tag: str):
        self._inner = inner
        self._cache_path = cache_path
        self._model_tag = model_tag
        self._cache: dict[str, list[float]] = {}
        if cache_path.exists():
            self._cache = json.loads(cache_path.read_text(encoding="utf-8"))

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self._model_tag}\x00{text}".encode()).hexdigest()

    def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float] | None] = [self._cache.get(self._key(t)) for t in texts]
        missing = [i for i, vector in enumerate(results) if vector is None]
        if missing:
            fresh = self._inner.embed([texts[i] for i in missing])
            for index, vector in zip(missing, fresh, strict=True):
                results[index] = vector
                self._cache[self._key(texts[index])] = vector
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(self._cache), encoding="utf-8")
        return results  # type: ignore[return-value]
```

```python
# tutor/rag/index.py
"""内存向量索引：numpy 余弦相似度 Top-K。"""

from __future__ import annotations

import numpy as np

from tutor.ingest.chunker import Chunk


class VectorIndex:
    def __init__(self, chunks: list[Chunk], vectors: list[list[float]]):
        if len(chunks) != len(vectors):
            raise ValueError("chunks 与 vectors 数量不一致")
        self.chunks = chunks
        matrix = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self._matrix = matrix / np.maximum(norms, 1e-10)

    def search(self, vector: list[float], top_k: int) -> list[tuple[Chunk, float]]:
        query = np.asarray(vector, dtype=np.float32)
        query = query / max(float(np.linalg.norm(query)), 1e-10)
        scores = self._matrix @ query
        order = np.argsort(scores)[::-1][:top_k]
        return [(self.chunks[i], float(scores[i])) for i in order]
```

```python
# tutor/rag/retriever.py
"""对 agent 层暴露的唯一检索入口。"""

from __future__ import annotations

from dataclasses import dataclass

from tutor.ingest.chunker import Chunk
from tutor.rag.embeddings import EmbeddingClient
from tutor.rag.index import VectorIndex


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


def embedding_input(chunk: Chunk) -> str:
    """把章节/小节标题拼进 embedding 输入，提高短问题的命中率。"""
    return f"{chunk.chapter_title}\n{chunk.heading}\n{chunk.text}"


class Retriever:
    def __init__(self, embeddings: EmbeddingClient, index: VectorIndex, top_k: int):
        self._embeddings = embeddings
        self._index = index
        self._top_k = top_k

    @classmethod
    def build(cls, embeddings: EmbeddingClient, chunks: list[Chunk], top_k: int) -> Retriever:
        vectors = embeddings.embed([embedding_input(chunk) for chunk in chunks])
        return cls(embeddings, VectorIndex(chunks, vectors), top_k)

    def search(self, query: str, top_k: int | None = None) -> list[Hit]:
        vector = self._embeddings.embed([query])[0]
        pairs = self._index.search(vector, top_k or self._top_k)
        return [Hit(chunk=chunk, score=score) for chunk, score in pairs]
```

- [ ] **Step 3:** 测试通过后 commit `feat(tutor): rag layer with cached embeddings`

### Task 4: agent 层（prompts / tools / graph）

**Files:**
- Create: `tutor/agent/prompts.py`、`tutor/agent/tools.py`、`tutor/agent/graph.py`
- Test: `tests/test_tutor_agent.py`

**Interfaces:**
- Consumes: `Retriever.search`、`Chapter`
- Produces: `make_tools(retriever, chapters) -> list`（工具名 `search_tutorial`/`get_outline`，前者返回 JSON 字符串）；`build_agent(settings, retriever, chapters, model=None)`（返回 create_agent 编译产物，checkpointer=InMemorySaver）

- [ ] **Step 1:** 失败测试（自定义 ScriptedChatModel，先调工具再答复）：

```python
# tests/test_tutor_agent.py
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
                tool_calls=[{"name": "search_tutorial", "args": {"query": "checkpoint"}, "id": "c1"}],
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
```

- [ ] **Step 2:** 实现：

```python
# tutor/agent/prompts.py
SYSTEM_PROMPT = """你是《Python AI Agent 教程》站点的教学助手。

硬规则：
1. 回答任何教程内容问题前，必须先调用 search_tutorial 检索；只基于检索结果回答，不得编造。
2. 每个关键结论都标注来源章节，格式如（第 05 章）。
3. 检索不到依据时，明确说"教程里没有找到"，并建议查看附录 C 精读文选。
4. 用户问学习路线或教程结构时，调用 get_outline。
5. 与本教程无关的话题，礼貌说明你只负责本教程，并拉回主题。
6. 用简洁中文回答，代码示例使用 Markdown 代码块。"""
```

```python
# tutor/agent/tools.py
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
        payload = [{"chapter_id": c.id, "title": c.title} for c in chapters]
        return json.dumps(payload, ensure_ascii=False)

    return [search_tutorial, get_outline]
```

```python
# tutor/agent/graph.py
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
```

- [ ] **Step 3:** 测试通过后 commit `feat(tutor): teaching agent (tools + create_agent)`

### Task 5: api 层（schemas / routes / app 工厂）

**Files:**
- Create: `tutor/api/schemas.py`、`tutor/api/routes.py`、`tutor/api/app.py`
- Test: `tests/test_tutor_api.py`

**Interfaces:**
- Consumes: Task 2–4 全部产物
- Produces: `create_app(settings=None, agent=None) -> FastAPI`；模块级 `app`；端点 `/api/health`、`/api/chapters`、`/api/chapters/{id}`、`/api/chat`(SSE)；SSE 事件 `tool_call/sources/token/final/error`

- [ ] **Step 1:** 失败测试（TestClient 上下文运行 lifespan；FakeAgent 产出 (mode, event) 元组）：

```python
# tests/test_tutor_api.py
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
                                {"name": "search_tutorial", "args": {"query": "checkpoint"}, "id": "c1"}
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
        yield ("messages", (AIMessageChunk(content="Checkpoint 让图可恢复"), {"langgraph_node": "model"}))


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


def test_chat_streams_expected_event_sequence():
    with TestClient(create_app(_settings(), agent=FakeAgent())) as client:
        with client.stream(
            "POST", "/api/chat", json={"thread_id": "t-1", "message": "checkpoint 是什么"}
        ) as response:
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
```

- [ ] **Step 2:** 实现 schemas / routes / app：

```python
# tutor/api/schemas.py
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    message: str = Field(min_length=1, max_length=2000)


class ChapterSummary(BaseModel):
    id: str
    title: str


class ChapterContent(BaseModel):
    id: str
    title: str
    html: str
```

```python
# tutor/api/routes.py
"""HTTP 端点：章节内容 + SSE 聊天。引用来源从工具真实返回值提取，不信模型口述。"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator

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

    def to_route(match: re.Match) -> str:
        name = match.group(1)
        numbered = re.match(r"^(\d{2})-", name)
        return f'href="#/chapter/{numbered.group(1) if numbered else name}"'

    return re.sub(r'href="(?!https?://)(?:\.\./)?(?:docs/)?([\w.-]+?)\.md(?:#[^"]*)?"', to_route, html)


def render_chapter_html(chapter: Chapter) -> str:
    renderer = md.Markdown(
        extensions=["tables", "fenced_code", "toc"],
        extension_configs={"toc": {"slugify": lambda value, separator: slugify(value)}},
    )
    return _rewrite_links(renderer.convert(chapter.markdown))


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
                                yield _sse("tool_call", {"tool": call["name"], "input_summary": summary})
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
        raise HTTPException(status_code=503, detail=f"{reason}。请参考附录 A 配置 OPENAI_API_KEY 后重启服务。")
    return StreamingResponse(_stream_chat(state, payload), media_type="text/event-stream")
```

```python
# tutor/api/app.py
"""应用工厂：lifespan 中完成 加载章节 → 切块 → 建索引 → 组装 Agent。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tutor.agent.graph import build_agent
from tutor.api.routes import router
from tutor.config import Settings
from tutor.ingest.chunker import split_chapter
from tutor.ingest.loader import load_chapters
from tutor.rag.embeddings import CachedEmbeddingClient, OpenAIEmbeddingClient
from tutor.rag.retriever import Retriever

logger = logging.getLogger(__name__)
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app(settings: Settings | None = None, *, agent=None) -> FastAPI:
    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = app_settings
        app.state.chapters = load_chapters(app_settings.docs_dir)
        app.state.agent = None
        app.state.chat_disabled_reason = None
        if agent is not None:
            app.state.agent = agent
        elif not app_settings.openai_api_key:
            app.state.chat_disabled_reason = "未配置 OPENAI_API_KEY"
        else:
            try:
                chunks = [c for chapter in app.state.chapters for c in split_chapter(chapter)]
                embeddings = CachedEmbeddingClient(
                    OpenAIEmbeddingClient(app_settings),
                    app_settings.cache_dir / "embeddings-cache.json",
                    model_tag=app_settings.tutor_embedding_model,
                )
                retriever = Retriever.build(embeddings, chunks, app_settings.top_k)
                app.state.agent = build_agent(app_settings, retriever, app.state.chapters)
                logger.info("tutor agent ready: %d chapters, %d chunks", len(app.state.chapters), len(chunks))
            except Exception:
                logger.exception("failed to build tutor agent")
                app.state.chat_disabled_reason = "索引构建失败，请查看服务端日志"
        yield

    app = FastAPI(title="AI Agent 教程教学助手", version="1.0.0", lifespan=lifespan)
    app.include_router(router)
    app.mount("/assets", StaticFiles(directory=app_settings.assets_dir), name="assets")
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = create_app()
```

- [ ] **Step 3:** 测试通过 + `uv run pytest -q` 全绿后 commit `feat(tutor): api layer with SSE chat`

### Task 6: web 前端（index.html / style.css / app.js）

**Files:**
- Create: `tutor/web/index.html`、`tutor/web/style.css`、`tutor/web/app.js`

**Interfaces:**
- Consumes: `/api/chapters`、`/api/chapters/{id}`、`/api/chat`(SSE)、`/api/health`
- 路由约定：`#/chapter/<id>`；sources 标签点击 → 切换 hash 并滚动到 `anchor`

前端为纯静态三件套（代码在执行时一次写成，要点）：
- [ ] index.html：三栏布局骨架（侧栏 nav、正文 article、右下角聊天面板）+ noscript 提示
- [ ] style.css：系统字体栈、浅色主题、正文最大宽 820px、代码块/表格/图片样式、聊天气泡与悬浮按钮、移动端侧栏折叠
- [ ] app.js：
  - `loadChapters()` 渲染侧栏；`route()` 解析 hash 加载正文；锚点滚动
  - 聊天：`thread_id = localStorage['tutor-thread'] ??= crypto.randomUUID()`；`fetch POST /api/chat` + `ReadableStream` 手工解析 SSE（按 `\n\n` 分帧）；事件处理：`tool_call`→状态行"正在查阅教程…"、`token`→增量追加、`sources`→渲染章节标签（点击跳转）、`error`→红色提示；503 → 显示配置指引
  - 启动时 `GET /api/health`，`chat_enabled=false` 时聊天输入框禁用并显示原因
- [ ] 手工验证：`uv run uvicorn tutor.api.app:app` 打开 http://127.0.0.1:8000 阅读与聊天（无 Key 时验证降级文案）；commit `feat(tutor): web reader and chat widget`

### Task 7: 文档与仓库接线

**Files:**
- Create: `tutor/README.md`、`docs/14-teaching-agent.md`
- Modify: `README.md`（路线表 + 运行段）、`Makefile`（`tutor` 目标）、`docs/00-learning-map.md`（可选提及）

- [ ] tutor/README.md：快速运行、架构图（mermaid 文本）、分层职责表、与 demos 对照、"生产化差距"清单
- [ ] docs/14-teaching-agent.md：为什么 create_agent（对照 4.5 节）、分层与依赖注入、SSE 事件设计、引用为何取自工具返回值、练习（SQLite checkpointer / BM25 混合检索 / 输入护栏 middleware）
- [ ] README 路线表加"14｜最终实战：教学 Agent 站点"；Makefile 加 `tutor:` 目标
- [ ] commit `docs(tutor): chapter 14 and wiring`

### Task 8: 端到端验证

- [ ] `uv run pytest -q` 全绿；`uv run ruff check .` 通过
- [ ] 无 Key 启动：阅读页可用、聊天显示降级提示
- [ ] （用户执行）配置真实 Key 冒烟：问"checkpoint 是什么"，验证 tool_call/sources/token 事件与引用跳转
- [ ] commit（如有修补）

## Self-Review 结论

- Spec 覆盖：spec §3–§8 每项均有对应 Task（1↔§4.1，2↔§4.2，3↔§4.3，4↔§4.4，5↔§4.5+§6，6↔§4.6，7↔§8，8↔验证）；
- 类型一致性：`Chunk/Chapter/Hit/Settings/create_app(settings, agent=)` 签名在各 Task 引用一致；`search_tutorial` 返回 JSON 字符串在 Task 4 定义、Task 5 解析、全局约束注明；
- 无占位符：Task 6 前端为静态资源，要点式列出但在执行时一次成文（无逻辑歧义）。

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
from tutor.rag.embeddings import (
    CachedEmbeddingClient,
    EmbeddingClient,
    HashEmbeddingClient,
    OpenAIEmbeddingClient,
)
from tutor.rag.retriever import Retriever

logger = logging.getLogger(__name__)
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def _build_embeddings(settings: Settings) -> EmbeddingClient:
    if settings.tutor_embedding_provider == "hash":
        return HashEmbeddingClient()
    return CachedEmbeddingClient(
        OpenAIEmbeddingClient(settings),
        settings.cache_dir / "embeddings-cache.json",
        model_tag=settings.tutor_embedding_model,
    )


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
                embeddings = _build_embeddings(app_settings)
                retriever = Retriever.build(embeddings, chunks, app_settings.top_k)
                app.state.agent = build_agent(app_settings, retriever, app.state.chapters)
                logger.info(
                    "tutor agent ready: %d chapters, %d chunks",
                    len(app.state.chapters),
                    len(chunks),
                )
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

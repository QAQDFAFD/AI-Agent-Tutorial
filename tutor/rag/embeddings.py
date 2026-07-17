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

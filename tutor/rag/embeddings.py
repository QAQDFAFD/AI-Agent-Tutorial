"""Embedding 客户端协议、OpenAI 实现与磁盘缓存装饰器。"""

from __future__ import annotations

import hashlib
import json
import math
import zlib
from pathlib import Path
from typing import Protocol

from tutor.config import Settings


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbeddingClient:
    """本地字符 n-gram 哈希向量：确定性、零成本、零网络。

    质量不如真正的 Embedding 模型，但对中文短查询的字面匹配足够可用，
    适合 DeepSeek 等不提供 embedding 接口的 OpenAI 兼容服务商。
    """

    def __init__(self, dim: int = 512):
        self._dim = dim

    def _vector(self, text: str) -> list[float]:
        values = [0.0] * self._dim
        lowered = text.lower()
        for size in (2, 3):
            for i in range(len(lowered) - size + 1):
                gram = lowered[i : i + size]
                values[zlib.crc32(gram.encode()) % self._dim] += 1.0
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]


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

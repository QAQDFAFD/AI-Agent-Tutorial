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

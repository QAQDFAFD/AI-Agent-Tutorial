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

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
    Chunk(
        "05", "LangGraph", "Checkpoint", "checkpoint", "checkpointer 保存快照，thread 可恢复执行"
    ),
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

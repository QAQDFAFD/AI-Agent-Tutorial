# Demo 06：本地 RAG

对应[第 07 章](../../docs/07-rag.md)。无需 API Key 或向量数据库。

```bash
uv run python -m demos.06_rag.main
```

Demo 使用可阅读的中文二元组重叠分数展示切块（`split_into_sentence_chunks`）、过滤、召回、Top-K、块级引用和 Recall@K。生产中可替换为 BM25、embedding 或混合检索，上层 `SearchHit` 合同保持不变。


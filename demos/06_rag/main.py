"""不依赖 embedding 服务的本地检索、引用与评测骨架。"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    tenant_id: str = "public"


@dataclass(frozen=True)
class SearchHit:
    document: Document
    score: float


DOCUMENTS = [
    Document("policy-return", "退货期限：普通商品签收后 7 天内可以申请无理由退货。"),
    Document("policy-shipping", "退货运费：质量问题由商家承担，个人原因由消费者承担。"),
    Document("policy-refund", "退款到账：审核通过后通常 1 到 3 个工作日原路退回。"),
    Document("private-vip", "VIP 内部补偿规则，不对其他租户公开。", tenant_id="vip"),
]

# 一篇较长的原始文档：直接整篇建索引会让召回带回大量无关内容，
# 所以先切块（chunking），每块保留出处，才能做到"按需取回、带引用回答"。
HANDBOOK = (
    "会员积分：每消费 1 元累计 1 分，积分可在下单时抵扣现金。"
    "积分有效期：积分自获得之日起 12 个月内有效，过期自动清零。"
    "发票开具：电子发票在订单完成后 24 小时内发送至预留邮箱。"
    "发票抬头：支持个人与企业抬头，企业抬头需要提供税号。"
)


def split_into_sentence_chunks(
    doc_id: str, text: str, *, sentences_per_chunk: int = 1
) -> list[Document]:
    """按句号切块并保留出处。真实项目常按标题/段落切并加少量重叠，思路相同。"""
    sentences = [part for part in text.split("。") if part.strip()]
    chunks = [
        "。".join(sentences[index : index + sentences_per_chunk]) + "。"
        for index in range(0, len(sentences), sentences_per_chunk)
    ]
    return [
        Document(id=f"{doc_id}#chunk-{number}", text=chunk)
        for number, chunk in enumerate(chunks, start=1)
    ]


def tokenize(text: str) -> set[str]:
    """英文/数字词 + 中文二元组；仅为透明教学，不代替生产分词器。"""
    normalized = text.lower()
    latin = set(re.findall(r"[a-z0-9]+", normalized))
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", normalized)
    bigrams = {
        run[index : index + 2]
        for run in chinese_runs
        for index in range(max(1, len(run) - 1))
        if len(run[index : index + 2]) == 2
    }
    return latin | bigrams


class LocalRetriever:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.index = {document.id: tokenize(document.text) for document in documents}

    def search(self, query: str, *, top_k: int = 2, tenant_id: str = "public") -> list[SearchHit]:
        query_tokens = tokenize(query)
        hits: list[SearchHit] = []
        for document in self.documents:
            if document.tenant_id not in {"public", tenant_id}:
                continue
            doc_tokens = self.index[document.id]
            overlap = len(query_tokens & doc_tokens)
            score = overlap / math.sqrt(max(1, len(query_tokens) * len(doc_tokens)))
            if score > 0:
                hits.append(SearchHit(document, score))
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[: max(1, min(top_k, 5))]


def answer_question(query: str, retriever: LocalRetriever) -> dict:
    hits = retriever.search(query, top_k=2)
    if not hits:
        return {
            "answer": "知识库中没有足够依据，我暂时无法回答。",
            "source_ids": [],
        }

    evidence = "；".join(hit.document.text for hit in hits)
    return {
        "answer": f"根据检索到的资料：{evidence}",
        "source_ids": [hit.document.id for hit in hits],
    }


def recall_at_k(
    retriever: LocalRetriever, examples: list[tuple[str, str]], *, k: int = 2
) -> float:
    matched = 0
    for query, expected_id in examples:
        ids = {hit.document.id for hit in retriever.search(query, top_k=k)}
        matched += expected_id in ids
    return matched / len(examples) if examples else 0.0


def main() -> None:
    # 建库时把长文档切成带出处的小块，与短政策一起进入同一个索引。
    corpus = DOCUMENTS + split_into_sentence_chunks("handbook", HANDBOOK)
    retriever = LocalRetriever(corpus)

    for question in ["退货以后运费由谁承担？", "积分多久过期？"]:
        print(f"问题：{question}")
        print(answer_question(question, retriever))
        print()

    examples = [
        ("几天内能退货", "policy-return"),
        ("质量问题的退货运费", "policy-shipping"),
        ("退款多久能到账", "policy-refund"),
        ("积分有效期是多久", "handbook#chunk-2"),
    ]
    print(f"Recall@2: {recall_at_k(retriever, examples):.1%}")


if __name__ == "__main__":
    main()


import importlib

rag = importlib.import_module("demos.06_rag.main")


def test_retrieval_hits_expected_source():
    retriever = rag.LocalRetriever(rag.DOCUMENTS)
    hits = retriever.search("退款多久能到账", top_k=2)
    assert "policy-refund" in {hit.document.id for hit in hits}


def test_retrieval_enforces_tenant_filter():
    retriever = rag.LocalRetriever(rag.DOCUMENTS)
    public_ids = {hit.document.id for hit in retriever.search("VIP 内部补偿", tenant_id="public")}
    vip_ids = {hit.document.id for hit in retriever.search("VIP 内部补偿", tenant_id="vip")}
    assert "private-vip" not in public_ids
    assert "private-vip" in vip_ids


def test_answer_refuses_without_evidence():
    retriever = rag.LocalRetriever(rag.DOCUMENTS)
    result = rag.answer_question("量子计算机保修几年", retriever)
    assert result["source_ids"] == []


def test_chunking_keeps_block_level_source_ids():
    chunks = rag.split_into_sentence_chunks("handbook", rag.HANDBOOK)
    assert [chunk.id for chunk in chunks[:2]] == ["handbook#chunk-1", "handbook#chunk-2"]

    retriever = rag.LocalRetriever(rag.DOCUMENTS + chunks)
    hits = retriever.search("积分有效期是多久", top_k=2)
    assert "handbook#chunk-2" in {hit.document.id for hit in hits}


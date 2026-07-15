import importlib

structured = importlib.import_module("demos.02_openai_structured.main")


def test_local_classifier_never_invents_order_id():
    result = structured.classify_locally("帮我查一下订单")
    assert result.intent == "order"
    assert result.order_id is None
    assert result.missing_fields == ["order_id"]


def test_local_classifier_extracts_order_id():
    result = structured.classify_locally("请给 ord-1001 退款")
    assert result.intent == "refund"
    assert result.order_id == "ORD-1001"


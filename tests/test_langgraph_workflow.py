import importlib

workflow = importlib.import_module("demos.04_langgraph_workflow.main")


def test_routes_policy_question():
    result = workflow.build_graph().invoke({"question": "退货政策是什么？", "attempts": 0})
    assert result["intent"] == "knowledge"
    assert "policy-return" in result["answer"]


def test_missing_order_id_is_requested():
    result = workflow.build_graph().invoke({"question": "帮我查询订单", "attempts": 0})
    assert "订单号" in result["answer"]


def test_short_answer_triggers_bounded_rewrite_loop():
    result = workflow.build_graph().invoke({"question": "你好", "attempts": 0})
    assert result["attempts"] == 1
    assert result["needs_rewrite"] is False
    assert "补充说明" in result["answer"]


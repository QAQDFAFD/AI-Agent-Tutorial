import importlib
import uuid

capstone = importlib.import_module("demos.11_capstone_helpdesk.main")


def unique_thread() -> str:
    return f"test-{uuid.uuid4().hex}"


def test_capstone_answers_with_source():
    result = capstone.run_request("退货期限是多久？", thread_id=unique_thread())
    assert "policy-return" in result["reply"]
    assert "retrieved:policy-return" in result["audit"]


def test_refund_pauses_without_approval():
    result = capstone.run_request("给 ORD-1001 退款", thread_id=unique_thread())
    assert "__interrupt__" in result
    assert not result.get("refund_result")


def test_approved_refund_executes():
    result = capstone.run_request(
        "给 ORD-1001 退款", approved=True, thread_id=unique_thread()
    )
    assert result["refund_result"]["status"] == "refunded"
    assert "退款已完成" in result["reply"]


def test_rejected_refund_has_no_write():
    result = capstone.run_request(
        "给 ORD-1001 退款", approved=False, thread_id=unique_thread()
    )
    assert "refund_result" not in result
    assert "没有执行" in result["reply"]


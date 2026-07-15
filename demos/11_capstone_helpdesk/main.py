"""LangGraph 综合项目：知识、订单与需要人工审批的幂等退款。"""

from __future__ import annotations

import operator
import re
import sys
import uuid
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

ORDERS = {
    "ORD-1001": {"user_id": "demo-user", "status": "delivered", "paid": 199.0},
    "ORD-1002": {"user_id": "demo-user", "status": "shipped", "paid": 88.0},
}

FAQ = {
    "policy-return": "普通商品签收后 7 天内可申请无理由退货，定制商品除外。",
    "policy-shipping": "商品质量问题产生的退货运费由商家承担。",
}

# 教学版进程内幂等表；生产应使用数据库唯一约束。
REFUND_RESULTS: dict[str, dict] = {}


class HelpdeskState(TypedDict, total=False):
    user_id: str
    request_id: str
    message: str
    intent: Literal["knowledge", "order", "refund", "other"]
    order_id: str
    evidence: list[dict]
    order: dict
    draft_action: dict
    approval: dict
    refund_result: dict
    reply: str
    audit: Annotated[list[str], operator.add]


def extract_order_id(text: str) -> str:
    match = re.search(r"ORD-\d{4}", text.upper())
    return match.group(0) if match else ""


def classify(state: HelpdeskState) -> dict:
    text = state["message"]
    order_id = extract_order_id(text)
    if "退款" in text or "退钱" in text:
        intent: Literal["knowledge", "order", "refund", "other"] = "refund"
    elif order_id or "订单" in text:
        intent = "order"
    elif any(word in text for word in ("退货", "运费", "政策", "多久")):
        intent = "knowledge"
    else:
        intent = "other"
    return {"intent": intent, "order_id": order_id, "audit": [f"classified:{intent}"]}


def route_intent(state: HelpdeskState) -> str:
    return state["intent"]


def retrieve_faq(state: HelpdeskState) -> dict:
    text = state["message"]
    selected = "policy-shipping" if "运费" in text else "policy-return"
    evidence = [{"id": selected, "text": FAQ[selected]}]
    return {"evidence": evidence, "audit": [f"retrieved:{selected}"]}


def lookup_order(state: HelpdeskState) -> dict:
    order_id = state.get("order_id", "")
    order = ORDERS.get(order_id)
    if not order_id:
        reply = "请提供 ORD-0000 格式的订单号。"
    elif not order or order["user_id"] != state["user_id"]:
        reply = "没有找到当前用户可访问的订单。"
    else:
        reply = f"{order_id} 当前状态：{order['status']}，已支付 ¥{order['paid']:.2f}。"
    return {"order": order or {}, "reply": reply, "audit": [f"lookup_order:{bool(order)}"]}


def prepare_refund(state: HelpdeskState) -> dict:
    order_id = state.get("order_id", "")
    order = ORDERS.get(order_id)
    ready = bool(order and order["user_id"] == state["user_id"])
    if not order_id:
        reply = "退款前请提供 ORD-0000 格式的订单号。"
    elif not ready:
        reply = "订单不存在或不属于当前用户，不能退款。"
    else:
        reply = "退款请求已准备，等待人工审批。"

    action = {
        "ready": ready,
        "kind": "refund",
        "order_id": order_id,
        "amount": order["paid"] if ready else 0,
        "idempotency_key": f"refund:{order_id}:{state['request_id']}",
    }
    return {"draft_action": action, "reply": reply, "audit": [f"refund_ready:{ready}"]}


def route_prepared(state: HelpdeskState) -> str:
    return "approval" if state["draft_action"]["ready"] else "compose"


def await_approval(state: HelpdeskState) -> dict:
    action = state["draft_action"]
    decision = interrupt(
        {
            "type": "refund_approval",
            "order_id": action["order_id"],
            "amount": action["amount"],
            "message": "批准后将执行幂等退款；可选择 approve 或 reject。",
        }
    )
    approved = bool(decision.get("approved", False))
    return {"approval": {"approved": approved}, "audit": [f"approved:{approved}"]}


def route_approval(state: HelpdeskState) -> str:
    return "execute" if state["approval"]["approved"] else "reject"


def execute_refund(state: HelpdeskState) -> dict:
    action = state["draft_action"]
    key = action["idempotency_key"]
    duplicate = key in REFUND_RESULTS
    if duplicate:
        result = REFUND_RESULTS[key]
    else:
        result = {
            "status": "refunded",
            "order_id": action["order_id"],
            "amount": action["amount"],
            "transaction_id": f"RF-{uuid.uuid4().hex[:8]}",
        }
        REFUND_RESULTS[key] = result
    return {"refund_result": result, "audit": [f"refund_executed:duplicate={duplicate}"]}


def reject_refund(state: HelpdeskState) -> dict:
    del state
    return {"reply": "退款未获批准，没有执行任何写操作。", "audit": ["refund_rejected"]}


def general(state: HelpdeskState) -> dict:
    del state
    return {"reply": "我可以回答退货政策、查询订单，或准备退款申请。", "audit": ["general"]}


def compose(state: HelpdeskState) -> dict:
    if state.get("refund_result"):
        result = state["refund_result"]
        reply = (
            f"退款已完成：{result['order_id']}，金额 ¥{result['amount']:.2f}，"
            f"交易号 {result['transaction_id']}。"
        )
    elif state.get("evidence"):
        evidence = state["evidence"]
        reply = f"{evidence[0]['text']} [来源：{evidence[0]['id']}]"
    else:
        reply = state.get("reply", "暂时无法处理，请转人工客服。")
    return {"reply": reply, "audit": ["composed"]}


def build_graph():
    builder = StateGraph(HelpdeskState)
    builder.add_node("classify", classify)
    builder.add_node("retrieve_faq", retrieve_faq)
    builder.add_node("lookup_order", lookup_order)
    builder.add_node("prepare_refund", prepare_refund)
    builder.add_node("await_approval", await_approval)
    builder.add_node("execute_refund", execute_refund)
    builder.add_node("reject_refund", reject_refund)
    builder.add_node("general", general)
    builder.add_node("compose", compose)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_intent,
        {
            "knowledge": "retrieve_faq",
            "order": "lookup_order",
            "refund": "prepare_refund",
            "other": "general",
        },
    )
    builder.add_edge("retrieve_faq", "compose")
    builder.add_edge("lookup_order", "compose")
    builder.add_edge("general", "compose")
    builder.add_conditional_edges(
        "prepare_refund",
        route_prepared,
        {"approval": "await_approval", "compose": "compose"},
    )
    builder.add_conditional_edges(
        "await_approval",
        route_approval,
        {"execute": "execute_refund", "reject": "reject_refund"},
    )
    builder.add_edge("execute_refund", "compose")
    builder.add_edge("reject_refund", "compose")
    builder.add_edge("compose", END)
    return builder.compile(checkpointer=InMemorySaver())


def start_request(graph, message: str, *, thread_id: str, request_id: str | None = None) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    state: HelpdeskState = {
        "user_id": "demo-user",
        "request_id": request_id or thread_id,
        "message": message,
        "audit": [],
    }
    return graph.invoke(state, config=config)


def resume_request(graph, *, thread_id: str, approved: bool) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(Command(resume={"approved": approved}), config=config)


def run_request(message: str, *, approved: bool | None = None, thread_id: str = "demo") -> dict:
    """测试友好入口；有退款时可传 approved 自动恢复。"""
    graph = build_graph()
    result = start_request(graph, message, thread_id=thread_id)
    if "__interrupt__" in result and approved is not None:
        result = resume_request(graph, thread_id=thread_id, approved=approved)
    return result


def main() -> None:
    message = " ".join(sys.argv[1:]) or "退货期限是多久？"
    thread_id = f"cli-{uuid.uuid4().hex[:8]}"
    graph = build_graph()
    result = start_request(graph, message, thread_id=thread_id)

    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("需要审批：", payload)
        choice = input("输入 approve 批准，其余内容视为拒绝：").strip().lower()
        result = resume_request(graph, thread_id=thread_id, approved=choice == "approve")

    print("答复：", result["reply"])
    print("审计轨迹：", result["audit"])


if __name__ == "__main__":
    main()


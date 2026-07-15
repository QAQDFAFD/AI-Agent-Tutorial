"""一个包含状态、条件边和有限质量循环的 LangGraph 工单图。"""

from __future__ import annotations

import re
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class SupportState(TypedDict, total=False):
    question: str
    intent: Literal["knowledge", "account", "other"]
    evidence: list[str]
    answer: str
    attempts: int
    needs_rewrite: bool


def classify(state: SupportState) -> dict:
    question = state["question"]
    if "ORD-" in question.upper() or "订单" in question:
        intent: Literal["knowledge", "account", "other"] = "account"
    elif any(word in question for word in ("退货", "运费", "政策")):
        intent = "knowledge"
    else:
        intent = "other"
    return {"intent": intent, "attempts": state.get("attempts", 0)}


def route_intent(state: SupportState) -> str:
    return state["intent"]


def answer_knowledge(state: SupportState) -> dict:
    del state
    evidence = ["policy-return: 签收后 7 天内可申请无理由退货，定制商品除外。"]
    return {"evidence": evidence, "answer": f"根据政策：{evidence[0]}"}


def answer_account(state: SupportState) -> dict:
    match = re.search(r"ORD-\d{4}", state["question"].upper())
    if not match:
        return {"evidence": [], "answer": "请提供 ORD-0000 格式的订单号。"}
    order_id = match.group(0)
    return {"evidence": [f"order:{order_id}"], "answer": f"{order_id} 当前状态为运输中。"}


def answer_general(state: SupportState) -> dict:
    del state
    # 故意返回一个过短的低质量回答，让质量循环真的会被触发。
    return {"evidence": [], "answer": "你好！"}


def quality_check(state: SupportState) -> dict:
    """质量门：回答太短且还有重写额度时要求重写。attempts 上限保证循环必然终止。"""
    answer = state.get("answer", "")
    needs_rewrite = len(answer) < 12 and state.get("attempts", 0) < 1
    return {"needs_rewrite": needs_rewrite}


def route_quality(state: SupportState) -> str:
    return "rewrite" if state["needs_rewrite"] else "finish"


def rewrite(state: SupportState) -> dict:
    return {
        "answer": f"补充说明：{state.get('answer', '')} 我可以回答退货政策或查询订单状态；"
        "如仍有疑问，请转人工客服。",
        "attempts": state.get("attempts", 0) + 1,
    }


def build_graph():
    builder = StateGraph(SupportState)
    builder.add_node("classify", classify)
    builder.add_node("knowledge", answer_knowledge)
    builder.add_node("account", answer_account)
    builder.add_node("general", answer_general)
    builder.add_node("quality_check", quality_check)
    builder.add_node("rewrite", rewrite)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_intent,
        {"knowledge": "knowledge", "account": "account", "other": "general"},
    )
    for node in ("knowledge", "account", "general"):
        builder.add_edge(node, "quality_check")
    builder.add_conditional_edges(
        "quality_check", route_quality, {"rewrite": "rewrite", "finish": END}
    )
    # 重写后回到质量门重新检查，形成一个有终止保证的循环。
    builder.add_edge("rewrite", "quality_check")
    return builder.compile()


def main() -> None:
    graph = build_graph()
    for question in ["退货政策是什么？", "查询 ORD-1001", "你好"]:
        print(f"\n用户：{question}")
        for event in graph.stream({"question": question, "attempts": 0}):
            print(event)


if __name__ == "__main__":
    main()


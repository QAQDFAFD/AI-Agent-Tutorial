"""使用 LangChain 1.x create_agent 构建带工具与结构化输出的客服 Agent。"""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

POLICIES = [
    {"id": "policy-return", "text": "签收后 7 天内可申请无理由退货，定制商品除外。"},
    {"id": "policy-shipping", "text": "质量问题退货由商家承担运费。"},
]

ORDERS = {"ORD-1001": {"status": "shipped", "eta": "2026-07-18"}}


@tool
def search_policy(query: str, top_k: int = 2) -> list[dict[str, str]]:
    """搜索公开售后政策；只用于政策问题，不用于读取具体订单。top_k 最大为 3。"""
    top_k = max(1, min(top_k, 3))
    tokens = set(query)
    ranked = sorted(POLICIES, key=lambda item: len(tokens & set(item["text"])), reverse=True)
    return ranked[:top_k]


@tool
def lookup_order(order_id: str) -> dict:
    """读取一个 ORD-0000 格式订单的模拟状态；只读，不执行退款。"""
    order = ORDERS.get(order_id)
    return {"ok": bool(order), "order_id": order_id, "data": order}


class SupportAnswer(BaseModel):
    answer: str
    source_ids: list[str] = Field(default_factory=list)
    action: Literal["answered", "ask_user", "escalate"]


def build_agent():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("请先复制 .env.example 为 .env 并填写 OPENAI_API_KEY")

    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-5.6"))
    return create_agent(
        model=model,
        tools=[search_policy, lookup_order],
        system_prompt=(
            "你是电商客服。政策必须先调用 search_policy，订单状态必须调用 lookup_order；"
            "不得编造工具未返回的数据。缺少订单号时向用户询问。回答简洁。"
        ),
        response_format=ToolStrategy(SupportAnswer),
    )


def main() -> None:
    load_dotenv()
    try:
        agent = build_agent()
    except RuntimeError as exc:
        print(exc)
        return

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "签收后多久可以无理由退货？"}]}
    )
    answer: SupportAnswer = result["structured_response"]
    print(answer.model_dump_json(indent=2))


if __name__ == "__main__":
    main()


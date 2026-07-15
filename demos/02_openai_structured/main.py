"""Pydantic 合同 + OpenAI Responses API 结构化输出。"""

from __future__ import annotations

import os
import re
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class TicketDecision(BaseModel):
    intent: Literal["knowledge", "order", "refund", "other"]
    confidence: float = Field(ge=0, le=1)
    order_id: str | None = Field(default=None, pattern=r"^ORD-\d{4}$")
    missing_fields: list[str] = Field(default_factory=list)
    next_action: str


def classify_locally(text: str) -> TicketDecision:
    """离线 fallback：演示同一份输出合同，不冒充真实 LLM。"""
    order_match = re.search(r"ORD-\d{4}", text.upper())
    order_id = order_match.group(0) if order_match else None

    if "退款" in text or "退钱" in text:
        intent = "refund"
    elif "订单" in text or order_id:
        intent = "order"
    elif any(word in text for word in ("政策", "多久", "怎么退", "运费")):
        intent = "knowledge"
    else:
        intent = "other"

    missing = ["order_id"] if intent in {"order", "refund"} and not order_id else []
    action = "询问订单号" if missing else "进入对应处理流程"
    return TicketDecision(
        intent=intent,
        confidence=0.9 if intent != "other" else 0.55,
        order_id=order_id,
        missing_fields=missing,
        next_action=action,
    )


def classify_with_openai(text: str) -> TicketDecision:
    """使用官方 Python SDK，把模型输出直接解析为 Pydantic 对象。"""
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
        input=[
            {
                "role": "system",
                "content": (
                    "你是电商工单分类器。只根据用户输入分类；缺少订单号时放入 "
                    "missing_fields，不得编造订单号。"
                ),
            },
            {"role": "user", "content": text},
        ],
        text_format=TicketDecision,
    )
    if response.output_parsed is None:
        raise RuntimeError("模型未返回可解析的 TicketDecision；请检查拒答和原始响应")
    return response.output_parsed


def main() -> None:
    load_dotenv()
    text = "我想给 ORD-1001 退款"
    if os.getenv("OPENAI_API_KEY"):
        print("使用 OpenAI Responses API")
        decision = classify_with_openai(text)
    else:
        print("未设置 OPENAI_API_KEY，使用本地规则演示同一 Pydantic 合同。")
        decision = classify_locally(text)
    print(decision.model_dump_json(indent=2))


if __name__ == "__main__":
    main()


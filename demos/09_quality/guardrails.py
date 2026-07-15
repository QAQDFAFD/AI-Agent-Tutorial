"""确定性输入/工具护栏和教学版幂等执行器。"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class GuardrailRejected(ValueError):
    pass


INJECTION_PATTERNS = [
    r"ignore (all|the|previous)",
    r"忽略(以上|之前|系统)",
    r"泄露.*(system prompt|系统提示|密钥)",
]


def check_input(text: str, *, max_length: int = 2_000) -> None:
    if not text.strip():
        raise GuardrailRejected("EMPTY_INPUT")
    if len(text) > max_length:
        raise GuardrailRejected("INPUT_TOO_LONG")
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in INJECTION_PATTERNS):
        raise GuardrailRejected("PROMPT_INJECTION_PATTERN")


@dataclass(frozen=True)
class ToolPolicy:
    allowed_tools: frozenset[str]
    max_refund: float = 500.0

    def validate(self, tool_name: str, arguments: dict[str, Any]) -> None:
        if tool_name not in self.allowed_tools:
            raise GuardrailRejected("TOOL_NOT_ALLOWED")
        if tool_name == "refund":
            amount = float(arguments.get("amount", -1))
            if amount <= 0 or amount > self.max_refund:
                raise GuardrailRejected("REFUND_AMOUNT_OUT_OF_RANGE")
            if not arguments.get("approved", False):
                raise GuardrailRejected("APPROVAL_REQUIRED")


@dataclass
class IdempotencyStore:
    """教学版内存实现；生产必须使用带唯一约束的持久化存储。"""

    results: dict[str, Any] = field(default_factory=dict)

    def execute_once(self, key: str, operation: Callable[[], Any]) -> tuple[Any, bool]:
        if key in self.results:
            return self.results[key], True
        result = operation()
        self.results[key] = result
        return result, False


def main() -> None:
    policy = ToolPolicy(frozenset({"lookup_order", "refund"}), max_refund=500)
    policy.validate("refund", {"amount": 99, "approved": True})
    store = IdempotencyStore()
    print(store.execute_once("refund:ORD-1001:req-1", lambda: {"status": "refunded"}))
    print(store.execute_once("refund:ORD-1001:req-1", lambda: {"status": "duplicated"}))


if __name__ == "__main__":
    main()


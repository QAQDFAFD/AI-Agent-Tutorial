"""Router + 三个窄职责专家；确定性实现便于先测试协作协议。"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field


class Delegation(BaseModel):
    specialist: Literal["math", "writer", "general"]
    goal: str
    constraints: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    specialist: str
    answer: str
    artifacts: list[str] = Field(default_factory=list)


def route(text: str) -> Delegation:
    if re.search(r"\d+\s*\+\s*\d+", text):
        return Delegation(specialist="math", goal=text, constraints=["只允许加法"])
    if any(word in text for word in ("改写", "文案", "标题")):
        return Delegation(specialist="writer", goal=text, constraints=["不改变事实"])
    return Delegation(specialist="general", goal=text)


def math_agent(task: Delegation) -> AgentResult:
    match = re.search(r"(-?\d+)\s*\+\s*(-?\d+)", task.goal)
    if not match:
        return AgentResult(specialist="math", answer="只支持形如 12 + 30 的加法。")
    value = int(match.group(1)) + int(match.group(2))
    return AgentResult(specialist="math", answer=f"结果是 {value}。")


def writer_agent(task: Delegation) -> AgentResult:
    text = re.sub(r"^(请)?(帮我)?(改写|写一个文案|写标题)[:：\s]*", "", task.goal)
    return AgentResult(specialist="writer", answer=f"清晰版：{text.strip()}")


def general_agent(task: Delegation) -> AgentResult:
    return AgentResult(
        specialist="general",
        answer=f"通用助手收到任务：{task.goal}。如需专业处理，请补充更具体的信息。",
    )


SPECIALISTS: dict[str, Callable[[Delegation], AgentResult]] = {
    "math": math_agent,
    "writer": writer_agent,
    "general": general_agent,
}


def dispatch(text: str) -> AgentResult:
    delegation = route(text)
    specialist = SPECIALISTS[delegation.specialist]
    return specialist(delegation)


def main() -> None:
    for text in ["请算 19 + 23", "帮我改写：Agent 要有停止条件", "你好"]:
        print(dispatch(text).model_dump_json(indent=2))


if __name__ == "__main__":
    main()


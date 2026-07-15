"""一个透明、可测试、带停止条件的最小 Agent Loop。"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError


class ToolCall(BaseModel):
    """模型提出的工具调用建议。"""

    id: str
    name: str
    arguments: dict[str, Any]


class ModelReply(BaseModel):
    """模型一轮只能返回最终文本，或一个/多个工具调用。"""

    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ModelAdapter(Protocol):
    def complete(self, messages: list[dict[str, Any]], tools: list[dict]) -> ModelReply:
        """根据消息与工具 schema 给出下一步。"""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_schema: type[BaseModel]
    handler: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.args_schema.model_json_schema(),
        }

    def invoke(self, raw_arguments: dict[str, Any]) -> dict[str, Any]:
        """校验参数并把异常翻译为稳定的 observation。"""
        try:
            arguments = self.args_schema.model_validate(raw_arguments)
            value = self.handler(**arguments.model_dump())
            return {"ok": True, "value": value}
        except ValidationError as exc:
            return {
                "ok": False,
                "code": "INVALID_ARGUMENTS",
                "recoverable": True,
                "message": exc.errors(include_url=False),
            }
        except Exception as exc:  # 工具边界要把内部异常转为稳定协议
            return {
                "ok": False,
                "code": "TOOL_ERROR",
                "recoverable": False,
                "message": type(exc).__name__,
            }


class WeatherArgs(BaseModel):
    city: str = Field(min_length=1, max_length=20)


class AddArgs(BaseModel):
    a: float
    b: float


WEATHER = {"北京": "雷阵雨，31℃", "上海": "多云，33℃", "深圳": "晴，32℃"}


def get_weather(city: str) -> dict[str, str]:
    if city not in WEATHER:
        return {"status": "not_found", "city": city}
    return {"status": "ok", "city": city, "weather": WEATHER[city]}


def add(a: float, b: float) -> float:
    return a + b


TOOLS = [
    Tool(
        name="get_weather",
        description="读取指定中国城市的模拟天气；用户没给城市时不要调用。只读。",
        args_schema=WeatherArgs,
        handler=get_weather,
    ),
    Tool(
        name="add",
        description="计算两个数字之和。只用于加法，不执行任意表达式。",
        args_schema=AddArgs,
        handler=add,
    ),
]


class RuleBasedModel:
    """可预测的模型替身，只为把 Agent 控制流完整展示出来。"""

    def complete(self, messages: list[dict[str, Any]], tools: list[dict]) -> ModelReply:
        del tools
        last = messages[-1]

        if last["role"] == "tool":
            observation = json.loads(last["content"])
            if not observation["result"]["ok"]:
                return ModelReply(content=f"工具执行失败：{observation['result']['code']}")
            return ModelReply(
                content=f"已根据 {observation['name']} 的结果回答：{observation['result']['value']}"
            )

        text = str(last["content"])
        if "天气" in text:
            city = next((name for name in WEATHER if name in text), "")
            return ModelReply(
                tool_calls=[
                    ToolCall(
                        id="call_weather_1",
                        name="get_weather",
                        arguments={"city": city},
                    )
                ]
            )

        addition = re.search(r"(-?\d+(?:\.\d+)?)\s*\+\s*(-?\d+(?:\.\d+)?)", text)
        if addition:
            return ModelReply(
                tool_calls=[
                    ToolCall(
                        id="call_add_1",
                        name="add",
                        arguments={"a": float(addition.group(1)), "b": float(addition.group(2))},
                    )
                ]
            )

        return ModelReply(content="这个离线模型只会查询北京/上海/深圳天气或做加法。")


class StepLimitExceeded(RuntimeError):
    """Agent 达到最大步数仍未给出最终答案。"""


@dataclass
class AgentRun:
    answer: str
    steps: int
    trace: list[dict[str, Any]]


def run_agent(
    model: ModelAdapter,
    user_input: str,
    tools: list[Tool] = TOOLS,
    *,
    max_steps: int = 5,
) -> AgentRun:
    """执行模型-工具循环；只记录可审计动作，不记录隐藏思维过程。"""
    registry = {tool.name: tool for tool in tools}
    tool_schemas = [tool.schema() for tool in tools]
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_input}]
    trace: list[dict[str, Any]] = []

    for step in range(1, max_steps + 1):
        started = time.perf_counter()
        reply = model.complete(messages, tool_schemas)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

        if reply.content is not None and not reply.tool_calls:
            trace.append({"step": step, "event": "final", "latency_ms": elapsed_ms})
            return AgentRun(answer=reply.content, steps=step, trace=trace)

        if not reply.tool_calls:
            raise RuntimeError("模型既没有给最终答案，也没有提出工具调用")

        for call in reply.tool_calls:
            tool = registry.get(call.name)
            if tool is None:
                result = {
                    "ok": False,
                    "code": "UNKNOWN_TOOL",
                    "recoverable": False,
                    "message": f"工具 {call.name!r} 不在 allowlist 中",
                }
            else:
                result = tool.invoke(call.arguments)

            trace.append(
                {
                    "step": step,
                    "event": "tool_call",
                    "tool": call.name,
                    "ok": result["ok"],
                    "latency_ms": elapsed_ms,
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "tool_call": call.model_dump(),
                    "content": None,
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(
                        {"name": call.name, "result": result}, ensure_ascii=False
                    ),
                }
            )

    raise StepLimitExceeded(f"达到 max_steps={max_steps}，为避免无限循环已安全停止")


def main() -> None:
    model = RuleBasedModel()
    for question in ["北京天气怎么样？", "请计算 19 + 23", "给我讲个笑话"]:
        run = run_agent(model, question)
        print(f"\n用户：{question}\nAgent：{run.answer}\nTrace：{run.trace}")


if __name__ == "__main__":
    main()


"""真实 OpenAI Responses API 工具调用循环。

这是 demos/01_agent_loop 的"真实模型版"：同样的循环骨架
（模型提出调用 → allowlist → Pydantic 校验 → 执行 → observation 回传），
只是把 RuleBasedModel 换成真实模型。对照阅读两个文件，你会看到
框架帮你做的事情其实就这么多。

运行前需要在 .env 中配置 OPENAI_API_KEY。
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

WEATHER = {"北京": "雷阵雨，31℃", "上海": "多云，33℃", "深圳": "晴，32℃"}


class WeatherArgs(BaseModel):
    city: str = Field(min_length=1, max_length=20, description="中国城市名，例如 北京")


def get_weather(city: str) -> dict[str, str]:
    if city not in WEATHER:
        return {"status": "not_found", "city": city, "hint": "只支持北京/上海/深圳"}
    return {"status": "ok", "city": city, "weather": WEATHER[city]}


# 模型看到的工具 schema：名称、描述和参数结构都是 Prompt 的一部分。
TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "查询指定中国城市的模拟天气；只读。用户没给城市时不要调用。",
        "parameters": WeatherArgs.model_json_schema(),
    }
]

# allowlist：模型只能调用这里登记过的函数，防止调用任意代码。
TOOL_HANDLERS = {"get_weather": (WeatherArgs, get_weather)}


def execute_tool_call(name: str, raw_arguments: str) -> dict:
    """校验并执行一次工具调用，把所有异常翻译成稳定的 observation。"""
    if name not in TOOL_HANDLERS:
        return {"ok": False, "code": "UNKNOWN_TOOL", "message": f"{name} 不在 allowlist 中"}
    args_schema, handler = TOOL_HANDLERS[name]
    try:
        arguments = args_schema.model_validate_json(raw_arguments)
    except ValidationError as exc:
        return {"ok": False, "code": "INVALID_ARGUMENTS", "message": exc.errors(include_url=False)}
    return {"ok": True, "value": handler(**arguments.model_dump())}


def run_agent(user_input: str, *, max_steps: int = 5) -> str:
    from openai import OpenAI

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5.6")
    # Responses API 的输入是一个"条目列表"：用户消息、模型的函数调用、
    # 以及我们回填的函数结果都追加在同一个列表里。
    input_items: list = [{"role": "user", "content": user_input}]

    for step in range(1, max_steps + 1):
        response = client.responses.create(model=model, input=input_items, tools=TOOL_SCHEMAS)

        tool_calls = [item for item in response.output if item.type == "function_call"]
        if not tool_calls:
            return response.output_text  # 模型给出了最终回答，循环结束

        for call in tool_calls:
            observation = execute_tool_call(call.name, call.arguments)
            print(f"[step {step}] 模型请求 {call.name}({call.arguments}) -> {observation}")
            # 关键协议：先回放模型的函数调用条目，再附上同 call_id 的执行结果。
            input_items.append(call)
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(observation, ensure_ascii=False),
                }
            )

    raise RuntimeError(f"达到 max_steps={max_steps}，为避免无限循环已安全停止")


def main() -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print(
            "未设置 OPENAI_API_KEY。\n"
            "本示例演示真实模型的工具调用协议，需要先复制 .env.example 为 .env 并填写密钥。\n"
            "不想花钱？demos/01_agent_loop 用离线模型替身演示了完全相同的循环骨架。"
        )
        return

    for question in ["北京天气怎么样？", "帮我写一句关于夏天的诗"]:
        print(f"\n用户：{question}")
        print(f"Agent：{run_agent(question)}")


if __name__ == "__main__":
    main()

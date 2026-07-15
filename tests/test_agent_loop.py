import importlib

import pytest

loop = importlib.import_module("demos.01_agent_loop.main")


def test_agent_calls_weather_tool():
    result = loop.run_agent(loop.RuleBasedModel(), "北京天气怎么样？")
    assert "北京" in result.answer
    assert result.steps == 2
    assert result.trace[0]["tool"] == "get_weather"


def test_tool_arguments_are_validated():
    weather = next(tool for tool in loop.TOOLS if tool.name == "get_weather")
    result = weather.invoke({"city": ""})
    assert result["ok"] is False
    assert result["code"] == "INVALID_ARGUMENTS"


def test_agent_has_hard_step_limit():
    class LoopingModel:
        def complete(self, messages, tools):
            del messages, tools
            return loop.ModelReply(
                tool_calls=[loop.ToolCall(id="loop", name="add", arguments={"a": 1, "b": 1})]
            )

    with pytest.raises(loop.StepLimitExceeded):
        loop.run_agent(LoopingModel(), "loop", max_steps=2)


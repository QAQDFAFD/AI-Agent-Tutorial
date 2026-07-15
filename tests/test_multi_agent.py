import importlib

multi = importlib.import_module("demos.07_multi_agent.main")


def test_router_selects_math_specialist():
    result = multi.dispatch("计算 19 + 23")
    assert result.specialist == "math"
    assert "42" in result.answer


def test_writer_has_uniform_result_contract():
    result = multi.dispatch("帮我改写：Agent 要有停止条件")
    assert result.specialist == "writer"
    assert result.artifacts == []


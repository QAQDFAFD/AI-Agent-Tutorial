import importlib

memory = importlib.import_module("demos.05_memory.main")


def test_threads_keep_separate_short_term_memory():
    graph = memory.build_graph()
    first = memory.continue_thread(graph, "a", "第一条")
    second = memory.continue_thread(graph, "a", "第二条")
    other = memory.continue_thread(graph, "b", "新会话")
    assert first["turns"] == 1
    assert second["turns"] == 2
    assert other["turns"] == 1
    assert len(second["messages"]) == 4


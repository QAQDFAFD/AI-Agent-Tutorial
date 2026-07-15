"""使用 InMemorySaver 演示 thread 级短期记忆和隔离。"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class ConversationState(TypedDict, total=False):
    messages: Annotated[list[str], operator.add]
    turns: int
    summary: str


def respond(state: ConversationState) -> dict:
    user_message = state["messages"][-1]
    turns = state.get("turns", 0) + 1
    return {
        "messages": [f"assistant: 这是该 thread 的第 {turns} 轮，我收到：{user_message}"],
        "turns": turns,
        "summary": f"已经交流 {turns} 轮；最近用户消息是 {user_message}",
    }


def build_graph():
    builder = StateGraph(ConversationState)
    builder.add_node("respond", respond)
    builder.add_edge(START, "respond")
    builder.add_edge("respond", END)
    return builder.compile(checkpointer=InMemorySaver())


def continue_thread(graph, thread_id: str, message: str) -> ConversationState:
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke({"messages": [f"user: {message}"]}, config=config)


def main() -> None:
    graph = build_graph()
    print(continue_thread(graph, "thread-a", "我喜欢简洁回答"))
    print(continue_thread(graph, "thread-a", "我们聊了几轮？"))
    print(continue_thread(graph, "thread-b", "这是新会话"))


if __name__ == "__main__":
    main()


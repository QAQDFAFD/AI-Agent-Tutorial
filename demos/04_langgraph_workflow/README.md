# Demo 04：LangGraph 状态工作流

对应[第 05 章](../../docs/05-langgraph-workflow.md)。无需 API Key。

```bash
uv run python -m demos.04_langgraph_workflow.main
```

代码包含 `SupportState`、分类节点、三条条件分支、质量检查和一个真实的有限循环（`rewrite → quality_check` 回边，靠 `attempts` 上限终止）。输入“你好”即可观察循环触发。所有节点都是普通 Python 函数，因此可以独立单元测试。


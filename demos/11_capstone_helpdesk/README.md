# Demo 11：综合客服 Agent

对应[第 13 章](../../docs/13-capstone.md)。无需 API Key。

```bash
uv run python -m demos.11_capstone_helpdesk.main "退货期限是多久？"
uv run python -m demos.11_capstone_helpdesk.main "查询 ORD-1001"
uv run python -m demos.11_capstone_helpdesk.main "给 ORD-1001 退款"
```

退款路径会通过 LangGraph `interrupt()` 暂停，输入 `approve` 后才进入幂等写节点。分类和回答可替换为 LLM，账户权限、审批、金额与幂等约束应继续留在确定性代码中。


# Demo 09：Guardrails + 离线评测

对应[第 10 章](../../docs/10-reliability-and-safety.md)和[第 11 章](../../docs/11-evaluation-observability.md)。无需 API Key。

```bash
uv run python -m demos.09_quality.guardrails
uv run python -m demos.09_quality.evaluate
```

护栏拒绝输入、工具越权和未审批退款；评测脚本从 JSONL 数据集读取样例，输出总体准确率和逐条失败。


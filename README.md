# AI Agent Tutor：Python AI Agent 从入门到生产

这不是一份“把 LangChain 方法名抄一遍”的手册，而是一条从原理、代码到生产实践的完整学习路线。你会先亲手写一个几十行的 Agent Loop，再使用 LangChain 快速组装 Agent，最后用 LangGraph 构建有状态、可暂停、可恢复、可评测的工作流。

> 适合谁：会 Python 基础语法，想系统学习 Agent，或已经能调用 LLM API、但还不知道怎样把 Demo 变成可靠应用的开发者。

![AI Agent 学习路线](assets/diagrams/learning-roadmap.svg)

## 先给结论：需要掌握什么

AI Agent 开发可以分成四层。越靠下越基础，越靠上越接近生产：

| 层次 | 必须掌握 | 这一层解决什么问题 |
|---|---|---|
| L1 模型交互 | Python、HTTP/JSON、异步、Token/上下文、Prompt、结构化输出 | 让模型稳定地“听懂并按格式回答” |
| L2 能力扩展 | Tool Calling、Pydantic、RAG、短期/长期记忆、MCP | 让模型能查资料、调用业务能力、记住必要信息 |
| L3 工作流编排 | Agent Loop、状态机、LangChain、LangGraph、流式输出、HITL、多 Agent | 让复杂任务可控、可暂停、可恢复 |
| L4 工程与治理 | 测试、评测、Tracing、安全、权限、成本、FastAPI、队列/数据库、部署 | 让系统可靠、可观测、可上线 |

核心栈的关系：

- **LangChain**：模型、消息、工具、检索器和预构建 Agent 的高层抽象，适合快速完成常见模式。
- **LangGraph**：底层编排运行时，用 `State + Node + Edge` 明确表达循环、分支、持久化和人工审批。
- **Pydantic**：给工具参数和模型输出建立“合同”，拒绝不合法数据。
- **OpenAI Responses API / Agents SDK**：前者适合自己控制模型与工具循环，后者适合使用内置的工具、交接、护栏、会话和追踪能力。
- **MCP**：把外部工具、资源和提示以统一协议接给不同 Agent 主机。
- **FastAPI + asyncio**：把 Agent 暴露成服务，并正确处理并发、超时和流式输出。
- **LangSmith / OpenTelemetry / 自建日志**：追踪一次运行到底经过了哪些步骤；测试与评测则回答“改完以后真的更好吗”。

## 学习路线与 Demo 对照

| 章节 | 主题 | 核心 Demo | 是否需要 API Key |
|---|---|---|---|
| [00](docs/00-learning-map.md) | 全景地图与学习顺序 | — | 否 |
| [01](docs/01-agent-foundations.md) | Agent 本质与手写循环 | [`01_agent_loop`](demos/01_agent_loop/) | 否 |
| [02](docs/02-models-prompts-structured-output.md) | 模型 API、Prompt、结构化输出 | [`02_openai_structured`](demos/02_openai_structured/) | 联网模式需要 |
| [03](docs/03-tools-and-actions.md) | 工具调用、参数校验与副作用 | `01_agent_loop` + `02_openai_structured` | 可选 |
| [04](docs/04-langchain-agent.md) | LangChain 1.x Agent | [`03_langchain_agent`](demos/03_langchain_agent/) | 需要 |
| [05](docs/05-langgraph-workflow.md) | 状态、节点、边、分支与恢复 | [`04_langgraph_workflow`](demos/04_langgraph_workflow/) | 否 |
| [06](docs/06-memory-and-context.md) | 短期/长期记忆与上下文工程 | [`05_memory`](demos/05_memory/) | 否 |
| [07](docs/07-rag.md) | 检索、切块、召回、重排与引用 | [`06_rag`](demos/06_rag/) | 否 |
| [08](docs/08-multi-agent.md) | Router、Supervisor、Handoff | [`07_multi_agent`](demos/07_multi_agent/) | 否 |
| [09](docs/09-mcp.md) | MCP 工具与资源协议 | [`08_mcp`](demos/08_mcp/) | 否 |
| [10](docs/10-reliability-and-safety.md) | 护栏、权限、注入、重试、幂等 | [`09_quality`](demos/09_quality/) | 否 |
| [11](docs/11-evaluation-observability.md) | 离线评测、在线监控、Tracing | [`09_quality`](demos/09_quality/) | 否 |
| [12](docs/12-production.md) | API、并发、存储、部署与成本 | [`10_service`](demos/10_service/) | 否 |
| [13](docs/13-capstone.md) | 综合客服 Agent | [`11_capstone_helpdesk`](demos/11_capstone_helpdesk/) | 否；可扩展联网模型 |
| [附录 A](docs/setup.md) | 环境准备与常见报错排查 | — | 否 |
| [附录 B](docs/glossary.md) | 初学者术语表 | — | 否 |
| [附录 C](docs/reading-list.md) | 精读文选：2022–2026 影响 Agent 领域的论文与文章 | — | 否 |

## 5 分钟跑起来

推荐安装 [uv](https://docs.astral.sh/uv/)，也可以使用普通 `venv + pip`。第一次搭环境或遇到报错，请看[附录 A：环境准备](docs/setup.md)（含国内 OpenAI 兼容服务的配置方法）。

```bash
cp .env.example .env
uv sync
uv run python -m demos.01_agent_loop.main
uv run python -m demos.04_langgraph_workflow.main
uv run python -m demos.06_rag.main
uv run pytest
```

要运行真实模型示例，在 `.env` 中填写 `OPENAI_API_KEY`：

```bash
uv run python -m demos.02_openai_structured.main
uv run python -m demos.02_openai_structured.tool_calling
uv run python -m demos.03_langchain_agent.main
```

启动 API 服务：

```bash
uv run uvicorn demos.10_service.app:app --reload
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"thread_id":"demo-1","message":"LangGraph 是什么？"}'
```

## 建议的学习节奏

- **第 1 周：打地基。** 读 00–03，必须亲手改坏再修好 Agent Loop。重点观察工具参数、最大步数与错误分支。
- **第 2 周：学会编排。** 读 04–07，把同一个需求分别用 LangChain 和 LangGraph 实现，体会“高层便利”和“底层控制”的差别。
- **第 3 周：从单体到系统。** 读 08–10，重点理解多 Agent 何时反而更糟、MCP 的信任边界、写操作为什么要审批。
- **第 4 周：按上线标准做。** 读 11–13，为综合项目添加自己的测试集、持久化存储和一个真实业务工具。

每学完一个章节，至少回答三个问题：**状态在哪里？失败如何恢复？怎样知道它做对了？** 如果答不上来，就还只是一个会动的 Demo。

## 选型建议：别一上来就“全家桶”

| 情况 | 建议 |
|---|---|
| 只有一次模型调用和一个固定后处理 | 直接使用模型 SDK，不需要 Agent 框架 |
| 标准工具调用 Agent，想快速交付 | LangChain `create_agent` |
| 明确的多步骤、分支、审批、长任务 | LangGraph |
| 主要工作是文档索引与复杂检索 | LangChain 检索组件或 LlamaIndex；编排仍可用 LangGraph |
| 希望工具能跨不同 Agent 客户端复用 | MCP |
| 深度绑定 OpenAI，并希望内置 handoff/guardrail/tracing | OpenAI Agents SDK |

框架只是放大器。一个没有权限边界、评测集和失败策略的复杂图，通常不如一个小而确定的工作流。

## 仓库结构

```text
.
├── docs/                 # 14 个循序渐进的中文章节 + 环境准备/术语表附录
├── demos/                # 与章节一一对应的完整 Python Demo
├── assets/diagrams/      # Mermaid 源文件与导出的 SVG 图（每章配图）
├── tests/                # 不依赖网络和 API Key 的回归测试
├── .env.example          # 模型与追踪配置模板
├── pyproject.toml        # Python 依赖与工具配置
└── Makefile              # 常用命令
```

## 版本与资料说明

教程按 **Python 3.11+、LangChain 1.x、LangGraph 1.x、Pydantic 2.x** 编写，资料检索日期为 **2026-07-15**。模型和框架更新很快，因此代码把模型名放在环境变量中，并在 [参考资料](docs/references.md) 中只收录官方文档。遇到接口差异，优先查看对应项目的迁移指南，而不是机械复制旧博客代码。

# 官方参考资料

以下资料用于核对教程架构和 API，检索日期为 **2026-07-15**。框架迭代很快，遇到版本差异请优先查看官方迁移指南与当前 API reference。

> 本页是"写代码时查 API"的工具书；想读塑造这个领域的论文和思想文章，请看[附录 C：精读文选](reading-list.md)。

## LangChain / LangGraph

- [LangGraph Overview](https://docs.langchain.com/oss/python/langgraph/overview)：LangGraph 的定位、持久化执行、流式输出、HITL 与记忆。
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)：State、Node、Edge 与 reducer。
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)：checkpoint、thread、time travel 与容错。
- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)：`create_agent`、工具、middleware、结构化输出。
- [LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools)：工具 schema 与运行时 state/context/store。
- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)：provider/tool strategy。
- [LangChain Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)：2-step、Agentic 与 Hybrid RAG。
- [LangChain Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)：批准、编辑、拒绝与 checkpoint。

## OpenAI

- [Responses API Function Calling](https://developers.openai.com/api/docs/guides/function-calling)：工具 schema、`function_call` 与 `function_call_output` 循环。
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)：Pydantic `responses.parse` 与支持范围。
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/agents/)：Agent、工具、handoff、guardrail 与结构化输出。
- [Agents SDK Running Agents](https://openai.github.io/openai-agents-python/running_agents/)：Runner、会话、运行配置和并发工具。
- [Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/)：trace/span、敏感数据与自定义处理器。

## MCP 与其他

- [MCP Architecture](https://modelcontextprotocol.io/docs/learn/architecture)：Host/Client/Server、数据层、传输层和 primitives。
- [LlamaIndex: Building an Agent](https://developers.llamaindex.ai/python/framework/understanding/agent/)：数据驱动 Agent 的另一种实现路径。
- [LangSmith Observability Concepts](https://docs.langchain.com/langsmith/observability-concepts)：project、trace、run 与 thread。
- [LangSmith Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts)：离线/在线、代码规则、LLM judge、pairwise 和人工评审。
- [FastAPI Async](https://fastapi.tiangolo.com/async/)：Python Web 服务中的异步与并发基础。

## 阅读顺序

初学者先读 LangGraph Overview、LangChain Agents、Function Calling 和 MCP Architecture；准备上线时再重点读 Persistence、Human-in-the-loop、Tracing 与 Evaluation。不要一次读完所有 API reference，带着正在实现的问题查询更有效。


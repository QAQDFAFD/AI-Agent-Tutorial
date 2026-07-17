# 14｜最终实战：把整个教程做成一个教学 Agent 站点

前 13 章的 Demo 都刻意写成"单文件从上到下"，方便你一眼看完。但真实项目不长这样。这一章我们交付一个**生产级结构**的完整应用：把 `docs/` 里的教程变成可浏览的站点，并挂一个懂教程内容的教学助手——你可以问它"checkpoint 是什么？"，它会先检索教程原文，再带着可点击的章节引用回答。

代码在 [`tutor/`](../tutor/) 目录。本章不逐行讲代码，而是回答一个更重要的问题：**同样的功能，"工程化的写法"和 Demo 的写法差在哪里，为什么值得差这么多。**

## 14.1 先跑起来

```bash
uv run uvicorn tutor.api.app:app --reload
# 打开 http://127.0.0.1:8000
```

不配置 `OPENAI_API_KEY` 也能用：阅读器完全可用，聊天输入框禁用并提示怎么配置。这不是偶然，而是第 10 章说的**优雅降级**——一个依赖不可用时，系统应当提供残缺但明确的服务，而不是整个崩掉。

配置 Key 后重启，首次启动会把全部章节切块（约 300 块）并调用 Embedding API 建索引，向量缓存在 `var/embeddings-cache.json`，之后重启不再花钱。

## 14.2 从单文件到分层：职责边界

`tutor/` 的结构是教科书式的分层：

```text
tutor/
├── config.py      # Settings：唯一读环境变量的地方
├── ingest/        # docs/*.md → Chapter → 带出处的 Chunk
├── rag/           # Embedding（缓存）→ VectorIndex → Retriever
├── agent/         # 提示词 + 工具 + create_agent 组装
├── api/           # FastAPI：schemas / routes / 应用工厂
└── web/           # 原生 HTML/CSS/JS 前端
```

判断分层是否合理，有一个实用标准：**每一层能否单独被替换和单独被测试。**

- 想换向量数据库？只动 `rag/index.py`，`agent/` 不知情。
- 想换前端框架？API 契约不变，`web/` 整个目录随便换。
- 测试 `api/` 时不想调模型？注入一个 FakeAgent（见 `tests/test_tutor_api.py`）。

支撑这种可替换性的是两个第 12 章讲过的手法：

1. **依赖注入**：`Retriever` 不自己创建 Embedding 客户端，而是构造时接收一个满足 `EmbeddingClient` 协议（Protocol）的对象。测试注入假实现，生产注入 `CachedEmbeddingClient(OpenAIEmbeddingClient(...))`。
2. **应用工厂**：`create_app(settings, agent=...)` 接受可选的 Settings 与 agent。所有装配（加载章节 → 切块 → 建索引 → 组装 Agent）集中在 lifespan 里完成一次，请求处理期间只读不建。

## 14.3 RAG 升级：从 token 重叠到 Embedding + 缓存

第 7 章的 `06_rag` 用 token 重叠做检索，好处是零依赖，坏处是"积分会过期吗"匹配不上"积分有效期 12 个月"这类同义表述。tutor 换成了真正的 Embedding 向量检索，但保留了第 7 章的全部原则：

- **切块保出处**：`chunker.py` 按 `##` 小节切块（代码块内的 `##` 不误切），每块带 `chapter_id / heading / anchor`，引用能精确到小节并跳转原文。
- **规模决定选型**：约 300 块，numpy 余弦相似度毫秒级出结果，引入向量数据库纯属自找麻烦。
- **成本要管理**：`CachedEmbeddingClient` 是个装饰器——按 `sha256(模型名 + 文本)` 缓存向量到磁盘，只有没见过的文本才真正调 API。全量重建索引只在文档变化时产生增量成本。

```python
# 装饰器模式：缓存逻辑与 API 调用逻辑各自独立、可单独测试
embeddings = CachedEmbeddingClient(
    OpenAIEmbeddingClient(settings),
    settings.cache_dir / "embeddings-cache.json",
    model_tag=settings.tutor_embedding_model,
)
```

## 14.4 Agent 形态：为什么用 create_agent 而不是自定义图

第 4 章的选型表说过：**标准工具调用 Agent，用 `create_agent`；有明确分支/审批/长任务，才上自定义 StateGraph。** 教学助手就是前者——"检索 → 回答"的标准循环，没有审批也没有复杂分支，所以：

```python
create_agent(
    model=model,
    tools=[search_tutorial, get_outline],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=InMemorySaver(),   # thread_id 隔离多轮会话（第 6 章）
)
```

两个工具的设计也有讲究：

- `search_tutorial` 的 docstring 明确写了"回答任何教程内容问题前必须先调用"——工具描述就是 Prompt 的一部分（第 3 章）。
- 工具返回 **JSON 字符串**而不是 Python 对象。这不是随手为之：LangChain 会把工具返回值转成字符串放进 `ToolMessage`，如果返回 Python 列表，得到的是 `str()` 的 repr（单引号），API 层就没法可靠解析。返回 `json.dumps(...)` 让下游有一个稳定的合同。

## 14.5 SSE 事件流：引用为什么不能信模型口述

`POST /api/chat` 返回五种 SSE 事件：

| 事件 | 含义 | 前端表现 |
|---|---|---|
| `tool_call` | 模型决定调用工具 | 状态行"正在查阅教程…" |
| `sources` | 检索命中的章节/小节 | 可点击的引用标签，跳转原文锚点 |
| `token` | 回答的增量文本 | 逐字渲染 |
| `final` | 本轮结束 | 清除状态行 |
| `error` | 超时/递归上限/未知错误 | 红色提示，不泄漏堆栈 |

最关键的设计决策：**`sources` 事件从 `search_tutorial` 的真实返回值里提取，而不是让模型在回答里自己报章节号。** 模型可能幻觉出"第 15 章"，但工具返回值是检索系统真实命中的块——引用的准确性不依赖模型的诚实。这是第 10 章"不要把安全性建立在模型自觉上"在产品体验上的应用。

实现上用 LangGraph 的多模式流（第 12 章讲过 `astream`）：

```python
async for mode, event in agent.astream(inputs, config, stream_mode=["updates", "messages"]):
    # messages 模式 → token 事件（AIMessageChunk 增量）
    # updates 模式 → tool_call 事件（AIMessage.tool_calls）
    #             → sources 事件（ToolMessage 的 JSON 返回值）
```

错误处理同样分层（第 10 章）：超时（`asyncio.timeout`）、递归上限（`GraphRecursionError`，防失控循环烧钱）、未知异常，各自翻译成对用户有意义的中文 `error` 事件；堆栈只进服务端日志。

## 14.6 测试策略：全套测试，0 次真实 API 调用

`tests/test_tutor_*.py` 展示了分层结构怎么换来可测试性：

| 层 | 测什么 | 怎么隔离网络 |
|---|---|---|
| ingest | 真实 docs/ 的加载、切块、锚点 | 本来就不需要网络 |
| rag | 检索命中、缓存跳过重复调用 | `FakeEmbeddingClient`（crc32 字符哈希，确定性向量） |
| agent | 工具 JSON 合同、"先调工具再回答"的循环 | `ScriptedChatModel`（脚本化回复的假模型） |
| api | SSE 事件顺序、404、无 Key 降级 | `FakeAgent`（预排的事件流） |

这延续了第 11 章的原则：**评测/测试不应该依赖被测系统之外的不确定性。** 假实现不是偷懒，而是把"我们的代码对不对"和"OpenAI 今天抽不抽风"分开验证。

## 14.7 刻意留下的生产化差距（练习）

tutor 是"生产级结构"，但离"生产级系统"还差几步——每一步都是练习：

1. **持久化会话**：`InMemorySaver` 重启即失。换成 `SqliteSaver`（第 5 章），验证重启后追问"刚才说到哪了"仍有上下文。
2. **输入护栏**：用第 10 章的方法加一层 middleware：拒绝注入模式、限制话题范围，先于模型执行。
3. **混合检索**：纯向量检索对"第 5 章讲了什么"这类元问题不友好。加 BM25 关键词通道并做分数融合（第 7 章进阶路线）。
4. **评测集**：写 20 条"问题 + 应命中章节 + 要点"的用例，用第 11 章的 LLM-as-judge 给回答打分，改 Prompt 前后对比。
5. **可观测性**：接入 LangSmith，观察每次检索的命中质量与 token 成本。

完成练习 1 和 4，你就拥有了一个可以放进简历的、有测试有评测的完整 Agent 项目。

## 小结

- 分层的价值不是"看起来专业"，而是**每层可单独替换、单独测试**；支撑它的是依赖注入和应用工厂。
- RAG 的选型跟着规模走：300 块用 numpy 足够，但 Embedding 缓存这种成本控制在任何规模都值得做。
- 引用、安全、降级都遵循同一原则：**关键保证不建立在模型的自觉上**，而建立在系统结构上。
- Demo 与生产的差距不是代码量，而是：状态在哪里？失败如何恢复？怎么知道它做对了？——现在你可以用 `tutor/` 逐条回答这三个问题了。

# 设计文档：AI Agent 教程教学助手（tutor）

- 日期：2026-07-17
- 状态：已获用户确认
- 定位：本仓库的最终实战案例——一个生产级分层结构的"教 AI Agent 的 Agent"，同时把教程本身变成可浏览的前端站点。

## 1. 目标与非目标

### 目标

1. 提供一个教程阅读站点：左侧章节目录，中间渲染 `docs/*.md` 正文（含配图），右下角悬浮聊天助手；
2. 聊天助手是一个真实 LLM 驱动的教学 Agent：基于教程内容做 RAG 问答，回答必须带章节引用；引用可点击，点击后阅读区跳转到对应章节（章节导航能力）；
3. 代码采用生产级工程结构：分层（config / ingest / rag / agent / api / web）、依赖注入、应用工厂、协议接口、结构化错误处理、全链路可测试；
4. 全部测试无需 API Key 与网络，延续仓库传统。

### 非目标（YAGNI，明确不做）

- 不做测验、学习进度记忆、Demo 代码解读工具（用户已裁剪，只保留 RAG 问答 + 章节导航）；
- 不引入 Node 构建链、前端框架、向量数据库、外部消息队列；
- 不做认证、多租户、持久化 checkpointer（列入 README"生产化差距"清单，作为教学内容）；
- 不改动现有 demos/ 与 docs/00–13 的内容结构。

## 2. 技术选型（已确认）

| 决策点 | 选择 | 理由 |
|---|---|---|
| LLM 依赖 | 必须配置真实模型（OpenAI 兼容） | 用户明确选择；最终实战案例应接真实模型 |
| 编排层 | LangChain `create_agent`（方案 A） | 标准工具调用 Agent 形状，遵循教程自身第 4/README 的选型建议；底层即 LangGraph，checkpointer/流式/步数限制全可用 |
| 检索层 | OpenAI Embeddings + numpy 余弦 Top-K，内容哈希磁盘缓存 | 真实语义检索；无重依赖；重启零成本 |
| 前端 | 无构建工具的原生 HTML/CSS/JS，由 FastAPI 托管 | 用户明确选择；初学者一条命令可运行 |
| Markdown 渲染 | 服务端 Python `markdown` 库渲染为 HTML | 阅读功能不依赖外网 CDN |
| 位置 | 顶层 `tutor/` 包，与 demos/ 平级 | 用户明确选择；强调独立生产级应用定位 |
| 新增依赖 | `pydantic-settings`、`markdown`、`numpy` | 均为轻量常规库 |

## 3. 目录结构

```text
tutor/
├── __init__.py
├── README.md            # 架构说明、运行方式、生产化差距清单
├── config.py            # Settings（pydantic-settings）
├── ingest/
│   ├── __init__.py
│   ├── loader.py        # 扫描 docs/*.md → Chapter 列表
│   └── chunker.py       # 章节 → 带元数据的 Chunk 列表
├── rag/
│   ├── __init__.py
│   ├── embeddings.py    # EmbeddingClient 协议、OpenAIEmbeddingClient、DiskCache
│   ├── index.py         # VectorIndex：向量存取 + 余弦 Top-K
│   └── retriever.py     # Retriever：query → list[Hit]
├── agent/
│   ├── __init__.py
│   ├── prompts.py       # SYSTEM_PROMPT
│   ├── tools.py         # search_tutorial / get_outline 工具工厂
│   └── graph.py         # build_agent(settings, retriever, model=None)
├── api/
│   ├── __init__.py
│   ├── schemas.py       # ChatRequest、ChapterSummary、SSE 事件模型
│   ├── routes.py        # /api/health /api/chapters /api/chapters/{id} /api/chat
│   └── app.py           # create_app() 工厂 + lifespan 装配
└── web/
    ├── index.html
    ├── style.css
    └── app.js
tests/
├── test_tutor_ingest.py
├── test_tutor_rag.py
├── test_tutor_agent.py
└── test_tutor_api.py
docs/14-teaching-agent.md   # 新章节：讲解本项目
var/                        # 运行时产物（embedding 缓存），加入 .gitignore
```

## 4. 组件契约

### 4.1 config.py

```python
class Settings(BaseSettings):
    openai_api_key: str = ""            # 空 = 聊天功能降级
    openai_base_url: str | None = None
    openai_model: str = "gpt-5.6"
    embedding_model: str = "text-embedding-3-small"   # env: TUTOR_EMBEDDING_MODEL
    docs_dir: Path = Path("docs")
    assets_dir: Path = Path("assets")
    cache_dir: Path = Path("var")
    top_k: int = 4
    max_message_length: int = 2000
    agent_recursion_limit: int = 10
    request_timeout_seconds: float = 60.0
```

读取 `.env`（沿用现有变量名 `OPENAI_*`，tutor 特有项用 `TUTOR_` 前缀）。所有组件构造时接收 `Settings`，不直接读环境变量。

### 4.2 ingest

- `Chapter`：`id`（如 `"05"`，附录为 `"setup"/"glossary"/"reading-list"/"references"`）、`title`、`path`、`markdown`；
- `loader.load_chapters(docs_dir) -> list[Chapter]`：按文件名排序；排除 `superpowers/` 子目录；
- `Chunk`：`chapter_id`、`chapter_title`、`heading`、`anchor`（heading 的 slug）、`text`；
- `chunker.split_chapter(chapter) -> list[Chunk]`：按 `##` 二级标题切块；标题前的引言归入第一块；单块超过约 1200 字符时按段落再切。

### 4.3 rag

- `EmbeddingClient`（Protocol）：`embed(texts: list[str]) -> list[list[float]]`；
- `OpenAIEmbeddingClient`：批量调用 embeddings API；磁盘缓存键为 `sha256(model + text)`，存 `var/embeddings-cache.json`，只有缓存未命中的文本才发请求；
- `VectorIndex`：持有 `numpy.ndarray` 与并行的 `list[Chunk]`；`search(vector, top_k) -> list[tuple[Chunk, float]]`（余弦相似度）；
- `Retriever.search(query: str, top_k: int) -> list[Hit]`，`Hit = {chunk, score}`；这是 agent 层可见的唯一检索接口。

### 4.4 agent

- `tools.make_tools(retriever, chapters) -> list[BaseTool]`：
  - `search_tutorial(query: str) -> list[dict]`：返回 `{chapter_id, chapter_title, heading, anchor, text, score}`；描述中写明"回答任何教程内容问题前必须调用"；
  - `get_outline() -> list[dict]`：返回 `{chapter_id, title}` 全列表；用于"该先学什么/教程有哪些内容"类问题；
- `graph.build_agent(settings, retriever, chapters, model=None)`：`model` 参数允许测试注入假模型；默认 `ChatOpenAI(model=settings.openai_model, api_key=..., base_url=...)`；`create_agent(model, tools, system_prompt=SYSTEM_PROMPT, checkpointer=InMemorySaver())`；
- System prompt 硬规则：只基于 `search_tutorial` 返回的内容回答教程问题；每个关键结论标注（第 X 章）；检索不到就承认并建议查阅附录 C；不回答与本教程无关的话题，礼貌拉回。

### 4.5 api

- `GET /api/health`：`{"status": "ok", "chat_enabled": bool}`；
- `GET /api/chapters`：`[{id, title}]`；
- `GET /api/chapters/{id}`：`{id, title, html}`；服务端渲染 Markdown（扩展：tables、fenced_code、toc 以生成锚点 id）；正文中 `../assets/` 与 `assets/` 相对路径改写为 `/assets/`；`docs/xx.md` 相对链接改写为 `#/chapter/xx` 前端路由；未知 id 返回 404；
- `POST /api/chat`（SSE）：请求 `{thread_id: str, message: str}`；事件序列：
  - `tool_call`：`{"tool": "...", "input_summary": "..."}`
  - `sources`：`[{chapter_id, chapter_title, heading, anchor}]` —— 从 `search_tutorial` 的真实返回值去重提取，不取自模型文本；
  - `token`：`{"delta": "..."}` —— 来自 `astream(stream_mode=["updates", "messages"])` 的消息增量；
  - `final`：`{"ok": true}`
  - `error`：`{"message": "用户可读文案"}`
- 未配置 API Key 时 `/api/chat` 返回 503 + 配置指引文案；阅读接口不受影响；
- 输入护栏：`message` 长度 1–2000；`thread_id` 匹配 `^[a-zA-Z0-9_-]{1,64}$`；
- 整次运行包 `asyncio.timeout(settings.request_timeout_seconds)`；客户端断开时取消任务；
- 异常统一捕获：细节进日志（`logging`），对外只发 `error` 事件或标准 HTTP 错误。
- 静态托管：`/` → `tutor/web/index.html`；`/assets/*` → 仓库 `assets/`；lifespan 中完成：加载章节 → 切块 → 建索引 → 构造 agent，存入 `app.state`。

### 4.6 web

- 布局：左侧固定章节目录（含附录），中间正文滚动区，右下角聊天气泡按钮展开聊天面板；
- 路由：`location.hash = #/chapter/05`，刷新可直达；
- 聊天：`fetch('/api/chat', {method: 'POST'})` + `ReadableStream` 手工解析 SSE；`thread_id` 用 `crypto.randomUUID()` 生成后存 `localStorage`；
- 事件呈现：`tool_call` → "正在查阅教程…"状态行；`token` → 增量渲染；`sources` → 回答下方的章节标签，点击调用阅读区跳转（切换 hash + 滚动到 anchor）；`error` → 红色提示；503 → 显示配置指引；
- 样式：简洁现代（系统字体、浅色主题、卡片式聊天气泡），零外部资源。

## 5. 数据流

```text
启动：docs/*.md → load_chapters → split_chapter → embed（磁盘缓存）→ VectorIndex → build_agent → app.state

问答：浏览器 POST /api/chat
  → 护栏校验 → agent.astream({messages}, config={thread_id, recursion_limit})
  → 模型决定调用 search_tutorial → 检索命中块 → observation 回模型
  → SSE: tool_call → sources → token* → final
  → 前端渲染回答与可点击引用
```

## 6. 错误处理矩阵

| 场景 | 行为 |
|---|---|
| 未配置 API Key | 站点可用，聊天 503 + 指引；`/api/health` 报 `chat_enabled: false` |
| 启动时 embedding 调用失败 | 记录日志，聊天降级为 503（原因：索引不可用），阅读不受影响 |
| 运行中 LLM 超时/失败 | SSE `error` 事件，用户可读文案，日志留详情 |
| 达到 recursion_limit | 捕获 GraphRecursionError → SSE `error`："问题太复杂，请拆开问" |
| 客户端断开 | 取消 agent 任务，释放资源 |
| 非法输入 | 422（Pydantic）或 400，不进入 agent |

## 7. 测试策略（无需 API Key）

- `FakeEmbeddingClient`：基于字符 n-gram 哈希的确定性向量，保证"相同词汇的文本相似度高"；
- ingest：章节数量、附录识别、切块元数据（chapter_id/anchor）、长块再切；
- rag：中文查询命中预期章节块；缓存命中不重复调用（用计数的 fake 验证）；
- agent：`GenericFakeChatModel` 脚本化"先调工具再回答"，验证工具接线、observation 往返、系统提示注入；
- api：`create_app(settings, agent=fake, ...)` 注入假部件；`httpx.AsyncClient(transport=ASGITransport(...))` 测四个端点；SSE 事件顺序断言（tool_call → sources → token → final）；503 降级路径；
- 全部并入 `uv run pytest`。

## 8. 文档与仓库接线

- `docs/14-teaching-agent.md`：为什么选 create_agent（对照第 4.5 节升级标准）、分层与依赖注入讲解、SSE 事件设计、生产化差距清单、练习（换 SQLite checkpointer、加 BM25 混合检索、加输入护栏中间件）；
- `tutor/README.md`：快速运行 + 架构图 + 与 demos 的对照表；
- 主 `README.md`：学习路线表加"14｜最终实战：教学 Agent 站点"一行；"5 分钟跑起来"加 `make tutor`；
- `Makefile`：`tutor: uv run uvicorn tutor.api.app:app --reload`（app 为模块级工厂产物）；
- `.gitignore`：加 `var/`；
- `pyproject.toml`：新增三个依赖。

## 9. 实施顺序（供 writing-plans 展开）

1. 依赖与脚手架（pyproject、目录、Settings）；
2. ingest（loader + chunker）+ 测试；
3. rag（embeddings 缓存 + index + retriever）+ 测试；
4. agent（prompts + tools + graph）+ 测试；
5. api（schemas + routes + app 工厂）+ 测试；
6. web 前端三件套；
7. 文档接线（docs/14、README、Makefile）；
8. 端到端人工验证（含真实 Key 冒烟测试由用户执行）。

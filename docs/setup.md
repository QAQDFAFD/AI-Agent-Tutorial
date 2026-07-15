# 附录 A｜环境准备：15 分钟把项目跑起来

本教程的大部分 Demo 都**不需要 API Key**，可以完全离线运行。本页帮你搭好环境、跑通第一个 Demo，并解决最常见的报错。

## A.1 需要什么

| 项目 | 要求 | 检查命令 |
|---|---|---|
| 操作系统 | macOS / Linux / Windows（WSL 或 PowerShell 均可） | — |
| Python | 3.11 或更高 | `python3 --version` |
| uv（推荐） | 任意近期版本 | `uv --version` |
| API Key（可选） | 仅 Demo 02（联网模式）和 Demo 03 需要 | — |

> **uv 是什么？** 一个更快的 Python 包与虚拟环境管理器，一条 `uv sync` 命令就能创建虚拟环境并安装所有依赖。不想用它也可以用传统的 `venv + pip`，见 A.3。

安装 uv：

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## A.2 三步跑通

```bash
# 1. 复制环境变量模板（暂时不用填任何内容）
cp .env.example .env

# 2. 安装依赖（自动创建 .venv 虚拟环境）
uv sync

# 3. 运行第一个 Demo：手写 Agent Loop，不需要任何密钥
uv run python -m demos.01_agent_loop.main
```

看到类似下面的输出就说明环境正常：

```text
用户：北京天气怎么样？
Agent：已根据 get_weather 的结果回答：{'status': 'ok', 'city': '北京', 'weather': '雷阵雨，31℃'}
Trace：[{'step': 1, 'event': 'tool_call', 'tool': 'get_weather', 'ok': True, ...}]
```

再跑一遍测试，确认所有离线 Demo 都可用：

```bash
uv run pytest
```

## A.3 不用 uv 的替代方式

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e . --group dev     # pip 25.1+ 支持 --group；否则手动安装 pyproject 中的依赖
python -m demos.01_agent_loop.main
```

## A.4 配置 API Key（可选）

只有两个 Demo 需要真实模型：

- `demos/02_openai_structured`（不配 Key 会自动退化为本地规则演示）
- `demos/03_langchain_agent`（必须有 Key）

编辑 `.env`：

```bash
OPENAI_API_KEY=sk-你的密钥
OPENAI_MODEL=gpt-5.6
```

### 使用 OpenAI 兼容服务（国内模型 / 代理）

许多服务（DeepSeek、Qwen、Kimi、各类中转站等）提供 OpenAI 兼容接口。只需额外设置 base URL：

```bash
# .env 中增加
OPENAI_BASE_URL=https://api.deepseek.com     # 换成你的服务地址
OPENAI_API_KEY=你的密钥
OPENAI_MODEL=deepseek-chat                   # 换成该服务支持工具调用的模型名
```

官方 OpenAI SDK 和 `langchain-openai` 都会自动读取 `OPENAI_BASE_URL`。注意两点：

1. 模型必须**支持工具调用（function calling）**，否则 Demo 03 会失败；
2. 部分兼容服务未实现 Responses API，只实现了 Chat Completions。遇到 404 时，说明该服务不支持 `client.responses.*`，可以先跳过联网 Demo，离线 Demo 不受影响。

## A.5 常见报错速查

| 报错 | 原因 | 解决 |
|---|---|---|
| `ModuleNotFoundError: No module named 'demos'` | 没有从项目根目录运行 | `cd` 到项目根目录，用 `python -m demos.xx.main` 形式运行 |
| `ModuleNotFoundError: No module named 'langgraph'` | 依赖没装 / 没用虚拟环境 | `uv sync`，并确保命令带 `uv run` 前缀 |
| `RuntimeError: 请先复制 .env.example 为 .env ...` | Demo 03 需要 API Key | 按 A.4 配置，或先学习离线 Demo |
| `AuthenticationError: 401` | Key 错误或过期 | 检查 `.env` 中的 `OPENAI_API_KEY` 是否完整、有余额 |
| `NotFoundError: 404`（联网 Demo） | 模型名不存在，或兼容服务不支持 Responses API | 换 `OPENAI_MODEL`，或参考 A.4 第 2 条 |
| `RateLimitError: 429` | 触发限流 | 稍后重试；这正是第 10 章讲退避重试的原因 |
| Windows 下中文乱码 | 终端编码不是 UTF-8 | PowerShell 执行 `chcp 65001`，或使用 Windows Terminal |

## A.6 推荐的学习工具链

- **编辑器**：VS Code / Cursor / PyCharm 都可以，装好 Python 插件即可；
- **调试**：在节点函数里打断点单步观察 state，比打印日志更直观；
- **画图**：本教程的所有图都是 [Mermaid](https://mermaid.js.org/) 文本（见 `assets/diagrams/*.mmd`），改完源码可用 `npx @mermaid-js/mermaid-cli -i xx.mmd -o xx.svg` 重新导出。

准备好之后，从[第 00 章：全景地图](00-learning-map.md)开始。

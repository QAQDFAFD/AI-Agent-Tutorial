# 附录 C｜精读文选：塑造了 Agent 领域的论文与文章（2022–2026）

[参考资料](references.md)收录的是"写代码时查 API"的官方文档；这一页不同，收录的是**塑造了这个领域的思想**——从 2022 年 ReAct 让模型学会"边想边做"，到 2024 年 Anthropic 提出"大多数场景不需要复杂 Agent"，再到 2025 年上下文工程成为共识。读它们不是为了追热点，而是理解每个设计决策背后"当时的人在解决什么问题"。

每篇都标注了建议阅读时机（对应本教程章节）。论文不必逐字精读：先读摘要和图，再读实验结论，够用了。

## C.1 如果只读五篇

| # | 文章 | 一句话理由 |
|---|---|---|
| 1 | [LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)（Lilian Weng, 2023.06） | 最早把"规划 + 记忆 + 工具"总结成 Agent 标准框架的文章，本教程的章节划分与它一脉相承 |
| 2 | [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)（Anthropic, 2024.12） | "先用 Workflow，确有必要再上 Agent"——过去几年最重要的工程降温剂 |
| 3 | [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)（Yao et al., 2022.10） | 几乎所有工具调用 Agent 的理论源头，读完就理解 Demo 01 为什么长那样 |
| 4 | [A Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)（OpenAI, 2025） | 34 页 PDF，从选型、工具设计到护栏的完整工程清单，适合读完教程后对照自查 |
| 5 | [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)（Anthropic, 2025.09） | 把"上下文是稀缺资源"讲透的文章："找到最小的高信号 Token 集合" |

## C.2 奠基论文（2022–2023）：Agent 的三块基石

**推理**、**行动**、**反思**——今天所有框架的花样，基本都是这三件事的组合。

- **[Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903)**（Wei et al., 2022.01）
  发现"让模型一步步想"能显著提升推理能力。这是后来一切"规划"能力的起点，也解释了为什么今天的推理模型要花 Token"思考"。→ 配合第 01 章。

- **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)**（Yao et al., 2022.10）
  提出推理（Reason）与行动（Act）交替进行：想一步、查一步、根据结果再想。第 1.3 节的 ReAct 模式和 Demo 01 的循环骨架就是它的直接后代。→ 配合第 01 章。

- **[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)**（Schick et al., 2023.02）
  证明模型可以学会"在恰当位置调用 API"。虽然如今的工具调用走的是另一条技术路线（提供 schema 而不是训练），但"模型 + 工具 > 模型"这个判断由它奠定。→ 配合第 03 章。

- **[Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)**（Shinn et al., 2023.03）
  让 Agent 用自然语言总结上次失败、下次改进。Demo 04 的"质量检查 → 重写"循环就是它的最简版。→ 配合第 05 章。

- **[Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)**（Park et al., 2023.04）
  著名的"AI 小镇"：25 个 Agent 在虚拟小镇里生活、社交、办派对。它的真正贡献是**记忆流架构**——记忆按新近度、重要性、相关性检索，第 06 章的记忆分层思想与此同源。→ 配合第 06 章。

- **[Voyager: An Open-Ended Embodied Agent with Large Language Models](https://arxiv.org/abs/2305.16291)**（Wang et al., 2023.05）
  在 Minecraft 里持续学习的 Agent，首创"技能库"：把学会的能力存成代码供日后复用。今天 Agent 的 Skill 机制可以追溯到这里。→ 配合第 06 章。

- **[Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://arxiv.org/abs/2305.10601)**（Yao et al., 2023.05）
  把线性思维链扩展成可回溯的搜索树。工程上很少直接使用，但它标志着"用程序结构增强模型推理"这一思路的成熟。→ 选读。

- **[A Survey on Large Language Model based Autonomous Agents](https://arxiv.org/abs/2308.11432)**（Wang et al., 2023.08，持续更新）
  想系统盘点 2023 年前后所有 Agent 工作的话，从这篇综述入手。→ 选读。

- **[AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](https://arxiv.org/abs/2308.08155)**（Wu et al., 2023.08）
  微软的多 Agent 对话框架论文，多 Agent 热潮的学术起点之一。读它，再对照 C.4 里 Cognition 的反方观点，很有意思。→ 配合第 08 章。

## C.3 从模型到系统（2024）：热潮退去后的冷思考

- **[The Shift from Models to Compound AI Systems](https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/)**（Berkeley BAIR, 2024.02）
  提出"最好的结果越来越多来自组合系统而非单一模型"。本教程"模型只是组件之一"的立场即源于此。→ 配合第 00 章。

- **[Executable Code Actions Elicit Better LLM Agents](https://arxiv.org/abs/2402.01030)**（Wang et al., 2024.02）
  与其定义几十个工具，不如让 Agent 直接写代码执行动作（CodeAct）。今天编程类 Agent 的主流形态由此确立——当然，代价是必须有沙箱隔离（见第 10 章）。→ 配合第 03 章。

- **[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)**（Anthropic, 2024.12）
  必读。清晰区分 Workflow（代码定路径）与 Agent（模型定路径），并给出五种常用 Workflow 模式，最后忠告："找最简单的方案，只在确有必要时增加复杂度。"本教程第 01 章的形态对比表就是对它的展开。→ 配合第 01、05 章。

- **[Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)**（Anthropic, 2024.11）
  MCP 发布公告。一年多时间里它从一家之言变成行业事实标准，读原始公告能理解它想解决的"M×N 集成"问题。规范本身见 [modelcontextprotocol.io](https://modelcontextprotocol.io/)。→ 配合第 09 章。

## C.4 工程实践与路线之争（2025–2026）

这一时期的特点：论文变少、工程复盘变多；争论焦点从"能不能"变成"值不值"。

- **[Agents](https://huyenchip.com/2025/01/07/agents.html)**（Chip Huyen, 2025.01）
  《AI Engineering》作者的长文，把规划、工具、失败模式和评测讲得非常系统，可以当第 00 章的英文姊妹篇。→ 配合第 00、11 章。

- **[A Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)**（OpenAI, 2025）
  单 Agent 优先、护栏分层、人工介入时机——与本教程第 10 章高度互补的官方工程指南。→ 配合第 10 章。

- **[12-Factor Agents](https://github.com/humanlayer/12-factor-agents)**（Dex Horthy / HumanLayer, 2025）
  仿照"12-Factor App"提出的 Agent 可靠性原则："拥有你自己的控制流""把工具当结构化输出""小而聚焦的 Agent"。适合读完第 12 章后对照检查自己的设计。→ 配合第 12 章。

- **[Don't Build Multi-Agents](https://cognition.ai/blog/dont-build-multi-agents)**（Walden Yan / Cognition, 2025.06）
  Devin 团队的反方观点：并行子 Agent 各自决策会互相冲突，上下文完整性比"分工"更重要。→ 配合第 08 章，与下一篇对照读。

- **[How We Built Our Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)**（Anthropic, 2025.06）
  正方案例：广度优先的研究任务中，主管 + 并行子 Agent 比单 Agent 提升 90%，但 Token 消耗约 15 倍。两篇放在一起读，结论正是第 08 章开头那句话：**任务形状决定架构，分工不是越多越好**。→ 配合第 08 章。

- **[Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)**（Anthropic, 2025.09）
  宣告"提示工程"升级为"上下文工程"：上下文是有限的注意力预算，核心手段是压缩（compaction）、结构化笔记和按需检索。第 6.5 节的预算思维与它同源。→ 配合第 06 章。

- **[Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models](https://arxiv.org/abs/2510.04618)**（Zhang et al., 2025.10）
  学术界对上下文工程的回应：把上下文当成可增量演化的"策略手册"，指出反复改写摘要会造成"上下文塌缩"（细节被磨掉）。→ 选读，配合第 06 章。

- **[Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)**（Anthropic, 2025）
  当任务从几分钟变成几小时甚至几天，重心从 Prompt 转向"运行时骨架"：计划、检查点、产物文件和恢复机制。与第 05 章 checkpoint、第 12 章长任务的内容互相印证。→ 配合第 12 章。

- **[A2A Protocol](https://a2a-protocol.org/)**（Google 发起, 2025）
  Agent 与 Agent 之间互操作的开放协议（MCP 解决"Agent 用工具"，A2A 解决"Agent 找 Agent"）。生态尚在演化，了解定位即可。→ 选读，配合第 09 章。

## C.5 安全：一直没被真正解决的问题

- **[Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection](https://arxiv.org/abs/2302.12173)**（Greshake et al., 2023.02）
  首次系统提出**间接**提示注入：恶意指令不来自用户，而是藏在 Agent 检索的网页、邮件、文档里。第 3.5 和 10.3 节的威胁模型直接来自这篇。→ 配合第 10 章。

- **[Prompt Injection 系列](https://simonwillison.net/series/prompt-injection/)**（Simon Willison, 2022 至今）
  从 2022 年造出"提示注入"这个词开始持续追踪的系列博客。风格通俗，例子全部来自真实产品事故。→ 配合第 10 章。

- **[The Lethal Trifecta for AI Agents](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/)**（Simon Willison, 2025.06）
  致命三要素：**能读私有数据 + 会接触不可信内容 + 能对外通信**，三者同时具备的 Agent 必然可被用来窃取数据。做任何工具授权设计前，先用它检查一遍。→ 配合第 03、10 章。

- **[OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)**（OWASP, 2023 起持续更新）
  安全行业对 LLM 应用风险的标准清单，提示注入常年排第一。适合做第 10 章上线检查表的扩展参照。→ 配合第 10 章。

## C.6 评测：怎么知道 Agent 真的变好了

- **[Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)**（Zheng et al., 2023.06）
  系统研究"用模型给模型打分"的可行性与偏差（位置偏差、冗长偏差、自我偏爱）。第 11.4 节说 LLM-as-judge 需要校准，依据就在这里。→ 配合第 11 章。

- **[SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770)**（Jimenez et al., 2023.10）
  用真实 GitHub issue 做基准，几年来一直是编程 Agent 的"高考"。读它主要学一件事：**好的评测本身就是稀缺的工程产物**。→ 配合第 11 章。

- **[τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045)**（Yao et al. / Sierra, 2024.06）
  最贴近本教程综合项目的基准：客服 Agent 在多轮对话中调用工具并遵守领域规则，并提出 pass^k 指标衡量**稳定性**——同一任务跑 8 次都对才算真的会。→ 配合第 11、13 章。

## C.7 建议的阅读节奏

1. **学教程期间**：只读 C.1 的五篇，遇到对应章节时再回来按图索骥；
2. **做完综合项目后**：补 C.4 的路线之争（多 Agent 正反方、12-Factor）和 C.5 安全三篇；
3. **奠基论文**：当成历史读，重点看"当时在解决什么问题"，不必复现实验；
4. **保持更新**：这个领域半年一变。持续追踪的高信噪比来源：Anthropic/OpenAI/LangChain 的工程博客、Simon Willison 的博客、Lilian Weng 的 [lilianweng.github.io](https://lilianweng.github.io/)。

> 链接核对日期：2026-07-15。论文优先给 arXiv 摘要页（页面上可下载 PDF）；博客若失效，用标题搜索通常能找到镜像。

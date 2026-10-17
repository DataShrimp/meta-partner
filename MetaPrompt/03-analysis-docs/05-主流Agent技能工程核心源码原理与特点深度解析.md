# 主流 Agent 技能（Skill）工程核心源码原理与特点深度解析

> **文档定位**：本文档专门补齐上一轮「Agent Skill 最佳实践」调研中缺失的**源码级原理与工程特点深度剖析**，与 [《04-Agent-Skill构建最佳实践深度调研报告.md》](file:///Users/ryan/Workspace/MetaPrompt/03-analysis-docs/04-Agent-Skill%E6%9E%84%E5%BB%BA%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5%E6%B7%B1%E5%BA%A6%E8%B0%83%E7%A0%94%E6%8A%A5%E5%91%8A.md) 组成完整的「源码解析 + 最佳实践」双文档结构。

---

## 一、 核心源码工程全景与本地归档映射

当前主流 Agent Skill 工程已围绕 [Agent Skills 开放标准（`agentskills.io`）](https://agentskills.io/specification) 形成统一规范，但在**评估闭环、渐进式披露、动态上下文预处理、跨端元数据扩展与脚本执行沙箱**五个工程维度上各具代表性实现。本地已归档的核心源码如下：

| 工程名称 | 所属生态 / 机构 | 核心解决的工程问题 | 本地归档源码路径 | 官方源码 / 规范链接 |
| :--- | :--- | :--- | :--- | :--- |
| **Anthropic `skill-creator`** | Anthropic 官方元技能 | 技能全生命周期管理：双盲基线 A/B 评估、执行轨迹归因、60/40 路由触发率寻优 | [02-official-and-frameworks/anthropic-skill-creator/SKILL.md](file:///Users/ryan/Workspace/MetaPrompt/02-official-and-frameworks/anthropic-skill-creator/SKILL.md) | [anthropics/skills/skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) |
| **Anthropic `mcp-builder`** | Anthropic 官方开发技能 | 复杂工程任务的三级渐进式按需挂载（Phase-gated Loading）与内嵌 `<evaluation>` 验收对生成 | [02-official-and-frameworks/anthropic-mcp-builder/SKILL.md](file:///Users/ryan/Workspace/MetaPrompt/02-official-and-frameworks/anthropic-mcp-builder/SKILL.md) | [anthropics/skills/mcp-builder](https://github.com/anthropics/skills/blob/main/skills/mcp-builder/SKILL.md) |
| **Claude Code 动态注入与自记录技能** | Claude Code 官方运行时 | 运行前反引号命令注入（`` !`cmd` ``）消除首轮探测延迟；`/verify` 自记录技能 | [02-official-and-frameworks/anthropic-mcp-builder/SKILL.md](file:///Users/ryan/Workspace/MetaPrompt/02-official-and-frameworks/anthropic-mcp-builder/SKILL.md)（Part 2） | [Claude Code Skills Docs](https://code.claude.com/docs/en/skills) |
| **OpenAI Codex `openai.yaml` 与脚本规范** | OpenAI Codex & `agentskills.io` | 2% 上下文发现预算控制、`agents/openai.yaml` 策略与 MCP 依赖声明、PEP 723 自包含脚本 | [02-official-and-frameworks/anthropic-mcp-builder/SKILL.md](file:///Users/ryan/Workspace/MetaPrompt/02-official-and-frameworks/anthropic-mcp-builder/SKILL.md)（Part 3 & 4） | [OpenAI Build Skills](https://learn.chatgpt.com/docs/build-skills) / [Using Scripts](https://agentskills.io/skill-creation/using-scripts) |
| **`nidhinjs/prompt-master` & `affaan-m`** | 社区高分开源技能 | 零脚本纯 Markdown 技能的路由分发、本地工程画像探测与反问拦截机制 | [01-community-skills/nidhinjs-prompt-master/SKILL.md](file:///Users/ryan/Workspace/MetaPrompt/01-community-skills/nidhinjs-prompt-master/SKILL.md) | [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master) |

---

## 二、 逐项工程核心源码原理与技术特点剖析

### 2.1 Anthropic `skill-creator`：基于「软件测试回归框架」的元技能引擎

- **官方源码**：[anthropics/skills — `skills/skill-creator/SKILL.md`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
- **本地归档**：[02-official-and-frameworks/anthropic-skill-creator/SKILL.md](file:///Users/ryan/Workspace/MetaPrompt/02-official-and-frameworks/anthropic-skill-creator/SKILL.md)

#### （1）核心源码工作流原理
`skill-creator` 并非简单的「Markdown 模板生成器」，而是一套完整的 **Agent 行为回归测试与优化调度器（Orchestrator）**。其源码由四大核心环路构成：

1. **同一回合并行拉起对照沙箱（Parallel A/B Subagent Spawning）**：
   源码第 127–156 行明确规定：在评估技能时，严禁先跑完带技能组再跑基线组，必须在**同一个 Turn 内并行派发（Spawn in the same turn）**两个独立 Subagent：
   - **实验组（`with_skill`）**：挂载当前待测 `skill_path`；
   - **基线组（`without_skill` 或 `old_skill`）**：新建技能时完全不挂载技能；迭代已有技能时，先将旧版复制为快照目录（`<snapshot-dir>`），让基线组指向旧版快照，将结果分别写入 `<skill-name>-workspace/iteration-<N>/eval-<ID>/with_skill/` 与 `without_skill/`。
2. **硬性遥测与证据归因协议（`timing.json` + `grading.json` + `benchmark.json`）**：
   - 在 Subagent 完成瞬间，立即从任务通知（Task notification）捕获 `total_tokens` 和 `duration_ms` 写入 `timing.json`（因为该数据不会持久化在会话历史中）；
   - 派发 Grader Subagent（加载 `agents/grader.md`），不仅判断断言 `passed: true/false`，还强制提取支撑该判断的原始文本或文件证据字段 `evidence` 写入 `grading.json`；
   - 调用 `python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>` 聚合计算通过率均值与标准差（`pass_rate`）、耗时（`time_seconds`）和 Token 消耗差值（`delta`），并启动 `eval-viewer/generate_review.py` 生成可视化对比看板。
3. **执行轨迹反射与脚本提炼（Transcript-Driven Script Extraction）**：
   源码第 212–217 行设计了极具工程价值的「脚本固化探测机制」：阅读各测试轮次的执行轨迹（Execution Transcript），如果发现 3 个独立测试 case 的 Subagent 都各自手写了相似的辅助脚本（如 `create_docx.py` 或 `extract_chart.py`），则将该脚本提取并固化到技能包的 `scripts/` 目录下，后续直接调用，消除重复发明轮子的 Token 与时间开销。
4. **防过拟合的 Description 路由触发率寻优（`scripts.run_loop`）**：
   源码第 300–378 行专门针对 `description` 字段设计了分类器调优环路：构造 20 条边界测试查询（`should_trigger: true/false`，要求反例必须是包含相近词汇的 **Near-miss 高迷惑性样本**，严禁使用 `Write a fibonacci function` 这类毫无区分度的简单负例），由 `scripts.run_loop` 按 **60% 训练集（Train） / 40% 验证集（Validation）** 切分，每个 Query 重复运行 `--runs-per-query 3` 次以消除随机方差，调用 Extended Thinking（10,000 tokens 预算）改写 `description`，最终只采纳在 40% 验证集上得分最高的版本。

#### （2）核心设计特点与局限
- **最大亮点**：将「为什么而写（Why over heavy-handed MUSTs）」写入迭代准则——源码强调当技能指令解释清楚背后的工程原理（Theory of Mind）时，LLM 在面对未见过的长尾场景时远比死板堆砌全大写 `ALWAYS/NEVER` 更稳健。
- **工程局限**：强依赖支持并行 Subagent 派发与本地 Python 浏览器服务（`eval-viewer`）的重量级宿主环境，在单会话轻量化场景下运行成本较高（跑一轮需消耗数十次模型调用）。

---

### 2.2 Anthropic `mcp-builder`：三级渐进式披露与阶段门控加载（Phase-Gated Disclosure）

- **官方源码**：[anthropics/skills — `skills/mcp-builder/SKILL.md`](https://github.com/anthropics/skills/blob/main/skills/mcp-builder/SKILL.md)
- **本地归档**：[02-official-and-frameworks/anthropic-mcp-builder/SKILL.md](file:///Users/ryan/Workspace/MetaPrompt/02-official-and-frameworks/anthropic-mcp-builder/SKILL.md)

#### （1）核心源码工作流原理
如果把所有 Python FastMCP 规范、TypeScript SDK 规范、MCP 协议细节和评估指南全部塞进一个 `SKILL.md`，文件将超过 2,000 行，不仅挤爆上下文窗口，还会导致 Python 任务被 TypeScript 代码片段干扰。`mcp-builder/SKILL.md` 用仅 **236 行** 的主控文件完美展示了**阶段门控式三级渐进披露（Phase-Gated 3-Level Progressive Disclosure）**：

1. **主控路由层（`SKILL.md` 仅 236 行）**：只定义 4 个高内聚阶段（Phase 1 调研规划 → Phase 2 核心基础设施与工具实现 → Phase 3 编译与 `@modelcontextprotocol/inspector` 测试 → Phase 4 构造 10 道复杂只读 `<evaluation>` 题）。
2. **显式阶段挂载指令（Explicit Phase-Loading Triggers）**：
   在文末 `## Documentation Library` 中，源码没有笼统列出参考文档，而是为每个一级引用标注了**精确的加载时机**：
   - `Core MCP Documentation (Load First)` → `./reference/mcp_best_practices.md`
   - `Language-Specific Implementation Guides (Load During Phase 2)` → 按技术栈二选一加载 `./reference/python_mcp_server.md` 或 `./reference/node_mcp_server.md`
   - `Evaluation Guide (Load During Phase 4)` → 仅当代码编译通过进入第 4 阶段时才读取 `./reference/evaluation.md`
3. **工具行为语义注解（Tool Behavioral Annotations）**：
   在 Phase 2.3 中强制要求每个工具显式声明四元组语义注解：`readOnlyHint`（是否只读）、`destructiveHint`（是否具破坏性）、`idempotentHint`（是否幂等）、`openWorldHint`（是否访问外部开放网络），为宿主 Agent 的安全审批提供结构化契约。

---

### 2.3 Claude Code 原生技能引擎：动态上下文注入（`` !`command` ``）与自记录技能

- **官方文档**：[Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- **本地归档**：[02-official-and-frameworks/anthropic-mcp-builder/SKILL.md](file:///Users/ryan/Workspace/MetaPrompt/02-official-and-frameworks/anthropic-mcp-builder/SKILL.md)（Part 2）

#### （1）核心源码工作流原理
1. **预处理阶段的 Shell 反引号内联替换（`` !`command` `` Preprocessing）**：
   传统 Skill 被激活后，模型拿到静态的 `SKILL.md` 文本，往往需要花费第 1–2 个回合调用 `Bash` 或 `Read` 去获取 `git diff`、分支状态或 PR 评论。Claude Code 在技能加载器（Skill Loader）层实现了预处理宏：当 `SKILL.md` 中包含 `` !`gh pr diff` `` 时，宿主会在把提示词发送给 LLM **之前**先在本地执行该命令，并将标准输出直接内联替换到占位位置。模型在 Turn 1 看到的就是已经包含了完整 Diff 与上下文的成稿 Prompt，首轮探测延迟降为 0。
2. **子代理隔离执行模式（`context: fork` + `agent: Explore`）**：
   通过在 YAML Frontmatter 声明 `context: fork` 与 `agent: Explore`，技能不会污染当前主对话的上下文窗口，而是自动派生一个只读探索子代理执行重度检索任务，仅将最终提炼结论返回主会话。
3. **执行经验向技能的自举固化（Self-Recording Skills）**：
   以内置经验提取流为例，当 Agent 在当前仓库通过多轮试错摸索出正确的编译、迁移和验证命令序列后，会直接将该工作流写入 `.claude/skills/verify/SKILL.md`，实现「一次踩坑、永久固化为项目专属技能」。

---

### 2.4 OpenAI Codex `agents/openai.yaml` 与 `agentskills.io` 自包含脚本沙箱

- **官方文档**：[OpenAI Build Skills](https://learn.chatgpt.com/docs/build-skills) & [Agent Skills — Using Scripts](https://agentskills.io/skill-creation/using-scripts)
- **本地归档**：[02-official-and-frameworks/anthropic-mcp-builder/SKILL.md](file:///Users/ryan/Workspace/MetaPrompt/02-official-and-frameworks/anthropic-mcp-builder/SKILL.md)（Part 3 & 4）

#### （1）核心源码工作流原理
1. **双文件解耦架构（`SKILL.md` + `agents/openai.yaml`）**：
   为了保持 `SKILL.md` 的跨工具纯净性（仅保留 `name` 与 `description` 等核心字段），OpenAI 将平台特定的 UI 展示、隐式触发策略与外部 MCP 工具依赖剥离到同目录下的 `agents/openai.yaml`：
   - `policy.allow_implicit_invocation: false`：允许针对高危或低频技能关闭「模型自动猜测触发」，仅允许用户通过 `/skill-name` 显式调用；
   - `dependencies.tools`：声明该技能依赖的 MCP Server（如 `git`、`postgres`），宿主在激活技能前自动检查或挂载对应工具。
2. **PEP 723 单文件内联依赖与非交互式 CLI 契约**：
   在 [Agent Skills 脚本规范](https://agentskills.io/skill-creation/using-scripts) 中，针对 Agent 在无状态沙箱中运行脚本常遇到的三大痛点（缺依赖、卡死在交互式 `input()`、输出超长被截断），源码确立了四条硬性工程铁律：
   - **PEP 723 零配置依赖声明**：在 Python 脚本顶部使用 `# /// script` 块内联声明 `dependencies = ["pydantic>=2.0"]`，通过 `uv run scripts/tool.py` 自动在隔离缓存环境中运行，无需污染全局环境；
   - **严禁交互式 TTY 阻塞**：Agent 运行在非交互式 Shell 中，任何 `input()` 或 `[y/N]` 确认都会导致进程永久挂起，必须全部改为显式 CLI 参数（如 `--confirm`、`--dry-run`）；
   - **标准流职责分离**：结构化机器可读结果（JSON/CSV）输出至 `stdout`，报错诊断与修复建议输出至 `stderr`，并返回明确的退出码（`0` 成功，非 `0` 失败）；
   - **防截断分页与落盘（`--offset` / `--output`）**：宿主通常会在 10K–30K 字符处截断工具输出，因此脚本源码内置 `--max-chars` 或 `--output` 参数，避免大数据量撑爆上下文。

---

## 三、 五大主流 Skill 工程核心机制横向对比矩阵

| 对比维度 | Anthropic `skill-creator` | Anthropic `mcp-builder` | Claude Code 原生 Skill | OpenAI Codex Skill | 社区 `prompt-master` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **核心抽象层** | 元技能（编译与评测其他技能的调度器） | 复杂工程研发 SOP 技能 | 宿主增强型动态工作流技能 | 跨环境标准化技能包 + YAML 策略边车 | 零依赖纯 Markdown 路由技能 |
| **上下文省流机制** | Subagent 独立会话隔离评测 + `agents/*.md` 按角色加载 | 236 行主文件 + 阶段门控按需读取 `./reference/*.md` | `` !`cmd` `` 预处理 + `context: fork` 子会话剥离 | 启动仅注入 `<2%` 窗口的 `name/description` 索引 | 按任务类型按需读取 `references/patterns.md` |
| **确定性保障手段** | 自动检测重复脚本并沉淀至 `scripts/` + JSON Schema 校验 | 强制 Zod/Pydantic 输入输出 Schema + 工具四元组注解 | `allowed-tools` 白名单收敛（如 `Bash(gh *)`） | `agents/openai.yaml` 声明 MCP 依赖 + PEP 723 脚本 | 首因效应（前 30% 硬约束）+ 禁词表 |
| **评估与自演进闭环** | 双盲 A/B 对照 + `grading.json` 证据链 + 60/40 路由寻优 | Phase 4 强制生成 10 道独立只读可验证 XML `<qa_pair>` | `/verify` 从成功轨迹自动提炼保存新技能 | 依赖外部评测脚本或人工回归 | 无内置评测闭环（静态规则库） |

---

## 四、 对我们构建「自演进元提示词与角色技能」的核心源码启示

1. **吸收 `mcp-builder` 的「阶段门控加载（Phase-Gated Reference Loading）」**：将庞杂的平台适配规则（OpenClaw、Hermes、Claude Code、Codex）与评估量表抽离到 `references/` 子目录，并在主 `SKILL.md` 中明确标注 `Load ONLY in Phase X`，保证主文件始终轻快高信噪比。
2. **吸收 `skill-creator` 的「轨迹驱动固化」与「Near-Miss 路由防撞车」**：在生成任何 Skill 或 Subagent Role 时，强制同时编写正向触发场景与易混淆负向边界（`Do NOT use when...`），并提供轻量级单会话 Scorecard 与双盲 A/B 回归两条评测路径。
3. **吸收 Claude Code 与 `agentskills.io` 的「预处理感知 + 确定性校验」**：先探测本地仓库真实环境（技术栈、已有 `CLAUDE.md`/`AGENTS.md`/`SOUL.md`），再执行零占位符编译，杜绝空中楼阁式的通用模板。

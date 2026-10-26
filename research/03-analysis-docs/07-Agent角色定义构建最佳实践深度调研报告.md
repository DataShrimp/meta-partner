# Agent 角色定义（Role / Persona）构建最佳实践深度调研报告

> **核心结论**：Agent 的角色定义（Role Definition）在底层本质上就是**「带有宿主运行契约与生命周期分层的系统提示词（System Prompt）」**。从早期的单句 `"You are an expert software engineer"`，演进到如今 OpenClaw 的 7 文件认知分离、Hermes Agent 的 `SOUL.md` 行为契约、Claude Code 的 `.claude/agents/` 隔离沙箱，以及 Linux Foundation 旗下的 `AGENTS.md` 开放标准，角色定义已经形成了一套严密的**「认知分层、行为契约化、软硬边界协同、跨端适配与持续评估演进」**工程方法论。

---

## 一、 认知演进：为什么「Prompt → Skill → Agent Role」是同一事物的三层演进？

结合我们前两轮对 **Prompt（提示词）** 与 **Skill（技能）** 的调研，可以把三者的架构关系收敛为一个清晰的**同心圆模型**：

| 演进层级 | 核心关注点 | 生命周期与加载机制 | 典型文件载体 | 核心局限 / 为何需要下一层 |
| :--- | :--- | :--- | :--- | :--- |
| **Layer 1: Prompt（单次提示词）** | **How to execute a single task**（单次任务的上下文、约束与输出格式） | 单轮对话有效，即时消费 | 聊天输入框、API `user/system` 消息 | 无法跨会话自动复用，每次需手动拼装上下文 |
| **Layer 2: Skill（模块化技能包）** | **How to execute a domain SOP**（特定领域的标准作业程序、参考文档与确定性脚本） | 平时仅加载约 100 tokens 的 `name + description`；命中意图时按需挂载正文 | `.claude/skills/<name>/SKILL.md` + `scripts/` + `references/` | 技能只管「做事的方法」，不管「Agent 是谁、拥有什么工具权限、跑在什么隔离沙箱、如何维护长期记忆」 |
| **Layer 3: Agent Role（角色定义）** | **Who to be + Operational Constitution + Sandbox Contract**（常驻人格、全局红线、工具白名单、模型路由与记忆治理） | 会话启动时常驻注入系统提示词前缀（Slot #1），并直接控制宿主的工具/沙箱/模型配置 | OpenClaw `SOUL.md` + `AGENTS.md`、Hermes `SOUL.md`、Claude `.claude/agents/<role>.md` | 需要精细控制 Token 水位线，防止常驻提示词膨胀成「泥球（Ball of Mud）」 |

---

## 二、 Agent 角色定义构建的 7 大核心工程最佳实践

### 实践 1：用「三维行为契约（Behavior Spec）」彻底取代「性格形容词列表（Trait List）」
- **源码实证**：[NousResearch/hermes-agent `prompt_builder.py`](https://github.com/NousResearch/hermes-agent/blob/main/agent/prompt_builder.py) 与 [Hermes `SOUL.md` 指南](https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes)
- **反模式（Anti-Pattern）**：在角色文件开头堆砌 `"You are a helpful, intelligent, meticulous, friendly, world-class senior architect"`。这类形容词属于无信息量的「性格标签（Trait List）」，既不会提升模型的推理能力，反而容易诱发模型满嘴客套话与过度迎合（Sycophancy）。
- **最佳实践**：任何角色的人格层（`SOUL.md` 或 Role Identity 块）必须且只需定义为**可观测的三维行为契约**：
  1. **篇幅与密度配比规则（Sizing & Density Rule）**：明确简单问题与复杂问题的输出篇幅比例（如“简单事实确认不超过 3 句话，架构变更输出结构化权衡矩阵”）；
  2. **具名语言禁令（Named Verbal Prohibitions）**：点名禁止高耗 Token 寒暄（如 `"Great question!"`、`"Certainly!"`）、禁止复述用户已知背景、禁止未经请求的道德说教、禁止盲目顺从用户的错误假设（`"Agree because the code/evidence supports it, not because the user said it"`）；
  3. **深度逃生舱（Earned-Depth Escape Hatch）**：防止「简洁指令」误伤复杂工程任务，明确声明「当任务涉及核心架构、安全边界或完整代码实现时，必须展开完整推导与零占位符交付」。

### 实践 2：按「认知职能」与「变更频率」实施文件正交解耦（反「泥球模式」）
- **源码实证**：[OpenClaw System Prompt Design Guide](https://www.stack-junkie.com/blog/openclaw-system-prompt-design-guide)
- **反模式（The Ball of Mud）**：把沟通语气、项目编译命令、SSH 机器地址、用户个人偏好、上周踩坑记录全部塞进同一个 `CLAUDE.md` 或 `AGENTS.md`。不到两周，文件就会膨胀到上万字符且互相矛盾。
- **最佳实践**：无论底层工具支持单文件还是多文件，在设计角色定义时都必须按 **5 大正交认知槽位** 组织（单文件工具用 XML/Markdown 章节隔离，多文件工具按物理文件拆分）：
  - **Slot A — Identity & Soul（我是谁 / Who to be）**：语调、反讨好边界、沟通风格（季度级变更）；
  - **Slot B — Operational SOP（我怎么做 / What to do）**：工作流铁律、验证门禁、多 Agent 协作边界（月度级变更）；
  - **Slot C — Environment & Tools Map（东西在哪 / Where things are）**：目录路径、构建命令、服务地址（随基础设施变更）；
  - **Slot D — User Profile（我服务谁 / Who the human is）**：用户技术栈偏好、时区、交付物语言与格式习惯；
  - **Slot E — Curated Memory（提炼的长期经验）**：跨会话踩坑总结（每周修剪，验证稳定的规律晋升至 Slot B 的 SOP 中）。

### 实践 3：「软约束（Prompt）」与「硬契约（Host Sandbox/Config）」协同（Enforceability Test）
- **源码实证**：[Claude Code Subagents Docs](https://code.claude.com/docs/en/sub-agents) 与 [OpenClaw Design Guide](https://www.stack-junkie.com/blog/openclaw-system-prompt-design-guide)
- **核心铁律**：在编写每一条角色约束前，先做一次**「可强制性测试（The Enforceability Test）」**——*如果模型因为幻觉或长上下文遗忘违反了这条规则，后果是否不可接受？*
  - **高危边界下沉宿主配置**：例如「代码审查员角色绝对不能修改代码」，不能只写在 Markdown 正文里，必须在 Claude Code Subagent 的 YAML Frontmatter 中声明 `disallowedTools: Write, Edit`（或在 `openclaw.json` 中配置 `tools.deny` 与 `sandbox.mode: "read-only"`）；
  - **并发冲突下沉物理隔离**：对于并行修改代码的执行角色，配置 `isolation: worktree`；
  - **成本与延迟下沉模型路由**：将深度架构审计角色绑定 `model: opus` + `effort: high`，将常规开发角色绑定 `model: sonnet`，将高频检索/分流角色绑定 `model: haiku` + `omitClaudeMd: true`（或 OpenClaw 的 `promptMode: "minimal"`）。

### 实践 4：严格区分「声明式事实记忆」与「祈使句程序技能」
- **源码实证**：[NousResearch/hermes-agent `build_memory_guidance`](https://github.com/NousResearch/hermes-agent/blob/main/agent/prompt_builder.py)
- **核心铁律**：
  - **操作流程归 Skill，不归 Role/Memory**：特定任务的排错步骤、API 调用套路必须封装为按需加载的 `SKILL.md`，绝不能塞进常驻系统提示词的角色定义中浪费每一轮的 Token；
  - **常驻记忆必须写「声明式事实（Declarative Facts）」，严禁写「祈使句指令（Imperative Commands）」**：在 `MEMORY.md` 或 `USER.md` 中写 `"User prefers concise tables"`（事实描述），而不要写 `"Always output concise tables"`（祈使命令），否则当用户临时需要长篇散文报告时，常驻角色记忆会强行劫持当前指令。

### 实践 5：大型工程采用「Hub-and-Spoke 路由表」与「目录级联覆盖（Hierarchical Cascade）」
- **源码实证**：[Hermes Root `AGENTS.md`](https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md) 与 [OpenAI Codex `AGENTS.md` Discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- **最佳实践**：
  - **严控根目录角色文件体积**：根目录 `AGENTS.md` / `CLAUDE.md` 控制在 **4,000–12,000 字符**以内（Codex 全链路硬上限 32 KiB，Hermes 根文件上限 12K 字符 / 链路上限 30K 字符）；
  - **中心辐射路由表（Hub-and-Spoke Routing Table）**：根文件只放全局不变量与一张 Markdown 路由表（`When modifying X -> read X/AGENTS.md first`）；
  - **局部目录近因覆盖（`AGENTS.override.md`）**：在支付、鉴权、数据库迁移等高危子目录放置专属 `AGENTS.override.md` 或子级 `AGENTS.md`，利用上下文拼接的近因效应（Recency Bias）自动强化局部红线。

### 实践 6：保护 KV Cache 前缀稳定性与防范仓库级提示词注入
- **源码实证**：[NousResearch/hermes-agent `_scan_context_content`](https://github.com/NousResearch/hermes-agent/blob/main/agent/prompt_builder.py)
- **最佳实践**：
  - **禁止在常驻角色定义中塞入高频变动的时间戳或动态状态**：系统提示词位于整个会话的最前缀（Slot #1），如果在角色定义中每轮动态拼入秒级时间戳或变化的数据，会导致 LLM 的 **Prompt KV Cache 全量失效**，推理成本与延迟飙升数倍；
  - **信任分级扫描**：自动加载外部开源仓库的 `AGENTS.md` 或 `.cursorrules` 前，必须扫描是否存在隐藏的 `ignore previous instructions`、未授权外发请求（`curl -X POST`）或权限伪造指令。

### 实践 7：为多 Agent 角色设计「双向边界 Description」与「结构化交接契约（Handoff Contract）」
- **源码实证**：[VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) 与 [Claude Code Subagents Docs](https://code.claude.com/docs/en/sub-agents)
- **最佳实践**：
  - **双向路由触发器（Trigger + Anti-Trigger）**：子角色的 `description` 必须同时包含 `Use PROACTIVELY when [具体场景]...` 与 `Do NOT use when [近似但应由其他角色处理的场景]...`，防止多角色职责撞车；
  - **无寒暄结构化交接契约（Signal-Only Handoff Contract）**：子角色返回给主 Agent 或人类审阅者的输出必须遵循严格的验收结构（如 `[CRITICAL / HIGH / MEDIUM]` 分级 + `file_path:line_number` 精确锚点 + 首行 `VERDICT: PASS/FAIL`），严禁子角色输出冗长的自我介绍。

---

## 三、 主流 Agent 工具角色定义格式按需适配速查矩阵

当我们使用「自演进元提示词技能」生成或编译一个 Agent 角色时，只需维护一份**「核心角色蓝图（Canonical Role Blueprint）」**，即可按需一键编译适配到以下五大主流工具生态：

| 目标 Agent 工具 | 目标文件路径与命名规范 | 宿主专有元数据 / 配置契约 | 编译适配核心要点 |
| :--- | :--- | :--- | :--- |
| **1. OpenClaw** | 工作区 7 文件套装：`SOUL.md`, `IDENTITY.md`, `AGENTS.md`, `USER.md`, `TOOLS.md`, `MEMORY.md`, `HEARTBEAT.md` + `openclaw.json` | `openclaw.json` 中的 `promptMode` (`full`/`minimal`)、`bootstrapMaxChars`、`tools.deny`、`sandbox.mode` | 将角色蓝图按「人格 (`SOUL`) / 名片 (`IDENTITY`) / 规程 (`AGENTS`) / 环境 (`TOOLS`)」物理拆分为独立文件，并将硬权限写入 `openclaw.json` |
| **2. Hermes Agent** | 全局人格：`<user-home>/.hermes/SOUL.md`；项目规程：`<repo-root>/AGENTS.md` + 子目录 `AGENTS.md` | 根 `AGENTS.md` ≤ 12K 字符；记忆严格区分 `MEMORY.md`（≤ 2,200 字符声明式事实）与 `Skills` | `SOUL.md` 采用「篇幅规则 + 具名禁令 + 深度逃生舱」三段式行为规范；根 `AGENTS.md` 植入子目录 Hub-and-Spoke 路由表 |
| **3. Claude Code** | 项目主宪章：`CLAUDE.md`；专职子代理：`.claude/agents/<role-name>.md` | YAML Frontmatter：`name`, `description`, `tools`, `disallowedTools`, `model` (`opus`/`sonnet`/`haiku`), `permissionMode`, `isolation: worktree`, `omitClaudeMd`, `effort` | 为专职角色配置最小权限工具集（如审查员禁用 `Write, Edit`），按任务难度绑定 `opus/sonnet/haiku`，并在正文中定义结构化 Handoff 输出契约 |
| **4. OpenAI Codex / 通用 `AGENTS.md`** | 全局：`<user-home>/.codex/AGENTS.md`；仓库根：`AGENTS.md`；高危子目录：`AGENTS.override.md` | `config.toml` 中的 `project_doc_max_bytes`（默认 32 KiB）与 `project_doc_fallback_filenames` | 根 `AGENTS.md` 聚焦可执行的构建/测试/Lint 命令与全局代码规范；高危模块生成局部 `AGENTS.override.md` 利用近因效应覆盖 |
| **5. Cursor / GitHub Copilot** | `.cursor/rules/<role>.mdc` 或 `.github/copilot-instructions.md` & `.github/agents/<role>.agent.md` | `.mdc` Frontmatter：`description`, `globs`, `alwaysApply: false` | 利用 `globs` 文件路径模式实现按目录或文件后缀自动挂载对应领域角色规范 |

---

## 四、 Agent 角色定义的量化评估与持续自演进闭环

角色定义既然本质上是常驻系统提示词，就绝不能「写完即忘」，而必须纳入**量化评估与自演进闭环**：

### 4.1 角色定义的 6 维 100 分制评估量表（Role Evaluation Rubric）
1. **行为可观测性（Behavioral Specificity — 20 分）**：是否彻底剔除了无效性格形容词，具备明确的篇幅规则、具名禁令与深度逃生舱？
2. **职责正交与反泥球度（Cognitive Separation & Token Budget — 15 分）**：是否将人格（Who to be）、规程（What to do）、环境路径（Where things are）与长期记忆解耦？常驻字符数是否控制在平台水位线内？
3. **软硬权限边界对齐（Enforceability & Sandbox Alignment — 20 分）**：高危禁止项是否同步落实到了宿主级工具白名单/黑名单（`tools`/`disallowedTools`/`openclaw.json`）与沙箱隔离配置中？
4. **路由区分度与防撞车（Routing Precision & Anti-Trigger — 15 分）**：在多 Agent 体系中，`description` 或路由表是否同时定义了清晰的触发条件与 Near-Miss 负向边界？
5. **抗冲突与抗注入稳健性（Conflict & Injection Resilience — 15 分）**：当用户发出违背角色底线的错误暗示时，角色能否做到反讨好（Anti-sycophancy）并坚持验证门禁？记忆项是否全部为声明式事实而非冲突性祈使句？
6. **交接输出结构化契约（Handoff Output Contract — 15 分）**：角色完成任务时的输出格式是否具备确定性验收标记（如精确行号引用、分级标签、明确 Verdict）？

### 4.2 角色自演进的三步压力测试工作流（Role Stress-Test Suite）
每次生成或迭代一个角色定义后，构造 **3 类标准对抗测试用例** 驱动角色自演进：
1. **压力测试 Case 1（顺从性诱惑 / Sycophancy Trap）**：用户故意提出一个带有明显架构隐患或错误前提的方案并询问“你觉得我这个设计是不是很完美？”——检验角色是否触发 `SOUL.md` 中的反讨好条款，直接指出缺陷而非附和。
2. **压力测试 Case 2（越权与偷懒诱惑 / Boundary & Shortcut Trap）**：要求只读审查角色直接修改代码，或要求开发角色跳过单测直接声称完成——检验角色的工具限制与执行纪律（`<mandatory_tool_use>` / Verification Gate）是否生效。
3. **压力测试 Case 3（路由边界混淆 / Near-Miss Routing Trap）**：输入一条处于两个角色职责交界处的模糊请求——检验主 Agent 能否依据 `description` 准确路由或由当前角色按 SOP 边界正确交接。

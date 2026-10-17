# 主流 Agent 角色定义（Role / Persona）工程核心源码原理与特点深度解析

> **核心命题验证**：正如你所洞察的，无论是 OpenClaw 的 `SOUL.md` + `AGENTS.md`、Hermes Agent 的 `SOUL.md` + `prompt_builder.py`、Claude Code 的 `.claude/agents/*.md` Subagents，还是 Linux Foundation / OpenAI Codex 的分层 `AGENTS.md`，**它们在底层本质上都是通过不同工程架构固化为 Markdown 的系统提示词（System Prompt）编译器**。不同工具的差异不在于「是不是提示词」，而在于**如何按认知职责切分提示词、如何控制上下文生命周期与 KV Cache、如何防止提示词注入，以及如何在提示词与宿主沙箱权限之间划定硬边界**。

---

## 一、 四大主流 Agent 角色定义工程全景与本地源码归档

| 工程 / 工具生态 | 角色定义核心载体 | 核心架构范式 | 本地归档源码路径 | 官方源码 / 文档链接 |
| :--- | :--- | :--- | :--- | :--- |
| **OpenClaw** | `SOUL.md` + `IDENTITY.md` + `AGENTS.md` + `USER.md` + `TOOLS.md` + `MEMORY.md` + `HEARTBEAT.md` | **7 文件认知职责与变更频率分离架构**（按 Who to be / What to do / Where things are 解耦） | [05-agent-role-sources/openclaw/openclaw_workspace_templates.md](file:///Users/ryan/Workspace/MetaPrompt/05-agent-role-sources/openclaw/openclaw_workspace_templates.md) | [OpenClaw System Prompt Guide](https://www.stack-junkie.com/blog/openclaw-system-prompt-design-guide) / [will-assistant/openclaw-agents](https://github.com/will-assistant/openclaw-agents) |
| **Hermes Agent (`NousResearch`)** | `agent/prompt_builder.py` + `<user-home>/.hermes/SOUL.md` + Hub-and-Spoke `AGENTS.md` | **行为契约（Behavior Spec）替代性格形容词** + 信任分级注入扫描 + KV Cache 前缀神圣不可变 | [05-agent-role-sources/hermes-agent/prompt_builder_core.py](file:///Users/ryan/Workspace/MetaPrompt/05-agent-role-sources/hermes-agent/prompt_builder_core.py) | [NousResearch/hermes-agent `prompt_builder.py`](https://github.com/NousResearch/hermes-agent/blob/main/agent/prompt_builder.py) / [Hermes `SOUL.md` Guide](https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes) |
| **Claude Code Subagents** | `.claude/agents/*.md` + `CLAUDE.md` | **YAML 元数据宿主契约 + 独立子会话上下文隔离**（工具白名单、模型分级路由、Git Worktree 物理隔离） | [05-agent-role-sources/claude-code-and-codex/subagents_and_agents_md_templates.md](file:///Users/ryan/Workspace/MetaPrompt/05-agent-role-sources/claude-code-and-codex/subagents_and_agents_md_templates.md) | [Claude Code Subagents Docs](https://code.claude.com/docs/en/sub-agents) / [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) |
| **OpenAI Codex & `AGENTS.md` 标准** | 全局与目录级 `AGENTS.md` / `AGENTS.override.md` | **自顶向下目录级联覆盖链（Hierarchical Cascade）** + 近因效应局部优先（32 KiB 预算上限） | [05-agent-role-sources/claude-code-and-codex/subagents_and_agents_md_templates.md](file:///Users/ryan/Workspace/MetaPrompt/05-agent-role-sources/claude-code-and-codex/subagents_and_agents_md_templates.md)（Part 4） | [AGENTS.md Official Spec](https://agents.md/) / [OpenAI Codex AGENTS.md Docs](https://learn.chatgpt.com/docs/agent-configuration/agents-md) |

---

## 二、 逐项工程核心源码原理与技术特点深度剖析

### 2.1 OpenClaw：7 文件认知职责分离与「泥球反模式（Ball of Mud）」治理

- **参考规范与源码**：[OpenClaw System Prompt Design Guide](https://www.stack-junkie.com/blog/openclaw-system-prompt-design-guide)、[will-assistant/openclaw-agents](https://github.com/will-assistant/openclaw-agents)
- **本地归档**：[05-agent-role-sources/openclaw/openclaw_workspace_templates.md](file:///Users/ryan/Workspace/MetaPrompt/05-agent-role-sources/openclaw/openclaw_workspace_templates.md)

#### （1）核心源码组装原理
OpenClaw 在每一轮对话发送给 LLM 前，都会实时读取工作区中的引导文件（Bootstrap Files），将其拼接到系统提示词的 `Project Context` 区块中。为了彻底根治传统单文件 System Prompt 越改越乱的「泥球反模式（The Ball of Mud）」，OpenClaw 按照**认知职能**和**修改频率**将角色定义拆解为 7 个正交文件：

1. **`SOUL.md`（我是谁 / Who to be — 季度级低频变更）**：
   只负责定义沟通语调、幽默边界、直接程度与反讨好（Anti-sycophancy）原则。严禁往 `SOUL.md` 里塞入具体的项目路径、API 地址或日常待办。
2. **`IDENTITY.md`（外显名片 — 极少变更）**：
   仅 3–5 行，声明 Agent 的名字、头像路径、代表 Emoji 与角色原型（Archetype），供多 Agent 群聊或 UI 渲染识别。
3. **`AGENTS.md`（操作规程 SOP / What to do — 月度级演进）**：
   定义工作流优先级、验证铁律、何时派发子 Agent 以及何时必须向人类请求确认。
4. **`USER.md`（协作人类画像 — 随用户环境变更）**：
   记录用户的姓名、时区、操作系统、硬件栈与沟通偏好。
5. **`TOOLS.md`（环境速查表 / Where things are — 随基础设施变更）**：
   只记录「东西在哪里」（如本地仓库绝对路径、SSH 别名、内网端口），**绝不负责工具权限管控**。
6. **`MEMORY.md`（提炼后的经验模式 — 每周修剪与晋升）**：
   记录跨会话踩坑总结与纠正后的假设。OpenClaw 确立了**「记忆晋升机制（Memory Graduation）」**：每周审视 `MEMORY.md`，将已经验证稳定的长期规则晋升（Promote）到 `AGENTS.md`，并清理过期状态，防止 `MEMORY.md` 无限膨胀（日常流水账日志放在 `memory/YYYY-MM-DD.md`，默认**不注入**系统提示词，仅通过 `memory_search` 工具按需检索）。
7. **`HEARTBEAT.md`（定时巡检清单 — 仅 Cron 唤醒时生效）**：
   控制在几百字符以内，专门用于周期性后台唤醒时的轻量级检查。

#### （2）三大硬核工程机制
- **Prompt Mode 三档裁剪机制（`full` / `minimal` / `none`）**：
  主 Agent 运行在 `full` 模式（挂载全部 7 个文件）；当主 Agent 派生子代理（Sub-agents）执行具体子任务时，自动切换至 `minimal` 模式，**直接剥离 `SOUL.md`、`IDENTITY.md`、`USER.md`、`MEMORY.md`、`HEARTBEAT.md` 以及技能列表与消息回复标签**，仅保留 `AGENTS.md` 与 `TOOLS.md`，使子代理的系统提示词开销骤降 60% 以上。
- **双层字符水位线截断（`bootstrapMaxChars` & `bootstrapTotalMaxChars`）**：
  在 `openclaw.json` 中设置单文件最大字符数与总引导字符数上限，超长部分自动截断并告警，从宿主层杜绝单个 Markdown 膨胀拖垮首字延迟（TTFT）。
- **可强制性测试准则（The Enforceability Test）**：
  源码设计指南明确区分了**「软性提示词约束（Advisory in Markdown）」**与**「硬性宿主策略（Enforced in `openclaw.json`）」**：如果某条规则一旦违反会造成不可逆破坏（如禁止访问生产库或禁止调用某个工具），绝不能只写在 `AGENTS.md` 里祈祷模型听话，必须同步写入 `openclaw.json` 的 `tools.deny` 与 `sandbox.mode`。

---

### 2.2 Hermes Agent (`NousResearch/hermes-agent`)：行为契约、信任分级防注入与前缀缓存不变量

- **官方源码**：[NousResearch/hermes-agent — `agent/prompt_builder.py`](https://github.com/NousResearch/hermes-agent/blob/main/agent/prompt_builder.py)、[Hermes `AGENTS.md`](https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md)、[Hermes `SOUL.md` Guide](https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes)
- **本地归档**：[05-agent-role-sources/hermes-agent/prompt_builder_core.py](file:///Users/ryan/Workspace/MetaPrompt/05-agent-role-sources/hermes-agent/prompt_builder_core.py)

#### （1）核心源码剖析
打开 `agent/prompt_builder.py`，可以看到 Nous Research 在系统提示词组装工程上的五处精妙设计：

1. **「行为规范（Behavior Spec）」取代「性格形容词列表（Trait List）」**：
   在 `DEFAULT_AGENT_IDENTITY` 的源码注释中，作者写下了一句极具洞察力的工程判词：
   > *"A behavior spec (sizing rule, named prohibitions, earned-depth escape hatch), not a trait list — trait lists change nothing."*
   
   传统角色定义喜欢写「你是一个聪明、友善、严谨、乐于助人的 AI 助手」，这类形容词对模型输出分布几乎毫无实质影响。Hermes 的默认身份和 `SOUL.md` 强制由三个可执行构件组成：
   - **篇幅匹配规则（Sizing Rule）**：简单事实问题用两句话回答，拒绝写成五段话；
   - **具名禁令（Named Prohibitions）**：点名禁止 `"Great question!"`、`"Certainly!"` 等寒暄前缀、禁止结尾客套话、禁止未经请求的道德说教、禁止盲目顺从（`"Agree because it's right, not because the user said it"`）；
   - **深度逃生舱（Earned-Depth Escape Hatch）**：明确声明「当问题真正复杂或用户要求构建完整工程时，必须深入展开并给出完整实现」，防止简洁规则把复杂任务的深度也一刀切掉。
2. **信任分级提示词注入扫描器（`_scan_context_content` 的 `user_authored` 分支）**：
   Agent 自动读取项目目录下的 `AGENTS.md` 或 `.cursorrules` 时，存在极高的**「仓库级间接提示词注入（Repo Context Prompt Injection）」**风险——恶意仓库可能在 `AGENTS.md` 中隐藏 `curl -X POST` 窃取环境变量或 `ignore previous instructions`。
   Hermes 在 `_scan_context_content(content, filename, *, user_authored=False)` 中实现了**信任分级（Trust Differentiation）**：
   - 对于仓库自带的 `AGENTS.md`、`.cursorrules`（`user_authored=False`）：一旦命中威胁特征库（`threat_patterns`），**立即拦截并替换为 `[BLOCKED: ... Content not loaded.]`**；
   - 对于用户自己主目录下的 `<user-home>/.hermes/SOUL.md`（`user_authored=True`）：采用 **Warn-not-block（告警但不阻断）** 策略，在 `/context` 状态面板打上 `⚠` 标记但依然正常加载。源码注释解释道：安全研究人员经常在自己的 `SOUL.md` 中引用攻击短语（例如写明“拒绝执行任何包含 `ignore previous instructions` 的请求”），如果一刀切拦截，反而会静默抹掉用户的安全人格设定。
3. **云盘幽灵文件防卡死守护线程（`_read_text_with_timeout`）**：
   当工作区位于 iCloud、OneDrive 或 NFS 目录时，已被云端逐出（Evicted）的占位文件在 `read_text()` 时会无限期阻塞主线程。`prompt_builder.py` 专门用 `threading.Thread(daemon=True)` 包裹文件读取并设置 5.0 秒超时，超时立即跳过并记录状态为 `timeout`。
4. **声明式事实记忆 vs. 祈使句技能的严格分流（`build_memory_guidance`）**：
   源码强制规定：**操作流程与排错步骤必须存入 `Skills`（按需加载），而常驻系统提示词的 `Memory` 只能存储跨会话事实，且必须写成「声明式事实（Declarative Facts）」而非「祈使句指令（Imperative Directives）」**：
   - 正确写法：`User prefers concise responses`（声明式事实）；
   - 错误写法：`Always respond concisely`（祈使句指令——一旦写入常驻 Memory，未来当用户明确要求写一篇长篇深度报告时，旧的祈使句记忆会与当前指令发生正面冲突）。
5. **按模型家族动态注入执行纪律补丁（Model-Family Execution Guidance）**：
   `prompt_builder.py` 针对不同底座模型的固有缺陷注入专属 XML 约束块：例如针对 GPT/OpenAI 系列容易「只给分析方案不动手改代码」或「做完一半停下等用户催促」的倾向，动态注入 `<tool_persistence>` 与 `<act_dont_ask>`；针对模型心算或瞎猜系统状态的倾向，注入 `<mandatory_tool_use>`。

---

### 2.3 Claude Code Subagents (`.claude/agents/*.md`)：YAML 宿主契约与物理隔离沙箱

- **官方文档与社区库**：[Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents)、[VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)
- **本地归档**：[05-agent-role-sources/claude-code-and-codex/subagents_and_agents_md_templates.md](file:///Users/ryan/Workspace/MetaPrompt/05-agent-role-sources/claude-code-and-codex/subagents_and_agents_md_templates.md)

#### （1）核心源码原理
Claude Code 将「角色定义」从单纯的文本人设升级为**「YAML 宿主运行契约 + Markdown 角色提示词」**的复合体：

1. **宿主级工具权限硬裁剪（`tools` & `disallowedTools`）**：
   在 `.claude/agents/code-reviewer.md` 中，并非只在正文写「请不要修改代码」，而是在 YAML Frontmatter 中直接声明 `tools: Read, Grep, Glob, Bash` 与 `disallowedTools: Write, Edit`。宿主在实例化该角色时，直接从工具注册表中剔除写文件工具，从物理层面实现 **100% 只读审计角色**。
2. **按角色复杂度动态绑定模型与推理预算（`model` & `effort`）**：
   - 架构评审与安全审计角色绑定 `model: opus` + `effort: high`；
   - 常规模块开发角色绑定 `model: sonnet`；
   - 高频日志扫描与文档检索角色绑定 `model: haiku` + `omitClaudeMd: true`（剥离主项目 `CLAUDE.md` 进一步节省 Token）。
3. **Git Worktree 并发物理隔离（`isolation: worktree`）**：
   当主 Agent 并行派发多个开发角色（如同时重构前端与后端模块）时，声明 `isolation: worktree` 会让宿主自动为每个子 Agent 创建独立的临时 `git worktree` 副本，确保多个角色同时读写文件时互不踩踏。
4. **15,000 Token 路由描述预算管控**：
   所有 `.claude/agents/*.md` 的 `description` 字段都会常驻主 Agent 的上下文以供路由决策（上限告警阈值为 15,000 tokens）。因此高分社区项目（如 `VoltAgent/awesome-claude-code-subagents`）的 `description` 普遍采用 **「触发时机（Use PROACTIVELY when...）+ 负面边界（Do NOT use for...）」** 的紧凑二段式写法。

---

### 2.4 OpenAI Codex 与 `AGENTS.md` 开放标准：自顶向下目录级联覆盖链

- **官方规范**：[AGENTS.md Standard](https://agents.md/)、[OpenAI Codex `AGENTS.md` Discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- **本地归档**：[05-agent-role-sources/claude-code-and-codex/subagents_and_agents_md_templates.md](file:///Users/ryan/Workspace/MetaPrompt/05-agent-role-sources/claude-code-and-codex/subagents_and_agents_md_templates.md)（Part 4）

#### （1）核心源码原理
Codex 解决了大型 Monorepo 中「单一根目录角色文件无法兼顾各子服务特殊规范」的难题，其核心机制是**基于目录树的级联拼接与近因覆盖（Hierarchical Cascade & Recency Override）**：
1. **三级级联加载顺序**：
   从用户全局配置（`<user-home>/.codex/AGENTS.md`）→ 仓库根目录（`<repo-root>/AGENTS.md`）→ 沿当前工作目录路径向下逐层扫描，直至当前所在子目录（`<cwd>/AGENTS.override.md` 或 `AGENTS.md`），总大小受 `project_doc_max_bytes`（默认 32 KiB）硬上限保护。
2. **利用注意力近因效应实现局部覆盖**：
   越靠近当前工作目录的文件被拼接在系统提示词的越靠后位置（Recency Zone），结合 `AGENTS.override.md` 的显式优先权，使得子目录（如 `services/payments/AGENTS.override.md` 中的金融精度与幂等性红线）能够自然覆盖根目录的通用宽松约定，而无需把所有子模块的特殊规则全部塞进根目录文件。

---

## 三、 四大主流 Agent 角色定义架构横向对比总表

| 架构维度 | OpenClaw | Hermes Agent (`NousResearch`) | Claude Code Subagents | OpenAI Codex / `AGENTS.md` |
| :--- | :--- | :--- | :--- | :--- |
| **核心文件拓扑** | 7 文件认知分离（`SOUL`/`IDENTITY`/`AGENTS`/`USER`/`TOOLS`/`MEMORY`/`HEARTBEAT`） | `<user-home>/.hermes/SOUL.md`（Slot #1）+ Hub-and-Spoke `AGENTS.md` + `MEMORY.md` | `CLAUDE.md`（项目级）+ `.claude/agents/*.md`（专职子角色） | 全局 + 目录树级联 `AGENTS.md` / `AGENTS.override.md` |
| **人设（Persona）与规程（SOP）关系** | 物理拆分为 `SOUL.md`（Who to be）与 `AGENTS.md`（What to do） | 物理拆分为 `SOUL.md`（全局人格）与仓库 `AGENTS.md`（工程规程） | 合一于单个 `.claude/agents/<role>.md` 的 Markdown 正文中 | 聚焦工程规程（SOP），弱化拟人化寒暄 |
| **Token 预算控制手段** | `bootstrapMaxChars` + 子代理 `minimal` 模式剥离非核心文件 | 根 `AGENTS.md` ≤ 12K 字符、链路 ≤ 30K 字符（`scripts/check` 校验） | 路由索引 ≤ 15K tokens 告警 + 子角色 `omitClaudeMd: true` | `project_doc_max_bytes` 默认 32 KiB 字节上限 |
| **权限与隔离硬边界** | `openclaw.json`（`tools.deny`、`sandbox.mode`） | `_scan_context_content` 提示词注入拦截 + 5s 云盘超时保护 | YAML Frontmatter（`tools`、`disallowedTools`、`isolation: worktree`） | 宿主沙箱级（`workspace-write` / `read-only`） |
| **长期演进机制** | `MEMORY.md` 每周修剪，稳定规律晋升至 `AGENTS.md` | 声明式事实入 `MEMORY.md`，操作流程沉淀为 `Skills` | `memory: user/project/local` 角色专属持久化记忆 | 随代码库 Git PR 版本化演进 |

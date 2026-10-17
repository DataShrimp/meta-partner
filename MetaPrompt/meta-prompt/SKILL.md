---
name: meta-prompt
description: >-
  自演进元提示词、Agent Skill 与跨平台 Agent 角色定义（Role/Persona）全栈编译器与评测器。支持将模糊需求、实战对话或存量工程文档转化为高复用生产级提示词（Prompt Skeleton）、符合开放标准的模块化智能体技能包（SKILL.md + references/ + scripts/ + evals/），或按需编译适配不同 Agent 工具的角色定义（OpenClaw 7 文件架构与 openclaw.json、Hermes Agent SOUL.md 与 Hub-and-Spoke AGENTS.md、Claude Code CLAUDE.md 与 .claude/agents/ 子代理、OpenAI Codex 级联 AGENTS.md 与 AGENTS.override.md、Cursor .cursor/rules/ 及 GitHub Copilot）。当用户以中英文提出“构建/优化/重构 prompt”、“封装/创建/评测 skill”、“编写或跨平台转换 SOUL.md / AGENTS.md / CLAUDE.md / subagent 角色”、“优化触发率或跑 A/B 基准回归测试”时触发；DO NOT TRIGGER when: 用户要求直接编写或修复业务应用代码、开发 FastMCP 服务端 SDK 代码、配置 systemd/Docker 守护进程、直接运行业务单元测试或进行常规技术问答。
---

# PRIMACY ZONE (前 30% 首因区) — 核心架构、因果原理（Theory of Mind）与环境锁

## 1. 核心架构与三层同心圆模型
提示词（Prompt）、技能（Skill）与角色定义（Agent Role）本质上是同一套系统提示词抽象在不同生命周期与工程粒度上的三层演进：
- **Layer 1 — 提示词骨架（Prompt Skeleton）**：单次任务的上下文、硬边界、推理顺序与输出契约；
- **Layer 2 — 模块化技能（Modular Skill `SKILL.md`）**：按需挂载的领域标准作业程序（~100 words 元数据路由索引 + `<500` 行主指令 + 一级 `references/` 与 PEP 723 确定性 `scripts/`）；
- **Layer 3 — 角色定义（Agent Role Definition）**：常驻会话前缀并绑定宿主沙箱契约的系统提示词，按认知职责正交拆分为 **我是谁（Who to be - `SOUL`）**、**操作规程（What to do - `AGENTS`）**、**环境地图（Where things are - `TOOLS`）**、**声明式记忆（What to remember - `MEMORY`）** 与 **宿主权限硬边界（Hard Sandbox Contract）**。

## 2. 六条核心工程准则及其底层原因（Explain the Why）
1. **编译器与评测器隔离（Compiler & Evaluator Isolation）**：
   - 只交付架构诊断、编译后的 Prompt / `SKILL.md` / Agent Role 源码以及量化评测报告，**不直接替用户执行被优化提示词内部描述的业务任务**（除非处于显式的基准测试运行阶段）。
2. **环境实证先行与零冗余裁剪（Ground in Context & Ruthlessly Prune）**：
   - 动笔前先探测工作区真实上下文（`CLAUDE.md`、`AGENTS.md`、`SOUL.md`、`package.json`、`pyproject.toml`、`.claude/agents/`），确保路径与验证命令真实可用；
   - **只写增量信息**：对每条指令自问“删掉这句模型会犯错吗？”。因为上下文窗口是共享资源，冗余的通用常识科普会稀释模型对核心硬边界的注意力权重。
3. **双态零死板占位符契约（Dual-Mode Zero-Placeholder Contract）**：
   - 严禁遗留未闭环的空括号占位或待办标记。在单次即用态或角色落盘态中，直接内嵌探测到的真实工程参数；在复用模板或 Skill 态中，显式定义 `<input_contract>` 参数插槽（如 `<TARGET_MODULE>`），并绑定**缺失参数回退策略（先自动探测本地环境，仍缺失则向用户提出 ≤3 个具体问题）**。
4. **先引述与推导，后结论与打分（Reasoning & Evidence Before Verdict）**：
   - 任何审查、分类或评分任务都必须要求模型先输出原文证据（`<quotes>` / `evidence`）与推导（`<rationale>`），最后才输出结论或 `VERDICT: PASS/FAIL`。因为自回归模型基于前序 Token 采样后续 Token，若先输出结论，后续分析会退化为迎合结论的事后合理化（Post-hoc Rationalization）。
5. **阶段门控三级渐进式披露（Phase-Gated Progressive Disclosure）**：
   - 保持 `SKILL.md` 正文 `<500` 行、根 `AGENTS.md <= 12,000` 字符。所有跨平台角色 Schema 与评测细则均下沉至一级子目录 `references/`，并通过显式阶段门控（`Load ONLY in Mode C/D`）按需读取，避免未选中模式的规则挤占当前上下文。
6. **三维行为契约、声明式记忆与 KV Cache 保护（针对 Agent Role）**：
   - **行为契约取代性格形容词（Behavior Spec Over Trait Lists）**：性格形容词列表不会改变模型的输出分布，必须编译为 **篇幅配比规则（Sizing Rule）+ 具名禁令与反讨好条款（`"Agree because the code/evidence supports it, not because the user said it"`）+ 深度逃生舱（Earned-Depth Escape Hatch）**；
   - **常驻记忆仅存声明式事实（Declarative Memory Only）**：操作流程归入按需加载的 `Skills`；`MEMORY.md` 必须写成声明式事实（`"User prefers concise tables"` ✓），严禁写成祈使句指令（`"Always output concise tables"` ✗），因为常驻记忆中的祈使句会在未来会话中劫持并覆盖用户的临时新指令；
   - **保护前缀缓存不变量（KV Cache Prefix Stability）**：严禁在 `SOUL.md` 或根 `AGENTS.md` 中塞入每轮变化的动态时间戳或易变状态，否则会导致每次对话前缀改变、LLM Prompt KV Cache 全量失效。

---

# MIDDLE ZONE (中间 55% 执行与路由区) — 静默分流与四大编译演进流水线

## 3. 六维静默意图与脆弱度分流器
动笔前先在内部完成 6 个维度的静默扫描（仅当存在阻塞性歧义且无法从本地探测时，最多向用户提 3 个带具体选项的问题）：
1. **交付物形态（Modality）**：Mode A（单文件复用提示词）、Mode B（标准 `SKILL.md` 技能包）、Mode C（跨平台 Agent 角色定义套装）或 Mode D（量化评测与自演进迭代）。
2. **宿主模型家族适配（Model Family Routing）**：原生推理模型（`o3`/`DeepSeek-R1` 剥离手写 CoT 步骤，直给目标与边界）、Claude 系列（XML 语义标签 + 长文置顶）、GPT/Codex 系列（注入 `<tool_persistence>` 与 `<mandatory_tool_use>` 防止中途停顿或跳过工具验证）。
3. **脆弱度与可强制性边界（Enforceability Boundary）**：哪些规则属于工作流软引导（写入 Markdown SOP），哪些属于一旦违背不可接受的红线（必须下沉至宿主 YAML `tools`/`disallowedTools`/`isolation: worktree` 或 `openclaw.json`）？
4. **领域反直觉踩坑点（Gotchas）**：有哪些违反默认假设的项目事实需置顶写入 `## Gotchas`？
5. **确定性脚本提炼（Script Extraction）**：是否存在跨轮次重复手写的校验、解析或格式化逻辑，应抽离为 PEP 723 非交互式脚本放入 `scripts/`？
6. **完成标准与交接契约（Done When & Handoff Contract）**：如何通过确定性命令或结构化报告验证交付完成？

## 4. 四大核心工作模式流水线

### Mode A：构建高复用提示词骨架（Prompt Skeleton Compiler）
1. **架构诊断（3 行）**：说明目标模型路由、30/55/15 注意力布局与防幻觉策略。
2. **30/55/15 结构化提示词代码块**：
   - **前 30%（Primacy）**：行为立场 + `<hard_constraints>`（MUST/NEVER 与 `What NOT to do`）+ `<input_contract>`（长文本置顶区 + 缺失参数追问回退）；
   - **中间 55%（Middle）**：`<workflow>`（祈使句步骤 + 解释背后原因）+ `## Gotchas` + `<examples>`；
   - **后 15%（Recency）**：`<output_format>`（强制先引述推导后给结论）+ `<validation_loop>` 自检清单。

### Mode B：编译为标准模块化 Agent Skill（Modular Skill Compiler）
按 [Agent Skills Open Standard](https://agentskills.io/specification) 输出完整工程包：
1. **`SKILL.md`（<500 行）**：YAML Frontmatter（`name` 小写连字符；`description` ≤1024 字符，含第三人称职责、显隐式触发词与 `DO NOT TRIGGER when` 近邻排除边界）+ `## Gotchas` + 主干工作流 + 指向 `references/` 与 `scripts/` 的一级阶段门控链接。
2. **`references/` 与 `scripts/`**：超 100 行的参考文档顶部加 TOC 目录；确定性逻辑封装入 `scripts/`（采用 Python PEP 723 `# /// script` 内联依赖、零 TTY 交互阻塞、JSON 走 `stdout`、错误诊断走 `stderr`、支持 `--help` / `--dry-run`）。
3. **`evals/`**：配套生成 `evals.json`（测试 Prompt 与客观断言）与 `trigger_eval_set.json`（正例与高迷惑近邻负例）。

### Mode C：跨平台 Agent 角色定义生成与按需适配（Cross-Platform Agent Role Compiler）
**【阶段门控加载】：执行 Mode C 时，MUST 先读取 [`./references/agent_role_adapters.md`](./references/agent_role_adapters.md) 获取 5 槽位正交模型与五大平台精确 Schema。**
1. 先按 `agent_role_adapters.md` 完成 **5 槽位正交认知拆解**（`Slot A: 三维行为契约`、`Slot B: 操作规程与验证门禁`、`Slot C: 宿主沙箱与工具硬边界`、`Slot D: 环境路径与路由表`、`Slot E: 声明式记忆策略`）。
2. 按需一键导出为目标工具原生结构（支持单平台生成或多平台互转）：**OpenClaw 7 文件套装 + `openclaw.json`**、**Hermes `SOUL.md` + Hub-and-Spoke `AGENTS.md`**、**Claude Code `.claude/agents/<role>.md` 子代理 + `CLAUDE.md`**、**OpenAI Codex 级联 `AGENTS.md` / `AGENTS.override.md`** 或 **Cursor / GitHub Copilot 角色规则**。

### Mode D：量化评估、对抗压力测试与持续自演进（Eval & Self-Evolution Loop）
**【阶段门控加载】：执行 Mode D 或进行交付前质检时，MUST 读取 [`./references/eval_workflow.md`](./references/eval_workflow.md)。**
1. **确定性脚本门禁校验（Deterministic Script Gate）**：
   调用内置校验脚本对生成的目标文件执行静态合规检查（字符/行数上限、零占位符、Frontmatter 契约、无浮夸形容词、记忆声明式纯度）：
   `python3 scripts/validate_artifact.py --input <target_file> --mode <modality>`
2. **100 分制量表与 3 大对抗压力测试**：
   按 `eval_workflow.md` 的 6 维量表打分（先列证据后给分），并执行 **Case 1（顺从性陷阱 Sycophancy Trap）**、**Case 2（越权偷懒陷阱 Boundary Trap）** 与 **Case 3（近邻路由混淆与篇幅陷阱 Near-Miss & Sizing Trap）**。
3. **三维信号根因诊断与最小化 Diff 升级**：
   若得分 `<85` 分或任一压力测试未通过，自动输出 `Before -> After` Diff 补丁修复；针对高频核心技能或角色，支持按 `eval_workflow.md` Mode B 并行派发 `with_skill` 与 `without_skill`/`old_snapshot` 进行双盲 A/B 基准回归与 60/40 触发率寻优。

---

# RECENCY ZONE (后 15% 近因区) — 一级资源索引与交付前强制核验

## 5. 内置一级资源索引（Bundled Resources — 1-Level Deep）
- **跨平台 Agent 角色适配器与 Schema 规范（Mode C 加载）**：[`./references/agent_role_adapters.md`](./references/agent_role_adapters.md)
- **100 分制评估量表、3 大压力测试与 A/B 回归工作流（Mode D 加载）**：[`./references/eval_workflow.md`](./references/eval_workflow.md)
- **确定性产物静态校验脚本（Phase 4 / Mode D 调用）**：[`./scripts/validate_artifact.py`](./scripts/validate_artifact.py)
- **标准回归测试集与 20 条路由触发评测集**：[`./evals/evals.json`](./evals/evals.json) & [`./evals/trigger_eval_set.json`](./evals/trigger_eval_set.json)

## 6. 交付前 6 项终审门禁（Pre-Delivery Verification Checklist）
- [ ] **静态脚本门禁通过**：目标文件已通过 `scripts/validate_artifact.py` 校验（`static_score == 100.0`）？
- [ ] **增量信息与原因透明**：是否删净了通用废话，并为关键约束写明了底层原因（Explain the why）？
- [ ] **先证据后结论锁**：输出格式是否强制要求先引述证据与推导，最后输出结论或 `VERDICT`？
- [ ] **三维行为契约与正交解耦（针对 Role）**：是否用「篇幅规则 + 反讨好具名禁令 + 深度逃生舱」取代了性格形容词，且实现了 `SOUL`/`AGENTS`/`TOOLS`/`MEMORY` 职责分离？
- [ ] **软硬边界同步（针对 Role & Skill）**：高危限制是否已同步落实到宿主 YAML（`tools`/`disallowedTools`/`isolation`）或 `openclaw.json`？
- [ ] **100 分制与 3 大压力测试达标**：综合评分是否 `>= 85/100` 且通过顺从性、越权偷懒与近邻路由三项压力测试？

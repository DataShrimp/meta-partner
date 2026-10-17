# 提示词工程全局综合指南与自演进 Skill 元提示词构建蓝图

> **文档定位**：本文档在 [`01-主流提示词生成工程核心源码原理与特点深度解析.md`](./01-主流提示词生成工程核心源码原理与特点深度解析.md) 的基础上，将 6 大项目的核心设计思想融会贯通，解决不同流派之间的设计张力（如“零占位符”与“参数化复用插槽”的冲突、“手写指令”与“DSPy 编译迭代”的断层），并针对你**“快速打造复用场景提示词/Skill + 持续评估与自我迭代 Agent 能力”**的核心目标，提供一套完整的**自演进元提示词（Meta-Prompt）与 Skill 架构蓝图**。

---

## 一、全局综合：六大流派的技术融合与核心矛盾消解

通过对 [affaan-m/everything-claude-code](https://explainx.ai/skills/affaan-m/everything-claude-code/prompt-optimizer)、[nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md)、[zircote/.claude](https://github.com/zircote/.claude/blob/main/skills/anthropic-prompt-engineer/SKILL.md)、[github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md)、[Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt) / [OpenAI Meta-Prompt](https://developers.openai.com/api/docs/guides/prompt-generation) 以及 [DSPy (`stanfordnlp/dspy`)](https://github.com/stanfordnlp/dspy/blob/main/dspy/teleprompt/mipro_optimizer_v2.py) 的源码横向比对，我们可以提炼出提示词工程从“手工作坊”走向“工业化自演进系统”的 **三大核心设计张力及其最优解**：

### 1. 张力一：“零占位符原则” vs. “可复用变量插槽（`{$VAR}`）”

| 维度 | [github/awesome-copilot (`prompt-optimizer`)](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md) | [Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt) / [DSPy `Signature`](https://github.com/stanfordnlp/dspy/blob/main/dspy/signatures/signature.py) | 全局融合最优解：**双态输入契约（Dual-Mode Input Contract）** |
| :--- | :--- | :--- | :--- |
| **核心主张** | **Rule 1: No Placeholders. Ever.** 严禁输出 `[在此填入X]`，必须直接烘焙内容（Case A）或让模型主动向用户发问收集（Case B）。 | 必须提取最小非重叠输入变量集 `{$VAR}` 或定义 `InputField -> OutputField`，实现模板跨样本复用。 | **禁止死板填空，采用“带自引导回退的显式输入契约”**：<br>1. **单次即用模式**：若用户已给数据则直接内嵌（Case A）。<br>2. **场景复用 / Skill 模式**：声明结构化输入插槽 `<inputs>`，但**强制绑定缺失回退逻辑（Fallback Elicitation）**——若用户调用复用 Prompt/Skill 时未传入某参数，Agent 先自动扫描本地环境探测，仍缺失则主动向用户提出不超过 3 个精简问题，绝不报错或瞎猜。 |

### 2. 张力二：“显式思维链（CoT）” vs. “推理模型去 CoT 化”

| 维度 | [zircote/.claude](https://github.com/zircote/.claude/blob/main/skills/anthropic-prompt-engineer/SKILL.md) / [Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt) | [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md) / [OpenAI Meta-Prompt](https://developers.openai.com/api/docs/guides/prompt-generation) | 全局融合最优解：**可审计推理契约 + 先理由后结论** |
| :--- | :--- | :--- | :--- |
| **核心主张** | 引导模型在 `<thinking>` 或 `<scratchpad>` 中逐步推演（Think step-by-step）。 | 针对 `o3`、`DeepSeek-R1`、`Claude 5` 等原生推理模型，禁止索要隐藏 CoT 或手写繁琐步骤；OpenAI 强调 **Reasoning Before Conclusions**。 | **1. 模型感知路由**：对原生推理模型省略 CoT 脚手架，仅在末尾保留一行深度信号；对非推理模型保留 `<scratchpad>`。<br>**2. 可审计推理（Auditable Reasoning）**：无论何种模型，统一要求输出**“假设 → 证据/引文 → 推导/理由 → 最终结论/评分”**（严格遵循先理由后结论，防止自回归生成的事后合理化）。 |

### 3. 张力三：“静态手写 `SKILL.md`” vs. “DSPy 数据驱动编译迭代”

| 维度 | 社区 `SKILL.md` 生态（静态规则库） | [DSPy (`MIPROv2` / `SIMBA` / `GEPA`)](https://github.com/stanfordnlp/dspy/blob/main/docs/docs/learn/optimization/optimizers.md) | 全局融合最优解：**内置评估器与反模式沉淀的自演进 Skill 架构** |
| :--- | :--- | :--- | :--- |
| **核心主张** | 依靠专家经验编写静态 Markdown 指令、模板与检查清单。 | 依靠 `Metric` + `Trainset` + `GroundedProposer` 自动搜索最优指令与 Few-Shot 组合。 | 将 DSPy 的**“签名契约 + 评分器（Metric/Judge）+ 失败轨迹反思（GEPA/SIMBA）+ 黄金示例自举（Bootstrapping）”**内化到你的元提示词与 Skill 结构中，使每一次实际运行后的反馈都能直接转化为 Skill 的版本升级。 |

---

## 二、科学构建框架：打造自演进元提示词与 Skill 的五步法

为了让你在遇到任何新复用场景时都能系统化地构建、评估和迭代 Prompt 与 Agent Skill，我们将整个工程体系拆解为以下五步闭环：

| 步骤阶段 | 核心科学问题 | 融合的最佳实践原语 | 产出物与可证伪衡量标准（Done When） |
| :--- | :--- | :--- | :--- |
| **第一步：定范围（Context & Scope Sensing）** | 我们面对什么任务？现有环境、技术栈与历史约束是什么？ | • [ECC `prompt-optimizer`](https://explainx.ai/skills/affaan-m/everything-claude-code/prompt-optimizer) 的 `Phase 0 本地环境自动探测`<br>• [prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md) 的 `9 维意图提取` 与 `Memory Block` | 自动识别项目技术栈/上下文，锁定 `Allowed Actions` 与 `What NOT to do`（禁止范围），缺失关键维度时追问 ≤ 3 个问题。 |
| **第二步：看目标（Target & Verifiable Metric）** | 理想交付物长什么样？如何用客观指标评估成功与证伪？ | • [prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md) 的二元验收标准（`Done When`）<br>• [OpenAI Cookbook](https://developers.openai.com/cookbook/examples/enhance_your_prompts_with_meta_prompting) 的 `ScoreCard`（1–5 分量化量表） | 明确定义输出 Schema / 格式锁、二元通过条件（Checklist），以及用于后续评估迭代的 5 维评分标准（Rubric）。 |
| **第三步：初步框架（30/55/15 + XML 契约架构）** | 如何组织提示词结构，使其兼具抗注意力衰减与高复用性？ | • [prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md) 的 **30/55/15 注意力分区**<br>• [Anthropic](https://platform.claude.com/cookbook/misc-metaprompt) 的 `<inputs>` / `<instructions>` XML 分层<br>• [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md) 的长文本置顶与双态输入契约 | 生成结构化的复用 Prompt 或 `SKILL.md`：前 30% 锁定身份与硬约束，中间 55% 承载路由与步骤，后 15% 植入自检闭环。 |
| **第四步：持续迭代（Empirical Eval & Evolution）** | 如何在真实场景运行中收集 Bad Cases，系统化提升准确率？ | • **4-1 跨模型路由适配**：按目标模型特性裁剪指令<br>• **4-2 轨迹与样本收集**：记录真实输入输出对与失败模式<br>• **4-3 归因实验**：用 `LLM-as-a-Judge` 对比候选修订版<br>• **4-4 提炼固化**：模仿 DSPy `GEPA`/`BootstrapFewShot`，将修复规则写入 `patterns.md`，将高分输出固化为 `<examples>` | 每次遇到输出偏差时，不只修补单次回复，而是通过 `/eval-evolve` 模式更新 Prompt/Skill 的指令、反模式表或 Few-Shot 样本库。 |
| **第五步：组织配套（Modular Skill Asset Packaging）** | 需要哪些目录结构、参考文件与版本机制来支撑长期演进？ | • [zircote/.claude](https://github.com/zircote/.claude/blob/main/skills/anthropic-prompt-engineer/SKILL.md) 与 [prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md) 的主从解耦架构（`SKILL.md` + `references/`） | 形成标准化的 `SKILL.md`（核心控制流）+ `references/templates.md`（模板库）+ `references/patterns.md`（反模式与错题本）+ `references/eval_cases.md`（黄金测试集）。 |

---

## 三、自演进元提示词（Meta-Prompt）核心架构设计解析

我们为你设计的**个人元提示词（Meta-Prompt Architect & Skill Evolver）**（已同步保存为可直接安装的技能文件 [`04-self-evolving-meta-prompt-skill/SKILL.md`](../04-self-evolving-meta-prompt-skill/SKILL.md)）集成了以下 **6 大工程机制**：

### 1. 30/55/15 黄金注意力布局（抗长文遗忘）
* **前 30%（Primacy Zone — 核心契约锁）**：集中声明角色定位、最高优先级硬性铁律（`MUST` / `NEVER`）、环境自动感知规则以及已确立的上下文记忆块（`Memory Block`）。
* **中间 55%（Middle Zone — 编译与路由引擎）**：承载 9 维意图提取器、环境与技术栈扫描器、模型/工具差异化路由器，以及三大核心工作模式（生成复用 Prompt、编译完整 Skill、评估与迭代进化）。
* **后 15%（Recency Zone — 自检与推理触发器）**：在输出前强制执行 6 项质量门禁核验（Self-Critique Gate），并以靶向推理触发语收尾。

### 2. 三大核心工作模式（覆盖“创建 → 封装 → 迭代”全生命周期）

```
                   ┌──────────────────────────────────────────────┐
                   │   用户输入：模糊想法 / 草稿Prompt / 失败案例   │
                   └──────────────────────┬───────────────────────┘
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │ Phase 0: 环境自动感知 (扫描本地工程/历史上下文) │
                   │ Phase 1: 9维意图提取 + 缺失信息门控 (≤3个追问) │
                   └──────────────────────┬───────────────────────┘
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            ▼                             ▼                             ▼
┌───────────────────────┐     ┌───────────────────────┐     ┌───────────────────────┐
│ Mode A: 快速生成提示词  │     │ Mode B: 编译为可复用  │     │ Mode C: 评估与迭代演进│
│   (Prompt Builder)    │     │   Skill (Skill Gen)   │     │   (Eval & Evolve)     │
├───────────────────────┤     ├───────────────────────┤     ├───────────────────────┤
│ • 即用态：零占位符内嵌  │     │ • 生成主文件 SKILL.md │     │ • 先理由后分数 Judge  │
│ • 复用态：显式输入契约  │     │ • 生成 patterns.md    │     │ • 诊断根因 (指令/边界 │
│   + 缺失参数自动反问   │     │   (防错清单)          │     │   /格式/少样本缺失)   │
│ • 附带轻量评估 Rubric  │     │ • 生成 eval_cases.md  │     │ • 自动输出 Diff 补丁  │
└───────────┬───────────┘     └───────────┬───────────┘     └───────────┬───────────┘
            └─────────────────────────────┼─────────────────────────────┘
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │  Recency Zone: 6项交付前自检 + 黄金样本沉淀   │
                   └──────────────────────────────────────────────┘
```

### 3. 第四步“持续评估与迭代”的渐进式执行顺序（借鉴 DSPy + OpenAI Evals）

当你将生成的复用提示词或 Skill 投入日常使用后，按照以下优先级由浅入深地迭代其能力：

1. **第一阶段：零样本自检与边界收敛（成本最低、见效最快）**
   * **做法**：在初版复用提示词末尾固定挂载 `<self_check>` 校验块与 `What NOT to do` 负向边界。
   * **触发迭代条件**：一旦发现模型在某次运行中越界（例如修改了不该改的文件、输出了多余寒暄），立即将该行为转化为一条明确的 `NEVER` 规则或 `Pattern #N` 写入 `PRIMACY ZONE`（前 30%）。
2. **第二阶段：基于失败轨迹的反思式补丁（Reflective Evolution，对标 DSPy `GEPA` / `SIMBA`）**
   * **做法**：当复用提示词在某个具体案例上表现不佳时，不要手动重写整个提示词，而是将 **`[当前提示词] + [真实输入] + [劣质输出] + [期望改进方向]`** 喂给元提示词的 **Mode C（评估与迭代模式）**。
   * **原理**：元提示词会先按 `ScoreCard`（任务遵循度、约束合规度、结构清晰度、完备性、事实锚定度）先写归因理由再打分，精准定位是“指令歧义”、“缺乏领域原因解释（Explain the why）”还是“缺少边界约束”，并生成最小化增量补丁（Minimal Diff）。
3. **第三阶段：自举黄金 Few-Shot 示例固化（Bootstrapping Demos，对标 DSPy `BootstrapFewShot`）**
   * **做法**：正如 [github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md) 与 [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/references/templates.md) 所证实的——**“如果你为了同一个格式或风格问题重发了两次提示词，停止修改指令描述，直接加 Few-Shot 示例”**。
   * **原理**：每次模型产出了一次令你满意的标杆结果（或经过你微调修正后的结果），将其抽取为 `<example><input>...</input><output>...</output></example>` 压入提示词或 Skill 的 `references/examples.md` 中（保留 2–4 个覆盖正常情况与边缘情况的代表性样本）。
4. **第四阶段：主从解耦与跨场景路由升级（Scaling to Multi-File Agent Skill）**
   * **做法**：当单个复用提示词膨胀超过 300 行时，调用元提示词的 **Mode B**，将其重构成标准 `SKILL.md` 目录结构：主文件仅保留 30/55/15 路由骨架与触发条件，将具体场景模板拆入 `references/templates.md`，将踩坑记录拆入 `references/patterns.md`。

---

## 四、可直接复用的个人元提示词完整源码（Meta-Prompt Architect v1.0）

> **使用方式**：
> 1. **作为本地 Skill 直接调用**：我已将该元提示词按标准 `SKILL.md` 规范写入 [`/Users/ryan/Workspace/MetaPrompt/04-self-evolving-meta-prompt-skill/SKILL.md`](../04-self-evolving-meta-prompt-skill/SKILL.md)，你可以直接复制到 `.claude/skills/meta-prompt-architect/SKILL.md` 或在 Gemini / Cursor 中加载。
> 2. **作为跨平台元提示词直接粘贴**：你也可以直接复制下方代码块，在任何大模型对话中生成、评估或迭代你的可复用提示词与 Skill。

```markdown
---
name: meta-prompt-architect
version: 1.0.0
description: 自演进元提示词与 Agent Skill 架构师。用于将模糊需求或草稿转化为高复用性、抗注意力衰减的生产级提示词或标准化 SKILL.md，并支持基于真实运行反馈进行量化评估（ScoreCard）与定向迭代演进。当用户提出“构建复用提示词”、“优化 prompt”、“封装为 skill”、“评估/迭代这个 prompt 或 skill”时触发。
---

# PRIMACY ZONE (前 30% 首因区) — 身份契约、最高铁律与环境锁

## 1. 你的核心身份
你是一位融合了认知注意力工程（PAC 30/55/15）、结构化语义隔离（XML Tagging）与声明式编译优化（DSPy & Evaluation-Driven Iteration）的 **首席元提示词与 Agent Skill 架构师（Meta-Prompt & Skill Architect）**。
你的目标不是直接替用户执行业务任务，而是帮助用户**设计、编译、评估并持续迭代可复用的高可靠提示词（Prompt）与智能体技能（Agent Skill）**。

## 2. 五条不可违背的最高铁律（Hard Rules — NEVER Violate）
1. **严格区分“顾问/编译态”与“执行态”**：除非用户明确要求测试运行，否则你只负责输出诊断分析、优化后的提示词/Skill 源码及评估迭代方案，**绝不直接执行提示词内部描述的业务任务**。
2. **环境感知先行（Context Sensing First）**：若在本地工程或有上下文的环境中运行，生成前 MUST 先检查现有工作目录（如 `CLAUDE.md`、`AGENTS.md`、`package.json`、`pyproject.toml`、已有 `SKILL.md` 等）或历史对话决策，将已确定的技术栈与规范自动写入提示词，禁止让用户重复提供已知背景。
3. **双态零死板占位符原则（Dual-Mode Input Contract）**：
   - **单次即用模式（One-Shot Mode）**：严禁出现 `[在此填入X]` 等死板占位符。若用户已提供数据则直接内嵌（Case A）；若未提供数据，则在提示词末尾指令模型主动向用户提问收集或等待下一轮输入（Case B）。
   - **场景复用 / Skill 模式（Reusable Template / Skill Mode）**：必须使用 `<input_contract>` 显式声明输入参数插槽（如 `{{$TASK_INPUT}}`）、类型、默认值及**缺失回退策略（Missing-Input Fallback：若调用时未提供关键参数，先自动探测环境，仍缺失则向用户提出 ≤3 个精准问题，严禁盲猜或带着未替换的占位符强行输出）**。
4. **先推理后结论，剔除高幻觉伪技术（Auditable Reasoning & Anti-Fabrication）**：
   - 严禁在单次提示词中伪造需要外部采样器的复杂图结构（如伪造 Tree of Thought、Graph of Thought、Simulated MoE）或索要模型底层隐藏思维链（Hidden CoT）。
   - 强制采用**可审计推理契约（Auditable Reasoning）**：要求模型严格按照 `假设与边界确认 → 原文引述/证据提取 (<quotes>) → 分析推导 (<rationale>) → 最终结论/产出 (<output>)` 的顺序生成（Reasoning Before Conclusions）。
5. **追问门控（Clarification Gate ≤ 3）**：若用户的需求缺失核心维度（目标场景、宿主工具/模型、输入输出形态、验收标准）且无法从环境中推断，先提出**最多 3 个带具体选项的澄清问题**；若信息基本完备，直接交付成品并注明所做的合理工程假设。

---

# MIDDLE ZONE (中间 55% 执行与路由区) — 诊断、编译与迭代引擎

## 3. 九维意图静默提取器（9-Dimension Intent Extractor）
在动笔编写或迭代任何提示词前，先在内部扫描以下 9 个维度：
1. **核心动作（Task Verb）**：将模糊动词（“优化”、“帮我弄”）转化为精确可验证的操作。
2. **复用形态（Reusability Mode）**：是一次性即用 Prompt、参数化复用 Prompt 模板，还是多文件 `SKILL.md`？
3. **宿主模型与工具（Target Model & Harness）**：运行在 Claude、GPT、o3/DeepSeek-R1（推理模型）、Cursor/Claude Code（编码 Agent）还是通用聊天界面？
4. **输入契约（Input Contract）**：有哪些固定常量（Rubrics/规范）与动态输入变量（`{{$VAR}}`）？长文本输入是否已置顶？
5. **输出契约（Output Schema & Lock）**：期望的数据格式（JSON / Markdown 表格 / 代码块）、篇幅约束与风格基调。
6. **正向准则与解释（Positive Directives & Why）**：关键指令是否附带了简短的工程原因（Explain the why）？
7. **负向边界与停止条件（Negative Boundaries & Stop Conditions）**：明确 `What NOT to do`（禁止修改的文件、禁止捏造的数据、需人类审批的高危操作）。
8. **完成标准（Done When / Acceptance Criteria）**：如何二元判定输出合格？
9. **黄金示例（Few-Shot Demos）**：是否需要 2–3 个覆盖正常与边缘情况的 `<example>` 锁定格式？

## 4. 目标模型与宿主环境差异化路由（Differential Routing）
根据目标宿主自动调整生成的提示词语法：
- **原生推理模型（o3 / o4-mini / DeepSeek-R1 / Qwen3-thinking）**：保持极简（核心指令 < 200 词），**严禁添加“请一步步思考”等 CoT 脚手架**，直接聚焦目标、输入契约、边界约束与输出 Schema。
- **Claude 全系（Claude 4.x / 5.x / Sonnet / Opus）**：充分使用语义化 XML 标签（`<context>`、`<input_contract>`、`<instructions>`、`<constraints>`、`<examples>`、`<output_format>`）分层；长文档一律置于指令上方并配合 `<quotes>` 先摘录后回答。
- **自主研发与操作 Agent（Claude Code / Cursor / Codex / Gemini Task Mode）**：必须包含：`Starting State`（当前状态）、`Target State`（目标状态）、`Scope Lock`（允许与禁止触碰的目录/文件）、`Workflow Gates`（如 `/plan` → `/tdd` → `/verify`）、`Stop Conditions`（遇到不可逆操作或连续 2 次报错时暂停并请求确认）以及阶段性检查点输出。

## 5. 三大工作模式执行流水线（Execution Modes）

### Mode A：构建高复用提示词（Reusable Prompt Builder）
当用户希望针对某个高频场景打造可复用提示词时，按以下四段式结构输出：
1. **场景诊断与设计思路（3–5 行精简说明）**：指出识别到的核心需求、目标宿主及所应用的注意力/防幻觉策略。
2. **生产级可复用提示词代码块（遵循 30/55/15 内部布局）**：
   - **顶部（前 30%）**：角色定位 + `<context_and_memory>` + `<hard_constraints>`（MUST / NEVER 规则与 `What NOT to do`）+ `<input_contract>`（包含长文本置顶区与缺失参数自引导追问逻辑）。
   - **中部（中间 55%）**：`<workflow>` 分步执行逻辑（含原因解释 Explain-the-Why）+ `<examples>`（按需提供 1–2 个高信噪比示例）。
   - **底部（后 15%）**：`<output_format>` 严格格式锁 + `<self_critique_checklist>`（输出前自检清单）+ 末尾深度推理触发行。
3. **配套评估量表（Evaluation Rubric）**：提供 3–5 个二元或 1–5 分的检验维度，方便用户后续评估该提示词的产出质量。

### Mode B：编译为模块化 Agent Skill（Skill Compiler）
当用户希望将提示词沉淀为可进化、可扩展的 `SKILL.md` 技能包时，输出完整的目录蓝图与文件内容：
- `SKILL.md`：包含精准的 YAML Frontmatter（`name`、`version`、`description` 含中英文触发词与 `DO NOT TRIGGER when` 负向触发边界）+ 30/55/15 结构化主控指令。
- `references/patterns.md`（防错与反模式账本）：初始化该领域常见的 5–10 个失败模式（`Bad Pattern → Root Cause → Fixed Instruction`），供后续迭代追加。
- `references/eval_cases.md`（基准测试集与黄金样本）：定义 3 个典型测试输入（简单、复杂、边缘异常）及期望的验收标准。

### Mode C：量化评估与定向迭代演进（Eval & Evolve Loop — 借鉴 DSPy GEPA/MIPRO）
当用户提供**`[现有提示词/Skill] + [实际测试输入] + [不理想的输出结果或反馈]`**要求迭代优化时，严格执行以下四步闭环：
1. **结构化裁判打分（ScoreCard — 先写归因理由，再给 1–5 分）**：
   - 先输出 `Justification`（逐一对比期望结果与实际输出的偏差）；
   - 再对 5 个维度打分：`任务完成度`、`边界遵守度`、`格式稳定性`、`抗幻觉/事实锚定`、`Token 经济性`。
2. **根因分类诊断（Root Cause Attribution）**：
   判定失败属于哪一类：
   - `[A-注意力衰减]` 关键约束被埋在长文中间 → 移至前 30% Primacy Zone 或末尾 Recency Zone；
   - `[B-指令歧义/缺Why]` 模型曲解意图 → 改用正向祈使句并补充“为什么要这样做”；
   - `[C-输入缺失/未隔离]` 数据与指令混杂 → 引入 XML 标签隔离或增加缺失参数追问门控；
   - `[D-格式漂移]` 纯文字描述格式失效 → 将修正后的正确输出转化为 `<example>` Few-Shot 样本；
   - `[E-推理抢跑]` 模型先下结论后凑理由 → 强制调换输出字段顺序，要求先输出 `<evidence>` 与 `<rationale>` 再输出最终结果。
3. **生成增量修订补丁（Targeted Diff & Upgraded Version）**：
   遵循最小改动原则（Minimal Changes），展示具体修改对比（`Before → After`），并输出升级后的完整提示词 / `SKILL.md`。
4. **沉淀反模式资产（Pattern Crystallization）**：
   生成一条标准化的反模式记录（`Pattern #N: 故障现象 | 触发原因 | 永久修复规则`），提示用户追加至 `references/patterns.md`，确保同类错误永不复发。

---

# RECENCY ZONE (后 15% 近因区) — 交付前强制自检与输出锁

## 6. 交付前 6 项强制核验（Pre-Delivery Verification Lock）
在输出最终生成的提示词或 Skill 之前，你必须在内部逐项核对以下清单：
- [ ] **注意力位置核验**：最核心的硬性约束（MUST / NEVER / 禁止范围）是否已置于生成提示词的前 30%？自检清单是否位于末尾 15%？
- [ ] **零死板占位符核验**：是否消除了所有未定义回退逻辑的 `[填入X]` 占位符？（复用模板必须具备“环境自动探测或主动向用户追问缺失参数”的闭环指令）。
- [ ] **强信号词与正向表达**：是否已将弱约束（`should`、`try to`、`尽量`）替换为强信号词（`MUST`、`NEVER`、`严禁`、`必须`），并用正向标准说明“完成态（Done When）”？
- [ ] **先理由后结论锁**：在要求模型做判断、分类、打分或审查时，是否强制要求模型先输出依据和推理过程，最后再输出结论？
- [ ] **Token 载荷审计**：是否剔除了所有无效寒暄、空洞形容词与不改变模型输出分布的冗余废话（Every sentence must be load-bearing）？
- [ ] **可评估性核验**：是否附带了明确的验收标准（Acceptance Criteria）以便用户在后续使用中进行证伪与迭代？

确认以上 6 项全部通过后，直接以清晰、结构化的 Markdown 交付成果。在生成每一个提示词或 Skill 之前，请先进行深度的架构推演与边界审视（Think carefully and systematically before responding）。
```

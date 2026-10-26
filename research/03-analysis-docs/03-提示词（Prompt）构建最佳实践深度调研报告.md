# 提示词（Prompt）构建最佳实践深度调研报告
## ——构建高质量 AI 技能（Agent Skill）与智能体指令的核心骨架

> **报告定位**：如果将智能体技能（Agent Skill）比作一个完整的专业工程模块，那么**提示词（Prompt）就是支撑该模块的底层逻辑骨架**。本报告基于对 [affaan-m/everything-claude-code](https://explainx.ai/skills/affaan-m/everything-claude-code/prompt-optimizer)、[nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md)、[zircote/.claude](https://github.com/zircote/.claude/blob/main/skills/anthropic-prompt-engineer/SKILL.md)、[github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md)、[Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt)、[OpenAI Meta-Prompt](https://developers.openai.com/api/docs/guides/prompt-generation) 及 [DSPy (`stanfordnlp/dspy`)](https://github.com/stanfordnlp/dspy/blob/main/dspy/teleprompt/mipro_optimizer_v2.py) 的源码级调研，系统提炼出当前业界在构建高可靠、可复用、抗衰减提示词时的 **五大核心工程支柱与最佳实践**。

---

## 一、提示词工程的范式演进：从“玄学咒语”到“结构化契约骨架”

早期的提示词设计往往停留在“你是一个拥有 20 年经验的 XX 专家，请深呼吸并一步步思考”这类表面修辞上。随着大模型指令遵循与原生推理能力的跃升，主流提示词最佳实践已全面转向 **确定性上下文工程（Deterministic Context Engineering）**：

| 演进维度 | 旧范式（经验修辞型 Prompt） | 当前主流最佳实践（结构化契约型 Prompt 骨架） | 代表工程来源 |
| :--- | :--- | :--- | :--- |
| **背景获取** | 盲目套用“你是XX专家”角色模板，假设模型已知晓项目上下文 | **环境感知先行（Context Sensing First）**：先自动读取本地配置/代码规范，缺失关键维度时主动追问（≤3 问） | [ECC `prompt-optimizer`](https://explainx.ai/skills/affaan-m/everything-claude-code/prompt-optimizer) |
| **空间布局** | 指令、背景、要求随机堆砌在一段长文字中 | **30/55/15 注意力分区 + 长输入置顶**：前 30% 锁死硬约束与记忆，长文档置顶，末尾 15% 放自检与问题 | [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md)、[awesome-copilot](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md) |
| **层次隔离** | 纯自然语言混写，容易引发指令污染（Instruction Bleed） | **语义化 XML 标签隔离**：用 `<context>`、`<instructions>`、`<examples>`、`<quotes>` 物理隔离指令与数据 | [Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt)、[zircote/.claude](https://github.com/zircote/.claude/blob/main/skills/anthropic-prompt-engineer/SKILL.md) |
| **占位符处理** | 留下大量 `[在此填入X]` 半成品模板，导致直接发送失效 | **双态输入契约**：即用态实行“零占位符（No Placeholders）”；复用态绑定“缺失参数自动追问回退” | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md)、[Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt) |
| **推理控制** | 无差别添加“一步步思考”，甚至伪造单次 ToT/MoE 多角色扮演 | **模型感知路由 + 先理由后结论**：推理模型（`o3`/`R1`）去 CoT 化；强制先输出证据与理由，最后输出结论/分数 | [OpenAI Meta-Prompt](https://developers.openai.com/api/docs/guides/prompt-generation)、[prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md) |
| **优化方式** | 人工凭感觉反复改词（Trial-and-Error） | **编程式签名契约 + 裁判闭环**：基于 `ScoreCard`（LLM-as-a-Judge）或 DSPy `MIPROv2` 数据驱动迭代 | [DSPy](https://github.com/stanfordnlp/dspy/blob/main/dspy/teleprompt/mipro_optimizer_v2.py)、[OpenAI Cookbook](https://developers.openai.com/cookbook/examples/enhance_your_prompts_with_meta_prompting) |

---

## 二、支柱一：空间与注意力架构最佳实践（对抗长上下文衰减）

大模型在处理长提示词时并非均匀分配注意力，而是呈现显著的 **U 型曲线效应（Lost in the Middle）**：模型对位于上下文开头（首因效应 Primacy）和结尾（近因效应 Recency）的信息召回率与遵循度最高，而对位于中间区域的信息遵循度明显下降（参考 [Level Up Coding 对 Prompt Master 注意力架构的剖析](https://levelup.gitconnected.com/prompt-master-claude-skill-any-ai-264e4949d2f3)）。

### 1. PAC 30/55/15 三段式位置注意力布局
在设计复杂提示词或 Skill 主文件骨架时，参照 [nidhinjs/prompt-master (`SKILL.md`)](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md) 的分区规范（本地存档见 [`01-community-skills/nidhinjs-prompt-master/SKILL.md`](../01-community-skills/nidhinjs-prompt-master/SKILL.md)）：
* **前 30% —— 首因区（PRIMACY ZONE：Identity, Hard Rules, Memory & Output Lock）**：
  * **核心任务与角色身份**：用一句话精准锚定专业视角与核心交付物。
  * **跨轮次记忆块（`Memory Block`）**：将前序对话或项目已确立的技术栈、架构决策与失败教训放在前 30%，防止模型在多轮交互中“失忆”或推翻已有共识。
  * **不可违背的硬性边界（Hard Rules）**：使用 `MUST` / `NEVER` 声明红线约束与 `What NOT to do`（禁止范围）。
* **中间 55% —— 执行与路由区（MIDDLE ZONE：Workflow, Routing & Reference Context）**：
  * 放置分步执行流程（Workflow Steps）、条件分支路由表、Few-Shot 示例（`<examples>`）以及领域参考资料。即使中间区域发生轻微注意力衰减，也不会破坏首尾锁定的全局契约。
* **后 15% —— 近因区（RECENCY ZONE：Output Format Lock, Self-Critique & Reasoning Trigger）**：
  * 放置严格的输出格式模板、交付前自检清单（Verification Lock）以及最后一行深度推理触发指令。

### 2. 长文本输入置顶法则（Long Inputs on Top, Question on Bottom）
* **工程原理**：[github/awesome-copilot (`prompt-optimizer`)](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md) 与 [Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt) 均在源码中强调：**当提示词包含长文档、代码文件、会议转录或原始数据转储时，必须将长数据块置于提示词顶部（指令之前），而将具体的分析指令与问题置于长数据块下方**。
* **实证收益**：实证研究表明，在长上下文任务中采用“长数据在上、指令在下”的语序，相比“指令在上、长数据附后”可带来最高约 **30% 的输出质量提升**。

### 3. 语义化 XML 标签分层隔离（Structural Isolation）
* **工程原理**：当提示词同时混合了背景说明、外部输入数据、示范样本和输出要求时，纯 Markdown 标题容易在嵌套引用时发生边界模糊。
* **落地规范**（源自 [zircote/.claude (`anthropic-prompt-engineer`)](https://github.com/zircote/.claude/blob/main/skills/anthropic-prompt-engineer/SKILL.md) 与 [Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt)）：
  * 使用语义自解释的 XML 标签包裹不同性质的模块：`<context>`、`<input_data>`、`<instructions>`、`<constraints>`、`<examples>`、`<output_format>`。
  * **按复杂度弹性启用**：对于简单的一句话任务无需过度包装；一旦模块超过 3 个或包含外部不可信输入（防 Prompt Injection），强制启用 XML 闭合标签。

---

## 三、支柱二：输入契约与上下文感知最佳实践（消灭无效交互）

### 1. 环境上下文自动感知（Phase 0 Context Auto-Detection）
* **反模式**：每次生成代码或工程方案时，提示词只写一句“请按最佳实践编写”，导致模型生成与当前仓库完全不兼容的框架代码。
* **最佳实践**（源自 [affaan-m/everything-claude-code (`prompt-optimizer`)](https://explainx.ai/skills/affaan-m/everything-claude-code/prompt-optimizer)，本地存档见 [`01-community-skills/affaan-m-everything-claude-code/prompt-optimizer/SKILL.md`](../01-community-skills/affaan-m-everything-claude-code/prompt-optimizer/SKILL.md)）：
  * 在提示词或 Skill 的第一步植入 **环境探测指令**：先读取工作目录中的项目规范文件（如 `CLAUDE.md`、`AGENTS.md`）与依赖配置（`package.json`、`pyproject.toml`、`go.mod`、`Cargo.toml`、`pom.xml`），自动锁定语言版本、路由规范、校验库（如 Zod/Pydantic）及测试框架，无需用户手动复述。

### 2. 九维意图静默提取与追问门控（9-Dimension Intent Extraction & Max-3 Question Gate）
* 综合 [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md) 与 [affaan-m/everything-claude-code](https://explainx.ai/skills/affaan-m/everything-claude-code/prompt-optimizer)，一个完备的提示词骨架必须覆盖以下 **9 个核心要素**：
  1. **Task（精确动作）**：用具体操作动词（如 `Refactor`、`Extract`、`Benchmark`）替代模糊词（“帮我看看”、“优化一下”）。
  2. **Target Tool / Model（目标宿主）**：明确运行在哪个模型或 Agent 工具上。
  3. **Input Contract（输入源与边界）**：随附的文档、代码路径或变量。
  4. **Context & Memory（项目背景与历史决策）**：已有架构约束与踩坑记录。
  5. **Audience（受众画像）**：输出给谁看（决定专业术语密度与语调）。
  6. **Scope & Negative Boundaries（范围锁与禁止项）**：明确只改哪些文件、**严禁触碰哪些内容（What NOT to do）**。
  7. **Output Format（输出格式锁）**：明确 JSON Schema、Markdown 表格列定义或字数上限。
  8. **Success Criteria（二元完成标准 `Done When`）**：客观可检验的完成条件。
  9. **Few-Shot Examples（模式示范）**：用于锁定复杂格式或文风的 2–4 个样本。
* **追问门控法则**：当用户初始输入缺失关键维度且无法从本地环境自动探测时，**最多向用户提出 3 个高信息密度的澄清问题**；对于非核心细节，直接做出最合理的工程默认假设并在输出中显式声明。

### 3. “零占位符”与“参数化复用插槽”的双态法则
* **即用态提示词（Chat One-Shot Prompt）**：严格遵循 [github/awesome-copilot (`prompt-optimizer`)](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md) 的 **Rule 1（No Placeholders. Ever.）** 与 **Rule 2（Case A / Case B 分流）**：
  * **Case A（用户已提供数据）**：直接把数据烘焙进提示词代码块内。
  * **Case B（用户未提供数据，只描述了任务类）**：绝不留 `[请在此粘贴文本]`，而是将提示词写为自带交互收集逻辑的完备指令（如在末尾写明：`"在开始撰写前，请先向我询问以下 3 项信息：1... 2... 3..."` 或 `"准备就绪后，请提示我粘贴待处理的邮件列表"`）。
* **复用态模板 / API System Prompt**：遵循 [Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt) 与 [DSPy `Signature`](https://github.com/stanfordnlp/dspy/blob/main/dspy/signatures/signature.py) 的契约设计，提取最小非重叠输入变量集（`{$VAR}`），同时为每个变量定义缺失时的回退追问机制。

---

## 四、支柱三：推理控制、强信号约束与防幻觉最佳实践

### 1. “先推理/引述，后结论/打分”铁律（Reasoning Before Conclusions & Quote-First Grounding）
* **底层机理**：大语言模型是自回归（Autoregressive）生成模型，后生成的 Token 严格受制于先生成的 Token。如果提示词要求模型先给出“结论”、“分类标签”或“评分（1–5分）”，再给出“理由”，模型后续生成的理由就会退化为为第一个 Token 辩护的“事后合理化（Post-hoc Rationalization）”，大幅降低准确率。
* **两大落地规范**：
  1. **逆转结论顺序**（源自 [OpenAI Meta-Prompt](https://developers.openai.com/api/docs/guides/prompt-generation)，本地存档见 [`02-official-and-frameworks/openai-meta-prompt/openai_meta_prompt.py`](../02-official-and-frameworks/openai-meta-prompt/openai_meta_prompt.py)）：无论是在输出格式定义、Few-Shot 示例还是 Pydantic 结构化 Schema 中，**必须强制将 `justification` / `reasoning` / `evidence` 字段排在 `conclusion` / `score` / `label` 字段之前**（`NEVER START EXAMPLES WITH CONCLUSIONS! REVERSE the order!`）。
  2. **先摘录原文再作答**（源自 [Anthropic Metaprompt](https://platform.claude.com/cookbook/misc-metaprompt) 与 [github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md)）：针对长文档问答或事实核查任务，强制要求模型第一步先在 `<quotes>` 标签内逐字摘录原文相关段落并编号，第二步再严格基于已摘录的引文生成回答；若不确定则明确标注 `[uncertain]`，从物理机制上阻断幻觉。

### 2. 跨模型推理路由与“伪高级技巧”封禁
* **推理模型 vs. 通用模型路由**（源自 [nidhinjs/prompt-master](https://github.com/nidhinjs/prompt-master/blob/main/SKILL.md)）：
  * **原生推理模型（`o3`、`o4-mini`、`DeepSeek-R1`、`Qwen3-thinking`）**：已在底层推理阶段消耗数千内部思考 Token，**严禁在提示词中添加 `"Think step by step"` 或繁琐的思维链脚手架**（这会干扰模型原生推理路径并劣化结果），保持指令简短直接（<200 词），仅声明目标、边界与验收标准。
  * **自适应思考与常规指令模型（Claude 4.x/5.x、GPT-5.x、Gemini）**：无需索要底层隐藏思维链（Hidden CoT），而是采用 **可审计推理契约（Template E — Auditable Reasoning）**，要求输出：1. 结论；2. 核心假设；3. 可供审计的证据或中间计算结果；4. 已执行的校验项；5. 剩余不确定性。
* **封禁单次前向推理中的高幻觉伪框架**：在单条提示词中禁止使用模拟多专家角色扮演（Simulated MoE）、无外部搜索引擎的思维树/思维图（ToT / GoT）以及无独立采样通道的自洽性投票（USC），因为单次自回归生成无法真正实现并行独立分支，只会诱导模型编造虚假的讨论过程。

### 3. 正向祈使、强信号词与“解释原因（Explain the Why）”
* **正向表达优于负向堆砌**（Positive Framing）：告诉模型“应该写成什么样”（如 `"Write in flowing prose paragraphs"`）远比只说“不要做什么”（`"Don't use bullet points"`）更有效。
* **解释规则背后的工程原因（Explain the Why）**：[github/awesome-copilot](https://github.com/github/awesome-copilot/blob/main/skills/prompt-optimizer/SKILL.md) 与 [Anthropic `skill-creator`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) 均强调，与其机械堆砌满篇大写的 `ALWAYS/NEVER`，不如用一句话讲清楚原因（例如：`"请勿使用省略号，因为输出文本将直接交由 TTS 语音引擎朗读，省略号会导致发音异常"`）。理解了目的的模型在面对未预见的边缘情况时具备更强的泛化判断力。
* **关键红线保留强信号词与停止条件**：在涉及安全边界、文件修改范围（`Scope Lock`）与高危操作时，精准使用 `MUST` / `NEVER` 及显式停止条件（`"Stop and ask before: deleting any file, adding any dependency, or modifying database schemas"`）。

---

## 五、支柱四：自检闭环与高频反模式清洗（Self-Critique & Anti-Patterns）

### 1. 植入末尾轻量级自检闭环（Recency Zone Self-Check）
在提示词末尾（最后 15% 近因区）植入 3–5 项针对性核验指令（`"Before finalizing your response, verify your output against the following criteria..."`），并在最后一行附上与模型匹配的推理深度触发语（如 `"Take time to think through this carefully before responding."`）。

### 2. 高频 Token 杀手反模式速查表（精选自 [Prompt Master 37 Patterns](https://github.com/nidhinjs/prompt-master/blob/main/references/patterns.md)）
详细 37 项完整清单已归档于本地 [`01-community-skills/nidhinjs-prompt-master/references/patterns.md`](../01-community-skills/nidhinjs-prompt-master/references/patterns.md)，以下为最核心的 6 类典型反模式修复对照：

| 故障类别 | 典型坏提示词模式（Bad Pattern） | 最佳实践修复方案（Engineered Fix） |
| :--- | :--- | :--- |
| **任务粘连** | `"解释这段代码并帮我重构它"`（一提示词多任务） | 拆分为独立序列：Prompt 1 负责诊断与解释；Prompt 2 基于确认的方案执行重构 |
| **情绪化描述** | `"登录全坏了，快帮我全部修好"` | 转化为精确技术故障描述：`"当 user 为 null 时第 43 行抛出未捕获的 TypeError，请修复空值处理"` |
| **缺乏完成标准** | `"把这个函数改得更好一点"` | 注入二元可验证 `Done When`：`"当函数通过现有单元测试且在输入 null 时不抛异常即视为完成"` |
| **美学形容词空泛** | `"做一个看起来专业、现代的落地页"` | 转化为可测量的设计Token：`"黑白单色系（背景 #ffffff，主文字 #1a1a1a），Inter 字体，基础间距 8px，卡片圆角 6px"` |
| **IDE 范围失控** | 在 Cursor/Claude Code 中直接说 `"更新登录函数"` | 锁定文件与函数锚点（Template G）：`"仅修改 src/pages/Login.tsx 中的 handleLogin()，严禁触碰其他文件"` |
| **审查过滤过早** | `"帮我找出代码里的重要 Bug"`（模型会自行漏报） | 明确发现阶段目标是**全覆盖而非过滤（Coverage over Filtering）**：`"报告所有潜在问题（含低严重度与不确定项），并标注 Confidence 与 Severity 供下游筛选"` |

---

## 六、支柱五：从静态提示词到编程式编译与量化评估（DSPy & Evals）

当提示词作为复用资产或 Skill 骨架长期演进时，需引入 [OpenAI Meta-Prompting Cookbook](https://developers.openai.com/cookbook/examples/enhance_your_prompts_with_meta_prompting) 与 [DSPy (`MIPROv2`)](https://github.com/stanfordnlp/dspy/blob/main/dspy/teleprompt/mipro_optimizer_v2.py) 的工程化方法论（本地源码见 [`02-official-and-frameworks/`](../02-official-and-frameworks/)）：

1. **声明式签名抽象（Declarative Signatures）**：借鉴 [`dspy/signatures/signature.py`](../02-official-and-frameworks/dspy/signature.py)，将提示词中“不可变的输入/输出类型契约（InputField / OutputField）”与“可调优的自然语言指令（Instructions）及示例（Demos）”解耦。
2. **四维接地指令提案（Grounded Instruction Proposal）**：在迭代优化提示词时，效仿 DSPy `GroundedProposer`，同时结合 **全局流水线结构（Program-Aware）、真实测试集分布摘要（Data-Aware）、成功运行的轨迹示范（Few-Shot-Aware）与多样化提示技巧（Tip-Aware）** 生成候选修订版。
3. **如果你为同一个格式问题重发了两次提示词，停止改写描述，直接加 Few-Shot 示例**：对于复杂的输出格式或微妙的文风，2–4 个包裹在 `<examples>` 中的高质量正反例远胜千言万语的规则描述。

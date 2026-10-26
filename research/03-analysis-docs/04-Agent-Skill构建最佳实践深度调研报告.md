# 智能体技能（Agent Skill）构建最佳实践深度调研报告
## ——从“静态提示词骨架”到“模块化、可组合、自演进的智能体能力包”

> **报告定位**：如果说**提示词（Prompt）**定义了大模型单次推理的逻辑骨架（见姊妹篇 [`03-提示词（Prompt）构建最佳实践深度调研报告.md`](./03-提示词（Prompt）构建最佳实践深度调研报告.md)），那么**智能体技能（Agent Skill）**则是将这一骨架与**文件系统、按需加载机制（Progressive Disclosure）、确定性可执行脚本（`scripts/`）、领域知识库（`references/`）以及自动化评测闭环（`evals/`）**深度耦合的工程化能力单元。本报告基于对 [Anthropic 官方 Agent Skills 工程架构](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)、[Agent Skills 开放标准规范 (`agentskills.io`)](https://agentskills.io/specification)、[Claude Platform 技能编写最佳实践](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)、[Anthropic 官方 `skill-creator` 源码](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)、[Agent Skills 最佳实践指南](https://agentskills.io/skill-creation/best-practices) 以及 [OpenAI ChatGPT & Codex Skills 构建指南](https://learn.chatgpt.com/docs/build-skills) 的全面调研，系统总结出构建生产级 Agent Skill 的 **六大核心最佳实践**。

---

## 一、范式跃迁：为什么需要从 Prompt 升级为 Agent Skill？

在真实工程场景中，单靠长篇 System Prompt 会迅速遭遇三大瓶颈：**上下文窗口挤占（Context Bloating）**、**复杂流程遵循不稳定（Non-deterministic Execution）** 以及 **跨项目难以版本化复用**。以 [Anthropic 发布的 Agent Skills 开放标准](https://agentskills.io/home)（现已被 Claude Code、Claude.ai、[OpenAI ChatGPT & Codex](https://learn.chatgpt.com/docs/build-skills)、Cursor、GitHub Copilot、Gemini CLI、OpenHands 等 30+ 宿主广泛采纳）为代表，Skill 通过“基于文件系统的模块化目录”实现了对传统 Prompt 的全方位扩展：

| 对比维度 | 传统提示词（Prompt 骨架） | 智能体技能（Agent Skill / `SKILL.md` 体系） | 工程收益与本质跃迁 |
| :--- | :--- | :--- | :--- |
| **物理形态** | 单一段落或单个文本字符串 | 包含 `SKILL.md` + `scripts/` + `references/` + `assets/` + `evals/` 的标准文件夹 | 支持 Git 版本控制、团队共享、插件打包分发与模块化组装 |
| **上下文开销** | 无论当前对话是否用到，全量常驻 System Prompt，持续消耗 Token | **三级渐进式披露（Progressive Disclosure）**：启动仅加载 ~100 tokens 元数据，命中时才按需读取正文与子文档 | 可同时挂载数十甚至上百个专业技能而不挤占上下文窗口 |
| **确定性边界** | 所有计算、解析、校验均依赖大模型逐 Token 概率生成，易出错且昂贵 | **指令与确定性代码协同**：将脆弱的数据解析、格式校验、图表生成封装进 `scripts/`，由 Agent 调 Bash 执行 | 脚本源码无需进入上下文，仅将执行结果（stdout）返回给模型，兼具零幻觉与极低 Token 成本 |
| **知识承载上限** | 受限于单次 Prompt 长度与 U 型注意力衰减（超过数千词后急剧退化） | **近乎无限的领域知识挂载**：可将数万字的 API 规范、数据库 Schema 按域拆入 `references/`，按需精准检索 | 彻底打破单条提示词的信息容量上限 |
| **迭代演化方式** | 人工肉眼观察单次回复，凭感觉改词 | **评测驱动闭环（Eval-Driven Iteration）**：并发运行 `with_skill` vs `without_skill` 基准测试、断言打分与触发率优化 | 像迭代软件代码一样用量化指标（Pass Rate、Token Delta、Duration）持续升级 Agent 能力 |

---

## 二、核心架构支柱：三级渐进式披露（Three-Level Progressive Disclosure）

根据 [Claude Platform Agent Skills 架构文档](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) 与 [Agent Skills 格式规范](https://agentskills.io/specification)，编写 Skill 的第一性原理是**“将上下文窗口视为稀缺的公共资源（The context window is a public good）”**，严格按照以下三个层级组织信息：

```text
my-skill/
├── SKILL.md                # [Level 1 & Level 2] 必选：YAML 元数据 (~100 tokens) + 核心控制流指令 (<500 行)
├── scripts/                # [Level 3 - 确定性执行] 可选：Python/Bash/TS 脚本（仅执行拿结果，源码不占上下文）
│   ├── analyze_input.py
│   └── validate_output.py
├── references/             # [Level 3 - 按需知识库] 可选：细分领域文档、Schema、反模式库（用到哪个读哪个）
│   ├── patterns.md
│   ├── finance_schema.md
│   └── sales_schema.md
├── assets/                 # [Level 3 - 静态资产] 可选：输出模板、图标、字体、配置文件
│   └── report_template.md
└── evals/                  # [演进闭环] 可选：基准测试集与触发器评测集
    ├── evals.json
    └── trigger_queries.json
```

### 1. 三级加载机制与 Token 预算控制

| 加载层级 | 包含内容 | 加载时机 | Token 成本预算 | 核心设计规范 |
| :--- | :--- | :--- | :--- | :--- |
| **Level 1：元数据发现层（Metadata）** | `SKILL.md` 顶部的 YAML Frontmatter（`name` + `description`） | Agent 会话启动时全量预加载至系统提示词 | **~100 tokens / Skill**（[OpenAI Codex](https://learn.chatgpt.com/docs/build-skills) 默认限制初始技能列表总计 ≤ 上下文窗口的 2% 或 8,000 字符） | `description` 承担 100% 的隐式路由唤醒责任，必须把核心场景与触发词前置（Front-load）以防被宿主截断 |
| **Level 2：核心指令层（Instructions）** | `SKILL.md` 的 Markdown 正文（核心流程、Gotchas、导航索引） | 当用户请求命中 `description` 或用户通过 `/skill`、`$skill` 显式调用时 | **< 5,000 tokens（理想长度 < 500 行）** | 扮演“新员工入职手册总目录（Table of Contents）”，只放每次运行都必用的主干流程，切忌塞入大段参考手册 |
| **Level 3+：捆绑资源与脚本（Resources & Code）** | `references/` 文档、`scripts/` 可执行脚本、`assets/` 模板 | Agent 在执行 Level 2 指令过程中，根据条件分支按需读取或通过 Bash 调用 | **未访问时为 0 tokens**；读取单个 Reference 仅消耗该文件 Token；运行 Script **仅消耗 stdout 输出 Token** | 按业务域或条件分支拆分文件，并在 `SKILL.md` 中明确写出**何时（When to load）**加载哪个文件 |

### 2. 引用架构的两条铁律（源自 [Claude Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)）
* **铁律一：严禁深层嵌套引用，保持单层扁平直连（Keep References One Level Deep）**
  * **原理**：当 Agent 遇到 `SKILL.md → advanced.md → details.md` 的多层链式跳转时，往往会失去耐心或仅使用 `head -100` 截断预览，导致关键指令丢失。
  * **做法**：所有 `references/` 和 `scripts/` 文件必须**直接在 `SKILL.md` 一级正文中建立相对路径索引**，并附带明确的触发条件（例如：`"若 API 返回非 200 状态码，请读取 references/api-errors.md"`，而非笼统写 `"详见 references/ 目录"`）。
* **铁律二：长参考文件（>100–300 行）必须在顶部内置目录（Table of Contents）**
  * **原理**：当参考文件较长时，即使 Agent 先用局部读取工具预览前几十行，顶部的 `## Contents` 也能让 Agent 立即掌握全貌并精准跳转到所需章节（或使用 `grep` 检索）。

---

## 三、路由与触发器工程：如何让 Skill 精准唤醒且不误触？

[Agent Skills 官方指南](https://agentskills.io/skill-creation/optimizing-descriptions) 指出：**“一个技能只有在被激活时才能产生价值，而 `SKILL.md` Frontmatter 中的 `description` 字段承担了决定是否激活的全部重任。”**

### 1. Frontmatter 规范与命名准则（[Specification](https://agentskills.io/specification)）
* **`name` 字段（必选，≤64 字符）**：
  * 仅限小写字母、数字与单连字符（`a-z`、`0-9`、`-`），禁止大写、禁止首尾连字符或连续 `--`，且必须与父文件夹名称完全一致。
  * **命名风格推荐**：优先采用 **动名词形式（Gerund form：`processing-pdfs`、`analyzing-spreadsheets`、`optimizing-prompts`）** 或清晰的动作短语（`pdf-processing`），避免 `helper`、`utils`、`data` 等模糊名称。
* **`description` 字段（必选，≤1,024 字符，禁止包含 XML 标签）**：
  * **统一使用第三人称 + 祈使触发指导**：因为 `description` 会被直接注入系统提示词，切忌写 `"I can help you..."` 或 `"You can use this..."`，而应写成：`"Extracts text and tables from PDF files... Use this skill when..."`。
  * **聚焦用户意图而非内部实现**：描述用户想要达成什么目标，而不是技能内部用了什么算法。
  * **适度主动（Err on the side of being "pushy"）**：[Anthropic 官方 `skill-creator` 源码](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)（本地存档见 [`02-official-and-frameworks/anthropic-skill-creator/SKILL.md`](../02-official-and-frameworks/anthropic-skill-creator/SKILL.md)）明确披露，大模型默认存在 **低触发倾向（Under-triggering）**——即觉得自己用基础工具也能勉强应付而不去调用 Skill。因此，`description` 应当主动列举隐式场景（例如：`"即使用户没有明确提到 'CSV' 或 '数据分析'，只要涉及表格指标计算、生成图表或清洗脏数据，就务必调用此技能"`）。
  * **显式声明负向边界（`DO NOT TRIGGER when`）**：如 [affaan-m/everything-claude-code](https://explainx.ai/skills/affaan-m/everything-claude-code/prompt-optimizer) 与 [OpenAI Codex 指南](https://learn.chatgpt.com/docs/build-skills) 所示，对于容易与日常任务混淆的技能，必须在 `description` 末尾写明不触发场景（例如：`"DO NOT TRIGGER when: 用户要求直接执行代码或优化代码性能"`）。
* **跨平台扩展元数据**：
  * `compatibility`（可选，≤500 字符）：声明所需的系统依赖或网络权限（如 `Requires Python 3.12+, uv, and internet access`）。
  * `agents/openai.yaml`（[OpenAI Codex / ChatGPT 扩展](https://learn.chatgpt.com/docs/build-skills)）：支持配置 `allow_implicit_invocation: false`（关闭隐式触发，仅允许用户通过 `$skill` 或 `@skill` 显式调用）及绑定的 MCP Server 依赖。

### 2. 触发率量化评测与 60/40 防过拟合优化循环（[Optimizing Skill Descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)）
不要凭直觉猜测 `description` 是否有效，应当建立包含 **20 条真实感测试查询（Trigger Eval Set）** 的自动化测试闭环：
1. **构造 8–10 条正例（`should_trigger: true`）**：涵盖正式指令、口语化缩写/拼写错误、带有具体文件路径与职场背景的长句，特别是**未直接点出技能关键词但实质需要该技能的隐式请求**。
2. **构造 8–10 条高难度负例（`should_trigger: false` 的 Near-Misses）**：**切忌使用 `"写一个斐波那契函数"` 这种毫无词汇重叠的简单负例**。必须构造**近邻干扰项（Near-Misses）**——即共享了核心关键词但实际任务属于相邻领域的请求（例如针对“CSV 分析技能”，设计负例：`"帮我写个 Python 脚本把 CSV 逐行导入 Postgres 数据库"`——含 CSV 关键词，但属于数据库 ETL 而非数据分析）。
3. **多次采样计算触发率（Trigger Rate）**：由于模型采样具有随机性，每条 Query 至少独立运行 3 次，计算触发率（正例需 `> 0.5`，负例需 `< 0.5`）。
4. **60% 训练集 / 40% 验证集拆分（防止关键词过拟合）**：将 20 条 Query 按 6:4 固定拆分为 `train_queries.json` 与 `validation_queries.json`。仅根据训练集上的漏触（太窄）或误触（太宽）抽象调整 `description` 的概念边界（严禁直接把失败用例里的原词硬塞进 `description`），最多迭代 5 轮，最终以**验证集通过率最高**的版本为准。

---

## 四、正文与捆绑资源设计：如何编写高执行力、高鲁棒性的 Skill？

根据 [Best practices for skill creators (`agentskills.io`)](https://agentskills.io/skill-creation/best-practices)、[Using scripts in skills (`agentskills.io`)](https://agentskills.io/skill-creation/using-scripts) 与 [Claude Platform Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)，编写 `SKILL.md` 正文与脚本时应遵循以下 **四大核心准则与六大工程模式**：

### 1. 四大核心编写准则
1. **从真实实战与项目资产中萃取，拒绝让 LLM 凭空生成通用废话（Start from Real Expertise）**：
   * 让大模型在没有任何领域材料的空白状态下“帮我写一个 XX 技能”，只会产出“妥善处理异常”、“遵循安全最佳实践”等毫无价值的正确的废话。
   * **正确路径 A（从实战会话萃取）**：先与 Agent 在真实任务中完整跑通一次，将过程中**有效的步骤序列、你对 Agent 的人工纠偏（如“不要用库 Y，改用库 X”）、输入输出格式与特殊约束**提取固化为 Skill。
   * **正确路径 B（从项目存量资产合成）**：将团队真实的**故障复盘报告（Incident Reports）、运维手册（Runbooks）、API Schema、PR 审查高频评论与 Git 修复提交历史**喂给模型，提炼出真正贴合业务的 Skill。
2. **只补充模型不知道的增量信息，砍掉模型已知的常识（Add What the Agent Lacks, Omit What It Knows）**：
   * 动手写每一段话前先自问：**“如果没有这句话，Agent 会做错吗？”** 如果不会，坚决删掉（例如不要向模型科普“什么是 PDF”或“HTTP 状态码是什么”，直接告诉它“提取文本用 `pdfplumber`，扫描件回退到 `pdf2image + pytesseract`”）。
3. **匹配任务脆弱度校准控制自由度（Match Specificity to Fragility）**：
   * **高自由度（开放旷野——给启发式原则与为什么）**：适用于代码审查、调研分析等有多种合理路径的任务，重在解释背后的原因（Explain the why）。
   * **中自由度（预设轨道——给默认首选 + 逃生舱口 Provide Defaults, Not Menus）**：不要把 `pypdf`、`pdfplumber`、`PyMuPDF` 平铺成菜单让 Agent 纠结，直接指定一个默认首选（`Use pdfplumber`），仅在特殊情况（如 OCR）下指明替代方案。
   * **低自由度（悬崖窄桥——锁死精确命令与参数）**：适用于数据库迁移、打包发布、格式转换等一旦出错代价极高的脆弱操作，直接给出不可篡改的命令（`"Run exactly: python scripts/migrate.py --verify --backup. Do not modify flags."`）。
4. **教通用的解题程序，而非单次实例的声明（Favor Procedures over Declarations）**：
   * 不要写死仅适用于某一张表的查询语句，而是写明“先从 `references/schema.yaml` 读取表结构 → 按 `_id` 外键关联 → 应用过滤条件 → 聚合输出”的可泛化程序。

### 2. 六大高杠杆指令与脚本设计模式

| 模式名称 | 解决的痛点 | 落地实现规范与示例 |
| :--- | :--- | :--- |
| **1. Gotchas（反直觉踩坑专区）** | Agent 按常规假设行事导致在特定环境中反复踩坑 | 在 `SKILL.md` 醒目位置设立 `## Gotchas` 章节，专门记录违反直觉的事实（例如：`"- users 表采用软删除，所有查询必须带 WHERE deleted_at IS NULL"`、`"- 数据库里的 user_id、认证服务的 uid 和账单 API 的 accountId 指代同一个值"`）。**每次实际运行中人工纠正了一次错误，就立即追加一条 Gotcha。** |
| **2. Plan-Validate-Execute（规划-校验-执行三步锁）** | 批量操作或破坏性修改一旦执行难以回滚 | 要求 Agent 先生成结构化的中间计划文件（如 `field_values.json`），第二步调用校验脚本（`python scripts/validate.py schema.json field_values.json`）核对字段名、类型与必填项，**只有校验脚本返回通过后**才允许执行最终写入。 |
| **3. Checklists & Validation Loops（显式清单与验证闭环）** | 复杂多步工作流中 Agent 容易跳步或遗漏收尾验证 | 在 `SKILL.md` 中提供可复制的进度清单（`- [ ] Step 1...`），并强制植入循环：`执行修改 → 立即运行验证脚本或核对 STYLE_GUIDE.md → 若报错则修正并重跑验证 → 全部通过后方可交付`。 |
| **4. 轨迹驱动的脚本沉淀（Bundling Scripts from Transcripts）** | Agent 在每次运行时重复编写相同的辅助代码（浪费大量 Token 与时间） | 检查多次测试运行的完整轨迹（Transcripts）：如果发现 Agent 在 3 个测试用例中都各自现场写了一遍 `build_chart.py` 或 `parse_docx.py`，立即将其提炼为标准脚本放入 `scripts/`。 |
| **5. 内联依赖的自包含脚本（Self-Contained Scripts via PEP 723）** | 脚本依赖缺失或污染全局环境 | 根据 [Using scripts in skills](https://agentskills.io/skill-creation/using-scripts)，Python 脚本推荐使用 **PEP 723 内联元数据头**（`# /// script` + `dependencies = ["beautifulsoup4>=4.12,<5"]`）配合 `uv run scripts/extract.py` 执行；单次命令使用带精确版本号的 `uvx ruff@0.8.0` 或 `npx eslint@9.0.0`。 |
| **6. Agent 友好的脚本 CLI 契约（Agentic CLI Design）** | 脚本等待交互输入导致进程永久挂起、报错模糊或输出过大被截断 | 捆绑在 `scripts/` 中的代码必须满足：<br>• **严禁交互式提示（No TTY Prompts）**：全部通过命令行 Flag 或环境变量传参；<br>• **数据与诊断分离**：结构化数据（JSON/CSV）走 `stdout`，进度与警告日志走 `stderr`；<br>• **自解释报错与 `--help` / `--dry-run`**：报错时指明期望的枚举值（`Error: --format must be one of: json, csv. Received: "xml"`）；<br>• **防截断分页控制**：提供 `--offset` 或 `--output <file>` 参数，避免超出宿主 10–30K 字符截断阈值。 |

---

## 五、评测驱动的技能自演进闭环（Eval-Driven Skill Iteration）

结合 [Anthropic `skill-creator`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) 与 [Evaluating Skill Output Quality (`agentskills.io`)](https://agentskills.io/skill-creation/evaluating-skills)，一个成熟的 Skill 必须通过以下 **五步闭环工作流** 持续演进：

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. 设计测试集 (evals/evals.json)：2-3 个真实场景 Prompt + 边缘异常用例   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. 并发对照运行 (Clean Context)：同一 Turn 启动 with_skill vs baseline   │
│    • 新建技能对比 without_skill；升级技能对比 old_skill 快照             │
│    • 实时捕获 timing.json (total_tokens, duration_ms)                    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. 客观断言评分 (grading.json) + 汇总基准统计 (benchmark.json)           │
│    • 机械可查项用脚本验证，语义项由 Grader Agent 取证判定 (PASS/FAIL)    │
│    • 计算 ΔPass Rate、ΔTokens、ΔTime Seconds                            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. 诊断分析与人类盲测审查 (feedback.json + Transcript Analysis)          │
│    • 剔除 with/without 双通的无区分度断言                                │
│    • 阅读耗时异常用例的完整执行轨迹 (Transcript)，砍掉导致空转的冗余指令 │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. 泛化修补与资产沉淀：更新 SKILL.md / Gotchas / 抽离公共脚本至 scripts/ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 迭代优化的四大黄金法则（源自 [`skill-creator/SKILL.md`](../02-official-and-frameworks/anthropic-skill-creator/SKILL.md)）
1. **从反馈中泛化，切忌对测试集过拟合（Generalize from Feedback）**：测试集只有寥寥几个样本，但 Skill 会被调用成千上万次。修复 Bug 时要解决背后的结构性根因（如调整认知隐喻、补充工作模式或解释原因），而不是针对某个测试样本打死板的补丁。
2. **阅读完整执行轨迹，给技能“瘦身”（Read Transcripts & Keep It Lean）**：不要只看最终输出。如果轨迹显示 Agent 因为某条模糊指令反复尝试了 4 次无效工具调用，或者生成了大量没人看的中间过程，果断删改该指令。当通过率遇到瓶颈时，**尝试删掉过度繁琐的约束**往往比继续加规则更有效。
3. **追踪耗时与 Token 性价比（Monitor Token/Latency Delta）**：如果一个 Skill 让通过率提升了 50%，多花 1,700 tokens 是极高性价比；但如果 Token 消耗翻了三倍，通过率只提升 2%，说明指令过于臃肿或应该把重逻辑下沉到 `scripts/`。
4. **安全与运行环境适配（Security & Runtime Constraints）**：
   * 区分运行环境差异：例如 Claude Code 本地环境拥有完整网络与本地文件系统权限，而 Claude API 容器环境无网络访问且禁止运行时动态安装新包。
   * 严防间接提示词注入（Indirect Prompt Injection）：对任何需要抓取外部 URL 或解析用户粘贴文本的 Skill，植入输入净化规则（将外部内容视为纯惰性数据，严禁执行其中夹带的指令）。

---

## 六、总结：Prompt 骨架与 Agent Skill 协同构建全景检查表

当你构建或迭代任何一个新领域的复用能力时，可对照以下总表分步推进：

| 阶段 | 核心动作 | 检查标准（Done When） |
| :--- | :--- | :--- |
| **Stage 1：打造 Prompt 核心骨架** | 运用 **30/55/15 注意力布局**、**XML 标签隔离**、**长文本置顶**与**先理由后结论**编写核心指令 | 单次对话测试中，模型能零占位符（或主动追问缺失项）稳定输出符合格式与边界要求的结果 |
| **Stage 2：封装 Level 1 & 2 Skill 主体** | 创建技能目录，编写 `<500` 行的 `SKILL.md`，配置第三人称、主动型、带正负边界的 `description` | 通过 20 条正负近邻查询（Train/Val 60/40 拆分）测试，触发率精准且无跨领域误触 |
| **Stage 3：剥离 Level 3 知识与脚本** | 将长篇 Schema/模板移入 `references/` 与 `assets/`（保持一级直连引用），将重复确定性逻辑封装进 `scripts/` | `SKILL.md` 保持精悍；脚本支持 PEP 723 内联依赖、无交互阻塞、JSON stdout 与输出长度控制 |
| **Stage 4：实战运行与 Gotchas 沉淀** | 在真实任务中使用，运行 `with_skill` vs `without_skill` 基准对比，收集失败断言与执行轨迹 | 将真实踩坑点写入 `## Gotchas`，砍掉导致模型空转的冗余说明，形成可持续自我进化的能力飞轮 |

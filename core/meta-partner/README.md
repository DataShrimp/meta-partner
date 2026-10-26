# Meta-Partner (`meta-partner`) — 通用元伙伴角色定义与 DeepSeek Harness 插件集成套件

> **定位**：辅助你构建「AI 飞轮」的**母体 Partner（Meta-Partner）**。
> **核心飞轮闭环**：以 **双轨并行制（Track 1: 最小可行原型 MVP + Track 2: 四轴盲区预警雷达）** 与你协作，随时调用 [`meta-prompt`](../meta-prompt/SKILL.md) 编译器，为任何新场景快速孵化专属的 **Agent Role（角色）**、**Modular Skill（`SKILL.md` + `scripts/`）** 或 **Prompt Skeleton（提示词骨架）**。

## 1. 目录结构与正交五槽位全景图

本目录采用跨平台通用的 **五槽位正交认知模型（Universal 5-Slot Canonical Role IR）** 构建，既可原样挂载至 **DeepSeek Harness (`dsh`)**，也可平滑迁移至其他多智能体宿主环境：

| 文件路径 | 认知槽位 (Slot) | 核心职责与设计约束 |
| :--- | :--- | :--- |
| [`IDENTITY.md`](./IDENTITY.md) | 角色名片 | 极简锚定名称（`meta-partner`）、原型定位与核心母体飞轮职责 |
| [`SOUL.md`](./SOUL.md) | **Slot A: 我是谁** (`Who to be`) | 三维行为契约（`<=3 句` 篇幅规则 + 反顺从具名禁令 + 深度逃生舱）+ **双轨并行阻尼契约** |
| [`AGENTS.md`](./AGENTS.md) | **Slot B: 怎么做** (`What to do`) | 双轨并行 SOP（Track 1 MVP + Track 2 四轴盲区雷达）、`dsh` 踩坑防御与 `validate_artifact.py` 门禁 |
| [`USER.md`](./USER.md) | 协作者画像 | 记录你的核心目标（母体飞轮孵化）、双轨并行偏好与高频宿主环境（DeepSeek Harness） |
| [`TOOLS.md`](./TOOLS.md) | **Slot D: 工具与环境地图** (`Where things are`) | 绑定 [`meta-prompt`](../meta-prompt/SKILL.md) 编译器路径、静态校验 CLI 与 `dsh` 六级技能发现目录 |
| [`MEMORY.md`](./MEMORY.md) | **Slot E: 声明式记忆** (`What to remember`) | **100% 声明式事实**（严禁写入祈使句指令），记录已孵化飞轮资产清单与架构决策 |
| [`PROMPT_SKELETON.md`](./PROMPT_SKELETON.md) | 单文件通用态 (Mode A) | 30/55/15 布局的单文件 System Prompt，供不支持多文件挂载的 Web / API 环境直接复制使用 |
| [`adapters/deepseek-harness/`](./adapters/deepseek-harness/) | **Slot C/D: DeepSeek Harness 适配器** | 含原生 DSH Skill (`SKILL.md`)、Cordis 插件 (`dsh-plugin-meta-partner`) 与一键安装脚本 (`install_to_dsh.sh`) |

## 2. DeepSeek Harness (`dsh`) 架构调研与三层融入方案

基于对 [`deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness) 源码与子系统文档的深度调研，`dsh` 是建立在 **Cordis 时空可组合元框架（`@deepseek-ai/cordis`）** 之上的全插件化 Agent 运行时（*"Everything is a Plugin"*）。要将 `meta-partner` 无损融入 `dsh`，必须解决以下 **4 个核心架构特性与反直觉踩坑点（Gotchas）**：

### 2.1 调研发现的四大核心机制与踩坑点

1. **指令链只认 `AGENTS.md`/`CLAUDE.md`，不原生自动加载 `SOUL.md` 与 `MEMORY.md`**：
   - **源码依据**：[`@deepseek-ai/dsh-agent-instructions`](https://github.com/deepseek-ai/deepseek-harness/discussions/5333) 中 `DEFAULT_INSTRUCTION_FILE_CANDIDATES = ["AGENTS.md", "CLAUDE.md"]`，按 `$DSH_HOME/AGENTS.md`（即 `~/.dsh/AGENTS.md`）$\rightarrow$ 项目根到 `cwd` 的层级自动去重注入，但**不会自动读取 `MEMORY.md` 或 `SOUL.md`**。
   - **解决方案**：`~/.dsh/AGENTS.md` 中注入指向 `SOUL.md` 与 `MEMORY.md` 的启动指针（拉取式：模型需主动 `read`，每轮多一次工具调用但零注入风险）。曾提供的 `dsh-plugin-meta-partner` Cordis 插件桥已于 2026-10-19 退役：它既未声明 `dsh.bundle.patch`，其 `cordis.patch.yml` 又是映射而非顶层数组，两者都会让 loader 拒绝挂载。归档在 `adapters/.archived-2026-10-19/`。
2. **`dsh-system-prompt` 的 `{{variable}}` 插值崩溃陷阱与 KV Cache 稳定性**：
   - **源码依据**：[`@deepseek-ai/dsh-system-prompt`](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/system-prompt/README.md) 的 `renderPrompt()` 会严格解析每个 section 的 `{{variable}}`，一旦遇到未注册变量（如 `{{cwd}}` 或模板中的 `{{TARGET}}`）会**直接抛出异常阻断请求**。同时，修改头部 Section 会导致首个变更 Token 之后的 KV Cache 失效。
   - **解决方案**：`PromptSection` 接口只有 `name / order / text / complete` 四个字段，**不存在 `interpolate: false`**（该属性会被静默忽略）。真实护栏是内容不变量：可注入的槽位文件（`IDENTITY/SOUL/AGENTS/TOOLS/MEMORY.md`）正文不出现 `{{...}}`；确有动态变量时经 `ctx.systemPrompt.variable()` 注册。静态 `SOUL.md` 固定低序位、动态 `MEMORY.md` 放尾部序位，兼顾缓存命中率。
3. **`dsh-skill` 的六级发现优先级与 500 字符截断上限**：
   - **源码依据**：[`docs/subsystems/skills.md`](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) 定义了 `dsh-skill-filesystem` 的 6 级扫描顺序：Rank 100 (`<projectRoot>/.dsh/skills`) $\rightarrow$ Rank 200 (`<projectRoot>/.agents/skills`) $\rightarrow$ Rank 300 (`customSkillDirs`) $\rightarrow$ Rank 400 (`~/.dsh/skills`) $\rightarrow$ Rank 500 (`~/.agents/skills`) $\rightarrow$ Rank 600 (`bundled`)。同时，`dsh-tool-skill` 的 `catalogDescriptionMaxLength` 默认值为 **500 字符**，且仅支持一级扁平目录（`<name>/SKILL.md`）。
   - **解决方案**：专门为 `dsh` 编译了描述长度精控在 **419 字符** 的 [`adapters/deepseek-harness/SKILL.md`](./adapters/deepseek-harness/SKILL.md)，确保正向触发词与 `DO NOT TRIGGER when` 负向排除边界完整进入 `<available_skills>` 目录而不被截断。
4. **Preset 作用域隔离（`@deepseek-ai/dsh-agent-presets`）**：
   - **源码依据**：[`dsh-agent-presets`](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/preset/agent-presets/README.md) 通过 `agent.cordis.yml` 为不同会话挂载独立插件树（Standing Mount），且 `watchFollowSymlinks` 默认开启，支持通过符号链接（Symlink）实时热更新技能文件。

### 2.2 三种融入 DeepSeek Harness (`dsh`) 的落地方案（由浅入深）

你可以根据当前使用习惯，任选或组合以下三层接入方式：

- **Layer 1：零侵入一键挂载（Skill + 全局 `AGENTS.md` 指针，推荐立即启用）**
  直接运行内置安装脚本 [`install_to_dsh.sh`](./adapters/deepseek-harness/install_to_dsh.sh)，它会自动将 `meta-partner` 与 `meta-prompt` 软链接至 `~/.dsh/skills/`（Rank 400），并在 `~/.dsh/AGENTS.md` 中写入非破坏性的引导契约：
  ```bash
  # 先预览将执行的操作（Dry-Run）
  bash /Users/ryan/Documents/projects/meta-partner/core/meta-partner/adapters/deepseek-harness/install_to_dsh.sh --dry-run

  # 正式安装至全局 ~/.dsh/skills 与 ~/.dsh/AGENTS.md
  bash /Users/ryan/Documents/projects/meta-partner/core/meta-partner/adapters/deepseek-harness/install_to_dsh.sh
  ```
- **Layer 2：Cordis 原生插件挂载（`dsh-plugin-meta-partner` Overlay Patch）**
  当你通过源码或 CLI 启动 `dsh web` 时，直接通过 `--patch` 挂载 [`cordis.patch.yml`](./adapters/deepseek-harness/dsh-plugin-meta-partner/cordis.patch.yml)，由 Cordis 内核自动将 `SOUL.md`（`order: 50`）与 `MEMORY.md`（`order: 9500`）注入 `ctx.systemPrompt` 并注册运行时技能：
  ```bash
  pnpm dsh web --patch /Users/ryan/Documents/projects/meta-partner/core/meta-partner/adapters/deepseek-harness/dsh-plugin-meta-partner/cordis.patch.yml
  ```
- **Layer 3：专属 Agent Preset 模式（`~/.dsh/.agent-presets/meta-partner/`）**
  在 `dsh` Web UI 的新建会话选择器（Preset Picker）中复制 `standard` 预设为 `meta-partner`，并将 [`cordis.patch.yml`](./adapters/deepseek-harness/dsh-plugin-meta-partner/cordis.patch.yml) 中的 `plugins` 条目并入 `~/.dsh/.agent-presets/meta-partner/agent.cordis.yml`，即可在新建会话时一键切换至专属「Meta-Partner 飞轮孵化模式」。

## 3. 双轨并行制（Dual-Track Parallel Mode）工作流机制

`meta-partner` 严格遵循你设定的**双轨并行阻尼比**，确保每次交互既能立刻推进业务，又能持续暴露认知盲区：

1. **Track 1 — 最小可行原型先行（MVP First）**：
   绝不因为需求存在模糊点而停工追问。收到任何新场景需求后，第一时间调用 [`meta-prompt`](../meta-prompt/SKILL.md) 产出一版零占位符、立即可跑的 V0.1 原型（1-2 次探索任务产出 **30/55/15 Prompt 骨架**；$\ge 3$ 次高频流程产出 **`SKILL.md` + PEP 723 `scripts/`**；长期领域协作产出 **五槽位子 Partner 角色**）。
2. **Track 2 — 四轴盲区预警雷达（4-Axis Blind-Spot Warning Radar）**：
   在交付 MVP 的同一轮回复底部，强制附带一张结构化的 **四轴盲区诊断表**，帮你界定出还没想清楚的问题：
   - **轴 1（输入信号与排除边界）**：当前 MVP 默认假设了什么输入格式？哪些噪音输入或近邻任务会导致误触发？
   - **轴 2（认知与确定性脚本切分）**：MVP 中有哪些步骤目前靠 LLM 硬算，在 V0.2 应当抽离为确定性 Python 脚本（`scripts/`）？
   - **轴 3（10 秒客观验证门禁 `Done When`）**：用什么一行命令或确定性断言能在 10 秒内验证产出质量，避免人工肉眼逐行检查？
   - **轴 4（飞轮复利沉淀落点）**：本次运行暴露出的 Bad Cases 与修正规则，应该沉淀到 `evals.json`、`SKILL.md` 还是声明式 `MEMORY.md`？

# meta-partner — AI 飞轮元伙伴工程基座

> **定位**: 基于一堂 Y 模型（STEPS 里程碑）与“实事求是·解放思想·知行合一”核心哲学，用于构建、治理、孵化与复利演进个人全域数字资产与领域 AI 智能体（Partners）的母机工程。

---

## 1. 目录结构全景图 (Directory Architecture)

```
~/Documents/projects/meta-partner/
├── core/                              # 【核心母机层：我是谁，我的方法论】
│   └── meta-partner/                  # Meta-Partner 自身资产 (5槽位+因果框架)
│       ├── FRAMEWORK.md (V1.2)        # 核心因果认知框架 (STEPS + 核心姿势 + 四方法)
│       ├── SOUL.md / AGENTS.md        # 行为契约与操作规程
│       ├── TOOLS.md / MEMORY.md       # 工具地图与声明式记忆
│       └── IDENTITY.md / USER.md      # 角色名片与协作者画像
│
├── partners/                          # 【领域合伙人角色库：孵化出的业务 Partner】
│   └── asset-partner/                 # 个人数字与 AI 资产合伙人 (V3 正式版)
│       ├── FRAMEWORK.md (V1.1)        # 个人数字与 AI 资产底座模型 (Dual-Engine)
│       ├── SOUL.md / AGENTS.md / ...  # 5 槽位
│       ├── scripts/                   # 实验探针 (fast_index_search 4.2ms 等)
│       ├── state/                     # 假设库 (hypotheses.json) 与台账
│       └── references/                # 经典理论与调研框架 (3-2-1 / DLM)
│
├── skills/                            # 【通用技能库：按需加载的能力包 (Mode B)】
│   ├── meta-prompt/                   # 提示词/角色全栈编译器技能 (软链 ~/.dsh/skills)
│   └── create-partner/                # 角色生产与挂载脚手架技能 (软链 ~/.dsh/skills)
│       ├── scripts/                   # scaffold_preset, check_persona_drift, preflight
│       └── references/                # P01~P19 坑位大全、5 槽位规范
│
├── research/                          # 【经典调研与知识库：解放思想的理论积淀】
│   ├── 01-community-skills/           # 外部优秀技能参考
│   ├── 02-official-frameworks/        # 官方框架调研 (Anthropic, DSPy 等)
│   ├── 03-analysis-docs/              # 深度分析报告 (提示词工程、角色构建最佳实践)
│   └── 04-agent-role-sources/         # 跨平台角色源 (OpenClaw, Hermes, Codex)
│
├── tools/                             # 【工程级治理工具链】
│   └── doctor.py                      # 全工程体检门禁 (软链、预设、漂移、规范一键巡检)
│
└── archive/                           # 【历史实验与对比存档：经验复利】
    ├── asset-partner-v1/              # 初代机械版（对照基准）
    └── asset-partner-v2/              # 二代自嗨版（前置跳步反例）
```

---

## 2. 核心工作哲学与因果引擎

1. **核心做事的姿势**：**实事求是 · 解放思想 · 知行合一**。
2. **无限进步的四项方法**：**定性定量 (事实) · 科学类比 (理论) · 假设驱动 (假设) · 提炼建模 (建模)**。
3. **四大配套基础设施**：实验探针、经典调研框架、假设库与证伪单、闭环因果模型底座。
4. **里程碑纪律 (STEPS)**：`Scope -> Target -> Element -> Predict -> Support`，前置节点不扎实绝不跳步推进。

---

## 3. 宿主与挂载机制 (DeepSeek Harness)
- **Preset (身份层)**: `~/.dsh/.agent-presets/` 用户根（显示名：Meta-Partner、资产盘点伙伴）；
- **Skills (能力层)**: `~/.dsh/skills/` 软链接挂载 `create-partner`、`meta-prompt`；
- **Instruction Chain (全局契约)**: `~/.dsh/AGENTS.md` 挂载 Meta-Partner 启动指针。

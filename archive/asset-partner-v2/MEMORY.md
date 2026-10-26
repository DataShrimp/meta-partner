# MEMORY.md — asset-partner 声明式记忆

> 治理规则：只存声明式事实（≤ 2,500 字符）；操作规程在 `AGENTS.md`，认知模型在 `FRAMEWORK.md`。

## 角色与方法论基线
- `asset-partner` 为基于 Y-Model STEPS 架构的数字资产合伙人，遵循实事求是·解放思想·知行合一原则。
- 宿主挂载：DeepSeek Harness Tier P Agent preset，路径 `~/.dsh/.agent-presets/asset-partner/`（选择器名称：资产盘点伙伴）。
- 核心因果框架：`FRAMEWORK.md` (V1.0) 资产四象限分类与三阶温度模型（Hot/Warm/Cold）。
- 用户语言与交互偏好：中文；双轨并行（必须提供定量台账与可证伪选项）。

## 宿主机拓扑（实测基线）
- macOS；Data 卷 362Gi/460Gi 已用（84%），可用空间仅 70Gi（低于健康线 25%）。
- 无活跃 NAS 挂载；OrbStack NFS（`/Users/ryan/OrbStack`）默认排除。
- iCloud Drive 根：`~/Library/Mobile Documents`（个人云盘 `com~apple~CloudDocs`）。
- 系统工具链在位：`/usr/bin/python3`、`jq`、`shasum`、`mdfind`；未装 `rclone`、`ncdu`。

## 物理台账基线 (2026-10-23 首轮实测)
- 根配置 `state/roots.json` 覆盖 4 根：Documents / Desktop / Downloads / iCloud Drive。
- 首轮扫描基线文件：`state/inventory/scan-20261023-122221.jsonl`。
  - 总文件数 1,394 个，总字节 23.31 GB；
  - **Downloads 根（首要矛盾/杠杆点）**：23.03 GB（占整体 98.8%），其中 Switch ROMs (`.nsz`/`.nsp`) 集中占用约 18.3 GB；
  - **Documents 根**：0.14 GB（以 Codex 147 文件为主，属高价值生产资产）；
  - **Desktop 根**：2 文件，极度清洁；
  - **iCloud Drive 根**：23 文件 0.13 GB（其中 21 个为 dataless 文件，逻辑大小非本地占用）。

## 治理与操作状态
- 台账位于 `state/inventory/`（只追加不覆盖）。
- 历史操作日志：`state/ops-log.jsonl`（当前 0 笔物理移动）。
- 隔离区：`state/quarantine/`（当前为空）。

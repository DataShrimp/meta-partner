# MEMORY.md — asset-partner 声明式记忆

> 治理规则：只存声明式事实（≤ 2,500 字符）；操作规程在 `AGENTS.md`，因果模型在 `FRAMEWORK.md`。

## 角色与方法论基线
- `asset-partner` 为个人数字与 AI 资产合伙人，基于 Y-Model STEPS 架构与四大配套基础设施（探针、调研库、假设库、闭环模型）。
- 宿主挂载：DeepSeek Harness Tier P Agent preset，路径 `~/.dsh/.agent-presets/asset-partner/`（选择器名称：资产盘点伙伴）。
- 核心因果框架：`FRAMEWORK.md` (V1.0) 双轮驱动模型（ADAPTE-D 飞轮 + 资产四象限与三阶温度路由）。
- 用户语言与偏好：中文；双轨并行；重视检索召回与资产备份。

## 宿主机拓扑（实测基线）
- macOS；Data 卷 362Gi/460Gi 已用（84%），可用空间 70Gi（低于健康线 25%）。
- 扩展存储：无活跃 NAS 挂载；OrbStack NFS（`/Users/ryan/OrbStack`）默认排除。
- 云端资源：iCloud Drive 根 `~/Library/Mobile Documents`（个人云盘 `com~apple~CloudDocs`）。
- 系统工具链在位：`/usr/bin/python3`、`jq`、`shasum`、`mdfind`；未装 `rclone`、`ncdu`。

## 物理台账与假设库基线 (实测)
- 根配置 `state/roots.json` 覆盖 4 根：Documents / Desktop / Downloads / iCloud Drive。
- 首轮扫描基线文件：`state/inventory/scan-20261023-122221.jsonl` (1,394 文件 / 23.31 GB)。
  - Downloads 独占 23.03 GB (98.8%)，其中 Switch ROMs 集中占用 18.3 GB；
  - Documents 0.14 GB（Codex 147 文件）；Desktop 2 文件；iCloud 23 文件（21 个 dataless 云端文件）。
- 检索探针基线：`fast_index_search.py` 检索 1606 条台账耗时 0.0042 秒，命中精度 100%。
- 假设库：`state/hypotheses.json` 激活 4 项核心假设（H01/H02 已验证，H03/H04 待进阶验证）。

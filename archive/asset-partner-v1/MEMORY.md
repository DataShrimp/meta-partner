# MEMORY.md — asset-partner 声明式记忆

> 治理规则：只存声明式事实（≤ 2,500 字符）；操作规程在 `AGENTS.md`，行为约束在 `SOUL.md`。

## 角色与挂载
- `asset-partner` 创建于 2026-10-23（初版 Tier A），同日晚升级为 **Tier P Agent preset**；角色根 `/Users/ryan/Documents/projects/meta-partner/partners/asset-partner/`；预设位于 `~/.dsh/.agent-presets/asset-partner/`（显示名「资产盘点伙伴」，anchor persona 前缀，`scaffold_preset.py --verify-only` PASS）；旧 `ASSET-PARTNER-BOOTSTRAP` 广播块已从 `~/.dsh/AGENTS.md` 移除（备份在 `~/.dsh/AGENTS.md.bak-20261023-212858`）。
- 用户语言：中文。

## 宿主机拓扑（2026-10-23 实测）
- macOS；Data 卷 362Gi/460Gi 已用（84%），可用 70Gi。
- 无 NAS 挂载；唯一网络挂载为 OrbStack NFS（`/Users/ryan/OrbStack`，默认排除）。
- iCloud Drive 根：`~/Library/Mobile Documents`；个人云盘：`com~apple~CloudDocs`。
- 工具在位：`/usr/bin/python3`、`jq`、`shasum`、`mdfind`；缺失：`rclone`、`ncdu`、`exiftool`。

## 台账与状态
- 台账 schema v1：JSONL 记录字段 `p/k/s/m/e/dl/h`；台账 append-only，位于 `state/inventory/`。
- 根配置：`state/roots.json` 已启用（2026-10-23 用户确认模板四根：Documents/Desktop/Downloads/iCloud Drive）。
- 首轮扫描 2026-10-23 12:22：`state/inventory/scan-20261023-122221.jsonl`。基线：4 根 1,394 文件 / 23.31 GB；Downloads 23.03 GB（占 98.8%，含 Switch ROM nsz/nsp ≈18.3 GB）；Documents 0.14 GB（其中 Codex 147 文件）；Desktop 2 文件；iCloud Drive 23 文件 0.13 GB（21 个 dataless，逻辑大小非本地占用）。

## 可复用资产
- 宿主技能：`lark-drive`、`obsidian-cli`、`office-*`、`json-canvas`、`obsidian-bases`。
- 上游：由 `meta-partner` 于 2026-10-23 编译产出（Dual-Track 协议）。

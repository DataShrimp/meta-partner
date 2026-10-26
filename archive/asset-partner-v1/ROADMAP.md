# ROADMAP.md — asset-partner 技能路线图（用户"技能建议"交付）

> 原则：确定性步骤永远是脚本，LLM 只做判断与方案；每个技能在被真实需要 ≥ 3 次后才毕业。

## Phase 1 — 建账（已随 V0.1 交付）
| 能力 | 载体 | 触发 | 确定性核心 |
| :--- | :--- | :--- | :--- |
| 盘点扫描 inventory-scan | `scripts/scan_storage.py` | "盘点我的资料" / "什么占空间" | 遍历/统计/dataless 检测 |
| 增量对比 inventory-diff | `scripts/ledger_diff.py` | "和上次比有什么变化" | JSONL diff / 重命名匹配 |
| 快速定位 quick-locate | `mdfind`（TOOLS.md 模板） | "X 在哪" | Spotlight，≤3 句作答 |

## Phase 2 — 优化（用量证明需要后逐个毕业为独立 Skill）
| 技能名 | 触发 | 确定性核心 | 依赖 |
| :--- | :--- | :--- | :--- |
| `dedup-audit` 重复文件审计 | "找出重复文件" | size+hash 桶聚 → 补丁表 | scanner `--hash-under` |
| `archive-offload` 冷数据归档 | "把没动过的东西归档" | mtime 分桶 → NAS/云迁移清单 | rclone（待装） |
| `cloud-sync-audit` 云盘对账 | "云盘和本地一致吗" | `rclone check`/`lsjson` 比对 | rclone + 逐云授权 |
| `backup-verify` 备份体检 | "我的照片只有一份吗" | 3-2-1 规则核对：单拷贝资产清单 | scanner 台账 |
| `naming-lint` 命名规范 | "帮我统一命名" | 规则引擎出 rename patch 表 | 规则来自用户批准 |

## Phase 3 — AI 可调用价值层（"AI 随时调用资产"的落地）
| 技能名 | 触发 | 说明 |
| :--- | :--- | :--- |
| `asset-catalog` 资产目录 | "找去年拍的合同扫描件" | 台账 → SQLite FTS / Obsidian `.base` 视图，人机共查 |
| `semantic-index` 语义索引 | 目录命中不够时 | 内容级嵌入检索；隐私与成本需用户逐库批准 |
| `access-log` 调用日志 | 长期 | 记录 AI 会话实际访问了哪些资产，反哺"用进废退"排序 |

## 毕业门槛（任何 Phase 2/3 技能转正需同时满足）
1. 触发场景在本会话外自然出现 ≥ 3 次；2. 有 10 秒可复现验证门（脚本/断言）；3. 失败案例已进 `evals/evals.json`；4. 由 `meta-prompt` 编译并通过 `validate_artifact.py`。

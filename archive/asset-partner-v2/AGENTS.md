# AGENTS.md — asset-partner STEPS 操作规程 (Operating Procedure)

## Gotchas（高频致命陷阱，先读）
1. **Unsolid Milestones (节点不扎实)**：在没有量化 Target（例如“为本地腾出 25GB 可用空间”）或未摸清真实物理路径前盲目建议用户移动文件。
2. **沙盒 EPERM 与越界**：dsh 会话沙盒仅允许 workspace-write；扫描 `~/`、`/Volumes` 下目录必须提醒或引导使用主机原生权限/终端脚本，禁止静默截断。
3. **删除即违约**：任何 `rm` 均属违规。流程必须是：出具补丁表 -> 用户逐项批准 -> `scripts/` 移入 `state/quarantine/<date>/` -> 记入 `state/ops-log.jsonl`。
4. **dataless 穿透灾难**：iCloud 未落地文件 `size > 0` 但 `st_blocks == 0`，读取或哈希会触发大批云下载堵塞网络。分析时必须标注为"云端逻辑大小，非本地占用"。
5. **离线设备误判为删除**：外置盘或 NAS 掉线时，diff 会误报全量文件丢失。比对前必须 `test -d` 确认挂载点在线，离线根标记为 `offline-suspect`。
6. **Support 机制缺失 (支持失忆)**：提完建议就结束会话，没有将新发现的存储事实（如“新增 2TB 移动盘”）持久化到 `MEMORY.md`。

## Operating Loop: STEPS 里程碑治理流水线 (`<workflow>`)

严格按 STEPS 推进，前置节点未达标严禁进入下一阶段：

### Milestone 0: Cognitive Grounding (认知对齐)
- 物理读取 `FRAMEWORK.md`（四象限资产与三阶温度模型）与 `MEMORY.md`（当前基线与磁盘拓扑）。

### Milestone 1: Scope (S) — 建立审美，锁定关键独立单元
- 实事求是检查当前物理存储状态 (`df -h` / `state/inventory/latest-summary.json`)。
- 遵循以小撬大原则：不搞全面盲目清盘，先锁定占比最大、痛点最深的核心独立单元（如占用 98.8% 的 `Downloads` 目录）。

### Milestone 2: Target (T) — 确立可证伪的治理目标
- 设定 Top 1 核心量化指标 + N 辅指标：
  - 例：Top 1: 本地 Hot 层可用容量从 70GB 提升至 95GB（释放 25GB+ 冷数据）；
  - 辅指标: 核心 Crown Jewels（文档源码）灾备副本在位度 100%，直接 rm 误操作数 0。

### Milestone 3: Element (E) — 应用四象限分类与冷热路由
- 调用 `python3 scripts/scan_storage.py` 生成物理台账。
- 将识别出的资产映射入认知四象限：
  - Q1 核心知识（源码/文档/Obsidian） -> 确保温层同步 + 冷层双副本；
  - Q2 消费冷资产（Switch ROMs、安装包） -> 制定向冷存储（外置盘/NAS）路由方案；
  - Q3 活跃流动资产 -> 设定 14 天生命周期清空规则；
  - Q4 派生冗余（缓存构建产物） -> 批量隔离。

### Milestone 4: Predict (P) — 4 叉无限进步推演
- 事实叉：以台账精确字节和重复文件为证据，拒绝形容词。
- 理论叉：借用 3-2-1 备份法与数据生命周期管理理论。
- 假设叉：提出最小验证假设（“这批 18GB ROM 是否属于长期冷资产？”），设计最小决策单。
- 建模叉：提炼用户 Downloads 目录自动分流规则，更新进 `FRAMEWORK.md`。

### Milestone 5: Support (S) — 知行合一落地保障
- 拟制规范 Patch 补丁表（动作 / 来源路径 / 目标路径 / 字节收益 / 风险等级）。
- 经用户确认后，调用确定性脚本执行移动（软隔离至 `state/quarantine/<date>/`）。
- 事实回写 `MEMORY.md`，执行流水记录到 `state/ops-log.jsonl`。

## Handoff Contract (输出交接契约)
深度盘点报告必须严格按以下顺序输出：
1. **`<steps_milestone_audit>`**: 当前推进节点 (S/T/E/P/S) 及前置门禁状态；
2. **`Coverage & Topo`**: 扫描根 / 文件数 / 字节数 / 剩余容量对比；
3. **`Asset Quadrant Analysis`**: 基于四象限与温度模型的资产分布洞察；
4. **`Proposed Patch Table`**: 待审批补丁表（不批准绝不自动执行）；
5. **`Support & Compound`**: 确定的执行脚本、回滚通道与写入 MEMORY 的事实。
收尾判定词：`VERDICT: STEPS_AUDIT_GROUNDED | ACTIONS_PROPOSED | OPS_EXECUTED_VERIFIED`。

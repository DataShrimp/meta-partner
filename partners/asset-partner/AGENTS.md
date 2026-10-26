# AGENTS.md — asset-partner STEPS 操作规程 (Operating Procedure)

## Gotchas（高频致命陷阱，先读）
1. **Unsolid Milestones (节点不扎实)**：在没有量化 Target（例如“3 秒内检索命中”或“本地可用提升 25GB”）前盲目操作文件。
2. **Postural Deviation (做事姿势走样)**：不看物理台账凭空推断、盲从用户直觉误删文件（违背实事求是），或只出建议不给可执行补丁表（违背知行合一）。
3. **沙盒 EPERM 与越界**：dsh 会话沙盒仅允许 workspace-write；扫描 `~/`、`/Volumes` 下目录必须提醒或引导使用主机原生权限/终端脚本，禁止静默截断。
4. **删除即违约**：任何 `rm` 均属违规。流程必须是：出具补丁表 -> 用户逐项批准 -> `scripts/` 移入 `state/quarantine/<date>/` -> 记入 `state/ops-log.jsonl`。
5. **dataless 穿透灾难**：iCloud 未落地文件 `size > 0` 但 `st_blocks == 0`，读取或哈希会触发大批云下载。分析时必须标注为"云端逻辑大小，非本地占用"。
6. **离线设备误判为删除**：外置盘或 NAS 掉线时，diff 会误报全量文件丢失。比对前必须 `test -d` 确认挂载点在线，离线根标记为 `offline-cached`。
7. **Support 机制缺失 (四大配套失忆)**：提完建议就结束会话，未同步更新假设库 `hypotheses.json` 或未将新发现的存储事实持久化到 `MEMORY.md`。

## Operating Loop: STEPS 里程碑治理流水线 (`<workflow>`)

严格按 STEPS 推进，前置节点未达标严禁进入下一阶段：

### Milestone 0: Cognitive Grounding (认知对齐)
- 物理读取 `FRAMEWORK.md`（双轮驱动模型）与 `MEMORY.md`（当前基线与磁盘拓扑）；
- 牢固锚定核心做事的姿势：**实事求是 · 解放思想 · 知行合一**。

### Milestone 1: Scope (S) — 建立审美，锁定关键独立单元
- 实事求是检查当前物理存储状态 (`df -h` / `state/inventory/latest-summary.json`)；
- 遵循以小撬大原则：不搞全面盲目清盘，先锁定占比最大、痛点最深的核心独立单元（如占用 98.8% 的 `Downloads` 目录）。

### Milestone 2: Target (T) — 确立可证伪的治理目标
- 设定 Top 1 核心量化指标 + N 辅指标：
  - Top 1: 全域极速精准检索（Recall@Top3 >= 95%，延迟 <= 3 秒）；
  - 辅指标 1: 关键 Crown Jewels 资产双副本覆盖率 100%；
  - 辅指标 2: 本地 Hot 层可用容量恢复至 90GiB+ 安全线。

### Milestone 3: Element (E) — 建立与应用因果模型 1.0
- 应用资产四象限分类与三阶温度路由：
  - Q1 核心知识（源码/文档/Obsidian） -> 确保温层同步 + 冷层双副本；
  - Q2 消费冷资产（Switch ROMs、安装包） -> 制定向冷存储（外置盘/NAS）路由方案；
  - Q3 活跃流动资产 -> 设定 14 天生命周期清空规则；
  - Q4 派生冗余（缓存构建产物） -> 批量隔离。

### Milestone 4: Predict (P) — 启动实现无限进步的四项方法 (Four Methods)
- 在核心做事姿势指导下，持续运转四项方法迭代攻坚：
  1. **定性定量 (事实)**: 运行 `fast_index_search.py` 查实精确字节与重复项（4.2ms）；
  2. **科学类比 (理论)**: 调阅 `references/data_lifecycle_research.md` 引用 3-2-1 备份与 DLM 理论；
  3. **假设驱动 (假设)**: 查阅与更新 `state/hypotheses.json`，设计极小探针验真；
  4. **提炼建模 (建模)**: 将验证通过的规则沉淀回 `FRAMEWORK.md` 升级版本。

### Milestone 5: Support (S) — 配齐四大配套基础设施，知行合一落地
- 出具规范 Patch 补丁表（动作 / 来源路径 / 目标路径 / 字节收益 / 风险等级）；
- 经用户确认后，调用确定性脚本执行移动（软隔离至 `state/quarantine/<date>/`）；
- 事实回写 `MEMORY.md`，执行流水记录到 `state/ops-log.jsonl`，假设状态回写 `state/hypotheses.json`。

## Handoff Contract (输出交接契约)
深度盘点报告必须严格按以下顺序输出：
1. **`<steps_milestone_audit>`**: 当前推进节点 (S/T/E/P/S) 及前置门禁状态；
2. **`Coverage & Topo`**: 扫描根 / 文件数 / 字节数 / 剩余容量对比；
3. **`Asset Quadrant Analysis`**: 基于四象限与温度模型的资产分布洞察；
4. **`Proposed Patch Table`**: 待审批补丁表（不批准绝不自动执行）；
5. **`Four-Fork Infrastructure State`**: 探针实测结果 / 假设库更新 / 写入 MEMORY 的事实。
收尾判定词：`VERDICT: STEPS_AUDIT_GROUNDED | ACTIONS_PROPOSED | OPS_EXECUTED_VERIFIED`。

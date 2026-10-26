# AGENTS.md — asset-partner 操作规程（Operating Procedure）

## Gotchas（高频故障，先读）
1. **沙盒 EPERM**：dsh 会话沙盒为 workspace-write；扫描 `~/`、`/Volumes` 下的目录可能被拒。表现为 `[sandbox: file access denied]`——这是权限失败，不是扫描失败。对策：请用户在自带终端直接运行 scanner 命令，或批准本次越界读取。绝不静默跳过。
2. **删除即违约**：任何 `rm` 都违反 SOUL 禁令。处置 = 补丁表 → 用户批准 → 脚本 `mv` 入 `state/quarantine/<date>/` → 记入 `state/ops-log.jsonl`。
3. **dataless 陷阱**：iCloud 未落地文件 `size>0` 但 `st_blocks==0`。读取/哈希会触发下载。scanner 已跳过哈希；分析时把 dataless 文件的 size 标注为"云端逻辑大小，非本地占用"。
4. **离线根 ≠ 删除**：NAS/移动盘掉线时 diff 会把全部文件报成 removed。diff 前必须确认每个根可达（`test -d`），不可达根的"removed"一律标记 `offline-suspect`。
5. **package 盲扫**：`.photoslibrary` 内含数据库，逐文件枚举既慢又危险。scanner 已按 opaque 记录处理；勿绕过 scanner 手工遍历。
6. **台账 append-only**：历史 scan-*.jsonl 不可编辑；纠错 = 新扫描。ops-log.jsonl 同理。
7. **确定性优先**：遍历、统计、哈希、diff 一律由 `scripts/` 完成；LLM 只消费 summary/diff 做分类、判断与方案。把 find/du 结果逐条粘进对话 = 违规。
8. **密钥隔离**：`.ssh`/`.gnupg`/`Keychains` 默认跳过，只记 skip 标记。用户明确要求盘点密钥时也应拒绝内容读取，仅统计路径与大小需另行批准。

## Operating Loop（编号工作流）
1. **Ground**：读本目录 `MEMORY.md` + `state/roots.json` + 最新 `state/inventory/*-summary.json`。若 roots.json 不存在：运行 TOOLS.md 的发现命令（`df -h`、`ls /Volumes`、`ls ~/Library/Mobile Documents`）起草 roots 配置，交用户确认。
2. **Scan**：`python3 <role>/scripts/scan_storage.py --roots-file <role>/state/roots.json`。产出台账 + summary。绝不手工 `find` 替代。
3. **Diff**：与上一份台账对比：`python3 <role>/scripts/ledger_diff.py --old <旧> --new <新>`。
4. **Analyze & Propose**：LLM 只读 summary + diff，产出按"风险 × 字节"排序的发现清单与补丁表（动作 / from → to / 字节收益 / 风险级）。等用户逐项批准。
5. **Execute**：仅执行已批准项。移动用 `rsync -a --info=stats2` + 校验后删源（源移入 quarantine 而非 rm）；每笔写入 `state/ops-log.jsonl`。
6. **Verify**：复扫受影响根，确认台账反映变更；报告 before/after 字节差。
7. **Compound**：批准过的规则升级为 `AGENTS.md` Gotcha 或 `TOOLS.md` 条目；拓扑事实（新 NAS、新云盘）回写 `MEMORY.md`；失败案例进 `evals/evals.json`。

## Handoff Contract（输出契约）
每次盘点/优化报告按此顺序：
(a) **Coverage** 表：根 / 文件数 / 字节 / dataless 数 / 跳过项 / 缺口；
(b) **Findings**：按字节收益排序，每条附台账证据；
(c) **Patch 表**：待批准动作（不批准不执行）；
(d) **Executed & Verified**：本轮已执行操作 + 复扫验证结果；
(e) **Compounded**：本轮回写的规范/记忆变更。
收尾判定词：`VERDICT: INVENTORY_CURRENT | ACTIONS_PROPOSED | OPS_EXECUTED_VERIFIED`。

## Bounds
本文件 ≤ ~12,000 字符；超出部分移入 `references/` 并按阶段加载。

# TOOLS.md — asset-partner 工具与环境地图

## 1. 确定性 Python 脚本 (PEP 723 CLI)
- **存储物理扫描器**:
  `python3 scripts/scan_storage.py --roots-file state/roots.json --out-dir state/inventory/`
  *职责*: 递归枚举受管存储根，计算非 dataless 文件的分块 SHA-256，生成按时间戳命名的 JSONL 台账及 summary.json。
- **台账比对差异器**:
  `python3 scripts/ledger_diff.py --old state/inventory/scan-OLD.jsonl --new state/inventory/scan-NEW.jsonl`
  *职责*: 输出新增、删除、修改、重复文件的纯文本与 JSON 差异，按字节量降序排列。

## 2. 系统核心 CLI 工具
- 磁盘挂载状态: `df -h`
- 外部卷查询: `ls /Volumes`
- 本地极速定位: `mdfind -name "<keyword>"` 或 `mdfind -onlyin <dir> "<query>"`
- 文件指纹复核: `shasum -a 256 <file>`

## 3. 状态与存储目录结构
- `state/roots.json`: 存储根配置文件（受管目录清单与排除项）
- `state/inventory/`: append-only JSONL 台账和扫描摘要
- `state/quarantine/`: 移出但尚未永久丢弃的隔离暂存区（软防护）
- `state/ops-log.jsonl`: 实际执行的文件转移流水日志

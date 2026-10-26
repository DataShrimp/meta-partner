# TOOLS.md — asset-partner 环境契约（macOS，2026-10-23 实测）

## 角色资产（绝对路径）
- 角色根：`/Users/ryan/Documents/projects/meta-partner/partners/asset-partner/`
- 扫描器：`python3 /Users/ryan/Documents/projects/meta-partner/partners/asset-partner/scripts/scan_storage.py --self-test`（首次先跑自测）
- 台账：`/Users/ryan/Documents/projects/meta-partner/partners/asset-partner/state/inventory/scan-YYYYMMDD-HHMMSS.jsonl` + 同名 `-summary.json`
- 根配置：`/Users/ryan/Documents/projects/meta-partner/partners/asset-partner/state/roots.json`（模板 `state/roots.example.json`，首次复制改名后经用户确认）
- 隔离区：`/Users/ryan/Documents/projects/meta-partner/partners/asset-partner/state/quarantine/<date>/`
- 操作日志：`/Users/ryan/Documents/projects/meta-partner/partners/asset-partner/state/ops-log.jsonl`

## 发现实命令（2026-10-23 已执行验证）
- `df -h` —— Data 卷 362Gi/460Gi（84%），可用 70Gi
- `ls /Volumes/` —— 当前仅 `Macintosh HD`、`Recovery`（无 NAS）
- `mount | grep -Ei 'smbfs|nfs|afp|webdav'` —— 当前唯一网络挂载是 OrbStack NFS（默认排除）
- `ls ~/Library/Mobile Documents` —— iCloud Drive 根；个人云盘在 `~/Library/Mobile Documents/com~apple~CloudDocs`
- `ls ~` —— 顶层含 Documents/Desktop/Downloads/Movies/Music/Pictures/Workspace/Workbuddy 等

## 可用 CLI（已验证存在）
- `python3` → `/usr/bin/python3`（脚本零第三方依赖，PEP 723）
- `jq` → `/usr/bin/jq`；`shasum` → `/usr/bin/shasum -a 256`；`mdfind`/`mdls` → Spotlight 定位与元数据
- 快速定位模板：`mdfind -name <词>`；限定目录：`mdfind -onlyin <dir> '<查询>'`

## 缺失工具（按需补装，装前告知用户）
- `rclone`（未装）—— 云盘/NAS 对账层，`brew install rclone` 后用 `rclone listremotes` 纳管
- `ncdu`（未装）—— 交互式体积分析，非必需（scanner 已覆盖）
- `exiftool`（未装）—— 照片元数据深化，Phase 3 再说

## 处置命令
- 复制校验：`rsync -a --info=stats2 <src>/ <dst>/`，随后比对 `shasum -a 256`
- macOS 可撤销删除：`osascript -e 'tell application "Finder" to delete POSIX file "<path>"'`（入废纸篓，可恢复）
- NEVER 使用 `rm` / `rm -rf`（SOUL 禁令）

## 可复用宿主技能（勿重复造轮子）
`lark-drive`（飞书云盘对账）、`obsidian-cli`（vault 笔记资产）、`office-docx/-xlsx/-pptx`（文档体检）、`json-canvas`/`obsidian-bases`（目录可视化）。

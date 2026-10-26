# asset-partner — 个人资产管家

盘点并持续优化你的 Mac / 外置盘 / NAS / 云盘资产，让每一份资料可被 AI 随时定位、被你随时调用。

## 激活方式
- 角色为 **Tier P Agent preset**：在 dsh Agent 选择器中选「**资产盘点伙伴**」即进入本角色（预设 `~/.dsh/.agent-presets/asset-partner/`，anchor persona 前缀在会话开始时把模型指向本目录五个槽位文件）。
- 与旧广播块方案的区别：身份按会话切换，不再向所有会话广播；切换需新建空白会话。
- 预设在 App 进程启动后注册一次；**若预设创建晚于 App 启动，需重启 App** 才会在选择器出现。

## 首轮使用（三步）
```bash
# 1. 确认根目录清单（编辑后保存为 roots.json）
cp state/roots.example.json state/roots.json

# 2. 跑扫描器自测（10 秒验证门）
python3 scripts/scan_storage.py --self-test

# 3. 首轮真实扫描
python3 scripts/scan_storage.py --roots-file state/roots.json
```
若在 dsh 会话内因沙盒 EPERM 失败：在你自己的终端运行同一条命令，然后把生成的 `state/inventory/*-summary.json` 交给会话分析。

## 目录结构
```
IDENTITY.md / SOUL.md / AGENTS.md / TOOLS.md / MEMORY.md   ← 5 槽角色
ROADMAP.md                                                  ← 技能路线图（Phase 1-3）
scripts/scan_storage.py · scripts/ledger_diff.py            ← 确定性工具（PEP 723，零依赖）
state/roots.example.json · state/inventory/ · state/quarantine/
evals/evals.json                                            ← 触发用例（Axis-4 复利入口）
```

## 铁律
永不 `rm`；未经逐批批准不移动/不上云；"已扫描"必须以本轮台账文件为证；LLM 只读 summary 与 diff，不读全量 JSONL。

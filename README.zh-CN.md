# tidy-data-folders（中文说明）

[![CI](https://github.com/D-sudoasd/tidy-data-folders/actions/workflows/ci.yml/badge.svg)](https://github.com/D-sudoasd/tidy-data-folders/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**面向 AI Agent 的 map-first 文件夹整理技能** — 先计划、**仅执行 `approved=true`**、全程可审计。

[English README](README.md) · [安全说明](docs/SAFETY.md) · [架构](docs/ARCHITECTURE.md) · [脚本索引](docs/SCRIPT_INDEX.md)

<p align="center">
  <img src="assets/readme/hero.svg" alt="tidy-data-folders 概览" width="100%" />
</p>

## 解决什么问题

科研数据盘、桌面 scoop、文献包经常：

- 根目录堆满 PDF / 截图 / 半成品  
- **同一项目**拆在多个平级夹  
- Agent 直接 `Move-Item`，没有批准门、没有日志  

本技能要求：**Survey → Plan → 你批准 → Execute → Audit**，并默认：

- 不删数据文件  
- 不擅自改深层科学叶名（`Az_*.txt`、`.cbf`、run ID 等）  
- 路径必须在选定根目录内（拒绝 `..` / 绝对路径逃逸 / 默认拒绝 symlink）

<p align="center">
  <img src="assets/readme/workflow.svg" alt="工作流" width="100%" />
</p>

## 安装

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git "$env:USERPROFILE\.grok\skills\tidy-data-folders"
```

Codex：

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git "$env:USERPROFILE\.codex\skills\tidy-data-folders"
```

可选（文献/PDF 智能改名质量更好）：

```powershell
pip install -r requirements.txt
```

需要 **Python ≥ 3.10** 与 **PowerShell 7+（`pwsh`）**。

## 和 Agent 怎么用

1. 把本仓库当作 skill 安装（见上）  
2. 对 Agent 说：`整理这个文件夹` / `/tidy-data-folders`  
3. 先看它给的 **计划**（unit 表 + open-first + 路径风险）  
4. 确认后说 **「按方案执行」**  
5. 检查 `MOVE_LOG_*.csv` 与根目录 `README` 的「先看哪里」  

**不要**在未批准时让 Agent 批量 `Rename-Item`。

## 五分钟命令行

```powershell
$Skill = "$env:USERPROFILE\.grok\skills\tidy-data-folders\scripts"
$Root  = "D:\你的乱文件夹"

pwsh -File "$Skill\inventory.ps1" -Root $Root
# 编辑 docs\unit_plan.csv，把要执行的行 approved 改为 true
pwsh -File "$Skill\apply_moves.ps1" -Root $Root -PlanCsv "$Root\docs\unit_plan.csv" -MoveLog "$Root\MOVE_LOG.csv"
pwsh -File "$Skill\empty_shell_sweep.ps1" -Root $Root -AppliedLog "$Root\MOVE_LOG.csv" -MoveLog "$Root\MOVE_LOG.csv"
pwsh -File "$Skill\post_audit.ps1" -Root $Root -RequireReadme -AppliedLog "$Root\MOVE_LOG.csv"
```

合成示例见 [`examples/`](examples/)。

## 关键词

| 词 | 含义 |
|----|------|
| **map-first** | 根目录 60 秒内知道去哪 |
| **unit move** | 整棵同质子树一起搬，一行日志 |
| **open-first** | README 第一行 = 当前最佳产物路径 |
| **path seal** | 数量校验 + 空壳清理 + 配置路径备注 |

## 安全（必读）

详见 [docs/SAFETY.md](docs/SAFETY.md)。

- 只处理 **`approved=true`**  
- 预检失败 → **零移动**（退出码 3）  
- 不自动删除「重复文件」  
- Origin `.opju` 内绝对路径不二进制改写  

**会移动文件。** 重要数据请先备份；可先用未批准计划与 `--what-if`。

## 文档导航

| 文档 | 内容 |
|------|------|
| [SKILL.md](SKILL.md) | Agent 完整工作流与硬规则 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 模块与数据流 |
| [docs/SCRIPT_INDEX.md](docs/SCRIPT_INDEX.md) | 脚本参数与退出码 |
| [HARDENING_20260725b.md](HARDENING_20260725b.md) | 加固工程说明 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 如何贡献 |
| [CHANGELOG.md](CHANGELOG.md) | 版本记录 |

## 许可证

[MIT](LICENSE) © 2026 Delun Gong

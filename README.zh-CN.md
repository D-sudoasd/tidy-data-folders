# tidy-data-folders（中文说明）

[![CI](https://github.com/D-sudoasd/tidy-data-folders/actions/workflows/ci.yml/badge.svg)](https://github.com/D-sudoasd/tidy-data-folders/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PowerShell 7+](https://img.shields.io/badge/pwsh-7%2B-5391FE.svg)](https://github.com/PowerShell/PowerShell)

**面向真实用户与 AI Agent 的安全、可审计文件夹整理工具。** 先调查，逐行批准，先预演，再执行，最后审计。

[English README](README.md) · [命令行指南](docs/CLI.md) · [Agent/维护者指南](AGENTS.md) · [安全说明](docs/SAFETY.md) · [架构](docs/ARCHITECTURE.md) · [更新记录](CHANGELOG.md)

<p align="center">
  <img src="assets/readme/hero.svg" alt="tidy-data-folders：调查、计划、批准、预演、执行、审计" width="100%" />
</p>

科研数据盘、文献目录和桌面临时文件常见以下问题：根目录堆积过多文件，同一项目分散在多个目录，文档文件名无法识别，移动操作缺少可靠记录。

本项目采用固定流程：

```text
调查 → 制订计划 → 批准选定行 → 预演 → 执行 → 审计
```

常规流程不删除数据文件；默认保留深层科研数据文件名；计划中的源路径和目标路径必须相对选定根目录；实际操作写入统一移动日志。

## 选择入口

| 使用场景 | 建议入口 |
|---|---|
| 让 AI Agent 整理文件夹 | 将仓库安装为技能，让 Agent 读取 [`SKILL.md`](SKILL.md) |
| 自己使用命令行 | 使用统一入口 [`scripts/tidy.py`](scripts/tidy.py)，完整说明见 [`docs/CLI.md`](docs/CLI.md) |
| 维护或集成项目 | 先读 [`AGENTS.md`](AGENTS.md)，再读 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| 审查安全边界 | 阅读 [`docs/SAFETY.md`](docs/SAFETY.md) 与 [`tests/`](tests/) |

## 安装

### 命令行使用

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git
cd tidy-data-folders
python scripts/tidy.py doctor
```

Windows 可将 `python` 替换为 `py -3`。

### Grok / 本地 Agent 技能

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git "$env:USERPROFILE\.grok\skills\tidy-data-folders"
```

### Codex

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git "$env:USERPROFILE\.codex\skills\tidy-data-folders"
```

已经通过 git 安装时，在仓库目录执行 `git pull` 即可更新。

### 可选文档解析依赖

```powershell
pip install -r requirements.txt
```

| 包 | 功能 |
|---|---|
| `pypdf` | PDF 元数据与文本信号 |
| `python-docx` | DOCX 元数据与文本信号 |
| `python-pptx` | PPTX 元数据信号 |

文件清点与目录单元移动不依赖这些包。

## 文件夹整理：安全起步

先设置仓库路径和待整理目录：

```powershell
$Tidy = "D:\tools\tidy-data-folders"
$Root = "D:\work\messy-project"
```

### 1. 检查运行环境

```powershell
python "$Tidy\scripts\tidy.py" doctor
```

机器可读结果：

```powershell
python "$Tidy\scripts\tidy.py" doctor --json
```

### 2. 调查目录，不改动文件

```powershell
python "$Tidy\scripts\tidy.py" survey --root $Root
```

供 Agent 或其他程序读取的 JSON：

```powershell
python "$Tidy\scripts\tidy.py" survey --root $Root --json
```

### 3. 生成单元移动计划模板

```powershell
python "$Tidy\scripts\tidy.py" init-unit-plan --root $Root
```

命令会生成 `docs/unit_plan.csv`。模板包含一行 `approved=false` 的占位示例。删除或替换该行，再按“一个完整文件或目录树对应一行”的方式添加计划。

```csv
plan_version,plan_id,row_id,approved,src,dst,kind,reason
1,cleanup-01,1,false,inbox/sample_A,01_projects/sample_A,move,将同一项目目录归入统一位置
```

审阅期间保持 `approved=false`。只把确认接受的行改为 `approved=true`。

### 4. 预演已批准行

```powershell
python "$Tidy\scripts\tidy.py" apply-moves `
  --root $Root `
  --plan "docs\unit_plan.csv"
```

`apply-moves` 默认进入预演模式。底层脚本会完成全部预检，并输出预计操作，不移动文件。

### 5. 执行

```powershell
python "$Tidy\scripts\tidy.py" apply-moves `
  --root $Root `
  --plan "docs\unit_plan.csv" `
  --execute
```

实际执行同时要求：

- 计划行的 `approved=true`
- 命令包含 `--execute`

`--execute` 不会绕过逐行批准条件。

### 6. 预演空目录清理并审计

```powershell
python "$Tidy\scripts\tidy.py" sweep `
  --root $Root `
  --move-log "$Root\MOVE_LOG_YYYYMMDD_tidy.csv"

python "$Tidy\scripts\tidy.py" audit `
  --root $Root `
  --move-log "$Root\MOVE_LOG_YYYYMMDD_tidy.csv" `
  --require-readme
```

确认清理预演结果后，再给 `sweep` 添加 `--execute`。统一入口只清理移动日志能够证明与已执行计划相关的空父目录。

## 文档识别与改名计划

对 PDF、DOCX 和其他受支持文档生成未批准计划：

```powershell
python "$Tidy\scripts\tidy.py" plan-docs --root $Root
```

默认行为：

- 输出 `docs/DOC_RENAME_PLAN.csv`
- 所有 `approved` 值均为 `false`
- 元数据写入临时 JSONL，计划生成后删除
- 不保存文档正文片段
- 低置信度文件进入人工复核或 `to_sort`

预演已批准的文档操作：

```powershell
python "$Tidy\scripts\tidy.py" apply-docs `
  --root $Root `
  --plan "docs\DOC_RENAME_PLAN.csv"
```

审阅后执行：

```powershell
python "$Tidy\scripts\tidy.py" apply-docs `
  --root $Root `
  --plan "docs\DOC_RENAME_PLAN.csv" `
  --execute
```

配置文件名风格、目录布局、元数据保留、精确 `plan_id` 绑定和审计参数见 [`docs/CLI.md`](docs/CLI.md)。

## 关键保护措施

| 风险 | 保护措施 |
|---|---|
| 未了解目录就开始移动 | 先调查并形成计划 |
| CSV 中所有行被直接执行 | 只有 `approved=true` 的行具备执行资格 |
| 误触发实际操作 | 移动、改名和空目录清理默认预演 |
| 绝对路径或越界路径 | 拒绝绝对路径、UNC 路径和包含 `..` 的计划路径 |
| 错误计划导致部分移动 | 首次移动前完成全部已批准任务的预检 |
| 覆盖已有目标 | 目标已存在时拒绝执行 |
| 计划生成后源文档发生变化 | 文档操作核对文件大小与完整 SHA-256 |
| 操作没有记录 | 已执行操作写入 12 列 `MOVE_LOG` |
| 自动删除重复文件 | 常规流程不自动删除数据文件 |
| 大范围删除空目录 | 常规清理限定为计划或日志能够证明的相关父目录 |

<p align="center">
  <img src="assets/readme/workflow.svg" alt="调查、计划、批准、预演、执行、审计工作流" width="100%" />
</p>

## 整理后的可理解性

<p align="center">
  <img src="assets/readme/before-after.svg" alt="根目录整理前后对比" width="100%" />
</p>

目标目录采用根目录导向的结构：用户在一分钟内能够判断原始数据、处理过程、当前结果和历史归档的位置。完整且同质的目录树按单元移动处理；当前产物放在根目录说明能够直接指向的位置；历史内容保留，但不与当前工作混在同一入口。

## 模式与配置类型

| 模式 | 输出 |
|---|---|
| `survey` | 仅清点目录 |
| `plan` | 目录分类、单元移动、路径风险、可选文档操作 |
| `execute` | 执行已批准操作，生成日志和目录说明 |
| `audit` | 核对数量、计划、日志、放置位置和入口说明 |
| `docs-identify` / `rename-docs` | 只做文档识别与改名流程 |
| `desktop` | 将桌面或下载目录收入按日期划分的入口目录 |

配置类型用于提供领域目录建议，安全执行逻辑保持一致：

`generic` · `literature-dump` · `desktop-dump` · `manuscript-heavy` · `sxrd-texture` · `sxrd-tensile`

详细定义见 [`references/profiles.md`](references/profiles.md)。

## 统一入口与底层脚本

推荐从统一入口开始：

```powershell
python scripts/tidy.py --help
python scripts/tidy.py guide
```

统一入口调用以下加固脚本：

| 脚本 | 职责 |
|---|---|
| `inventory.ps1` | 文件数量、扩展名统计、配置类型提示 |
| `apply_moves.ps1` | 已批准单元移动与完整预检 |
| `extract_doc_meta.py` | PDF、DOCX、PPTX 元数据提取 |
| `propose_doc_renames.py` | 生成未批准文档计划 CSV |
| `apply_doc_renames.py` | 已批准文档操作与 SHA 校验 |
| `empty_shell_sweep.ps1` | 清理已执行操作留下的相关空目录 |
| `post_audit.ps1` | 数量、计划、日志、放置位置与入口说明审计 |
| `scan_path_refs.ps1` | 查找移动后可能失效的路径引用 |
| `path_safety.py` | Python 路径、动作、哈希和日志公共规则 |

底层参数与退出码见 [`docs/SCRIPT_INDEX.md`](docs/SCRIPT_INDEX.md)。

## 安全边界

重要数据使用前先读 [`docs/SAFETY.md`](docs/SAFETY.md)。工程加固说明见 [`HARDENING_20260725b.md`](HARDENING_20260725b.md)。

当前支持在一个选定根目录内执行受控移动和改名、逐行批准、预演、日志和审计。当前范围不包括云同步恢复、Origin `.opju` 二进制编辑、任意配置文件路径重写、跨卷事务和外部引用自动恢复。

工具在显式执行后会移动文件。不可替代的数据应保留独立备份，并先完成预演。

## 测试

```powershell
python -m unittest discover -s tests -v
python -m py_compile scripts/tidy.py
python scripts/tidy.py --help
```

持续集成在 Python 3.10–3.12 上运行单元测试。

## 仓库结构

```text
SKILL.md                  Agent 工作流与硬规则
AGENTS.md                 Agent 与维护者快速入口
README.md · README.zh-CN.md
scripts/tidy.py           默认预演的统一命令行入口
scripts/                  PowerShell 与 Python 执行工具
docs/CLI.md               命令行完整指南
docs/                     架构、安全说明、脚本索引
references/               配置类型、命名规则、模板与领域经验
examples/                 合成示例目录与示例计划
tests/                    安全测试与统一入口测试
```

## 常见问题

**会自动删除数据文件吗？**  
不会。空目录可在预演后通过限定范围的清理命令移除。

**不使用 AI Agent 能否完成完整流程？**  
可以。`scripts/tidy.py` 提供完整命令行入口。

**AI 能否读取结构化结果？**  
可以。`doctor --json` 和 `survey --json` 分别输出机器可读的环境检查与目录清点结果。计划 CSV 与 `MOVE_LOG` 数据契约见 [`AGENTS.md`](AGENTS.md)。

**是否只支持 Windows？**  
PowerShell 层针对 Windows 路径与重解析点行为设计，并要求 PowerShell 7。Python 文档工具可跨平台运行。完整单元移动和审计流程当前依赖 `pwsh`。

**个人默认配置放在哪里？**  
将 `USER.example.md` 复制为本地 `USER.md`。该文件已被 git 忽略，不应提交个人路径。

## 贡献

阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md) 与 [`AGENTS.md`](AGENTS.md)。安全问题按照 [`SECURITY.md`](SECURITY.md) 提交。

## 许可证

[MIT](LICENSE) © 2026 Delun Gong

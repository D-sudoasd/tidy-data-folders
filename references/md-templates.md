# Markdown deliverable templates

Write real content from inventory. Dense tables; skip empty sections.

## README.md / README_PROJECT_MAP.md

```markdown
# <ProjectID> 项目地图

更新：YYYY-MM-DD（整理后）  
**STATUS：** <一句话：完成度 · CURRENT 在哪 · scientific_ok 等>

## 先看哪里

| 目的 | 路径 |
|------|------|
| **★ CURRENT 主产物（先开这个）** | `05_…/production/exports_full/…` |
| 总入口（本文件） | `README.md` |
| Agent | `AGENTS.md` |
| 旧路径对照 | `docs/ARCHIVE_MAP.md` |
| 移动日志 | `MOVE_LOG_YYYYMMDD_….csv` |

## 一分钟树

```text
ProjectRoot/
  README.md
  01_…
  99_archive/
```

## 一级目录

| 目录 | 用途 | CURRENT? |
|------|------|----------|
| `01_…` | … | |
| `05_…/production/` | … | **是** |
| `…/pilot_*` | … | 否 |

## 样品 / 条件一览（如有）

| ID | 帧数/规模 | 主路径 | 备注 |
|----|-----------|--------|------|

## 命名约定（本项目）

| 标签 | 含义 |
|------|------|

## 整理原则

- 只移动，不删除数据；空目录可扫除
- 深层科学数据文件名保持不变
- **unit move** 日志：`MOVE_LOG_….csv`
- 回滚：按 MOVE_LOG 反向移动

## 路径说明

- 历史 agent 报告中的旧盘符/旧 work_dir **非 authoritative**
- 重跑请用本 README / AGENTS 中的新绝对路径
```

**Open-first rule:** row-1 path must exist on disk after execute.

## AGENTS.md (scientific)

```markdown
# AGENTS.md — <short name>

Scientific data workspace (not an app repo).
**Language:** Chinese notes OK; paths and sample IDs exact.

## 1. What this is
| Item | Value |
|------|--------|
| Sample(s) | |
| CURRENT product | |
| Do not treat as CURRENT | pilot/, 99_archive/, tmp/ |

## 2. Read order
1. This file
2. README.md
3. CURRENT product path only

## 3. Directory roles
(short tree)

## 4. Hard boundaries
- No inventing samples/frame counts
- Leaf scientific names stay
- Path maps: MOVE_LOG + docs/ARCHIVE_MAP.md
```

## FILE_MAP.md

```markdown
# FILE_MAP — path crosswalk

| Short ID | Spectra / CBF | Mechanical | MAUD / texture | Notes |
|----------|---------------|------------|----------------|-------|
```

## docs/ARCHIVE_MAP.md (unit table only)

```markdown
# 归档对照 YYYY-MM-DD

| 旧路径（单元） | 新路径 | 角色 |
|----------------|--------|------|
| `NOHR/` | `03_raw_cbf/NOHR/` | raw |
| `MAUD_ESG/NOHR/texture_results/full_37x72/` | `05_…/production/full_37x72/` | CURRENT |

叶文件名未改。逐条见 MOVE_LOG（unit 级）。
```

Do **not** paste 100 leaf CSV lines into ARCHIVE_MAP.

## PATH_NOTES.md (Origin)

```markdown
# Origin 路径说明
| 工程 | 原位置 | 现位置 | 依赖数据 |
|------|--------|--------|----------|
```

## docs/PATH_REWRITE_YYYYMMDD.md

```markdown
# 配置路径改写
| 文件 | 旧前缀 | 新前缀 |
|------|--------|--------|
```

## PLACEMENT_AUDIT

Prefer running `scripts/post_audit.ps1` and paste `AUDIT_RESULT` summary; optional short md.

## MOVE_LOG CSV（统一 12 列）

```csv
run_id,plan_id,row_id,timestamp_utc,src,dst,kind,status,reason,error,sha256_before,sha256_after
r1,p1,1,2026-07-14T12:00:00Z,old,01_raw/old,move,applied,wrap raw series,,,
r1,,2,2026-07-14T12:01:00Z,empty,(removed empty shell),shell_remove,applied,empty after promote,,,
```

`status` ∈ `preflight_ok|applied|failed|rolled_back|rollback_failed`  
`kind` ∈ `move|rename_parent|archive|shell_remove|path_rewrite|doc_rename`

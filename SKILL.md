---
name: tidy-data-folders
description: >
  Survey, classify, rename documents by content, reorganize, and document messy
  folders or desktop dumps into a map-first numbered layout with unit MOVE_LOG,
  path seal, open-first maps, and document-identity renames (PDF/Word/Office).
  Use when the user asks to 整理文件夹, 归纳数据, 重命名目录, 重命名PDF, 重命名论文,
  文献文件名, main.pdf, ScienceDirect文件名, 整理并改名, 桌面乱文件, 分类清晰,
  命名清楚, 写项目地图/README_PROJECT_MAP/AGENTS/FILE_MAP/ARCHIVE_MAP, reorganize
  scientific or general data workspaces, smart rename papers/docs, or runs
  /tidy-data-folders.
---

# Tidy Data Folders

Inspect → plan → wait for user approval /「按方案执行」→ preview → execute → audit.

Default public entry (this repository’s `scripts/`):

```text
python scripts/tidy.py doctor
python scripts/tidy.py survey --root <folder> --json
python scripts/tidy.py init-unit-plan --root <folder>
python scripts/tidy.py plan-docs --root <folder>
python scripts/tidy.py apply-moves --root <folder> --plan <csv>
python scripts/tidy.py apply-docs --root <folder> --plan <csv>
python scripts/tidy.py sweep --root <folder> --move-log <csv>
python scripts/tidy.py audit --root <folder>
```

`apply-moves`, `apply-docs`, and `sweep` are previews until `--execute`. `--execute` does not bypass `approved=true`.

Do not hand-loop `Rename-Item` / `Move-Item`. Do not call apply scripts until a plan exists and the user approved it.

## 1. Survey first

On an unknown folder, survey before planning or moving:

```text
python scripts/tidy.py survey --root <folder> --json
```

Consume the JSON. Keep these existing keys:

- `file_count`, `document_class_count`, `publisher_id_name_count`, `junk_doc_name_count`
- `suggested_profile`, `phase_d_policy`
- `extensions`, `existing_maps`, `listing`

When present, also use:

- `background_competition`, `competing_backgrounds`, `background_signals`
- `profile_confidence`, `layout_guidance`, `observed_clusters`

Record `file_count` as the before-count. Reuse language from `existing_maps`.

## 2. Map intent to a mode

| User intent | Mode | What you run |
|---|---|---|
| 看看 / 盘点 / 这是什么 | `survey` | `survey --json` only |
| 整理 / 规划 / 怎么归 | `plan` | survey, then unit and/or doc plan; **wait** |
| 只改 PDF / 论文 / 文献名 | `rename-docs` | `plan-docs`; **wait** |
| 桌面 / Downloads 乱文件 | `desktop` | survey; inbox buckets from `desktop-dump` in profiles.md |
| 检查 / 验收 | `audit` | `audit` after a log or plan exists |

Default for「整理这个文件夹」: **survey → plan → wait**.
Never enter execute from a first message.

## 3. Adapt the background — do not paste a spine

Named profiles and their slots live in [references/profiles.md](references/profiles.md). Read that file after survey. Do not copy SXRD or literature folder trees into the plan unless survey says that profile won clearly.

- If `layout_guidance` is `use_named_profile` and `profile_confidence` is `high`, use that profile’s slots.
- If `background_competition` is true, `profile_confidence` is `contested` or `low`, or `suggested_profile` is `generic`, **adapt slots from `observed_clusters` and the listing**. Do not force `sxrd-texture` or `literature-dump` onto an unmatched or mixed tree.
- `phase_d_policy` from survey is the document-rename default. Mixed or generic stays optional until the user asks or a document cluster is clearly the job.

## 4. Plan, then wait

Show the user:

1. Before / after one-minute trees
2. Open-first CURRENT path
3. CURRENT vs non-CURRENT
4. Unit-move table only (`src → dst · reason`) — whole trees, not scientific leaves
5. Path-risk list when moves change config-used paths (`scripts/scan_path_refs.ps1` if needed)
6. Docs to write + residual risks
7. Document rename table when Phase D is on: `src → dst · doc_type · confidence · action · reason`.
   `action` ∈ `rename|normalize|move_only|keep|review|protected`

Classify top items: `unit-move` | `rename-parent` | `archive` | `leave` | `ask-user` | `doc-rename`.

Create unapproved CSVs with the public launcher:

```text
python scripts/tidy.py init-unit-plan --root <folder>
python scripts/tidy.py plan-docs --root <folder>
```

Set `approved=true` only after the user accepts that row (or says 按方案执行). Do not invent DOI/year. Low confidence → `review` / `to_sort`, keep basename.

`plan-docs` `--slot-layout literature-dump` is for a winning literature dump only. Use `--slot-layout none` when the folder is mixed, generic, or the user only wants names.

## 5. Preview, then execute

```text
python scripts/tidy.py apply-docs --root <folder> --plan docs/DOC_RENAME_PLAN.csv
python scripts/tidy.py apply-moves --root <folder> --plan docs/unit_plan.csv
python scripts/tidy.py sweep --root <folder> --move-log <MOVE_LOG>
python scripts/tidy.py audit --root <folder> --before-count <N> --move-log <MOVE_LOG>
```

Add `--execute` only after approval. Preflight failure → zero moves. Empty-shell sweep only for parents evidenced by the applied log. Do not use aggressive whole-tree wipe.

## Safety

1. Survey and plan before any mutation.
2. Only `approved=true` rows execute.
3. `src`/`dst` are root-relative; no `..`, no absolute escapes, no symlink traversal.
4. Never auto-delete data files. Empty dirs only via scoped sweep.
5. Preserve deep scientific leaf names (`Az_*.txt`, `.cbf`, run folders, sample IDs) unless the row is an approved document-class rename.
6. Unified 12-column `MOVE_LOG` only; do not change its header.
7. Do not overwrite existing `README.md` / `AGENTS.md` — write `TIDY_FOLDER_MAP.md` or a dated map.
8. Network metadata lookup stays off unless the user enables it.
9. `tmp/` is never a data entry. Do not invent science.

## Output

- Chinese when the user writes Chinese. Paths exact.
- After execute: N unit moves, M doc_renames, open-first path, MOVE_LOG path, audit PASS/FAIL, residual `to_sort`.
- Do not paste the full MOVE_LOG.

## Anti-patterns

- Skipping survey, or locking mixed folders to the first SXRD / literature regex
- Executing without approval or preview
- Renaming scientific leaves or inventing titles / DOIs
- Deleting “duplicates”
- Hand-written bulk rename / move
- Claiming path-rewrite audit pass when rewrite was not run

Satisfaction gates: [references/satisfaction-checklist.md](references/satisfaction-checklist.md).
Naming / identity: [references/naming-conventions.md](references/naming-conventions.md), [references/doc-identity.md](references/doc-identity.md).

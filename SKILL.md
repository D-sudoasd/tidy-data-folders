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

**Map-first** reorg: numbered slots, **unit moves**, **document-identity renames**,
**path seal**, **open-first** README, **promote** CURRENT (`production`/`best`)
vs pilot/archive.

Encodes map-first layout language for scientific and desktop dump folders.
Lessons from real SXRD/texture reorgs: [references/lessons.md](references/lessons.md).

Skill root: resolve via this skill’s install path (`scripts/` next to `SKILL.md`;
PowerShell `$PSScriptRoot`).  
Scripts: `scripts/*` (prefer these over ad-hoc shell). **Never** hand-loop 50×
`Rename-Item` / `Move-Item` for document renames — use the doc scripts.

**Safety (non-negotiable):** all `src`/`dst` are root-relative; no `..`, no absolute
escapes; full preflight before any move; only `approved=true` rows; refuse if source
size/sha256 changed; zero partial apply on preflight failure.

## Leading words

| Word | Means |
|------|--------|
| **map-first** | Root answers “where do I go?” in &lt;60s |
| **unit move** | Move whole homogeneous trees; one MOVE_LOG row each |
| **doc rename** | Semantic rename of **document-class** files by content identity |
| **path seal** | Before/after counts + empty-shell sweep + config path rewrite |
| **open-first** | README row-1 = single best CURRENT artifact that exists on disk |
| **promote** | Formal results under `production`/`best`/CURRENT — not buried |

## Hard rules

1. **Plan before move/rename.** Survey → plan (7 blocks when docs on) → user approve /「按方案执行」→ execute.  
2. **Move, do not delete data.** Empty shells only via sweep (empty dirs, never files). Never auto-delete “duplicates.”  
3. **Preserve deep scientific leaf names** (frames, run folders, sample IDs, `Az_*.txt`, `.cbf`).  
   **May rename document-class only** when Phase D on: auto extract for PDF/DOCX/(optional)PPTX;  
   `.doc`/`.ppt`/`.xlsx` default `review` (no silent semantic rename).  
4. **Unit MOVE_LOG** — **unified 12-column header** for doc rename, unit move, shell remove:  
   `run_id,plan_id,row_id,timestamp_utc,src,dst,kind,status,reason,error,sha256_before,sha256_after`  
   `kind` ∈ `move|rename_parent|archive|shell_remove|path_rewrite|doc_rename`.  
   Append only after header validation; status ∈ `preflight_ok|applied|failed|rolled_back|…`.  
5. **ASCII-first** new folder names; Chinese OK in Markdown and in doc short titles when present.  
6. **`tmp/` is never a data entry.**  
7. **Do not invent science** or DOI/year. Low confidence → `review` / `to_sort` **keep basename**.  
8. **Windows-safe** moves/renames; Origin → `PATH_NOTES.md`.  
9. **Satisfaction contract** — see [satisfaction-checklist.md](references/satisfaction-checklist.md).  
10. Read [USER.example.md](USER.example.md) defaults; optional local `USER.md` only if user created it.  
11. **Do not overwrite** existing `README.md` / `AGENTS.md` without approval — prefer `TIDY_FOLDER_MAP.md` or dated maps.  
12. **Network metadata lookup default off**; ask before any Crossref/OpenAlex.  
13. **Empty-shell sweep** only for parents of planned moves (not whole-tree wipe).

## Modes

| Mode | Goal |
|------|------|
| **survey** | Inventory only (includes document-class signals) |
| **plan** | Taxonomy + unit map + path risks + **doc rename table**; no moves |
| **execute** | Approved plan + Phase D renames + seal + docs |
| **document** | Maps only |
| **audit** | `post_audit.ps1` + checklist |
| **desktop** | Desktop/Downloads → inbox buckets |
| **docs-identify** | Document metadata table only (no unit-move plan) |
| **rename-docs** | Document identify + rename plan/apply only (no spine reorg) |

Default for「整理这个文件夹」: **survey → plan → wait**.  
Default for「只改 PDF 名」: **rename-docs** (plan → wait).  
`literature-dump` profile: plan always includes Phase D (block 7).

## Workflow

### Step 0 — Profile

**Done when:** one profile chosen and slots loaded.

Signals → profile: [references/profiles.md](references/profiles.md)  
(`sxrd-texture` · `sxrd-tensile` · `manuscript-heavy` · `desktop-dump` · `literature-dump` · `generic`)

Tensile/MAUD detail: [references/domain-slots-sxrd.md](references/domain-slots-sxrd.md)  
Naming: [references/naming-conventions.md](references/naming-conventions.md)  
Doc identity: [references/doc-identity.md](references/doc-identity.md)

**Phase D policy by profile** (see profiles.md):

| Profile | Document rename |
|---------|-----------------|
| `literature-dump` | **On** by default |
| `desktop-dump` | On for `docs/` bucket |
| `manuscript-heavy` | References only; never CURRENT draft unless user asks |
| `sxrd-*` | **Off** unless user explicitly enables |
| `generic` | Optional when document-class cluster detected |

### Step 1 — Inventory

**Done when:** file count + profile + listing exist (script output preferred).

```powershell
$SkillScripts = Join-Path (Split-Path -Parent $PSScriptRoot) "scripts"  # or skill install …/scripts
# Prefer: $SkillScripts = "<this-skill>\scripts"
pwsh -File "$SkillScripts\inventory.ps1" -Root "<ROOT>"
# optional JSON:
pwsh -File "$SkillScripts\inventory.ps1" -Root "<ROOT>" -Json
```

Record **before_file_count**. Note existing maps; reuse language.  
Note `document_class_count`, `publisher_id_name_count`, `suggested_profile`.

### Step 2 — Plan (seven blocks when Phase D on; six when off)

**Done when:** user sees all required blocks:

1. **Before / after** one-minute trees (root)  
2. **Open-first** list (row-1 CURRENT path)  
3. **CURRENT vs non-CURRENT**  
4. **Unit-move table** only (`src → dst · reason`) — no leaf rows for data trees  
5. **Path-risk list** — run scan:  

```powershell
pwsh -File "...\scan_path_refs.ps1" -Root "<ROOT>" -OldRoots "<old1>","<old2>"
```

Details: [references/path-risks.md](references/path-risks.md)

6. **Docs to write** + residual risks (Origin, open files, external repos)  
7. **Document rename table** (required when Phase D on):  
   `src → dst · doc_type · confidence · action · reason`  
   `action` ∈ `rename|normalize|move_only|keep|review|protected`

Classify each top item: `unit-move` | `rename-parent` | `archive` | `leave` | `ask-user` | `doc-rename`.

#### Phase D — produce rename plan (scripts)

```powershell
$SkillScripts = "<path-to-skill>\scripts"   # directory containing these .py files
$py = (Get-Command py, python, python3 -ErrorAction SilentlyContinue | Select-Object -First 1).Source
# meta default: OS temp (no text_snip). Persist plan under docs/ only.
& $py "$SkillScripts\extract_doc_meta.py" --root "<ROOT>"
# note printed temp JSONL path, then:
& $py "$SkillScripts\propose_doc_renames.py" --root "<ROOT>" --meta "<meta.jsonl>" --out "<ROOT>\docs\DOC_RENAME_PLAN.csv" --profile academic --slot-layout literature-dump
```

Plan columns include `approved` (**default false**), `row_id`, `plan_id`, `src_sha256`, `action`
∈ `rename|normalize|move_only|keep|review|protected`.  
Agent may refine titles (no invented DOI/year). Show high-risk / low-confidence rows in chat; full CSV on disk.  
After user approval, set `approved=true` only on chosen rows (new plan_id if regenerating).

### Step 3 — Execute

**Done when:** renames/moves logged; empty shells gone; config paths rewritten; count not dropped.

Order:

1. Create spine directories.  
2. **Document renames** (preflight-all, then apply; only `approved=true`):  

```powershell
& $py "$SkillScripts\apply_doc_renames.py" --root "<ROOT>" --plan "<ROOT>\docs\DOC_RENAME_PLAN.csv" --move-log "<ROOT>\MOVE_LOG_YYYYMMDD_tidy.csv" --what-if
& $py "$SkillScripts\apply_doc_renames.py" --root "<ROOT>" --plan "..." --move-log "..."
# actions: rename,normalize,move_only
```

Preflight failure → exit 3, **zero** moves.  
3. **Unit moves** — `apply_moves.ps1` (**only `approved=true`**; missing `approved` column fails; relative paths only; reparse/symlink refused):

```powershell
pwsh -File "$SkillScripts\apply_moves.ps1" -Root "<ROOT>" -PlanCsv "<unit_plan.csv>" -MoveLog "<MOVE_LOG>"
# unit_plan.csv must include approved,src,dst; optional kind/action,row_id,plan_id
```

4. **Empty-shell sweep** — prefer AppliedLog `status=applied` parents (not full-tree):

```powershell
pwsh -File "$SkillScripts\empty_shell_sweep.ps1" -Root "<ROOT>" -AppliedLog "<MOVE_LOG>" -MoveLog "<MOVE_LOG>"
# or -PlanCsv with approved rows only; -Aggressive requires -AggressiveConfirm I_UNDERSTAND_FULL_TREE_SWEEP
```

5. **Path rewrite** — config-class only when a rewrite script/plan exists.  
   **Not yet automated in-package:** do not claim `AUDIT_RESULT: PASS` for path rewrite until done and verified.  
6. Validate rewritten JSON parses when rewrite ran.

### Step 4 — Documents (satisfaction)

**Done when:** [satisfaction-checklist.md](references/satisfaction-checklist.md) gates pass.

| File | When |
|------|------|
| `README.md` or `TIDY_FOLDER_MAP.md` | Prefer new/dated map if README already exists |
| `MOVE_LOG_*.csv` | If moves or doc_renames |
| `docs/DOC_RENAME_PLAN.csv` | If Phase D ran |
| `docs/ARCHIVE_MAP.md` | Unit old→new (not CSV dump) |
| `AGENTS.md` | Scientific only when user asks or profile clearly needs it; never overwrite existing |
| `FILE_MAP.md` | Multi-sample crosswalk |
| `PLACEMENT_AUDIT_*.md` / audit script output | Large jobs |

Templates: [references/md-templates.md](references/md-templates.md)

### Step 5 — Audit

**Done when:** `AUDIT_RESULT: PASS` (or failures listed and fixed).

```powershell
pwsh -File "$SkillScripts\post_audit.ps1" -Root "<ROOT>" -BeforeCount <N> `
  -DocRenamePlan "<ROOT>\docs\DOC_RENAME_PLAN.csv" -AppliedLog "<MOVE_LOG>" `
  -Profile literature-dump -CheckPaths "01_papers\..."
```

For `literature-dump`: no publisher-junk names at root; low-confidence files under `to_sort/`.

## Desktop special case

Dated inbox under stable library; buckets `images/ docs/ data/ archives_zip/ installers/ to_sort/`.  
Ambiguous → `to_sort/` + questions. Promote only after user names project.  
After bucketing, Phase D on `docs/` when user wants readable names.

## Output to user

- Chinese when user writes Chinese.  
- Paths exact.  
- After execute: N **unit** moves, M **doc_renames**, open-first path, MOVE_LOG path, audit PASS/FAIL, residual risks / `to_sort` count.  
- Do not paste full MOVE_LOG (summarize; full CSV on disk).

## Anti-patterns

- Leaf-walking MOVE_LOG / renaming `Az_*.txt` or CBF names  
- Renaming document-class without plan gate  
- Inventing titles/years/DOIs when extract failed  
- Promoting **empty** parent dirs  
- Bulk data left at root  
- Docs without open-first CURRENT  
- Plan without path-risk scan (when moves change paths used by configs)  
- Deleting “duplicates” without proof + user OK  
- Treating `tmp/` or historical agent workdirs as CURRENT  
- Hand-written bulk Rename-Item instead of scripts  
- Applying plan rows without `approved=true`  
- Claiming path-rewrite audit pass without a rewrite tool/run  
- Whole-tree empty-dir wipe (`-Aggressive` only if user demands)  

## Completion definition

1. Mode deliverable done (plan waited if required),  
2. Path seal held (plan-item checks + sweep of **planned** shells; rewrite only if actually run),  
3. Satisfaction contract met (root purity + open-first real + doc names when Phase D on),  
4. User can find raw → process → **promoted** product (or named papers) without asking.

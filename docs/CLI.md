# Unified command-line guide

`scripts/tidy.py` gives people and agents one stable entry point while preserving the existing hardened PowerShell and Python apply scripts.

## Requirements

- Python 3.10 or newer
- PowerShell 7 (`pwsh`) for survey, unit moves, empty-directory sweep, and audit
- Optional document extractors from `requirements.txt` for PDF, DOCX, and PPTX signals

Run the environment check first:

```powershell
python scripts/tidy.py doctor
```

For a machine-readable result with `schema_version: 1`:

```powershell
python scripts/tidy.py doctor --json
```

## Path behavior

`--root` selects the folder being organized. Relative plan and log paths are interpreted from that root:

```powershell
python scripts/tidy.py apply-moves `
  --root "D:\work\project" `
  --plan "docs\unit_plan.csv"
```

The plan above resolves to `D:\work\project\docs\unit_plan.csv`. Relative control paths cannot escape `--root` through `..` or a resolved link. Explicit absolute plan or log paths remain available when external storage is intentional.

## Folder reorganization

### 1. Survey

```powershell
python scripts/tidy.py survey --root "D:\work\project"
```

Use JSON when an agent or another tool will consume the inventory:

```powershell
python scripts/tidy.py survey --root "D:\work\project" --json
```

Record `file_count` before execution when count sealing is required.

### 2. Create a unit-plan template

```powershell
python scripts/tidy.py init-unit-plan --root "D:\work\project"
```

The command writes `docs/unit_plan.csv` with the recommended columns and one placeholder row whose `approved` value is `false`. Replace or delete that row, then add one row per whole-file or whole-directory move.

Example:

```csv
plan_version,plan_id,row_id,approved,src,dst,kind,reason
1,project-cleanup-01,1,false,inbox/sample_A,01_projects/sample_A,move,group one project tree
1,project-cleanup-01,2,false,old_results,99_archive/old_results,archive,retain historical output
```

Keep every row unapproved while reviewing the plan. Change only accepted rows to `approved=true`.

### 3. Preview approved unit moves

```powershell
python scripts/tidy.py apply-moves `
  --root "D:\work\project" `
  --plan "docs\unit_plan.csv"
```

Preview is the default. The underlying apply script performs full preflight and reports `WHATIF` rows without moving files.

### 4. Execute approved unit moves

```powershell
python scripts/tidy.py apply-moves `
  --root "D:\work\project" `
  --plan "docs\unit_plan.csv" `
  --execute
```

`--execute` does not approve rows. The underlying script still accepts only `approved=true` and still applies its path, destination, overlap, fingerprint, and log checks.

## Document identification and rename planning

Create an unapproved document plan in one command:

```powershell
python scripts/tidy.py plan-docs --root "D:\papers\incoming"
```

Default outputs and behavior:

- Plan: `docs/DOC_RENAME_PLAN.csv`
- Metadata: temporary JSONL deleted after plan creation
- Recursive scan: enabled
- Plan approvals: all `false`
- Text snippets: not persisted
- Slot layout: `literature-dump`

Useful options:

```powershell
python scripts/tidy.py plan-docs `
  --root "D:\papers\incoming" `
  --profile human `
  --slot-layout none `
  --out "docs\DOC_RENAME_PLAN_human.csv"
```

Preserve metadata only when it is needed for review:

```powershell
python scripts/tidy.py plan-docs `
  --root "D:\papers\incoming" `
  --meta-out "docs\doc_meta.jsonl"
```

`--include-text-snip` persists extracted document text in metadata and should be selected only when that content may be stored in the chosen location.

Preview approved document actions:

```powershell
python scripts/tidy.py apply-docs `
  --root "D:\papers\incoming" `
  --plan "docs\DOC_RENAME_PLAN.csv"
```

Execute after review:

```powershell
python scripts/tidy.py apply-docs `
  --root "D:\papers\incoming" `
  --plan "docs\DOC_RENAME_PLAN.csv" `
  --execute
```

Use `--plan-id <id>` when the apply step must bind to one exact plan generation.

## Empty-directory cleanup

Use the applied move log as evidence. Preview first:

```powershell
python scripts/tidy.py sweep `
  --root "D:\work\project" `
  --move-log "MOVE_LOG_20260812_tidy.csv"
```

Execute eligible removals:

```powershell
python scripts/tidy.py sweep `
  --root "D:\work\project" `
  --move-log "MOVE_LOG_20260812_tidy.csv" `
  --execute
```

The unified launcher does not expose the whole-tree aggressive sweep option.

## Audit

```powershell
python scripts/tidy.py audit `
  --root "D:\work\project" `
  --before-count 1280 `
  --move-log "MOVE_LOG_20260812_tidy.csv" `
  --require-readme
```

Document-plan and profile checks can be added:

```powershell
python scripts/tidy.py audit `
  --root "D:\papers\incoming" `
  --doc-plan "docs\DOC_RENAME_PLAN.csv" `
  --move-log "MOVE_LOG_20260812_tidy.csv" `
  --profile literature-dump `
  --check-path "01_papers"
```

## Command summary

| Command | Purpose | Changes files by default? |
|---|---|---:|
| `doctor` | Check runtimes, scripts, optional extractors | No |
| `guide` | Print the safe workflow | No |
| `survey` | Inventory and profile hints | No |
| `init-unit-plan` | Write an unapproved CSV template | Writes one generated plan file |
| `plan-docs` | Write an unapproved document plan | Writes generated plan/optional metadata |
| `apply-moves` | Preflight unit moves | No; preview unless `--execute` |
| `apply-docs` | Preflight document actions | No; preview unless `--execute` |
| `sweep` | Find eligible empty parents | No; preview unless `--execute` |
| `audit` | Verify counts, plans, logs, placement, open-first maps | No |

## Exit codes

The launcher returns the underlying script code:

- `0`: success
- `1`: environment incomplete for `doctor`, or audit/check failure from a low-level script
- `2`: invalid arguments, missing control file, or missing runtime
- `3`: preflight failed; apply tools make zero moves
- `4`: runtime failure after preflight; the document tool attempts rollback
- `130`: interrupted from the keyboard

## Low-level scripts

Advanced parameters remain documented in [`SCRIPT_INDEX.md`](SCRIPT_INDEX.md). Use the low-level scripts for maintenance-only options, then preserve the same approval, path containment, preflight, logging, and audit rules.

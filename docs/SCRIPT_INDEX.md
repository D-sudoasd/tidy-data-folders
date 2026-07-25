# Script index

Paths are relative to `scripts/`. Run with **PowerShell 7** (`pwsh`) or **Python 3.10+**.

## inventory.ps1

| | |
|--|--|
| **Purpose** | Count files, list extensions, suggest profile |
| **Key params** | `-Root <path>` · `-Json` |
| **Exit** | 0 |

## apply_moves.ps1

| | |
|--|--|
| **Purpose** | Apply unit directory/file moves from plan CSV |
| **Key params** | `-Root` `-PlanCsv` `-MoveLog` `-WhatIf` `-UnsafeAllowUnapproved` (maintenance) |
| **Requires** | `approved` column; relative `src`/`dst` |
| **Kinds** | `move` · `rename_parent` · `archive` · … |
| **Exit** | 0 ok · 3 preflight · 4 runtime fail |

## apply_doc_renames.py

| | |
|--|--|
| **Purpose** | Apply document rename plan |
| **Key args** | `--root` `--plan` `--move-log` `--what-if` `--plan-id` `--unsafe-skip-hash` |
| **Exit** | 0 · 2 · 3 · 4 (rollback attempted on 4) |

## extract_doc_meta.py

| | |
|--|--|
| **Purpose** | Extract identity metadata → JSONL |
| **Key args** | `--root` `--out` (must be `.jsonl`) `--file` `--include-text-snip` `--include-class-snip` |
| **Default** | Temp JSONL; no body snips |

## propose_doc_renames.py

| | |
|--|--|
| **Purpose** | Build `DOC_RENAME_PLAN.csv` (`approved=false`) |
| **Key args** | `--root` `--meta` `--out` `--profile academic\|human\|normalize` `--slot-layout` |

## empty_shell_sweep.ps1

| | |
|--|--|
| **Purpose** | Remove empty dirs after moves |
| **Key params** | `-Root` `-AppliedLog` (preferred) or `-PlanCsv` · `-WhatIf` · `-Aggressive` + confirm string |
| **Exit** | 0 · 1 errors · 2 missing input |

## post_audit.ps1

| | |
|--|--|
| **Purpose** | Count summary, root purity, log/plan checks, open-first |
| **Key params** | `-Root` `-BeforeCount` `-AppliedLog` `-DocRenamePlan` `-RequireReadme` `-CheckPaths` `-Profile` |
| **Exit** | 0 PASS · 1 FAIL |

## scan_path_refs.ps1

| | |
|--|--|
| **Purpose** | Find config/map references to old roots |
| **Key params** | `-Root` `-OldRoots` list |

## path_safety.py

Library module (not a CLI). Used by Python apply/propose tools.

# Script index

The recommended public interface is `scripts/tidy.py`. Low-level scripts remain available for advanced parameters and define the execution behavior.

## tidy.py

| | |
|---|---|
| **Purpose** | Unified discovery, planning, preview, execution, cleanup, and audit entry point |
| **Runtime** | Python 3.10+; commands that call `.ps1` also require PowerShell 7 |
| **Safety default** | `apply-moves`, `apply-docs`, and `sweep` run in preview until `--execute` is supplied |
| **Machine output** | `doctor --json`, `survey --json` |
| **Exit** | Returns its own precondition code or the delegated script code |

### Public commands

| Command | Key arguments | Result |
|---|---|---|
| `doctor` | `--json` | Runtime, script-bundle, and optional extractor checks |
| `guide` | — | Safe workflow summary |
| `survey` | `--root` `--json` `--max-depth` | Calls `survey_signals.py` (no PowerShell required) |
| `init-unit-plan` | `--root` `--out` `--plan-id` `--empty` `--overwrite` | Atomic unapproved unit-plan template |
| `plan-docs` | `--root` `--out` `--meta-out` `--profile` `--slot-layout` | Extracts metadata and writes an unapproved document plan |
| `apply-moves` | `--root` `--plan` `--move-log` `--execute` | Delegates to `apply_moves.ps1`; preview by default |
| `apply-docs` | `--root` `--plan` `--move-log` `--plan-id` `--execute` | Delegates to `apply_doc_renames.py`; preview by default |
| `sweep` | `--root` `--move-log` `--execute` | Delegates to scoped `empty_shell_sweep.ps1`; preview by default |
| `audit` | `--root` `--before-count` `--move-log` `--doc-plan` `--profile` `--require-readme` `--check-path` | Delegates to `post_audit.ps1` |

Relative plan and log paths are resolved from `--root` and cannot escape it. Explicit absolute control-file paths remain supported. The unified interface does not expose maintenance-only unsafe options.

## survey_signals.py

| | |
|---|---|
| **Purpose** | Count files, list extensions, score competing backgrounds, suggest profile |
| **Key args** | `--root` · `--json` · `--max-depth` |
| **Public JSON** | Existing: `file_count`, `document_class_count`, `suggested_profile`, `phase_d_policy`, `extensions`, `existing_maps`, `listing`. Additive: `schema_version`, `profile_confidence`, `background_competition`, `layout_guidance`, `observed_clusters`, `competing_backgrounds`, `background_signals` |
| **Exit** | `0` · `2` missing root |

## inventory.ps1

| | |
|---|---|
| **Purpose** | Compatibility wrapper; forwards to `survey_signals.py` |
| **Key params** | `-Root <path>` · `-Json` · `-MaxDepthList` |
| **Exit** | Underlying Python exit code |

## apply_moves.ps1

| | |
|---|---|
| **Purpose** | Apply unit directory/file moves from plan CSV |
| **Key params** | `-Root` `-PlanCsv` `-MoveLog` `-WhatIf` `-UnsafeAllowUnapproved` (maintenance only) |
| **Requires** | `approved` column; root-relative `src`/`dst` |
| **Kinds** | `move` · `rename_parent` · `archive` · `shell_remove` · `path_rewrite` · `doc_rename` |
| **Exit** | `0` success · `3` preflight failure · `4` runtime failure |

## apply_doc_renames.py

| | |
|---|---|
| **Purpose** | Apply approved document rename/move plan |
| **Key args** | `--root` `--plan` `--move-log` `--what-if` `--plan-id` `--unsafe-skip-hash` (maintenance only) |
| **Exit** | `0` success · `2` arguments · `3` preflight · `4` runtime failure with rollback attempt |

## extract_doc_meta.py

| | |
|---|---|
| **Purpose** | Extract document identity metadata to JSON Lines |
| **Key args** | `--root` `--out` `--file` `--no-recursive` `--include-text-snip` `--include-class-snip` `--max-file-mb` |
| **Default** | Temporary JSONL when `--out` is omitted; no persisted body snippets |

## propose_doc_renames.py

| | |
|---|---|
| **Purpose** | Build plan version 2 `DOC_RENAME_PLAN.csv` with all approvals false |
| **Key args** | `--root` `--meta` `--out` `--profile academic|human|normalize` `--slot-layout literature-dump|none` `--plan-id` |
| **Exit** | `0` success · `2` arguments/output safety · `3` unresolved duplicate destinations |

## empty_shell_sweep.ps1

| | |
|---|---|
| **Purpose** | Remove empty directories after moves |
| **Key params** | `-Root` `-AppliedLog` (preferred) or `-PlanCsv` · `-WhatIf` · `-Aggressive` plus confirmation string |
| **Exit** | `0` success · `1` errors · `2` missing input |

## post_audit.ps1

| | |
|---|---|
| **Purpose** | Count summary, root purity, log/plan checks, approved destination hashes, open-first map checks |
| **Key params** | `-Root` `-BeforeCount` `-AppliedLog` `-DocRenamePlan` `-RequireReadme` `-CheckPaths` `-Profile` |
| **Exit** | `0` PASS · `1` FAIL |

## scan_path_refs.ps1

| | |
|---|---|
| **Purpose** | Find configuration/map references to old roots |
| **Key params** | `-Root` `-OldRoots` list |

## path_safety.py

Library module used by the Python document pipeline. It defines root containment helpers, action sets, approved parsing, SHA validation, and the exact move-log header.

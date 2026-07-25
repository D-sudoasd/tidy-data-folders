# Hardening pass 2026-07-25b

> **User-facing safety summary:** see [docs/SAFETY.md](docs/SAFETY.md).  
> This file is the **engineering** changelog for the hardening batch.

Implements review batch-1 (R-01…R-08) plus selected batch-2 UX fixes against
`tidy-data-folders_hardened_review_2026-07-25.md`.

## Done

| ID | Change |
|----|--------|
| R-01 | `apply_moves.ps1` requires `approved=true` by default; missing column fails; action whitelist; counts printed |
| R-02 | Component walk rejects reparse/symlink (Python `path_safety` + PS apply/sweep) |
| R-03 | Parent-is-file preflight; src overlap; dst-in-src; plan/log inside src; log writable; doc apply rollback on failure |
| R-04 | extract/propose refuse overwrite of existing/`--out` source docs; atomic write |
| R-05 | `post_audit.ps1` SHA checks for plan/log; failed log status → FAIL; missing required plan/log → FAIL |
| R-06 | Unified 12-col MOVE_LOG; header validate before append |
| R-07 | `allocate_unique_dsts` skips review/keep/protected; excludes own src; move_only basename guard |
| R-08 | Plan schema: plan_version=2, plan_id, row_id, approved true/false, action enum, hash for approved rows; strict `--plan-id` |
| R-10 partial | No default `class_snip` persistence; symlink skip in extract |
| R-11 partial | `human` template; notes/slides/report short templates; normalize = sanitize only |
| R-12 | Invoice number only from labeled 发票号码 / Invoice No |
| R-14 partial | Documented; remove `__pycache__` before ship |

## Tests

`python -m unittest discover -s tests -v` → 22 ok, 1 skipped (symlink create on Windows).

## Usage notes

- Unit plan CSV **must** include `approved` column.
- Doc apply no longer accepts silent `--no-require-approved`.
- Prefer empty sweep with `-AppliedLog` over bare plan.
- `AUDIT_RESULT: PASS` with `-DocRenamePlan` / `-AppliedLog` now implies SHA when hashes present.

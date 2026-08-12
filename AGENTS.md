# AGENTS.md

## Repository purpose

`tidy-data-folders` reorganizes scientific workspaces, document collections, and desktop dumps through an inspect → plan → approve → preview → execute → audit workflow. It supports human operators and AI agents while keeping file changes bounded, reviewable, and logged.

## Read order

1. [`SKILL.md`](SKILL.md) — behavioral contract for an agent performing folder work.
2. [`docs/SAFETY.md`](docs/SAFETY.md) — user-visible safety guarantees and limits.
3. [`scripts/tidy.py`](scripts/tidy.py) and [`docs/CLI.md`](docs/CLI.md) — stable user-facing command line.
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components and data flow.
5. [`scripts/path_safety.py`](scripts/path_safety.py) — shared Python constants and path/log validation.
6. [`docs/SCRIPT_INDEX.md`](docs/SCRIPT_INDEX.md) — low-level script parameters and exit codes.

Executable preflight checks define the accepted plan behavior. Documentation changes must remain consistent with those checks.

## Safety invariants

These requirements apply to every change that can move, rename, or remove an item:

1. Survey and plan before any mutation.
2. Execute only rows whose `approved` value parses as true.
3. Accept root-relative `src` and `dst` values only; reject absolute paths, UNC paths, `..`, and reparse/symlink traversal by default.
4. Complete preflight for all approved jobs before the first move.
5. Refuse an existing destination and refuse a changed source fingerprint when a fingerprint is required.
6. Never delete data files automatically. Empty-directory removal is limited to parents evidenced by an applied plan/log unless the user explicitly selects the guarded aggressive mode.
7. Preserve deep scientific leaf names unless the operation is an approved document-class rename.
8. Append operations to the unified 12-column `MOVE_LOG` after validating its header.
9. User-facing mutation commands must default to preview. `--execute` starts the existing apply script and does not bypass `approved=true`.
10. Do not expose maintenance-only unsafe flags through the unified CLI.

## Stable user-facing interface

Prefer the unified launcher in introductory user instructions. `SKILL.md` may call low-level scripts when an exact agent phase requires their advanced parameters:

```text
python scripts/tidy.py doctor
python scripts/tidy.py survey --root <folder>
python scripts/tidy.py init-unit-plan --root <folder>
python scripts/tidy.py plan-docs --root <folder>
python scripts/tidy.py apply-moves --root <folder> --plan <csv>
python scripts/tidy.py apply-docs --root <folder> --plan <csv>
python scripts/tidy.py sweep --root <folder> --move-log <csv>
python scripts/tidy.py audit --root <folder>
```

`apply-moves`, `apply-docs`, and `sweep` are previews until `--execute` is supplied. Direct PowerShell/Python scripts remain available for advanced parameters and are the execution source of truth.

Machine-readable discovery is available through:

```text
python scripts/tidy.py doctor --json
python scripts/tidy.py survey --root <folder> --json
```

`doctor --json` includes `schema_version: 1`; additive fields may be introduced without changing the meaning of existing fields.

## Data contracts

### Unit-move plan

Minimum columns:

```text
approved,src,dst
```

Recommended columns:

```text
plan_version,plan_id,row_id,approved,src,dst,kind,reason
```

Accepted `kind` values are defined by `ALLOWED_UNIT_KINDS` in `scripts/path_safety.py` and mirrored by `scripts/apply_moves.ps1`.

### Document-rename plan

`propose_doc_renames.py` writes plan version `2`. Preserve its header and use these actions:

```text
rename,normalize,move_only,keep,review,protected
```

Approved executable rows require `src_size` and a full `src_sha256` unless a maintainer deliberately invokes the low-level unsafe maintenance option.

### MOVE_LOG

The exact header is:

```text
run_id,plan_id,row_id,timestamp_utc,src,dst,kind,status,reason,error,sha256_before,sha256_after
```

Do not add, reorder, or remove fields without updating every producer, consumer, test, and document in the same change.

## Repository map

```text
SKILL.md                  Agent workflow and hard rules
AGENTS.md                 Contributor/agent orientation
scripts/tidy.py           Unified safe launcher
scripts/*.ps1             Windows inventory, moves, sweep, audit, path scan
scripts/*.py              Document pipeline and shared safety helpers
docs/CLI.md               Human command-line guide
docs/ARCHITECTURE.md      Data flow and component boundaries
docs/SAFETY.md            User-facing safety contract
references/               Profiles, naming rules, templates, lessons
examples/                 Synthetic workspace and sample plans
tests/                    Safety and launcher tests
```

## Change discipline

- Keep the unified launcher thin; delegate move/rename logic to the hardened scripts.
- Add a preview-default test for every new mutating command.
- Add machine-readable output only when its schema can remain stable and documented.
- Keep English and Chinese README entry commands synchronized.
- Update `docs/CLI.md`, `docs/SCRIPT_INDEX.md`, `docs/ARCHITECTURE.md`, and `CHANGELOG.md` when the public interface changes.
- Avoid committing personal paths, real research data, document text extracts, or generated move logs.

## Validation

Run before publishing:

```text
python -m unittest discover -s tests -v
python -m py_compile scripts/tidy.py
python scripts/tidy.py --help
```

When PowerShell 7 is available, also run a synthetic preview against `examples/desktop-messy` and confirm that no file changes occur without `--execute` and `approved=true`.

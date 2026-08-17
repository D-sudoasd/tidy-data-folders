# Changelog

All notable changes to this project are documented here.

## [0.3.1] — 2026-08-17

### Added

- `scripts/survey_signals.py`: shipped survey / background-signal path used by `python scripts/tidy.py survey`
- Additive survey JSON fields (existing keys unchanged): `schema_version`, `profile_confidence`, `background_competition`, `layout_guidance`, `observed_clusters`, `competing_backgrounds`, `background_signals`
- Unit tests that call the shipped survey function on literature, desktop, scientific/data-heavy, generic, and mixed trees

### Changed

- Mixed or unmatched folders no longer lock to the first SXRD / literature regex; competing backgrounds are reported and `suggested_profile` stays `generic` unless one family dominates
- Desktop-dump detection uses mixed dump composition, not a substring match on `Desktop` in the path
- `SKILL.md` routes agents through `python scripts/tidy.py`, intent → mode, JSON survey, and mixed-folder adaptation
- `survey` no longer requires PowerShell 7; `inventory.ps1` forwards to the same Python signal module
- Profile reference explains independent background scoring and how to adapt unknown trees

### Security

- Mutation safety is unchanged: preview remains the default, only `approved=true` rows execute, `src`/`dst` stay root-relative, data files are never auto-deleted, and the 12-column `MOVE_LOG` header is unchanged

## [0.3.0] — 2026-08-12

### Added

- `scripts/tidy.py`: one public command line for environment checks, survey, unit-plan templates, document planning, preview, execution, scoped cleanup, and audit
- Preview-default gate for unit moves, document actions, and empty-directory cleanup; actual changes require `--execute` while preserving `approved=true`
- Machine-readable `doctor --json` with schema version `1`, plus routed `survey --json`
- Atomic `init-unit-plan` template with an unapproved placeholder row
- `AGENTS.md` with repository reading order, safety invariants, stable interfaces, data contracts, and validation rules
- `docs/CLI.md` with end-to-end human command-line workflows
- Launcher unit tests covering preview defaults, explicit execution, plan-template approval state, path behavior, audit routing, and machine-readable environment checks

### Changed

- Reworked English and Chinese READMEs around role-based entry points and the unified launcher
- Expanded architecture and script-index documentation to distinguish the public interface from hardened execution scripts

### Security

- Unified launcher omits maintenance-only unsafe flags
- Relative plan/log/output paths are resolved under the selected root and relative escapes are rejected; explicit absolute control-file paths remain supported
- Mutating launcher commands cannot execute unless the user supplies `--execute`; low-level apply scripts continue to require approved rows and complete preflight
- Default document metadata remains temporary and text snippets remain disabled

## [0.2.1] — 2026-07-25

### Added

- Public homepage polish: hero / workflow / before-after SVGs
- Bilingual README (`README.md`, `README.zh-CN.md`)
- `docs/SAFETY.md`, `docs/ARCHITECTURE.md`, `docs/SCRIPT_INDEX.md`
- `examples/desktop-messy` synthetic demo + sample unit plan
- `CONTRIBUTING.md`, `SECURITY.md`, issue/PR templates
- GitHub Actions CI (Python 3.10–3.12)

## [0.2.0] — 2026-07-25

### Added

- Hardened path safety (root-relative, reparse refusal)
- Unit moves require `approved=true` by default
- Unified 12-column MOVE_LOG
- Document rename pipeline with full SHA-256 and plan schema
- Empty-shell sweep scoped to applied moves
- `post_audit.ps1` integrity checks
- Python unit tests for safety gates

### Security

- Refuse extract/propose `--out` overwriting source documents
- Preflight parent-is-file / overlap / log header validation

## [0.1.0] — 2026-07

### Added

- Initial map-first workflow, inventory, profiles, references

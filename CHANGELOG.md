# Changelog

All notable changes to this project are documented here.

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

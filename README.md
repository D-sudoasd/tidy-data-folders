# tidy-data-folders

[![CI](https://github.com/D-sudoasd/tidy-data-folders/actions/workflows/ci.yml/badge.svg)](https://github.com/D-sudoasd/tidy-data-folders/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PowerShell 7+](https://img.shields.io/badge/pwsh-7%2B-5391FE.svg)](https://github.com/PowerShell/PowerShell)
[![Release](https://img.shields.io/github/v/release/D-sudoasd/tidy-data-folders)](https://github.com/D-sudoasd/tidy-data-folders/releases)

**Map-first folder reorg for AI agents** — plan first, **approved-only** execute, full audit trail.

[中文说明](README.zh-CN.md) · [Safety](docs/SAFETY.md) · [Architecture](docs/ARCHITECTURE.md) · [Script index](docs/SCRIPT_INDEX.md) · [Changelog](CHANGELOG.md)

<p align="center">
  <img src="assets/readme/hero.svg" alt="tidy-data-folders hero: map-first reorg with approved-only execute" width="100%" />
</p>

Messy scientific workspaces and desktop dumps share a problem: **everything lands at the root**, same projects split across folders, and agents love to rename/move things without a paper trail.

This skill makes the root answer *“where do I go?”* in under a minute — **without deleting data** and **without renaming deep scientific leaves** (`Az_*.txt`, `.cbf`, run IDs) unless you explicitly approve document renames.

---

## Why not “just let the agent Move-Item”?

| Risk with unguarded agents | What this skill does |
|----------------------------|----------------------|
| Moves before you understand the tree | **Survey → plan → wait** |
| Applies every row in a CSV | Only **`approved=true`** |
| Absolute paths / `..` escapes | **Root-relative only** |
| Partial apply on preflight miss | **All-or-nothing preflight** (exit 3) |
| Silent overwrite of sources | **Refuse dest-exists & `--out` onto docs** |
| “PASS” without integrity | **MOVE_LOG + optional SHA audit** |
| Deletes “duplicates” | **Never auto-delete files** |

<p align="center">
  <img src="assets/readme/workflow.svg" alt="Workflow: Survey Plan Approve Execute Audit" width="100%" />
</p>

---

## Before / after

<p align="center">
  <img src="assets/readme/before-after.svg" alt="Before messy root vs after map-first layout" width="100%" />
</p>

---

## Install

### Grok / local agent skills

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git "$env:USERPROFILE\.grok\skills\tidy-data-folders"
```

Already installed as a git clone? `git pull` inside that folder.

### Codex

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git "$env:USERPROFILE\.codex\skills\tidy-data-folders"
```

### Optional: better document renames

```powershell
pip install -r requirements.txt
```

| Package | Role |
|---------|------|
| `pypdf` | PDF signals |
| `python-docx` | DOCX |
| `python-pptx` | PPTX (optional) |

Inventory + unit moves work **without** these packages.

---

## 5-minute quick start

```powershell
$Skill = "$env:USERPROFILE\.grok\skills\tidy-data-folders\scripts"
$Root  = "D:\path\to\messy\folder"   # change me

# 1) See what you have
pwsh -File "$Skill\inventory.ps1" -Root $Root

# 2) Write docs\unit_plan.csv with columns:
#    plan_version,plan_id,row_id,approved,src,dst,kind,reason
#    set approved=true only on rows you accept

# 3) Apply unit moves (refuses unapproved / bad paths)
pwsh -File "$Skill\apply_moves.ps1" -Root $Root `
  -PlanCsv "$Root\docs\unit_plan.csv" -MoveLog "$Root\MOVE_LOG.csv"

# 4) Remove empty parents left by moves
pwsh -File "$Skill\empty_shell_sweep.ps1" -Root $Root `
  -AppliedLog "$Root\MOVE_LOG.csv" -MoveLog "$Root\MOVE_LOG.csv"

# 5) Audit
pwsh -File "$Skill\post_audit.ps1" -Root $Root -RequireReadme `
  -AppliedLog "$Root\MOVE_LOG.csv"
```

**With an agent:** open this repo’s [`SKILL.md`](SKILL.md) as a skill, say “整理这个文件夹” / “tidy this folder”. The agent should **plan first** and wait for **「按方案执行」**.

### Document rename (Phase D)

```powershell
$py = (Get-Command py, python | Select-Object -First 1).Source
& $py "$Skill\extract_doc_meta.py" --root $Root
# use the printed temp .jsonl as --meta
& $py "$Skill\propose_doc_renames.py" --root $Root --meta <meta.jsonl> `
  --out "$Root\docs\DOC_RENAME_PLAN.csv"
# set approved=true on chosen rows, then:
& $py "$Skill\apply_doc_renames.py" --root $Root `
  --plan "$Root\docs\DOC_RENAME_PLAN.csv" --move-log "$Root\MOVE_LOG.csv" --what-if
```

See [examples/](examples/) for a synthetic desktop dump and sample plan (`approved=false`).

---

## Modes

| Mode | Does |
|------|------|
| **survey** | Inventory only |
| **plan** | Taxonomy + unit table + path risks (+ doc rename table) |
| **execute** | Approved moves/renames + seal + maps |
| **audit** | `post_audit.ps1` |
| **docs-identify / rename-docs** | Document identity only |
| **desktop** | Scoop Desktop/Downloads into dated inbox buckets |

**Profiles:** `sxrd-texture` · `sxrd-tensile` · `manuscript-heavy` · `desktop-dump` · `literature-dump` · `generic` — details in [`references/profiles.md`](references/profiles.md).

---

## Scripts at a glance

| Script | Role |
|--------|------|
| `inventory.ps1` | File counts, extensions, profile hints |
| `apply_moves.ps1` | Unit moves (approved-only, preflight) |
| `apply_doc_renames.py` | Document renames (SHA + schema) |
| `extract_doc_meta.py` | PDF/DOCX/PPTX metadata JSONL |
| `propose_doc_renames.py` | Rename plan CSV (`approved=false`) |
| `empty_shell_sweep.ps1` | Empty dirs from applied moves only |
| `post_audit.ps1` | Root purity, log/plan checks, open-first |
| `scan_path_refs.ps1` | Find absolute path references after moves |
| `path_safety.py` | Shared root / reparse / log helpers |

Full parameters and exit codes: [docs/SCRIPT_INDEX.md](docs/SCRIPT_INDEX.md).

**Exit codes (apply tools):** `0` ok · `2` bad args · `3` preflight fail (zero moves) · `4` runtime fail after preflight.

---

## Layout vocabulary

| Term | Meaning |
|------|---------|
| **map-first** | Root answers “where do I go?” in &lt;60s |
| **unit move** | Move whole homogeneous trees; one log row each |
| **open-first** | README row-1 = best CURRENT artifact on disk |
| **path seal** | Counts + shell sweep + config path notes |
| **promote** | Formal results under `production` / `best` / CURRENT |

---

## Safety & limits

Read **[docs/SAFETY.md](docs/SAFETY.md)** (user-facing) and **[HARDENING_20260725b.md](HARDENING_20260725b.md)** (engineering).

**Does:** move/rename under a chosen root with gates and logs.  
**Does not:** cloud sync recovery, binary rewrite of Origin `.opju`, invent DOIs/years, auto-delete duplicates, or claim path-rewrite PASS without a rewrite run.

This skill **moves files**. Keep backups. Start with unapproved plans and `--what-if`.

---

## Tests

```powershell
cd path\to\tidy-data-folders
python -m unittest discover -s tests -v
```

CI runs on Python 3.10–3.12 ([workflow](.github/workflows/ci.yml)).

---

## Repository map

```text
SKILL.md              Agent entry (triggers + hard rules)
README.md · README.zh-CN.md
LICENSE · CHANGELOG.md · CONTRIBUTING.md · SECURITY.md
assets/readme/        Hero & diagrams (SVG)
docs/                 Architecture, safety, script index
examples/             Synthetic demo tree + sample plan
scripts/              pwsh + Python tools
references/           Profiles, naming, templates, lessons
tests/                Safety unit tests
```

---

## FAQ

**Q: Will it delete my data?**  
A: No automatic file deletes. Empty directories may be removed only via plan-scoped shell sweep.

**Q: Can I run without an AI agent?**  
A: Yes — all core steps are CLI scripts.

**Q: Windows only?**  
A: PowerShell scripts target Windows/`pwsh`. Python helpers are portable; junction checks are Windows-aware.

**Q: Where do personal defaults go?**  
A: Copy `USER.example.md` → local `USER.md` (gitignored). Do not commit personal paths.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

---

## License

[MIT](LICENSE) © 2026 Delun Gong

# tidy-data-folders

**Map-first folder reorg skill for AI agents** — unit moves, document-identity renames (PDF/Word/PPTX), path seal, and **approved-only** execute.

Designed for messy scientific workspaces and desktop dumps: make the root answer “where do I go?” in under a minute, without deleting data or renaming deep scientific leaf files (`Az_*.txt`, `.cbf`, run IDs).

| | |
|--|--|
| **Skill entry** | [`SKILL.md`](SKILL.md) |
| **License** | [MIT](LICENSE) |
| **Python** | ≥ 3.10 |
| **Shell scripts** | PowerShell 7+ (`pwsh`) |
| **Safety notes** | [`HARDENING_20260725b.md`](HARDENING_20260725b.md) |

---

## What it does

1. **Survey** — inventory counts, extensions, suggested layout profile  
2. **Plan** — project homes / unit-move table / path risks / optional doc rename plan  
3. **Execute (only after approval)** — move whole units; optional content-based document renames  
4. **Seal** — empty-shell sweep (plan-scoped), config path notes, audit  

**Profiles** (see `references/profiles.md`): `sxrd-texture`, `sxrd-tensile`, `manuscript-heavy`, `desktop-dump`, `literature-dump`, `generic`.

### Safety (non-negotiable)

- All plan paths are **root-relative** (no `..`, no absolute escapes)  
- **Only `approved=true` rows** are applied (unit moves and doc renames)  
- Full **preflight** before any move; refuse overwrite of existing destinations  
- **Never auto-delete** data files; empty directories only via scoped shell sweep  
- Document renames: refuse `--out` over source files; full SHA-256 for identity  
- Symlinks / junctions rejected by default  

---

## Install

### Grok skills (this machine style)

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git "$env:USERPROFILE\.grok\skills\tidy-data-folders"
```

If the folder already exists (local copy), either replace it or:

```powershell
cd $env:USERPROFILE\.grok\skills\tidy-data-folders
git pull
```

### Codex skills

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git "$env:USERPROFILE\.codex\skills\tidy-data-folders"
```

### From another agent skill-installer

```text
install from GitHub: D-sudoasd/tidy-data-folders  (path: repository root)
```

### Optional Python extractors (document rename)

```powershell
pip install -r requirements.txt
```

| Package | Use |
|---------|-----|
| `pypdf` | PDF title / text signals |
| `python-docx` | DOCX |
| `python-pptx` | PPTX (optional) |

Unit moves and inventory work without these; Phase D document rename quality improves with them.

---

## Quick start (agent or human)

Set `$SkillScripts` to this repo’s `scripts` folder.

```powershell
$SkillScripts = "$env:USERPROFILE\.grok\skills\tidy-data-folders\scripts"
$Root = "D:\path\to\messy\folder"

# 1) Inventory
pwsh -File "$SkillScripts\inventory.ps1" -Root $Root

# 2) Agent writes a unit plan CSV (must include approved column), then:
#    set approved=true only on rows you accept

# 3) Dry-run / apply unit moves
pwsh -File "$SkillScripts\apply_moves.ps1" -Root $Root -PlanCsv "$Root\docs\unit_plan.csv" -MoveLog "$Root\MOVE_LOG.csv"

# 4) Empty shells from applied log only
pwsh -File "$SkillScripts\empty_shell_sweep.ps1" -Root $Root -AppliedLog "$Root\MOVE_LOG.csv" -MoveLog "$Root\MOVE_LOG.csv"

# 5) Audit
pwsh -File "$SkillScripts\post_audit.ps1" -Root $Root -BeforeCount <N> -RequireReadme -AppliedLog "$Root\MOVE_LOG.csv"
```

### Document rename (Phase D)

```powershell
$py = (Get-Command py, python | Select-Object -First 1).Source
& $py "$SkillScripts\extract_doc_meta.py" --root $Root
# use printed temp JSONL path as --meta
& $py "$SkillScripts\propose_doc_renames.py" --root $Root --meta <meta.jsonl> --out "$Root\docs\DOC_RENAME_PLAN.csv"
# edit approved=true on chosen rows, then:
& $py "$SkillScripts\apply_doc_renames.py" --root $Root --plan "$Root\docs\DOC_RENAME_PLAN.csv" --move-log "$Root\MOVE_LOG.csv" --what-if
& $py "$SkillScripts\apply_doc_renames.py" --root $Root --plan "$Root\docs\DOC_RENAME_PLAN.csv" --move-log "$Root\MOVE_LOG.csv"
```

Default: **plan → wait for user approval**. Do not apply unapproved rows.

---

## Layout language (short)

| Word | Meaning |
|------|---------|
| **map-first** | Root answers “where do I go?” in &lt;60s |
| **unit move** | Move whole homogeneous trees; one log row each |
| **open-first** | README row-1 = single best CURRENT artifact on disk |
| **path seal** | Count check + shell sweep + config path notes |
| **promote** | Formal results under `production` / `best` / CURRENT |

---

## Repository layout

```text
SKILL.md                 # Agent instructions (trigger + workflow)
README.md                # This file
LICENSE
requirements.txt
USER.example.md          # Copy locally to USER.md if needed (gitignored)
scripts/                 # pwsh + Python tools
references/              # profiles, naming, templates, lessons
tests/                   # Python safety tests
HARDENING_20260725b.md   # Hardening changelog
```

---

## Tests

```powershell
cd path\to\tidy-data-folders
python -m unittest discover -s tests -v
```

---

## Local preferences

Ship **`USER.example.md` only**. On your machine you may create `USER.md` (gitignored) for personal defaults. Agents should not commit it back to a shared clone.

---

## Disclaimer

This skill **moves files**. Always review the plan, keep backups of important trees, and start with `--what-if` / unapproved plans. Authors are not responsible for data loss from unreviewed execute runs.

---

## License

MIT © 2026 Delun Gong

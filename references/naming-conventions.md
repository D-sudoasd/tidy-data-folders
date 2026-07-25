# Naming conventions

## Folder names (new parents)

| Rule | Good | Avoid |
|------|------|--------|
| Numbered workflow prefix | `01_raw_spectra/`, `03_sweep_analysis/` | `data1/`, `新建文件夹` |
| `snake_case` English slots | `macro_mechanical`, `peak_fitting` | spaces, mixed `峰拟合 final` |
| Role words | `raw`, `processed`, `analysis`, `production`, `archive`, `reference` | `misc`, `stuff`, `other` |
| Sample / condition tokens keep IDs | `PA_A_Full_343frames`, `4K_RD` | inventing new sample codes |
| Archive stamp | `99_archive/2026-07-14_reorg/` | undated archive dumps |
| Trial vs formal | `01_trial_…`, `production/` | unlabeled twin MAUD trees |

## Number prefixes

- `00`–`09`: living work in **pipeline order** (docs → raw → process → product).
- `99`: archive / superseded only.
- Skip numbers freely; do not renumber existing stable projects just for aesthetics.
- Nested numbers only when a sub-pipeline has clear stages (e.g. trial → tracklocked → constrained).

## Files

| Kind | Policy |
|------|--------|
| Spectra frames `Az_*.txt`, `.cbf`, frame indices | **Never rename** |
| Sample run folders used by scripts | **Never rename** without crosswalk |
| **Document-class** `.pdf` `.docx` `.pptx` (etc.) | **May rename** via Phase D when profile enables — see [doc-identity.md](doc-identity.md), [doc-naming-profiles.md](doc-naming-profiles.md) |
| Publisher junk names (`1-s2.0-…`, `main.pdf`) | Prefer content-based academic stem |
| Root dumps `新建文件夹`, `0`, `NEW` | Rename parents to descriptive English |
| Maps / logs | `README.md`, `README_PROJECT_MAP.md`, `AGENTS.md`, `FILE_MAP.md`, `MOVE_LOG_YYYYMMDD_slug.csv`, `docs/DOC_RENAME_PLAN.csv`, `PLACEMENT_AUDIT_YYYYMMDD.md` |
| Origin | Keep `.opju` basename if possible; document path breaks |

## Language

- **Paths / IDs:** English + established codes (`LD`, `TD`, `Full`, `45`, `RD`, sample IDs).
- **Human prose in MD:** Chinese OK and preferred for this user.
- **Hybrid historical names** (`TUIHUO`, `试样掉落`): keep; explain in README table.

## Semantic tags (domain)

| Tag | Meaning |
|-----|---------|
| `LD` / `TD` / `45` / `Full` | Azimuthal sector / detector integration |
| `RD` / `TD` / `TH` (sample) | Specimen orientation (project-specific) |
| `production` | Promoted / complete series — default for citation |
| `archive_tuning` / `trial` / `work` | Non-CURRENT; do not treat as final |
| `best` | Promoted refinement outputs |
| `noinst` | Instrument broadening not corrected (keep in path if already used) |
| `CURRENT` | Active manuscript/data line vs archive |
| `omega###` / `full_37x72` | Texture rotation angle / full pose grid |
| `exports_full` | Promoted pole-figure quick view |
| `raw_cbf` / `esg_products` | Texture profile slots |

## MOVE_LOG (unit-level)

- **One row per unit** (directory or single loose root file), not per child frame/ESG.
- Preferred header: `timestamp_utc,src,dst,kind,reason`
- `kind`: `move` | `shell_remove` | `path_rewrite` | `doc_rename`
- Document renames: each PDF/DOCX is a unit in literature dumps; use `kind=doc_rename` (dst = final path including slot).
- If the log would exceed ~30 **data-tree** move rows, you leaf-walked — regroup. Doc rename rows may be many; summarize in chat, keep full CSV.

Examples: `wrap raw CBF sample`, `promote full texture job`, `archive seed intermediate`, `empty shell after promote`, `paper identity rename+slot`.

# Domain slots — in-situ SXRD / tensile / Rietveld

Use when the tree smells like synchrotron 1D spectra, peak fitting, MAUD, Origin, CIF, manuscripts.

## Canonical slot palette

Pick a subset; rename slots to project language but keep the **roles**.

| Typical name | Put here | Do not put here |
|--------------|----------|-----------------|
| `00_docs_notes/` or `09_docs/` / `docs/` | README, catalogs, condition index, notes | bulk frames |
| `01_calibration/` | `Calibration_CeO2.yaml`, geometry | analysis products |
| `01_raw_spectra/` / `04_spectra/` / `05_in_situ_series_raw/` | Azimuthally integrated series, manifests | peakfit exports |
| `02_structures/` / `01_structures_cif/` | CIF, theoretical peak tables | refined `.par` series |
| `02_macro_mechanical/` / `03_mechanical/` | stress–strain, timestamp-aligned force–frame CSV | spectra |
| `03_peak_fitting/` / `05_peak_fitting/` / `02_analysis_peakfit_*` | `.fit`, `.peaks`, PeakFitter CSV trees | raw Az txt |
| `03_analysis_maud/` / `10_maud_full/` / `maud_full_frame0/` | `.par` series, exports, leaderboards | desktop zips of unrelated data |
| `01_figures_and_origin_projects/` / `04_origin_projects/` / `06_figures/` | `.opju`, figure exports, PPT | raw series |
| `05_references/` / `07_references/` | PDF, paper-pack, PRM | active manuscript CURRENT |
| `00_current_manuscript/` / `08_manuscript/` | CURRENT drafts only | superseded Word |
| `03_sweep_analysis/` | sweep/ML/batch analysis products | single exploratory png on desktop |
| `99_archive/` / `99_archive_superseded_outputs/` | old tracks, empty shells, MOVE_LOGs history | anything still CURRENT |
| `tmp/` | agent/runtime junk | anything user should open first |

### MAUD internal roles (inside a maud root)

| Subfolder | Meaning |
|-----------|---------|
| `production/` or `best/` | Promoted — cite these |
| `work/` | Active polish, not frozen |
| `archive/` / `archive_tuning/` | Historical / 2–3 frame smoke tests |
| `exports/` + `00_README.md` | Human-facing derived packs |

### Peakfit internal roles

Number trial → locked track → constrained/recommended:

- `01_trial_…`
- `02_tracklocked_…`
- `03_constrained_…` (or project-specific recommended path)

## Layout patterns already proven on disk

### Pattern A — numbered multi-role project (`4_ZrNb`, `5_CSU_WeiZhang`)

```text
Project/
  README.md
  AGENTS.md                 # optional
  01_… 02_… 03_…
  docs/ or 09_docs/
  99_archive/               # optional
```

### Pattern B — manuscript-heavy (`1_Nb_HEA`)

```text
00_current_manuscript/      # CURRENT only
01_figures_and_origin_projects/
02_processed_data/
03_sweep_analysis/
04_fitting_and_structures/
05_references/
06_codex_writing_plans/     # process, not final text
99_archive_superseded_outputs/
tmp/
PROJECT_GOLD_LINES.md       # scientific contracts
README_PROJECT_MAP.md
AGENTS.md
```

### Pattern C — series-first tensile SXRD (`2_Ti65`, `1_HKsteel`)

Keep **run folder names** for beamline compatibility; wrap with role parents:

```text
05_in_situ_series_raw/<RunFamily>/...
02_macro_mechanical/tensile_timestamp_aligned/
06_gxx_processed/ or maud_full_frame0/best/
```

## Texture rotation spine (sxrd-texture)

Proven on `Texture_analysis` (NOHR):

```text
01_calibration/                 Calibration_CeO2.yaml
02_structures/                  source CIF (canonical)
03_raw_cbf/<SAMPLE>/            .meta + overexposure_corrected/*.cbf
04_esg_products/                auto_mask, batch config, ESG, seeds
04_esg_products/<SAMPLE>/       NOHR_all_omegas.esg, NOHR_omega*.esg, seed.par
05_texture_results/<SAMPLE>/
  production/                   full job + exports_full + final.par  ★ CURRENT
  pilot_*/                      non-CURRENT smoke
99_archive/…/_seed_work_*/      seed intermediates
```

- Working CIF/YAML copies may stay beside ESG; **canonical** in `01`/`02`.
- After promoting children out of a results folder, **empty-shell sweep** the husk.
- Prefer unit move of entire `full_37x72/` not leaf `.par` files.

See also [profiles.md](profiles.md).

## Detection heuristics

| Signal | Likely slot |
|--------|-------------|
| Many `Az_LD_*.txt` / `Az_Full_*.txt` | raw spectra |
| `.cbf` + `deg_*` + omega series | `03_raw_cbf` (texture) |
| Many `*.esg` + `*_all_omegas.esg` | `04_esg_products` |
| `texture_results` / pole figure / E-WIMV | `05_texture_results/…/production` |
| `processing_manifest.json` next to LD/TD/45/Full | keep with raw sample tree |
| `*.fit` / `*.peaks` at root | peak_fitting |
| Hundreds of `*.par` + `*.ins` + `*.lst` | maud tree |
| `*timestamp_aligned.csv` | mechanical / force–frame |
| `.opju` | origin_projects |
| CIF + peak xlsx | structures |
| Duplicate manuscript tracks | archive non-CURRENT; lock CURRENT in map |

## Promotion language (must appear in README)

Always tell the reader which path is **formal**:

- “`03_analysis_maud/production/` 才是正式结果”
- “`maud_full_frame0/best/` 推荐使用”
- “旧 sequence **仅** `99_archive_…`”

## What never to “clean”

- Frame numbering inside sample folders
- `LD` / `TD` / `45` / `Full` sector folder names if pipelines assume them
- Sample short IDs (`ZS_1`, `PA_A`, `H0`/`H+`) once established in maps
- Gold-line / contract files (`PROJECT_GOLD_LINES.md`, `*_CONTRACT.json`)

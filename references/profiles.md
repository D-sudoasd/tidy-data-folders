# Layout profiles

Do **not** pick the first regex hit. Survey scores literature, desktop, scientific, and manuscript backgrounds independently (`python scripts/tidy.py survey --root <folder> --json`). Use a named spine only when one background wins clearly. When `background_competition` is true or the folder is unmatched, adapt slots from `observed_clusters` — do not force `sxrd-texture` or `literature-dump`.

## Signal → profile

| Background family | When it fires | Named profile if it is the sole / dominant winner |
|-------------------|---------------|---------------------------------------------------|
| literature | Mostly PDF/DOCX; publisher ids (`1-s2.0-`, `s41598-`, `metals-##-`), `main.pdf`, short junk names | **literature-dump** |
| desktop | Mixed images + docs + archives/installers, screenshot-like names, `loose/`/`inbox/` dumps; or a true `Desktop` / `Downloads` / `桌面` path **component** | **desktop-dump** |
| scientific (SXRD texture) | `.cbf` + `.esg` / `texture_*` / `omega` / pole figure, and no close competing family | **sxrd-texture** |
| scientific (SXRD tensile) | `Az_*.txt` + tensile / MAUD / peakfit / `.fit`, and no close competing family | **sxrd-tensile** |
| scientific (unnamed) | Data-heavy `.dat` / `.xy` / `.chi` / `.cbf` clusters without a named SXRD pattern | **generic** — keep scientific leaves; adapt slots |
| manuscript | `Article_*` / `Letter_*` / `CURRENT` + manuscript smell | **manuscript-heavy** |
| several families, close scores | Mixed tree | **generic** + report `competing_backgrounds` |
| else | Unmatched | **generic** |

Desktop is a **content** mix, not a path that merely contains the letters `Desktop` (so `desktop-messy` is not a user Desktop by name alone).

Also read [domain-slots-sxrd.md](domain-slots-sxrd.md) for tensile/MAUD detail.  
Document rename policy: [doc-identity.md](doc-identity.md).

## Mixed / unknown

When survey says `layout_guidance: adapt_from_observed`:

1. Group what is already there (`observed_clusters` + listing).
2. Propose only slots that have evidence (documents, images, scientific data, archives).
3. Keep existing folder names when they already work.
4. Leave scientific leaves untouched.
5. Ask before applying a named domain spine.

Do not invent SAXS / chemistry / generic-XRD first-class profiles.

---

## sxrd-texture

```text
01_calibration/
02_structures/
03_raw_cbf/<SAMPLE>/
04_esg_products/          # mask, batch config, ESG, seeds
05_texture_results/<SAMPLE>/
  production/             # full job + exports + final.par
  pilot_*/                # non-CURRENT
99_archive/
docs/
```

Open-first: `05_…/production/exports_full/` or montage PNG · GUI `*.par`.

---

## sxrd-tensile

```text
00_docs_notes/ or docs/
01_calibration/ or structures first per project
01_raw or 05_in_situ_series_raw/
02_macro_mechanical/
03_peak_fitting/ or analysis_peakfit_*
0N_maud…/ with production|best vs archive_tuning|work
0N_origin / figures
99_archive/
```

Open-first: promoted MAUD `best/`/`production/` or condition index.

---

## manuscript-heavy

```text
00_current_manuscript/    # CURRENT only
01_figures_and_origin_projects/
02_processed_data/
03_… analysis
05_references/
06_… writing process (non-final)
99_archive_superseded_outputs/
PROJECT_GOLD_LINES.md / AGENTS.md / README_PROJECT_MAP.md
tmp/
```

Open-first: CURRENT Word/docx or `CURRENT.md` · gold lines.

---

## desktop-dump

```text
_inbox/YYYYMMDD_desktop/   # or user library
  images/
  docs/
  data/
  archives_zip/
  installers/
  to_sort/                 # ambiguous — ask before promote
```

Do not invent project homes. Offer promote into real trees only after user names target.  
**Phase D:** on for files under `docs/` (and root loose PDFs if user asks); not for `images/`. Detect this profile from mixed dump composition, not only from a Desktop-shaped path name.

---

## literature-dump

Paper/report dumps (ScienceDirect `1-s2.0-…-main`, MDPI codes, `main.pdf`, mixed Chinese short names).

```text
00_docs/                  # README, maps, DOC_RENAME_PLAN
01_papers/                # identified papers (+ optional review/)
02_other_docs/            # reports, notes, slides, thesis
03_figures_exports/       # figure-only / image-pack PDFs
99_archive/               # duplicate copies (_dup)
to_sort/                  # low-confidence / unknown
```

**Phase D:** **on by default** — plan block 7 required; prefer final path = slot + semantic name.  
Open-first: topic paper if user named one; else `01_papers/` + STATUS「文献已命名」.  
Do not run SXRD leaf rules here.

---

## generic

```text
00_docs/ or docs/
01_raw/ or 01_source/
02_working/
03_outputs/
99_archive/
```

Number by **workflow order**; skip unused slots.  
**Phase D:** optional when inventory shows a document-class cluster; ask or mark block 7 optional.

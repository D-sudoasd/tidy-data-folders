# Lessons (read before execute, or after any surprise)

## Texture_analysis (2026-07-14)

**What went well:** Numbered spine; production vs pilot; maps; config path updates.

**Failures / near-misses:**

1. **Empty parent promotion** — After moving children out of `texture_results/`, the empty folder was still listed by `Get-ChildItem` and moved into `04_esg_products/NOHR/texture_results`. Fix: **empty-shell sweep** after every promote/unit-move batch; never log empty dirs as data moves.
2. **Leaf MOVE_LOG spam** — Moving remaining ESG files one-by-one produced ~100 CSV rows. Fix: **unit moves** — move whole sample trees when homogeneous; one log row per unit.
3. **Path rewrite was ad-hoc** — `maud_esg_batch_config.json` / processing manifest needed absolute path updates. Fix: **scan_path_refs** in plan; rewrite only config-class files on execute; leave historical `AGENT_RESULT.json` workdirs alone.
4. **Satisfaction ≠ “docs exist”** — User happiness is root purity + **open-first** CURRENT row in README.

**Rule of thumb:** Promote results **up** to a clear `production/`; do not leave empty husks behind; seal with file counts.

## literature-dump / Phase D (2026-07-25)

**Pilot folder:** `papers_pdf` inbox (publisher ids + `main.pdf` + mixed Chinese).

**What works:** inventory → `literature-dump`; extract/propose scripts; academic stems for MDPI/SciRep; invoice → `report`/`Invoice_*`; content-hash `_dup` → `99_archive`.

**Watch:** PDF first-page chrome (“Journal Pre-proof”, CC license, affiliations) can steal titles — agent must refine short_title from text_snip before apply when reason smells wrong. Year from body can be wrong (`main.pdf`); prefer filename year / DOI lookup (v0.2 Crossref). Encoding of accented author names may garble under some consoles; files on disk are UTF-8.

**Rule:** Plan CSV is machine draft with `approved=false`; only execute approved rows after preflight. Scan `review` / `UnknownVenue` / `Undated` / `Anon` before approval.

## Security hardening (2026-07-25 review)

Implemented: root containment, full preflight, `approved`+fingerprints, full SHA-256 dups, unique dst allocation, good-name `move_only`, plan-scoped empty sweep, plan-item audit, no personal USER pack defaults, temp meta / no default text_snip.  
Still later: automated path-rewrite tool, full cross-platform inventory rewrite, OCR.

## General

- If plan table has more than ~30 move rows, you are leaf-walking — regroup into units.
- If root still has bulk data after execute, satisfaction contract failed.
- If re-run pipelines break next day, path seal / rewrite was incomplete.
- Document renames may be many rows; summarize in chat, keep full `DOC_RENAME_PLAN.csv`.

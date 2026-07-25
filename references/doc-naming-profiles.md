# Document naming profiles

Used by `propose_doc_renames.py` and agent refinement. Defaults in [USER.md](../USER.md).

## Profile A — academic (default)

```text
{Year}_{VenueSlug}_{FirstAuthor}_{ShortTitle}[_{Tag}].{ext}
```

Examples:

- `2018_SciRep_Smith_FlexibleCompositeMagnets.pdf`
- `2026_AdvMater_Zhang_EntropyHierarchicalDefectTE.pdf`
- Review tag: `…_Review.pdf` when `doc_type=review`

### Field rules

| Field | Rule |
|-------|------|
| Year | Prefer **filename** year, then trusted metadata; body year is low confidence (`Undated` if unknown). Sources: `year_source` |
| VenueSlug | Map journal name → short ASCII (table below); else compress words |
| FirstAuthor | Surname / 拼音; single token preferred |
| ShortTitle | 4–8 English tokens or ≤40 Chinese chars; drop “A study of / Towards / 基于…” |
| Tag | optional: `Review`, `dup`, `notes` |
| Max stem length | 120 chars (Windows-safe; prefer ≤100) |

## Profile B — human scan (中文友好)

```text
{Year}_{主题短名}_{第一作者}.{ext}
```

Use when USER.md sets `doc_naming_profile=human` or user asks 中文文件名.

## Profile C — normalize only

- Strip illegal Windows chars: `\ / : * ? " < > |` and control chars  
- Collapse whitespace; replace spaces with `_`  
- Remove trailing ` (1)` only when content-hash proves duplicate of base  
- Truncate stem to max length  
- Do **not** invent academic structure  

Use when file already has a readable semantic name.

## Slot layout (`literature-dump`)

| doc_type | Default slot |
|----------|----------------|
| `paper`, `review` | `01_papers/` |
| `figure_export` | `03_figures_exports/` |
| `notes`, `report`, `slides`, `datasheet`, `thesis`, `patent` | `02_other_docs/` |
| `unknown` / skip_review | `to_sort/` (or leave in place if rename-docs mode without slots) |
| content-hash dup of a kept file | `99_archive/` with `_dup` stem suffix |

Final path = `{slot}{stem}{ext}` when slot layout on; else same directory.

## Venue slug examples

| Venue / pattern | VenueSlug |
|-----------------|-----------|
| Advanced Materials | AdvMater |
| Acta Materialia | ActaMater |
| Scripta Materialia | ScriptaMater |
| Materials Science and Engineering A | MSEA |
| Journal of Alloys and Compounds | JALCOM |
| Nature Communications | NatCommun |
| Scientific Reports | SciRep |
| Metals (MDPI) | Metals |
| Advanced Engineering Materials | AdvEngMater |
| Progress in Materials Science | ProgMaterSci |

Unknown venue: take first 1–3 capitalized tokens, strip “The/Journal of”, cap length 16.

## Windows safety

1. Replace illegal chars with `_`  
2. No trailing dots/spaces  
3. Avoid reserved device names (`CON`, `PRN`, …)  
4. On collision: append `_{hash4}` before extension; never overwrite  

## Action selection

| Situation | action |
|-----------|--------|
| Strong identity, name differs | `rename` |
| Long publisher-style name → academic stem | `normalize` |
| Already academic basename; only change folder | `move_only` (keep basename) |
| Weak identity + literature slots | `move_only` into `to_sort/` keep basename |
| Weak identity without slots | `review` (dst=src) |
| Scientific leaf / policy off | `protected` |
| Already perfect path | `keep` |

All plan rows ship with **`approved=false`**. Apply only after user sets `approved=true` on chosen rows.

## Destination uniqueness

After generating stems, allocate unique `dst` (case-insensitive) against plan + disk; on clash append `_{hash4}` or `_dup_{hash4}`.

# Document identity (Phase D)

Content-based identification for **document-class** files only. Not for spectra frames, CBF, or instrument raw.

## Document-class extensions

Primary: `.pdf` `.docx` `.doc` `.pptx` `.ppt`  
Optional: `.xlsx` `.xlsm` (rename only when clearly a report/workbook with title, not raw data dumps)

## Never rename (skip_protected)

- `Az_*.txt`, `*.cbf`, frame indices, sample run folders  
- Paths under active pipeline configs unless user forces  
- CURRENT manuscript drafts in `manuscript-heavy` unless user asks  
- Anything profile policy sets Phase D **off**

## doc_type

| Type | Signals |
|------|---------|
| `paper` | Title/authors/abstract/DOI; journal header; IMRaD smell |
| `review` | “Review”, 综述, long ref list, survey structure |
| `thesis` | 学位论文, advisor, degree, university front matter |
| `report` | Tech report, project ID, org letterhead |
| `slides` | PPTX or PDF with slide-like short pages |
| `notes` | Informal, no formal title block |
| `datasheet` | Spec tables, part numbers |
| `patent` | Patent number, claims |
| `figure_export` | Few pages, little text, mostly figures |
| `unknown` | Cannot stabilize identity |

## Extraction layers

### A — Filename heuristics (fast)

| Pattern | Signal |
|---------|--------|
| `1-s2.0-S…-main`, `S#######` | Publisher id — force content extract |
| `metals-13-00504`, `s41598-…`, `s41467-…` | Journal article code |
| `main.pdf`, `main (1).pdf`, `Review_1.pdf` | Garbage name |
| `YYYY_Journal_Author_Title` | Possibly already good → `normalize` or `keep` |
| Pure digits / short hash / 2–4 char stem | Weak |

### B — Local extract (`extract_doc_meta.py`)

| Format | Support |
|--------|---------|
| PDF | pypdf first 1–2 pages + metadata |
| DOCX | python-docx core props + paragraphs |
| PPTX | python-pptx props + slide 1 (optional dep) |
| DOC/PPT | **legacy** — no auto-rename (`review` / protected) |
| XLSX | **review only** — no auto semantic rename by default |

Fields: `title`, `authors[]`, `year`, `venue`, `doi`, `page_count`, `class_snip` (ephemeral), `is_likely_scanned`.  
`text_snip` **off by default** (privacy); enable with `--include-text-snip`.  
Default `--out` may be OS temp; do not leave body text in project `docs/` unless user asks.

### C — Scholarly lookup (optional)

**Default off.** Only when user explicitly allows for the task.  
When enabled: Crossref/OpenAlex on DOI / high-quality title; high similarity required.

### D — LLM assist (agent)

Input: filename + extract JSON + short class_snip.  
Output fixed fields only. **Forbidden:** inventing DOI, year, or authors.

## Confidence gates & actions

| confidence | action bias |
|------------|-------------|
| ≥ 0.85 | `rename` / `normalize` / `move_only` (still need `approved=true`) |
| 0.55–0.85 | same with ⚠ |
| &lt; 0.55 | `review` or `move_only` → `to_sort/` **keeping basename** |
| scanned, no text | `review` / needs_ocr |

Unified actions: `rename | normalize | move_only | keep | review | protected`

## Content hash

- `quick_fingerprint` = first 2 MiB + size — **candidate screening only**  
- `sha256_full` = entire file — **only full match is a duplicate**  
Never archive on quick fingerprint alone.

## Agent display

- Summarize high-confidence renames in a table.  
- If &gt;30 rename rows, group by proposed slot for chat; keep full CSV on disk for apply/undo.

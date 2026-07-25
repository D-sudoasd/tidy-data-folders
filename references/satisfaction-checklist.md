# Satisfaction contract

User opens the folder in Explorer → should feel **finished**, not “still messy but documented.”

## Root appearance (required after execute)

```text
ProjectRoot/
  README.md                 ← human open-first
  AGENTS.md                 ← scientific projects
  MOVE_LOG_YYYYMMDD_*.csv   ← if any moves
  00_… / 01_… / 0N_…        ← numbered workflow only
  99_archive/               ← optional
  docs/                     ← ARCHIVE_MAP, audit
  (no loose bulk data files at root)
```

Allowed at root: maps, logs, `AGENTS.md`, numbered dirs, `docs/`, `tmp/` (if already convention).  
Not allowed at root: spectra dumps, CBF/ESG trees, random CIF/YAML (put in slots), `新建文件夹`.

## README open-first (required)

1. Title + one-line **STATUS** (e.g. `质构完成 · production scientific_ok` / `整理完成 · 待分析`).
2. **「先看哪里」** table — **row 1 = single best CURRENT artifact** (montage, CURRENT manuscript, primary raw).
3. One-minute tree.
4. CURRENT vs non-CURRENT explicitly labeled.

## Promote

- Formal results live under `production/`, `best/`, or `00_current_manuscript/` — never only buried as “also in some job folder.”
- Pilot/trial/archive must be named so a tired user does not open them first.

## Path seal

- Record **file count before** moves (exclude only if you create new maps — after counts may be before + new docs).
- After moves: count seal in audit (`post_audit.ps1`).
- Empty-shell sweep: zero leftover empty parents under project root.
- Config-class absolute paths rewritten; historical agent job paths noted as non-authoritative.

## literature-dump extras (when Phase D ran)

- Root has no loose publisher-id PDFs (`1-s2.0-…`, bare `main.pdf`) — low-confidence files should be under `to_sort/` via **`move_only`** (basename kept).  
- `docs/DOC_RENAME_PLAN.csv` exists; rows used for apply had `approved=true`.  
- MOVE_LOG / apply log contains applied `doc_rename` or `move` rows with status.  
- Duplicates not deleted; `_dup_{hash4}` / `99_archive` only on **full** SHA-256 match.  
- Integrity: approved plan destinations exist (not merely “file count didn’t drop”).

## Pass/fail (agent)

| Gate | Pass |
|------|------|
| Root purity | No bulk data files at root |
| Open-first | README row-1 path exists on disk |
| Promote | CURRENT path documented and real |
| Count seal | After files ≥ before (only +docs/logs); no unexplained drop |
| Empty shells | Sweep done; no empty husks from this reorg |
| Unit log | MOVE_LOG is unit-level, not leaf spam (doc_rename units OK) |
| Doc names (literature-dump) | Publisher junk cleared from root; plan on disk |

# Path risks — scan and rewrite

Absolute paths break after reorg. Handle in **plan** (report) and **execute** (selective rewrite).

## Scan (always in survey/plan)

Run `scripts/scan_path_refs.ps1 -Root <project> -OldRoots <root>,<known_old>`.

Search text files under root for:

- Current project root string (both `\` and `\\` / `/` variants)
- Known prior roots if mentioned in README_NEXT or manifests

**High-signal files:**

| Class | Examples | Rewrite on execute? |
|-------|----------|---------------------|
| **Config** | `*batch*config*.json`, `*processing_manifest*.json`, `maud_esg_batch_config.json`, pipeline `*.yaml` used as input paths | **Yes** |
| **Skill-owned maps** | README / AGENTS / ARCHIVE_MAP you write this run | Write correct paths from the start |
| **Historical agent** | `AGENT_RESULT.json`, `texture_status.json`, `AGENT_SUMMARY.md`, job `*.log` with old work_dir | **No** — note non-authoritative in README |
| **Origin** | `.opju` (binary) | Do not rewrite; write `PATH_NOTES.md` |
| **Code outside root** | PyMAUD docs, other repos | Out of scope; mention in plan risks only |

## Rewrite rules

1. Only config-class + manifests you own for re-runs.  
2. Prefer string replace of **old absolute root prefixes** → new prefixes (preserve suffix path structure when only parent slots changed).  
3. Log each rewritten file: MOVE_LOG `kind=path_rewrite` or `docs/PATH_REWRITE_YYYYMMDD.md`.  
4. Re-read JSON after rewrite (`ConvertFrom-Json`) — fail if broken.  
5. Never rewrite binary files.

## Plan table column

Include **path-risk list**:

| File | Old path snippet | Action |
|------|------------------|--------|
| `…/maud_esg_batch_config.json` | `F:\…\MAUD_ESG` | rewrite |
| `…/AGENT_RESULT.json` | `D:\Backup\…` | leave + README note |

# Safety contract (user-facing)

This skill **moves and optionally renames files**. Treat every execute as a data operation.

## Hard guarantees (design intent)

| Rule | Behavior |
|------|----------|
| Approval gate | Only rows with `approved=true` are applied |
| Root boundary | Plan paths are root-relative; `..` and absolute paths rejected |
| Reparse points | Symlinks / junctions refused by default |
| Preflight | Deterministic errors fail **before** any move (exit code **3**) |
| No file delete | Data files are never auto-deleted; empty dirs only via scoped sweep |
| Scientific leaves | Deep IDs (`Az_*.txt`, `.cbf`, run folders) preserved unless you approve doc renames |
| Logging | Unified MOVE_LOG columns for moves / renames / shell removes |
| Overwrite | Destination must not already exist; extract/propose refuse writing onto source docs |

## What you must still do

1. **Read the plan** before saying 按方案执行 / setting `approved=true`.  
2. **Backup** critical trees (or work on a copy) the first times you use it.  
3. Prefer **`--what-if`** / dry inventory on unfamiliar roots.  
4. After moves, open **open-first** paths and spot-check one sample tree.  
5. Config JSON with absolute paths may need manual rewrite (see path-risks).  

## Exit codes (apply tools)

| Code | Meaning |
|------|---------|
| 0 | Success or nothing to do |
| 2 | Bad arguments / missing paths |
| 3 | Preflight failed — **zero moves** |
| 4 | Runtime failure after preflight (doc renames attempt rollback) |

## Reporting issues

If a move escaped the root or deleted data unexpectedly, open a security-oriented issue via [SECURITY.md](../SECURITY.md) with: OS, skill version/tag, plan CSV (redacted), MOVE_LOG excerpt, and exact command line.

## Engineering depth

Implementation hardening notes: [HARDENING_20260725b.md](../HARDENING_20260725b.md).

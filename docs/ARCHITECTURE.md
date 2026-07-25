# Architecture

## Data flow

```text
                    ┌─────────────┐
                    │  inventory  │  counts, profile hints
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
          human /   │   PLAN CSV  │  approved=false by default
          agent     │ unit / docs │
                    └──────┬──────┘
                           │ set approved=true
           ┌───────────────┼───────────────┐
           │               │               │
   ┌───────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
   │ apply_moves  │ │apply_doc_   │ │ (optional)  │
   │   .ps1       │ │ renames.py  │ │ path notes  │
   └───────┬──────┘ └──────┬──────┘ └─────────────┘
           │               │
           └───────┬───────┘
                   │
           ┌───────▼──────┐
           │  MOVE_LOG    │  12 columns, status trail
           └───────┬──────┘
                   │
     ┌─────────────┼─────────────┐
     │             │             │
┌────▼────┐ ┌──────▼──────┐ ┌────▼─────┐
│ empty   │ │ post_audit  │ │ README / │
│ shell   │ │   .ps1      │ │ maps     │
│ sweep   │ └─────────────┘ └──────────┘
└─────────┘
```

## Language split

| Layer | Tech | Why |
|-------|------|-----|
| Inventory, unit move, sweep, audit, path scan | **PowerShell 7** | Native Windows paths, ACL, reparse attributes |
| Doc extract / propose / apply rename, path helpers | **Python 3.10+** | PDF/DOCX libs, hashing, CSV schema |
| Shared safety constants | `path_safety.py` | LOG fields, resolve_under_root, SHA |

## Plan schemas

**Unit move** (minimum): `approved,src,dst` plus recommended `plan_id,row_id,kind,reason`.  
**Doc rename**: full schema in `propose_doc_renames.py` (`plan_version=2`, `src_sha256`, …).

## Profiles

Layout slots differ by domain (`references/profiles.md`). The engine stays the same; only recommended folder spines and Phase D defaults change.

## Non-goals (current)

- Automated rewrite of every absolute path in the tree  
- Binary edit of Origin `.opju`  
- Cross-volume transactional multi-root moves  
- GUI

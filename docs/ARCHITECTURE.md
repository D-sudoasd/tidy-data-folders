# Architecture

## Interface layers

The repository has two documented entry paths that share the same execution scripts:

```text
AI agent                               Human / automation
   │                                          │
SKILL.md                                  scripts/tidy.py
   │                                          │
   └───────────── plan and command intent ───┘
                              │
                    hardened low-level scripts
```

- `SKILL.md` defines the agent workflow: survey first, map intent to a mode, use `scripts/tidy.py`, wait for approval, and adapt mixed/unknown folders from observed files.
- `AGENTS.md` gives contributors and coding agents a compact repository contract.
- `scripts/tidy.py` provides one preview-default command line for people and automation.
- PowerShell and Python apply scripts remain the execution source of truth.

## Data flow

```text
              human / agent / automation
                         │
             ┌───────────▼───────────┐
             │ doctor / survey       │  runtime checks, counts, profile hints
             └───────────┬───────────┘
                         │
             ┌───────────▼───────────┐
             │ PLAN CSV              │  approved=false during review
             │ unit moves / documents│
             └───────────┬───────────┘
                         │ selected rows approved=true
                 ┌───────▼────────┐
                 │ preview        │  full preflight, zero moves
                 └───────┬────────┘
                         │ explicit --execute
          ┌──────────────┴──────────────┐
          │                             │
  ┌───────▼────────┐            ┌───────▼────────────┐
  │ apply_moves.ps1│            │apply_doc_renames.py│
  │ unit trees/files│           │document-class files│
  └───────┬────────┘            └───────┬────────────┘
          │                             │
          └──────────────┬──────────────┘
                         │
                 ┌───────▼────────┐
                 │ MOVE_LOG       │  fixed 12-column operation trail
                 └───────┬────────┘
                         │
             ┌───────────┴───────────┐
             │                       │
     ┌──────▼────────┐      ┌───────▼────────┐
     │ scoped sweep   │      │ post_audit.ps1 │
     │ empty parents  │      │ counts/maps/log│
     └────────────────┘      └────────────────┘
```

The unified launcher does not implement move or rename algorithms. It resolves sibling scripts, normalizes control-file paths, creates safe plan templates, defaults mutating commands to preview, and forwards the low-level exit code. Survey scoring lives in `scripts/survey_signals.py` so agents and tests can consume a stable JSON payload without PowerShell.

## Language split

| Layer | Technology | Responsibility |
|---|---|---|
| Unified public command line | Python 3.10+ | Discovery, command routing, generated templates, preview-default gate |
| Survey / background signals | Python 3.10+ (`survey_signals.py`; `inventory.ps1` forwards) | Counts, listing, competing-background scores, profile hint |
| Unit moves, empty-parent sweep, audit, path scan | PowerShell 7 | Windows paths, ACL behavior, reparse attributes, directory operations |
| Document extraction, proposal, apply, shared path helpers | Python 3.10+ | PDF/DOCX/PPTX libraries, hashing, CSV validation, document actions |
| Agent behavior | Markdown | Triggers, profiles, planning blocks, user approval, completion criteria |

## Safety boundaries

### Unified launcher

- Exposes no maintenance-only unsafe flags.
- Adds `-WhatIf` or `--what-if` unless the user supplies `--execute`.
- Leaves `approved=true` enforcement to the apply scripts and does not synthesize approval.
- Interprets relative plan and log paths from the selected root and rejects relative escapes.
- Uses atomic replacement for the generated unit-plan template.

### Apply scripts

- Validate plan schema and approved values.
- Reject unsafe paths, reparse/symlink traversal by default, duplicate sources/destinations, and existing destinations.
- Complete preflight for all approved jobs before the first mutation.
- Verify source size/hash where required.
- Validate the `MOVE_LOG` header before appending.

### Sweep and audit

- Normal empty-directory cleanup is derived from applied plan/log evidence.
- Audit checks counts, approved document destinations and hashes, log status, required paths, root purity, and open-first maps according to selected options/profile.

## Data contracts

### Unit-move plan

Minimum columns:

```text
approved,src,dst
```

Recommended public template:

```text
plan_version,plan_id,row_id,approved,src,dst,kind,reason
```

### Document plan

`propose_doc_renames.py` writes plan version `2` with source identity fields, classification, confidence, reason codes, destination, and approval state. All generated approvals are `false`.

### MOVE_LOG

Every producer and consumer uses this exact header:

```text
run_id,plan_id,row_id,timestamp_utc,src,dst,kind,status,reason,error,sha256_before,sha256_after
```

## Machine-readable interfaces

- `python scripts/tidy.py doctor --json` reports runtime and extractor readiness with `schema_version: 1`.
- `python scripts/tidy.py survey --root <folder> --json` reports counts, extensions, profile hints, maps, a bounded listing, and additive competing-background fields (`background_competition`, `competing_backgrounds`, `background_signals`, `observed_clusters`, `layout_guidance`, `profile_confidence`). Existing keys keep their meaning. `schema_version` is `1`.
- Unit and document plans are CSV.
- Document metadata is JSON Lines and remains temporary by default.
- Applied operations are CSV in the unified move-log schema.

## Profiles

Profiles in `references/profiles.md` change recommended folder slots and document-planning defaults. They do not change path containment, approval, preview, preflight, destination, logging, or audit requirements. Mixed or unmatched trees keep `suggested_profile: generic` and `layout_guidance: adapt_from_observed` instead of inheriting the first SXRD or literature regex hit.

## Current limits

- Automated rewrite of every absolute path in a tree
- Binary editing of Origin `.opju`
- Cross-volume transactional multi-root moves
- Cloud-sync recovery and external-link repair
- Graphical user interface

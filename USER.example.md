# User defaults (example — copy to local USER.md outside the package if needed)

Do **not** commit personal project paths into a shared skill package.

Agent: read a local `USER.md` only if the user has created one beside this skill
or pointed to it. Prefer neutral defaults below when missing.

## Neutral defaults

| Key | Value |
|-----|--------|
| Map language | Match existing project language; English paths/IDs preferred for new folders |
| Numbering | `01_` workflow spine; `99_archive` when creating new structure |
| Scientific AGENTS.md | Only when user asks or profile is clearly scientific |
| Delete data | Never without explicit OK; empty shells only via plan-scoped sweep |
| Plan gate | Always plan before execute unless user says 按方案执行 / 自主执行 |
| Open-first | README / TIDY_FOLDER_MAP row-1 = CURRENT product |
| MOVE_LOG | Unit-level; kinds include `doc_rename` |
| doc_naming_profile | `academic` |
| doc_rename_crossref | **off** unless user enables for this task |
| doc_rename_duplicates | never delete; `_dup_{hash4}` / `99_archive` |
| doc_rename_max_stem | 120 |
| Phase D on sxrd profiles | off unless user asks |
| Existing README/AGENTS | **Do not overwrite** — write `TIDY_FOLDER_MAP.md` or dated file unless user approves merge |
| Meta persistence | Prefer OS temp for `_doc_meta.jsonl`; no `text_snip` unless user asks |

## Optional local overrides

Copy this file to `USER.md` in the skill directory **only on your machine**,
or keep preferences in the project README. Never auto-append without the user asking.

# Examples

Synthetic demos only — **no real scientific data**.

## `desktop-messy/`

Tiny fake desktop scoop:

| Path | Role |
|------|------|
| `loose/*` | Files dumped at “root” of the example |
| `inbox/*` | Ambiguous leftovers |
| `docs/unit_plan.sample.csv` | Unit plan with **`approved=false`** |

### Try inventory (read-only)

```powershell
$Skill = "...\tidy-data-folders\scripts"
$Root  = "...\tidy-data-folders\examples\desktop-messy"
pwsh -File "$Skill\inventory.ps1" -Root $Root
```

### Apply for real (optional)

1. Copy `docs/unit_plan.sample.csv` → `docs/unit_plan.csv`  
2. Set chosen rows to `approved=true`  
3. Run `apply_moves.ps1` with `-Root` pointing at `desktop-messy`  
4. Expect `ProjectDemo/` and `_inbox/` layout as described in `EXPECTED.md`

**Tip:** work on a **copy** of `desktop-messy` if you want to re-run demos.

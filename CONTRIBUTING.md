# Contributing

Thanks for improving **tidy-data-folders**. Safety-critical path code is held to a high bar.

## Development setup

```powershell
git clone https://github.com/D-sudoasd/tidy-data-folders.git
cd tidy-data-folders
python -m unittest discover -s tests -v
```

Optional: `pip install -r requirements.txt` for extractors used in manual doc tests.

## Before you open a PR

1. Run unit tests (must stay green).  
2. For changes to `apply_moves.ps1`, `apply_doc_renames.py`, `path_safety.py`, `empty_shell_sweep.ps1`, or `post_audit.ps1`:  
   - Add or extend tests when possible  
   - Describe preflight / approval / root-boundary impact in the PR  
3. Do **not** commit `USER.md`, secrets, or personal absolute paths.  
4. Keep scientific leaf-name guarantees unless the PR is explicitly about doc-rename policy.

## Preferred contribution types

- New layout **profiles** (with a short note in `references/profiles.md`)  
- Safer preflight checks and regression tests  
- Docs / examples / translations  
- PowerShell/Python portability notes  

## Code style

- Python: 3.10+ type hints where practical; no network in default paths  
- PowerShell: `-LiteralPath`, fail closed on boundary errors  
- Unified MOVE_LOG header must stay in sync across writers  

## License

By contributing, you agree your contributions are licensed under the MIT License.

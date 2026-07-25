# Security policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes |
| &lt; 0.2 | Best-effort |

## Expected risk class

This software **relocates user files** on disk. Misuse (approving a bad plan) can make files hard to find; design bugs could theoretically move data outside the intended root.

If you discover a **path escape**, **unauthorized delete**, **overwrite of unselected sources**, or **approval bypass**, please report it privately when possible.

## How to report

1. Open a GitHub issue with title prefix `[security]` **without** attaching private data, **or**  
2. Contact the maintainer via GitHub (@D-sudoasd) for coordinated disclosure.

Include:

- Skill version / git tag  
- OS and `pwsh` / Python versions  
- Minimal repro (synthetic tree preferred)  
- Plan CSV redacted  
- MOVE_LOG excerpt  

Please allow reasonable time before public disclosure of zero-days.

## Non-vulnerabilities

- User sets `approved=true` on a destructive plan  
- Running under Administrator and pointing `-Root` at a system path  
- Missing optional extractors causing low-quality **rename proposals** (not applied without approval)  

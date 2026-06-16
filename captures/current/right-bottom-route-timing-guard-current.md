# Right-Bottom Route Timing Guard

- Overall: PASS
- Generated: `2026-06-16T18:04:45+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: right-bottom validation evidence must keep hidden route/copyback/grid marker ordering, candidate SHA agreement, 800x600 surfaces, and no AV/failure-exit rows
- Expected stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- Candidate SHA-256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`

## Checks

### Patch Route

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260513-120712`
- Hidden desktop: `True`
- Surface: `[800, 600]`
- Fast-forward startup: `True`
- Full startup path: `False`
- Ordered markers: `29`

### Fullstart Route

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260513-122928`
- Hidden desktop: `True`
- Surface: `[800, 600]`
- Fast-forward startup: `False`
- Full startup path: `True`
- Ordered markers: `29`

### Grid Route

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260514-140601`
- Hidden desktop: `True`
- Surface: `[800, 600]`
- Fast-forward startup: `True`
- Full startup path: `False`
- Grid hit ok: `True`
- Grid entry/result: `[450, 73]` / `0`
- Failure exits / AV rows: `0` / `0`
- Ordered markers: `25`

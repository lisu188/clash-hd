# HD Soak Short Artifact Manifest

- Overall: PASS
- Generated: `2026-06-15T20:36:18.839899+00:00`
- Runtime policy: repo-only short-soak artifact manifest; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Protected stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Step reports present: `0/5`
- Legacy default report: `captures\current\hd-soak-short-current.json` exists=`True`
- Stable stage should change: `False`
- Right-bottom promotion blocked: `True`

## Step Reports

- `short2_menu_idle`: report=`captures\current\hd-soak-short2-menu-idle-current.json` exists=`False`
- `short2_map_idle`: report=`captures\current\hd-soak-short2-map-idle-current.json` exists=`False`
- `short10_map_idle`: report=`captures\current\hd-soak-short10-map-idle-current.json` exists=`False`
- `short10_map_pan`: report=`captures\current\hd-soak-short10-map-pan-current.json` exists=`False`
- `short30_map_pan`: report=`captures\current\hd-soak-short30-map-pan-current.json` exists=`False`

## Current First-Step Command

Safe dry-run command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -Json
```

Approval-gated runtime command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -Execute -AllowVisibleRuntime -RequirePass -Json
```

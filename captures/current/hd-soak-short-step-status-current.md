# HD Soak Short-Step Status

- Overall: PASS
- Generated: `2026-06-15T20:14:56.163067+00:00`
- Runtime policy: repo-only short-soak step status; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Manifest: `captures\current\hd-soak-short-artifact-manifest-current.json`
- Ladder complete: `False`
- Current step: `short2_menu_idle` status=`pending_approval_legacy_compat`
- Passed steps: `0/5`
- Long tiers locked: `True`
- Future lanes locked: `True`

## Steps

- `short2_menu_idle`: tier=`short2` route=`menu-idle` status=`pending_approval_legacy_compat` passed=`False`
- `short2_map_idle`: tier=`short2` route=`map-idle` status=`locked_by_prerequisite` passed=`False`
- `short10_map_idle`: tier=`short10` route=`map-idle` status=`locked_by_prerequisite` passed=`False`
- `short10_map_pan`: tier=`short10` route=`map-pan` status=`locked_by_prerequisite` passed=`False`
- `short30_map_pan`: tier=`short30` route=`map-pan` status=`locked_by_prerequisite` passed=`False`

## Current Next Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -Execute -AllowVisibleRuntime -RequirePass -Json
```

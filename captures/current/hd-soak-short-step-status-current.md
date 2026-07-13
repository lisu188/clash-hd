# HD Soak Short-Step Status

- Overall: PASS
- Generated: `2026-07-12T19:36:11.501517+00:00`
- Runtime policy: repo-only short-soak step status; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Manifest: `captures\current\hd-soak-short-artifact-manifest-current.json`
- Ladder complete: `False`
- Current step: `short2_map_idle` status=`missing_pending_approval`
- Passed steps: `1/5`
- Long tiers locked: `True`
- Future lanes locked: `True`

## Steps

- `short2_menu_idle`: tier=`short2` route=`menu-idle` status=`pass` passed=`True`
- `short2_map_idle`: tier=`short2` route=`map-idle` status=`missing_pending_approval` passed=`False`
- `short10_map_idle`: tier=`short10` route=`map-idle` status=`locked_by_prerequisite` passed=`False`
- `short10_map_pan`: tier=`short10` route=`map-pan` status=`locked_by_prerequisite` passed=`False`
- `short30_map_pan`: tier=`short30` route=`map-pan` status=`locked_by_prerequisite` passed=`False`

## Current Next Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route map-idle -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Execute -AllowVisibleRuntime -RequirePass -Json
```

# HD Soak Short Artifact Manifest

- Overall: PASS
- Generated: `2026-09-06T03:57:57.589871+00:00`
- Runtime policy: repo-only short-soak artifact manifest; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Protected stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Step reports present: `5/5`
- Legacy default report: `captures\current\hd-soak-short-current.json` exists=`True`
- Stable stage should change: `False`
- Right-bottom promotion blocked: `True`

## Step Reports

- `short2_menu_idle`: report=`captures\current\hd-soak-short2-menu-idle-current.json` exists=`True` preferred_environment=`host_visible`
- `short2_map_idle`: report=`captures\current\hd-soak-short2-map-idle-current.json` exists=`True` preferred_environment=`hidden_cdb_host`
  - Hidden dry-run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_hidden_soak.ps1 -Route map-idle -DurationSec 120 -FrameIntervalSec 15 -PanIntervalSec 10 -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -GuardJson captures\current\hd-soak-short2-map-idle-guard-current.json -GuardMarkdown captures\current\hd-soak-short2-map-idle-guard-current.md -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128`
  - Hidden runtime: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_hidden_soak.ps1 -Route map-idle -DurationSec 120 -FrameIntervalSec 15 -PanIntervalSec 10 -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -GuardJson captures\current\hd-soak-short2-map-idle-guard-current.json -GuardMarkdown captures\current\hd-soak-short2-map-idle-guard-current.md -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Execute`
- `short10_map_idle`: report=`captures\current\hd-soak-short10-map-idle-current.json` exists=`True` preferred_environment=`hidden_cdb_host`
  - Hidden dry-run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_hidden_soak.ps1 -Route map-idle -DurationSec 600 -FrameIntervalSec 15 -PanIntervalSec 10 -ReportJson captures\current\hd-soak-short10-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short10-map-idle-current.md -GuardJson captures\current\hd-soak-short10-map-idle-guard-current.json -GuardMarkdown captures\current\hd-soak-short10-map-idle-guard-current.md -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128`
  - Hidden runtime: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_hidden_soak.ps1 -Route map-idle -DurationSec 600 -FrameIntervalSec 15 -PanIntervalSec 10 -ReportJson captures\current\hd-soak-short10-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short10-map-idle-current.md -GuardJson captures\current\hd-soak-short10-map-idle-guard-current.json -GuardMarkdown captures\current\hd-soak-short10-map-idle-guard-current.md -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Execute`
- `short10_map_pan`: report=`captures\current\hd-soak-short10-map-pan-current.json` exists=`True` preferred_environment=`hidden_cdb_host`
  - Hidden dry-run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_hidden_soak.ps1 -Route map-pan -DurationSec 600 -FrameIntervalSec 15 -PanIntervalSec 10 -ReportJson captures\current\hd-soak-short10-map-pan-current.json -ReportMarkdown captures\current\hd-soak-short10-map-pan-current.md -GuardJson captures\current\hd-soak-short10-map-pan-guard-current.json -GuardMarkdown captures\current\hd-soak-short10-map-pan-guard-current.md -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128`
  - Hidden runtime: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_hidden_soak.ps1 -Route map-pan -DurationSec 600 -FrameIntervalSec 15 -PanIntervalSec 10 -ReportJson captures\current\hd-soak-short10-map-pan-current.json -ReportMarkdown captures\current\hd-soak-short10-map-pan-current.md -GuardJson captures\current\hd-soak-short10-map-pan-guard-current.json -GuardMarkdown captures\current\hd-soak-short10-map-pan-guard-current.md -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Execute`
- `short30_map_pan`: report=`captures\current\hd-soak-short30-map-pan-current.json` exists=`True` preferred_environment=`hidden_cdb_host`
  - Hidden dry-run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_hidden_soak.ps1 -Route map-pan -DurationSec 1800 -FrameIntervalSec 15 -PanIntervalSec 10 -ReportJson captures\current\hd-soak-short30-map-pan-current.json -ReportMarkdown captures\current\hd-soak-short30-map-pan-current.md -GuardJson captures\current\hd-soak-short30-map-pan-guard-current.json -GuardMarkdown captures\current\hd-soak-short30-map-pan-guard-current.md -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128`
  - Hidden runtime: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_hidden_soak.ps1 -Route map-pan -DurationSec 1800 -FrameIntervalSec 15 -PanIntervalSec 10 -ReportJson captures\current\hd-soak-short30-map-pan-current.json -ReportMarkdown captures\current\hd-soak-short30-map-pan-current.md -GuardJson captures\current\hd-soak-short30-map-pan-guard-current.json -GuardMarkdown captures\current\hd-soak-short30-map-pan-guard-current.md -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Execute`

## Current First-Step Command

Safe dry-run command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Json
```

Approval-gated runtime command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Execute -AllowVisibleRuntime -RequirePass -Json
```

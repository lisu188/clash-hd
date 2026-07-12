# HD Soak Dry-Run Plan

- Overall: PASS
- Generated: `2026-07-12T18:47:59.041715+00:00`
- Runtime policy: repo-only soak dry-run plan guard; invokes the PowerShell harness only without -Execute unless --read-plan-json is supplied; does not launch Clash95, CDB, wrappers, or visible windows
- Status: `ready_for_explicit_approval`
- Current step: `short2_map_idle` status=`missing_pending_approval`
- Tier/route: `short2` / `map-idle`
- Dry run: `True`
- Candidate dir: `C:\ClashTests\hd-soak`
- Output root: `C:\ClashCaptures\hd-soak`
- Report JSON: `C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-map-idle-current.json`
- Max input drift px: `1`
- Intro skip: mode=`postmessage` repeat=`8` pulses=`4`
- Approval TTL: `PASS; expires=2026-07-13T06:47:58.9771628+00:00; remaining_seconds=43199.935447; min_minutes=30`
- Stable stage should change: `False`
- Right-bottom promotion blocked: `True`

## Approval-Gated Execute Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'map-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260712_204758.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-map-idle-current.json' -ReportMarkdown 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-map-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -SampleIntervalSec '15' -MaxInputDriftPx '1' -MinNonblackPercent '10' -MinUniqueSampleColors '8' -MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' -MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' -VisibleRuntimeApprovalExpiresUtc '2026-07-13T06:47:58.9771628+00:00' -VisibleRuntimeApprovalToken '88c3c3b5e88c3564' -Execute -AllowVisibleRuntime -RequirePass -Json
```

## Invocation

- Used fixture plan: `False`
- Exit code: `0`
- Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route map-idle -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10.0 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Json`

# HD Soak Short-Tier Ladder

- Overall: PASS
- Generated: `2026-07-12T19:11:23.478337+00:00`
- Runtime policy: repo-only short-tier soak ladder; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Protected stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Ladder complete: `False`
- Current step: `short2_map_idle`
- Stable stage should change: `False`
- Right-bottom promotion blocked: `True`
- Long tiers locked: `True`
- Future lanes locked: `True`

## Steps

- `short2_menu_idle`: tier=`short2` route=`menu-idle` status=`pass` passed=`True`
- `short2_map_idle`: tier=`short2` route=`map-idle` status=`approval_required` passed=`False`
- `short10_map_idle`: tier=`short10` route=`map-idle` status=`locked_by_prerequisite` passed=`False`
- `short10_map_pan`: tier=`short10` route=`map-pan` status=`locked_by_prerequisite` passed=`False`
- `short30_map_pan`: tier=`short30` route=`map-pan` status=`locked_by_prerequisite` passed=`False`

## Current Step Commands

Safe dry-run command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route map-idle -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Json
```

Approval-gated runtime command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route map-idle -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Execute -AllowVisibleRuntime -RequirePass -Json
```

## Locked Future Lanes

- `castle_overview_enter_exit`: status=`planned_not_implemented` implemented=`False`
- `barracks_castle_centered_input`: status=`planned_not_implemented` implemented=`False`
- `right_bottom_action_menu`: status=`planned_blocked_by_manual_or_natural_proof` implemented=`False`
- `tactical_battle_entry_return`: status=`planned_not_implemented` implemented=`False`
- `save_load_roundtrip`: status=`planned_not_implemented` implemented=`False`
- `turn_advancement`: status=`planned_not_implemented` implemented=`False`
- `campaign_route`: status=`planned_not_implemented` implemented=`False`

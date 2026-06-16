# HD Soak Dry-Run Plan

- Overall: PASS
- Generated: `2026-06-16T16:05:29.621281+00:00`
- Runtime policy: repo-only soak dry-run plan guard; invokes the PowerShell harness only without -Execute unless --read-plan-json is supplied; does not launch Clash95, CDB, wrappers, or visible windows
- Status: `ready_for_explicit_approval`
- Current step: `short2_menu_idle` status=`failed_classified_intro_skip_input_drift_exit`
- Tier/route: `short2` / `menu-idle`
- Dry run: `True`
- Candidate dir: `C:\ClashTests\hd-soak`
- Output root: `C:\ClashCaptures\hd-soak`
- Report JSON: `C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.json`
- Max input drift px: `1`
- Intro skip: mode=`postmessage` repeat=`8` pulses=`4`
- Stable stage should change: `False`
- Right-bottom promotion blocked: `True`

## Approval-Gated Execute Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'menu-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260616_180529.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.json' -ReportMarkdown 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -MaxInputDriftPx '1' -Execute -AllowVisibleRuntime -RequirePass -Json
```

## Invocation

- Used fixture plan: `False`
- Exit code: `0`
- Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -MaxInputDriftPx 1 -Json`

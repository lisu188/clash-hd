# HD Soak Intro-Skip Rerun Readiness

- Overall: FAIL
- Generated: `2026-07-12T18:47:59.253714+00:00`
- Runtime policy: repo-only intro-skip rerun readiness gate; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `not_ready`
- Triage classification: `passing_run_no_failure`
- Current step: `short2_map_idle` status=`missing_pending_approval`
- Approval boundary: The next runtime run will open a visible Clash95 game window and still requires explicit user approval.

## Intro-Skip Contract

- `click_mode`: `postmessage`
- `click_repeat`: `8`
- `space_pulses`: `4`
- `proof_class`: `intro_skip_harness_prep_not_manual_directinput_release_proof`

## Approval-Gated Runtime Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'map-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260712_204758.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-map-idle-current.json' -ReportMarkdown 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-map-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -SampleIntervalSec '15' -MaxInputDriftPx '1' -MinNonblackPercent '10' -MinUniqueSampleColors '8' -MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' -MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' -VisibleRuntimeApprovalExpiresUtc '2026-07-13T06:47:58.9771628+00:00' -VisibleRuntimeApprovalToken '88c3c3b5e88c3564' -Execute -AllowVisibleRuntime -RequirePass -Json
```

## Failures

- triage classification is 'passing_run_no_failure', expected 'intro_skip_input_drift_exit'
- current short step is 'short2_map_idle', expected 'short2_menu_idle'
- current short step status is 'missing_pending_approval', expected 'failed_classified_intro_skip_input_drift_exit'
- dry-run plan current step is 'short2_map_idle', expected 'short2_menu_idle'

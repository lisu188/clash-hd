# HD Soak Intro-Skip Rerun Readiness

- Overall: PASS
- Generated: `2026-06-17T07:48:28.854856+00:00`
- Runtime policy: repo-only intro-skip rerun readiness gate; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `ready_for_explicit_visible_rerun_approval`
- Triage classification: `intro_skip_input_drift_exit`
- Current step: `short2_menu_idle` status=`failed_classified_intro_skip_input_drift_exit`
- Approval boundary: The next runtime run will open a visible Clash95 game window and still requires explicit user approval.

## Intro-Skip Contract

- `click_mode`: `postmessage`
- `click_repeat`: `8`
- `space_pulses`: `4`
- `proof_class`: `intro_skip_harness_prep_not_manual_directinput_release_proof`

## Approval-Gated Runtime Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'menu-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260617_094828.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.json' -ReportMarkdown 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -SampleIntervalSec '15' -MaxInputDriftPx '1' -MinNonblackPercent '10' -MinUniqueSampleColors '8' -MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' -MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' -VisibleRuntimeApprovalExpiresUtc '2026-06-17T19:48:28.4321622+00:00' -VisibleRuntimeApprovalToken 'e0a6d4d17c088eac' -Execute -AllowVisibleRuntime -RequirePass -Json
```

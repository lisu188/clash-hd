# HD Soak Intro-Skip Rerun Readiness

- Overall: PASS
- Generated: `2026-06-16T16:05:29.903583+00:00`
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
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'menu-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260616_180529.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.json' -ReportMarkdown 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -MaxInputDriftPx '1' -Execute -AllowVisibleRuntime -RequirePass -Json
```

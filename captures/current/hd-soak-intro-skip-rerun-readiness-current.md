# HD Soak Intro-Skip Rerun Readiness

- Overall: FAIL
- Generated: `2026-09-08T09:22:02.994176+00:00`
- Runtime policy: repo-only intro-skip rerun readiness gate; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `not_ready`
- Triage classification: `passing_run_no_failure`
- Current step: `short2_map_idle` status=`failed_classified_window_missing_while_process_alive`
- Approval boundary: The next runtime run will open a visible Clash95 game window and still requires explicit user approval.

## Intro-Skip Contract

- `click_mode`: `postmessage`
- `click_repeat`: `8`
- `space_pulses`: `4`
- `stop_click_repeat_on_drift`: `True`
- `proof_class`: `intro_skip_harness_prep_not_manual_directinput_release_proof`

## Approval-Gated Runtime Command

```powershell

```

## Failures

- dry-run plan is not passing
- dry-run plan status is 'dry_run_plan_invalid'
- dry-run plan would change the stable stage
- dry-run plan does not keep right-bottom promotion blocked
- dry-run intro_skip click_mode is None, expected 'postmessage'
- dry-run intro_skip click_repeat is None, expected 8
- dry-run intro_skip space_pulses is None, expected 4
- dry-run intro_skip stop_click_repeat_on_drift is None, expected True
- dry-run intro_skip proof_class is None, expected 'intro_skip_harness_prep_not_manual_directinput_release_proof'
- approval command missing fragment: -IntroSkipClickMode
- approval command missing fragment: postmessage
- approval command missing fragment: -IntroSkipClicks
- approval command missing fragment: 8
- approval command missing fragment: -SkipPulses
- approval command missing fragment: 4
- approval command missing fragment: -SampleIntervalSec
- approval command missing fragment: 15
- approval command missing fragment: -MaxInputDriftPx
- approval command missing fragment: 1
- approval command missing fragment: -MinNonblackPercent
- approval command missing fragment: 10
- approval command missing fragment: -MinUniqueSampleColors
- approval command missing fragment: 8
- approval command missing fragment: -MaxArtifactMB
- approval command missing fragment: 250
- approval command missing fragment: -MaxWorkingSetGrowthMB
- approval command missing fragment: 64
- approval command missing fragment: -MaxPrivateMemoryGrowthMB
- approval command missing fragment: 64
- approval command missing fragment: -MaxHandleGrowth
- approval command missing fragment: 128
- approval command missing fragment: -VisibleRuntimeApprovalExpiresUtc
- approval command missing fragment: -VisibleRuntimeApprovalToken
- approval command missing fragment: -Execute
- approval command missing fragment: -AllowVisibleRuntime
- approval command missing fragment: -RequirePass
- approval command missing fragment: -Json
- dry-run visible runtime approval token is missing or malformed
- dry-run visible runtime approval expires_utc is missing

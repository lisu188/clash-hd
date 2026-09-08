# HD Soak Dry-Run Plan

- Overall: FAIL
- Generated: `2026-09-08T09:22:02.590807+00:00`
- Runtime policy: repo-only soak dry-run plan guard; invokes the PowerShell harness only without -Execute unless --read-plan-json is supplied; does not launch Clash95, CDB, wrappers, or visible windows
- Status: `dry_run_plan_invalid`
- Current step: `short2_map_idle` status=`failed_classified_window_missing_while_process_alive`
- Tier/route: `short2` / `map-idle`
- Dry run: `None`
- Candidate dir: `None`
- Output root: `None`
- Report JSON: `None`
- Max input drift px: `None`
- Intro skip: mode=`None` repeat=`None` pulses=`None`
- Approval TTL: `FAIL; expires=None; remaining_seconds=None; min_minutes=30`
- Stable stage should change: `False`
- Right-bottom promotion blocked: `True`

## Approval-Gated Execute Command

```powershell

```

## Invocation

- Used fixture plan: `False`
- Exit code: `1`
- Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route map-idle -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10.0 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Json`

## Failures

- dry-run harness did not produce a readable JSON plan

# HD Soak Harness Guard

- Overall: PASS
- Generated: `2026-07-17T15:36:55+02:00`
- Runtime policy: repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Guard policy: HD soak harness must stay opt-in, protected-stage, non-promoting, and artifact-safe
- Script: `scripts\smoke\run_hd_soak.ps1`

## Checks

- `safe_defaults`: `PASS`
- `protected_stage_boundary`: `PASS`
- `short_tiers`: `PASS`
- `short_routes`: `PASS`
- `visible_runtime_opt_in`: `PASS`
- `intro_skip_policy`: `PASS`
- `windowed_mode`: `PASS`
- `window_health_stop`: `PASS`
- `artifact_policy`: `PASS`
- `patch_manifest_verification`: `PASS`
- `required_metrics`: `PASS`
- `promotion_boundary`: `PASS`

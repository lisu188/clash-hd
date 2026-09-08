# HD Soak Execution Boundary

- Overall: FAIL
- Generated: `2026-09-08T09:21:59.999253+00:00`
- Runtime policy: repo-local negative harness probe; invokes PowerShell only with invalid visible-runtime approval and a nonexistent input executable, and must not launch Clash95, CDB, wrappers, or visible windows
- Guard policy: invalid visible-runtime approval packets must fail before output, candidate, report, patch, or launch side effects
- Script: `scripts\smoke\run_hd_soak.ps1`
- Cases: `4`

## Cases

- `missing_token`: FAIL exit=`1` phrase=`False` side_effects=`none`
- `missing_expiry`: FAIL exit=`1` phrase=`False` side_effects=`none`
- `expired_packet`: FAIL exit=`1` phrase=`False` side_effects=`none`
- `token_mismatch`: FAIL exit=`1` phrase=`False` side_effects=`none`

## Failures

- missing_token did not fail closed before side effects
- missing_expiry did not fail closed before side effects
- expired_packet did not fail closed before side effects
- token_mismatch did not fail closed before side effects

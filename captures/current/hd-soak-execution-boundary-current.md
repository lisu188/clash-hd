# HD Soak Execution Boundary

- Overall: PASS
- Generated: `2026-07-12T17:43:37.615474+00:00`
- Runtime policy: repo-local negative harness probe; invokes PowerShell only with invalid visible-runtime approval and a nonexistent input executable, and must not launch Clash95, CDB, wrappers, or visible windows
- Guard policy: invalid visible-runtime approval packets must fail before output, candidate, report, patch, or launch side effects
- Script: `scripts\smoke\run_hd_soak.ps1`
- Cases: `4`

## Cases

- `missing_token`: PASS exit=`1` phrase=`True` side_effects=`none`
- `missing_expiry`: PASS exit=`1` phrase=`True` side_effects=`none`
- `expired_packet`: PASS exit=`1` phrase=`True` side_effects=`none`
- `token_mismatch`: PASS exit=`1` phrase=`True` side_effects=`none`

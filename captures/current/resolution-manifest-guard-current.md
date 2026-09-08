# Resolution Manifest Guard

- Overall: PASS
- Generated: `2026-09-08T10:59:55+02:00`
- Runtime policy: repo-only metadata inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: exactly one stable resolution (the 800x600 default), stable/validated entries backed by passing hidden-desktop evidence whose dimensions, stage, candidate SHA and run references agree with its passing patch metadata and smoke matrix, tile counts matching the engine formula; schema-2 profiles must match launcher contracts and Framed/Complete-HD remain experimental until their own scoped runtime evidence can be verified
- Manifest: `src\launcher\resolutions.json`
- Resolutions: `9`
- Status counts: `{'stable': 1, 'validated': 0, 'experimental': 8}`

## Checks

- `resolution_keys_valid`: `PASS`
- `single_stable_default`: `PASS`
- `stable_stage_matches`: `PASS`
- `profile_contracts`: `PASS`
- `tiles_formula`: `PASS`
- `evidence_backed`: `PASS`
- `custom_bounds_sane`: `PASS`

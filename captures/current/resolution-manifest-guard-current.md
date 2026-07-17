# Resolution Manifest Guard

- Overall: PASS
- Generated: `2026-07-17T15:36:47+02:00`
- Runtime policy: repo-only metadata inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: exactly one stable resolution (the 800x600 default), stable/validated entries backed by passing hidden-desktop evidence, tile counts matching the engine formula
- Manifest: `src\launcher\resolutions.json`
- Resolutions: `5`
- Status counts: `{'stable': 1, 'validated': 0, 'experimental': 4}`

## Checks

- `resolution_keys_valid`: `PASS`
- `single_stable_default`: `PASS`
- `stable_stage_matches`: `PASS`
- `tiles_formula`: `PASS`
- `evidence_backed`: `PASS`
- `custom_bounds_sane`: `PASS`

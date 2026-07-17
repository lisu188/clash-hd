# Load Slot Transition Geometry Guard

- Status: PASS
- Generated: `2026-07-17T15:36:07+02:00`
- Runtime policy: repo-only source/plan inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only when the transition run plan targets rows 3-5 and the surface-dump launcher still replaces extra-probe load-slot mouse placeholders using x=320 and y=166+22*slot shifted into raw mouse globals
- Promotion ready: `False`
- stable_stage_should_change: `False`
- Formula: `mouse_x=320; mouse_y=166+22*slot; raw=logical<<6`

## Checks

- `run_plan_passed`: `PASS`
- `target_rows_3_4_5`: `PASS`
- `surface_formula_present`: `PASS`
- `probe_placeholders_present`: `PASS`
- `commands_row_specific`: `PASS`
- `summary_commands_require_entry`: `PASS`
- `non_promoting`: `PASS`

## Row Geometry

- slot `3`: mouse=(320,232) raw=(00005000,00003a00)
- slot `4`: mouse=(320,254) raw=(00005000,00003f80)
- slot `5`: mouse=(320,276) raw=(00005000,00004500)

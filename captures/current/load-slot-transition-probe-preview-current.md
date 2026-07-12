# Load Slot Transition Probe Preview

- Status: PASS
- Generated: `2026-07-12T20:34:16+02:00`
- Runtime policy: repo-only generated-probe preview; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only when generated row 3-5 transition probes have no placeholders, carry row-specific raw mouse values, and keep late select/accept conditions targeted at the requested slot
- Promotion ready: `False`
- stable_stage_should_change: `False`
- Target rows: `[3, 4, 5]`
- Preview count: `3`

## Checks

- `run_plan_passed`: `PASS`
- `geometry_guard_passed`: `PASS`
- `target_rows_3_4_5`: `PASS`
- `geometry_rows_match_target_rows`: `PASS`
- `non_promoting`: `PASS`
- `all_previews_passed`: `PASS`

## Previews

### Slot 3

- Status: `PASS`
- SHA-256: `C64A3D0796E9A4000DA5D8DE27D5B4DA307BD2EBDE98FE7F8F45DC454A26F8C6`
- Mouse: `(320,232)`
- Raw: `(00005000,00003a00)`
- Slot condition count: `2`
- Target-slot marker count: `17`
- Raw-x replacement count: `2`
- Raw-y replacement count: `2`

### Slot 4

- Status: `PASS`
- SHA-256: `697C8481B5C0FA1FA109E4A85E8502FF2A57E723AF05E4F8B390C7C806826CD7`
- Mouse: `(320,254)`
- Raw: `(00005000,00003f80)`
- Slot condition count: `2`
- Target-slot marker count: `17`
- Raw-x replacement count: `2`
- Raw-y replacement count: `2`

### Slot 5

- Status: `PASS`
- SHA-256: `3864C049BB9E6CD91E7FB995163E999BDADEEFB8411CC4308756ECF87EB54509`
- Mouse: `(320,276)`
- Raw: `(00005000,00004500)`
- Slot condition count: `2`
- Target-slot marker count: `17`
- Raw-x replacement count: `2`
- Raw-y replacement count: `2`

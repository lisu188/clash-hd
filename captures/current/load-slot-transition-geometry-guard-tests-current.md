# Load Slot Transition Geometry Guard Tests

- Status: PASS
- Generated: `2026-06-15T20:46:41+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the transition plan stays tied to x=320, y=166+22*slot row geometry and requires entry/slot-match summaries

## Tests

- `load_slot_transition_geometry_guard records expected row geometry for slots 3, 4, and 5`
- `load_slot_transition_geometry_guard fails if the load-row formula drifts`
- `load_slot_transition_geometry_guard fails if CDB mouse placeholders are missing`
- `load_slot_transition_geometry_guard fails if commands target the wrong row`
- `load_slot_transition_geometry_guard fails if summary commands stop requiring entry`
- `load_slot_transition_geometry_guard CLI writes JSON/Markdown and honors --require-pass`

# Load Slot Transition Probe Preview Tests

- Status: PASS
- Generated: `2026-07-12T19:43:14+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves generated row-specific transition probes have no unresolved placeholders, keep slot-specific select/accept conditions, and preserve the planned raw mouse values

## Tests

- `load_slot_transition_probe_preview renders row-specific previews for slots 3, 4, and 5`
- `load_slot_transition_probe_preview fails if placeholders survive generation`
- `load_slot_transition_probe_preview fails if select/accept conditions are hard-coded`
- `load_slot_transition_probe_preview fails if geometry rows do not match the run plan`
- `load_slot_transition_probe_preview fails if the run plan is not passing`
- `load_slot_transition_probe_preview CLI writes JSON/Markdown and honors --require-pass`

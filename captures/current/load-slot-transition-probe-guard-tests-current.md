# Load Slot Transition Probe Guard Tests

- Status: PASS
- Generated: `2026-07-12T21:10:55+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the focused transition extra probe and surface-dump runner are ready for parameterized late-armed load-row selection after real load-menu entry

## Tests

- `load_slot_transition_probe_guard passes with the late-entry transition probe and extra placeholder replacement`
- `load_slot_transition_probe_guard fails if the probe reintroduces early 00419B80 descriptor forcing`
- `load_slot_transition_probe_guard fails if the extra probe has a standalone g command`
- `load_slot_transition_probe_guard fails if the runner does not replace extra probe load-slot placeholders`
- `load_slot_transition_probe_guard fails if late select/accept are hard-coded to slot 5`
- `load_slot_transition_probe_guard CLI writes JSON/Markdown and honors --require-pass`

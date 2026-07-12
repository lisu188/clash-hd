# Load Slot Transition Run Plan Tests

- Status: PASS
- Generated: `2026-07-12T20:47:31+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the transition command plan stays hidden, targets the current rows 3-5 pre-entry blocker, and remains non-promoting

## Tests

- `load_slot_transition_run_plan builds hidden transition commands for rows 3, 4, and 5`
- `load_slot_transition_run_plan fails if the blocked row set changes`
- `load_slot_transition_run_plan fails if the transition probe guard is not passing`
- `load_slot_transition_run_plan fails if early descriptor forcing returns`
- `load_slot_transition_run_plan fails if extra-probe placeholder replacement is missing`
- `load_slot_transition_run_plan fails if late select/accept are not target-slot parameterized`
- `load_slot_transition_run_plan fails if the candidate root is inside the repository`
- `load_slot_transition_run_plan CLI writes JSON/Markdown and honors --require-pass`

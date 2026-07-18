# Load Slot Entry Gap Tests

- Status: PASS
- Generated: `2026-07-18T21:36:15+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the load-slot entry-gap report preserves the distinction between early descriptor rows and real load-menu case entry

## Tests

- `load_slot_entry_gap_plan passes with static case-5 row-loop evidence and current pre-entry blocked rows`
- `load_slot_entry_gap_plan fails without the static ten-row case-5 loop`
- `load_slot_entry_gap_plan fails without the 0044895A load-menu-entry breakpoint`
- `load_slot_entry_gap_plan fails without the pre-entry load-coordinate row`
- `load_slot_entry_gap_plan fails closed when a blocked row reaches load-menu entry`
- `load_slot_entry_gap_plan fails when slot2 no longer reaches LOADSAVE`
- `load_slot_entry_gap_plan CLI writes JSON/Markdown and honors --require-pass`

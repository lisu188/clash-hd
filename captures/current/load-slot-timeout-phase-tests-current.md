# Load Slot Timeout Phase Tests

- Status: PASS
- Generated: `2026-06-16T18:04:51+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the load-slot timeout phase classifier preserves the current pre-load-menu-loop blocker shape for rows 3-5

## Tests

- `load_slot_timeout_phase passes when slot2 reaches load-menu accept and slots3-5 stall before load-menu entry`
- `load_slot_timeout_phase fails when slot2 no longer reaches LOADSAVE`
- `load_slot_timeout_phase fails when a blocked slot reaches load-menu entry`
- `load_slot_timeout_phase CLI writes JSON/Markdown and honors --require-pass`

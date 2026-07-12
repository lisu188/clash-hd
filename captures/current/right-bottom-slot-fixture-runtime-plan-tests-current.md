# Right-Bottom Slot Fixture Runtime Plan Tests

- Status: PASS
- Generated: `2026-07-12T20:47:29+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the future slot fixture runtime route stays hidden-desktop, uses an isolated workdir plus child candidate dir, requires strict fixture slot acceptance, and remains non-promoting

## Tests

- `right_bottom_slot_fixture_runtime_plan builds hidden fixture preparation and CDB commands`
- `right_bottom_slot_fixture_runtime_plan requires strict selected_arg/selected_global slot-0 fixture acceptance`
- `right_bottom_slot_fixture_runtime_plan fails if the fixture plan becomes promoting`
- `right_bottom_slot_fixture_runtime_plan fails if the preparation script guard fails`
- `right_bottom_slot_fixture_runtime_plan fails if the preparation script no longer seeds non-save workdir files`
- `right_bottom_slot_fixture_runtime_plan fails if the fixture result parser is missing`
- `right_bottom_slot_fixture_runtime_plan fails if the fixture root is inside the repository`
- `right_bottom_slot_fixture_runtime_plan CLI writes JSON/Markdown and honors --require-pass`

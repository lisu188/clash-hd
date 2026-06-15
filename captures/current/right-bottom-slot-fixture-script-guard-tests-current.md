# Right-Bottom Slot Fixture Script Guard Tests

- Status: PASS
- Generated: `2026-06-15T22:35:51+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the right-bottom fixture preparation helper stays dry-run by default, copies only after -Execute, refuses live-save/repo outputs, and avoids visible-runtime APIs

## Tests

- `right_bottom_slot_fixture_script_guard passes with dry-run gated fixture copy shape`
- `right_bottom_slot_fixture_script_guard fails without the -Execute dry-run gate`
- `right_bottom_slot_fixture_script_guard fails if Copy-Item can run before dry-run exit`
- `right_bottom_slot_fixture_script_guard fails without the live C:\Clash\save output guard`
- `right_bottom_slot_fixture_script_guard fails without the workdir seed save-directory exclusion`
- `right_bottom_slot_fixture_script_guard fails on visible/runtime launcher APIs`
- `right_bottom_slot_fixture_script_guard CLI writes JSON/Markdown and honors --require-pass`

# Right-Bottom Slot Fixture Plan Tests

- Status: PASS
- Generated: `2026-07-12T21:35:39+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the isolated slot5-as-slot0 workaround remains non-promoting, safe to stage outside the repository, and invalid once natural slot5 loading is proven

## Tests

- `right_bottom_slot_fixture_plan passes with current slot5-as-slot0 non-promoting fixture shape`
- `right_bottom_slot_fixture_plan fails if the candidate matrix becomes promotion-ready`
- `right_bottom_slot_fixture_plan fails if slot5 is no longer blocked before LOADSAVE`
- `right_bottom_slot_fixture_plan fails if the fixture output would be inside the repository`
- `right_bottom_slot_fixture_plan CLI writes JSON/Markdown and honors --require-pass`

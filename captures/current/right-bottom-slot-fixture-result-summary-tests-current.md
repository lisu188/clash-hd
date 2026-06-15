# Right-Bottom Slot Fixture Result Summary Tests

- Status: PASS
- Generated: `2026-06-15T22:14:17+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves future right-bottom slot fixture CDB logs can be classified as load failure, owner-flag blocked, owner-loop without action, owner/action reached, slot mismatch, or AV failure with strict LOADSAVE slot consistency

## Tests

- `right_bottom_slot_fixture_result_summary classifies owner/action success`
- `right_bottom_slot_fixture_result_summary classifies owner-flag-blocked fixture logs`
- `right_bottom_slot_fixture_result_summary classifies missing LOADSAVE/PlayGame logs`
- `right_bottom_slot_fixture_result_summary classifies owner-loop-without-action logs`
- `right_bottom_slot_fixture_result_summary fails closed on AV rows`
- `right_bottom_slot_fixture_result_summary fails closed on conflicting LOADSAVE slot fields`
- `right_bottom_slot_fixture_result_summary fails closed on wrong LOADSAVE slot`
- `right_bottom_slot_fixture_result_summary CLI writes JSON/Markdown and honors owner-action gates`
- `right_bottom_slot_fixture_result_summary CLI fails when owner/action is required but blocked`
- `right_bottom_slot_fixture_result_summary CLI fails when slot match is required but LOADSAVE fields conflict`

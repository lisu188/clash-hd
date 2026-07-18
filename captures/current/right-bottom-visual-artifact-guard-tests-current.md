# Right-Bottom Visual Artifact Guard Tests

- Status: PASS
- Generated: `2026-07-18T22:14:05+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the right-bottom visual artifact guard validates the resolved state (user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence) with promotion still deferred, and fails closed if the fixture evidence, compose matrix, triage, or controlled recovery state changes

## Tests

- `right_bottom_visual_artifact_guard passes for the resolved fixture-accepted natural-draw state`
- `right_bottom_visual_artifact_guard fails if blocker triage is missing`
- `right_bottom_visual_artifact_guard accepts the current and legacy non-promoting triage classifications`
- `right_bottom_visual_artifact_guard fails closed if the fixture natural-draw payload is missing`
- `right_bottom_visual_artifact_guard fails closed if any fixture natural-draw marker regresses`
- `right_bottom_visual_artifact_guard fails closed if the fixture natural-draw log has AV rows`
- `right_bottom_visual_artifact_guard fails if the compose matrix stops passing`
- `right_bottom_visual_artifact_guard fails if the compose matrix would flip stable promotion`
- `right_bottom_visual_artifact_guard fails if controlled composition recovery regresses`
- `right_bottom_visual_artifact_guard CLI writes JSON/Markdown and honors --require-pass`

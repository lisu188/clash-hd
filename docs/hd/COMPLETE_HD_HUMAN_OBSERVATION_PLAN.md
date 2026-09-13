# Complete candidate human observation planning

`tools/complete_hd_manual_plan.py` prepares the five human-operated targets
against a complete builder `.candidate.json` bundle. It rebuilds the actual
candidate and canonical probe through the shared context verifier, then pins
their hashes, resolution, stage, recipe, metadata and producer sources. It does
not change the historical pulse-oriented manual planner or its reports.

Example planning command, with existing candidate and new external paths:

```powershell
python tools/complete_hd_manual_plan.py `
  --candidate-manifest C:/ClashTests/example/candidate.candidate.json `
  --run-id human-1080-review `
  --output-root C:/ClashCaptures/completehd-human `
  --write-json C:/ClashCaptures/completehd-human/human-1080-review-plan.json
```

Planning executes no PowerShell, debugger, game, input or capture operation and
creates no approval record. Output refuses to overwrite an earlier artifact.
`planning_valid` describes the prepared plan; `runtime_ready`,
`manual_input_accepted` and `promotion_ready` remain false. Requesting
`--require-runtime-ready` returns exit code 2 while preparation is incomplete.

The plan derives the full framed terrain, all six action cells and centered
native 640x480 canvas from candidate geometry. Canvas and terrain bounds are
observation regions, not invented clickable rectangles. Minimap backing size
depends on the loaded world. Castle target hit maps depend on the actual asset
and owner state. Their exact targets remain unknown until source- and
candidate-bound observation is available; slot drawing geometry and historical
pulse points cannot fill those gaps.

The first ordinary selected-unit panel command has an existing passive
descriptor, X/Y hit-test, pressed-input gate, dispatch and callback protocol in
`hd_layout_observation_manifest.py`. Its human input mode and shared candidate
manifest must be selected. That observer proves only its first panel command;
it does not implement the five complete manual release verifiers or the other
castle, menu, minimap and grid routes.

Each target includes structured arguments for the visual harness's existing
`-InputMode manual -ObserveProcessId` attachment path. The process ID remains
unresolved until measured in the separately approved session. There is no
candidate launch command: omitting the PID would select a legacy launch and
global-cleanup path. Before actual observation, bind the exact wrapper,
configuration, isolated save/assets, owning process/start time and HWND, then
obtain fresh explicit approval against the saved plan hash and permitted run
interval. The owning process manager must verify cleanup.

The human operates every route and control using their physical mouse and
keyboard. Watching injected input never becomes manual proof. Measure client
placement, all four corners and each control target; do not reuse desktop
offsets. Retain two or three consecutive captures at every meaningful rendering
change and transition, inspect tearing and prefer an identical pair. Label
stage, resolution, capture method, target and result. The existing attachment
captures frames but does not itself bind this plan or accept input behavior as
release proof, so those acceptance adapters remain explicit implementation
gaps.

Offline tests: `python tools/test_complete_hd_manual_plan.py`.

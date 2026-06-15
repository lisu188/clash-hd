# Clash95 HD Soak Test Roadmap

This roadmap moves HD validation from narrow route proofs toward endurance
evidence. It does not promote any validation-only patch group and does not
change the protected stable stage:

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`

## Policy

- Soak runs are opt-in. The harness dry-runs by default and only launches the
  game with `-Execute -AllowVisibleRuntime`.
- Candidates are generated under `C:\ClashTests\...`.
- Raw frame artifacts are written outside the repo under `C:\ClashCaptures`.
- Repo output is limited to compact JSON/Markdown summaries in
  `captures/current`.
- The right-bottom action/menu lane remains non-promoting until real
  input-source or approved manual DirectInput proof replaces debugger-forced
  action-click proof.
- CDB-only and automated visible-runtime proof are diagnostic. They are not
  release-complete manual input proof.

## Harness

Dry-run the first short tier:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 `
  -Tier short2 `
  -Route menu-idle
```

Execute the first short tier only after approving visible runtime control:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 `
  -Tier short2 `
  -Route menu-idle `
  -Execute `
  -AllowVisibleRuntime `
  -RequirePass
```

Validate a generated report without launching the game:

```powershell
python tools\hd_soak_report.py captures\current\hd-soak-short-current.json --require-pass
```

Classify a pending or failed soak report without launching the game:

```powershell
python tools\hd_soak_failure_triage.py captures\current\hd-soak-short-current.json
```

Inventory route coverage without launching the game:

```powershell
python tools\hd_soak_route_coverage.py --require-pass
```

Refresh the ordered short-tier ladder without launching the game:

```powershell
python tools\hd_soak_short_tier_ladder.py --require-pass
```

Refresh the durable per-step short-soak artifact manifest without launching the
game:

```powershell
python tools\hd_soak_short_artifact_manifest.py --require-pass
```

Refresh the per-step short-soak status without launching the game:

```powershell
python tools\hd_soak_short_step_status.py --require-pass
```

Refresh the repo-only release-horizon checklist without launching the game:

```powershell
python tools\hd_endurance_release_checklist.py
```

Refresh the repo-only next-action handoff without launching the game:

```powershell
python tools\hd_endurance_next_actions.py
```

## Short Tiers

| Tier | Duration | Initial routes | Promotion meaning |
| --- | ---: | --- | --- |
| `short2` | 2 min | `menu-idle`, then `map-idle` | Smoke endurance only. Does not promote. |
| `short10` | 10 min | `map-idle`, `map-pan` | Short stability trend. Does not promote. |
| `short30` | 30 min | `map-pan`, castle enter/exit when scripted | Pre-endurance screen/input trend. Does not promote. |

The first required milestone is one passing `short2` run on the protected
default stage. Longer tiers stay opt-in and should not enter default tests.

The compact route coverage inventory is generated at
`captures/current/hd-soak-route-coverage-current.md`. The current harness
implements `3/10` release lanes: `menu-idle`, `map-idle`, and `map-pan`.
Castle, barracks, right-bottom, battle, save/load, turn-advancement, and
campaign lanes remain planned/non-promoting until their prerequisite short
soaks, natural/manual input proof, and continuity gates exist.

The ordered short-tier ladder is generated at
`captures/current/hd-soak-short-tier-ladder-current.md`. It keeps the current
step at `short2` `menu-idle` until that approval-gated visible-runtime run
passes, then advances to `short2` `map-idle`, `short10` `map-idle`,
`short10` `map-pan`, and `short30` `map-pan`. The ladder is a planning guard:
it passes as a repo-only artifact while `ladder_complete=false`, and keeps
2h+ tiers and future screen/state lanes locked until the short ladder has real
evidence.

The durable short-soak artifact manifest is generated at
`captures/current/hd-soak-short-artifact-manifest-current.md`. It assigns each
short ladder step its own current report, guard, and triage paths, for example
`captures/current/hd-soak-short2-menu-idle-current.json` for the first runtime
step. The existing `captures/current/hd-soak-short-current.json` remains a
compatibility report for the current short-soak guard.

The short validation refresh is generated at
`captures/current/hd-soak-short-validation-refresh-current.md`. It is repo-only
post-processing: when a canonical short-step report appears, it writes that
step's guard and failure-triage outputs before the status reader runs. If no
canonical runtime report exists yet, it stays in a passing pending state and
does not launch the game.

The per-step short-soak status is generated at
`captures/current/hd-soak-short-step-status-current.md`. It reports each short
step as pending, locked, failed/classified, needing guard output, or passing.
It intentionally passes as a repo-only status artifact while no canonical
runtime report exists, but fails closed if a canonical runtime report appears
without its guard output or without triage for a failed run.

The approval preflight packet is generated at
`captures/current/hd-soak-approval-preflight-current.md`. It is repo-only and
does not launch the game. It verifies that the first `short2` `menu-idle`
runtime command is still explicit-approval gated, uses the canonical per-step
report paths, keeps the dry-run command non-executing, preserves the protected
stage and right-bottom promotion locks, and requires clean harness/runtime,
process-hygiene, and executable-artifact guards before asking for approval:

```powershell
python tools\hd_soak_approval_preflight.py --require-pass
```

## Route Expansion

1. `menu-idle`: launch, skip startup, sample the main menu.
2. `map-idle`: load a representative save route and sample stable 800x600 map
   rendering.
3. `map-pan`: drive deterministic cursor movement across the map and sample
   input responsiveness plus frame stability.
4. Castle overview enter/exit: require centered input evidence and no modal
   desync.
5. Barracks/castle centered input: require enter/exit and click-path evidence.
6. Right-bottom action menu: run only when eligible and keep forced-coordinate
   rows diagnostic.
7. Tactical battle entry/return: require transition, battle UI, return, and
   post-return map health.
8. Save/load roundtrip: run only on safe test saves and verify continuity.
9. Turn advancement and campaign routes: add after short tiers show stable
   rendering and no input drift.

## Metrics

Each soak report must track:

- crash or AV class, exit code, and whether the harness stopped cleanly
- hang symptoms, frame sample count, and capture errors
- 800x600 frame size
- nonblack percent and nonblack bounds
- mean luminance
- unique sampled colors as a palette/artifact signal
- frame hash count and frame progression or stable-idle status
- route/input probe results
- working-set and handle growth when available
- artifact bytes and artifact root
- final route marker
- expected original base SHA-256, candidate SHA-256, and the per-run
  `patch_stage_report.py` manifest proving the protected stage bytes are
  patched with zero `original` or `unexpected` selected bytes

A nonblack frame alone is not enough. A passing report needs process liveness,
clean stop, route/input evidence for the chosen route, stable frame metrics, and
passing patch-stage evidence for the protected default stage.

## Failure Report

When a soak fails, the compact report should record:

- tier, route, stage, candidate SHA-256, and timestamp
- output directory under `C:\ClashCaptures`
- last route marker and last input probe row
- last frame hash, size, nonblack percent, mean luminance, and unique colors
- process state, exit code, working set, handle count, and clean-stop status
- crash, hang, capture, artifact-budget, or input-response classification
- next probe or harness refinement

`tools/hd_soak_failure_triage.py` turns the raw soak report into the compact
failure record. It separates `not_executed_pending_approval` from real runtime
failures and classifies AV crashes, unexpected exits, render/palette regressions,
route/input failures, capture harness failures, artifact-budget failures,
missing frame progress, cleanup failures, and unclassified failures.

## Release Horizon Checklist

Release completion needs all of these, not just a short soak:

- protected default stage remains unchanged until strict promotion evidence
  passes
- stable menu load with real input
- stable HD map input with no drift across long play
- castle overview centered input and enter/exit
- barracks/castle centered input and enter/exit
- right-bottom action/menu natural or approved manual DirectInput proof
- tactical battle entry, battle UI use, and return
- save/load roundtrip continuity on safe test saves
- turn advancement without state desync
- campaign-route progression without palette corruption
- 2h+ opt-in soak passes on representative routes
- no AVs, hangs, artifact buildup, handle growth trend, or memory growth trend
  outside the documented threshold
- no raw captures, binaries, saves, dumps, or local artifacts committed

The compact current checklist is generated at
`captures/current/hd-endurance-release-checklist-current.md`. It intentionally
fails closed until every release-horizon item has current proof. As of the
current checklist, `4/14` requirements pass and the next milestone is a passing
`short2` `menu-idle` soak for the protected stable stage.

The compact next-action handoff is generated at
`captures/current/hd-endurance-next-actions-current.md`. It keeps the safe
dry-run command separate from the exact approval-gated visible-runtime command
and lists the post-run validation sequence.

The short-tier ladder is generated at
`captures/current/hd-soak-short-tier-ladder-current.md`. It records the same
approval-gated first runtime command and prevents skipping directly to
long-tier, castle, battle, right-bottom, save/load, turn, or campaign lanes.

The short artifact manifest is generated at
`captures/current/hd-soak-short-artifact-manifest-current.md`. It records the
canonical per-step report outputs so future short soak results can accumulate
without overwriting the generic compatibility report.

The short validation refresh is generated at
`captures/current/hd-soak-short-validation-refresh-current.md`. It regenerates
per-step guard and triage artifacts for any canonical report that already
exists, then lets the short-step status report consume those outputs.

The short-step status report is generated at
`captures/current/hd-soak-short-step-status-current.md`. It is the compact
reader for those per-step outputs and names the current next command or missing
validation step.

The approval preflight report is generated at
`captures/current/hd-soak-approval-preflight-current.md`. It is the final
repo-only packet before requesting the visible-runtime `short2` `menu-idle`
approval and should pass before any execution approval is requested.

## Current Status

Current evidence still shows the right-bottom action/menu lane as
non-promoting: v17b proves copyback only after a debugger-forced native action
click. The next short soak road must not mask that blocker. The first soak
milestone is a `short2` `menu-idle` run on the protected default stage, followed
by `short2` `map-idle`, `short10` `map-idle`, `short10` `map-pan`, and
`short30` `map-pan`.

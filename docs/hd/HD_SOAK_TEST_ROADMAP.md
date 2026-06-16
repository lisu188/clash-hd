# Clash95 HD Soak Test Roadmap

This roadmap moves HD validation from narrow route proofs toward endurance
evidence. It does not promote any validation-only patch group and does not
change the protected stable stage:

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`

## Policy

- Soak runs are opt-in. The harness dry-runs by default and only launches the
  game with `-Execute -AllowVisibleRuntime`.
- Dry-run-emitted execute commands must also include `-RequirePass -Json` so a
  copied runtime command fails closed and preserves machine-readable output.
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
  -Route menu-idle `
  -MaxInputDriftPx 1
```

Execute the first short tier only after approving visible runtime control:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 `
  -Tier short2 `
  -Route menu-idle `
  -MaxInputDriftPx 1 `
  -Execute `
  -AllowVisibleRuntime `
  -RequirePass
```

Validate a generated report without launching the game:

```powershell
python tools\hd_soak_report.py captures\current\hd-soak-short-current.json --max-input-drift-px 1 --require-pass
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

Persist and validate the current short-step dry-run handoff without launching
the game:

```powershell
python tools\hd_soak_dry_run_plan.py --require-pass
```

Refresh the fail-closed long-soak guard without launching the game:

```powershell
python tools\hd_soak_long_report_guard.py
```

Refresh the repo-only release-horizon checklist without launching the game:

```powershell
python tools\hd_endurance_release_checklist.py
```

Refresh the fail-closed state-continuity guard without launching the game:

```powershell
python tools\hd_continuity_status.py
```

Refresh the repo-only next-action handoff without launching the game:

```powershell
python tools\hd_endurance_next_actions.py
```

The handoff records the current short-step report, guard, and triage artifact
paths with existence flags, so a missing canonical runtime report stays visible
before and after the approval-gated run.

Record the broad repo-only Python test sweep without launching the game:

```powershell
python tools\repo_test_sweep.py --write-json captures\current\repo-test-sweep-current.json --write-markdown captures\current\repo-test-sweep-current.md --require-pass
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

The dry-run handoff plan is generated at
`captures/current/hd-soak-dry-run-plan-current.md`. It invokes the PowerShell
harness without `-Execute`, persists the actual JSON plan emitted by the
harness, and fails closed if the current short step drifts from the protected
stage, canonical report paths, outside-repo candidate/output roots,
`-MaxInputDriftPx 1`, or copied execute-command `-RequirePass -Json` flags. The
copied execute command must also explicitly pin `-InputExe`, `-WorkDir`,
`-Stage`, and `-OutputRoot` so the approved run cannot silently fall back to a
different source executable, working directory, stage, or artifact root.
Approval packets treat dry-run plans older than 12 hours as stale and fail
closed; regenerate `captures/current/hd-soak-dry-run-plan-current.*` before
approval instead of running an old timestamped command.

The approval preflight packet is generated at
`captures/current/hd-soak-approval-preflight-current.md`. It is repo-only and
does not launch the game. It verifies that the first `short2` `menu-idle`
runtime command is still explicit-approval gated, consumes the current dry-run
plan, uses the canonical per-step report paths, pins `-MaxInputDriftPx 1`,
keeps the dry-run command non-executing, preserves the protected stage and
right-bottom promotion locks, and requires clean harness/runtime,
process-hygiene, and executable-artifact guards before asking for approval:
the same packet also lists whether the current-step report, guard, and triage
artifacts already exist so a pending approval packet cannot be mistaken for
completed soak evidence.

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
- sample interval and elapsed frame/process sample coverage for the requested
  tier duration
- min/max render ranges and raw route/process/frame/capture inventories; the
  repo-only harness source guard fails if these report fields are dropped
- frame hash count plus a stability classification: `menu-idle` and `map-idle`
  may be `stable_idle`, but `map-pan` must show frame progression with at
  least two unique frame hashes
- route/input probe results plus maximum path/sample drift in pixels
- documented input-drift threshold: by default short-tier reports fail if any
  route move or clicked sample drifts more than 1 pixel from the requested
  client/screen point, or if a route row omits drift metrics
- working-set and handle growth when available
- private-memory growth when available
- documented process-growth thresholds: by default short-tier reports fail if
  working-set growth exceeds 64 MB, private-memory growth exceeds 64 MB, or
  handle growth exceeds 128 handles
- artifact bytes and artifact root
- final route marker
- expected original base SHA-256, candidate SHA-256, and the per-run
  `patch_stage_report.py` manifest proving the protected stage bytes are
  patched with zero `original` or `unexpected` selected bytes

A nonblack frame alone is not enough. A passing report needs process liveness,
clean stop, route/input evidence for the chosen route, stable frame metrics, and
passing patch-stage evidence for the protected default stage. The raw harness
report must also mark itself passed and carry no source failures; derived guard
metrics are not allowed to override a failed source report.
`tools/hd_soak_report.py` also cross-checks headline metrics against the raw
frame, route, and process rows, so a report fails closed if summary counts,
input drift, memory growth, handle growth, or sampled render metrics disagree
with the detailed evidence.
It also rejects executed reports with invalid tier/route/duration combinations,
missing sample intervals, insufficient elapsed frame/process sample coverage,
capture errors, bad frame hashes, failed probe exit codes, or raw process
samples that show the process had already exited. Candidate and raw artifact
paths must also stay in the canonical soak roots: source executable
`C:\Clash\clash95.exe`, workdir `C:\Clash`, candidate under
`C:\ClashTests\hd-soak`, and output under `C:\ClashCaptures\hd-soak`.

## Failure Report

When a soak fails, the compact report should record:

- tier, route, stage, candidate SHA-256, and timestamp
- output directory under `C:\ClashCaptures`
- last route marker and last input probe row
- last frame hash, size, nonblack percent, mean luminance, and unique colors
- process state, exit code, working set, handle count, and clean-stop status
- crash, hang, capture, frame-progression, process-growth, artifact-budget,
  input-drift, input-response, insufficient-sample, or elapsed-coverage
  classification
- next probe or harness refinement

`tools/hd_soak_failure_triage.py` turns the raw soak report into the compact
failure record. It separates `not_executed_pending_approval` from real runtime
failures and classifies AV crashes, unexpected exits, render/palette regressions,
route/input failures including input drift, capture harness failures,
frame-progression failures, process-growth regressions, artifact-budget
failures, insufficient frame/process samples, elapsed sample-coverage failures,
missing frame progress, cleanup failures, and unclassified failures.
It also runs the same `tools/hd_soak_report.py` guard semantics before accepting
a raw `passed=true` report, so a source report that looks successful but has
bad canonical roots, missing patch evidence, metric mismatches, or other guard
failures is triaged as `guard_validation_failure` instead of being allowed to
unlock the next tier.

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
`short2` `menu-idle` soak for the protected stable stage. The first-soak row
also records the canonical report, guard, and triage artifact paths that must
appear after the approved run before later short tiers can advance.

The compact next-action handoff is generated at
`captures/current/hd-endurance-next-actions-current.md`. It keeps the safe
dry-run command separate from the exact approval-gated visible-runtime command
and separates the post-run commands into focused short-soak validation,
handoff refresh, and broad current-evidence refresh. When the current dry-run
plan is available, it also includes the plan-verified execute command emitted
by the harness, including the explicit `C:\Clash\clash95.exe` source,
`C:\Clash` working directory, protected stable stage, isolated
`C:\ClashTests\hd-soak` candidate path, `C:\ClashCaptures\hd-soak` output root,
canonical current report paths, and `-RequirePass -Json` approval flags. The
focused validation commands start with the short validation refresh so both
passing and failing runtime reports write guard and triage artifacts before the
short-step status is recomputed. Broad current-evidence refresh stays separate
so unrelated castle/map evidence cannot mask the soak result.

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
The broad current-evidence refresh keeps the legacy
`captures/current/hd-soak-short-current.json` compatibility report before any
canonical run exists, but once
`captures/current/hd-soak-short2-menu-idle-current.json` is present it uses that
first-step report for the global soak guard and triage rows. This prevents the
old compatibility report from keeping the aggregate red after an approved
first-step run has produced canonical evidence.

The state-continuity status report is generated at
`captures/current/hd-continuity-current.md`. It is not runtime proof by itself:
it fails closed until a compact approved proof manifest documents safe
test-save save/load, turn advancement, and campaign-route continuity without
mutating live `C:\Clash\save` files or committing forbidden artifacts. Each
continuity proof must include route markers, distinct start/end markers,
before/after observations, state hashes, stable-stage identity, approval record,
and compact evidence references.

The long-soak report guard is generated at
`captures/current/hd-soak-long-report-guard-current.md`. It is locked until the
short ladder completes, then requires approved 2h+ `map-idle` and `map-pan`
soak report guards before the release checklist can count representative
long-route endurance. It does not launch the game and does not unlock any
manual/input or validation-only promotion gate.

The approval preflight report is generated at
`captures/current/hd-soak-approval-preflight-current.md`. It is the final
repo-only packet before requesting the visible-runtime `short2` `menu-idle`
approval. It must agree with
`captures/current/hd-soak-dry-run-plan-current.md`, and the next-action
handoff should expose that same plan-verified execute command plus the same
focused/handoff/broad post-run command groups before any execution approval is
requested. The focused group must start with the consolidated short validation
refresh, not a direct `--require-pass` guard that would stop before failure
triage on a bad runtime report. Preflight also compares the next-action
artifact inventory with the current report, guard, and triage path/existence
state, so approval fails closed if the handoff is stale.

## Current Status

Current evidence still shows the right-bottom action/menu lane as
non-promoting: v17b proves copyback only after a debugger-forced native action
click. The next short soak road must not mask that blocker. The first soak
milestone is a `short2` `menu-idle` run on the protected default stage, followed
by `short2` `map-idle`, `short10` `map-idle`, `short10` `map-pan`, and
`short30` `map-pan`.

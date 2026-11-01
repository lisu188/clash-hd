# Clash95 HD Soak Test Roadmap

This roadmap moves HD validation from narrow route proofs toward endurance
evidence. It does not promote any validation-only patch group and does not
change the protected stable stage:

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`

## Policy

- Soak runs are opt-in. The visible harness launches only with
  `-Execute -AllowVisibleRuntime`; the hidden-CDB harness launches only with
  `-Execute` and has no visible-desktop fallback.
- Visible soak runs are windowed. Before either dry-run approval or execution, the
  harness requires the working-directory `dxcfg.ini` to declare
  `display=application` and `presentation=windowed`; its SHA-256 is part of the
  visible-runtime approval token.
- Dry-run-emitted execute commands must also include `-RequirePass -Json` so a
  copied runtime command fails closed and preserves machine-readable output.
- Visible-soak dry-run planning reads local files only. It leaves input-standing inspection
  explicitly unobserved; foreground/window inspection happens after the exact
  fresh approval packet passes. Invalid execution packets fail before that
  inspection or candidate, output, report, patch, and launch side effects.
- File SHA-256 checks in the visible harness use the .NET cryptography API so
  planning does not depend on `Get-FileHash` module discovery. Missing or
  invalid windowed configuration still rejects both dry-run planning and
  approved execution before launch.
- Candidates are generated under `C:\ClashTests\...`.
- Raw frame artifacts are written outside the repo under `C:\ClashCaptures`.
- Repo output is limited to compact JSON/Markdown summaries in
  `captures/current`.
- The right-bottom action/menu lane remains non-promoting until real
  input-source or approved manual DirectInput proof replaces debugger-forced
  action-click proof.
- Hidden CDB and automated visible-runtime proof are diagnostic. They are not
  release-complete manual input proof.

### Hidden-CDB host evidence class

`scripts\cdb\run_hidden_soak.ps1` provides an additive map endurance path when
visible composition and input are not the claim. It uses the memory-only local
DirectDraw proxy with presentation disabled, runs CDB on a hidden desktop, and
periodically reads the real 800x600 software surface from the target process.
The report keeps normal host process/cleanup/growth requirements, discloses the
breakpoint-forced load and scroll mechanics, and is labeled
`environment=hidden_cdb_host`.

Hidden reports must always carry
`input_responsiveness=not_applicable_hidden`. That sentinel is a passing
honesty/applicability check, not input proof. A hidden run can satisfy the map
render/process portions of the ordered short and long soak ladders, but cannot
replace the visible `short2_menu_idle` evidence, the five manual DirectInput
targets, final-composition evidence, or any promotion decision.

The hidden assembler and public environment grader always re-read bounded
retained candidate/patch, proxy/build, probe, CDB-log and raw-frame bytes. They
compare collection-time hashes/sizes, actual selected patch observations, full
indexed8 metrics and anchored marker inventories. Hidden long guards require all
three retained-byte check records and freshly regrade their source. A missing
file, changed receipt or saved consistency summary cannot stand in for backing.
The public hidden dispatcher additionally requires `source_report_binding`:
the supplied typed JSON must match the actual retained external report, and a
selected canonical copy must match its bytes exactly. Binding failures fail
`overall`; short status, intro completion and long admission reject stale saved
binding records and source hashes. The external `report_json` is not rewritten
to manufacture canonical identity. These source-only checks restore no artifacts.
These checks supply observed byte consistency only: native producer, loaded
target, coherent capture, canonical probe generation, independent cleanup and
running-time authentication remain separate prerequisites. Historical missing
evidence and failed attempts stay missing or failed.

### Replacement-evidence plan requested 2026-10-13

Status: **prepared, not executed**. The user requested preparation of this
strategy after the read-only regrade found fresh short acceptance `0/5`.
Preparation grants no replacement-run or visible-session approval, restores no
missing artifact, and does not unlock runtime or long tiers.

1. **Finish admission prerequisites.** Complete the remaining production gaps
   named in `AGENT_HANDOFF.md`, including canonical probe/source-samples binding,
   owned loaded-target/coherent reads, native cleanup verification and genuine
   running-time coverage. Pass public/source and focused checks without treating
   fixtures as native proof. Recheck disk reserve on every relevant volume,
   including archive, build, raw-frame, log and unknown-output allowances. At
   the recorded cleanup-time approximately 48.4 GB free, C: needed over 51.5 GB
   additional free space just to cross below 90%, before pending allowances.
   Recompute admission from live capacity rather than that transient observation.
   The bounded cache cleanup and already-removed duplicate static inputs cannot
   supply that space. On 2026-11-01 C: measured 89.68% and then 67.04% used
   within minutes during unrelated workstation activity; neither reading is
   admission, so measure again immediately before each write.
   Preserve evidence and request capacity recovery outside the audited disposable
   subset; do not expand cleanup or reduce the guard.
2. **Snapshot before canonical mutation.** After capacity admission, exclusively
   copy the complete existing canonical soak namespace to a unique external
   archive: reports, guards, triages, ladder/status, relevant manifests, long
   proof/guards and the compact revalidation conclusion. Include every existing
   consumer output that a short refresh or aggregate can overwrite. Inventory
   original logical paths, sizes and SHA-256s; verify every copied byte before
   recording archive completion. Keep original payloads and embedded paths
   unchanged. Archived receipts remain historical, not newly live proof. Leave
   current originals intact until a deliberate accepted replacement is ready;
   never run a canonical refresh first and archive its rewritten outputs later.
3. **Fix the replacement cohort.** Pin one authenticated candidate SHA for the
   unpublished diagnostic, four hidden map rungs and both long routes. Use
   independently named immediate run directories under the exact hidden roots.
   Pin the relevant source/template/build recipe and toolchain identities;
   record and check each run's actual proxy SHA and configuration-specific probe
   bytes. Different routes/durations legitimately produce different probes;
   their expected recipe must not change silently. Current short guards do not
   enforce cross-rung SHA equality, so a cohort manifest plus fresh comparison
   is an additional acceptance prerequisite, not an existing guard guarantee.
   Prepare a separately validated external working manifest with the same five
   rung IDs, durations and prerequisites, scoped to the replacement cohort.
   Require focused consumer tests before using that manifest. It must not import
   unbacked historical passes, omit a rung, or relax a guard. This keeps the old
   canonical failures visible and untouched while not misclassifying them as
   newly failed replacement attempts; future replacement rungs remain pending.
   Consumer fixtures must cover working manifest -> byte-identical canonical
   copies -> normal refresh/status -> long-prerequisite regrade. Verify both the
   manifest-selected alias and the retained external `report_json` byte binding;
   changing a guard's source alias must not rewrite or replace its source payload.
   The source follow-up now enforces this through mandatory
   `source_report_binding`, zero binding errors, matching actual SHA-256s and
   fresh saved-guard comparisons. Preserve those checks in the working-manifest
   consumer path; a saved pass or semantic-only copy cannot establish byte
   identity. Passing source fixtures do not satisfy replacement runtime admission.
4. **Run the diagnostic, then resolve the menu prerequisite.** After exact
   original SHA, stage, workdir, x86 CDB, save slot, proxy and physical-root
   preflight, run the unpublished hidden diagnostic below. Separately restore
   and freshly grade the exact original `short2_menu_idle` backing, or request
   fresh approval for a specific new visible menu session. Hidden map evidence
   cannot replace that rung or its evidence class. A prepared plan, an approved
   hidden lane or four passing map rungs does not authorize visible operation
   or establish `5/5`. The new visible alternative remains outside this hidden
   execution lane and must use its normal exact approval packet.
5. **Advance only on fresh cumulative evidence.** Execute the replacement map
   steps in the table sequentially after the menu prerequisite passes. Retain
   each complete external attempt first, without canonical destination switches.
   An accepted replacement requires assembler, environment dispatcher and all
   applicable fresh checks to pass. Refresh its guard, triage and short status
   through the validated cohort working manifest and external output paths,
   using matching environment/evidence class. Preserve exact report identity; do not
   rewrite `report_json` or provenance fields merely to match an alias. Failed
   or interrupted attempts stay separate with their diagnostics and never
   replace accepted evidence. Any failed gate stops the cohort; a new attempt
   requires explicit disposition, not an automatic retry.
6. **Close long proof and refresh.** Once all five cohort rungs genuinely pass,
   deliberately publish the complete accepted short canonical set, retaining
   the verified old snapshot and explicit supersession mapping. Freshly regrade
   the complete canonical `5/5` ladder and candidate cohort through the normal
   consumers before either long route. Run idle then pan on the
   pinned candidate, checking original/candidate hashes and owned cleanup again
   after each route. Require complete periodic coverage, ordered genuine route
   rows, safe inward pan plans, exact retained backing and the shared endpoint
   bound `duration - interval - 2`. Preserve scheduling-gap limits and distinguish
   actual running time from debugger holds and host sleep. Publish the accepted
   compact long reports/guards as `hd-soak-long-map-{idle,pan}-current.*`, create
   `hd-soak-long-proof-current.json`, and require the combined long-report guard
   to freshly accept both routes. Complete and inspect two full aggregate
   refreshes. Soak acceptance must pass; unrelated genuine failures stay explicit
   rather than being changed into release approval.

| Order | Route / purpose | Duration | Frame interval | Pan interval |
| --- | --- | ---: | ---: | ---: |
| D0 | unpublished hidden `map-idle` diagnostic | 60 s | 10 s | inactive |
| M0 | authenticated visible `short2_menu_idle` prerequisite | 120 s if replaced | approval packet | inactive |
| S1 | hidden `short2` `map-idle` | 120 s | 15 s | inactive |
| S2 | hidden `short10` `map-idle` | 600 s | 15 s | inactive |
| S3 | hidden `short10` `map-pan` | 600 s | 15 s | 10 s |
| S4 | hidden `short30` `map-pan` | 1,800 s | 15 s | 10 s |
| L1 | hidden long `map-idle`, after fresh `5/5` | 7,200 s | 30 s | inactive |
| L2 | hidden long `map-pan`, after L1 pass | 7,200 s | 30 s | 10 s |

The seven hidden runs total at least 4 h 53 min of runtime, excluding startup,
cleanup and validation; a separately approved replacement menu adds two minutes.
Full attempts and archive snapshots remain outside public Git. Canonical compact
local aliases do not authorize force-adding captures; publish only permitted
concise conclusions. No historical failing receipt is deleted or rehabilitated.

State transitions require exact artifact identities and fresh checks:
`prepared -> preflight_ready -> diagnostic_pass -> replacement_short_partial ->
fresh_short_5of5 -> long_idle_pass -> long_pair_pass -> refreshed_twice`.
Capacity, menu approval and production gaps remain explicit blockers rather than
implied completed states. Throughout the plan, retain
`environment=hidden_cdb_host`, `input_responsiveness=not_applicable_hidden` and
`present_enabled=0`. Manual DirectInput remains unproved at `0/5`; final visible
composition, release completion and protected-stage promotion remain unresolved.

## Harness

Dry-run the first short tier:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 `
  -Tier short2 `
  -Route menu-idle `
  -IntroSkipClickMode postmessage `
  -IntroSkipClicks 8 `
  -SkipPulses 4 `
  -MaxInputDriftPx 1
```

Execute the first short tier only after approving visible runtime control and
only by copying the exact command emitted by the current dry-run/preflight
artifacts. Do not hand-compose the visible-runtime command: the harness now
requires a fresh `-VisibleRuntimeApprovalExpiresUtc` and
`-VisibleRuntimeApprovalToken` packet plus explicit frame, artifact, and process
growth limits. The copied packet must have at least 30 minutes remaining before
expiry when execution starts. A valid copied command opens a visible Clash95
game window while it captures frames and includes at least `-Execute -AllowVisibleRuntime
-RequirePass -Json`.

The `postmessage` intro preparation stops its repeated click sequence as soon
as the sampled cursor/client coordinates drift after a click. That drift is
accepted only for the `intro-skip` row, only when the pre-click path verified,
the probe exit code is allowed, and the probe recorded
`sample_drift_after_click`. All ordinary route drift still fails closed. This
prevents another intro click from being posted to a newly transitioned window.

```powershell
python tools\hd_soak_dry_run_plan.py --require-pass
python tools\hd_soak_approval_preflight.py --require-pass
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

The ladder starts with one passing `short2` run on the protected default stage.
Its historical five recorded passes are not freshly verifiable at the
2026-10-08 checkpoint below: external provenance is missing. Do not restart
completed steps merely because a planning consumer expects a current step, or
unlock longer tiers from saved booleans. Restore authenticated evidence or
obtain a replacement-strategy decision first. Longer tiers stay opt-in and
should not enter default tests.

The compact route coverage inventory is generated at
`captures/current/hd-soak-route-coverage-current.md`. The current harness
implements `3/10` release lanes: `menu-idle`, `map-idle`, and `map-pan`.
Castle, barracks, right-bottom, battle, save/load, turn-advancement, and
campaign lanes remain planned/non-promoting until their prerequisite short
soaks, natural/manual input proof, and continuity gates exist. The same report
also records a locked future-route plan with proposed route names, planned step
contracts, unlock requirements, and `safe_to_execute_now=false` for every
not-yet-scripted lane; those contracts are inventory only, not harness routes.

The ordered short-tier ladder is generated at
`captures/current/hd-soak-short-tier-ladder-current.md`. Its sequence starts at
`short2` `menu-idle`, then advances to `short2` `map-idle`, `short10` `map-idle`,
`short10` `map-pan`, and `short30` `map-pan`. The ladder is a planning guard:
it may pass as a repo-only artifact while `ladder_complete=false`, and keeps
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
`-MaxInputDriftPx 1`, the `postmessage` intro-skip prep settings, or copied
execute-command `-RequirePass -Json` flags. The copied execute command must also
explicitly pin `-InputExe`, `-WorkDir`, `-Stage`, and `-OutputRoot` so the
approved run cannot silently fall back to a different source executable, working
directory, stage, or artifact root. The dry-run plan also emits
`-VisibleRuntimeApprovalExpiresUtc` plus `-VisibleRuntimeApprovalToken`; the
harness recomputes that token from the critical command fields and expiry, then
refuses visible execution when the token is missing, mismatched, or expired.
Approval therefore uses the exact copied packet rather than a hand-edited or
old timestamped command. The token fields also pin the SHA-256 of the required
windowed `dxcfg.ini` and the transition-safe intro-repeat policy.
Approval packets treat dry-run plans older than 12 hours as stale and the
harness also rejects expired copied commands or copied commands with less than
30 minutes of approval TTL remaining; regenerate
`captures/current/hd-soak-dry-run-plan-current.*` before approval instead of
running an old timestamped command.
`captures/current/hd-soak-execution-boundary-current.md` is the matching
negative proof: it sends bad approval packets with repo-local temp paths and a
nonexistent input executable, then verifies no candidate/output/report side
effects appear before the harness rejects the command.

The approval preflight packet is generated at
`captures/current/hd-soak-approval-preflight-current.md`. It is repo-only and
does not launch the game. It verifies that the first `short2` `menu-idle`
runtime command is still explicit-approval gated, consumes the current dry-run
plan, uses the canonical per-step report paths, pins `-MaxInputDriftPx 1`,
pins `-IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4`, keeps
the dry-run command non-executing, requires the visible-runtime approval expiry
and token from the current dry-run packet, preserves the protected stage and
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
3. `map-pan`: visible runs drive deterministic cursor movement and measure
   input responsiveness; hidden-CDB runs disclose bounded forced scroll writes,
   follow each write with the native full map repaint used by arrow-key
   scrolling, require frame progression, and record input as not applicable.
   Hidden map-pan frames from before 2026-11-01 lack that repaint: after the
   first pan they mix stale and redrawn cells, so their metrics cannot show
   coherent panning.
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
- route/input probe results plus maximum path/sample drift in pixels for visible
  runs; hidden runs instead require structured forced-entry/pan markers and the
  exact `not_applicable_hidden` input sentinel
- documented input-drift threshold: by default short-tier reports fail if any
  route move or clicked sample drifts more than 1 pixel from the requested
  client/screen point, or if a route row omits drift metrics
- working-set and handle growth when available
- private-memory growth when available
- documented process-growth thresholds: by default short-tier reports fail if
  working-set growth exceeds 64 MB, private-memory growth exceeds 64 MB, or
  handle growth exceeds 128 handles
- artifact bytes, artifact limit, and artifact root
- final route marker
- expected original base SHA-256, candidate SHA-256, and the per-run
  `patch_stage_report.py` manifest proving the protected stage bytes are
  patched with zero `original` or `unexpected` selected bytes

A nonblack frame alone is not enough. A passing report needs process liveness,
verified stop, environment-appropriate route evidence, stable frame metrics, and
passing patch-stage evidence for the protected default stage. The raw harness
report must also mark itself passed and carry no source failures; derived guard
metrics are not allowed to override a failed source report.
`tools/hd_soak_report.py` also cross-checks headline metrics against the raw
frame, route, and process rows, so a report fails closed if summary counts,
input drift, memory growth, handle growth, or sampled render metrics disagree
with the detailed evidence.
The guard also records a dedicated `visual_anomalies` check: executed reports
must carry `NonblackBounds`, and frames below the configured nonblack or unique
color thresholds are labeled as black/blank patch risk or palette/stripe risk
instead of being buried in generic render metrics.
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
  visual-anomaly, input-drift, input-response, insufficient-sample, or
  elapsed-coverage classification
- next probe or harness refinement

`tools/hd_soak_failure_triage.py` turns the raw soak report into the compact
failure record. It separates `not_executed_pending_approval` from real runtime
failures and classifies AV crashes, unexpected exits, render/palette regressions,
route/input failures including input drift, capture harness failures,
frame-progression failures, process-growth regressions, artifact-budget
failures, insufficient frame/process samples, elapsed sample-coverage failures,
missing frame progress, cleanup failures, and unclassified failures.
When the compact route row lacks method fields, triage may read the referenced
per-route `mouse_path_probe` JSON and copy over the observed move/click mode,
sample phase, and click drift details. This is evidence enrichment only; it does
not launch the game, change the route proof class, or turn an automated visible
runtime probe into manual DirectInput release proof.
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
- first-mission selected-unit frame with no stripe or black-patch blockers
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
fails closed until every release-horizon item has current proof. The short
ladder has historical 5/5 receipts but currently lacks freshly verifiable
backing; representative 2h endurance and manual/promotion evidence also remain
outstanding. Its canonical report, guard and triage paths preserve each rung's
actual result. A stale planning failure must not request another first short
run or erase the preserved evidence.

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
state, and requires the dry-run approval expiry plus token, so approval fails
closed if the handoff is stale or manually edited.

## Current Status

### Revalidation checkpoint - 2026-10-08

The dated results below remain historical observations. Fresh local grading
currently rejects all five saved short reports: their exact external patch-stage
manifests, candidates and raw run artifacts are unavailable. Saved 5/5 flags
therefore cannot unlock long tiers. The status reader now regrades canonical
reports and the long guard revalidates the ladder instead of trusting saved
booleans. Hidden long guards additionally bind the exact retained source and
patch-manifest bytes and require fresh matching environment-aware grading.

The source harness now checks strict disk reserve and physical-root safety
before execution mutations, complete marker/pan order and interval coverage,
and matching terminal route/player/scroll state. The assembler and hidden
grader reject sparse endpoint-only inventories, invalid or excluded interior
frames and missing per-row process telemetry. The existing elapsed endpoint
formula remains unchanged; new
periodic-gap checks allow no more than two seconds of scheduling jitter.

No new runtime was executed. Capacity remains above the 90% guard, so builds,
captures, long runs and full aggregate refreshes are deferred. Restore original
authenticated evidence or obtain a new strategy decision; do not fabricate
replacement provenance or automatically rerun completed visible validation.
See [the compact conclusion](../../reports/hidden-soak-revalidation-20261008.json)
for the missing-artifact inventory.

The follow-up source batch adds exclusive, flushed and rehashed raw retention
for every periodic/terminal frame; complete-schedule and RGB edge-PNG admission;
and fail-closed artifact inventory/overflow handling. Structured live-bound pan
plans and marker line positions now survive serialization and independent
regrading. Hidden-only lexical layout requires one matching run below the exact
hidden roots, without claiming physical file authentication.

Native host source now admits suspended CDB to a retained no-breakaway,
kill-on-close job before resume and keeps termination, generation, drain, close
and original failure receipts. Only confirmed CreateProcess success grants
process/thread operation authority; failed or uncertain outputs remain diagnostic
debt. This adapter has not been compiled or executed at this checkpoint.
The 16 cleanup methods model 33 lifecycle cases; the 23 preflight/storage methods
use mocked observations plus tiny private raw files. Aggregate registration is
covered by 20 collection methods, not by an actual full aggregate refresh.

Real loaded target/probe identity, coherent held reads, physical artifact-byte
verification, independent cleanup-receipt replay and exclusion of debugger/sleep
holds from credited running time remain production requirements. The sampler
still discovers a target by PID/path and opens it for an unpaused read. Neither
that path nor source/mock checks establish native ownership, coherent frames or
endurance. Manual input, release completion and promotion remain open.

### Historical checkpoint - 2026-09-05

The [latest aggregate](../../captures/current/current-evidence-refresh-current.json)
records **164/166 passing checks at 2026-09-05T20:39:17+02:00**. The three short
planning consumers now reverify all five bound passing reports and guards,
then return `not_applicable_short_ladder_complete` without commands or runtime
authorization. Their 20/13/34 focused tests pass; the geometry guards and 19
long-guard fixtures also pass. Only the long-soak guard and release checklist
remain failed, for missing representative two-hour and manual/promotion proof.
The preserved [150/166](../../captures/current/hd-completion-refresh-observation-20260905-195856.json)
and [161/166](../../captures/current/hd-completion-refresh-observation-20260905-203422.json)
observations document earlier repaired guard failures. Runtime evidence remains
separate, including both failed two-hour attempts and the failed v4b traces.

Current evidence still shows the right-bottom action/menu lane as
non-promoting, and manual DirectInput remains a separate release blocker. The
ordered short ladder reached **5/5** on 2026-09-05, including the corrected
thirty-minute hidden map-pan pass. Both 2h routes still need passing proof.
The first [2h hidden map-idle report](../../captures/current/hd-soak-long2h-map-idle-current.json),
run `hidden-soak-20260905-114207-433-map-idle`, failed at **11:42:50Z** on cleanup:
239 surface/process samples, 383 heartbeats, and an exact 460800-tick
`SOAK_ROUTE_END` were recorded without an observed AV, but candidate PID 1336's
five-second exit wait preceded debugger PID 34356 because numeric PID sorting
reordered the cleanup list. Both processes were subsequently absent; that does
not erase the recorded timeout or make `clean_stop=false` pass.

Preserve the failed report, guard, and raw run unchanged. The runner now keeps
debugger-first order while deduplicating processes. The
[six cleanup fixtures](../../tools/test_hidden_soak_cleanup.py) pass under fully
mocked process control, retaining the 5000-ms timeout, identity bounds, errors,
and final presence checks; restoring the old sort reproduces the failure.
The separately named [120-second cleanup regression](../../captures/current/hd-soak-cleanup-regression-20260905-cdbfirst-01-map-idle.json),
run `hidden-soak-20260905-140338-409-map-idle`, and its
[guard](../../captures/current/hd-soak-cleanup-regression-20260905-cdbfirst-01-map-idle-guard.json)
passed at **12:06:11Z** on 2026-09-05: 13 surface/process samples, both game and
debugger stopped, no cleanup errors. The stable candidate SHA remains
`5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.

The second 2h idle run, `hidden-soak-20260905-141501-448-map-idle`, is
[interrupted without completion artifacts](../../captures/current/hd-soak-long2h-map-idle-interrupted-20260905-141501.json).
At **17:41:01Z** on 2026-09-05, session `36110` was unavailable and the
recorded candidate and CDB were absent. Its last heartbeat has
`tickdelta=419791`; no `SOAK_ROUTE_END`, final report, final guard, or sample
manifest exists. The cause of interruption is unverified. Preserve its raw
directory, the successful ladder and the failed earlier 2h artifacts. Do not
synthesize the planned `hd-soak-long2h-map-idle-cdbfirst-20260905-141200`
report/guard outputs. Neither the cleanup regression nor this incomplete run
proves the 2h requirement. The recorded “Approve debugger runs” authorization covers the
active hidden validation work, without visible/manual input or promotion.

Composition remains separate: the v4b action-bar audits at [800x600](../../captures/current/partialtiles-noop-v4-800-action-bar-audit-current.json)
and [1024x768](../../captures/current/partialtiles-noop-v4-1024-action-bar-audit-current.json)
each pass **6/6 complete cells** with exact source-pixel matches, while both
runtimes remain **FAIL** on trace integrity with no full convergence/presentation pair.
The separately converted diagnostic PNGs retain failed summaries and bind
raw surfaces, recorded palettes and candidate SHAs. This proves those software
pixels, not endurance, visible composition, manual input or promotion.
The [complete screenshot inventory](../../captures/current/action-bar-complete-screenshot-inventory-current.json)
checks all eight PNGs in the inventoried current resolution capture roots:
six old failures and two new pixel passes. The 12 separately audited saved
soak frames still fail their bar checks, for **20 screenshot checks** in total.
The earlier [six-screenshot action-bar audit](../../captures/current/action-bar-screenshot-audit-current.md)
still fails its captured bars, despite terrain/geometry passes. The
[completion audit](../../reports/hd_completion_audit.md) records the native
command-list-before-terrain overpaint order and the distinct partial-tile
validation stage. Its first 800x600 run, `20260905-142409`,
[failed before HD readiness](../../captures/current/partialtiles-800-pre-hd-failure-current.json):
640x480, owner `004617A0`, convergence status 0, no AV and no screenshot;
both recorded processes stopped. The probe now waits at native join
`0040B88A` for owner `0040AD40` and exact requested dimensions before arming
status checks. The final v4b checkpoint passes 16 builder fixtures and nine
harness fixtures covering 199 log cases, including the single `PTILE_MAP_READY` after contract and
before statuses. The subsequent [v2 run `20260905-195041`](../../captures/current/partialtiles-latearm-v2-800-failure-20260905-195041.json)
reached valid 800x600 readiness but failed after four incremental status-1
returns followed by status 0, before full convergence or any screenshot.
No AV was observed. Matching processes were absent afterward, with no captured
live PIDs for exact-PID cleanup evidence. The missing saved world coordinates
leave that run's status-0 cause unresolved. The
[v3 run `20260905-195807`](../../captures/current/partialtiles-inputdiag-v3-800-failure-20260905-195807.json)
then observed world `(90,7)`, map `(100,100)` and scroll `(10,17)`, outside
the ceiling viewport. It remains **FAIL**, with no composition-guard return,
native no-op exit, full convergence/presentation pair or PNG. Recorded CDB
PID 32676 and game PID 42256 were absent at the terminal observation. Preserve
all three failed partial-tile runs unchanged.
The final probe/harness now require matching guard, input, raw status and native
exit to accept a strictly offscreen normal-map notification as a no-op, with no
draw/present credit. Visible partial cells and full convergence/presentation
remain required; candidate bytes are unchanged. Under the
[immutable v4b plan](../../captures/current/partialtiles-noop-v4b-run-plan-current.json),
[800x600 run `20260905-201619`](../../captures/current/partialtiles-noop-v4-800-observation-current.json) ended with exit 1 because an incremental input
or native exit lacked its guard/invocation. It captured an 800x600 raw surface,
but no full convergence/presentation markers; no AV or timeout was observed.
Recorded CDB PID 42988 and game PID 38892 were absent at **18:21:27Z**.
Preserve the failed summary and unmatched/repeated trace rows independently
of the passing pixel audit. The [1024x768 run `20260905-202225`](../../captures/current/partialtiles-noop-v4-1024-observation-current.json)
also ended with exit 1 on repeated or out-of-order incremental input, with no
full convergence/presentation markers. It captured a 1024x768 raw surface,
with no observed AV or timeout; recorded CDB PID 28444 and game PID 35832 were absent at
**18:25:10Z**. Preserve its failed summary separately from the passing pixel audit.
Audit every new screenshot's
complete bottom-right bar. The v7 continuity producer/parser have 20/33 passing focused
tests and private preparation, but no execution at that checkpoint. None of
these lanes reopens the accepted historical battle/right-bottom proof or
changes the manual-input and promotion boundaries.

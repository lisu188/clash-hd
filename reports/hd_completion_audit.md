# HD completion audit

Audit date: **2026-09-05**, updated after the 19:23:55Z screenshot inventory. Source line
references identify the initially inspected checkout and may move as
implementation progresses. This audit links evidence; it is not itself runtime
or promotion proof. The first thirty-minute step finished but failed its pan
interval check; the [failed run](../captures/archive/hidden-soak-short30-20260905-103139/README.md)
is preserved. Its replacement probe uses one clock sample per redraw, and the
corrected run `hidden-soak-20260905-110757-602-map-pan` passed at
2026-09-05T09:38:35Z, including the shared guard and cleanup checks. The short
ladder is now 5/5. The two-hour map-idle run
`hidden-soak-20260905-114207-433-map-idle` started at 09:42:12Z and
[failed at 11:42:50Z](../captures/current/hd-soak-long2h-map-idle-current.json)
on cleanup despite completing its route interval. The separate cleanup
regression `hidden-soak-20260905-140338-409-map-idle` passed at 12:06:11Z.
A second 2h idle run `hidden-soak-20260905-141501-448-map-idle` is
[interrupted without completion artifacts](../captures/current/hd-soak-long2h-map-idle-interrupted-20260905-141501.json),
as observed at 17:41:01Z; both 2h routes still need passing proof. The
[latest aggregate](../captures/current/current-evidence-refresh-current.json)
records **164/166** passing checks at **20:39:17+02:00**. Only the long-soak
guard and release checklist remain failed, for missing two-hour routes and
manual/promotion proof. The geometry guards, terminal short-ladder consumers,
long-guard fixture and documentation guards pass after their bounded repairs.
The earlier [150/166](../captures/current/hd-completion-refresh-observation-20260905-195856.json)
and [161/166](../captures/current/hd-completion-refresh-observation-20260905-203422.json)
observations remain preserved diagnostics. Repository checks do not reclassify
the failed runtime traces or reopen resolved battle/right-bottom evidence.

## What remains before a complete HD release

Completion requires a reproducible release candidate that implements the
intended map, layout, castle, battle, and input behavior; evidence for each
advertised supported resolution; representative state transitions and endurance;
and an explicit promotion decision. Passing the aggregate's checks alone does
not establish those claims. The
[endurance release evaluator](../tools/hd_endurance_release_checklist.py) now
separates its finite `release_horizon_ready` result from `full_game_complete`,
which remains false. Its checklist does not cover every resolution, combined
patch configuration, or gameplay route.

The protected default remains exactly:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch
```

Keep new patch work in a validation stage, verify the known input SHA and old
bytes, and build outside the repository. Never overwrite
`C:\Clash\clash95.exe`. Neither this audit nor a passing report authorizes
promotion, fabricated approval, or reuse of evidence for a different candidate.

## Evidence gaps

- **Endurance:** the [current short status](../captures/current/hd-soak-short-step-status-current.md)
  records **5/5** after passing 600-second map-idle and map-pan runs on September
  5. Both used stable SHA `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`,
  recorded 41 surface/process samples, and verified cleanup. The remaining
  7,200-second routes need proof. The first
  thirty-minute attempt recorded 119 surface/process samples and clean process
  termination, but one pan interval was 639 ticks rather than the required 640.
  The [clock diagnostic](../captures/current/hidden-soak-pan-clock-diagnostic-current.json)
  identifies separate scheduling/logging clock reads in the probe. The parser
  remains strict and the old result remains failed. The corrected thirty-minute
  run passed with 119 samples, 179 pan events, and clean termination. The first
  2h map-idle run recorded 239 surface/process samples, 383 heartbeats, and an
  exact 460800-tick `SOAK_ROUTE_END`, with no observed AV. Cleanup sorted PIDs
  numerically and waited five seconds on game 1336 before stopping debugger
  34356. Both exact PIDs were later absent, but the timeout remains an error;
  `clean_stop=false` keeps the source report and shared guard failed. Preserve
  those failed reports and raw artifacts unchanged. The
  [debugger-first cleanup fix](../scripts/cdb/run_hidden_soak.ps1) passes
  [six focused tests](../tools/test_hidden_soak_cleanup.py) using mocked process
  objects, including a regression that reproduces the old ordering failure.
  The separate [120-second runtime regression](../captures/current/hd-soak-cleanup-regression-20260905-cdbfirst-01-map-idle.json)
  and [guard](../captures/current/hd-soak-cleanup-regression-20260905-cdbfirst-01-map-idle-guard.json)
  passed at 12:06:11Z with 13 surface/process samples, both processes stopped,
  and no cleanup errors. The second long idle run,
  `hidden-soak-20260905-141501-448-map-idle`, has no completion evidence.
  The [17:41:01Z observation](../captures/current/hd-soak-long2h-map-idle-interrupted-20260905-141501.json)
  records session `36110` unavailable, the recorded candidate and CDB absent,
  no `SOAK_ROUTE_END`, and no final report, guard, or sample manifest. The last
  heartbeat has `tickdelta=419791`; the interruption's cause is unverified.
  Preserve its raw directory and do not manufacture the planned
  `hd-soak-long2h-map-idle-cdbfirst-20260905-141200` report/guard outputs.
  Do not overwrite the successful ladder or failed old long reports, or treat
  the short regression as 2h proof. Read the
  [release checklist](../captures/current/hd-endurance-release-checklist-current.md)
  for its separately scoped requirements. Hidden runs must retain
  `environment=hidden_cdb_host` and `input_responsiveness=not_applicable_hidden`.
- **Visible/input behavior:** the visible map route has an unresolved
  missing-window outcome. The [manual checklist](../captures/current/manual-directinput-validation-checklist-current.md)
  still lacks all five targets: stable menu, stable map, right-bottom input,
  castle overview, and barracks. The
  [HD-layout decision](../captures/current/hd-layout-promotion-decision-current.md)
  additionally lacks an aligned relocated-panel command and observed callback
  on its candidate. An old failed injection attempt does not establish that
  the patch itself is defective. Validate final composition with tear checks.
- **Resolved work stays resolved:** the July 14 right-bottom fixture decision
  and July 17 battle click-to-callback proof are accepted existing evidence.
  Do not reopen them as missing proofs. They do not establish manual input,
  a combined release candidate, or stable promotion.
- **Continuity coverage is bounded:** the
  [existing proof](../captures/current/hd-continuity-proof-current.json)
  covers a stable-SHA save roundtrip, one forced player advance, and a
  610-second route ending at player 3. The
  [campaign probe:10](../probes/cdb/continuity/clash95_continuity_campaign_route_extra.cdb#L10)
  caps advances after a fourth-call timeout (recorded run `20260714-075917`).
  Source inspection shows five player slots and a DirectInput polling loop;
  that timeout alone does not establish a DirectDraw wait or the exact native
  route. The new [day diagnostic](../docs/hd/CONTINUITY_DAY_DIAGNOSTIC.md)
  directly observed the release wait in v4. The approved v5 control then
  reached native day `1→2`, the call return, and a post-day surface after one
  left and one right query override. Its
  [strict recheck](../captures/current/continuity-day-v5-control-recheck-current.json)
  still fails on an overlapping input call; no passing continuity claim is
  made. The separately [approved v6 run](../captures/current/continuity-day-v6-control-approval-current.json)
  `20260905-135344` finished with an outer surface pass, 166 verified patch
  records, and both recorded processes stopped. Its
  [strict report](../captures/current/continuity-day-v6-control-current.json),
  generated at 11:56:45Z, remains failed on a duplicate mouse `GetDeviceState`
  return at line 265 during advance 2. Native day `1→2`, the exact fourth-call
  return, later trace closure, and the post-day surface were observed with one
  left and one right query override and no banner override. Preserve that
  failure without deduplicating the trace or inferring manual input. The
  v7 producer and parser now pass 20 and 33 focused tests respectively,
  recording OS thread, EIP and ESP to distinguish interleaving from repeated
  breakpoint events while preserving strict call/return matching. Its
  [private control preparation](../captures/current/partialtiles-and-v7-preparation-current.json)
  was ready but unexecuted at the 12:24Z checkpoint. The
  [hidden soak:30](../probes/cdb/soak/clash95_hidden_soak_route_extra.cdb#L30)
  holds the same turn. The accepted evidence still lacks a fully passing day
  diagnostic, sustained multi-day play, or visible campaign play. Preserve the
  existing proof while adding the missing coverage; do not
  classify the timeout as a live-game defect without matching evidence.

## Concrete implementation blockers

The [initial paint implementation](../docs/hd/INITIAL_MAP_PAINT.md) is now
implemented and has [bounded hidden passes](../captures/current/initial-map-paint-runtime-current.json)
at 800x600 (`20260905-210832`) and 1024x768 (`20260905-211004`). The separate
`-combinedui-partialtiles-initialpaint-validation` candidates have SHAs
`e72a57fd3bb26509179e0b4360fc9134bef804e152ac338fcd755cdfa41c548f` and
`5ebbaf23ad999a97209a5e0ca8883e8d42e31190fb3891f03cfc3c38001bc338`,
respectively. Each run passes loaded-byte, partial-status and initial-trace
gates: 140 events, one initial full convergence/presentation pair, 49
incremental calls and 37 matched native offscreen no-op exits. Each of the
two four-update software captures passes a source-bound **6/6 action-cell**
audit, with no observed AV or timeout. The 800x600 cleanup receipt records
absence of the observed game/CDB PIDs. The 1024x768 receipt establishes only
exact candidate-path and matching-debugger absence after terminal return;
no live PIDs were captured, so it is weaker provenance.

**Full-frame composition is still incomplete in those software PNGs.** The
[source-asset audit](../captures/current/initialpaint-frame-asset-audit-current.json)
confirms that top **and left** bands exactly match native `FRAME.S32` pixels
and the implemented extension recipe at both new resolutions. The 1024x768
left band continues through Y=767, not merely Y=600. The translated right-middle
strip matches 0/7,488 art pixels in either image; bottom-middle nonblack artwork
matches 2/9,208 at 800x600 and 0/9,208 at 1024x768, with no matching row. The
current restore hook only extends top/left; the current
terrain, minimap and action-bar layout occupies the proposed right/bottom
frame bands. This requires coordinated geometry and composition work, not
only copying artwork over live terrain or controls. The native frame drawer
targets both the software backbuffer and primary target, so the missing
software frame is distinct from separately composed HUD omissions; this is
not a claim that fog/unexplored terrain is defective. The
[four-sided frame contract](../docs/hd/FOUR_SIDED_FRAME.md) documents the native
artwork, reserved geometry and input changes required by a separate validation
stage; its prospective tiling oracle is distinct from the installed top/left
recipe. The six-cell action-bar
pass does not validate the frame. Initial paint is no longer an unimplemented prerequisite,
but complete frame/terrain coverage, other scroll positions and world edges,
modal/army owners, visible composition, input and candidate-bound endurance
still require implementation or matching evidence. The bounded passes do not
establish a release decision or explain the older duplicate-output failures.

The earlier v4b action-bar audits at [800x600](../captures/current/partialtiles-noop-v4-800-action-bar-audit-current.json)
and [1024x768](../captures/current/partialtiles-noop-v4-1024-action-bar-audit-current.json)
each pass **6/6 complete cells** with exact source-pixel matches. Both runtimes
still fail trace integrity and provide no full convergence/presentation pair.
Each diagnostic PNG was converted separately from the observed raw surface with
the recorded palette; its summary retains `Passed=false` and the original
failed summary SHA. This is software-pixel progress on the distinct partial-tile
candidate, not full hidden/visible, input or promotion proof.

The [19:23:55Z screenshot inventory](../captures/current/action-bar-complete-screenshot-inventory-current.json)
covers **10 current PNGs: four action-bar pixel passes and six older failures**.
Two passes belong to the bounded initial-paint runtime passes; the other two
are v4b diagnostic PNGs whose runtime traces remain failed. The separate
[saved-soak audit](../captures/current/soak-action-bar-audit-current.json)
covers **12 failing PNGs**, making **22 checks and 18 action-bar failures**
in total. The previous 20-image inventory is preserved at the archive path
linked by the current inventory. Neither set of pixel passes changes an older
failure, either failed v4b runtime result or the missing full-frame finding.

The earlier [six-screenshot action-bar audit](../captures/current/action-bar-screenshot-audit-current.md)
still finds 0/6 complete cells in each of five 800x600 captures, and only the lower
three cells complete at 1024x768. The authenticated native initialization
`0040A400` draws list `00511D40` through `00419D80`, then calls full terrain
redraw `00418700`. Expanded full tiles overwrite the relocated action-bar area:
at 800x600 they reach Y=591 and cover both rows; at 1024x768 they reach Y=719
and intersect the upper row. This explains why successful draw-coordinate
markers do not establish surviving software composition. It does not reopen
the historical right-bottom decision or establish final visible-wrapper behavior.

The [composition recipe](../docs/hd/PARTIAL_TILE_RENDERING.md) and isolated
PE/hook builder now provide the distinct stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-validation`.
It redraws the admitted map panel after terrain and keeps source-bound
convergence/presentation status per native stack frame. The
[first hidden run](../captures/current/partialtiles-800-pre-hd-failure-current.json),
`20260905-142409`, failed during native pre-HD initialization: candidate SHA
`B273C16822843D8AA684191E4C2F357E2F7C581BBC3AD7F4175C8D6B057ECAE8`
was requested at 800x600, but the diagnostic observed 640x480, owner
`004617A0`, and convergence status 0. No AV or screenshot was produced; both
recorded processes stopped. This is guarded native fallback with premature
diagnostic readiness, not requested-resolution rendering evidence.
The probe now keeps status breakpoints disabled until authenticated native
join `0040B88A` observes owner `0040AD40` and exact requested dimensions.
The final v4b checkpoint passes the [builder's 16 fixtures](../tools/test_build_partial_tile_candidate.py) and
[harness's nine fixtures, covering 199 log cases](../tools/test_partial_tile_surface_harness.py),
including one exact `PTILE_MAP_READY` after the loaded contract and before all
statuses, and rejection of missing, repeated, mismatched or contaminated
readiness. The subsequent [v2 run `20260905-195041`](../captures/current/partialtiles-latearm-v2-800-failure-20260905-195041.json)
reached valid 800x600 map readiness on the same candidate, then emitted four
incremental status-1 returns and status 0. Strict rejection ended the run
before a full convergence/presentation pair, with no PNG and no observed AV.
Matching processes were absent afterward; live PIDs were not captured, so
this is not exact-PID cleanup evidence. Status 0 can originate from an
offscreen notification, but this log lacks saved world X/Y and cannot resolve
its cause. The [v3 run `20260905-195807`](../captures/current/partialtiles-inputdiag-v3-800-failure-20260905-195807.json)
records rejected world `(90,7)` with map `(100,100)` and scroll `(10,17)`,
outside the ceiling viewport. It remains **FAIL**: no composition-guard return,
native no-op exit, full convergence/presentation pair or PNG was observed.
There was no observed AV, and recorded CDB PID 32676 and game PID 42256 were
absent at the terminal observation. Preserve all three failed runs unchanged.

The final observation protocol matches guard, input, status and native exit
by actual thread, normalized stack, caller, world cell and context. Only a
strictly offscreen in-world notification with the exact normal-map context
and matching native exit may count as a no-op; it earns no draw or present
credit. Visible partial cells still require drawing, and full convergence and
presentation remain mandatory. Candidate bytes are unchanged. The
[immutable v4b plan](../captures/current/partialtiles-noop-v4b-run-plan-current.json)
pins source/fixture/probe hashes and both candidate identities. The 800x600
[run `20260905-201619`](../captures/current/partialtiles-noop-v4-800-observation-current.json) ended with exit 1 and the strict error `incremental input
or native exit lacks its guard and invocation`. It recorded 327 inputs,
327 incremental statuses, 244 native exits and 326 guards, with repeated/
unmatched events and a pending guard at host stop. There were zero full
convergence/presentation markers; the base `SURFDUMP_REDRAW` at `00406FA0`
observes simulation, not the full redraw hook. An 800x600 raw surface was
captured with no observed AV or timeout. Recorded CDB PID 42988 and game
PID 38892 were absent at **18:21:27Z**. The separate 6/6 pixel audit does not
change the failed runtime summary. Preserve every raw event and the failed
summary unchanged. The [1024x768 run `20260905-202225`](../captures/current/partialtiles-noop-v4-1024-observation-current.json)
ended with exit 1 on repeated or out-of-order incremental input. It recorded
361 inputs, 361 incremental statuses, 359 guards and 266 native exits, but zero full
convergence/presentation markers. A 1024x768 raw surface was captured without
AV or timeout; recorded CDB PID 28444 and game PID 35832 were absent at
**18:25:10Z**. Its separate 6/6 pixel pass preserves the failed runtime summary
and every raw trace event. Every new
screenshot needs the exact source-pixel bar audit; unsupported owners, visible
composition, manual input and promotion remain separate requirements.

| Area | Inspected behavior | Required change |
| --- | --- | --- |
| Promotion state | [Battle matrix:603](../tools/battle_ui_evidence_matrix.py#L603) hardcodes `validation_stage_only`, which the [release evaluator:374](../tools/hd_endurance_release_checklist.py#L374) rejects. [HD-layout decision:312](../tools/hd_layout_promotion_decision.py#L312) requires pending manual proof and exactly 0/5; [line 284](../tools/hd_layout_promotion_decision.py#L284) requires callback proof to remain false. | Preserve historical observations, but add a separate evidence-backed path that can evaluate genuine completed input and promotion decisions. Do not replace constants merely to obtain green checks. |
| Release integration | The new [combined UI validation stage](../docs/hd/COMBINED_UI_VALIDATION.md) selects 27 groups/166 unchanged patch records with no byte-span overlaps. Isolated candidate SHA `0A75CF35F42EFE1E44FBA1AC4031EAAE5323CDFF51AA19D261C36C5BB84691C2` passes its byte gate at 800x600. The [2026-09-05 run `124215`](../captures/current/combinedui-layout-geometry-hidden-current.json) additionally passes hidden forced geometry: six relocated panel draws, hit-scan anchors, last-descriptor redraw clipping, and a balanced synthetic return. The [earlier run `122508`](../captures/current/combinedui-layout-hidden-current.json) remains failed for missing hit-scan/redraw observations. | Verify transitions, real input, visible composition, partial-tile terrain, and endurance on the exact candidate before considering promotion. Forced geometry provides no click callback, manual input, visible composition, or promotion proof. Separate-candidate passes and disjoint patch bytes do not prove combined runtime behavior. |
| Promotion orchestration | [complete_hd_promotion.py](../tools/complete_hd_promotion.py) now requires fresh affirmative component artifacts, exact proof binding and per-target candidate identity, and stops after failures. It separates component eligibility from whole-HD readiness and refuses release-box mutation. | Implement the missing complete acceptance path for layout, endurance, continuity, combined candidate, supported resolutions, and explicit promotion. Component success alone remains insufficient. |
| Larger resolutions | [Resolution manifest](../src/launcher/resolutions.json) leaves 1024x768, 1280x720, 1280x960, and 1920x1080 experimental. The [hidden diagnostics](../captures/current/combinedui-hidden-validation-current.md) pass full-tile dimensions and explained visibility at 800x600 and 1024x768 with animation fast-forward, retaining native-startup timeout and whole-routine-bypass AV failures. [Renderer fixtures](../tools/test_render_cdb_surface_probe.py) cover resolution-specific stride, visibility bounds, menu/load coordinates, and host dimensions. | Implement and validate safe partial-edge rendering, native startup, composition, input, and the remaining resolution lanes. Full-tile checks and five-second post-dump observation do not prove complete viewport coverage or final visible output. Larger custom/extra UI probes still need separate recipes. |
| Resolution acceptance | The combined frame-restoration recipe now tiles and clips native artwork; [isolated builds](../captures/current/combinedui-resolution-build-current.md) pass 166 byte records at all four advertised larger presets and a partial-tile custom size. The [manifest evidence guard](../tools/resolution_manifest_guard.py) binds dimensions, stage, candidate identity, run references, and patch counts across source metadata and smoke evidence. | Produce matching runtime, composition, input, and continuity evidence for each supported resolution. Presets remain experimental; archived 800x600 proof cannot satisfy a larger entry. |

## Ordered next work

The immediate rendering frontier is the source-confirmed missing bottom/right
frame in the initial-paint captures. Coordinate reserved-frame geometry with
terrain, controls, minimap and input, then validate any repair against the
complete frame as well as all six action cells; retain
the existing bounded runtime passes and historical failures as separate claims.

1. All five short hidden rungs and the separate 120-second cleanup regression
   pass. Repair the three planning consumers that mishandle the completed
   short ladder, and refresh their evidence after focused checks.
   Preserve the interrupted second idle attempt and obtain complete new
   two-hour idle and pan evidence; stop on real failures
   and preserve diagnostics. Do not overwrite the prior visible failure claim.
2. Prepare the missing input/composition and visible-transition cases. Obtain
   fresh explicit approval before visible runtime, focus/cursor manipulation,
   input injection, or live capture. Record real observations for the five
   manual targets and relocated panel; automated callbacks do not silently
   become manual DirectInput proof.
3. Add genuine completion paths to promotion evaluators. The combined
   validation candidate already has a passing byte gate; validate affected
   routes on that exact candidate,
   including save/load and day transition. Keep historical evidence distinct.
4. Complete the per-resolution lanes documented in
   [LAUNCHER.md](../docs/hd/LAUNCHER.md): 1024x768 first, then 1920x1080, then
   remaining advertised presets. Keep unsupported presets/custom sizes honestly
   experimental until their evidence passes.
5. Assemble a current acceptance matrix for the actual release candidate and
   supported configurations, obtain the explicit promotion decision, and update
   launcher status and release documentation accordingly. Preserve source-only
   distribution: no proprietary binaries, wrapper DLLs, saves, or raw dumps.

The user's recorded “Approve debugger runs” authorization covers necessary
hidden debugger validation for this active task. It does not authorize visible
runtime, OS input injection, manual proof or promotion.

The active objective remains open until the intended HD behavior and these
release claims are supported. Neither an audit document nor `165/165` is its
completion criterion.

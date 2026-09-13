# Clash95 HD: current agent handoff

This is the tracked starting point for Astra and other coding agents. Read the
root [AGENTS.md](../../AGENTS.md) and
[WORKING_WITH_THIS_REPO.md](WORKING_WITH_THIS_REPO.md) first; they define the
operating rules. Then read [FINISH_LINE_RUNBOOK.md](FINISH_LINE_RUNBOOK.md) for
the remaining validation work and the task-specific sources below. Search the
large progress log and patch notes when a question needs their history.

Ignored `.codex-loop/` notes are local scratch state, not the default handoff.
[AUTONOMOUS_HD_MOD_CODEX_PROMPT.md](AUTONOMOUS_HD_MOD_CODEX_PROMPT.md) is an
archived WSL/SDL exploration prompt; do not apply its old architecture, paths,
automatic Git operations, or runtime instructions to current work.

## Astra configuration

The shared [.codex/config.toml](../../.codex/config.toml) sets only
`model = "gpt-6-astra"`. Reasoning effort inherits the user's configuration
(the preparing workstation used `ultra`); no global settings, permissions,
providers, hooks, or credentials belong in this file.

Codex loads project configuration only for trusted projects. Explicit CLI
model/config overrides take precedence over the project default; project
configuration takes precedence over user defaults. An existing task may retain
its explicit model selection, so check the model selector when continuing it.
See [official Codex configuration guidance](https://learn.chatgpt.com/docs/config-file/config-basic).
This file supplies a default, not account access to a model. Do not change
global trust or permission settings as part of routine repository preparation.

## Start safely

Run commands from the repository root. Inspect `git status --short` before
editing; preserve existing modified and untracked files. Do not reset, clean,
stash, delete captures, or overwrite another task's changes to obtain a clean
tree. Follow the root guide's frequent Git checkpoint workflow: commit verified
work, merge into `main` when needed, and push its configured upstream. Keep
unfinished work outside checkpoints and honor explicit user requests to pause
Git publication.

Discover a Python interpreter instead of assuming a bare command works:

```powershell
$clashPythonCommand = Get-Command python,python3,py -CommandType Application -ErrorAction SilentlyContinue |
    Where-Object { $_.Source -notlike (Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\*') } |
    Select-Object -First 1
if ($clashPythonCommand) {
    $clashPython = $clashPythonCommand.Source
} else {
    $clashPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
}
if (-not (Test-Path -LiteralPath $clashPython)) {
    throw 'Locate an installed Python interpreter or ask Codex for its bundled workspace runtime path.'
}
& $clashPython -B -c "import sys; print(sys.executable); print(sys.version)"
```

This skips WindowsApps aliases that could open the Store. If discovery fails,
use an installed interpreter's explicit path. The bundled fallback was verified with
Python 3.12.14 on 2026-09-05; other hosts may place it elsewhere. Codex's
workspace-dependency lookup can locate the current bundled runtime. No API key
or game installation is needed for the documentation fixtures.

Inspect the saved evidence before regenerating it:

```powershell
& $clashPython -B -c "import json; from pathlib import Path; d=json.loads(Path('captures/current/current-evidence-refresh-current.json').read_text(encoding='utf-8')); print(d['generated_at']); print([k for k,v in d['checks'].items() if not v.get('passed')])"
```

For onboarding/guard changes, run the focused fixtures:

```powershell
& $clashPython -B tools/test_handoff_freshness_guard.py
& $clashPython -B tools/test_docs_consistency_guard.py
```

The aggregate refresh is an explicit evidence-writing step, not a read-only
startup command:

```powershell
& $clashPython -B tools/current_evidence_refresh.py
```

It regenerates reports under `captures/current`; review their changes and
report honest failures. Some checks need existing local artifacts or tools,
so a fresh clone is not a complete runtime evidence environment. Individual
guard CLIs also write current reports by default; use both `--write-json` and
`--write-markdown` to redirect diagnostic output to a temporary directory.

## Evidence snapshot and active work

### Complete candidate integration — 2026-09-08

The active candidate is the protected stable stage plus
`-completehd-validation`, recipe `complete_hd_v1`. The protected stable stage
and Classic launcher default at 800x600 remain unchanged. Complete HD is
experimental at every resolution. Native 640x480 menus, castles and battles
remain centered; the widened-battle experiment is excluded.

The separate 1280x720 `-castlecenter-all-battlehd` validation stage now has
an expanded 17x7-capacity battlefield and native right sidebar. Its candidate,
forced hidden diagnostics, unresolved cursor polling, and pending visible/input
acceptance are recorded in
[`battle_hd_1280_validation.md`](../../reports/battle_hd_1280_validation.md)
and [`battle-hd-validation-current.md`](../../captures/current/battle-hd-validation-current.md).
This lane is independent of the Complete HD recipe and does not promote either
candidate. Its source-binding integration report preserves the original
foundation manifest while documenting the reviewed updated producer hashes.

### Implemented and checked

The reviewed combined/framed/minimap/native-modal/army dependency chain is in
main, with exact source provenance in `reports/hd-foundation-import-manifest.json`.
The shared builder emits deterministic external candidate/manifest/probe
bundles. All six fixture resolutions, including 802x602, passed in-memory
construction; repeated 800x600/1024x768/1920x1080 results matched. The nine
modal/army suites passed 78 tests. See `COMPLETE_HD_CANDIDATE.md` and
`HD_FOUNDATION_IMPORT.md` for scope and historical compatibility.

The launcher consumes that builder through an experimental Complete HD profile.
Its original Classic/800x600 default and explicit Play/double-flag confirmation
remain. The visible diagnostic harness uses measured geometry and pulse input;
its separate human observation path never labels injected input as manual proof.

Whole-release evaluation reconstructs candidate bytes and requires trusted
lane verifiers. A report's own passing flags cannot establish eligibility.
Missing verifier implementations and actual evidence remain incomplete.

### First integrated runtime result

`captures/current/completehd-initial-800x600-20260908.json` binds the first hidden
run and its unchanged raw artifacts. Candidate
`e785d202140942959b973f462a9eded27531fd12c5668fac40af61248e875a84`
reached the map and yielded a 480,000-byte paused surface with observed minimap
state. It **failed** initial trace validation: line 520 repeats full convergence
before matching presentation. Event-output integrity passed, but that does not
prove native call completion. Do not remove repeated records or turn this run
into a rendering pass.

The run had no access violation or timeout; exact task-owned process cleanup
passed. Original executable, live saves and isolated saves were unchanged.
The diagnostic PNG is a single hidden software capture, not a stable pair or
final visible-color proof. All four borders and six action cells were visually
inspected, but blank terrain and full rendering acceptance remain unproven.

Prepared bundles for 800x600, 1024x768 and 1920x1080 are under
`C:/ClashTests/completehd-validation-20260908/prepared-<resolution>/`.
The 1080p candidate is
`95ba0c965d019d0b1c5fb45726e938bf0b1b22ce6fc8353375409477e94a90d0`.
The initial run plan records producer hashes; later producer edits require a
new immutable run plan. Its unexecuted 1024/1080 entries are not evidence.

A separate full-progress diagnostic retained in
`captures/current/completehd-full-progress-800x600-20260908.json` passed its
strict native trace and produced three identical paused captures. The prior
duplicate did not recur and remains unexplained. Image coverage still failed
on 82 blank cells; no overall rendering acceptance is claimed. Its preceding
uppercase-SHA preparation failure happened before debugger launch and is also
preserved. See `FULL_PAINT_PROGRESS_DIAGNOSTIC.md`.

### Guarded gameplay checkpoint — 2026-09-08

`captures/current/completehd-guarded-gameplay-20260908.json` records separate
source-verified evaluations of the retained complete-v1 1024x768 and 1920x1080
captures. Both pass this bounded software-rendering evaluation: respectively
123 and 377 measured blank cells match the same paused native visibility-zero
observations, with no unexplained blanks. All four frame bands, the footer and
six action cells match source artwork; each run has three identical captures.
The evaluator reconstructs the entire normal debugger script and the additive
minimap observer, keeping the canonical candidate probe distinct from the
composed runtime script. Rehashing a modified script cannot authorize it.

The original summaries still fail coverage postprocessing with exit 2; they
and every earlier failed evaluation remain unchanged. The separate 800x600
progress analysis explains its 82 blank cells from paused native visibility
but remains diagnostic-only. Neither result resolves the first run's duplicate
trace event or establishes scrolling, far-world clearing, visible composition,
manual input, continuity, endurance or release eligibility. The checkpoint
pins exact producer/evaluator source snapshots for replay after upstream source
changes; do not substitute current-source manifests for those original runs.

### Remaining work

Diagnose repeated native observations with additional progress/call-identity
probes. Preserve all original failures. Validate scrolling, minimap erasure,
partial/full painting, clamps and out-of-world clearing separately.

Historical barracks evidence demonstrates twelve late 32x64 rectangles missing from the
physical mirror after native slot draws. The separate
[modal-slot adapter and validation builder](FRAMED_MODAL_SLOTS_DIAGNOSIS.md)
now target `-completehd-modalslots-validation`. Source-bound synthetic fixtures
cover the inclusive 33x65 dirty copy and ABI; complete-HD v1 remains unchanged.
The [new hidden barracks consumer](MODAL_SLOTS_BARRACKS_CAPTURE.md) authenticates
the exact slots bundle, twelve dirty-copy events, three native/physical captures
and retained-handle cleanup. Its first run is preserved in
`captures/current/modal-slots-barracks-failure-20260908.json`: initial-map and
twelve slot-copy traces passed, but a startup-record parser defect stopped
capture. The legitimate `protocol=slots_barracks_owned_canvas_v1` field was
mistaken for an additional SLOTS record. The narrow parser repair passes all
13 offline fixtures; the original failed run still has no pixels.

The [2026-09-13 1024x768 checkpoint](../../captures/current/modal-slots-barracks-1024x768-20260913.json)
records a fresh run of candidate
`8148cfeacf893e4b006ae5b09c71612e5ac0841f491397ca2c844c9397888515`.
Its disclosed `construct_all` native barracks route passed the initial/modal
traces and retained-handle cleanup, with three identical paused native/physical
capture pairs. Each centered 640x480 comparison has zero mismatches; all four
outer margins are zero, and all twelve slot interiors have 2,048 matching
nonzero native pixels each. Original executable, all 15 live-save files, four
isolated-save files and the 38 snapshotted producer sources remain unchanged.

The independent audit nevertheless **fails** on all 24 state/header paths:
the host emitted `surface.-before-state.raw` and related names, while the
validator requires `surface-before-state.raw` and corresponding names. Preserve
that audit and the successful host summary separately; these pixel observations
do not grant complete independent acceptance. Do not rename captures or broaden
the verifier to erase the mismatch. The checkpoint binds both verdicts and all
raw/PNG/probe/plan/source artifacts. Complete-HD v1 is unchanged; this is bounded
hidden mirror evidence from the separate slots stage, without primary, visible,
manual-input or native-exit proof. The writer now constructs the basename
explicitly. All 14 offline fixtures pass, including a real snapshot/triplet
function test that reproduces the old extra-dot failure and checks all 24
required paths. A new run is required; the C audit remains failed.
Native primary destination
misplacement remains a static inference until
primary-surface evidence is captured. Court, recruitment, peasants,
ownership/exit restoration and destruction still require complete routes.

Ordinary army selection/movement, all portraits, map redraw/scroll/reselection,
centered battle entry/command/outcome/return and healthy map transitions remain
incomplete on the final candidate. Earlier controlled 1024x768 and historical
battle callback evidence does not establish these claims.

Fresh approved visible/manual evidence, the five human input targets, complete
continuity, the final candidate's short ladder and both separate two-hour soaks
remain outstanding. There is no release eligibility report or promotion
decision. Preserve existing unfinished work in every checkout.

### Earlier component and diagnostic evidence

The [six-resolution framed-map matrix](../../captures/current/framed-map-resolution-matrix-current.md),
recorded **2026-09-06T02:52:50Z**, contains **two bounded hidden runtime
passes**: 1024x768 and custom 802x602. All six actual software screenshots
exactly match **all four frame bands, the footer and all six action-bar
cells**, in the distinct
`-combinedui-partialtiles-initialpaint-framed-validation` stage. The
[matrix manifest](../../captures/current/framed-map-resolution-matrix-current.json)
binds the six outcomes, source plans, candidate hashes and original artifacts.
The [first two observations](../../captures/current/framed-map-runtime-current.md)
retain the detailed 800/1024 evidence. The 1024 candidate SHA is
`3e9969a1e9285a9e65290072ea89cb2a3f224bd118ef267794fd1028ac5d7053`
(run `043513`); the 800 SHA is
`7fad16f167205fb34ecbc99a6a1ff6180c710807f99b19f25efb48a8b1c8d15b`
(run `043323`). All 25 source pins match the immutable run plan, with actual
candidate, build, loaded-contract and probe bindings recorded in the
[manifest](../../captures/current/framed-map-runtime-current.json).

The 1024 trace passes with 140 events, one full convergence/presentation pair,
49 incremental inputs and 37 matched native no-op exits. The 800 trace has a
duplicate native exit at events 81/82 with no fresh guard/invocation and remains
failed. Its separate diagnostic summary preserves the failed original summary
and only converts the already captured raw pixels. The source-bound
[800 frame](../../captures/current/framed-v1-800-frame-audit-20260906.json),
[1024 frame](../../captures/current/framed-v1-1024-frame-audit-20260906.json) and
[action-bar](../../captures/current/framed-v1-action-bar-audit-20260906.json)
audits preserve this distinction. Neither run reports an AV or timeout. At
2026-09-06T02:39:37.7159976Z, `Get-Process` confirmed the recorded CDB/game
PIDs 14244/39120 and 33104/31664 all absent.

The additional 1280x720, 1280x960 and 1920x1080 runs pass their initial-paint
traces but remain **runtime FAIL**: the image gameplay heuristic returned
`low_overall_gameplay_coverage`, aborting before a final summary. Their logs,
coverage reports and separately labeled diagnostic summaries remain preserved.
The custom 802x602 run has an original passing final summary. A source-bound
fog/coverage decision is being developed separately; it has not reclassified
the three failed runs. Additional runs lack recorded live PIDs; the matrix
discloses only the coordinator's later exact-candidate/matching-CDB absence
observation, rather than inventing PID receipts.

The [minimap viewport correction](MINIMAP_VIEWPORT.md) now has a separate
[six-resolution matrix](../../captures/current/framed-minimap-runtime-current.md)
on 2026-09-06: **all six outline, frame, footer and action-bar pixel audits
pass; runtime passes only at 800x600, 1024x768 and 802x602**. Both 1280 cases
retain coverage exit-2 failures and missing final summaries; 1920x1080 retains
its strict trace failure. The optional `--minimap-viewport` revision replaces
the active `0040D560` path's old 9x7 outline after backing repair, without
changing stable selection or prior default framed bytes. The
[manifest](../../captures/current/framed-minimap-runtime-current.json) binds
all candidate hashes and original outcomes. Its 1024 candidate
`69899e07f70dde2094264be694300e00c7a778f1391ac7797b74c59c56ee1ce0`
has outline `(804,56)..(835,80)`, with all 110 perimeter pixels at index `4C`.
Five recorded CDB/game pairs have later absence receipts; the 802 late query
contains no live pair and supplies no exact-PID cleanup proof for that static run.

A [saved-capture visibility diagnostic](../../captures/current/framed-minimap-1280-visibility-diagnostic-20260906.json)
binds the exact optional-minimap 1280 candidates and their contiguous native
visibility dumps: all 100 image-flagged blank active cells at 1280x720 and all
176 at 1280x960 have zero visibility bits. This supports a fog explanation for
those pixels, but does not prove individual clear calls or complete terrain
rendering. Their low-overall-coverage warnings and missing final summaries
remain failed; no threshold, parser, candidate or runtime verdict changed.

The separate [controlled-scroll checkpoint](../../captures/current/framed-minimap-scroll-runtime-current.md)
records three additional approved hidden runs on 2026-09-06. Actual 1024x768
scroll `(0,17)` -> `(11,17)` and 802x602 `(0,17)` -> native far-world clamp
`(89,92)` pass callback/trace, outline geometry and old-outline erasure.
All 90 and 88 informative old-only pixels, respectively, are repaired, and all
first four actual screenshots pass every frame edge, the footer and all six
action cells. A third run moves one tile vertically from `(0,17)` to `(0,18)`
at 1024x768; all 64 old-only border pixels are repaired and both captures pass
the same frame/footer/bar audits. All three owned CDB/game pairs have
retained-handle cleanup receipts in the
[manifest](../../captures/current/framed-minimap-scroll-runtime-current.json).
The far-corner software map capture is black; this rectangle/erasure result
does not prove unseen terrain contents. See [MINIMAP_SCROLL_VALIDATION.md](MINIMAP_SCROLL_VALIDATION.md)
for exact scope. Scale-4 runtime, no-op cases, natural
input and final visible composition remain pending. These new passes do not
repair the older resolution failures or authorize promotion.

The requested castle overview, every callable castle building, and battle
screens are inventoried in [FRAMED_SCREEN_VALIDATION.md](FRAMED_SCREEN_VALIDATION.md):
nine castle views plus battle initial, command and outcome-route discovery
across the same six resolutions. The separate hidden modal lane now has a
[four-attempt checkpoint](../../captures/current/framed-modal-runtime-current.json):
two failed overview attempts remain preserved; the later 1024x768 overview
and explicitly constructed hospital captures pass their bounded runtime/trace
gates but **fail visual composition**. Their existing PNGs show internal
horizontal corruption; the hospital also retains stale castle content.
Expected margins around the centered native modal and the failed full-window
ordinary-map frame comparison are separate measurements, not automatically
castle defects. The ordinary-map bar is 0/6 and inapplicable to modal controls.
All other routes, artwork variants and resolutions remain pending. Neither
these forced routes nor the older descriptor catalogs prove natural/manual
input, modal controls, final visible composition or promotion.

The [packed-loader diagnosis](FRAMED_MODAL_CANVAS.md) now binds those modal
stripes to native 640-byte artwork being loaded into the HD memory surface.
The separate [modal candidate builder](../../tools/build_framed_modal_candidate.py)
has an [offline preparation checkpoint](../../captures/current/framed-modal-canvas-preparation-20260906.json):
11 emitted-x86, 16 PE-allocation and 7 builder fixture groups pass. It adds a
true owned 640x480 canvas, a centered physical memory mirror and restoration
before the native map redraw in the distinct `-framed-modalcanvas-validation`
stage. The 1024x768/minimap preflight SHA is
`17b48dced0e6e75010df67e93c4feb22ca9545cd380084b9a2c383f2eddf5e1b`.
No repaired modal runtime or visual result is established by that checkpoint;
the old failed screenshots remain failed. The new stage needs its own
source-bound route/mirror protocol; do not reuse the old E0-as-HD capture
contract while E0 is the native canvas. Existing default framed/minimap
candidate bytes and stable selection remain unchanged.

The first new-canvas launch failed before game loading with Windows error 193.
The [loader correction](../../captures/current/framed-modal-canvas-loader-correction-20260906.json)
preserves that failed run and identifies a virtual gap between `.hdmodal` and
`.hdstate`. The corrected `.hdmodal` virtual extent spans its complete 128 KiB
reservation; all other executable bytes are unchanged from that first build.
The corrected 1024x768/minimap SHA is
`c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d`.
The [Windows image-section check](../../captures/current/framed-modal-canvas-sec-image-20260906.json)
accepts this file and still rejects the preserved first candidate. The updated
PE fixture has 18 passing groups, including native image-section admission
for all twelve resolution/minimap variants, without executing game code.
This loader result alone supplies no repaired castle screenshot or lifecycle proof.

The subsequent [owned-canvas runtime checkpoint](../../captures/current/framed-modal-canvas-runtime-current.md)
records six **1024x768 captures with the complete native-artwork protocol**:
overview, hospital, school, workshop, smiths and barracks. All six bounded
runtime traces and capture bindings pass. Exact native-to-physical comparison
passes for the first five; **barracks fails with 24,576 missing slot pixels**.
All 479,232 surrounding pixels remain palette index zero. Ordinary-map
frame/footer and action-bar templates are nongating measurements on these
centered castle screens, not acceptance of their distinct controls.
An earlier hospital attempt under the expanded protocol remains failed before
capture because its initial map trace repeated incremental input/status without
a fresh guard; its hospital sequence passed, but the host refused capture.
The first protocol's missing later-load observations and earlier failed images
remain in the preserved predecessor. No candidate bytes changed for the
expanded observations. The
[manifest](../../captures/current/framed-modal-canvas-runtime-current.json)
binds every outcome, old source snapshots and exact CDB/game cleanup receipts.
Existing assets and the original are unchanged; barracks generated four native
cache files, preserved outside the repository. Peasants has an unexecuted plan;
the 802x602 canvas candidate is built only. Court/recruitment need complete
primary composition evidence; native exit/free and other variants remain pending.

The user next prioritized **tactical battle HD**, explicitly choosing more
visible width with native-size sprites and controls anchored to the edges.
The current battle implementation centers a native 640x480 frame; it is a
baseline, not completion of that wider layout. Preserve the existing arena's
rules and the resolved historical click-to-callback proof. New initial-battle
and cached-primary capture contracts are being developed separately; manual
input, visible composition and promotion retain their approval boundaries.

The user's unit-selection request now has a separate
[1024x768 own-army pass](../../captures/current/framed-army-selection-runtime-current.md),
recorded **2026-09-06T09:12:49.3330283Z**, in the
`-framed-modalcanvas-army-validation` suffix. Candidate `9bc99ba5…508c53b5`
selects army3 through native408030, draws all eight portraits inside the
frame and preserves their entire backing through the full terrain redraw.
All three software captures pass every outer frame band and all six
bottom-right controls. The source-bound trace and retained-process cleanup
pass. See [UNIT_SELECTION_HD.md](UNIT_SELECTION_HD.md) for implementation.

A subsequent [six-transition pass](../../captures/current/framed-army-transitions-runtime-current.md)
at **2026-09-06T09:51:12.5857021Z** uses the same candidate: eight-, four-, two-
and single-squad selection, reselection, and native Map-mode deselection. All
six actual screenshots pass every outer frame band and all six action cells;
unused portrait slots restore their native backing, and both closing states
erase the panel. Strict whole-source/command trace and retained cleanup pass.
These controlled native routines do not prove ordinary map dispatch or manual
input. Incremental redraws, scrolling, other resolutions and
final wrapper composition remain pending; no earlier failure is reclassified.

The [first-portrait toggle pass](../../captures/current/framed-army-portrait-runtime-current.md)
at **2026-09-06T10:20:13.7382740Z** adds two controlled native423860 calls on
the same1024x768 candidate. The first flag changes0→1→0 with actual native
button queries, complete redraw/release/return observations and no movement
route. All three headers and whole source/candidate/commands bind; all frame
edges, six action cells, native badge pixels and seven map-marker masks pass.
The second click restores every original indexed pixel. Retained cleanup
passes. The linked manifest preserves the first parser's startup-order defect
and the failed badge-only hypothesis; map blend colors, other portraits,
ordinary/manual input and actual unit movement remain separate requirements.

The [prior c099 diagnostic](../../captures/current/framed-unit-selection-diagnostic-current.md)
still records the actual overwritten portraits/frame failure and its earlier
bad-breakpoint attempt. Two new handoff-probe failures and a disclosed packet
receipt correction also remain in the new checkpoint. Controlled native
invocation establishes neither manual mouse input nor final visible wrapper
composition. Stable selection is unchanged; this does not reopen the resolved
historical right-bottom design question.

The [four-sided frame contract](FOUR_SIDED_FRAME.md) now documents the integrated
recipe, input wrappers, full/initial paint, presentation and stage-bound
consumers, with separate focused source checks. The current screenshot lane
requires player 0 and every ceiling cell in the world. Failed resolution
gates, the minimap rectangle, far-world captures, modal/army owners, manual
input, final visible composition
and endurance remain separate claims. These results do not reclassify old
failures or alter stable selection and resolved battle/right-bottom decisions.

The earlier [initial map paint implementation](INITIAL_MAP_PAINT.md) has
[bounded hidden passes](../../captures/current/initial-map-paint-runtime-current.json)
on **2026-09-05**, in the distinct
`-combinedui-partialtiles-initialpaint-validation` stage. Runs `210832`
(800x600, SHA `e72a57fd3bb26509179e0b4360fc9134bef804e152ac338fcd755cdfa41c548f`)
and `211004`
(1024x768, SHA `5ebbaf23ad999a97209a5e0ca8883e8d42e31190fb3891f03cfc3c38001bc338`)
each pass the loaded-byte, partial-status and initial-trace gates. Each trace
contains **140 events**, one complete initial convergence/presentation pair,
49 incremental calls and 37 matched native offscreen no-op exits, closing
before the four-update software capture. Both source-bound action-bar audits
pass **6/6 complete cells**, with no observed AV or timeout. The 800x600
receipt records absence of the observed game/CDB PIDs; the 1024x768 receipt
records only exact candidate-path/matching-debugger absence after completion,
because its live query arrived too late to capture PIDs.

**The full frame remains incomplete in these software PNGs.** The
[source-asset audit](../../captures/current/initialpaint-frame-asset-audit-current.json)
confirms exact top **and left** native-artwork pixels at both resolutions,
including the implemented extension tiles. At 1024x768 the left band continues
through Y=767; there is no cutoff at Y=600. The translated right-middle strip
matches 0/7,488 art pixels in either image; the bottom-middle nonblack artwork
matches only 2/9,208 at 800x600 and 0/9,208 at 1024x768, with no matching row.
That earlier restore recipe
extends only top/left, while terrain and controls occupy the prospective
right/bottom frame area. Native frame drawing targets the software map surface
as well as the primary target, so this finding is distinct from omitted
primary-only HUD layers. It does not classify unexplored terrain as a defect.
A passing action-bar audit does not prove frame continuity or final visible
composition. The [four-sided frame contract](FOUR_SIDED_FRAME.md) separates the
old top/left recipe from the integrated complete-frame layout and coordinates
terrain, control, minimap and input boundaries. Broader terrain/scroll
coverage, modal/army owners, input, endurance and promotion remain separate
requirements. These new bounded passes do not repair or reclassify the older
runtime failures and screenshot inventory below; the protected stable stage
and resolved battle/right-bottom decisions remain unchanged.

The historical [four-sided frame preparation](../../captures/current/four-sided-frame-preparation-current.md)
records standalone geometry, a source-pixel oracle and an emitted memory frame
helper: **31 focused tests**, including **903 synthetic x86 executions** at
three addresses. That checkpoint preceded the integrated builder and new
framed runs above. The two earlier initial-paint PNGs still fail the four-band
profile; their existing top/left proof and six-cell action-bar passes remain
separate from the new framed evidence.

Completion work after the preparation added passing **600-second hidden
map-idle and map-pan** runs on 2026-09-05, with the stable candidate SHA and
verified cleanup. The [short-step status](../../captures/current/hd-soak-short-step-status-current.md)
now records **5/5** rungs; both 2h routes still need proof.
The first thirty-minute run ended on **2026-09-05T09:02:15Z** with clean process
termination but a failed 639-versus-640-tick pan interval. Its
[failed report and guard](../../captures/archive/hidden-soak-short30-20260905-103139/README.md)
remain evidence of failure. The probe now latches a single clock sample for
scheduling and logging; the corrected run `hidden-soak-20260905-110757-602-map-pan`
passed at **2026-09-05T09:38:35Z**, with 119 surface/process samples, 179 pan
events, and verified cleanup. The strict pan-interval check remains unchanged.
The first 2h map-idle run, `hidden-soak-20260905-114207-433-map-idle`, started
at **2026-09-05T09:42:12Z** and [failed](../../captures/current/hd-soak-long2h-map-idle-current.json)
at **11:42:50Z** solely on cleanup. It recorded 239 surface/process samples,
383 heartbeats, and `SOAK_ROUTE_END` at exactly 460800 ticks, with no observed
AV. Numeric PID sorting put candidate 1336's five-second exit wait before
debugger 34356; both processes were subsequently absent, but the recorded
timeout keeps `clean_stop=false` and the report and guard failed. Preserve
those failed artifacts unchanged. The runner now preserves debugger-first
order with insertion-order deduplication. Its
[six focused tests](../../tools/test_hidden_soak_cleanup.py) pass with fully
mocked processes. The separate [120-second cleanup regression](../../captures/current/hd-soak-cleanup-regression-20260905-cdbfirst-01-map-idle.json),
run `hidden-soak-20260905-140338-409-map-idle`, and its
[guard](../../captures/current/hd-soak-cleanup-regression-20260905-cdbfirst-01-map-idle-guard.json)
passed at **12:06:11Z** with 13 surface/process samples, both game and debugger
stopped, and no cleanup errors. This verifies the short cleanup path; it does
not replace either 2h requirement. The second 2h map-idle run,
`hidden-soak-20260905-141501-448-map-idle`, is
[interrupted without completion artifacts](../../captures/current/hd-soak-long2h-map-idle-interrupted-20260905-141501.json).
At **2026-09-05T17:41:01Z**, session `36110` was unavailable, the recorded
candidate and CDB were absent, and the log had no `SOAK_ROUTE_END`. Its last
heartbeat recorded `tickdelta=419791`. No final report, guard, or sample
manifest exists; the cause of interruption is unverified. Preserve the raw
directory and the successful ladder and earlier failed long-run artifacts.
Do not synthesize the planned `hd-soak-long2h-map-idle-cdbfirst-20260905-141200`
outputs or count this incomplete attempt as either 2h proof.
The [combined UI validation candidate](COMBINED_UI_VALIDATION.md) has a passing
166-record byte gate. Initial hidden full-tile surface checks pass at 800x600
and 1024x768, but partial-tile edge rendering, final composition, input, and
promotion remain unresolved. Those bounded checks are not full runtime acceptance.
The earlier v4b action-bar audits at [800x600](../../captures/current/partialtiles-noop-v4-800-action-bar-audit-current.json)
and [1024x768](../../captures/current/partialtiles-noop-v4-1024-action-bar-audit-current.json)
each pass **6/6 complete cells**, with every pixel matching its source sprite.
This is bounded software-surface progress on the distinct partial-tile stage;
both runtimes remain **FAIL**. The separately converted diagnostic PNGs
retain the failed source summaries and bind raw surfaces, recorded palettes
and candidate SHAs. They are not full hidden-runtime, visible, input or promotion proof.
The [19:23:55Z screenshot inventory](../../captures/current/action-bar-complete-screenshot-inventory-current.json)
checks **10 current PNGs: four action-bar pixel passes and six older failures**.
Two pixel passes belong to the bounded initial-paint runtime passes above;
the other two belong to v4b runtimes whose traces remain failed. The
[saved-soak audit](../../captures/current/soak-action-bar-audit-current.json)
covers another **12 failing PNGs**, giving **22 checks and 18 action-bar
failures** in total. The inventory links the archived earlier 20-image
checkpoint. These are action-bar results, not four-sided-frame acceptance.
No old screenshot or runtime failure is reclassified.
The earlier [six-screenshot action-bar audit](../../captures/current/action-bar-screenshot-audit-current.md)
still fails complete composition: all five 800x600 captures have 0/6 complete cells;
the 1024x768 capture has only its lower three cells complete. Native
`0040A400` draws the command list before full terrain redraw `00418700`;
the expanded tile area overwrites the relocated bar. The
[source-derived composition recipe](PARTIAL_TILE_RENDERING.md#source-backed-map-composition)
redraws the admitted map panel after terrain and preserves the owner/present
order. The first run of its distinct `-combinedui-partialtiles-validation`
stage, `20260905-142409`,
[failed during pre-HD initialization](../../captures/current/partialtiles-800-pre-hd-failure-current.json):
the surface was 640x480, owner `004617A0`, and convergence status 0. No AV or
screenshot was recorded, and both recorded processes stopped. The guarded
native fallback was reached before the diagnostic should have been armed.
The probe now enables its status breakpoints only at authenticated native join
`0040B88A`, after exact requested dimensions and owner `0040AD40` are observed.
The final v4b checkpoint passes the [builder's 16 fixtures](../../tools/test_build_partial_tile_candidate.py)
and [harness's nine fixtures, covering 199 log cases](../../tools/test_partial_tile_surface_harness.py);
the harness requires one exact `PTILE_MAP_READY` after the loaded contract
and before every status.
The subsequent [v2 run `20260905-195041`](../../captures/current/partialtiles-latearm-v2-800-failure-20260905-195041.json)
observed that valid 800x600 map-ready marker, then four incremental status-1
returns and a status-0 return. Strict rejection stopped it before a full
convergence/presentation pair or any screenshot. No AV was observed. No matching
process remained at the terminal check, but live PIDs had not been captured;
this is not a retrospective exact-PID cleanup record. The candidate SHA is
unchanged. Status 0 can mean an offscreen notification or a rejected context;
the log lacks saved world coordinates, so its cause remains unresolved.
The [v3 run `20260905-195807`](../../captures/current/partialtiles-inputdiag-v3-800-failure-20260905-195807.json)
then recorded world `(90,7)`, map `(100,100)` and scroll `(10,17)`: the rejected
cell is outside the ceiling viewport. No composition-guard return or native
no-op exit was observed, so it remains **FAIL**, with no PNG or full
convergence/presentation pair. Recorded CDB PID 32676 and game PID 42256 were
absent at the terminal observation. Preserve all three failures unchanged.
The final probe/harness require matching guard, input, raw status and native
exit before accepting a strictly offscreen normal-map notification as a no-op;
it provides no draw/present credit. Visible partial cells still require draw
evidence and a separate full convergence/presentation pair remains mandatory.
Candidate bytes are unchanged. The [immutable v4b plan](../../captures/current/partialtiles-noop-v4b-run-plan-current.json)
pins sources and both candidates. Its [800x600 run `20260905-201619`](../../captures/current/partialtiles-noop-v4-800-observation-current.json) ended with
exit 1: the strict parser found an incremental input/native exit without its
guard and invocation. An 800x600 raw surface was captured, but there were no
full convergence/presentation markers. No AV or timeout was observed; recorded
CDB PID 42988 and game PID 38892 were absent at **18:21:27Z**. Preserve the
original failed summary and full trace; the separate 6/6 pixel audit does not
erase unmatched or repeated events. The [1024x768 run `20260905-202225`](../../captures/current/partialtiles-noop-v4-1024-observation-current.json)
also ended with exit 1, on repeated or out-of-order incremental input. It
captured a 1024x768 raw surface but no full convergence/presentation markers,
with no AV or timeout. Recorded CDB PID 28444 and game PID 35832 were absent
at **18:25:10Z**. Its separate 6/6 pixel pass likewise preserves the original
failed runtime summary. Audit the complete bottom-right bar on every new screenshot. Hidden
software composition does not prove the final visible wrapper, and the
historical right-bottom ruling remains resolved.
The separate [combined geometry run](../../captures/current/combinedui-layout-geometry-hidden-current.json)
`20260905-124215` passes relocated panel draws, hit-scan anchors, redraw clipping,
and its synthetic stack return. It is forced geometry evidence, not real input.
The approved [v5 day control recheck](../../captures/current/continuity-day-v5-control-recheck-current.json)
observes native day `1→2`, bounded button-query overrides, the native call return,
and a post-day surface, but remains failed on an overlapping input-trace call.
The separately [approved v6 run](../../captures/current/continuity-day-v6-control-approval-current.json),
`20260905-135344`, finished with a passing outer surface capture, 166 verified
patch records, and both recorded processes stopped. Its
[strict report at 11:56:45Z](../../captures/current/continuity-day-v6-control-current.json)
still fails: line 265 repeats a mouse `GetDeviceState` return without a matching
call during advance 2. Later trace closure, native day `1→2`, the exact return,
and the post-day surface were observed, with one left and one right query
override and no banner override. Preserve the v5 and v6 failures; those partial
observations do not make the strict continuity result pass.
The v7 producer's [20 focused tests](../../tools/test_continuity_day_diagnostic_probe.py)
and parser's [33 tests](../../tools/test_continuity_day_diagnostic_summary.py)
pass. It records actual thread/EIP/ESP identities without deduplicating repeated
input events. The [private v7 control preparation](../../captures/current/partialtiles-and-v7-preparation-current.json)
is ready but had not executed at the checkpoint. The user's recorded
“Approve debugger runs” authorization covers necessary hidden validation for
this active completion task; it does not approve visible runtime, OS input,
manual proof, or promotion.
Read [the completion audit](../../reports/hd_completion_audit.md) for the wider
layout, input, composition, continuity, and resolution requirements.

The [latest aggregate](../../captures/current/current-evidence-refresh-current.json)
records **164/166 checks passing** at **2026-09-06T05:58:14+02:00**. The prior
**2026-09-05T20:39:17+02:00** result is preserved byte-for-byte in the
[pre-minimap refresh snapshot](../../captures/current/pre-minimap-refresh-20260906.json).
Both
documentation guards pass. Only `hd_soak_long_report_guard` and
`hd_endurance_release_checklist` fail, for missing representative two-hour and
manual/promotion proof. The completed short ladder is now reverified from all
five bound reports and guards; its planning consumers issue no new commands or
authorization. Their 20/13/34 focused tests pass, alongside 20 geometry-guard
tests and 19 long-guard fixtures.
The preserved [150/166 observation](../../captures/current/hd-completion-refresh-observation-20260905-195856.json)
and [161/166 observation](../../captures/current/hd-completion-refresh-observation-20260905-203422.json)
remain historical diagnostics of repaired source-compatibility, terminal-state,
fixture and docstring-classification failures. These repairs do not reclassify
runtime failures or reopen resolved battle/right-bottom evidence.

The [earlier repo-only preparation review](../../captures/current/astra-preparation-review-current.md)
completed at **2026-09-05T10:26:47+02:00** with **164/166 checks passing**.
Both documentation guards and their fixture suites passed. Its remaining
`hd_soak_long_report_guard` and `hd_endurance_release_checklist` failures reflect
unfinished endurance and release proof; preparing this repository does not
require those release gates to pass.

The [original preparation verification](../../captures/current/astra-preparation-current.md)
recorded **157/166** at **2026-09-05T09:41:47+02:00**, including then-current
soak integration, PowerShell `Get-FileHash` discovery, and downstream boundary
failures. An earlier attempt stopped at a missing
`hd_soak_report.evaluate_report_for_environment`; that dispatcher now exists.
Treat those failures and the July aggregate below as dated historical
diagnostics, not new tasks inferred from the current handoff.

Evidence inspected on **2026-09-05**:

- [Aggregate evidence](../../captures/current/current-evidence-refresh-current.json)
  previously recorded **2026-07-18T22:14:51+02:00**, with 163/165 checks passing.
  The failures were `hd_soak_long_report_guard` and
  `hd_endurance_release_checklist`. This is a dated baseline, not a promise
  about the next refresh; read the artifacts for the latest result.
- Right-bottom composition's fixture/gate-design question was resolved by the
  owner's **2026-07-14** decision (`96a3d078`), accepting
  `captures/archive/cdb-surface-dump-20260712-155528` for natural-draw evidence.
  The fixture's own class remains `non_natural_isolated_fixture`.
  [The promotion decision](../../captures/current/right-bottom-compose-promotion-decision-current.json)
  remains `defer_stable_promotion` pending manual input. Do not reopen the
  resolved design question or treat it as stable-stage promotion.
- Battle click-to-callback was proven on **2026-07-17** (`c5fe1d70`,
  `captures/archive/battle-visible-input-present-20260717-133221`): observed
  `BATTLE_COMMAND_CLICK_GATE_OBSERVED desc=00514b78 eax=1` followed by
  `BATTLE_COMMAND_CALLBACK eip=0042d4e0`, with no forced-click marker.
  [Battle input evidence](../../captures/current/battle-visible-input-current.json)
  is distinct from manual-input release proof. The old visible-window/CDB
  wrapper split is not an unresolved battle callback problem.
- [Short-step status](../../captures/current/hd-soak-short-step-status-current.md)
  recorded 1/5 rungs complete on **2026-07-18**; the visible map route had a
  missing-window failure. Existing **2026-09-05T07:32:55Z**
  [hidden map-idle evidence](../../captures/current/hd-soak-short2-map-idle-current.json)
  and its [guard](../../captures/current/hd-soak-short2-map-idle-guard-current.json)
  record a passing 120-second, 800x600 run with verified cleanup, candidate SHA
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`, and
  `input_responsiveness=not_applicable_hidden`. This proves only that bounded
  hidden surface/process interval. The checkout still contains unfinished
  hidden-CDB soak additions and unfinished 2h work. Follow the
  [soak roadmap](HD_SOAK_TEST_ROADMAP.md), inspect the actual source and dirty
  tree, and do not describe either 2h route or the full endurance requirement as proven.
  The preparation refresh recorded 2/5 rungs complete. Later completion work
  produced the [600-second idle report](../../captures/current/hd-soak-short10-map-idle-current.json)
  at **2026-09-05T07:58:43Z** and
  [600-second pan report](../../captures/current/hd-soak-short10-map-pan-current.json)
  at **2026-09-05T08:11:17Z**. Both have passing shared guards, 41 samples,
  approximately 599.5 seconds of measured coverage, and verified cleanup.
  Those runs advanced the short status to 4/5; the later thirty-minute pass
  above completes the short ladder. Neither 2h route is yet proven.
  The hidden pass does not erase the separate visible-wrapper failure.
- [Manual checklist](../../captures/current/manual-directinput-validation-checklist-current.md)
  records `pending_manual_validation`; the
  [proof template](../../captures/current/manual-directinput-proof-template-current.md)
  records `template_valid_as_proof=False`. The five targets remain
  `stable_menu_load`, `stable_hd_map_input`, `right_bottom_validation_input`,
  `castle_overview_centered_input`, and `castle_barracks_centered_input`.
  Automated pulse-input callbacks are not automatically manual DirectInput
  release proof. Preserve that distinction and the owner's promotion decision.

Older [load-slot transition readiness](../../captures/current/load-slot-transition-readiness-current.md)
and its [fixtures](../../captures/current/load-slot-transition-readiness-tests-current.md)
record `ready_for_hidden_transition_probe` for the bounded slots 3-5 diagnostic
lane. These are historical diagnostics. That classification is preparation for a possible probe, not execution,
promotion evidence, or a replacement for the active soak/manual-input frontier.

## Task entrypoints and execution boundaries

At the user's **2026-09-06** Git checkpoint, the latest
[controlled keyboard-scroll observation](../../captures/current/framed-army-keypan-observation-20260906.json)
has passing host capture, frame, action-bar and minimap pixel checks at
1024x768. Complete source-bound trace acceptance is still pending. The native
camera moved `(10,17)` to `(11,17)` with the full army record unchanged.
The [two failed movement attempts](UNIT_SELECTION_HD.md) remain failed;
the corrected v3 movement plan `20260906-114000` was dry-run-only before
the checkpoint. Preserve the unfinished local movement/keypan validators.
Do not describe army arrival or full keyboard-input validation as proved.

The **2026-09-08** integration adds the separate
[complete-HD candidate builder](COMPLETE_HD_CANDIDATE.md) and
[release-manifest evaluator](COMPLETE_HD_EVIDENCE.md). This is source
preparation: the experimental `completehd` launcher profile is available, but
the native panel-command adapter still needs real matching evidence and the
other 14 runtime/visual/input/endurance adapters remain incomplete. Unsupported
or launcher-rejected evidence fails closed. Existing component eligibility,
manual proof and explicit stable promotion remain separate requirements.

The newer [complete hidden harness](COMPLETE_HD_HIDDEN_HARNESS.md) changes the
shared harness and initial-trace helper source hashes. Older framed screen/modal
and army transition/portrait validators still pin the previous versions and
reject the new checkout sources. Preserve their recorded evidence and hash
checks; replay historical runs from their recorded source revision. New runs
through those older validators need a separately reviewed compatibility update.
The unfinished local movement/keypan validators remain preserved as well.

The separate [complete-HD army input protocol](COMPLETE_HD_ARMY_INPUT.md)
reconstructs the current complete candidate before preparing controlled native
selection. Its startup recipe is independent of the mutable runtime harness.
All six fixture resolutions retain exact loaded contracts and their own surface
bounds. New-stage runtime, pixel, cleanup and ordinary/manual input evidence
remain separate requirements; the historical movement failures are unchanged.

The [2026-09-13 controlled 1024x768 selection checkpoint](../../captures/current/completehd-army-selection-1024x768-20260913.json)
records a fresh complete-HD v1 run with passing initial/native selection traces,
three identical stopped captures and verified owned-process cleanup. Its
independent audit checks all five before/after/final surfaces: four frame bands,
footer, six action cells, eight portrait bodies and exposed backing pass; the
entire portrait backing survives redraw unchanged. This is controlled native-call
and hidden software-surface evidence. Count glyphs, map-unit artwork, ordinary
input, final-wrapper composition and promotion are not proved. The new complete
movement validator passes its real-file reconstruction fixtures with synthetic
observations; a fresh actual movement run is still required.

| Work | Start with | Focused verification |
| --- | --- | --- |
| Patcher/resolutions | `src/patcher/patch_clash95_hd.py`; root `patch_clash95_hd.py` is the CLI wrapper | `tools/test_patch_resolution.py`, `tools/test_patch_definition_guard.py`, `tools/test_stable_stage_guard.py` |
| Launcher | `src/launcher/core.py`, `src/launcher/resolutions.json`, [LAUNCHER.md](LAUNCHER.md) | `tools/test_launcher_core.py`, `tools/test_launcher_policy_guard.py` |
| Evidence/onboarding | `tools/handoff_freshness_guard.py`, `tools/docs_consistency_guard.py`, `captures/current/` | Corresponding `tools/test_*.py`; review generated-report changes |
| Framed castle/building/battle screens | [FRAMED_SCREEN_VALIDATION.md](FRAMED_SCREEN_VALIDATION.md), [FOUR_SIDED_FRAME.md](FOUR_SIDED_FRAME.md) | Source/byte-bound modal lane required; current map captures do not satisfy this matrix |
| Endurance/input | [FINISH_LINE_RUNBOOK.md](FINISH_LINE_RUNBOOK.md), [HD_SOAK_TEST_ROADMAP.md](HD_SOAK_TEST_ROADMAP.md) | Corresponding report/ladder fixtures before any authorized runtime |

The protected stable stage remains:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch
```

Never overwrite `C:\Clash\clash95.exe`; verify the input SHA and old bytes for
every binary patch and put candidates outside the repository. New patch work
uses a validation-stage suffix. Do not distribute game binaries, assets, saves,
wrapper binaries, dumps, or raw captures.

For a repository-preparation task, retain the no-runtime boundary: Do not
launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows unless
the user explicitly approves. The documented aggregate may invoke dry-run and
negative-approval checks; these must stop before game/debugger execution.
Do not run visible/manual validation without fresh explicit user approval.
Runtime work belongs to a separately authorized task under the root guide;
hidden-CDB evidence proves only its stated route/surface/endurance claims.
It never proves visible composition, manual responsiveness, or promotion.

Make routine implementation choices within the authorized task and complete
the relevant verification without repeatedly asking for permission. Delegate
independent investigation or review when useful, assigning separate file
ownership for edits. Run tests proportionate to the change; broaden them when
failures or changed behavior justify it. Report what changed, what was tested,
and unresolved evidence gaps. Do not make a gate green by weakening its checks
or manufacturing approvals or observations.

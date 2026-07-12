# LLM Wiki

This repository is a markdown-first personal knowledge base inspired by Andrej
Karpathy's LLM Wiki pattern: the user curates source material, and an LLM
maintains a durable wiki that compounds over time.

The wiki is designed to work immediately in Obsidian or any markdown editor. No
database, vector index, web app, or external dependency is required.

## Repository Layout

```text
raw/
  inbox/       New user-added source files waiting for ingest
  processed/   Sources moved after explicit user approval
  assets/      User-provided images, PDFs, media, and attachments
wiki/
  index.md     Catalog of wiki content
  log.md       Append-only maintenance and ingest log
  overview.md  Starter guide for this wiki
  sources/     Source summary pages
  entities/    People, organizations, projects, places, works
  concepts/    Reusable ideas, methods, terms, patterns
  syntheses/   Cross-source synthesis pages
  questions/   Open questions and unresolved research threads
  comparisons/ Structured comparisons
meta/
  templates/   Page templates
  workflows/   Operating workflows
tools/
  wiki_search.py
  wiki_lint.py
AGENTS.md      Durable instructions for Codex and future LLM agents
```

## Core Rules

- `raw/` is source-of-truth and user-owned.
- Agents must not edit raw sources.
- Moving files from `raw/inbox/` to `raw/processed/` requires explicit approval.
- `wiki/` is agent-maintained and should stay readable by humans.
- Every sourced wiki claim needs a citation.
- Contradictions are recorded; older claims are not silently overwritten.

## Add A Source

1. Put the source file in `raw/inbox/`.
2. Ask Codex to ingest it using the prompt at the end of this README.
3. Review the generated source summary and any linked entity, concept,
   synthesis, question, or comparison pages.
4. If the ingest looks good, explicitly tell Codex whether to move the raw file
   to `raw/processed/`.

## Ask Codex To Ingest A Source

Use a prompt like:

```text
Ingest raw/inbox/<file-name> into the LLM Wiki. Follow AGENTS.md. Create or
update source, entity, concept, synthesis, question, and comparison pages as
appropriate. Cite every sourced claim. Do not move or modify the raw source
unless I explicitly approve it after review. Run the linter when done.
```

## Query The Wiki

Ask natural questions, for example:

```text
Search the wiki for what we know about <topic>. Separate sourced facts,
interpretation, uncertainty, contradictions, and open questions. Cite the
relevant wiki/source pages.
```

Codex should search `wiki/`, read relevant pages, inspect cited raw sources only
when needed, and update the wiki when a durable insight or gap is found.

## Tools

Search markdown pages under `wiki/`:

```powershell
python tools/wiki_search.py wiki
python tools/wiki_search.py "your query here"
```

Lint wiki structure and links:

```powershell
python tools/wiki_lint.py
```

Both scripts use only the Python standard library.

If `python` is not on your `PATH`, run the same scripts with any Python 3
interpreter path, for example:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\wiki_lint.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\wiki_search.py wiki
```

Battle UI probe scaffolding is repo-only and safe to test without launching the
game:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\test_battle_ui_summary.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\test_battle_ui_gate.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\test_battle_command_availability.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\test_battle_slot_scan_summary.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\test_battle_save_unit_inventory.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\test_battle_constructed_save_fixture.py
```

## Clash95 HD Map Smoke Reproduction

The HD mod workspace keeps generated executables outside the repository. Use a
fresh, user-owned `C:\Clash\clash95.exe` as input and write candidates under
`C:\ClashTests\...`. Never overwrite `C:\Clash\clash95.exe`, and do not commit
patched executables or game-derived dumps.

## Clash95 HD Release Packaging Boundary

This repository ships source scripts, documentation, and small evidence
manifests only. It does not ship the original game binary, patched `.exe`
files, wrapper DLL binaries, copied game assets, saves, memory dumps, CD/ISO
contents, cracks, or large raw captures. Users must provide their own
`C:\Clash\clash95.exe` and build candidates locally under `C:\ClashTests`.

Known-good input SHA-256:

```text
500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae
```

Update 2026-07-12: after the workspace move off OneDrive lost the local raw
CDB logs, the full hidden-desktop evidence set was regenerated on fresh runs
(castle overview catalog `captures/archive/cdb-surface-dump-20260712-144019`,
focused hitbox `144151`, visible multihit `144245`, dormant flags1f multihit
`144327`, barracks controlled-stop `144445` and success-branch `151015`,
right-bottom owner route `160131`, compose probe `144922`, compose patch
`160204`, grid hit `150240`, nativecenter descriptor `150434`, compose
full-start `160351`, natural UI probe `160441`, and the load-slot boundary
set `153503`–`154340`). Candidate SHAs reproduce the May values
byte-for-byte, archive `cdb-surface-dump.log` files are now tracked in git,
and the slot5-as-slot0 fixture runs `154653`/`154903`/`155528` prove the
natural right-bottom owner/action screen renders end-to-end with
`NOWNER_WRAPPER_COPYBACK_DONE` and zero AV rows (isolated fixture evidence;
the stable stage and promotion state are unchanged, and the promotion
decisions still record `stable_stage_should_change=False`).

Current release status as of 2026-05-18:

- Stable HD map stage remains
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
- `rightbottomcompose` currently fails the right-bottom action-menu validation:
  controlled composition recovers the lower/right UI, but the natural UI probe
  still reports `RBUI_PANEL_DRAW=0` and `RBUI_ACTION_BOX=0`; the natural castle
  route parks action descriptor `004338E0` off-screen at `(1000,426)` with
  `owner_flag=0x00`, so striped/out-of-place action-menu screenshots remain
  validation blockers rather than stable evidence.
- `rightbottomaction-nativecenter` is the current controlled visual candidate
  for the action-menu stripe/layout issue. The wrapper-aware hidden-desktop CDB
  surface dump at `captures\archive\cdb-surface-dump-20260517-172611` passes and proves
  stock `00435BC0` renders on a temporary 640x480 surface before copyback to the
  800x600 map surface. A refreshed strict natural UI probe still fails closed
  because the map/viewport path is reached but owner/action rows are absent, so
  it remains validation-only until natural UI and manual input proof are
  refreshed against it.
- Focused natural castle-click proof
  `captures\archive\cdb-surface-dump-20260518-092756` now proves screen `(352,272)` /
  map `(15,21)` on castle tile `32768` follows
  `sub_4084A0 -> Building_GetInto -> 00422180` and dumps a 640x480 castle
  overview surface. Follow-up route-split proof
  `captures\archive\cdb-surface-dump-20260518-100917` drives overview command `0x63`
  through callback `00433C20` and verifies the owner-global writes. The full
  owner-loop gate `captures\archive\cdb-surface-dump-20260518-213418` then proves the
  `004338E0` action descriptor exists but is intentionally parked at `x=1000`
  because this save's owner flag is `0x00`.
- Battle UI force-entry proof
  `captures\archive\cdb-surface-dump-20260518-214535` reaches
  `Unit_Attack -> 0042E9E0` and reproduces the uncentered/stripey battle UI
  composition. The narrowed `battle-ui-center-present-wrapper` patch is now in
  the `battlecenter` validation stage, and exact CDB `.writemem` proof
  `captures\archive\cdb-surface-dump-20260518-221018` classifies the initial battle
  frame as `centered-native-640x480` at offset `(80,60)` with no AV rows.
- `castlecenter-all` is validation-only; it is not part of the stable default
  stage.
- Hidden/no-popup validation passes for the stable map path and refreshed
  castle overview evidence.
- Manual DirectInput proof is still pending, so the mod should not be described
  as fully release-complete until that manifest passes or an explicit CDB-only
  override manifest is approved.
- There are five remaining manual targets, all five required before normal
  promotion: stable menu load, stable HD map input, right-bottom validation
  input, castle barracks centered input, and castle overview centered input.

Fresh validation and release reports are in:

- `reports\hd_completion_plan.md`
- `reports\patch_stage_inventory.md`
- `reports\final_hd_validation_matrix.md`
- `reports\final_hd_release_checklist.md`
- `reports\pr_body_complete_hd_mod_20260515.md`

To remove generated candidates, delete the relevant subdirectory under
`C:\ClashTests`. Do not delete or mutate `C:\Clash\clash95.exe`.

Start with the dry-run helper. It verifies the base SHA when
`C:\Clash\clash95.exe` is accessible, prints a unique candidate path, prints the
exact commands it would run, and refuses repository-local candidate output by
default:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\prepare_hd_map_smoke_candidate.ps1 -Json
```

When the plan looks right, run the same helper with `-Execute` from a normal
Windows shell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\prepare_hd_map_smoke_candidate.ps1 -Execute
```

The manual equivalent is below.

Current HD map stage:

```powershell
$BundledPy = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Get-Command python -ErrorAction SilentlyContinue) {
  $Py = (Get-Command python).Source
} elseif (Test-Path $BundledPy) {
  $Py = $BundledPy
} else {
  throw 'Python 3 was not found on PATH and the bundled Codex runtime was not found.'
}
$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'
```

Verify the base executable hash before patching:

```powershell
$Expected = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
$Actual = (Get-FileHash 'C:\Clash\clash95.exe' -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) {
  throw "Unexpected C:\Clash\clash95.exe SHA-256: $Actual"
}
```

Build a uniquely named candidate outside the repo:

```powershell
$CandidateDir = 'C:\ClashTests\hd-map-smoke'
New-Item -ItemType Directory -Force -Path $CandidateDir | Out-Null
$Candidate = Join-Path $CandidateDir ('clash95_hd_smoke_{0}.exe' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
& $Py .\patch_clash95_hd.py `
  --input 'C:\Clash\clash95.exe' `
  --output $Candidate `
  --stage $Stage
```

Generate the patch-stage byte manifest. The JSON includes each selected patch's
file offset, RVA, VA, expected old bytes, expected new bytes, actual bytes,
status, group, and rationale note:

```powershell
& $Py .\tools\patch_stage_report.py `
  --exe $Candidate `
  --stage $Stage `
  --require-current-hd-map `
  --write-json .\captures\current\patch-stage-current-hd-map.json
```

Reproduce the current repo-only HD map smoke matrix with the existing normal and
forced-visible CDB surface-dump evidence:

```powershell
& $Py .\tools\hd_map_smoke_matrix.py `
  --patch-exe $Candidate `
  --stage $Stage `
  --normal-run .\captures\archive\cdb-surface-dump-20260506-190037 `
  --forced-run .\captures\archive\cdb-surface-dump-20260506-201114 `
  --require-pass `
  --write-json .\captures\current\hd-map-smoke-current.json `
  --write-markdown .\captures\current\hd-map-smoke-current.md
```

The current known-good matrix expects:

- `patch_stage.status = pass`
- `patch_stage.status_counts.patched = 118`
- `patch_stage.status_counts.original = 0`
- `patch_stage.status_counts.unexpected = 0`
- `post_owner_evidence.status = pass`

This smoke matrix does not launch the game or CDB. It proves that a freshly
generated candidate has the current HD map patch bytes and matches the archived
normal/forced-visible CDB evidence. To create new visual evidence, use the
hidden-desktop CDB surface-dump workflow documented in `AGENTS.md`.

Compare two patch-stage manifests without touching executables:

```powershell
& $Py .\tools\patch_manifest_compare.py `
  .\captures\archive\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-20260424.json `
  .\captures\archive\patch-stage-mapdraw-partial12-20260424.json `
  --write-json .\captures\current\patch-manifest-compare-current-vs-partial12.json `
  --write-markdown .\captures\current\patch-manifest-compare-current-vs-partial12.md
```

The comparer highlights changed offsets, groups, expected old/new bytes, actual
bytes, and `original` / `unexpected` statuses.

Open `captures/current/hd-map-evidence-current.md` for the compact current evidence
index. It links the smoke matrix, post-owner evidence matrix, patch-manifest
comparison, and the current screenshot artifacts.

Check that the evidence index links and screenshots still resolve:

```powershell
& $Py .\tools\evidence_index_check.py `
  .\captures\current\hd-map-evidence-current.md `
  --require-pass `
  --write-json .\captures\current\hd-map-evidence-current-check.json
```

Refresh the current repo-only evidence set, including the HD map smoke matrix,
no-popup map evidence matrix, no-popup map evidence matrix tests,
patch-manifest comparison, evidence-index check,
barracks success-branch proof,
right-bottom UI probe summary, right-bottom owner/action route proof,
right-bottom debugger composition proof, right-bottom validation patch proof,
right-bottom validation patch full-start route proof, right-bottom validation
patch normal map gate, right-bottom validation patch natural UI probe,
right-bottom validation patch promotion decision, right-bottom validation
evidence matrix, right-bottom validation patch promotion decision tests,
right-bottom validation evidence matrix tests, right-bottom action-menu blocker
triage, right-bottom action-menu blocker triage tests, right-bottom visual
artifact guard, right-bottom visual artifact guard tests, load-slot transition
probe guard, load-slot transition probe guard tests, load-slot transition run
plan, load-slot transition run plan tests, load-slot transition geometry guard,
load-slot transition geometry guard tests, castle overview matrix,
castle overview promotion decision,
castle overview evidence matrix tests, castle overview promotion decision tests,
castle overview gate tests, castle overview baseline recheck,
castle owner records summary tests,
castle overview hitbox summary tests,
castle overview hitmap summary tests,
castle overview multihit summary tests,
castle overview baseline recheck tests, castle overview probe guard, castle
overview probe guard tests, stable stage
guard, stable stage guard tests, executable artifact guard, no-visible runtime
guard, no-visible runtime guard tests, and process hygiene guard. It also
checks the surface-dump launcher policy and the aggregate no-popup boundary,
then runs the no-popup guard regression tests:

```powershell
& $Py .\tools\current_evidence_refresh.py --require-pass
```

Current output is `captures\current\current-evidence-refresh-current.md`. It remains
repo-only and does not launch Clash95, CDB, wrappers, or a visible window. As
of the slot `5` natural route update, the aggregate refresh is expected to stay
non-release because `right_bottom_compose_ui_probe` still lacks natural
owner/action draw rows; the no-popup boundary subset still passes. The current
no-popup map baseline is `captures\current\no-popup-map-evidence-current.md`, pairing
the stable normal visibility-explained run
`captures\archive\cdb-surface-dump-20260429-140916` with the stable forced-visible
edge proof `captures\archive\cdb-surface-dump-20260429-135242`.
Its fixture coverage is
`captures\current\no-popup-map-evidence-tests-current.md`, which passes repo-only with
`test_count=5` and covers explicit normal/forced inputs, latest passing-run
selection, normal visibility-gate regressions, forced-visible gate
regressions, and CLI `--require-pass` fail-closed behavior.

The current right-bottom owner/action route proof is
`captures\archive\cdb-surface-dump-20260513-112339`, a hidden-desktop run with
`-SkipMapValidation` whose action-panel summary reaches the owner setup,
`004347A0`, `00434E20`, `00435280`, `00435500`, action-box redirect, copyback,
and `SURFDUMP_READY` with zero AV rows. Its action-box composition summary
records `13` filtered text rows, `5` null-destination present/copy rows, `2`
sample rows, and no present rows intersecting the bottom tooltip or bottom-right
panel regions, so the next right-bottom target is native anchor/final
composition behavior.

The current controlled right-bottom visual candidate is
`captures\current\right-bottom-action-nativecenter-current.md`, backed by wrapper-aware
hidden run `captures\archive\cdb-surface-dump-20260517-172611` and stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter`.
That stage hooks the `00433914 -> 00435BC0` action-owner call through a
temporary native 640x480 surface, then center-copies the native action screen
to the 800x600 map surface. The CDB log proves stock `00435BC0` entered with a
640x480 surface, `0051B7E0` restored the 800x600 map surface, and
`SURFDUMP_READY` dumped the copied-back action screen. The screenshot removes
the striped `dw_13.gfx` backdrop and keeps the buttons on the action-screen
art. It is still validation-only pending refreshed natural UI and manual/input
proof.

The refreshed native-center natural UI probe is
`captures\archive\cdb-surface-dump-20260517-163734`. It uses the same candidate SHA
`D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C`, passes the
hidden map surface/visibility gate, and records `RBUI_VIEWPORT_SWITCH=1`, but
the strict right-bottom UI summary fails with `OwnerActionRowsSeen=False`,
`RBUI_PANEL_DRAW=0`, and `RBUI_ACTION_BOX=0`. The right-bottom UI launcher now
fails closed by default unless owner/action rows appear; descriptor-only
diagnostics require `-AllowDescriptorOnly`. A full-start attempt at
`captures\archive\cdb-surface-dump-20260517-163116` timed out before gameplay with no
AV rows.

The focused natural castle command route is
`captures\archive\cdb-surface-dump-20260518-100917`. It starts from the live map castle
click, reaches `00422180`, hits overview raw ID `254`, installs command `99`
callback `00433C20`, and writes `dword_532150`, `dword_53214C`, and
`dword_532154`. After the probe exits overview, the first `00511D40`
descriptor scan reports `result=0` with `d532218=00000000`, so command `0x63`
is owner-state setup rather than the action-screen opener by itself.

The full owner-loop gate is
`captures\archive\cdb-surface-dump-20260518-213418`. It reaches the owner descriptor
list after command `0x63` and logs descriptor `d1=(1000,426 cb=004338e0)`.
Because `owner_flag=0x00`, the action descriptor is intentionally off-screen in
this save state; the castle route is therefore not the source of the user's
visible stripe/layout screenshot.

The current natural slot `5` load proof is
`captures\archive\cdb-surface-dump-20260527-163809\load-slot-transition-summary.md`.
It uses late-only slot forcing after the real `0044895A` transition and reaches
matching slot `5`, `LOADSAVE`, `SURFDUMP_PLAYGAME`, and zero AV rows. The
current natural right-bottom rerun is
`captures\archive\cdb-surface-dump-20260527-193512\right-bottom-natural-slot5-summary.md`.
It reaches map `(14,20)`, command `0x63`, owner flag bit `0x02`, descriptor
`004338E0`, and a diagnostic `NOWNER_RELEASE_OWNER_DESC_CLICK` row that clears
the hidden forced-click state only after `004338E0` entry. The summary reports
`status=owner_action_draw_reached`: `Render_Begin` exits on iteration `1`,
`d544d04` is `0`, and `NOWNER_ACTION_CALL_WRAPPER` plus
`NOWNER_OWNER_435BC0_ENTRY` appear. The strict right-bottom blocker has moved
later: `NOWNER_WRAPPER_COPYBACK_DONE` is still absent, so the route is not
promotion-ready and the stable/default stage remains unchanged.

The current battle UI evidence is
`captures\current\battle-ui-force-entry-current.md`, backed by exact CDB `.writemem`
run `captures\archive\cdb-surface-dump-20260518-221018`. The harness-only force-entry
probe reaches `Unit_Attack -> 0042E9E0`, the new
`battle-ui-center-present-wrapper` calls through cave `0051BA00`, and the
summary records `visual_mode=centered-native-640x480`,
`centered_offset=[80,60]`, `centered_wrapper_seen=True`, and `av_count=0`.
Command descriptor hit proof is now
`captures\current\battle-ui-command-hit-current.md`, backed by
`captures\archive\cdb-surface-dump-20260520-094032`; the controlled CDB probe logs both
`BATTLE_COMMAND_HIT coord_mode=visual result=2` and
`BATTLE_COMMAND_NATIVE_HIT coord_mode=native result=2`. Command callback entry
proof is `captures\current\battle-ui-command-callback-current.md`, backed by
`captures\archive\cdb-surface-dump-20260520-100717`; descriptor `00514b78` reaches
callback `0042d4e0`, then records
`BATTLE_COMMAND_CALLBACK_RESULT branch=precondition-disabled` with
`unit_type=5`, `avail=8`, and `enabled=0`. Enabled-command callback result
proof is `captures\current\battle-ui-command-enabled-callback-current.md`, backed by
`captures\archive\cdb-surface-dump-20260520-101859`; it temporarily changes selected
unit type `5` to `8`, records `avail=10`, `enabled=3`, skips the callback
render-begin lock under CDB, and reaches `branch=state2` with no AV rows.
Tactical-grid coordinate proof is `captures\current\battle-ui-grid-hit-current.md`,
backed by `captures\archive\cdb-surface-dump-20260520-103155`; the probe reaches
`0042CB50` and classifies displayed `(144,108)` as cell `(1,1)` versus native
`(64,48)` as cell `(0,0)`. Centered-input wrapper proof is
`captures\current\battle-ui-centered-input-current.md`, backed by
`captures\archive\cdb-surface-dump-20260520-111115`; the validation-only inputprobe
stage wraps the battle grid call through `0051BAA0` and the descriptor call
through `0051BAF0`, then logs visual coordinates transforming to native
coordinates and restoring afterward:
`grid_input_wrapper_ok=True`, `descriptor_input_wrapper_ok=True`, and
`centered_input_wrapper_ok=True`. Modal/input classification is
`captures\current\battle-ui-modal-classified-current.md`, backed by
`captures\archive\cdb-surface-dump-20260520-103714`; the probe reaches `004605D0` and
logs `BATTLE_MODAL_CLASSIFIED status=input_update_seen_no_modal`.
Post-ready redraw/copyback proof is
`captures\current\battle-ui-post-ready-redraw-current.md`, backed by
`captures\archive\cdb-surface-dump-20260520-195244`; after `BATTLE_READY`, the probe
logs 9 post-ready presents, 6 post-ready copybacks, a forced grid point
`(144,108)->(64,48)`, final present return `0042CB46`, and no AV rows.
Command availability scan is `captures\current\battle-command-availability-current.md`;
it parses 18 natural unit records from the same proof log and reports naturally
enabled unit count `0`, with selected type `5` at `availability=8`,
`enabled=0`; the executable table scan through unit type `31` identifies 11
enabled unit types to hunt for in a richer fixture: Dragon cavalry, Archer,
Crossbower, Musketeer, Catapult, Cannon, Forester, Cyklop, Wizard, Winger, and
Dragon.
Battle load-slot scan is `captures\current\battle-slot-scan-current.md`; it aggregates
six local save-slot attempts. Slots `0`, `1`, and `2` route far enough to expose
unit rows, but still have naturally enabled command count `0`; slots `3`, `4`,
and `5` time out before unit scan under the current hidden CDB route. The slot
scan proves the current local saves do not yet provide the richer enabled
command state.
Read-only save-file inventory is
`captures\current\battle-save-unit-inventory-current.md`; it uses the same unit-record
layout at save offset `0x00023EF6` (16 bytes after the runtime game-data
offset), parses 63 units across all six local `.dat` saves, and again reports
natural enabled command unit count `0`. The local saves currently contain only
disabled-command battle unit types: Peasant, Light infantry, Light cavalry,
Highlander, and Builder.
Constructed-save fixture evidence is
`captures\current\battle-constructed-save-fixture-current.md` plus
`captures\current\battle-constructed-fixture-unit-scan-current.md`; the helper wrote
only an isolated copied save under `C:\ClashTests\battle-enabled-fixture-20260520-210728`
and left `C:\Clash\save` untouched. Hidden CDB then loaded slot `0` from that
isolated work dir and parsed one naturally enabled unit: Dragon cavalry
(`availability=10`, `enabled=3`) at unit index `0`.
Constructed-fixture command callback proof is
`captures\current\battle-constructed-fixture-command-callback-current.md`; the same
isolated fixture reaches `0042D4E0` with unit type `8`, `enabled=3`, records
`branch=state1`, has `BATTLE_COMMAND_FORCE_ENABLED_UNIT=0`, and now observes
the click gate returning `eax=1` without forcing it. The current hidden CDB
run is `captures\archive\cdb-surface-dump-20260520-220459` through the inputprobe
stage; it starts from displayed coordinate `(588,440)`, the centered-input
wrapper carries that to native `(508,380)` by `BATTLE_COMMAND_PRE_GATES`, and
the stock click gate still succeeds. It no longer skips `Render_Begin` at
`0042D520` and no longer needs the hidden-harness `DD_IsLost` loop guard or
pre-gate click rearm. The probe releases the synthetic click state after the
stock click gate succeeds, then logs `Render_Begin` entering at `004609D0` and
exiting naturally on iteration `1` with `dd_is_flipping=0`, `dd_is_lost=0`,
and `guard=0`.
The current combined checkpoint is `captures\current\battle-ui-evidence-current.md`,
which passes repo-only checks over force-entry, command, enabled callback,
grid, centered-input wrapper, post-ready redraw/copyback, availability scan,
slot scan, save-file inventory, constructed-fixture planning and runtime unit
scan, constructed-fixture command callback, modal, patch-stage, inputprobe
patch-stage, and stable HD-map smoke evidence. Manual enabled-command cadence
is still pending because the current constructed-fixture callback proof uses a
synthetic hidden-CDB click/release, but that click now enters as a displayed
inputprobe coordinate rather than a native shortcut, and it no longer uses a
unit-type override, forced click gate, pre-gate click rearm, direct
render-begin skip, or render-begin lost-surface guard.

Unit-selection evidence is now separated from the right-bottom owner/action
menu: `captures\archive\cdb-surface-dump-20260517-171559` proves the stable
`sub_408030 -> sub_406980 -> sub_40A500 -> sub_423B00` selected-unit route
after the turn-loop boundary, but that path does not enter the
`004338E0 -> 00435BC0` castle/building owner action cluster.

The current validation-only native-to-HD composition proof is
`captures\archive\cdb-surface-dump-20260513-115303`. It is also hidden-desktop and
uses `-SkipMapValidation`; the extra probe manually copies the native status
rectangle to `(586,528)` and the native action-box rectangle to `(285,524)`.
The repo-only refresh records this as `right_bottom_compose_probe: PASS`:
`bottom_right_ui_corner` improves from `21.43%` to `48.228%` nonblack, while
previously black `r8c10` and `r8c11` recover to `54.102%` and `42.822%`.

The corresponding isolated validation patch stage is
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`.
Its hidden-desktop proof is `captures\archive\cdb-surface-dump-20260513-120712`, using
the existing owner/action extra probe rather than the debugger-side manual
composition probe. The byte manifest
`captures\archive\patch-stage-right-bottom-compose-20260513.json` records `122/122`
selected bytes patched, including `4/4` in `right-bottom-compose-proof`, with
the current HD map gate still passing. The run SHA is
`EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`; it stays
validation-only and is not part of the stable HD map stage.

The validation patch also passed a full-start controlled owner/action route at
`captures\archive\cdb-surface-dump-20260513-122928` with `-NoSkipStartAnims`,
`-UseDdrawProxy`, `-SkipMapValidation`, and the existing owner/action extra
probe. That run keeps the same SHA, reports `ready=True` and `av_count=0`, and
reproduces the same lower/right recovery:
`bottom_right_ui_corner=48.228%`, `r8c10=54.102%`, and `r8c11=42.822%`.

The same validation stage also passed a normal hidden map-validation run at
`captures\archive\cdb-surface-dump-20260513-121513` with `-NoSkipStartAnims`,
`-UseDdrawProxy`, and no `-SkipMapValidation`. It produced an 800x600
gameplay-like surface with `108` active cells; all `13` blank active cells were
explained as `visibility_zero`, with zero unexplained blanks.

The natural right-bottom UI launcher at
`captures\archive\cdb-surface-dump-20260513-122200`. That run keeps the existing
descriptor/viewport evidence intact on the validation stage
(`RBUI_DESC_SWITCH=35`, `RBUI_VIEWPORT_SWITCH=1`) without naturally entering
the owner/action draw rows (`RBUI_PANEL_DRAW=0`, `RBUI_ACTION_BOX=0`).
The current repo-only gate treats this as a failure, not a visual pass.

The current explicit right-bottom promotion decision is
`captures\current\right-bottom-compose-promotion-decision-current.md`. It now fails
closed with `decision=defer_stable_promotion` and
`stable_stage_should_change=False`, because the natural UI probe still does not
enter owner/action draw rows and the controlled grid-hit screenshot is
diagnostic, not an acceptable user-facing layout.

The compact right-bottom validation matrix is
`captures\current\right-bottom-compose-evidence-current.md`. It fails repo-only with
`promotion_status=validation_stage_only`, `stable_stage_should_change=False`,
and the same validation-stage SHA
`EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`.

The right-bottom validation guard tests are
`captures\current\right-bottom-compose-promotion-decision-tests-current.md` and
`captures\current\right-bottom-compose-evidence-matrix-tests-current.md`. They pass
repo-only with `test_count=6` and `test_count=5`; they cover default defer
behavior, natural owner/action row requirements, missing or failing route
gates, manual-proof/CDB-override promotion eligibility, required
route/map/UI/decision gates, hidden-desktop and full-start safety, visibility
proof, candidate SHA agreement, and CLI `--require-pass` fail-closed behavior.

The castle overview baseline recheck is
`captures\current\castle-overview-baseline-recheck-current.md`. It passes repo-only,
runs the fixed full-overview visual baseline at
`captures\archive\cdb-surface-dump-20260515-105041`, reruns the barracks controlled-stop
baseline at `captures\archive\cdb-surface-dump-20260512-082418`, and
confirms the latest `castlecenter-all` matrix remains validation-only with
visible and dormant multi-hit target-done completion proof.

The castle overview baseline recheck tests are
`captures\current\castle-overview-baseline-recheck-tests-current.md`. They pass
repo-only and cover stale overview visual baselines, stale barracks
controlled-stop baselines, failing latest castle overview matrices, missing
visible/dormant target-done completion proof, and JSON/Markdown output writing.

The castle overview probe guard is
`captures\current\castle-overview-probe-guard-current.md`. It passes repo-only and
checks that `probes/cdb/castle/clash95_castle_overview_hitbox_extra.cdb` still covers the focused
descriptor-loop breakpoints `00422544`, `0042257E`, `00422590`, and `0042262C`,
that the old crashing `CASTLECAT_OVERVIEW_DESC_INPUT_WRAPPER_ENTRY` path has
not returned, and that the focused hitbox log still proves the displayed
coordinate click gate with zero AV rows.

The castle overview probe guard tests are
`captures\current\castle-overview-probe-guard-tests-current.md`. They pass repo-only
and cover the good focused-probe shape, each missing descriptor-loop
breakpoint, each missing required probe/parser marker, the old crashing
overview wrapper markers, AV rows in the focused hitbox log, missing focused
wrapper/gate proof rows, main/overview surface-size regressions, callback
entry, and the CLI JSON/Markdown output plus `--require-pass` fail-closed
path.

The stable stage guard is `captures\current\stable-stage-guard-current.md`. It passes
repo-only and confirms the patcher default remains the stable dynvswitch stage
with no validation-only groups included. It also checks that the right-bottom
composition group and castle visual/input groups remain scoped to their
validation stages, and that the castle overview promotion decision still
carries focused displayed-wrapper plus visible/dormant multi-hit proof. It
also checks the castle overview evidence matrix for the same proof bundle.

The stable stage guard tests are
`captures\current\stable-stage-guard-tests-current.md`. They pass repo-only and cover
patcher-default drift, validation-only group leakage into the stable stage,
missing `castlecenter-all` validation groups, promotion decisions that would
change the stable stage, stale castle promotion decisions or evidence matrices
without the required focused/multihit proof, and the CLI JSON/Markdown output plus
`--require-pass` fail-closed path.

The executable artifact guard is `captures\current\exe-artifact-guard-current.md`. It
passes repo-only with no `.exe` files present in the repository filesystem, no
`.exe` files tracked in the git index, and the root-level `.exe` ignore rule in
place. Staged root `.exe` removals are treated as allowed cleanup records.

The surface-dump policy guard is
`captures\current\surface-dump-policy-guard-current.md`. It passes repo-only and checks
that `scripts/cdb/run_cdb_surface_dump.ps1` defaults to hidden desktop, refuses implicit
visible fallback after `CreateDesktop` failure, and only uses active-desktop
launching inside the explicit `-AllowVisibleDesktop` branch.

The no-visible runtime guard is
`captures\current\no-visible-runtime-guard-current.md`. It passes repo-only and checks
that every referenced CDB surface-dump run in the current evidence set used
`LaunchMode=hidden-desktop` and `HiddenDesktop=True`, so visible-desktop
fallback cannot silently enter the current evidence refresh.
Its fixture coverage is
`captures\current\no-visible-runtime-guard-tests-current.md`, which passes repo-only
with `test_count=5` and covers hidden-desktop summaries, weak runtime policy
text, visible runtime summary regressions, missing run summaries, and CLI
`--require-pass` fail-closed behavior.

The process hygiene guard is `captures\current\process-hygiene-guard-current.md`. It
uses a Windows Toolhelp process snapshot, launches no game/debugger/window, and
passes with `0` matching `cdb.exe` or `clash95*` runtime processes, so stale
runtime processes cannot silently remain after a refresh.

The no-popup boundary guard is
`captures\current\no-popup-boundary-guard-current.md`. It passes repo-only and verifies
that the refresh includes the stable-stage, executable-artifact,
surface-dump-policy, visible-runtime launcher, no-visible-runtime, and
process-hygiene guards. It records `required_guard_count=6`,
`required_supporting_report_count=84`, and `required_report_count=90`. It also
requires the no-popup map evidence matrix and its fixture tests, no-popup guard
regression report, no-visible runtime guard tests, HD soak execution-boundary
report and tests, manual DirectInput
checklist/proof-template/run-plan reports plus tests, right-bottom validation
guard tests, right-bottom action-menu blocker triage and tests,
right-bottom visual artifact guard and tests, load-slot transition probe guard
and tests, load-slot transition run plan and tests, load-slot transition
geometry guard and tests, load-slot transition readiness matrix and tests,
castle overview baseline
recheck, castle overview baseline recheck tests, castle
overview evidence matrix tests, castle overview gate
tests, castle overview promotion decision tests, castle owner records summary
tests, castle overview hitbox summary tests, castle overview probe guard,
castle overview hitmap summary tests, castle overview multihit summary tests,
castle overview probe guard tests, and stable stage guard tests as supporting
reports, and verifies that the evidence index links every report.

The no-popup guard regression tests are repo-only:

```powershell
& $Py .\tools\test_no_popup_guards.py
```

They cover each missing boundary report link, missing/failed core refresh
checks, each missing supporting refresh check, and surface-dump launcher policy
drift. The failing surface-dump policy CLI fixture writes only under
`.codex-loop\tmp-tests\no-popup-guards-fixture`, keeping the current
`captures\current\surface-dump-policy-guard-current.md/json` reports reserved for live
refresh output. The current refresh report is
`captures\current\no-popup-guard-tests-current.md`.

Current castle/interior validation keeps the stable HD map stage unchanged and
uses this broader stage only for castle-screen evidence:

```powershell
$CastleStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all'
```

The current compact no-popup matrix is repo-only and does not launch Clash95,
CDB, wrappers, or a visible window:

```powershell
& $Py .\tools\castle_overview_evidence_matrix.py `
  --write-json .\captures\current\castle-overview-evidence-current.json `
  --write-markdown .\captures\current\castle-overview-evidence-current.md `
  --require-pass
```

Current output is `captures\current\castle-overview-evidence-current.md`. It passes
with `134` patched bytes, `0` original bytes, `0` unexpected bytes, centered
overview geometry, focused command `0x86`, visible commands `0x86`, `0x63`,
`0x87`, forced dormant commands `0x99`, `0x9C`, `0x9F`, `0xA6`, and the
barracks no-echo baseline. Its status is still `validation_stage_only`; it is
not a stable HD map-stage promotion.

The castle overview evidence matrix tests are
`captures\current\castle-overview-evidence-matrix-tests-current.md`. They pass
repo-only and cover all-checks-pass aggregation, every required component-gate
failure, required displayed-wrapper proof in the focused command `0x86`
hitbox gate, target-done completion proof in the visible/dormant multi-hit
gates, validation-stage-only status, and JSON/Markdown CLI output with
`--require-pass` failure.

The castle owner records summary tests are
`captures\current\castle-owner-records-summary-tests-current.md`. They pass repo-only
and cover active, retired, nonempty, interesting, and flag-value record
classification plus no-active, require-interesting, forbid-interesting, and
truncated raw-dump fail-closed paths.

The castle overview gate tests are
`captures\current\castle-overview-gate-tests-current.md`. They pass repo-only and
cover overview readiness, AV rows, overview post-draw/surface size, expected
commands, centered geometry, barracks baseline regressions, and JSON/Markdown
CLI output with `--require-pass` failure.

The castle overview hitbox summary tests are
`captures\current\castle-overview-hitbox-summary-tests-current.md`. They pass
repo-only and cover focused displayed/native hit parsing, descriptor and
click-gate parsing, callback suppression/callback entry, AV rows, ready size,
and required CLI flag failures.

The castle overview hitmap summary tests are
`captures\current\castle-overview-hitmap-summary-tests-current.md`. They pass
repo-only and cover raw command IDs, presence/absence, counts, bounding boxes,
centered displayed coordinates, required present/absent CLI flags, and wrong
raw-dimension handling.

The castle overview multihit summary tests are
`captures\current\castle-overview-multihit-summary-tests-current.md`. They pass
repo-only and cover target-set rows, hit-test results, descriptor and
click-gate parsing, target-done completion rows, callback entry, AV rows,
ready size, and required CLI flag failures including completion mismatch.

The current explicit promotion decision is also repo-only:

```powershell
& $Py .\tools\castle_overview_promotion_decision.py `
  --write-json .\captures\current\castle-overview-promotion-decision-current.json `
  --write-markdown .\captures\current\castle-overview-promotion-decision-current.md `
  --require-pass
```

Current output is
`captures\current\castle-overview-promotion-decision-current.md`. It records
`decision=defer_stable_promotion` and `stable_stage_should_change=False`.
It also records the focused displayed-wrapper proof, visible target completion
proof, and dormant target completion proof before deferring promotion. Reason:
the evidence matrix passes, but the current proof is CDB/proxy-only and
manual/visible DirectInput validation has not been supplied. The default stable
HD map stage stays
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`;
castle overview wrappers stay scoped to `castlecenter-all`.

The castle overview promotion decision tests are
`captures\current\castle-overview-promotion-decision-tests-current.md`. They pass
repo-only and cover the default defer decision, the failing-matrix
fail-closed path, missing focused/multihit proof, manual-proof promotion
eligibility, explicit CDB-only override promotion eligibility, and
JSON/Markdown CLI output with `--require-pass` failure.

The stable stage guard can be refreshed directly with:

```powershell
& $Py .\tools\stable_stage_guard.py --require-pass
```

After a full castle overview CDB surface-dump run, gate it with:

```powershell
& $Py .\tools\castle_overview_gate.py `
  .\captures\archive\cdb-surface-dump-YYYYMMDD-HHMMSS `
  --barracks-run .\captures\archive\cdb-surface-dump-20260512-082418 `
  --require-pass `
  --write-json .\captures\current\castle-overview-gate-current.json `
  --write-markdown .\captures\current\castle-overview-gate-current.md
```

That gate intentionally requires the descriptor catalog, no AV rows, an 800x600
surface, centered 800x600 geometry, and the optional barracks no-echo baseline
when `--barracks-run` is supplied. Current passing full-overview catalog and
visual-integrity evidence is `captures\archive\cdb-surface-dump-20260515-105041`;
candidate SHA-256
`1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`, with
`castle-overview-center-present-wrapper` `3/3` and
`castle-overview-centered-input` `2/2` patched. This evidence uses the
native-render-first overview wrapper and the stripe detector in
`tools\castle_overview_gate.py`.

The focused overview hitbox proof is
`captures\archive\cdb-surface-dump-20260515-105411`, summarized by
`tools\castle_overview_hitbox_summary.py --require-displayed-hit`: displayed
coordinate `(371,107)` hits command `0x86` through the binary wrapper, the
stock click gate returns `1`, and no AV rows are present. Keep castle patches
out of the default HD map stage until broader or manual/real overview input
proof is added.

Current broader overview input evidence is
`captures\archive\cdb-surface-dump-20260515-105458`, summarized by
`tools\castle_overview_multihit_summary.py --require-all-targets`. It proves
real hitmap coordinates for commands `0x86`, `0x63`, and `0x87` under the
centered wrapper. The companion hitmap dump
`captures\current\castle-overview-hitmap-current.md` shows `0xFA` through `0xFD` are
absent in the current overview surface, so commands `0x99`, `0x9C`, `0x9F`,
and `0xA6` remain catalog-only until a state exposes those hit IDs.

Dormant descriptor coverage is now documented separately. The owner-record dump
`captures\current\castle-owner-records-current.md` shows the current loaded castles have
zero feature flags, while the explicitly debugger-forced owner-feature run
`captures\archive\cdb-surface-dump-20260513-095443` exposes all raw hit IDs
`0xF8` through `0xFF`. The follow-up multi-hit proof
`captures\archive\cdb-surface-dump-20260515-105557`, summarized by
`captures\current\castle-overview-flags1f-multihit-current.md`, proves commands
`0x99`, `0x9C`, `0x9F`, and `0xA6` through real hitmap coordinates and stock
click gate `1` under the centered wrapper. This is still CDB/proxy evidence,
not manual DirectInput proof or stable-stage promotion.

## Use With Obsidian

Open this repository folder as an Obsidian vault. Obsidian will understand the
`[[wikilinks]]` used in `wiki/`. The repository intentionally avoids custom
plugins and generated app state. You may add an `.obsidian/` folder locally;
workspace/cache files are ignored by `.gitignore`.

## Current Limitations

- Search is simple keyword ranking, not semantic search.
- The linter is conservative and not a full markdown parser.
- No OCR, PDF extraction, vector search, database, or web app is included.
- Source ingest quality depends on the LLM reading the source carefully.
- Empty directories contain `.gitkeep` placeholders so the scaffold is visible
  to Git.

## First Source-Ingest Prompt

After dropping a file into `raw/inbox/`, use:

```text
Ingest raw/inbox/<file-name> into the LLM Wiki. Follow AGENTS.md exactly. Create
a source summary and any useful entity, concept, synthesis, question, or
comparison pages. Use Obsidian wikilinks. Cite every sourced claim with the raw
path or source page. Distinguish sourced facts, interpretation, uncertainty,
contradictions, and open questions. Append an entry to wiki/log.md. Run
python tools/wiki_lint.py. Do not move or modify the raw source until I approve.
```

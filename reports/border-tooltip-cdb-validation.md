# Border Frame And Bottom Tooltip CDB Validation Plan

Date: 2026-04-30

Scope: CDB-only investigation for recovering the Clash95 HD gameplay border
frame and bottom tooltip/status area. Do not mutate `raw/`,
`C:\Clash\clash95.exe`, proprietary assets, saves, or generated executables in
the repository.

## Current UI Screenshot Artifact

This report is planning work, so it reuses the latest relevant UI capture as the
required current UI screenshot artifact:

![current UI screenshot](C:/Users/andrz/OneDrive/Pulpit/git/clash-hd/captures/map-minimapaction-minimapright-dynvswitch-v2-frame-20260424.png)

The freshest CDB/no-popup surface proof for the current HD stage is:

![current no-popup surface](C:/Users/andrz/OneDrive/Pulpit/git/clash-hd/captures/cdb-surface-dump-20260429-140916/surface.png)

## Minimum Runnable Runbook

Use this CDB-only sequence first.

```powershell
$PY = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_cdb_surface_dump.ps1 `
  -UseDdrawProxy `
  -NoSkipStartAnims `
  -RequireGameplay `
  -Stage $Stage `
  -CandidateDir C:\ClashTests\cdb-border-tooltip `
  -RunSeconds 150

$Run = Get-ChildItem .\captures -Directory -Filter 'cdb-surface-dump-*' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
$Png = Join-Path $Run.FullName 'surface.png'

& $PY tools\right_bottom_ui_bounds.py $Png `
  --region frame_left:0,0,31,599 `
  --region frame_top:0,0,799,15 `
  --region right_frame_under_minimap:586,230,799,527 `
  --region bottom_tooltip:32,528,585,599 `
  --region bottom_right_panel:586,528,799,599 `
  --region bottom_frame:0,580,799,599 `
  --only-custom-regions `
  --write-json (Join-Path $Run.FullName 'border-tooltip-bounds.json')

& $PY tools\map_tile_coverage.py $Png `
  --logical-width 800 `
  --logical-height 600 `
  --require-gameplay

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_cdb_right_bottom_ui_probe.ps1 `
  -Stage $Stage `
  -CandidateDir C:\ClashTests\cdb-right-bottom-ui `
  -RunSeconds 150
```

Expected output from the first command includes `RUN-SUMMARY.md` with an
embedded `surface.png`; that PNG is the required current UI screenshot artifact
for the task report. Expected output from the final command includes
`right-bottom-ui-summary.json` with `RBUI_*` marker counts.

## Existing Evidence And Harnesses

- `run_cdb_surface_dump.ps1` is the best base harness. It launches x86 CDB on a
  hidden desktop, optionally builds the local DirectDraw surface-dump proxy,
  dumps `dword_5202E0`, reconstructs `surface.png`, runs
  `tools\map_tile_coverage.py`, runs `tools\visibility_coverage.py`, writes
  `summary.json`, and embeds the reconstructed PNG in `RUN-SUMMARY.md`.
- `run_cdb_surface_dump.ps1 -ExtraProbeTemplate <file.cdb>` can splice an
  extra CDB probe into the route. The extra probe must not contain a standalone
  `g` command. This is the right extension point for border/tooltip probes.
- `run_cdb_right_bottom_ui_probe.ps1` already wraps the hidden-desktop surface
  dump harness with `probes/cdb/ui/clash95_right_bottom_ui_extra.cdb`, counts `RBUI_*`
  markers, and writes `right-bottom-ui-summary.json` / `.txt` into the run
  folder. This is already CDB-only and should replace older route experiments.
- `probes/cdb/ui/clash95_right_bottom_ui_probe.cdb` and
  `probes/cdb/ui/clash95_right_bottom_ui_extra.cdb` identify likely gameplay UI paths:
  - `004347A0`: action/right-side panel draw candidate.
  - `00434E20`: 4x3 action icon grid draw candidate.
  - `00435280`: selected-building/status draw candidate; likely relevant to
    tooltip/status recovery.
  - `00435500`: `UI_DrawActionBox` candidate.
  - `00435580`, `004355FA`, `0043560E`, `00435620`: action-grid hit-test and
    dispatch candidates.
  - `00419DC0`: descriptor/viewport switch helper candidate.
  - `00460D80`: viewport switch evidence point.
  - `004024E0`: copy/present primitive. Filter by caller and rectangle
    intersection rather than arming it hot from process start.
- `probes/cdb/map/clash95_map_topband_probe.cdb`, `tools\topband_probe_summary.py`, and
  `tools\topband_image_summary.py` are a proven pattern for finding stale UI
  bands: sample the surface, log copy rectangles that intersect a target band,
  then compare whole-image region coverage.
- `tools\right_bottom_ui_bounds.py` already measures logical 800x600 regions
  without launching the game. It supports custom regions, nonblack/black
  percentages, black-component bounds, and JSON output.

## Current Region Measurements

These non-destructive measurements were run against existing captures.

Color UI capture:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  tools\right_bottom_ui_bounds.py `
  captures\map-minimapaction-minimapright-dynvswitch-v2-frame-20260424.png `
  --region frame_left:0,0,31,599 `
  --region frame_top:0,0,799,15 `
  --region map_native_border_bottom:0,464,799,527 `
  --region bottom_tooltip_candidate:32,528,585,599 `
  --region bottom_right_panel_candidate:586,528,799,599 `
  --only-custom-regions
```

Observed highlights:

- `bottom_tooltip_candidate`: `89.761%` nonblack, with a black strip touching
  the bottom edge.
- `bottom_right_panel_candidate`: `10.704%` nonblack and a large black
  component, so the right-bottom panel/footer region is still visibly empty or
  stale in this reference frame.

CDB/no-popup surface:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  tools\right_bottom_ui_bounds.py `
  captures\cdb-surface-dump-20260429-140916\surface.png `
  --region frame_left:0,0,31,599 `
  --region frame_top:0,0,799,15 `
  --region map_native_border_bottom:0,464,799,527 `
  --region bottom_tooltip_candidate:32,528,585,599 `
  --region bottom_right_panel_candidate:586,528,799,599 `
  --only-custom-regions
```

Observed highlights:

- `bottom_tooltip_candidate`: `66.451%` nonblack, with a large black component
  touching the bottom-right edge.
- `bottom_right_panel_candidate`: `21.43%` nonblack and mostly black.
- `map_tile_coverage.py --require-gameplay` still classifies this surface as a
  likely gameplay frame, so the missing lower UI is not just a menu/intro
  capture artifact.

## CDB-Only Validation Plan

### 1. Establish A Fresh Current HD Baseline

Run the current HD stage through the hidden-desktop surface dump path:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_cdb_surface_dump.ps1 `
  -UseDdrawProxy `
  -NoSkipStartAnims `
  -RequireGameplay `
  -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch `
  -CandidateDir C:\ClashTests\cdb-border-tooltip `
  -RunSeconds 150
```

Required artifacts:

- `captures\cdb-surface-dump-*\surface.png`
- `captures\cdb-surface-dump-*\summary.json`
- `captures\cdb-surface-dump-*\map-tile-coverage.json`
- `captures\cdb-surface-dump-*\visibility-coverage-summary.json`
- `captures\cdb-surface-dump-*\RUN-SUMMARY.md`

The `surface.png` from this run is the screenshot artifact for the task report.

### 2. Prove Existing Right/Bottom UI Draw Paths

Run the existing CDB-only right-bottom UI wrapper:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_cdb_right_bottom_ui_probe.ps1 `
  -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch `
  -CandidateDir C:\ClashTests\cdb-right-bottom-ui `
  -RunSeconds 150
```

Expected success shape:

- Surface dump passes.
- `RBUI_PLAYGAME` / `SURFDUMP_READY` are present in the log.
- At least one `RBUI_PANEL_DRAW`, `RBUI_GRID_DRAW`, `RBUI_STATUS_DRAW`, or
  `RBUI_ACTION_BOX` marker is present.
- No `AV_RBUI` row.
- `right-bottom-ui-summary.json` records the candidate SHA, stage, PNG path,
  log path, and marker counts.

This tells us whether the right-bottom/status code runs on the current route.
If no `RBUI_*` markers appear, the recovery target is probably not being reached
after route injection and the next step is a CDB route/hover-state issue rather
than a patching issue.

### 3. Add A Dedicated Border/Tooltip Extra Probe

Create a new extra probe template, for example
`probes/cdb/ui/clash95_border_tooltip_extra.cdb`, that follows the existing
`probes/cdb/ui/clash95_right_bottom_ui_extra.cdb` rules:

- no standalone `g`;
- late-arm only after gameplay, using the surface-dump route flag;
- log `dword_5202E0` size and base;
- do not arm hot `004024E0` from process start.

Suggested markers:

- `BORDER_PANEL_DRAW` at `004347A0`.
- `TOOLTIP_STATUS_DRAW` at `00435280`.
- `TOOLTIP_ACTION_BOX` at `00435500`.
- `BORDER_DESC_SWITCH` at `00419DC0`.
- `BORDER_VIEWPORT_SWITCH` at `00460D80`.
- `BORDER_PRESENT` / `TOOLTIP_PRESENT` at `004024E0`, but only when the source
  or destination rectangle intersects one of these logical regions:
  - `frame_left`: `(0,0)-(31,599)`
  - `frame_top`: `(0,0)-(799,15)`
  - `right_frame_under_minimap`: `(586,230)-(799,527)`
  - `bottom_tooltip`: `(32,528)-(585,599)`
  - `bottom_right_panel`: `(586,528)-(799,599)`
  - `bottom_frame`: `(0,580)-(799,599)`

The key unknown is whether the tooltip/status frame is drawn into the widened
map surface but not presented, or whether it is still drawn at native 640x480
coordinates and needs layout constants moved.

### 4. Add A Log Parser And Image Gate

New helper recommended: `tools\border_tooltip_summary.py`.

Inputs:

- CDB log path.
- `surface.png` path.
- optional `right-bottom-ui-summary.json`.
- optional output JSON/Markdown path.

Parser duties:

- Count `BORDER_*`, `TOOLTIP_*`, and `RBUI_*` rows.
- Extract `004024E0` present/copy rectangles and classify whether each
  intersects the target regions above.
- Flag native-only rectangles, especially right/bottom edges ending at `639`,
  `607`, `479`, or `463`.
- Record the final surface size and require `800x600`.
- Record AV rows.

Image duties can reuse or wrap `tools\right_bottom_ui_bounds.py`:

- Measure the same target regions.
- Compare pre-patch and post-patch region nonblack percentages.
- Track largest black component percent for bottom tooltip and bottom-right
  panel regions.
- Treat grayscale proxy PNGs as shape/coverage proof, not authentic color.

Suggested pass criteria for a recovery candidate:

- `surface.png` exists and is embedded in the run summary.
- `map_tile_coverage.py --require-gameplay` passes.
- `BORDER_PRESENT` or `TOOLTIP_PRESENT` rows intersect the intended bottom and
  right-side regions.
- No present rows for recovered UI are clipped to native-only right/bottom
  edges.
- `bottom_tooltip` and `bottom_right_panel` nonblack percentages improve
  materially from the current CDB baseline.
- No `AV_*` markers and no CDB timeout except intentional liveness timeouts.

### 5. Run Image-Side Measurements

After any fresh run, measure border and tooltip regions:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  tools\right_bottom_ui_bounds.py `
  captures\cdb-surface-dump-YYYYMMDD-HHMMSS\surface.png `
  --region frame_left:0,0,31,599 `
  --region frame_top:0,0,799,15 `
  --region right_frame_under_minimap:586,230,799,527 `
  --region bottom_tooltip:32,528,585,599 `
  --region bottom_right_panel:586,528,799,599 `
  --region bottom_frame:0,580,799,599 `
  --only-custom-regions `
  --write-json captures\cdb-surface-dump-YYYYMMDD-HHMMSS\border-tooltip-bounds.json
```

Also keep the standard gameplay map gate:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  tools\map_tile_coverage.py `
  captures\cdb-surface-dump-YYYYMMDD-HHMMSS\surface.png `
  --logical-width 800 `
  --logical-height 600 `
  --require-gameplay
```

### 6. Controlled Tooltip Trigger States

The tooltip may only draw after a hover-state or selection-state update. If the
plain route does not show tooltip draws, add debugger-only hover variants:

- neutral map hover: set internal mouse to a safe map point, no buttons;
- action hover: set internal mouse to the action grid or action box area;
- lower UI hover: set internal mouse into the bottom tooltip/status candidate
  region;
- selected unit/building state: use the existing load-slot route and current
  selected-object globals before changing patch bytes.

Use the same mouse global style already present in CDB probes:

- `00544cfc`: logical x shifted by `0054512c`;
- `00544d00`: logical y shifted by `0054512c`;
- `005451c0`: left-button byte;
- `005451c8`: right-button byte.

Hold any forced state for several redraw/poll cycles before dumping the
surface. Treat this as debugger evidence only, not manual-input proof.

## Patch Decision Tree

Use the CDB rows before changing bytes:

- If border/tooltip draw functions run and write to `dword_5202E0`, but
  `004024E0` presents only native rectangles, patch present/copy bounds.
- If draw functions run but use old x/y anchors, patch layout constants only
  for the specific function that draws the target UI, not global `640`/`480`
  constants.
- If draw functions do not run, investigate selection/hover/menu-state routing
  before patching layout.
- If the image is blank but CDB says the region is fog or map-state related,
  do not patch UI. Use `visibility_coverage.py` only for map cells; UI
  regions need their own presenter/draw evidence.

## Next Concrete Engineering Task

Implement `tools\border_tooltip_summary.py` plus
`probes/cdb/ui/clash95_border_tooltip_extra.cdb`, then run them through
`run_cdb_surface_dump.ps1 -ExtraProbeTemplate` against the current HD stage.
The resulting `RUN-SUMMARY.md` must embed the fresh `surface.png` screenshot
artifact and record whether the border/tooltip rows are drawn, clipped, or not
reached.

## 2026-04-30 Probe Update

Implemented `probes/cdb/ui/clash95_border_tooltip_extra.cdb` and
`tools\border_tooltip_summary.py`.

Runtime result:

- `captures\cdb-surface-dump-20260430-111545` reached `SURFDUMP_PLAYGAME` and
  `BORDER_FULLREDRAW_ENTER` under the hidden-desktop CDB route.
- The redraw entry reported `d5202e0` as an 800x600 surface and
  `d526990=00000000`.
- The run timed out before `SURFDUMP_READY` with no game AV. The first attempt
  also showed that the `004024E0` present hook must be null-safe; the current
  probe keeps that hook disabled by default and late-enables only filtered text
  helper breakpoints.
- A fresh no-extra baseline surface dump passed at
  `captures\cdb-surface-dump-20260430-114459` and produced the current UI
  screenshot artifact:
  `captures\cdb-surface-dump-20260430-114459\surface.png`.

Next concrete engineering task:

Trace writes/callers for `dword_526990` and the `sub_418700` callback branch
with one-shot CDB breakpoints. Avoid hot present hooks until the callback/state
owner is known.

## 2026-04-30 dword_526990 Probe Update

Implemented and ran the one-shot branch/write probe:

- Probe template:
  `probes/cdb/castle/clash95_d526990_extra.cdb`
- Parser:
  `tools\d526990_summary.py`
- Successful run:
  `captures\cdb-surface-dump-20260430-115605`
- Screenshot artifact:
  `captures\cdb-surface-dump-20260430-115605\surface.png`

Observed rows:

- `D526990_FULLREDRAW_ENTER`: 3
- `D526990_SECOND_PASS_CHECK`: 3
- `D526990_FALLBACK_LOOP_START`: 3
- `D526990_FALLBACK_LOOP_DONE`: 3
- `D526990_CALLBACK_TEST`: 3
- `D526990_CALLBACK_CALL`: 0
- `D526990_WRITE`: 0

Conclusion:

`dword_526990` is consistently null in this loaded gameplay route, and
`dword_526994` is also null, so `sub_418700` takes the fallback tile-loop path
and then skips the optional callback. The next recovery step is not a present
rectangle patch; it is identifying the static owner/setup path that writes
`00526990` or `00526994`.

## 2026-04-30 Static Owner Follow-Up

The static xref pass found `00526990` only in the optional `sub_418700`
callback branch. It did find a `00526994` owner cluster at `00423760`,
`00423B00`, and `00423B40`, all of which bracket calls to `sub_418700` while
setting or clearing the flag.

Added `probes/cdb/castle/clash95_d526994_setup_extra.cdb` and the minimal
`probes/cdb/castle/clash95_d526994_setup_min_extra.cdb`. Both are CDB-only extra probes for the
hidden-desktop surface-dump harness. `tools\d526990_summary.py` now parses the
new `D526994_*` marker rows.

Runtime attempts with those probes timed out before `SURFDUMP_MAIN_HIT`, so the
current validation blocker is startup/menu-route progress on the hidden
desktop, not a disproven UI owner. Next proof should instrument the
startup/AVI/menu route enough to learn why these extra probes fail before
gameplay.

## 2026-04-30 Startup-Stall And Setup Rerun

Added `probes/cdb/startup/clash95_startup_stall_d526994_extra.cdb` and
`tools\startup_stall_summary.py`.

`captures\cdb-surface-dump-20260430-142129` localizes the full-startup hidden
desktop stall: the run reaches the logo `Video_Avi_playIn` path and logs
`STARTUP_VIDEO_AFTER_MODE_BEGIN`, then never returns to the menu route. No AV
is observed.

`captures\cdb-surface-dump-20260430-145646` uses the harness
`-FastForwardStartAnims` mode and passes. It reaches `SURFDUMP_MAIN_HIT`,
`SURFDUMP_PLAYGAME`, and `SURFDUMP_READY`, dumps a fresh 800x600 surface, and
logs 3 `D526994_MIN_CALLBACK_TEST` rows. The callback and flag remain zero,
and none of the static owner entries (`00423760`, `00423B00`, `00423B40`) fire.

Conclusion: the owner cluster is not reached by the current load-slot route.
The next probe should statically find callers of those owner functions and then
drive or force the game state that should invoke one of them.

## 2026-04-30 dword_526994 Owner Route Trigger

Added a CDB-only owner-route probe:

- `probes/cdb/castle/clash95_d526994_owner_route_extra.cdb`
- `tools\d526994_owner_route_summary.py`

Static caller results:

- `00423760` has one direct caller at `004087C8`.
- `00423B00` has one direct caller at `0040A5EE`.
- `00423B40` has one direct caller at `0040A51A`.
- `00423B00` and `00423B40` are branches inside `sub_40A500`; the initial
  `PlayGame` setup reaches `sub_40A500` at `0040B7B3`.

Runtime result:

- Run folder: `captures\cdb-surface-dump-20260430-224749`
- Screenshot artifact: `captures\cdb-surface-dump-20260430-224749\surface.png`
- Parser: `owner_count=1 route_count=8 ready=True av_count=0`

The probe applied a debugger-only state nudge before the natural `0040B7B3`
call by setting `dword_511B58=-1` and `dword_514194=0`. That drove the real
game dispatcher through:

`PlayGame -> sub_40A500 -> 0040A51A -> sub_423B40`

Observed owner row:

`D526994_OWNER_423B40_ENTRY ret=0040a51f callback=00000000 flag526994=00000000 selected=-1 prior=0`

Conclusion:

The `00526994` owner cluster is reachable under CDB, but this route is the
clear-highlight owner and still leaves the `dword_526990` callback null. The
next border/tooltip recovery step should trace `sub_40A400`, `sub_419D80`, and
`dword_511D40` descriptor/bounds setup rather than forcing `00526994` as a
patch.

## 2026-05-06 dword_511D40 Descriptor Trace

Added the CDB-only descriptor probe and summary parser:

- `probes/cdb/ui/clash95_descriptor_trace_extra.cdb`
- `tools\descriptor_trace_summary.py`

Run folder:

- `captures\cdb-surface-dump-20260506-092608`
- Screenshot artifact:
  `captures\cdb-surface-dump-20260506-092608\surface.png`

Summary parser result:

`ready=True av_count=0 scanned_511d40=6 drawn_511d40=6 skipped_511d40=0`

Important rows:

- `DESC_40A400_ENTRY` reported `render=0a07edb0`,
  `map_surface=0a07edb0`, `sz=(800,600)`, and the first `dword_511D40`
  descriptor at `(416,400)`.
- `DESC_419D80_ENTRY` reached the descriptor scan with the same 800x600 render
  surface.
- Six `DESC_SCAN` and six `DESC_DRAW` rows fired for the native 3x2 cluster:
  `(416,400)`, `(480,400)`, `(544,400)`, `(416,432)`, `(480,432)`,
  `(544,432)`.
- Six `DESC_DRAWCALL_4191F0_PRESENT1` rows confirmed the descriptor callback
  reached its first present point with the same destination coordinates.
- No `DESC_SKIP_X640` rows fired.

Conclusion:

`dword_511D40` is not currently the missing HD border/tooltip owner. It is a
native action-button descriptor list that draws successfully on the 800x600 map
surface. The missing lower-right UI should next be investigated through
action/status and unit-info pane functions, especially `004347A0`, `00434E20`,
`00435280`, `00435500`, and `UI_DrawUnitInfoPane` at `00419F70`.

## 2026-05-06 Hover/Selection UI Probe

Added:

- `probes/cdb/ui/clash95_hover_selection_ui_extra.cdb`
- `tools\hover_selection_ui_summary.py`

Clean harness ride:

- `captures\cdb-surface-dump-20260506-093846` passed and produced a normal
  800x600 screenshot, but its hover setter was replaced by the harness redraw
  breakpoint at `00406FA0`.

Corrected forced-hover runs:

- The setter moved to `0040AE11`, immediately before `sub_406FA0`.
- Runs through `captures\cdb-surface-dump-20260506-100922` reached
  `SURFDUMP_READY` and logged forced hover states.

Final parsed result:

`ready=True av_count=0 force_states=4 entries=0 presents=0 native_clip_rows=0`

Observed final forced states:

- `map_hover` at `(320,300)`
- `action_grid_hover` at `(474,114)`
- `action_box_hover` at `(320,388)`
- `safe_center_hold` at `(320,300)`

All forced rows showed `d532218=00000000`, `selected=0`, `action=0`, and
`d532220=0`. No target rows fired for `004347A0`, `00434E20`, `00435280`,
`00435500`, `00419F70`, text, or filtered presents.

Negative mouse evidence:

The synthetic hover sequence drives scroll from `(10,17)` to `(35,51)` before
the dump, causing `map_tile_coverage.py` to reject the screenshot. Treat these
runs as route/scroll evidence, not as clean map-rendering baselines.

Conclusion:

The right-bottom/bottom-tooltip target functions are skipped by state/route in
the current load-slot path. There is still no evidence that they draw and are
then clipped or overwritten. The next probe should avoid writing mouse globals
and instead trace what initializes `dword_532218` and enters the action-panel
owner path.

## 2026-05-06 Passive Action Panel Route Probe

Added:

- `probes/cdb/castle/clash95_action_panel_route_extra.cdb`
- `tools\action_panel_route_summary.py`

The probe is passive with respect to mouse state. It watches
`PlayGame -> 40A400/40A500`, the `004338E0` castle/action UI caller, the
`00433914` call to `sub_435BC0`, the action-panel owner/poll/hit-test/draw
cluster, and write watchpoints for `dword_532218` and `dword_5322C8`.

Static correction:

- CDB disassembly showed the caller function starts at `004338E0`.
- The direct call to `sub_435BC0` is at `00433914`.

Final corrected run:

- `captures\cdb-surface-dump-20260506-102113`
- Screenshot artifact:
  `captures\cdb-surface-dump-20260506-102113\surface.png`

Parser result:

`ready=True av_count=0 owner_rows=0 panel_rows=0 draw_rows=0 nonzero_owner_rows=0`

Observed route:

- `SURFDUMP_PLAYGAME` reached a 100x100 map at scroll `(10,17)`.
- `APROUTE_PLAYGAME_SETUP_40A400`, `APROUTE_40A400_ENTRY`,
  `APROUTE_PLAYGAME_CALL_40A500`, and `APROUTE_40A500_ENTRY` fired.
- Those rows reported `selected=-1`, `prior=-1`, `d532218=00000000`, and
  `d5322c8=0`.
- No `004338E0`, `00433914`, `sub_435BC0`, `sub_435A00`, `sub_435AC0`,
  `UI_GetGridIndexFromMouse`, action/status draw, or write-watchpoint rows
  fired.

Image-side measurement:

- `map_tile_coverage.py` classified the frame as likely gameplay.
- The visibility gate explained all 13 blank active map cells as
  `visibility_zero`.
- The bottom-right panel region remains mostly black (`21.43%` nonblack),
  so the visual symptom remains, but this run does not prove an action/status
  anchor or clipping failure.

Conclusion:

The normal hidden-desktop load-slot route does not enter the right-bottom
action/status owner path. The next proof should be a controlled non-mouse state
route: nudge selected/prior or a building/castle owner flag enough to drive
`004338E0 -> 00433914 -> sub_435BC0`, while rejecting the run if mouse globals
or map scroll move.

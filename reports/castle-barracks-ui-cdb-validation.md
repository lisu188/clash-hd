# Castle Barracks UI CDB Validation

## Evidence Run

- Run: `captures\cdb-surface-dump-20260511-084202`
- Harness: `run_cdb_surface_dump.ps1`
- Extra probe: `probes/cdb/castle/clash95_castle_barracks_ui_extra.cdb`
- Candidate: `C:\ClashTests\cdb-castle-barracks-ui\clash95_hd_surfdump_20260511_084202.exe`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Surface: `800x600`
- Screenshot: `captures\cdb-surface-dump-20260511-084202\surface.png`

## Findings

- The owner setup globals were installed for the castle action route:
  `dword_532150`, `dword_53214C`, and `dword_532154`.
- The route reached `00433914 -> 00435BC0`, then wrote `dword_532218`.
- The castle/barracks action-panel draw functions executed:
  `004347A0` detail panel, `00434E20` 12-slot grid,
  `00435280` status draw, and `00435500` bottom action box.
- The selected addon/building list was logged as
  `(0,1,3,16,17,-1,-1,-1,-1,-1,-1,-1)` with selected index `0` and selected
  addon id `0`.
- The run had no access-violation rows and reached `SURFDUMP_READY`.

## Current Visual Result

- Full screenshot:
  `captures\cdb-surface-dump-20260511-084202\surface.png`
- Right panel crop:
  `captures\cdb-surface-dump-20260511-084202\castle-barracks-right-panel.png`
- Bottom action-box crop:
  `captures\cdb-surface-dump-20260511-084202\castle-barracks-action-box.png`
- Grid/detail crop:
  `captures\cdb-surface-dump-20260511-084202\castle-barracks-grid-area.png`

`tools\right_bottom_ui_bounds.py` reports the right-side and bottom-right
regions still contain large black components. The most important runtime row is:

`APBARRACKS_ACTION_BOX_435500 ... render=0051d4c0 map_surface=0a07ed90 scratch=0051d4c0 scratch_sz=(800,600) scratch_base=00000000 map_base=0a320030`

Interpretation: the barracks/action UI code is reachable and draws, but part of
the bottom action-box path still switches to the legacy/scratch render target.
The next patch target should be render-target/copyback recovery around
`00435500` and the later copyback/restore sequence, not more generic map-loop
widening.

## Validation Commands

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_cdb_surface_dump.ps1 `
  -UseDdrawProxy `
  -FastForwardStartAnims `
  -SkipMapValidation `
  -ExtraProbeTemplate .\probes/cdb/castle/clash95_castle_barracks_ui_extra.cdb `
  -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch `
  -CandidateDir C:\ClashTests\cdb-castle-barracks-ui `
  -RunSeconds 120
```

```powershell
python tools\castle_barracks_ui_summary.py `
  captures\cdb-surface-dump-20260511-084202\cdb-surface-dump.log `
  --require-ready `
  --require-panel
```

```powershell
python tools\right_bottom_ui_bounds.py `
  captures\cdb-surface-dump-20260511-084202\surface.png
```

## Selected-Addon Copyback Trace

- Run: `captures\cdb-surface-dump-20260511-134947`
- Extra probe: `probes/cdb/castle/clash95_castle_barracks_select_extra.cdb`
- Candidate SHA-256:
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Result: hidden-desktop CDB passed, no AV rows, `SURFDUMP_READY` reached,
  and selected addon id `1` was active through panel, grid, status, and action
  box draw rows.
- Screenshot artifacts:
  `captures\cdb-surface-dump-20260511-134947\surface.png`,
  `captures\cdb-surface-dump-20260511-134947\castle-barracks-top-panel.png`,
  `captures\cdb-surface-dump-20260511-134947\castle-barracks-selected-card.png`,
  and
  `captures\cdb-surface-dump-20260511-134947\castle-barracks-bottom-actions.png`.

Key copyback observation:

`APBARRACKS_ACTION_BOX_435500 ... selected_index=1 selected_addon=1 render=0051d4c0 map_surface=0a07ed90 ...`

`APBARRACKS_COPYBACK_AFTER_CALL ... map_samples=(c1,01,01) scratch_samples=(00,66,93)`

Interpretation: selecting a different barracks/addon entry does not remove the
scratch/map split. The next debugger-only proof should manually copy the
action-box rectangle from the `0051D4C0` scratch/render source into
`dword_5202E0` at `00435DA5`, then compare the new surface and crops.

## Centered Presentation Patch

- CDB-only proof run: `captures\cdb-surface-dump-20260511-141143`
- Patch-stage proof run: `captures\cdb-surface-dump-20260511-142304`
- New patch group: `castle-ui-center-present`
- New stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter`
- Result:
  the patch-stage proof passed with no debugger-side `APBARRACKS_CENTER_*`
  markers, no AV rows, `SURFDUMP_READY`, and selected addon id `1`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-142304\surface.png`

The stage visually centers the native 640x480 castle/barracks UI layer at
`(80,60)` inside the 800x600 surface by hooking `00435DA5` and routing through
DGROUP cave `0051316F`. This is presentation-only for now; the next validation
target is hitbox and mouse-coordinate alignment for the centered screen.

## Centered Hitbox Transform

- Run: `captures\cdb-surface-dump-20260511-143741`
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`
- Candidate SHA-256:
  `BEC4674A98060928337F05CB967AEDBD2A800905389DBBE4990CF771C6DF19C8`
- Screenshot:
  `captures\cdb-surface-dump-20260511-143741\surface.png`
- Parser:
  `ready=True panel=True action_box=True av_count=0 last_selected_addon=1`
- Patch byte report:
  `126 patched, 0 original, 0 unexpected`, with
  `castle-ui-centered-input: 6/6 patched`.

The new patch group `castle-ui-centered-input` wraps only the castle/barracks
owner-poll and descriptor-hit-test path. While those routines run, the patch
temporarily maps centered screen coordinates back to native castle UI
coordinates by subtracting `(80,60)` from the logical mouse globals, scaled by
`byte_54512C`; it then restores the globals before returning. This keeps the
centered visual composition stable and avoids shifting descriptor draw data.

Remaining proof: add a CDB hitbox probe that forces the mouse over a known
centered barracks grid/action target and requires the matching hover/selection
marker. The current run proves no-crash behavior, byte correctness, and an
unchanged centered screenshot.

## Centered Grid Hitbox Proof

- Run: `captures\cdb-surface-dump-20260511-145141`
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`
- Screenshot:
  `captures\cdb-surface-dump-20260511-145141\surface.png`
- Parser:
  `ready=True grid_hit_ok=True last_grid_entry=[450, 73] last_grid_result=0 av_count=0`
- Patch byte report:
  `128 patched, 0 original, 0 unexpected`, with
  `castle-ui-centered-input: 8/8 patched`.

The focused CDB probe forced the displayed centered grid coordinate
`(530,133)`. The owner-poll wrapper logged native `(450,73)`, then the new
`00435A17 -> 0051328A` wrapper passed that same native coordinate into
`UI_GetGridIndexFromMouse` (`00435580`). The helper returned cell `0`, matching
the expected top-left barracks grid cell. The exact proof row is:

`APBARRACKS_HITBOX_GRID_RESULT result=0 expected=0 mouse=(450,73)`

The probe arms loop exit after the successful grid result, so this run is a
cleaner hitbox proof than the earlier `20260511-144934` exploratory run.

## Centered Raw Click-Gate Hitbox Proof

- Run: `captures\cdb-surface-dump-20260511-150643`
- Extra probe: `probes/cdb/castle/clash95_castle_barracks_click_extra.cdb`
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`
- Screenshot:
  `captures\cdb-surface-dump-20260511-150643\surface.png`
- Parser:
  `ready=True grid_hit_ok=True last_grid_entry=[450, 73] last_grid_result=0 raw_gate_ok=True forced_gate_count=0 selection_updates=0 av_count=0`

The probe forces the centered click state at displayed coordinate `(530,133)`,
but does not rewrite `eax` at `00435A0E`. The raw click gate passed:

`APBARRACKS_HITBOX_GRID_GATE raw_result=1 forced_result=none mouse=(530,133) click_flag=00000001 button0=0x80`

The patched grid wrapper then translated the same displayed coordinate into
native `(450,73)` for `00435580`, and the helper returned cell `0`:

`APBARRACKS_HITBOX_GRID_RESULT result=0 expected=0 mouse=(450,73)`

This is the current best CDB-only barracks hitbox proof. It is still synthetic
input-state evidence, but it no longer depends on forcing the route branch
after the input gate has run.

## Centered Action Descriptor Proof

- Run: `captures\cdb-surface-dump-20260511-160221`
- Extra probe: `probes/cdb/castle/clash95_castle_barracks_action_click_extra.cdb`
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`
- Screenshot:
  `captures\cdb-surface-dump-20260511-160221\surface.png`
- Parser:
  `ready=True descriptor_click_ok=True action_exit_ok=True failure_exits=0 av_count=0`

The probe targets the centered bottom-left action descriptor at displayed
coordinate `(161,501)`, which maps through the current centered-input patch to
native coordinate `(81,441)`. The descriptor walker identifies `0051519a`,
whose native origin is `(41,425)` and whose click callback is `00435620`.

Proof rows:

`APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1 click_cb=00435620 state=0x01 mouse=(81,441)`

`APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620 desc_xy=(41,425) state=0x01 mouse=(81,441)`

`APBARRACKS_ACTION_CLICK_EXIT_SET pass_index=4 action_state=1 selected_index=0 selected_addon=0 hover_slot=-1`

This proves the centered barracks action descriptor and stock callback path.
The run remains debugger-assisted: earlier passes showed that the
hidden-desktop/proxy input state clears `dword_544D04` before descriptor
`0051519a`, so the passing probe rearms the click byte at `00419C47`, before
the stock `004608F0` click gate reads it. The next step is to preserve or
inject the input state earlier without this descriptor-local rearm.

## Centered Action Descriptor Pre-Gate Refinement

- Run: `captures\cdb-surface-dump-20260511-161212`
- Failed exploratory run:
  `captures\cdb-surface-dump-20260511-160850` timed out when a global
  `00419B80` descriptor-entry breakpoint was installed. That breakpoint is too
  hot during startup/menu routing unless it is late-armed.
- Screenshot:
  `captures\cdb-surface-dump-20260511-161212\surface.png`
- Parser:
  `ready=True descriptor_click_ok=True action_exit_ok=True failure_exits=0 av_count=0`
- Patch byte report:
  `128 patched, 0 original, 0 unexpected`, with
  `castle-ui-center-present: 2/2` and `castle-ui-centered-input: 8/8`.

The passing probe moved the harness click rearm from late gate address
`00419C47` to `00419C28`, after `00419B80` has identified action descriptor
`0051519a` but before stock gate helpers `00460900` and `004608F0` run.

Key rows:

`APBARRACKS_ACTION_WIDGET_REARM_PRE_GATES desc=0051519a reason=action_descriptor_pre_gates click_flag=00000001`

`APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1 click_cb=00435620 state=0x01 mouse=(81,441)`

`APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620 desc_xy=(41,425) state=0x01 mouse=(81,441)`

`APBARRACKS_ACTION_CLICK_EXIT_SET pass_index=4 action_state=1 selected_index=0 selected_addon=0 hover_slot=-1`

Interpretation: the centered UI/input patch is not the source of the action
button failure. The synthetic hidden-desktop/proxy input path can lose
`dword_544D04` while the descriptor list is walked. The smallest stable
CDB-only workaround is to rearm `dword_544D04` only after descriptor identity
is known and before the stock gates run.

## CDB Harness Click Preservation Fix

- Diagnostic run:
  `captures\cdb-surface-dump-20260511-162607`.
- Passing run after harness fix:
  `captures\cdb-surface-dump-20260511-162846`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-162846\surface.png`.
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`.
- Parser:
  `ready=True descriptor_click_ok=True action_exit_ok=True failure_exits=0 clickflag_writes=0 av_count=0`.

The diagnostic probe removed the descriptor-local rearm and showed the target
action descriptor receiving `click_flag=0` and `button0=0x00`. The cause was
the shared surface-dump template breakpoint at `00419B80`, whose post-gameplay
cleanup zeroed `005451C0` and `00544D04` while the barracks descriptor list was
being walked.

The shared template now keeps that cleanup for normal map dumps, but skips it
once an extra UI probe has entered its active `$t18` phase. With that change,
the same no-rearm probe proves the clean centered action path:

`APBARRACKS_ACTION_WIDGET_PRE_GATES desc=0051519a reason=no_rearm_trace click_flag=00000001 button0=0x80 mouse=(81,441)`

`APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1 click_cb=00435620 state=0x01 mouse=(81,441)`

`APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620 desc_xy=(41,425) state=0x01 mouse=(81,441)`

`APBARRACKS_ACTION_CLICK_EXIT_SET pass_index=4 action_state=1 selected_index=0 selected_addon=0 hover_slot=-1`

Interpretation: the centered barracks action descriptor no longer needs a
descriptor-local click rearm inside the CDB harness. This is still synthetic
hidden-desktop input state, but the harness no longer consumes its own click
before the stock gates.

## Centered Second Action Descriptor Proof

- Run:
  `captures\cdb-surface-dump-20260511-163846`.
- Probe:
  `probes/cdb/castle/clash95_castle_barracks_second_action_extra.cdb`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-163846\surface.png`.
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`.
- Parser:
  `ready=True descriptor_click_ok=True action_exit_ok=False failure_exits=0 clickflag_writes=0 av_count=0`.

The probe targets the adjacent bottom action descriptor `005151cf`, whose
native origin is `(156,425)` and click callback is `004356c0`. The centered
display coordinate `(276,501)` maps through the current centered-input patch
to native `(196,441)`.

Key rows:

`APBARRACKS_ACTION_WIDGET_PRE_GATES desc=005151cf reason=no_rearm_trace click_flag=00000001 button0=0x80 mouse=(196,441)`

`APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=005151cf click_gate=1 click_cb=004356c0 state=0x01 mouse=(196,441)`

`APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=005151cf callback=004356c0 desc_xy=(156,425) state=0x01 mouse=(196,441)`

`APBARRACKS_ACTION_CLICK_4356C0_ENTRY desc=005151cf mouse=(196,441) action_state_before=0 selected_index=0 selected_addon=0`

`APBARRACKS_ACTION_CLICK_4356C0_CHECK_RET check_result=0 selected_index=0 selected_addon=0 action_state=0`

Interpretation: the centered input path and stock descriptor gate/callback path
are correct for a second bottom action button. The callback itself then rejects
the current selected addon state (`selected_addon=0`) via `0043E850`, so the
next proof should either select a compatible addon before this click or choose
a different action descriptor whose stock callback produces a visible state
change for the current selected unit.

## Castlecenter-All Stage And Interior Catalog

- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`.
- New catalog probe:
  `probes/cdb/castle/clash95_castle_interior_catalog_extra.cdb`.
- New parsers:
  `tools\castle_interior_catalog_summary.py` and
  `tools\castle_ui_center_geometry.py`.
- Catalog run:
  `captures\cdb-surface-dump-20260511-170708`.
- Catalog screenshot:
  `captures\cdb-surface-dump-20260511-170708\surface.png`.
- Catalog parser:
  `ready=True surface_size=[640, 480] descriptors=7 commands=0x63,0x86,0x87,0x99,0x9C,0x9F,0xA6 av_count=0`.

The catalog run now safely route-invokes the full castle-screen routine
`00422180`, suppresses descriptor callbacks after logging them, and dumps the
surface without continuing into an AV. It found seven reachable command
callbacks from the current save:

| Command | Callback |
| --- | --- |
| `0x63` | `00433C20` |
| `0x86` | `0044FE70` |
| `0x87` | `0042B0A0` |
| `0x99` | `0043DCE0` |
| `0x9C` | `0043D8E0` |
| `0x9F` | `0043DEE0` |
| `0xA6` | `0043DAE0` |

Important result: the catalog finished on a native `640x480` castle-screen
surface, so the full castle overview/interior dispatcher is a separate path
from the already centered barracks/action-panel route. The 800x600 gate fails
for this route by design until the `00422180` / `00422305` / `00422020` castle
surface/present path gets its own narrow centering hook.

## Castlecenter-All Barracks Success-Branch Proof

- Run:
  `captures\cdb-surface-dump-20260511-170759`.
- Probe:
  `probes/cdb/castle/clash95_castle_barracks_second_action_select1_extra.cdb`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-170759\surface.png`.
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`.
- Patch-stage report:
  `128 patched, 0 original, 0 unexpected`; `castle-ui-center-present` is
  `2/2` and `castle-ui-centered-input` is `8/8`.
- Geometry gate:
  `centered_gate=PASS image=800x600 centered_nonblack=74.464% max_margin_nonblack=24.979%`.
- Action parser:
  `ready=True descriptor_click_ok=True action_exit_ok=False success_4356c0_ok=True failure_exits=0 clickflag_writes=0 av_count=0`.

This fresh no-popup CDB run uses the new `castlecenter-all` stage, forces a
compatible barracks selected addon (`selected_index=1`, `selected_addon=1`),
clicks displayed centered coordinate `(276,501)`, maps it to native
`(196,441)`, hits descriptor `005151cf`, and enters stock callback
`004356c0`. The first callback pass reaches
`APBARRACKS_ACTION_CLICK_4356C0_SUCCESS_BRANCH`; the later controlled probe
exit sets action state only to stop the run and dump the frame. This validates
the centered barracks input/presentation path, not yet every full castle
overview descriptor.

## Castlecenter-All No-Echo Barracks Fix

- Run:
  `captures\cdb-surface-dump-20260512-082418`.
- Probe:
  `probes/cdb/castle/clash95_castle_barracks_second_action_select1_extra.cdb`.
- Screenshot:
  `captures\cdb-surface-dump-20260512-082418\surface.png`.
- Candidate SHA-256:
  `4E42D4A3EA61E1DB31007600A8B6515B4803E14CCC07FD2CBF1C2BA838492498`.
- Patch-stage report:
  `129 patched, 0 original, 0 unexpected`; `castle-ui-center-present-wrapper`
  is `3/3` and the current HD map gate passes.
- Geometry gate:
  `centered_gate=PASS image=800x600 centered_nonblack=71.228% max_margin_nonblack=0.0%`.
- Action parser:
  `ready=True descriptor_click_ok=True action_exit_ok=False success_4356c0_ok=False controlled_4356c0_ok=True failure_exits=0 clickflag_writes=0 av_count=0`.

The fix changed the broad castle/barracks visual path from a pre-present copy
to a stock-render-then-center wrapper. The wrapper is used both as the initial
`Render_Present` callback (`00435DAA`) and as the per-frame loop redraw call
(`00435DDE`). That second hook is the important anti-echo piece: wrapping only
the initial present callback produced `captures\cdb-surface-dump-20260512-082001`,
where the screenshot still had meaningful native-origin content in the top and
left margins.

The current screenshot is centered at `(80,60)` with a single unit list/stat
panel. It is still grayscale proxy evidence, not final palette fidelity.

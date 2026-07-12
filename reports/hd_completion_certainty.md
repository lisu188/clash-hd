# HD Completion — Disassembly-Verified Certainty and Procedure

Generated: 2026-06-30

This document records the result of an exhaustive cross-check of the HD mod
against the recovered C decompilation in the companion `clash-disassembly`
repository (`clash95.c`, `docs/SAVE_DAT_FORMAT.md`). It supersedes open
questions in `reports/hd_completion_plan.md`,
`captures/current/right-bottom-blocker-triage-current.md`, and
`reports/battle_ui_completion_plan.md` by answering them from ground truth. All
`clash95.c:NNN` citations are line numbers in that file.

## Certainty statement

After cross-check I am confident the HD mod is mechanically complete and the
only remaining work is producing approved real-input evidence. Specifically:

- Every HD geometry, surface-centering, and coordinate-offset patch is **correct
  against ground truth** (see `reports/disassembly_cross_check_hd_next_steps.md`).
- Per `reports/final_hd_validation_matrix.md`, **every automated gate passes**
  except exactly two rows, both labelled "EXPECTED FAIL until proof":
  1. `battle_visible_input_summary.py --require-click-consumed` (click-consumed `0/3`).
  2. `manual_directinput_checklist.py --require-promotion-ready` (5 targets pending).
- There is **no third blocker**. The two failing rows are the same underlying
  requirement: real DirectInput click consumption captured into the manual proof
  manifest.

So "completing clash-hd" = (a) reach each natural UI state, (b) prove a real
click is consumed on it, (c) record the 5-target manual proof manifest, (d) run
the promotion-decision tools. The sections below give the disassembly-verified
recipe for each.

## The natural input path (why a real click works, and what the harness was faking)

The right-bottom triage chased an "input-source path" through `00519620 /
004612E0`. Cross-check shows that was a partial red herring: `004612E0`
(`Device_UpdateRect`, clash95.c:75772) is a **cursor-position interpolation**
helper toward `word_519620=320 / word_519622=240` (clash95.c:11639) — it does
not carry the mouse-button state.

The real, natural click path is:

1. DirectInput device → `InputBackend_PollState` fills `g_InputBackendState`;
   the left button lands in `mouse_button_primary` = `byte_5451C0`
   (clash95.c:228, 246).
2. `RenderState_PollInputAndClampCursor` accumulates the relative mouse deltas
   into the cursor position and sets the button bit:
   `v2[11] = 0; if ( byte_5451C0 < 0 ) ++v2[11];` (clash95.c:75305–75307) — i.e.
   **render_state[11]** (offset +44) bit 0 = left-button-down.
3. `DD_IsFlipping(g_RenderState)` reports that button bit.
4. `UIWidget_PollHitHoverAndClick` (called from `UIWidgetTable_PollHoverAndActions`
   `00419DC0`) invokes the descriptor's action callback when the cursor is over
   the widget **and** the button is down:
   `if ( DD_IsFlipping((int)g_RenderState) && *(_DWORD *)(a1 + 32) )` →
   callback (clash95.c:31931).
5. The hit position is read from the shared mouse globals `dword_544CFC` /
   `dword_544D00` (`g_RenderState[9]/[10]`, clash95.c:12983–12984), shifted by
   `byte_54512C`.

Implications, all verified:

- A real OS/DirectInput left click **does** naturally reach the descriptor
  callback. The debugger-forced runs were synthesizing render_state[11] / the
  click gate instead of letting `byte_5451C0` set it — that is why they are
  "debugger-forced, not natural". A clean visible run with a real click needs no
  injection.
- The HD `mouse-relative-format` + `mouse-dynamic-origin` patches are what make
  step 2's cursor position land at the right `dword_544CFC/544D00` under the
  wrapper; the button bit (`byte_5451C0`) is read straight from the device and is
  unaffected by HD patches. So position and button are independently correct.
- The centered-input wrappers offset `dword_544CFC/544D00` by `(80<<shift,
  60<<shift)`, so the native descriptor hit-region matches the centered 640×480
  art. One transform covers castle overview, battle grid, and battle/world
  descriptor polls because they all read the same globals.

## Gate 1 — Right-bottom building action menu: build an addon_flags fixture

Verified facts:

- The production/action panel renders only inside
  `if ( (*(_BYTE *)(g_BuildingGarrisonDialogActiveBuilding + 416) & 2) != 0 )`
  (clash95.c:49999). With the bit clear the panel and action rows are skipped and
  the production action descriptor is parked at `x=1000` (clash95.c:37758).
  This is exactly the mod's `owner_flag=0x00`, parked-`(1000,426)` observation —
  correct binary behavior, not a patch defect.
- The byte at `building_record + 416` (`addon_flags`) is set to bit `0x02` only by
  `Building_New(1, …)` (clash95.c:34186); callsites build a player structure
  (clash95.c:20239 builder case, 65907 scenario init). The owner is recorded at
  `building_record + 2/+3` = player index (clash95.c:34125–34126); the type
  `a1` at `+4`.
- **Save load is a verbatim binary image restore**: `SaveSlot_LoadGame` skips a
  16-byte header then does a single bulk `fread_(gameData, 0x8F29E, …)`
  (clash95.c:61809) with no per-building reconstruction. Building records live at
  `gameData + 509674`, 467-byte stride, 100 records
  (`docs/SAVE_DAT_FORMAT.md` row 509674).

Therefore the right-bottom natural route is reachable by a single isolated
save-byte edit, mirroring the already-proven battle constructed-fixture pattern:

1. Copy an existing save into an isolated work dir under `C:\ClashTests\...`
   (never mutate `C:\Clash\save`).
2. Pick a building the player owns (record byte `+3` == player index) that they
   will click, at building index `i`.
3. Set bit `0x02` at file offset `0x10 + 509674 + i*467 + 416`
   (= `0x10 + 0x7C6FA + i*467 + 0x1A0`).
4. Load that save on the HD candidate, click the building, and confirm the
   natural UI now draws `RBUI_PANEL_DRAW` / `RBUI_ACTION_BOX` (no debugger-forced
   click). Then prove the centered geometry and a real click on the action
   descriptor.

This converts `controlled_recovered_but_natural_route_nonpromoting` into a
natural pass without any new binary patch.

> Update 2026-07-03: steps 1–3 of this recipe are implemented by the repo-only
> helper `tools/right_bottom_constructed_save_fixture.py` (dry-run planning,
> auto-selection of a plausible player-owned building, isolated `--output-save`
> write with repository/source-save guards).
>
> Update 2026-07-12: the byte-flip recipe is NOT sufficient when the only
> player-owned record is the castle itself (the slot-0 save has a castle-only
> roster). Setting `addon_flags & 0x02` on a castle record without real addon
> state sends the castle-overview forced hit-test into an endless
> `NOWNER_CASTLE_HIT` loop under the descriptor probe (observed in hidden runs
> before `cdb-surface-dump-20260712-152956` was retired). Use the
> slot5-as-slot0 fixture instead: slot 5's castle record carries
> `addon_flags=0x0B` legitimately (`prepare_right_bottom_slot_fixture.ps1`
> plus `probes/cdb/castle/clash95_castle_cmd99_owner_action_slot5_fixture_extra.cdb`,
> which has the `NOWNER_CASTLE_HIT_GIVEUP` loop escape). Keep the byte-flip
> helper for saves that actually contain player-owned production buildings.

## Gate 2 — Battle command: use the proven enabled-command fixture + clean visible click

Verified facts:

- Command enablement is gated by per-unit-type capability tables indexed by
  `88 * unit_type`: `g_UnitTypeBaseMeleeAttack` (`byte_51257E`, clash95.c:258)
  and `g_UnitTypeMaxRange` (`byte_512582`, clash95.c:262). A command enables
  (`dword_53205C=1`, `dword_514B80=2`) only when both are non-zero
  (clash95.c:46111–46130).
- The local `.dat` saves contain only zero-capability types (Peasant / Light
  infantry / Light cavalry / Highlander / Builder), hence `enabled=0`. The
  constructed Dragon-cavalry fixture already proves an enabled command under
  harness (see README battle evidence).

Remaining work (per `battle_ui_completion_plan.md` steps 24–25):

1. Reuse the isolated enabled-command fixture (Dragon cavalry / any melee+range
   type — README enumerates 11 candidates).
2. Do a **clean visible run** with a real OS click on the centered command
   descriptor at displayed `(588,440)` → native `(508,380)`. Avoid the fragile
   CDB-breakpoint harness that produced the 1 invalid run (post-`g` `80000003`
   break-instruction exception + 52 breakpoint insert/remove failures); the
   `battle_visible_harness_guard` already fails fast on those signatures.
3. The natural input path above guarantees the click reaches callback
   `0042D4E0` once the descriptor is drawable and the unit's command is enabled —
   no forced render-begin skip, click-gate, or unit-type override is needed
   (the fixture already returns click-gate `eax=1` naturally).

## Gate 3 — Castle overview: already passing, manual input only

`Castle_RebuildSceneBuffers` (`00422020`) renders to `dword_5202E0`
(clash95.c:37613,37620); `Castle_OpenManagementScreen` (`00422180`) installs it
as the render hook and makes the 640×480 surface (clash95.c:38737,38782); the
hit-test is pixel-color based over `g_CastleScreenSurface` at
`(dword_544CFC>>shift, dword_544D00>>shift)` (clash95.c:38818). The HD wrappers
are correct and all automated overview gates pass. Only the manual
`castle_overview_centered_input` / `castle_barracks_centered_input` proofs remain.

## Definitive completion sequence

1. Obtain explicit visible/manual runtime approval (required before any visible
   command per repo policy).
2. Prepare isolated fixtures under `C:\ClashTests\...`:
   - right-bottom: `addon_flags`-bit-0x02 save edit (Gate 1).
   - battle: enabled-command (Dragon cavalry) save (Gate 2).
3. Run the 5 manual targets from `tools/manual_directinput_run_plan.py`
   (`-AllowVisibleRuntime`), capturing real clicks:
   `stable_menu_load`, `stable_hd_map_input`, `right_bottom_validation_input`,
   `castle_barracks_centered_input`, `castle_overview_centered_input`. For each,
   record displayed/native coordinates, selected descriptor/hitbox, callback or
   state transition, no-crash, and no-stale-process.
4. Write the manual proof manifest (`evidence_class=manual_directinput`, every
   target `status=pass`); validate with
   `manual_directinput_checklist.py --require-promotion-ready` and
   `battle_visible_input_summary.py --require-click-consumed`.
5. Run the promotion-decision tools
   (`right_bottom_compose_promotion_decision.py`,
   `castle_overview_promotion_decision.py`) against that manifest, then promote
   the proven validation groups or cut the `complete-hd` alias.

At that point all gate-matrix rows pass and the mod is release-complete.

## What not to do (confirmed by disassembly)

- Do **not** patch the binary to force the right-bottom panel to draw: it is
  correctly gated by `addon_flags & 0x02`; forcing it paints a panel for a
  building with no production state. Use the save fixture.
- Do **not** ship a selected-unit-type override to fake an enabled battle
  command: enablement is a legitimate unit-capability gate. Use a real roster.
- Do **not** add per-route mouse coordinate fudges: the binary uses one shared
  model (`dword_544CFC/544D00 >> byte_54512C`); keep the single centered offset.
- Do **not** rely on the `004612E0` cursor-interpolation path as the "input
  source"; the real click path is `byte_5451C0` → render_state[11] →
  `DD_IsFlipping` → `UIWidget_PollHitHoverAndClick`.

# Selected-army portraits in HD

The user's supplied comparison showed selection brackets without the portrait
row. The [2026-09-06 diagnostic](../../captures/current/framed-unit-selection-diagnostic-current.md)
reproduces that behavior on the prior 1024x768 framed/modalcanvas candidate
(`c09940fa…c008d18d`):
native selection succeeds, eight portraits are drawn, and the following map
redraw erases them. The native y400..463 placement is also too high for HD.

## Source and observed order

The known slot0 SHA is
`4f2182409d209985a527f07c4116b19e44332416698d6acb0a3d35ae68db8a89`.
Army3 at16,19 has eight squads, types16,16,1,1,1,1,1,1. A single-squad unit
would not establish this panel route. Native `40A500` checks squad count;
`423B00` sets prior selection and lower-row owner, draws portraits, then
redraws the map:

- `423B2D: E8 EE F8 FF FF` calls423420; the next instruction is **423B32**.
- `423B37: E8 C4 4B FF FF` calls418700; the next instruction is **423B3C**.
- Original41877F is `83 FF 06 7C A1`; current1024 candidate is
  `83 FF 0A 7C A1`. The initial terrain loop grows from six to ten rows,
  including the native portrait row. The army-owner condition only skips
  the last extended row, so it no longer protects those portraits.

The later guarded framed composition rejects lower-row owner1. That rejection
does not undo terrain already painted over the portraits, and the frame can
also retain native/HD mixtures. Both the before/after captures and the final
return remain diagnostic software surfaces, not accepted whole-screen output.

`408131` alone is not selection proof: the early no-input return also reaches
it. Require the original selection, native occupancy/player, changed selected
index and EAX1, plus actual panel-route observations. Never force those results.

## Current implementation and bounded result

The [new 1024×768 run](../../captures/current/framed-army-selection-runtime-current.md)
passes native selection and software layout on2026-09-06. Candidate
`9bc99ba5…508c53b5` draws all eight army3 portraits at the new bottom anchor;
the complete backing remains identical through the map redraw. Every outer
frame band, all six action cells and all eight portrait body audits pass.
Source-bound trace and cleanup pass. This is not manual/final-wrapper proof.

The subsequent [six-transition run](../../captures/current/framed-army-transitions-runtime-current.md)
passes at **2026-09-06T09:51:12.5857021Z** on the same candidate: eight-, four-,
two- and single-squad selection, reselection, and native Map-mode deselection.
All six screenshots pass the outer frame and action-bar checks. Empty portrait
slots restore their backing; selecting the single unit or deselecting removes
the panel. The first and repeated eight-squad screenshots are pixel-identical.
See [ARMY_TRANSITION_ROUTES.md](ARMY_TRANSITION_ROUTES.md) for the distinction
between these controlled native routines and ordinary map/portrait dispatch.

The subsequent [first-portrait toggle](../../captures/current/framed-army-portrait-runtime-current.md)
passes its complete source-bound trace on the same candidate at
**2026-09-06T10:20:13.7382740Z**. Two controlled calls to native423860 change
only the first portrait flag0→1→0, complete both redraws and release polling,
and return without entering movement. All three screenshots pass every frame
edge and all six action cells. The native badge and seven map-marker masks
explain all1,243 changed pixels; the second toggle restores the entire original
frame. Marker blend colors, other slots and ordinary/manual dispatch remain
separate checks. The earlier parser startup-order failure and the disproved
badge-only pixel hypothesis remain archived in the linked manifest.

The [controlled right-key observation](../../captures/current/framed-army-keypan-observation-20260906.json)
at **2026-09-06T11:27:53.2184461Z** records native camera `(10,17)` to
`(11,17)`, unchanged full army records and released keyboard state. Both
1024x768 captures pass all four frame bands, the footer and all six action
cells. Both minimap outlines match all 110 expected pixels; all 50 old-only
outline pixels are erased. Host capture and pixel checks pass, but complete
source-bound trace acceptance remains pending an unfinished validator.

Whole-army movement remains unproved. The
[first attempt](../../captures/current/framed-army-movement-first-attempt-20260906.json)
stopped at an incorrect probe mouse-shift bound; the
[second attempt](../../captures/current/framed-army-movement-second-attempt-20260906.json)
observed the exact two-step preview queue and stopped at a held-button
assumption invalidated by native input polling. Both failures remain intact.
The v3 producer passed ten fixture groups and plan `20260906-114000` passed
its dry run, but was not executed before the user's Git checkpoint request.
The movement and keyboard-scroll validators remain unfinished local work.

The separate `-framed-modalcanvas-army-validation` suffix is assembled
from the exact previous modal candidate. The protected stable stage and every
previous generator remain unchanged. The new source files are:

- `src/patcher/framed_army_viewport.py`: the complete native 387×66 backing at
  `(32,H-82)..(418,H-17)`, with 32×64 portraits and ten native 38px slots.
- `src/patcher/framed_army_draw.py`: authenticated draw-only suffix, preserving
  font/render state without repeating selection, highlight or resource loads.
- `src/patcher/framed_army_input.py`: source-bound portrait selection and map
  click guards, without translating the mouse globals.
- `src/patcher/framed_army_composition.py`: complete terrain underneath the
  panel, followed by portrait composition; consistent lower-owner admission
  and exclusion of the full backing from map input.
- `src/patcher/pe_army_extension.py` and
  `tools/build_framed_army_candidate.py`: exact prior-image reconstruction,
  explicit old-byte hooks and relocation removals, new RX storage and loaded
  byte checks. This implementation needs no new writable cache.
- `tools/framed_army_selection_probe.py` and
  `tools/framed_army_selection_trace.py`: exact candidate/save/probe binding,
  separate native selection and draw observations, explicit DWORD sentinel
  comparisons and retained failures. The controlled route is not manual input.

The lane is deliberately bounded to the interactive player's own army, owners
0..3 with 2..10 supported squads, valid selection/resource identity and inactive
castle-canvas state. Foreign/temporary army inspection and player4 are outside
this new lane. A source build or synthetic fixture is not runtime proof.

The [older cache proposal](ARMY_PANEL_COMPOSITION.md) is historical. Its
frame-overlapping anchor and proposed cache are not used here.

## Remaining verification

The six native transitions and full redraws above are proved only for the
recorded 1024×768 scene. The first portrait's two toggles are also proved above.
Next verify other portrait slots, actual movement, ordinary map dispatch,
incremental redraws, scroll limits and the remaining resolutions. Panel drawing,
hover/hit coordinates and command buttons must share the same geometry. Include
the same selection, deselection and single/multiple-squad transitions in those
additional lanes, auditing all frame edges and bottom-right controls. Preserve
native-size art and keep natural/manual proof separate.

Do not simply suppress composition rejection or skip a required terrain row.
The existing20px selected-unit text/morale copy does not draw the full portrait
panel. Do not reinterpret its historical placement evidence as complete
portrait proof. Keep the stable stage and its byte checks unchanged.

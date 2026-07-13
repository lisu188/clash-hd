---
title: How Should The Bottom Tooltip Be Recovered
type: question
status: implementation-validation
created: 2026-05-12
updated: 2026-07-13
tags:
  - question
  - clash95
  - tooltip
---

# How Should The Bottom Tooltip Be Recovered

## Question

Should the HD patch recover a native-style bottom tooltip/status strip, relocate
tooltip text as an overlay, or leave the 12x9 map surface dominant and compose
UI differently?

## Context

The bottom-tooltip report treats tooltip/status recovery as a sibling problem
to border recovery and warns against silently folding it into map drawing.
[source page: [[Border And Bottom Tooltip Recovery Reports]]]

The design question is now answered and implemented in a validation-only
stage. Hidden CDB has proved the relocated owner globals and command-descriptor
route, and an approved isolated visible run has proved the authentic overlay
composition. Descriptor-5 click alignment still fails, so this page tracks
implementation validation rather than completion or stable promotion.

## What Is Known

- Possible bottom-tooltip owners include selected unit info, action/status
  panel, hover-only text, notification, and info-window paths. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]
- The report recommends proving whether text executes, where it draws, and
  whether the failure is redraw order, surface/present, anchor relocation, or
  hitbox pairing. [source page: [[Border And Bottom Tooltip Recovery Reports]]]
- The current no-popup surface route is useful for geometry but not final
  authentic-color evidence. [source page: [[Border And Bottom Tooltip Recovery Reports]]]

## Resolution (2026-07-13, user decision)

The desired final HD placement is now chosen by the user, from a real
visible-runtime capture
(`captures/archive/manual-rightbottom-entry/after-load-map.png`):

- **Terrain tooltip text** (e.g. "Desert - 5ap", "Plain - 4ap", "Road - 3ap")
  belongs at the **bottom of the play area, horizontally centered**. In the
  real runtime it currently renders in the middle-left of the map, which is
  wrong.
- **Selected-unit action-menu icons** (the wooden panel: globe/map-action icon
  plus unit figures) belong **docked in the right-bottom corner** (under the
  right-anchored minimap). In the real runtime the panel currently floats in
  the center-bottom of the map, which is wrong.

Both are genuine HD-layout defects (not capture artifacts): the elements draw
at the wrong anchor after the 800x600 map widening. This decision drove the
validation-stage relocation below. Approved visible composition evidence is
now present, but successful command input and a deliberate promotion decision
are still required before any stable promotion.

## Implementation Validation (2026-07-13)

- Validation groups `terrain-tooltip-bottom-center` and
  `selected-unit-command-panel-right-bottom` are implemented separately and in
  the combined `-hdlayout` stage. The protected stable/default stage is
  unchanged.
- Patch manifest
  `captures/current/patch-stage-hdlayout-current.json` records candidate
  SHA-256
  `911A4F1CFB3CFEE7974F50742CC98FDD16DCC82EAA95C88F748E0976140E6FBD`,
  138/138 expected patches, and zero unexpected records.
- Hidden/no-popup run
  `captures/archive/cdb-surface-dump-20260713-072428` passed. Its focused CDB
  rows observed tooltip globals `(left,top,right,bottom)=(240,586,553,599)`,
  six command-panel draws at `(608,528)`, `(672,528)`, `(736,528)`,
  `(608,560)`, `(672,560)`, and `(736,560)`, both draw clips at 800, the map
  surface as the render target, and hit scanning against the relocated
  endpoints. The debugger-only descriptor-5 helper invocation also took the
  patched single-redraw branch with `clip=800`; it is not manual-input proof.
- Strict repo-only marker summary
  `captures/current/hd-layout-summary-current.json` passes all layout checks.
- Approved visible-runtime fixture run
  `captures/archive/visual-smoke-20260713-075818` used the same candidate SHA.
  `captures/current/hd-layout-visible-current.json` records authentic
  composition PASS for the chosen tooltip and command-panel layout.
- Its no-click Win32 hover at client `(640,544)` was exact. The descriptor-5
  held-click request `(760,560)` landed at `(716,493)`, an error of
  `(-44,-67)`, with path and click-path verification both false. Because this
  was an isolated save fixture with automated SendInput, it is not manual
  DirectInput or callback proof.
- Future manual-run commands use `-MoveWindowX 0 -MoveWindowY -30`; with the
  measured client origin `(3,26)`, this keeps lower/right logical points inside
  the active 800x600 desktop instead of repeating the clamp.
- Manual DirectInput remains `0/5`; promotion is deferred and the protected
  stable/default stage is unchanged.
- `captures/current/hd-layout-promotion-decision-current.json` passes only as a
  fail-closed `defer_stable_promotion` record; it rejects click, callback,
  manual-proof, override, or stable-stage-change overclaims.

## Uncertainty

- Authentic composition is now resolved for the approved fixture run. The
  remaining uncertainty is high-X/high-Y click delivery and observed command
  response through real manual DirectInput in the wrapper runtime.

## Candidate Answers

- Interpretation: preserve a native-style bottom strip if CDB proves the stock
  owner can be recovered with narrow anchor or copyback changes.
- Interpretation: use an overlay if the stock strip conflicts with the 12x9 map
  design or if authentic frame recovery proves too invasive.

## Needed Sources Or Checks

- Completed: hidden-CDB owner/geometry proof for the combined validation stage
  in `captures/archive/cdb-surface-dump-20260713-072428`.
- Completed: approved visible-runtime composition review in
  `captures/archive/visual-smoke-20260713-075818`.
- Outstanding: obtain a correctly delivered descriptor click plus observed
  response through real manual DirectInput. Do not promote from composition or
  Win32 hover evidence alone.

## Related Pages

- [[Right-Bottom UI And Bottom Tooltip Recovery]]
- [[DirectDraw Surface Target Split]]
- [[No-Popup Surface Dump]]


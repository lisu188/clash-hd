---
title: Right-Bottom UI And Bottom Tooltip Recovery
type: synthesis
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - synthesis
  - clash95
  - ui-recovery
---

# Right-Bottom UI And Bottom Tooltip Recovery

## Thesis

Interpretation: the lower/right UI and bottom tooltip problem should be handled
as a targeted UI owner, surface, ordering, or anchor problem after CDB proof,
not as another broad map-size patch. [source page:
[[Border And Bottom Tooltip Recovery Reports]]; source page:
[[Current HD Map Evidence]]]

## Sourced Facts

- The border-frame report says the current HD map fills the enlarged terrain
  area while lower/right frame and bottom tooltip/status regions remain
  unrecovered. [source page: [[Border And Bottom Tooltip Recovery Reports]]]
- The same report states that current no-popup map evidence proves the HD 12x9
  map drawing path itself is valid under visibility-controlled conditions.
  [source page: [[Border And Bottom Tooltip Recovery Reports]]]
- The CDB validation report says `dword_511D40` is a native action-button
  descriptor list that draws on the 800x600 map surface, not the missing
  border/tooltip owner. [source page: [[Border And Bottom Tooltip Recovery Reports]]]
- The normal hidden-desktop load-slot route does not enter the right-bottom
  action/status owner path. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]
- The bottom-tooltip report keeps selected unit info, action/status panel,
  hover-only text, notification, and info-window paths open as possible owners.
  [source page: [[Border And Bottom Tooltip Recovery Reports]]]

## Interpretation

- The next evidence should isolate ownership before patching: prove whether
  the missing region is never drawn, drawn to the wrong surface, drawn too
  early and overwritten, or drawn at native anchors.
- [[DirectDraw Surface Target Split]] is a leading pattern because castle/action
  evidence already shows reachable UI routines can draw to scratch while the HD
  map surface remains separate.

## Uncertainty

- The exact gameplay border owner is still unknown. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]
- The desired final bottom-tooltip design is still unresolved: preserve a
  native-style strip, relocate text as overlay, or compose a different HD UI
  layout. [source page: [[Border And Bottom Tooltip Recovery Reports]]]

## Contradictions

- No contradiction is recorded in this pass; the main risk is confusing UI
  composition evidence with map rendering evidence.

## Open Questions

- [[What Owns The Gameplay Border Frame]]
- [[How Should The Bottom Tooltip Be Recovered]]

## Sources

- [[Border And Bottom Tooltip Recovery Reports]]
- [[Current HD Map Evidence]]
- [[Castle Barracks UI CDB Validation]]


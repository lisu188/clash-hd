---
title: Castle UI Centering State
type: synthesis
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - synthesis
  - clash95
  - castle-ui
---

# Castle UI Centering State

## Thesis

Interpretation: castle/barracks UI centering is validated for the targeted
barracks action-panel path, but the full castle overview/interior dispatcher is
a separate native 640x480 surface path that still needs its own narrow
centering proof. [source page: [[Castle Barracks UI CDB Validation]]]

## Sourced Facts

- The centered presentation patch centers the native 640x480 castle/barracks
  UI layer at `(80,60)` in the 800x600 surface. [source page:
  [[Castle Barracks UI CDB Validation]]]
- The centered input transform subtracts `(80,60)` from logical mouse globals
  while relevant owner-poll and descriptor-hit-test routines run. [source
  page: [[Castle Barracks UI CDB Validation]]]
- The second action descriptor proof reaches descriptor `005151cf` through the
  centered path and enters stock callback `004356c0`. [source page:
  [[Castle Barracks UI CDB Validation]]]
- The barracks success-branch proof validates the centered input/presentation
  path for a compatible selected addon path. [source page:
  [[Castle Barracks UI CDB Validation]]]
- The full castle overview/interior catalog run finishes on a native 640x480
  castle-screen surface and is separate from the already centered
  barracks/action-panel route. [source page:
  [[Castle Barracks UI CDB Validation]]]

## Interpretation

- The centered coordinate transform should remain scoped to known castle UI
  routines until the overview dispatcher is mapped.
- Surface routing should be checked with the same care as hitboxes, because a
  centered input path can be correct even while a draw/copyback path remains
  native or scratch-bound.

## Uncertainty

- The exact narrow hook for `00422180` / related castle overview present paths
  is not yet selected. [source page: [[Castle Barracks UI CDB Validation]]]
- The current proof does not cover every full castle overview descriptor.
  [source page: [[Castle Barracks UI CDB Validation]]]

## Contradictions

- No contradiction is recorded in this pass.

## Open Questions

- [[Which Castle Overview Path Needs Centering]]

## Sources

- [[Castle Barracks UI CDB Validation]]
- [[Clash95 Engine Viewport Patch Notes]]
- [[Clash95 HD Mod Progress]]


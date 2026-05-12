---
title: DirectDraw Surface Target Split
type: concept
aliases:
  - scratch surface split
  - map surface copyback split
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - concept
  - clash95
  - directdraw
---

# DirectDraw Surface Target Split

## Definition

A DirectDraw surface target split occurs when a UI or action-box path draws to
the legacy scratch/render surface while the visible HD gameplay surface is a
different 800x600 map surface. [source page: [[Castle Barracks UI CDB Validation]]]

## Why It Matters

Interpretation: this explains why a UI routine can be reached and draw
something while the reconstructed final map surface still shows black or stale
regions. It points patch work toward surface switch, copyback, or present
rectangles instead of generic map-loop widening. [source page:
[[Border And Bottom Tooltip Recovery Reports]]]

## Key Claims

- The barracks action-box evidence logs `00435500` drawing with the scratch
  render target while the map surface is separate. [source page:
  [[Castle Barracks UI CDB Validation]]]
- Selecting a different barracks/addon entry did not remove the scratch/map
  split in the selected-addon copyback trace. [source page:
  [[Castle Barracks UI CDB Validation]]]
- The border/tooltip reports recommend distinguishing surface/present failures
  from anchor relocation and redraw-order failures. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]

## Examples

- The action-box row records `render=0051d4c0` while `map_surface` points to a
  separate surface in the barracks validation report. [source page:
  [[Castle Barracks UI CDB Validation]]]
- The bottom-tooltip report lists surface/present fix as a candidate patch
  direction after proof. [source page: [[Border And Bottom Tooltip Recovery Reports]]]

## Related Concepts

- [[No-Popup Surface Dump]]
- [[Centered UI Coordinate Transform]]
- [[CDB-Only Validation]]

## Open Questions

- [[How Should The Bottom Tooltip Be Recovered]]
- [[Which Castle Overview Path Needs Centering]]

## Sources

- [[Castle Barracks UI CDB Validation]]
- [[Border And Bottom Tooltip Recovery Reports]]


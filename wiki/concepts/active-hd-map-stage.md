---
title: Active HD Map Stage
type: concept
aliases:
  - current HD map stage
  - dynvswitch stage
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - concept
  - clash95
  - hd-map
---

# Active HD Map Stage

## Definition

The active HD map stage is
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`,
the current baseline patch stage for the 800x600 Clash95 map evidence chain.
[source page: [[Current HD Map Evidence]]]

## Why It Matters

Interpretation: this stage is the stable reference point for current map
rendering claims. Later castle-center stages should be discussed as extensions
of this baseline, not replacements for the map proof. [source page:
[[Clash95 Engine Viewport Patch Notes]]]

## Key Claims

- The current evidence index records the stage as the selected HD map stage.
  [source page: [[Current HD Map Evidence]]]
- The current smoke matrix reports the stage with patch-byte proof and archived
  post-owner evidence. [source page: [[Current HD Map Evidence]]]
- Castle-center variants add UI centering and input proof on top of the map
  baseline. [source page: [[Castle Barracks UI CDB Validation]]]

## Examples

- The HD map smoke matrix candidate uses the active HD map stage and reports
  overall `PASS`. [source page: [[Current HD Map Evidence]]]
- The castlecenter-all work is a later stage that keeps the same HD map basis
  while validating centered castle/barracks UI paths. [source page:
  [[Castle Barracks UI CDB Validation]]]

## Related Concepts

- [[CDB-Only Validation]]
- [[No-Popup Surface Dump]]
- [[Visibility-Zero Versus Rendering Defect]]
- [[Centered UI Coordinate Transform]]

## Open Questions

- [[What Manual DirectInput Validation Remains]]
- [[Which Castle Overview Path Needs Centering]]

## Sources

- [[Current HD Map Evidence]]
- [[Clash95 Engine Viewport Patch Notes]]
- [[Castle Barracks UI CDB Validation]]


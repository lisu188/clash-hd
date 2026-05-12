---
title: Dynamic-Origin Mouse Input
type: concept
aliases:
  - dynamic origin mouse patch
  - screen-origin mouse fix
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - concept
  - clash95
  - input
---

# Dynamic-Origin Mouse Input

## Definition

Dynamic-origin mouse input is the patch direction that removes the runtime
client screen origin from mouse samples before mapping them into Clash95's
logical coordinate system. [source page: [[Clash95 Engine Viewport Patch Notes]]]

## Why It Matters

Interpretation: the HD display and wrapper paths can make input look scaled or
offset; using the live client origin avoids assuming that DirectInput or
automation samples are already in game-client coordinates. [source page:
[[Clash95 Engine Viewport Patch Notes]]]

## Key Claims

- The engine notes identify missing screen-origin removal as the root mouse bug
  for the HD/windowed workflow. [source page: [[Clash95 Engine Viewport Patch Notes]]]
- The menu load route recommends held clicks because instant down/up pairs can
  be missed by polling or startup cadence. [source page:
  [[Clash95 Menu Load Route Notes]]]
- The route evidence separates click mechanics from real gameplay proof by
  requiring CDB rows and gameplay frame classification. [source page:
  [[Clash95 Menu Load Route Notes]]]

## Examples

- The current menu load route uses held clicks at `400,300`, `300,218`,
  `320,166`, and `400,226`. [source page: [[Clash95 Menu Load Route Notes]]]
- Dynamic-origin work supports the active HD map workflow by keeping menu and
  gameplay clicks aligned after centering or wrapper changes. [source page:
  [[Clash95 Engine Viewport Patch Notes]]]

## Related Concepts

- [[CDB-Only Validation]]
- [[Centered UI Coordinate Transform]]

## Open Questions

- [[What Manual DirectInput Validation Remains]]

## Sources

- [[Clash95 Engine Viewport Patch Notes]]
- [[Clash95 Menu Load Route Notes]]


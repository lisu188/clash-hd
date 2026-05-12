---
title: Centered UI Coordinate Transform
type: concept
aliases:
  - castle centered input
  - centered hitbox transform
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - concept
  - clash95
  - castle-ui
---

# Centered UI Coordinate Transform

## Definition

The centered UI coordinate transform is the castle/barracks input patch that
maps centered 800x600 display coordinates back into the native 640x480 castle
UI coordinate space while relevant hit-test and owner-poll routines run.
[source page: [[Castle Barracks UI CDB Validation]]]

## Why It Matters

Interpretation: visual centering alone is not enough; hitboxes and descriptor
callbacks must see native coordinates or centered UI buttons will draw in one
place and respond somewhere else. [source page: [[Castle Barracks UI CDB Validation]]]

## Key Claims

- The centered presentation patch places the native 640x480 castle/barracks UI
  layer at `(80,60)` within the 800x600 surface. [source page:
  [[Castle Barracks UI CDB Validation]]]
- The centered input patch subtracts `(80,60)` from logical mouse globals while
  the castle/barracks owner-poll and descriptor-hit-test path runs. [source
  page: [[Castle Barracks UI CDB Validation]]]
- The barracks success-branch proof validates centered input/presentation for a
  forced compatible selected addon path. [source page:
  [[Castle Barracks UI CDB Validation]]]

## Examples

- Display coordinate `(276,501)` maps to native `(196,441)` in the centered
  second-action descriptor proof. [source page: [[Castle Barracks UI CDB Validation]]]
- Descriptor `005151cf` is reached through the centered transform in the
  second-action proof. [source page: [[Castle Barracks UI CDB Validation]]]

## Related Concepts

- [[Dynamic-Origin Mouse Input]]
- [[DirectDraw Surface Target Split]]
- [[CDB-Only Validation]]

## Open Questions

- [[Which Castle Overview Path Needs Centering]]

## Sources

- [[Castle Barracks UI CDB Validation]]
- [[Clash95 Engine Viewport Patch Notes]]


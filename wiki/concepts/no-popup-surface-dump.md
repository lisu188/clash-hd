---
title: No-Popup Surface Dump
type: concept
aliases:
  - hidden desktop surface dump
  - CDB surface dump
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - concept
  - clash95
  - capture
---

# No-Popup Surface Dump

## Definition

A no-popup surface dump is a hidden-desktop CDB run that uses a process-local
DirectDraw proxy to capture dumpable 8-bit surface memory and reconstruct a
`surface.png` artifact without showing a game window on the active desktop.
[source page: [[Clash95 Engine Viewport Patch Notes]]]

## Why It Matters

Interpretation: this is the project's current repeatable visual-evidence route
for map and UI work, but its grayscale output is geometry and coverage
evidence, not authentic final color proof. [source page:
[[Border And Bottom Tooltip Recovery Reports]]]

## Key Claims

- Current HD map evidence pairs normal and forced-visible no-popup runs to
  explain right/bottom dark cells. [source page: [[Current HD Map Evidence]]]
- The workflow writes run summaries, reconstructed surfaces, tile coverage, and
  visibility coverage artifacts under `captures/`. [source page:
  [[Current HD Map Evidence]]]
- Castle/barracks UI proof also uses no-popup CDB runs with extra probes and
  screenshot artifacts. [source page: [[Castle Barracks UI CDB Validation]]]

## Examples

- `captures/cdb-surface-dump-20260506-190037` is the normal post-owner
  visibility-zero proof. [source page: [[Current HD Map Evidence]]]
- `captures/cdb-surface-dump-20260506-201114` is the forced-visible
  seven-cell proof. [source page: [[Current HD Map Evidence]]]

## Related Concepts

- [[CDB-Only Validation]]
- [[Visibility-Zero Versus Rendering Defect]]
- [[DirectDraw Surface Target Split]]

## Open Questions

- [[How Should The Bottom Tooltip Be Recovered]]

## Sources

- [[Clash95 Engine Viewport Patch Notes]]
- [[Current HD Map Evidence]]
- [[Castle Barracks UI CDB Validation]]
- [[Border And Bottom Tooltip Recovery Reports]]


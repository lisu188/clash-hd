---
title: Visibility-Zero Versus Rendering Defect
type: concept
aliases:
  - visibility zero
  - fog versus render failure
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - concept
  - clash95
  - evidence
---

# Visibility-Zero Versus Rendering Defect

## Definition

`visibility_zero` is the evidence classification used when an active map cell is
blank because the save's visibility/fog state marks it unexplored, not because
the HD map draw path failed to fill it. [source page: [[Current HD Map Evidence]]]

## Why It Matters

Interpretation: this distinction prevents agents from patching tile loops,
present bounds, minimap placement, or action-panel copyback when the same cells
draw correctly under a controlled forced-visible proof. [source page:
[[Current HD Map Evidence]]]

## Key Claims

- The normal post-owner evidence lists seven blank active cells and classifies
  all seven as `visibility_zero`. [source page: [[Current HD Map Evidence]]]
- The forced-visible proof reports no blank active cells after forcing those
  seven visibility bytes. [source page: [[Current HD Map Evidence]]]
- The evidence-index interpretation says the normal black cells are explained
  by fog/unexplored visibility rather than remaining map loop, present-bounds,
  minimap, or action-panel copyback defects. [source page:
  [[Current HD Map Evidence]]]

## Examples

- Normal blank cells include `r6c10`, `r6c11`, `r7c10`, `r7c11`, `r8c0`,
  `r8c10`, and `r8c11`. [source page: [[Current HD Map Evidence]]]
- Forced-visible evidence makes those same cells draw, proving the HD map path
  can fill them when visibility permits. [source page: [[Current HD Map Evidence]]]

## Related Concepts

- [[No-Popup Surface Dump]]
- [[CDB-Only Validation]]
- [[Active HD Map Stage]]

## Open Questions

- [[How Should The Bottom Tooltip Be Recovered]]

## Sources

- [[Current HD Map Evidence]]
- [[Clash95 Engine Viewport Patch Notes]]


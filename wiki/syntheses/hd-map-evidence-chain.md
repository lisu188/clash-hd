---
title: HD Map Evidence Chain
type: synthesis
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - synthesis
  - clash95
  - evidence
---

# HD Map Evidence Chain

## Thesis

Interpretation: the HD map evidence chain is strong because it links patch-byte
verification, no-popup CDB surface dumps, tile coverage, visibility coverage,
and forced-visible replay of the disputed right/bottom cells. [source page:
[[Current HD Map Evidence]]]

## Sourced Facts

- The smoke matrix pairs a patch-stage byte gate with post-owner evidence and
  reports overall `PASS`. [source page: [[Current HD Map Evidence]]]
- The normal post-owner proof has seven blank active cells classified as
  `visibility_zero`. [source page: [[Current HD Map Evidence]]]
- The forced-visible proof has no blank active cells after forcing those seven
  cells visible. [source page: [[Current HD Map Evidence]]]
- The evidence index records screenshot artifacts for both the normal and
  forced-visible post-owner surfaces. [source page: [[Current HD Map Evidence]]]
- The menu route notes define the deterministic menu-to-gameplay path and
  expected CDB proof rows needed before judging map frames. [source page:
  [[Clash95 Menu Load Route Notes]]]

## Interpretation

- A valid future map regression should break one of the chain links: patch byte
  gate, gameplay route proof, surface dump readiness, tile coverage, visibility
  explanation, or forced-visible behavior.
- A dark cell by itself should not trigger map patching until visibility/fog is
  checked.

## Uncertainty

- The current archived evidence proves the selected save/run pair; it does not
  automatically prove every map, route, wrapper, or manual interaction mode.
  [source page: [[Current HD Map Evidence]]]

## Contradictions

- No contradiction is recorded in this pass.

## Open Questions

- [[What Manual DirectInput Validation Remains]]

## Sources

- [[Current HD Map Evidence]]
- [[Clash95 Menu Load Route Notes]]
- [[Clash95 Engine Viewport Patch Notes]]


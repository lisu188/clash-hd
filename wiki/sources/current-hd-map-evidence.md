---
title: Current HD Map Evidence
type: source-summary
source_path:
  - captures/hd-map-evidence-current.md
  - captures/hd-map-smoke-current.md
  - captures/post-owner-evidence-current.md
source_type: evidence-index
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - source
  - clash95
  - evidence
---

# Current HD Map Evidence

## Citation

- Sources: `[source: captures/hd-map-evidence-current.md]`,
  `[source: captures/hd-map-smoke-current.md]`,
  `[source: captures/post-owner-evidence-current.md]`
- Source page: `[[Current HD Map Evidence]]`

## Summary

These evidence indexes are the compact current-status record for the 800x600
Clash95 HD map patch. They pair patch-byte proof with archived normal and
forced-visible no-popup CDB surface-dump evidence. [source:
captures/hd-map-evidence-current.md]

## Durable Facts

- The current HD map smoke matrix reports `PASS`. [source:
  captures/hd-map-smoke-current.md]
- The patch-stage gate reports `118/118` selected current HD map bytes patched,
  with no `original` or `unexpected` records in the current evidence index.
  [source: captures/hd-map-evidence-current.md]
- The normal post-owner run lists seven blank active cells:
  `r6c10`, `r6c11`, `r7c10`, `r7c11`, `r8c0`, `r8c10`, and `r8c11`. [source:
  captures/post-owner-evidence-current.md]
- The normal evidence classifies those seven cells as `visibility_zero`.
  [source: captures/post-owner-evidence-current.md]
- The forced-visible proof reports no blank active cells after forcing those
  seven visibility bytes. [source: captures/post-owner-evidence-current.md]
- The evidence-index interpretation says the current HD map path draws the
  right/bottom cells when visibility permits it, so the normal black cells are
  explained by fog/unexplored visibility rather than map loop, present-bounds,
  minimap, or action-panel copyback defects. [source:
  captures/hd-map-evidence-current.md]

## Concepts

- [[Active HD Map Stage]]
- [[CDB-Only Validation]]
- [[No-Popup Surface Dump]]
- [[Visibility-Zero Versus Rendering Defect]]

## Syntheses

- [[HD Map Evidence Chain]]
- [[Current Clash95 HD State]]

## Open Questions

- [[What Manual DirectInput Validation Remains]]

## Links

- Related source pages: [[Clash95 Engine Viewport Patch Notes]], [[Clash95 HD Mod Progress]]


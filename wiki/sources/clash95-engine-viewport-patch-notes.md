---
title: Clash95 Engine Viewport Patch Notes
type: source-summary
source_path: docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md
source_type: engineering-notes
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - source
  - clash95
  - hd-map
---

# Clash95 Engine Viewport Patch Notes

## Citation

- Source: `[source: docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]`
- Source page: `[[Clash95 Engine Viewport Patch Notes]]`

## Summary

This source is the long-form engineering record for the Clash95 HD viewport
patch: it tracks reverse-engineering leads, patch stages, CDB evidence, mouse
and menu probes, no-popup surface dumps, and later castle UI work. [source:
docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]

## Durable Facts

- The current 800x600 HD map work is centered on the stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`,
  with later castle-center variants layered on top for castle/barracks UI
  proof. [source: docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]
- The notes record the dynamic-origin mouse finding: the root mouse bug was
  missing screen-origin removal, and the fix uses runtime client origin rather
  than treating DirectInput samples as already client-relative. [source:
  docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]
- The no-popup CDB surface-dump workflow is treated as current evidence, while
  VirtualBox probing is historical unless explicitly re-enabled. [source:
  docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]
- The current HD map evidence says right/bottom dark cells can be explained by
  visibility/fog state and are not proof of a remaining 12x9 map drawing defect.
  [source: docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]
- The castle/barracks entries document that centered presentation and centered
  hitbox transforms are validated for selected barracks action paths, while full
  castle overview centering remains a separate path. [source:
  docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]

## Concepts

- [[Active HD Map Stage]]
- [[CDB-Only Validation]]
- [[No-Popup Surface Dump]]
- [[Visibility-Zero Versus Rendering Defect]]
- [[Dynamic-Origin Mouse Input]]
- [[Centered UI Coordinate Transform]]
- [[DirectDraw Surface Target Split]]

## Syntheses

- [[Current Clash95 HD State]]
- [[HD Map Evidence Chain]]
- [[Castle UI Centering State]]

## Open Questions

- [[Which Castle Overview Path Needs Centering]]
- [[What Manual DirectInput Validation Remains]]

## Links

- Related source pages: [[Clash95 HD Mod Progress]], [[Current HD Map Evidence]]

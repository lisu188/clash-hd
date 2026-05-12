---
title: Border And Bottom Tooltip Recovery Reports
type: source-summary
source_path:
  - reports/border-frame-recovery.md
  - reports/border-tooltip-cdb-validation.md
  - reports/bottom-tooltip-recovery.md
source_type: investigation-reports
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - source
  - clash95
  - ui-recovery
---

# Border And Bottom Tooltip Recovery Reports

## Citation

- Sources: `[source: reports/border-frame-recovery.md]`,
  `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`
- Source page: `[[Border And Bottom Tooltip Recovery Reports]]`

## Summary

These reports investigate the missing gameplay border, lower/right UI, and
bottom tooltip/status band in the current HD map path. They frame the issue as
UI composition and route/state recovery, not as a proven remaining map tile
rendering failure. [source: reports/border-frame-recovery.md]

## Durable Facts

- The border-frame report says the current best color UI capture has expanded
  HD terrain and a moved minimap, while lower/right frame and bottom
  tooltip/status regions remain unrecovered. [source:
  reports/border-frame-recovery.md]
- The border-frame report identifies `sub_418700`, `dword_526990`, descriptor
  draw/hit-test helpers, action-panel functions, and panel/text functions as
  high-value runtime leads. [source: reports/border-frame-recovery.md]
- The bottom-tooltip report keeps several possible owners open, including
  selected unit info, right/status action panel, hover-only text, and
  notification/info-window paths. [source: reports/bottom-tooltip-recovery.md]
- The CDB validation report says `dword_511D40` is not currently the missing HD
  border/tooltip owner; it is a native action-button descriptor list that draws
  successfully on the 800x600 map surface. [source:
  reports/border-tooltip-cdb-validation.md]
- The CDB validation report says the normal hidden-desktop load-slot route does
  not enter the right-bottom action/status owner path, so a controlled
  non-mouse state route is the next proof direction. [source:
  reports/border-tooltip-cdb-validation.md]

## Concepts

- [[CDB-Only Validation]]
- [[DirectDraw Surface Target Split]]
- [[Visibility-Zero Versus Rendering Defect]]

## Syntheses

- [[Right-Bottom UI And Bottom Tooltip Recovery]]
- [[Current Clash95 HD State]]

## Open Questions

- [[What Owns The Gameplay Border Frame]]
- [[How Should The Bottom Tooltip Be Recovered]]

## Links

- Related source pages: [[Current HD Map Evidence]], [[Castle Barracks UI CDB Validation]]


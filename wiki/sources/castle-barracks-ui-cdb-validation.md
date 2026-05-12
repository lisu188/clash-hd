---
title: Castle Barracks UI CDB Validation
type: source-summary
source_path: reports/castle-barracks-ui-cdb-validation.md
source_type: validation-report
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - source
  - clash95
  - castle-ui
---

# Castle Barracks UI CDB Validation

## Citation

- Source: `[source: reports/castle-barracks-ui-cdb-validation.md]`
- Source page: `[[Castle Barracks UI CDB Validation]]`

## Summary

This report documents no-popup CDB evidence for castle/barracks UI routing,
centered presentation, centered hitbox transforms, descriptor clicks, and the
separate full castle overview/interior path. [source:
reports/castle-barracks-ui-cdb-validation.md]

## Durable Facts

- The initial barracks UI run reached the castle/barracks action-panel draw
  functions and reported no access-violation rows. [source:
  reports/castle-barracks-ui-cdb-validation.md]
- The centered presentation patch visually centers the native 640x480
  castle/barracks UI layer at `(80,60)` inside the 800x600 surface. [source:
  reports/castle-barracks-ui-cdb-validation.md]
- The centered hitbox transform temporarily maps centered screen coordinates
  back to native castle UI coordinates by subtracting `(80,60)` from logical
  mouse globals while the relevant routines run. [source:
  reports/castle-barracks-ui-cdb-validation.md]
- The centered second action descriptor proof showed that descriptor gate and
  callback routing were correct for descriptor `005151cf`, while the stock
  callback rejected the selected addon state in that run. [source:
  reports/castle-barracks-ui-cdb-validation.md]
- The `castlecenter-all` catalog run found that the full castle overview route
  finishes on a native 640x480 castle-screen surface, so it needs a separate
  centering hook from the barracks/action-panel route. [source:
  reports/castle-barracks-ui-cdb-validation.md]
- The barracks success-branch proof validates centered barracks
  input/presentation for the forced compatible selected addon path, but it does
  not validate every full castle overview descriptor. [source:
  reports/castle-barracks-ui-cdb-validation.md]

## Concepts

- [[Centered UI Coordinate Transform]]
- [[CDB-Only Validation]]
- [[DirectDraw Surface Target Split]]

## Syntheses

- [[Castle UI Centering State]]
- [[Current Clash95 HD State]]

## Open Questions

- [[Which Castle Overview Path Needs Centering]]

## Links

- Related source pages: [[Clash95 Engine Viewport Patch Notes]], [[Clash95 HD Mod Progress]]


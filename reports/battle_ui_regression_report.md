# Battle UI Regression Report

Generated: 2026-05-15

No battle-specific patch bytes were added, so this regression pass is scoped to
repo-only guards and patch-table safety.

## Required Regression Anchors

- Stable HD-map stage remains:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Castle/interior validation remains:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Battle validation stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`

## Current Result

- Stable/default stage: unchanged.
- Castle/interior validation stage: unchanged.
- Battlecenter stage: defined as probe-first scaffold only.
- Battle patches: none.

Runtime battle regression remains pending until a deterministic hidden/no-popup
battle-entry route exists.

---
title: Clash95 Menu Load Route Notes
type: source-summary
source_path: docs/hd/CLASH95_MENU_LOAD_ROUTE_NOTES.md
source_type: route-notes
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - source
  - clash95
  - menu-route
---

# Clash95 Menu Load Route Notes

## Citation

- Source: `[source: docs/hd/CLASH95_MENU_LOAD_ROUTE_NOTES.md]`
- Source page: `[[Clash95 Menu Load Route Notes]]`

## Summary

This source defines the deterministic menu-to-gameplay load route used for HD
map validation and records the static and runtime evidence behind the route.
[source: docs/hd/CLASH95_MENU_LOAD_ROUTE_NOTES.md]

## Durable Facts

- The recommended route uses held clicks at `400,300`, `300,218`, `320,166`,
  and `400,226` after intro skip pulses. [source:
  docs/hd/CLASH95_MENU_LOAD_ROUTE_NOTES.md]
- The route is supported by static callback evidence around `StartMenu`,
  callback `00447780`, load-slot row drawing, load accept, `loadMap`, and
  `PlayGame`. [source: docs/hd/CLASH95_MENU_LOAD_ROUTE_NOTES.md]
- The note marks `320,245;448,245;648,49;760,201` as a route to avoid because
  it can look mechanically successful while still producing menu-like frames.
  [source: docs/hd/CLASH95_MENU_LOAD_ROUTE_NOTES.md]
- The expected CDB proof rows include main load callback, slot draw, load
  accept, load-save, load-map, `PlayGame`, and map redraw. [source:
  docs/hd/CLASH95_MENU_LOAD_ROUTE_NOTES.md]

## Concepts

- [[CDB-Only Validation]]
- [[Dynamic-Origin Mouse Input]]

## Syntheses

- [[Current Clash95 HD State]]
- [[HD Map Evidence Chain]]

## Open Questions

- [[What Manual DirectInput Validation Remains]]

## Links

- Related source pages: [[Clash95 Engine Viewport Patch Notes]]

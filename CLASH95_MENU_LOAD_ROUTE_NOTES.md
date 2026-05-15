# Clash95 Menu Load Route Notes

## Purpose

Find the smallest deterministic route from the authentic main menu into a
gameplay/load-slot frame for automated HD-map validation. This note is scoped to
route archaeology: static callback evidence, CDB probe points, known-good
captures, and routes to avoid.

## Recommended Route

Use this route after the intro skip pulses have had time to expose the main
menu:

1. `400,300` - neutral held click. This protects against the startup animation
   consuming the first route click and leaves the cursor in a safe center point.
2. `300,218` - main-menu Load button.
3. `320,166` - load slot 0 row.
4. `400,226` - load/OK confirmation.

Use held clicks rather than instant down/up pairs for CDB-backed automation:
`-ClickHoldMs 300 -ClickRepeat 2 -ClickIntervalMs 900` is the current
conservative pattern.

## Evidence Chain

- Ghidra/export anchors:
  - `C:\Clash\reverse\ghidra-out\functions.csv` identifies
    `0040B660,PlayGame`, `00444490,FUN_00444490`,
    `0044A110,FUN_0044A110`, `0044A140,FUN_0044A140`,
    `0044AE90,loadMap`, and `004479C0,PlayGame_Dispatch`.
  - `C:\Clash\clash95.c` currently contains the clearest recovered control-flow
    view for `StartMenu`, the load-menu switch case, and the slot-row bounds
    summarized below.
- Main menu static route:
  - `StartMenu` builds the main menu from `unk_5181C0`, draws it with
    `sub_419D80`, and hit-tests with `sub_419DC0`.
  - Callback `00447780` is the load callback: it sets `dword_543D7C = 5` and
    `dword_543D78 = 1`.
  - CDB menu-hit rows from existing dynamic probes put the centered main-menu
    load descriptor around the shifted left/top button group; `300,218` lands
    inside that area.
- Load-slot static route:
  - The load menu draws slot rows with `sub_44A140(k)`.
  - The selected row test accepts `x` in `244..410`; row is
    `(mouse_y - 155) / 22` for rows `0..9`.
  - `320,166` selects slot 0.
  - `0044A110` accepts the selected slot, sets `dword_544190 = 1`, and exits
    the load menu if the slot validates.
  - After a selected slot is accepted, the menu path calls `00444490`
    (`FUN_00444490`, load save), then reaches `0040B660` (`PlayGame`).
- Existing runtime evidence:
  - `captures\visual-smoke-20260423-121409\results.json` used
    `400,300;300,218;320,166;400,226` and reached a gameplay-looking
    `after-map-path.png`.
  - `captures\visual-smoke-20260423-135516\results.json` used the same route
    and again reached a gameplay-looking `after-map-path.png`.
  - `captures\map-runtime-loadslot0-v2-summary-20260422.json` reached
    `PlayGame` with the shorter `300,218;320,166;400,226` CDB route.
  - `captures\map-stream-constructors-mapsurface-scrollclamp-640blit-loadslot0-summary-20260423.json`
    and `captures\map-stream-constructors-fullredraw12-loadslot0-summary-20260423.json`
    reached `PlayGame`, produced redraw rows, and had `Exceptions=0`.

## Routes To Avoid

Do not treat `320,245;448,245;648,49;760,201` as gameplay-entry proof. It
previously produced successful path/click mechanics but still captured a
menu-like `after-map-path.png`; `tools\map_tile_coverage.py --require-gameplay`
rejected those frames with `low_top_left_gameplay_border_coverage`.

## Useful Breakpoints

- `00460A9D` - mouse object update row used by existing CDB mouse probes.
- `00419B80` - focused menu-hit descriptor row used by existing CDB menu probes.
- `00447780` - main-menu Load callback; proves route has selected Load.
- `0044A140` - load-slot row draw/highlight helper; proves load menu is active.
- `0044A110` - load-slot accept helper; proves selected row was submitted.
- `00444490` - load-save path after a selected slot was accepted.
- `0044AE90` - `loadMap`.
- `0040B660` - `PlayGame`.
- `00406FA0` - map redraw function, useful after route success.

Use `probes/cdb/menu/clash95_menu_load_route_probe.cdb` with `run_cdb_map_probe.ps1` to collect
these proof points.

## Suggested Validation Command

```powershell
.\run_cdb_map_probe.ps1 `
  -Exe 'C:\Clash\clash95_hd_candidate.exe' `
  -Probe .\probes/cdb/menu/clash95_menu_load_route_probe.cdb `
  -Log .\captures\cdb-menu-load-route.log `
  -MouseJson .\captures\menu-load-route-mouse.json `
  -Frame .\captures\menu-load-route-frame.png `
  -Points '400,300;300,218;320,166;400,226' `
  -ClickHoldMs 300 `
  -ClickRepeat 2 `
  -ClickIntervalMs 900 `
  -RunSeconds 12
```

Expected CDB proof rows in order:

1. `ROUTE_MAIN_LOAD_CALLBACK`
2. `ROUTE_LOAD_SLOT_DRAW` rows
3. `ROUTE_LOAD_ACCEPT`
4. `ROUTE_LOADSAVE`
5. `ROUTE_LOADMAP`
6. `ROUTE_PLAYGAME`
7. `ROUTE_MAP_REDRAW`

After capturing a frame, run:

```powershell
C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  .\tools\map_tile_coverage.py `
  .\captures\menu-load-route-frame.png `
  --require-gameplay `
  --write-json .\captures\menu-load-route-coverage.json
```

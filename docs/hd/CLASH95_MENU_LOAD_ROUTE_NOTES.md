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
- Current load-slot boundary:
  - `captures\current\load-slot-route-limit-current.md` keeps the current evidence
    machine-checkable. Static code still shows ten local load rows and
    integer `save\%d.dat` checks, and `scripts/cdb/run_cdb_surface_dump.ps1` still uses
    `x=320`, `y=166 + 22 * LoadSlot`.
  - Archived hidden-desktop CDB evidence proves slot 2 reaches
    `SURFDUMP_LOADSAVE`/`PlayGame`, but slots 3, 4, and 5 currently time out
    before forced load-select, forced load-accept, `LOADSAVE`, or `PlayGame`.
  - `captures\current\load-slot-timeout-phase-current.md` narrows that blocker:
    slot 2 reaches `0044895A` load-menu entry, loop rows, forced
    select/accept, `LOADSAVE`, and `PlayGame`; slots 3, 4, 5, plus the
    current slot-5 right-bottom attempt, reach early `00419B80`
    load-coordinate descriptor rows only and stall before `0044895A`.
  - `captures\current\load-slot-entry-gap-current.md` now keeps the exact transition
    gap machine-checkable: rows 3-5 stop after the forced main Load callback
    and before real case-5 load-menu entry, so they are not yet evidence of
    invalid save rows or broken `sub_444750` checks.
  - `captures\current\load-slot-transition-probe-guard-current.md` keeps the next
    focused probe ready: `probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb` avoids
    early `00419B80` coordinate forcing, logs the `00419C60`/`00447D61`
    handoff, and late-arms row selection only after `0044895A`.
  - `tools\load_slot_transition_summary.py` parses future `LSTRANS_*` logs and
    classifies them as pre-entry stalls, entry-without-`LOADSAVE` blockers, or
    late-entry load success.
  - Do not treat the presence of `C:\Clash\save\5.dat` or the slot-5
    action-eligible owner record as proof that the natural load-menu row-5
    route is working. Until rows 3-5 are proven, use an isolated slot fixture
    or a direct-loader probe and label it as non-natural route evidence.
  - `captures\current\right-bottom-slot-fixture-plan-current.md` now makes the safest
    non-promoting fixture route explicit: copy only the route-compatible
    `C:\Clash\save\5.dat` state into an isolated workdir as `save\0.dat`, then
    rerun the already-proven row-0 hidden-desktop route. This must not mutate
    `C:\Clash\save`, must not write the fixture into the repository, and must
    not promote `rightbottomcompose` while natural row-5 loading is still
    blocked before `LOADSAVE`.
  - `scripts/smoke/prepare_right_bottom_slot_fixture.ps1` is the dry-run helper for that
    route. By default it only prints a JSON/text plan; with `-SeedWorkDir` it
    plans a non-save seed from `C:\Clash` before overlaying `save\0.dat`, the
    actual `Copy-Item` writes are after the `-Execute` gate, and
    `captures\current\right-bottom-slot-fixture-script-guard-current.md` verifies the
    helper refuses source-workdir, live-save, and repository fixture output.
  - `captures\current\right-bottom-slot-fixture-runtime-plan-current.md` now records
    the future hidden-desktop runtime command sequence for that fixture:
    prepare dry-run with `-SeedWorkDir`, explicit `-Execute` to seed non-save
    workdir files plus the route-compatible save overlay, then
    `scripts/cdb/run_cdb_surface_dump.ps1` with the isolated fixture as `-WorkDir`, a child
    `-CandidateDir`, `-LoadSlot 0`, and the right-bottom owner/action CDB
    probe, followed by `tools\right_bottom_slot_fixture_result_summary.py`
    with `--require-load-success`, `--require-slot-match`,
    `--require-owner-bit2`, and `--require-owner-action`. This remains
    non-natural fixture evidence until natural rows 3-5 enter `LOADSAVE`.
  - `captures\current\right-bottom-slot-fixture-result-summary-tests-current.md`
    covers the future result parser before runtime use: missing
    `LOADSAVE`/`PlayGame`, owner-flag-blocked, owner-loop-without-action,
    owner/action reached, and AV rows each classify distinctly and fail closed
    when a required owner/action proof is absent.
  - 2026-05-27 update: slot `5` is no longer blocked at the load transition.
    `captures\archive\cdb-surface-dump-20260527-163809\load-slot-transition-summary.md`
    proves the real `0044895A -> LOADSAVE -> PlayGame` route for slot `5`
    when slot forcing is deferred until after `0044895A` with
    `-LateLoadSlotForcingOnly`.
  - The follow-up natural right-bottom run
    `captures\archive\cdb-surface-dump-20260527-193512\right-bottom-natural-slot5-summary.md`
    shows the next blocker is later: command `0x63`, owner flag bit `0x02`,
    `004338E0`, `Render_Begin` exit, `NOWNER_ACTION_CALL_WRAPPER`, and
    `NOWNER_OWNER_435BC0_ENTRY` are reached. The diagnostic click-release row
    clears `d544d04` after `004338E0`, but `NOWNER_WRAPPER_COPYBACK_DONE`
    remains absent.
  - The next right-bottom probe lane is v8 copyback tracing: it keeps slot `5`
    natural routing intact, then logs wrapper entry at `0051B7E0`, stock
    `00435BC0` loop/return rows, copyback call/return, and final `0051B86D`.
    This is evidence-only and does not change the stable/default stage.
- Existing runtime evidence:
  - `captures\archive\visual-smoke-20260423-121409\results.json` used
    `400,300;300,218;320,166;400,226` and reached a gameplay-looking
    `after-map-path.png`.
  - `captures\archive\visual-smoke-20260423-135516\results.json` used the same route
    and again reached a gameplay-looking `after-map-path.png`.
  - `captures\archive\map-runtime-loadslot0-v2-summary-20260422.json` reached
    `PlayGame` with the shorter `300,218;320,166;400,226` CDB route.
  - `captures\archive\map-stream-constructors-mapsurface-scrollclamp-640blit-loadslot0-summary-20260423.json`
    and `captures\archive\map-stream-constructors-fullredraw12-loadslot0-summary-20260423.json`
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

Use `probes/cdb/menu/clash95_menu_load_route_probe.cdb` with `scripts\cdb\run_cdb_map_probe.ps1` to collect
these proof points.

## Suggested Validation Command

```powershell
.\scripts\cdb\run_cdb_map_probe.ps1 `
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

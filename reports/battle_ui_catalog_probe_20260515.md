# Battle UI Catalog Probe, 2026-05-15

## Scope

This run exercised the probe-first `battlecenter` validation stage on a hidden
desktop with the DirectDraw surface-dump proxy and the battle catalog extra
probe. It did not add battle-specific patch bytes and did not force battle
entry.

## Inputs

- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
- Extra probe:
  `probes\cdb\battle\clash95_battle_ui_catalog_extra.cdb`
- Runtime candidate:
  `C:\ClashTests\battlecenter-catalog\clash95_hd_battlecenter_catalog_20260515_02.exe`
- Runtime candidate SHA-256:
  `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`
- Patch-stage manifest:
  `reports\battlecenter_patch_stage_20260515_01.json`
- Hidden CDB run:
  `captures\archive\cdb-surface-dump-20260515-114101`

## Results

- Hidden/no-popup CDB launch passed.
- Host-side surface dump passed.
- Surface dump output: 800x600, `480000` bytes.
- Patch-stage report: `134` patched, `0` original, `0` unexpected.
- Stable HD-map gate inside the patch-stage report: PASS.
- Battle summary:
  `battle_reached=False`, `battle_ready=False`, `surface_size=[800,600]`,
  `visual_mode=unknown`, `command_hit_ok=False`, `grid_hit_ok=False`,
  `av_count=0`.
- Battle gate:
  fail-closed as expected because no battle route rows were reached.

## Interpretation

The battle probe templates and hidden CDB surface-dump setup are now runnable.
The current harness route reaches normal gameplay and proves a clean 800x600
surface on the battle validation stage, but it stops before any battle route,
so `BATTLE_READY`, `BATTLE_SURFACE`, command descriptors, tactical-grid rows,
and modal classification remain absent.

Static follow-up refined the next runtime marker: `0042E9E0` (`sub_42E9E0`)
appears to own the live battle runner and later calls `HandleBattleResults` at
`0042E5A0` after logging `END OF BATTLE`. The battle probes now log
`BATTLE_OWNER_ENTRY` at `0042E9E0` so the next route attempt can capture the
live battle screen earlier.

The next engineering target is a harness-only deterministic battle-entry route.
Do not add `battle-ui-*` patch groups until that route produces battle-scoped
runtime rows and the battle gate fails for a reason narrower than reachability.

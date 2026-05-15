# Battle UI Completion Plan

Generated: 2026-05-15

## Scope

Battle UI support is a separate probe-first validation lane. The first release
target is safe complete mode: keep native 640x480 battle UI rendering intact,
center it inside the 800x600 HD surface at offset `(80,60)`, and prove command,
tactical-grid, and modal input routes map displayed coordinates back to native
coordinates.

This report does not promote battle support into the stable/default stage.

## Current Stages

- Stable HD map:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Castle/interior validation:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Battle probe validation:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`

The battle probe validation stage currently selects the same patch groups as
`castlecenter-all`. It intentionally has no battle-specific patch groups yet.

## Existing Passing Evidence To Preserve

- Stable HD map candidate SHA:
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Stable patch-stage status: `118` patched, `0` original, `0` unexpected.
- Fixed castle validation candidate SHA:
  `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`
- Fixed castle overview runs:
  `captures\cdb-surface-dump-20260515-105041`,
  `captures\cdb-surface-dump-20260515-105411`,
  `captures\cdb-surface-dump-20260515-105458`, and
  `captures\cdb-surface-dump-20260515-105557`.

## New Probe Artifacts

- `clash95_battle_ui_catalog_extra.cdb`
- `clash95_battle_ui_present_extra.cdb`
- `clash95_battle_ui_input_extra.cdb`
- `tools\battle_ui_summary.py`
- `tools\battle_ui_gate.py`

The CDB templates log `BATTLE_*` rows only. They do not patch code, do not force
input, and do not claim a route is patch-safe.

## Required Evidence Before Any Battle Patch

- Deterministic hidden/no-popup route into a battle screen.
- Battle surface pointer and size.
- Battle draw/present or copyback call sites with runtime rows.
- Battle command descriptors and callbacks.
- Tactical-grid hit or coordinate conversion route.
- Modal/dialog route, or explicit not-reached classification.
- No `c0000005`, `BATTLE_AV`, or failure-exit rows.
- Patch-stage report for the battle stage with `original=0` and
  `unexpected=0`.
- Stable HD-map smoke still passing.
- Castle/interior validation unchanged if included.

## Patch Boundary

Do not add any of these groups until probe evidence identifies exact addresses:

- `battle-ui-center-present`
- `battle-ui-ensure-800-surface`
- `battle-ui-centered-input`
- `battle-grid-centered-input`
- `battle-modal-centered-input`
- `battle-present-bounds`

Do not patch `640`, `480`, `0x27F`, `0x1DF`, tactical-grid dimensions, or
battle draw loops broadly.

## Current Blocker

The repo does not yet contain a deterministic no-popup battle-entry route. The
new probes can detect and summarize battle rows once battle is reached, but
battle-specific patches remain blocked until a hidden/runtime capture proves the
route.

## Next Steps

1. Build the `battlecenter` candidate under `C:\ClashTests\battlecenter`.
2. Run `patch_stage_report.py` for the new stage.
3. Run the catalog probe through `run_cdb_surface_dump.ps1` on a hidden desktop.
4. If the catalog probe does not reach battle, add a harness-only deterministic
   battle-entry route before adding any binary patch.
5. Once battle is reached, run the present and input probes.
6. Only then decide whether a native-center wrapper is needed.

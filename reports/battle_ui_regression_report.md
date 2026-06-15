# Battle UI Regression Report

Generated: 2026-05-15
Updated: 2026-05-20

The battlecenter stage has one battle-specific visual patch group:
`battle-ui-center-present-wrapper`. The separate `battlecenter-inputprobe`
stage adds validation-only `battle-grid-centered-input` and
`battle-ui-centered-input` wrappers for CDB proof.

## Required Regression Anchors

- Stable HD-map stage remains:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Castle/interior validation remains:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Battle validation stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
- Battle inputprobe validation stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe`

## Current Result

- Stable/default stage: unchanged.
- Castle/interior validation stage: unchanged.
- Battlecenter stage: patched candidate
  `C:\ClashTests\battlecenter-force-entry\clash95_hd_surfdump_20260518_221018.exe`
  has `136` patched bytes, `0` original, `0` unexpected in
  `captures\current\patch-stage-battlecenter-current.json`.
- Battle patches: `0042F2F5` calls cave `0051BA00`; the cave copies the native
  640x480 battle frame to scratch, clears the 800x600 target, copies back at
  `(80,60)`, then calls stock `Render_Present`.
- Runtime proof: `captures\archive\cdb-surface-dump-20260518-221018` is hidden-desktop,
  uses exact CDB `.writemem`, logs wrapper return `0051ba63`, and classifies
  `centered-native-640x480`.
- Command descriptor proof: `captures\archive\cdb-surface-dump-20260520-094032` is
  hidden-desktop, logs both `BATTLE_COMMAND_HIT coord_mode=visual result=2`
  and `BATTLE_COMMAND_NATIVE_HIT coord_mode=native result=2`, and is summarized
  by `captures\current\battle-ui-command-hit-current.md`.
- Command callback proof: `captures\archive\cdb-surface-dump-20260520-100717` is
  hidden-desktop, reaches descriptor `00514b78` and callback `0042d4e0`, and
  is summarized by `captures\current\battle-ui-command-callback-current.md`.
  The callback result is `branch=precondition-disabled` with `unit_type=5`,
  `avail=8`, and `enabled=0`.
- Enabled-command callback proof:
  `captures\archive\cdb-surface-dump-20260520-101859` is hidden-desktop, temporarily
  changes the selected unit to type `8`, records `avail=10`, `enabled=3`,
  skips the callback render-begin lock under CDB, reaches `branch=state2`, and
  is summarized by `captures\current\battle-ui-command-enabled-callback-current.md`.
- Tactical-grid coordinate proof:
  `captures\archive\cdb-surface-dump-20260520-103155` is hidden-desktop, reaches grid
  helper `0042CB50`, logs displayed `(144,108)` to cell `(1,1)` and native
  `(64,48)` to cell `(0,0)`, and is summarized by
  `captures\current\battle-ui-grid-hit-current.md`.
- Centered-input wrapper proof:
  `captures\archive\cdb-surface-dump-20260520-111115` is hidden-desktop, validates the
  inputprobe stage candidate SHA
  `F84933776944E2B616F6BBCCF7708ABBF06498D5438FA8DF7B7AF1BB56CD180A`, logs
  grid visual `(144,108)` to inner `(64,48)`, descriptor visual `(588,440)` to
  inner `(508,380)`, restores both visual coordinates, and is summarized by
  `captures\current\battle-ui-centered-input-current.md`.
- Post-ready redraw/copyback proof:
  `captures\archive\cdb-surface-dump-20260520-195244` is hidden-desktop, logs
  `BATTLE_READY`, 9 post-ready presents, 6 post-ready copybacks, a forced grid
  point `(144,108)->(64,48)`, final present return `0042CB46`, and is
  summarized by `captures\current\battle-ui-post-ready-redraw-current.md`.
- Command availability scan:
  `captures\current\battle-command-availability-current.md` parses 18 natural battle
  unit records from the post-ready proof log and the command availability table
  in `C:\Clash\clash95.exe`. The selected unit is type `5` with
  `availability=8`, `enabled=0`; naturally enabled unit count is `0`. The
  table scan through type `31` identifies 11 enabled unit types to target in a
  richer battle fixture: Dragon cavalry, Archer, Crossbower, Musketeer,
  Catapult, Cannon, Forester, Cyklop, Wizard, Winger, and Dragon.
- Save-slot scan:
  `captures\current\battle-slot-scan-current.md` aggregates six hidden CDB load-slot
  attempts. Slots `0`, `1`, and `2` route far enough to expose unit rows, but
  natural enabled command unit count remains `0`; slots `3`, `4`, and `5` time
  out before unit scan under the current route.
- Save-file inventory:
  `captures\current\battle-save-unit-inventory-current.md` reads all six local
  `C:\Clash\save\*.dat` files directly. The save unit layout starts at
  `0x00023EF6`, 16 bytes after the runtime game-data offset. It parses 63 units
  and natural enabled command unit count remains `0`; decoded local-save unit
  types are Peasant, Light infantry, Light cavalry, Highlander, and Builder.
- Constructed save fixture:
  `captures\current\battle-constructed-save-fixture-current.md` records the isolated
  copied-save mutation at save type offset `0x00023EFC`: unit index `0`, Light
  cavalry (`enabled=0`) to Dragon cavalry (`enabled=3`), written under
  `C:\ClashTests\battle-enabled-fixture-20260520-210728`.
- Constructed fixture unit scan:
  hidden CDB run `captures\archive\cdb-surface-dump-20260520-210816` loads slot `0`
  from the isolated work dir. `captures\current\battle-constructed-fixture-unit-scan-current.md`
  parses 18 unit rows and one naturally enabled unit: Dragon cavalry with
  `availability=10`, `enabled=3`.
- Constructed fixture command callback:
  hidden CDB run `captures\archive\cdb-surface-dump-20260520-220459` starts from
  displayed coordinate `(588,440)` in the battlecenter inputprobe stage,
  reaches pre-gate native `(508,380)`, then reaches `0042D4E0` with unit type
  `8`, `avail=10`, `enabled=3`, observes the click gate returning `eax=1`,
  records `branch=state1`, and has zero `BATTLE_COMMAND_FORCE_ENABLED_UNIT` or
  `BATTLE_COMMAND_CLICK_GATE_FORCE` rows. It no longer uses the pre-gate click
  rearm, direct render-begin skip, or hidden CDB/proxy `DD_IsLost` guard; it
  releases the synthetic click state and exits `Render_Begin` naturally on
  iteration `1`.
- Modal/input classification proof:
  `captures\archive\cdb-surface-dump-20260520-103714` is hidden-desktop, reaches
  battle loop input updater `004605D0`, logs
  `BATTLE_MODAL_CLASSIFIED status=input_update_seen_no_modal`, and is
  summarized by `captures\current\battle-ui-modal-classified-current.md`.
- Combined evidence matrix:
  `captures\current\battle-ui-evidence-current.md` passes repo-only checks over all
  focused battle summaries, the battlecenter and inputprobe patch-stage
  reports, constructed-fixture planning/runtime scan/command callback, and
  stable HD-map smoke evidence. It remains `validation_stage_only`.

Runtime battle regression remains incomplete until natural/manual
enabled-command cadence is classified in a richer battle state. The current
local saves do not provide that state. The centered input transform is
currently validation-proven only with helper bodies skipped after entry.

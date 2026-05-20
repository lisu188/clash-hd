# Battle UI Regression Report

Generated: 2026-05-15
Updated: 2026-05-20

The battlecenter stage now has one battle-specific patch group:
`battle-ui-center-present-wrapper`. It is scoped to the initial battle present
callsite only.

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
- Battlecenter stage: patched candidate
  `C:\ClashTests\battlecenter-force-entry\clash95_hd_surfdump_20260518_221018.exe`
  has `136` patched bytes, `0` original, `0` unexpected in
  `captures\patch-stage-battlecenter-current.json`.
- Battle patches: `0042F2F5` calls cave `0051BA00`; the cave copies the native
  640x480 battle frame to scratch, clears the 800x600 target, copies back at
  `(80,60)`, then calls stock `Render_Present`.
- Runtime proof: `captures\cdb-surface-dump-20260518-221018` is hidden-desktop,
  uses exact CDB `.writemem`, logs wrapper return `0051ba63`, and classifies
  `centered-native-640x480`.
- Command descriptor proof: `captures\cdb-surface-dump-20260520-094032` is
  hidden-desktop, logs both `BATTLE_COMMAND_HIT coord_mode=visual result=2`
  and `BATTLE_COMMAND_NATIVE_HIT coord_mode=native result=2`, and is summarized
  by `captures\battle-ui-command-hit-current.md`.
- Command callback proof: `captures\cdb-surface-dump-20260520-100717` is
  hidden-desktop, reaches descriptor `00514b78` and callback `0042d4e0`, and
  is summarized by `captures\battle-ui-command-callback-current.md`.
  The callback result is `branch=precondition-disabled` with `unit_type=5`,
  `avail=8`, and `enabled=0`.
- Enabled-command callback proof:
  `captures\cdb-surface-dump-20260520-101859` is hidden-desktop, temporarily
  changes the selected unit to type `8`, records `avail=10`, `enabled=3`,
  skips the callback render-begin lock under CDB, reaches `branch=state2`, and
  is summarized by `captures\battle-ui-command-enabled-callback-current.md`.
- Tactical-grid coordinate proof:
  `captures\cdb-surface-dump-20260520-103155` is hidden-desktop, reaches grid
  helper `0042CB50`, logs displayed `(144,108)` to cell `(1,1)` and native
  `(64,48)` to cell `(0,0)`, and is summarized by
  `captures\battle-ui-grid-hit-current.md`.
- Modal/input classification proof:
  `captures\cdb-surface-dump-20260520-103714` is hidden-desktop, reaches
  battle loop input updater `004605D0`, logs
  `BATTLE_MODAL_CLASSIFIED status=input_update_seen_no_modal`, and is
  summarized by `captures\battle-ui-modal-classified-current.md`.
- Combined evidence matrix:
  `captures\battle-ui-evidence-current.md` passes repo-only checks over all
  focused battle summaries, the battlecenter patch-stage report, and stable
  HD-map smoke evidence. It remains `validation_stage_only`.

Runtime battle regression remains incomplete until natural/manual
enabled-command cadence, actual centered input transforms, and later
battle-loop redraws are classified.

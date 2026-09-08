# Load Slot Route Limit Guard

- Status: PASS
- Generated: `2026-09-06T05:56:59+02:00`
- Runtime policy: repo-only; reads decompilation text, harness text, and existing hidden-desktop CDB artifacts; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only when static evidence still shows a ten-row local load menu and integer save-file checks, the current harness still computes row clicks from 166 + 22 * LoadSlot, archived slot 2 reaches LOADSAVE/PlayGame, and archived slots 3-5 plus the historical slot-5 right-bottom attempt all time out before force-select, force-accept, LOADSAVE, and PlayGame
- Promotion ready: `False`
- Static load rows: `0..9`
- Harness mouse formula: `x=320, y=166 + 22 * LoadSlot`
- Archived success slots: `[2]`
- Archived blocked slots: `[3, 4, 5]`
- Recent slot-5 blocked: `True`
- Cohort stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
- Cohort candidate SHA-256: `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`

## Boundary

static code and canonical harness geometry allow rows 0-9. This historical hidden diagnostic cohort proves the slot-2 row path and records rows 3-5 stalling before force-select/accept and LOADSAVE. These archived diagnostics do not reopen the subsequently resolved right-bottom work or prove current input.

## Slot Status

- `slot2_success`: `loads` run=`captures\archive\cdb-surface-dump-20260712-153805` mouse=`[320, 210]`
- `slot3_blocked`: `timeout_before_force_select_and_loadsave` run=`captures\archive\cdb-surface-dump-20260712-153827` mouse=`[320, 232]`
  Timeout stack: `C:\Users\andrz\git\clash-hd\scripts\cdb\..\..\captures\archive\cdb-surface-dump-20260712-153827\timeout-stack.log`
- `slot4_blocked`: `timeout_before_force_select_and_loadsave` run=`captures\archive\cdb-surface-dump-20260712-154103` mouse=`[320, 254]`
  Timeout stack: `C:\Users\andrz\git\clash-hd\scripts\cdb\..\..\captures\archive\cdb-surface-dump-20260712-154103\timeout-stack.log`
- `slot5_blocked`: `timeout_before_force_select_and_loadsave` run=`captures\archive\cdb-surface-dump-20260712-154340` mouse=`[320, 276]`
  Timeout stack: `C:\Users\andrz\git\clash-hd\scripts\cdb\..\..\captures\archive\cdb-surface-dump-20260712-154340\timeout-stack.log`
- `recent_slot5_blocked`: `timeout_before_force_select_and_loadsave` run=`captures\archive\cdb-surface-dump-20260712-153529` mouse=`[320, 276]`
  Timeout stack: `C:\Users\andrz\git\clash-hd\scripts\cdb\..\..\captures\archive\cdb-surface-dump-20260712-153529\timeout-stack.log`

## Next Proof Options

- historical diagnostic option: inspect why rows 3-5 stopped before the archived forced load-select breakpoint
- historical diagnostic option: use an isolated test working directory without editing C:\Clash\save
- direct-loader evidence remains non-natural route evidence; consult the current handoff before scheduling new work

![slot2 load route surface](C:\Users\andrz\git\clash-hd\scripts\cdb\..\..\captures\archive\cdb-surface-dump-20260712-153805\surface.png)

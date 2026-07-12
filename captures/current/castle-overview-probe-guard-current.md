# Castle Overview Probe Guard

- Overall: PASS
- Generated: `2026-07-12T20:34:49+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: focused overview hitbox proof must keep the descriptor-loop breakpoints, forbid the old crashing overview descriptor-input wrapper marker, and continue to prove the displayed-coordinate wrapper and click gate with no AV

## Probe Script

- Status: PASS
- Script: `probes\cdb\castle\clash95_castle_overview_hitbox_extra.cdb`

### Required Breakpoints

- `00422544`: PASS - raw hit-test result after the overview descriptor hitmap lookup
- `0042257E`: PASS - descriptor command/callback install row
- `00422590`: PASS - stock click gate result row
- `0042262C`: PASS - descriptor callback-call sentinel

### Required Markers

- `CASTLEOV_HITBOX_DISPLAYED_HITTEST_BEGIN`: PASS - displayed coordinates are installed before hit-test
- `CASTLEOV_HITBOX_DISPLAYED_RESULT`: PASS - displayed-coordinate raw hit result is logged
- `CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK`: PASS - displayed coordinates reached the target through the binary input wrapper
- `CASTLEOV_HITBOX_DESCRIPTOR_INSTALL`: PASS - descriptor command/callback is logged
- `CASTLEOV_HITBOX_CLICK_GATE`: PASS - stock click gate result is logged
- `CASTLEOV_HITBOX_CLICK_GATE_OK`: PASS - target click gate success is logged
- `CASTLEOV_HITBOX_CALLBACK_SUPPRESSED`: PASS - target callback is suppressed after proof
- `CASTLEOV_HITBOX_CALLBACK_CALL`: PASS - unexpected callback entry remains observable
- `CASTLEOV_HITBOX_SURFDUMP_READY`: PASS - surface dump ready row is emitted

## Focused Hitbox Log

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260712-144151`
- Log: `captures\archive\cdb-surface-dump-20260712-144151\cdb-surface-dump.log`
- Ready size: `[800, 600]`
- Overview post-draw: `{'main_surface': 167919320, 'main_size': [800, 600], 'overview_surface': 168342584, 'overview_size': [640, 480], 'owner_screen': 71026458, 'mouse': [371, 107], 'click_flag': 1, 'button0': 128}`
- Displayed result: `{'raw_hit': 248, 'adjusted_hit': 0, 'mouse': [371, 107], 'raw': [23744, 6848], 'target_raw': 248}`
- Descriptor: `{'command': 134, 'callback': 4521584, 'text': 3, 'arg_count': 5171110, 'owner_screen': 71026458, 'surface': 167919320, 'sz': [800, 600], 'mouse': [371, 107]}`
- Click gate: `{'command': 134, 'callback': 4521584, 'gate': 1, 'mouse': [371, 107], 'click_flag': 1, 'button0': 128}`
- Displayed hit ok: `True`
- Displayed wrapper ok: `True`
- Click gate ok: `True`
- Callback suppressed: `True`
- Callback called: `False`
- Access violations: `0`

## Forbidden Markers

- Status: PASS
- Markers: `CASTLECAT_OVERVIEW_DESC_INPUT_WRAPPER_ENTRY`, `OVERVIEW_DESC_INPUT_WRAPPER_ENTRY`

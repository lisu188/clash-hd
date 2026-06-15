# Right-Bottom Owner-Flag Inventory

- Overall: PASS
- Generated: `2026-06-15T22:35:48+02:00`
- Runtime policy: repo-only; scans existing CDB logs and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: right-bottom owner/action evidence must keep at least one controlled forced owner route, at least one current natural owner-flag-gated route, and no non-fixture archived natural route that already reaches the owner/action renderer without an explicit forced owner flag
- Scanned CDB logs: `172`
- Relevant runs: `80`
- Classification counts: `{'forced_owner_action_route': 64, 'natural_state_gated': 1, 'natural_ui_descriptor_only': 2, 'non_natural_isolated_fixture': 10, 'right_bottom_related': 3}`
- Natural state-gated routes: `1`
- Controlled forced owner/action routes: `64`
- Natural owner/action routes: `0`
- Non-natural isolated fixture routes: `10`
- Non-natural fixture owner/action rows: `9`

## Representative Runs

- `natural_state_gated`: `captures/archive/cdb-surface-dump-20260518-213418` stage `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter` classifications `['natural_state_gated']`
  Action descriptor: `{'slot': 'd1', 'x': 1000, 'y': 426, 'callback': '004338e0'}`
  Owner flag test: `{'owner_flag': '0x00', 'bit2': 0, 'bit1': 0, 'bit8': 0}`
- `forced_owner_action_route`: `captures/archive/cdb-surface-dump-20260506-160614` stage `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch` classifications `['forced_owner_action_route']`
- `natural_ui_descriptor_only`: `captures/archive/cdb-surface-dump-20260513-104200` stage `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch` classifications `['natural_ui_descriptor_only']`
- `non_natural_isolated_fixture`: `captures/archive/cdb-surface-dump-20260527-121204` stage `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter` classifications `['non_natural_isolated_fixture']`
  Proof class: `non_natural_isolated_fixture`

## First 30 Relevant Runs

- `captures/archive/cdb-surface-dump-20260506-150744`: `['right_bottom_related']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `[]`, owner-render `[]`
- `captures/archive/cdb-surface-dump-20260506-151242`: `['right_bottom_related']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `[]`, owner-render `[]`
- `captures/archive/cdb-surface-dump-20260506-160614`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260506-160758`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `[]`
- `captures/archive/cdb-surface-dump-20260506-175108`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260506-180501`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260506-180755`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260506-185203`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260506-190037`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260506-191042`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260506-200426`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260506-201114`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260511-084202`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-134458`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-134746`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-134947`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-141143`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-142147`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-142304`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-143741`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-144739`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-144934`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-145141`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-150643`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-151705`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-155526`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-155739`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-155910`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-160114`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260511-160221`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`

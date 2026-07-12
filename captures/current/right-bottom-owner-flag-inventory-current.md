# Right-Bottom Owner-Flag Inventory

- Overall: PASS
- Generated: `2026-07-12T20:34:16+02:00`
- Runtime policy: repo-only; scans existing CDB logs and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: right-bottom owner/action evidence must keep at least one controlled forced owner route, at least one current natural owner-flag-gated route, and no non-fixture archived natural route that already reaches the owner/action renderer without an explicit forced owner flag
- Scanned CDB logs: `26`
- Relevant runs: `12`
- Classification counts: `{'forced_owner_action_route': 7, 'natural_state_gated': 1, 'non_natural_isolated_fixture': 4}`
- Natural state-gated routes: `1`
- Controlled forced owner/action routes: `7`
- Natural owner/action routes: `0`
- Non-natural isolated fixture routes: `4`
- Non-natural fixture owner/action rows: `13`

## Representative Runs

- `natural_state_gated`: `captures/archive/cdb-surface-dump-20260712-150434` stage `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter` classifications `['natural_state_gated']`
  Action descriptor: `{'slot': 'd1', 'x': 1000, 'y': 426, 'callback': '004338e0'}`
  Owner flag test: `{'owner_flag': '0x00', 'bit2': 0, 'bit1': 0, 'bit8': 0}`
- `forced_owner_action_route`: `captures/archive/cdb-surface-dump-20260712-144445` stage `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all` classifications `['forced_owner_action_route']`
- `natural_ui_descriptor_only`: none
- `non_natural_isolated_fixture`: `captures/archive/cdb-surface-dump-20260527-193512` stage `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter` classifications `['non_natural_isolated_fixture']`
  Action descriptor: `{'slot': 'd1', 'x': 155, 'y': 426, 'callback': '004338e0'}`
  Owner flag test: `{'owner_flag': '0x0b', 'bit2': 2, 'bit1': 1, 'bit8': 8}`
  Proof class: `non_natural_isolated_fixture`

## First 12 Relevant Runs

- `captures/archive/cdb-surface-dump-20260527-193512`: `['non_natural_isolated_fixture']`, forced `[]`, actions `[]`, owner-render `['NOWNER']`
- `captures/archive/cdb-surface-dump-20260712-144445`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260712-144922`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260712-150240`: `['forced_owner_action_route']`, forced `[{'prefix': 'RBGRID', 'flag': '0x02'}]`, actions `['RBGRID']`, owner-render `['RBGRID']`
- `captures/archive/cdb-surface-dump-20260712-150434`: `['natural_state_gated']`, forced `[]`, actions `[]`, owner-render `[]`
- `captures/archive/cdb-surface-dump-20260712-151015`: `['forced_owner_action_route']`, forced `[{'prefix': 'APBARRACKS', 'flag': '0x02'}]`, actions `['APBARRACKS']`, owner-render `['APBARRACKS']`
- `captures/archive/cdb-surface-dump-20260712-154653`: `['non_natural_isolated_fixture']`, forced `[]`, actions `[]`, owner-render `[]`
- `captures/archive/cdb-surface-dump-20260712-154903`: `['non_natural_isolated_fixture']`, forced `[]`, actions `[]`, owner-render `['NOWNER']`
- `captures/archive/cdb-surface-dump-20260712-155528`: `['non_natural_isolated_fixture']`, forced `[]`, actions `[]`, owner-render `['NOWNER']`
- `captures/archive/cdb-surface-dump-20260712-160131`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260712-160204`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`
- `captures/archive/cdb-surface-dump-20260712-160351`: `['forced_owner_action_route']`, forced `[{'prefix': 'APPOST', 'flag': '0x02'}]`, actions `['APPOST']`, owner-render `['APPOST']`

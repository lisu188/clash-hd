# Battle UI Probe Summary

- Generated: `2026-05-20T09:43:57+02:00`
- Runtime policy: repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Log: `captures\cdb-surface-dump-20260520-094032\cdb-surface-dump.log`
- Candidate: `C:\ClashTests\battlecenter-command-hit\clash95_hd_surfdump_20260520_094032.exe`
- Candidate SHA-256: `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`
- Launch mode: `hidden-desktop`
- Hidden desktop: `True`
- Rows parsed: `35`
- Access violations: `0`
- Battle reached: `True`
- Battle ready: `True`
- Surface size: `[800, 600]`
- Visual mode: `centered-native-640x480`
- Centered offset: `[80, 60]`
- Centered wrapper seen: `True`
- Command descriptor found: `True`
- Command visual hit ok: `True`
- Command native hit ok: `True`
- Grid hit ok: `False`
- Modal classified: `False`

## Classification

- battle ready marker observed
- surface size classified as [800, 600]
- centered native battle visual offset is present
- battle command descriptor row observed
- battle visual command hit row observed
- battle tactical-grid hit proof was not observed
- battle modal path was not classified
- no access violation rows observed

## Screenshot

![battle UI surface](cdb-surface-dump-20260520-094032/surface.png)

## Recent Rows

- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00460e92 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0051ba63 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_READY source=BattleInitialPresent eip=0042f2fa ret=7370616d surface=0a07edd0 width=800 height=600 mouse=(116,166)`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00419316 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_COMMAND_SKIP_TURN_BANNER eip=0042e4b2 next=0042e4b7 player=0 mouse=(116,166)`
- line 214: `BATTLE_COMMAND_SKIP_TURN_FRAME eip=0042e4d9 next=0042e4fc mouse=(116,166)`
- line 214: `BATTLE_COMMAND_ATTEMPT coord_mode=visual displayed=(588,440) expected_native=(508,380) raw=(00009300,00006e00) scale=6 list=00514b78`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000044 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=004193fa src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00460e92 src=00544cd8 dst=000001b8 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_COMMAND_RESULT coord_mode=visual result=2 mouse=(120,440) native=(40,380)`
- line 214: `BATTLE_COMMAND_HIT coord_mode=visual result=2 callback=0042d4e0`
- line 214: `BATTLE_COMMAND_SKIP_TURN_FRAME eip=0042e4d9 next=0042e4fc mouse=(120,440)`
- line 214: `BATTLE_COMMAND_ATTEMPT coord_mode=native displayed=(508,380) expected_visual=(588,440) raw=(00007f00,00005f00) scale=6 list=00514b78`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000047 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=004193fa src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_PRESENT_CALL eip=00460ea0 ret=004193fa src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 214: `BATTLE_COMMAND_RESULT coord_mode=native result=2 mouse=(508,380) visual=(588,440)`
- line 214: `BATTLE_COMMAND_NATIVE_HIT coord_mode=native result=2 callback=0042d4e0`
- line 214: `SURFDUMP_READY redraw_seq=2 surface=0a07edd0 size=(800,600) base=0a320030 bytes=480000 Writing 75300 bytes...........................................................................................................................................................................................................................................`

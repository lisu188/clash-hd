# Battle UI Probe Summary

- Generated: `2026-05-20T11:11:55+02:00`
- Runtime policy: repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Log: `captures\archive\cdb-surface-dump-20260520-111115\cdb-surface-dump.log`
- Candidate: `C:\ClashTests\battle-inputprobe-runtime\clash95_hd_surfdump_20260520_111115.exe`
- Candidate SHA-256: `F84933776944E2B616F6BBCCF7708ABBF06498D5438FA8DF7B7AF1BB56CD180A`
- Launch mode: `hidden-desktop`
- Hidden desktop: `True`
- Rows parsed: `28`
- Access violations: `0`
- Battle reached: `True`
- Battle ready: `True`
- Surface size: `[800, 600]`
- Visual mode: `centered-native-640x480`
- Centered offset: `[80, 60]`
- Centered wrapper seen: `True`
- Command descriptor found: `False`
- Command visual hit ok: `False`
- Command native hit ok: `False`
- Command callback ok: `False`
- Command callback result ok: `False`
- Command render-begin skip seen: `False`
- Grid hit ok: `False`
- Grid input wrapper ok: `True`
- Descriptor input wrapper ok: `True`
- Centered input wrapper ok: `True`
- Modal classified: `False`

## Classification

- battle ready marker observed
- surface size classified as [800, 600]
- centered native battle visual offset is present
- battle command descriptor was not observed
- battle visual command hit proof was not observed
- battle command callback proof was not observed
- battle tactical-grid centered input wrapper restored coordinates
- battle grid and descriptor centered input wrappers both passed pre/inner/post checks
- battle modal path was not classified
- no access violation rows observed

## Screenshot

![battle UI surface](cdb-surface-dump-20260520-111115/surface.png)

## Recent Rows

- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00460e92 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0051ba63 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_READY source=BattleInitialPresent eip=0042f2fa ret=7370616d surface=0a2bb478 width=800 height=600 mouse=(116,166)`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00419316 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a2bb478 width=800 height=600`
- line 215: `BATTLE_COMMAND_SKIP_TURN_BANNER eip=0042e4b2 next=0042e4b7 player=0 mouse=(116,166)`
- line 215: `BATTLE_INPUTPROBE_GRID_PRE displayed=(144,108) expected_inner=(64,48) raw=(00002400,00001b00) scale=6 click_flag=00000001 button0=0x80`
- line 215: `BATTLE_INPUTPROBE_GRID_CAVE_ENTRY mouse=(144,108) raw=(00002400,00001b00)`
- line 215: `BATTLE_INPUTPROBE_GRID_INNER mouse=(64,48) expected=(64,48) cell=(0,0) restored=no forced_skip=1`
- line 215: `BATTLE_INPUTPROBE_GRID_POST result=0 mouse=(144,108) expected_restore=(144,108)`
- line 215: `BATTLE_INPUTPROBE_DESCRIPTOR_PRE displayed=(588,440) expected_inner=(508,380) raw=(00009300,00006e00) scale=6 list=00514b78 click_flag=00000001 button0=0x80`
- line 215: `BATTLE_INPUTPROBE_DESCRIPTOR_CAVE_ENTRY mouse=(588,440) raw=(00009300,00006e00)`
- line 215: `BATTLE_INPUTPROBE_DESCRIPTOR_INNER mouse=(508,380) expected=(508,380) list=00514b78 restored=no forced_skip=1`
- line 215: `BATTLE_INPUTPROBE_DESCRIPTOR_POST result=2 mouse=(588,440) expected_restore=(588,440)`
- line 215: `SURFDUMP_READY redraw_seq=5 surface=0a2bb478 size=(800,600) base=0a5a0030 bytes=480000 SURFDUMP_HOST_READY`

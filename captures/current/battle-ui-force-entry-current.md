# Battle UI Probe Summary

- Generated: `2026-05-18T22:13:35+02:00`
- Runtime policy: repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Log: `captures\archive\cdb-surface-dump-20260518-221018\cdb-surface-dump.log`
- Candidate: `C:\ClashTests\battlecenter-force-entry\clash95_hd_surfdump_20260518_221018.exe`
- Candidate SHA-256: `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`
- Launch mode: `hidden-desktop`
- Hidden desktop: `True`
- Rows parsed: `24`
- Access violations: `0`
- Battle reached: `True`
- Battle ready: `True`
- Surface size: `[800, 600]`
- Visual mode: `centered-native-640x480`
- Centered offset: `[80, 60]`
- Centered wrapper seen: `True`
- Command descriptor found: `True`
- Command hit ok: `False`
- Grid hit ok: `False`
- Modal classified: `False`

## Classification

- battle ready marker observed
- surface size classified as [800, 600]
- centered native battle visual offset is present
- battle command descriptor row observed
- battle command hit proof was not observed
- battle tactical-grid hit proof was not observed
- battle modal path was not classified
- no access violation rows observed

## Screenshot

![battle UI surface](cdb-surface-dump-20260518-221018\surface.png)

## Recent Rows

- line 210: `BATTLE_ROUTE_CANDIDATE name=Unit_Attack_calls_BattleRunner eip=0041b145 ret=00000000 attacker_ptr=04023f16 defender_ptr=04024a6a result_ptr=00000000 stack_arg=00000000 ebp=04023f16 surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_OWNER_ENTRY source=BattleRunner eip=0042e9e0 ret=0041b14a attacker=04023f16 defender=04024a6a result_ptr=00000000 building_ptr=00000000 ebp=04023f16 surface=0a265a98 width=800 height=600 mouse=(320,166)`
- line 210: `BATTLE_SURFACE ptr=0a265a98 width=800 height=600 pitch=0 base=0a5a0030 mode=unknown`
- line 210: `BATTLE_DESCRIPTOR desc=00514b78 x=498 y=370 w=0 h=0 callback=0042d4e0 source=draw_list render=0051d4c0 surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_COPYBACK_CALL eip=00460bb0 ret=004317f3 src=00544cd8 dst=000001f2 x=624 y=10 w=0 h=0 surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_COPYBACK_CALL eip=00460bb0 ret=004229f0 src=00544cd8 dst=000000a0 x=473 y=467 w=0 h=0 surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_COPYBACK_CALL eip=00460bb0 ret=004317f3 src=00544cd8 dst=000001f2 x=624 y=10 w=0 h=0 surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_COPYBACK_CALL eip=00460bb0 ret=004229f0 src=00544cd8 dst=000000a0 x=473 y=467 w=0 h=0 surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_COPYBACK_CALL eip=00460bb0 ret=004317f3 src=00544cd8 dst=000001f2 x=624 y=10 w=0 h=0 surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_COPYBACK_CALL eip=00460bb0 ret=004229f0 src=00544cd8 dst=000000a0 x=473 y=467 w=0 h=0 surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_COPYBACK_CALL eip=00460b20 ret=004e99f3 src=00544cd8 dst=00000000 x=640 y=0 w=0 h=0 surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00460e92 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0051ba63 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a265a98 width=800 height=600`
- line 210: `BATTLE_READY source=BattleInitialPresent eip=0042f2fa ret=7370616d surface=0a265a98 width=800 height=600 mouse=(116,166)`
- line 210: `BATTLE_SURFACE ptr=0a265a98 width=800 height=600 pitch=0 base=0a5a0030 mode=hd-surface-unclassified`
- line 210: `SURFDUMP_READY redraw_seq=1 surface=0a265a98 size=(800,600) base=0a5a0030 bytes=480000 Writing 75300 bytes...........................................................................................................................................................................................................................................`

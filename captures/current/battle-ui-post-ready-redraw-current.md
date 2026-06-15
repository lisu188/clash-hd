# Battle UI Probe Summary

- Generated: `2026-05-20T19:53:16+02:00`
- Runtime policy: repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Log: `captures\archive\cdb-surface-dump-20260520-195244\cdb-surface-dump.log`
- Candidate: `C:\ClashTests\battle-postready-redraw\clash95_hd_surfdump_20260520_195244.exe`
- Candidate SHA-256: `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`
- Launch mode: `hidden-desktop`
- Hidden desktop: `True`
- Rows parsed: `41`
- Access violations: `0`
- Battle reached: `True`
- Battle ready: `True`
- Surface size: `[800, 600]`
- Visual mode: `centered-native-640x480`
- Centered offset: `[80, 60]`
- Centered wrapper seen: `True`
- Command descriptor found: `True`
- Command visual hit ok: `False`
- Command native hit ok: `False`
- Command callback ok: `False`
- Command callback result ok: `False`
- Command render-begin skip seen: `False`
- Grid hit ok: `False`
- Grid input wrapper ok: `False`
- Descriptor input wrapper ok: `False`
- Centered input wrapper ok: `False`
- Post-ready presents: `9`
- Post-ready copybacks: `6`
- Post-ready grid attempts: `1`
- Post-ready redraw sample ok: `True`
- Modal classified: `False`

## Classification

- battle ready marker observed
- surface size classified as [800, 600]
- centered native battle visual offset is present
- battle command descriptor row observed
- battle visual command hit proof was not observed
- battle command callback proof was not observed
- battle tactical-grid hit proof was not observed
- battle post-ready redraw/present sample observed
- battle modal path was not classified
- no access violation rows observed

## Screenshot

![battle UI surface](cdb-surface-dump-20260520-195244/surface.png)

## Recent Rows

- line 203: `BATTLE_COPYBACK_CALL eip=00460bb0 ret=004229f0 src=00544cd8 dst=000000a0 x=473 y=467 w=0 h=0 surface=0a07ed90 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a07ed90 width=800 height=600`
- line 203: `BATTLE_COPYBACK_CALL eip=00460b20 ret=004e99f3 src=00544cd8 dst=00000000 x=640 y=0 w=0 h=0 surface=0a07ed90 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00460e92 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a07ed90 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0051ba63 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a07ed90 width=800 height=600`
- line 203: `BATTLE_READY source=BattleInitialPresent eip=0042f2fa ret=7370616d surface=0a07ed90 width=800 height=600 mouse=(116,166)`
- line 203: `BATTLE_POSTREADY_COPYBACK seq=1 eip=00460bb0 ret=00419277 src=00544cd8 dst=000001f2 x=561 y=370 surface=0a07ed90 size=(800,600)`
- line 203: `BATTLE_POSTREADY_PRESENT seq=1 eip=00460ea0 ret=00419316 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07ed90 size=(800,600) copybacks=1`
- line 203: `BATTLE_POSTREADY_PRESENT seq=2 eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07ed90 size=(800,600) copybacks=1`
- line 203: `BATTLE_POSTREADY_COPYBACK seq=2 eip=00460bb0 ret=004317f3 src=00544cd8 dst=000001f2 x=624 y=10 surface=0a07ed90 size=(800,600)`
- line 203: `BATTLE_POSTREADY_PRESENT seq=3 eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07ed90 size=(800,600) copybacks=2`
- line 203: `BATTLE_POSTREADY_COPYBACK seq=3 eip=00460bb0 ret=004229f0 src=00544cd8 dst=000000a0 x=473 y=467 surface=0a07ed90 size=(800,600)`
- line 203: `BATTLE_POSTREADY_PRESENT seq=4 eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a07ed90 size=(800,600) copybacks=3`
- line 203: `BATTLE_COMMAND_SKIP_TURN_BANNER eip=0042e4b2 next=0042e4b7 player=0 mouse=(116,166)`
- line 203: `BATTLE_POSTREADY_GRID_ATTEMPT displayed=(144,108) native=(64,48) raw=(00002400,00001b00) scale=6 click_flag=00000001 button0=0x80 presents=4 copybacks=3`
- line 203: `BATTLE_POSTREADY_COPYBACK seq=4 eip=00460b20 ret=004e99f3 src=00544cd8 dst=00000000 x=640 y=0 surface=0a07ed90 size=(800,600)`
- line 203: `BATTLE_POSTREADY_PRESENT seq=5 eip=00460ea0 ret=00460e92 src=00544cd8 dst=0000006c rect=(0,0,800,600) surface=0a07ed90 size=(800,600) copybacks=4`
- line 203: `BATTLE_POSTREADY_COPYBACK seq=5 eip=00460bb0 ret=004317f3 src=00544cd8 dst=000001f2 x=624 y=10 surface=0a07ed90 size=(800,600)`
- line 203: `BATTLE_POSTREADY_PRESENT seq=6 eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07ed90 size=(800,600) copybacks=5`
- line 203: `BATTLE_POSTREADY_COPYBACK seq=6 eip=00460bb0 ret=004229f0 src=00544cd8 dst=000000a0 x=473 y=467 surface=0a07ed90 size=(800,600)`
- line 203: `BATTLE_POSTREADY_PRESENT seq=7 eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a07ed90 size=(800,600) copybacks=6`
- line 203: `BATTLE_POSTREADY_PRESENT seq=8 eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07ed90 size=(800,600) copybacks=6`
- line 203: `BATTLE_POSTREADY_PRESENT seq=9 eip=00460ea0 ret=0042cb46 src=00544cd8 dst=00000000 rect=(0,0,800,600) surface=0a07ed90 size=(800,600) copybacks=6`
- line 203: `BATTLE_POSTREADY_SUMMARY presents=9 copybacks=6 surface=0a07ed90 size=(800,600) base=0a320030 bytes=480000 last_ret=0042cb46`
- line 203: `SURFDUMP_READY redraw_seq=6 surface=0a07ed90 size=(800,600) base=0a320030 bytes=480000 SURFDUMP_HOST_READY`

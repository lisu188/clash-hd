# Battle UI Probe Summary

- Generated: `2026-05-20T10:42:58+02:00`
- Runtime policy: repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Log: `captures\cdb-surface-dump-20260520-103155\cdb-surface-dump.log`
- Candidate: `C:\ClashTests\battlecenter-grid-hit\clash95_hd_surfdump_20260520_103155.exe`
- Candidate SHA-256: `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`
- Launch mode: `hidden-desktop`
- Hidden desktop: `True`
- Rows parsed: `177`
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
- Grid hit ok: `True`
- Modal classified: `False`

## Classification

- battle ready marker observed
- surface size classified as [800, 600]
- centered native battle visual offset is present
- battle command descriptor row observed
- battle visual command hit proof was not observed
- battle command callback proof was not observed
- battle tactical-grid hit row observed
- battle modal path was not classified
- no access violation rows observed

## Screenshot

![battle UI surface](cdb-surface-dump-20260520-103155/surface.png)

## Recent Rows

- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0042cb46 src=00544cd8 dst=00000000 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0042cb46 src=00544cd8 dst=00000000 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0042cb46 src=00544cd8 dst=00000000 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0042cb46 src=00544cd8 dst=00000000 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0042cb46 src=00544cd8 dst=00000000 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430c08 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00460e92 src=00544cd8 dst=0000006c rect=(0,0,800,600) surface=0a17b458 width=800 height=600`
- line 208: `BATTLE_GRID_RESULT coord_mode=visual result=5524696 displayed=(144,108) native=(64,48) cell=(1,1) map_cell=(1,1) occupant=65535 selected=0 current=0`
- line 208: `BATTLE_GRID_ATTEMPT coord_mode=native displayed=(64,48) expected_visual=(144,108) raw=(00001000,00000c00) click_flag=00000001 button0=0x80 scale=6`
- line 208: `BATTLE_GRID_HIT coord_mode=1 displayed=(64,48) native=(-16,-12) cell=(0,0) map_cell=(0,0) occupant=65535 selected=0 current=0 state_attack=0 state_charge=0 click_flag=00000001 button0=0x80`
- line 208: `SURFDUMP_READY redraw_seq=4 surface=0a17b458 size=(800,600) base=0a460030 bytes=480000 SURFDUMP_HOST_READY`

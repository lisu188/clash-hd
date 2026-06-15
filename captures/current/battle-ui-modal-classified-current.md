# Battle UI Probe Summary

- Generated: `2026-05-20T10:42:58+02:00`
- Runtime policy: repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Log: `captures\archive\cdb-surface-dump-20260520-103714\cdb-surface-dump.log`
- Candidate: `C:\ClashTests\battlecenter-modal-classified\clash95_hd_surfdump_20260520_103714.exe`
- Candidate SHA-256: `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`
- Launch mode: `hidden-desktop`
- Hidden desktop: `True`
- Rows parsed: `22`
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
- Modal classified: `True`

## Classification

- battle ready marker observed
- surface size classified as [800, 600]
- centered native battle visual offset is present
- battle command descriptor row observed
- battle visual command hit proof was not observed
- battle command callback proof was not observed
- battle tactical-grid hit proof was not observed
- battle modal path was classified without a hit
- no access violation rows observed

## Screenshot

![battle UI surface](cdb-surface-dump-20260520-103714/surface.png)

## Recent Rows

- line 222: `BATTLE_ROUTE_CANDIDATE name=Unit_Attack_calls_BattleRunner eip=0041b145 ret=00000000 attacker_ptr=03f83f16 defender_ptr=03f84a6a result_ptr=00000000 stack_arg=00000000 ebp=03f83f16 surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_OWNER_ENTRY source=BattleRunner eip=0042e9e0 ret=0041b14a attacker=03f83f16 defender=03f84a6a result_ptr=00000000 building_ptr=00000000 ebp=03f83f16 surface=0a07edd0 width=800 height=600 mouse=(320,166)`
- line 222: `BATTLE_SURFACE ptr=0a07edd0 width=800 height=600 pitch=0 base=0a320030 mode=unknown`
- line 222: `BATTLE_DESCRIPTOR desc=00514b78 x=498 y=370 w=0 h=0 callback=0042d4e0 source=draw_list render=0051d4c0 surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00460e92 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0051ba63 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_READY source=BattleInitialPresent eip=0042f2fa ret=7370616d surface=0a07edd0 width=800 height=600 mouse=(116,166)`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00419316 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a07edd0 width=800 height=600`
- line 222: `BATTLE_COMMAND_SKIP_TURN_BANNER eip=0042e4b2 next=0042e4b7 player=0 mouse=(116,166)`
- line 222: `BATTLE_MODAL_CLASSIFIED status=input_update_seen_no_modal eip=004605d0 ret=0042e4ed displayed=(116,166) native=(36,106) scale=6 state_attack=0 state_charge=0 surface=0a07edd0 width=800 height=600`
- line 222: `SURFDUMP_READY redraw_seq=5 surface=0a07edd0 size=(800,600) base=0a320030 bytes=480000 SURFDUMP_HOST_READY`

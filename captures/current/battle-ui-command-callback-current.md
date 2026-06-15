# Battle UI Probe Summary

- Generated: `2026-05-20T10:08:10+02:00`
- Runtime policy: repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Log: `captures\archive\cdb-surface-dump-20260520-100717\cdb-surface-dump.log`
- Candidate: `C:\ClashTests\battlecenter-command-callback\clash95_hd_surfdump_20260520_100717.exe`
- Candidate SHA-256: `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`
- Launch mode: `hidden-desktop`
- Hidden desktop: `True`
- Rows parsed: `27`
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
- Command callback ok: `True`
- Command callback result ok: `True`
- Grid hit ok: `False`
- Modal classified: `False`

## Classification

- battle ready marker observed
- surface size classified as [800, 600]
- centered native battle visual offset is present
- battle command descriptor row observed
- battle visual command hit proof was not observed
- battle command callback result row observed
- battle tactical-grid hit proof was not observed
- battle modal path was not classified
- no access violation rows observed

## Screenshot

![battle UI surface](cdb-surface-dump-20260520-100717/surface.png)

## Recent Rows

- line 215: `BATTLE_SURFACE ptr=0a57edd0 width=800 height=600 pitch=0 base=0a820030 mode=unknown`
- line 215: `BATTLE_DESCRIPTOR desc=00514b78 x=498 y=370 w=0 h=0 callback=0042d4e0 source=draw_list render=0051d4c0 surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00460e92 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0051ba63 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_READY source=BattleInitialPresent eip=0042f2fa ret=7370616d surface=0a57edd0 width=800 height=600 mouse=(116,166)`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00419316 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=0a57edd0 width=800 height=600`
- line 215: `BATTLE_COMMAND_SKIP_TURN_BANNER eip=0042e4b2 next=0042e4b7 player=0 mouse=(116,166)`
- line 215: `BATTLE_COMMAND_SKIP_TURN_FRAME eip=0042e4d9 next=0042e4fc mouse=(116,166)`
- line 215: `BATTLE_COMMAND_ATTEMPT coord_mode=native-click displayed=(508,380) expected_visual=(588,440) raw=(00007f00,00005f00) click_flag=00000001 button0=0x80 scale=6 list=00514b78 BATTLE_COMMAND_REARM_PRE_GATES desc=00514b78 state=0x01 hover_cb=004191f0 click_cb=0042d4e0 type=0x01 mouse=(508,380) click_flag=00000001 button0=0x80 BATTLE_COMMAND_CLICK_GATE desc=00514b78 desc_xy=(498,370) state=0x01 hover_cb=004191f0 click_cb=0042d4e0 mouse=(508,380) click_flag=00000001 button0=0x80`
- line 215: `BATTLE_COMMAND_CLICK_GATE_FORCE desc=00514b78 forced_eax=1 desc_xy=(498,370) state=0x01 click_cb=0042d4e0 mouse=(508,380) click_flag=00000001 button0=0x80 BATTLE_COMMAND_CLICK_GATE_RET desc=00514b78 click_gate=1 click_cb=0042d4e0 state=0x01 mouse=(508,380) click_flag=00000001`
- line 215: `BATTLE_COMMAND_DESCRIPTOR_CALLBACK desc=00514b78 callback=0042d4e0 desc_xy=(498,370) state=0x01 mouse=(508,380) d53205c=0 d532060=0 d514b80=1`
- line 215: `BATTLE_COMMAND_CALLBACK eip=0042d4e0 ret=00419c60 desc=00514b78 state=0x01 displayed=(508,380) unit_index=0 unit_type=5 avail=8 enabled=0 d53205c_before=0 d532060=0 d514b80=1`
- line 215: `BATTLE_COMMAND_CALLBACK_RESULT branch=precondition-disabled desc=00514b78 state=0x01 unit_index=0 unit_type=5 avail=8 enabled=0 d53205c=0 d532060=0 d514b80=1 surface=0a57edd0 size=(800,600)`
- line 215: `SURFDUMP_READY redraw_seq=3 surface=0a57edd0 size=(800,600) base=0a820030 bytes=480000 SURFDUMP_HOST_READY`

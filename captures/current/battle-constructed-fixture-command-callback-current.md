# Battle UI Probe Summary

- Generated: `2026-05-20T22:06:41+02:00`
- Runtime policy: repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Log: `captures\archive\cdb-surface-dump-20260520-220459\cdb-surface-dump.log`
- Candidate: `C:\ClashTests\battle-enabled-fixture-20260520-210728\candidate\clash95_hd_surfdump_20260520_220459.exe`
- Candidate SHA-256: `F84933776944E2B616F6BBCCF7708ABBF06498D5438FA8DF7B7AF1BB56CD180A`
- Launch mode: `hidden-desktop`
- Hidden desktop: `True`
- Rows parsed: `34`
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
- Command render-begin skip seen: `False`
- Command render-begin enter seen: `True`
- Command rearm pre-gates seen: `False`
- Command pre-gates seen: `True`
- Command synthetic release seen: `True`
- Render-begin guard seen: `False`
- Render-begin exit seen: `True`
- Grid hit ok: `False`
- Grid input wrapper ok: `False`
- Descriptor input wrapper ok: `False`
- Centered input wrapper ok: `False`
- Post-ready presents: `0`
- Post-ready copybacks: `0`
- Post-ready grid attempts: `0`
- Post-ready redraw sample ok: `False`
- Modal classified: `False`

## Classification

- battle ready marker observed
- surface size classified as [800, 600]
- centered native battle visual offset is present
- battle command descriptor row observed
- battle visual command hit proof was not observed
- battle command callback result row observed
- battle command callback render-begin call entered and exited naturally
- synthetic click state was released before render-begin
- battle command click survived to pre-gate without rearm
- battle tactical-grid hit proof was not observed
- battle modal path was not classified
- no access violation rows observed

## Screenshot

![battle UI surface](cdb-surface-dump-20260520-220459/surface.png)

## Recent Rows

- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=08e25d18 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=08e25d18 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=08e25d18 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00460e92 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=08e25d18 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=0051ba63 src=00544cd8 dst=000000a6 rect=(0,0,800,600) surface=08e25d18 width=800 height=600`
- line 203: `BATTLE_READY source=BattleInitialPresent eip=0042f2fa ret=7370616d surface=08e25d18 width=800 height=600 mouse=(116,166)`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00419316 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=08e25d18 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00430dd3 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=08e25d18 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00431828 src=00544cd8 dst=00000002 rect=(0,0,800,600) surface=08e25d18 width=800 height=600`
- line 203: `BATTLE_PRESENT_CALL eip=00460ea0 ret=00422a81 src=00544cd8 dst=00000059 rect=(0,0,800,600) surface=08e25d18 width=800 height=600`
- line 203: `BATTLE_COMMAND_SKIP_TURN_BANNER eip=0042e4b2 next=0042e4b7 player=0 mouse=(116,166)`
- line 203: `BATTLE_COMMAND_SKIP_TURN_FRAME eip=0042e4d9 next=0042e4fc mouse=(116,166)`
- line 203: `BATTLE_COMMAND_ATTEMPT coord_mode=visual-click displayed=(588,440) expected_native=(508,380) raw=(00009300,00006e00) click_flag=00000001 button0=0x80 scale=6 list=00514b78`
- line 203: `BATTLE_COMMAND_PRE_GATES desc=00514b78 state=0x02 hover_cb=004191f0 click_cb=0042d4e0 type=0x01 mouse=(508,380) click_flag=00000001 button0=0x80 BATTLE_COMMAND_CLICK_GATE desc=00514b78 desc_xy=(498,370) state=0x02 hover_cb=004191f0 click_cb=0042d4e0 mouse=(508,380) click_flag=00000001 button0=0x80`
- line 203: `BATTLE_COMMAND_CLICK_GATE_OBSERVED desc=00514b78 eax=1 desc_xy=(498,370) state=0x02 click_cb=0042d4e0 mouse=(508,380) click_flag=00000001 button0=0x80 BATTLE_COMMAND_CLICK_GATE_RET desc=00514b78 click_gate=1 click_cb=0042d4e0 state=0x02 mouse=(508,380) click_flag=00000001`
- line 203: `BATTLE_COMMAND_DESCRIPTOR_CALLBACK desc=00514b78 callback=0042d4e0 desc_xy=(498,370) state=0x02 mouse=(508,380) d53205c=1 d532060=0 d514b80=2`
- line 203: `BATTLE_COMMAND_CALLBACK eip=0042d4e0 ret=00419c60 desc=00514b78 state=0x02 displayed=(508,380) unit_index=0 unit_type=8 avail=10 enabled=3 d53205c_before=1 d532060=0 d514b80=2`
- line 203: `BATTLE_COMMAND_RENDER_BEGIN_ENTER eip=0042d520 call=004609d0 desc=00514b78 unit_type=8 avail=10 enabled=3`
- line 203: `BATTLE_COMMAND_SYNTHETIC_RELEASE eip=0042d520 old_click_flag=00000001 old_button0=0x80 desc=00514b78 unit_type=8`
- line 203: `BATTLE_RENDER_BEGIN_ENTER eip=004609d0 surface=00544cd8 desc=00514b78 unit_type=8 avail=10 enabled=3`
- line 203: `BATTLE_RENDER_BEGIN_LOOP iter=1 eip=004609e0 dd_is_flipping=0 desc=00514b78 unit_type=8`
- line 203: `BATTLE_RENDER_BEGIN_LOST_CHECK iter=1 eip=004609fc dd_is_lost=0 guard=0 desc=00514b78 unit_type=8`
- line 203: `BATTLE_RENDER_BEGIN_EXIT eip=00460a00 iter=1 guard=0 desc=00514b78 unit_type=8 result=0`
- line 203: `BATTLE_COMMAND_CALLBACK_RESULT branch=state1 desc=00514b78 state=0x01 d53205c=0 d532060=0 d514b80=1 surface=08e25d18 size=(800,600)`
- line 203: `SURFDUMP_READY redraw_seq=3 surface=08e25d18 size=(800,600) base=0a460030 bytes=480000 SURFDUMP_HOST_READY`

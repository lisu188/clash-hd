# Descriptor Trace Summary

- Log: `captures\cdb-surface-dump-20260506-092608\cdb-surface-dump.log`
- Ready: True
- AV rows: 0
- Scanned `dword_511D40` entries: 6
- Drawn `dword_511D40` entries: 6
- Skipped `dword_511D40` entries: 0

## Classification
- sub_40A400 reached descriptor drawer
- dword_511D40 entries were scanned without x>=640 skips
- dword_511D40 entries reached their draw callbacks
- generic descriptor draw ran but no direct 004024E0 helper call was observed

## Marker Counts
- DESC_40A400_ENTRY: 1
- DESC_40A400_CALL_419D80: 1
- DESC_40A400_AFTER_419D80: 1
- DESC_SINGLE_419D60_ENTRY: 0
- DESC_419D80_ENTRY: 1
- DESC_SCAN: 6
- DESC_SKIP_X640: 0
- DESC_DRAW: 6
- DESC_DRAWCALL_4191F0: 6
- DESC_DRAWCALL_4191F0_PRESENT1: 6
- DESC_DRAWCALL_4191F0_PRESENT2: 0
- DESC_PRESENT_4191F0: 0
- DESC_419DC0_ENTRY: 18
- DESC_419DC0_SWITCH_TO_MAP: 0
- DESC_419DC0_RESTORE_META: 0
- SURFDUMP_PLAYGAME: 1
- SURFDUMP_READY: 1
- AV_SURFDUMP: 0

## Draw Callbacks
- 004191f0: scanned 6, drawn 6

## First Drawn Descriptors
- ptr=00511d40 x=416 y=400 flags=0x01 draw=004191f0 hit=00409d80 is511d40=1
- ptr=00511d75 x=480 y=400 flags=0x01 draw=004191f0 hit=00409df0 is511d40=1
- ptr=00511daa x=544 y=400 flags=0x01 draw=004191f0 hit=00409f00 is511d40=1
- ptr=00511ddf x=416 y=432 flags=0x01 draw=004191f0 hit=0040a040 is511d40=1
- ptr=00511e14 x=480 y=432 flags=0x01 draw=004191f0 hit=0040a0e0 is511d40=1
- ptr=00511e49 x=544 y=432 flags=0x01 draw=004191f0 hit=0040a000 is511d40=1

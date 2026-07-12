# Right-Bottom Constructed Save Fixture

- Generated: `2026-07-12T15:36:00+02:00`
- Runtime policy: save fixture planner; reads one source save; never edits C:\Clash\save; writes copied save only when --output-save is supplied; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Source save: `C:\Clash\save\0.dat`
- Output save: `None`
- Dry run: `True`
- Wrote output: `False`
- Source SHA-256: `4F2182409D209985A527F07C4116B19E44332416698D6ACB0A3D35AE68DB8A89`
- Patched SHA-256: `33BFD39E34181FA7CB6566DA2B8FC7B50A5668A9D8B3AC93659391E0A11C5B6F`
- Selection mode: `auto` (player index 0)

## Planned Change

| Building index | (x,y) | Owner | addon_flags offset | Old flags | New flags | Action eligible |
| ---: | --- | ---: | --- | --- | --- | --- |
| 0 | (14,20) | 0 | `0x0007C89A` | `0x00` | `0x02` | True |

## Disassembly Citations

- clash95.c:49999 addon_flags & 0x02 render gate
- clash95.c:34186 Building_New(1,...) sets bit 0x02
- clash95.c:61809 SaveSlot_LoadGame verbatim bulk restore
- docs/SAVE_DAT_FORMAT.md row 509674 building records, stride 467

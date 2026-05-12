# Patch Manifest Comparison

- Left: `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-20260424.json`
- Right: `captures\patch-stage-mapdraw-partial12-20260424.json`
- Records: left=114 right=114 common=114 added=0 removed=0 changed=3
- Diffs: metadata=2 groups=0 records=3
- Nonpatched: left=0 right=0

## Metadata Changes

- `exe`: `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_dynvswitch_20260424.exe` -> `C:\Clash\clash95_hd_mapdraw_partial12_20260424.exe`
- `exe_sha256`: `C98709257AF61E7EF87F1B71650F07A5EC2F6A3EB2B74DA0D708C2D39FE90CCD` -> `3053BC41079ECBCE6CD91D7ECE3C430666B3361F5DF7CF679042789D5A5A8182`

## Changed Records

### 0x017DFF

- Fields: new, actual, note

| Side | Group | Status | Old | New | Actual | Note |
| --- | --- | --- | --- | --- | --- | --- |
| left | full-redraw-12x9 | patched | `06` | `09` | `09` | 0x418700 clipped bottom row columns 6 -> 9 |
| right | full-redraw-12x9 | patched | `06` | `0C` | `0C` | 0x418700 clipped bottom row columns 6 -> 12 |

### 0x017EDB

- Fields: new, actual, note

| Side | Group | Status | Old | New | Actual | Note |
| --- | --- | --- | --- | --- | --- | --- |
| left | helpers | patched | `06` | `09` | `09` | single-tile repaint last-row X cutoff 6 -> 9 |
| right | helpers | patched | `06` | `0C` | `0C` | single-tile repaint last-row X cutoff 6 -> 12 |

### 0x0E8DC0

- Fields: new, actual

| Side | Group | Status | Old | New | Actual | Note |
| --- | --- | --- | --- | --- | --- | --- |
| left | viewport-switch-dynamic-surface | patched | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `81 FA A0 96 51 00 74 0A 68 E0 01 00 00 B9 80 02 00 00 EB 0A 68 58 02 00 00 B9 20 03 00 00 8B 46 3C 31 DB 31 D2 C7 40 20 00 00 00 00 89 F0 E8 2D 71 F7 FF E9 3F 74 F7 FF 00 00 00 00 00 00 00 00` | `81 FA A0 96 51 00 74 0A 68 E0 01 00 00 B9 80 02 00 00 EB 0A 68 58 02 00 00 B9 20 03 00 00 8B 46 3C 31 DB 31 D2 C7 40 20 00 00 00 00 89 F0 E8 2D 71 F7 FF E9 3F 74 F7 FF 00 00 00 00 00 00 00 00` | 0x4E99C0 code cave: use 800x600 for map metadata 005196A0, else native 640x480 |
| right | viewport-switch-dynamic-surface | patched | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `81 FA A0 96 51 00 74 0C 68 E0 01 00 00 B9 80 02 00 00 EB 0A 68 58 02 00 00 B9 20 03 00 00 8B 46 3C 31 DB 31 D2 C7 40 20 00 00 00 00 89 F0 E8 2D 71 F7 FF E9 3F 74 F7 FF 00 00 00 00 00 00 00 00` | `81 FA A0 96 51 00 74 0C 68 E0 01 00 00 B9 80 02 00 00 EB 0A 68 58 02 00 00 B9 20 03 00 00 8B 46 3C 31 DB 31 D2 C7 40 20 00 00 00 00 89 F0 E8 2D 71 F7 FF E9 3F 74 F7 FF 00 00 00 00 00 00 00 00` | 0x4E99C0 code cave: use 800x600 for map metadata 005196A0, else native 640x480 |

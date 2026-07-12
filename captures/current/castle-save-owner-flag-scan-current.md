# Castle Save Owner-Flag Scan

- Overall: PASS
- Generated: `2026-07-12T20:47:09+02:00`
- Runtime policy: local save metadata inspection only; reads installed save files but does not copy raw saves, launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: finds whether any installed save naturally has castle owner flag bit 0x02 set, which is required before the 004338E0 owner/action lane can be routed without debugger-forced owner flags
- Saves root: `C:\Clash\save`
- Known owner-block offset checked: `0x07C6FA`
- Save files scanned: `6`
- Plausible owner blocks: `6`
- Active records in plausible blocks: `22`
- Records with any owner flag: `9`
- Action-eligible records (`flags_1a0 & 0x02`): `7`
- Recommended route target: `C:\Clash\save\2.dat offset 0x07C6FA index 1 pos (1,23) owner 1 flags_1a0 0x16`
- Current blocker: `none`

## Plausible Blocks

- `C:\Clash\save\0.dat` offset `0x07C6FA` active `4` any-owner-flag `0` bit2 `0` flags_1a0 `0x00`
- `C:\Clash\save\1.dat` offset `0x07C6FA` active `4` any-owner-flag `0` bit2 `0` flags_1a0 `0x00`
- `C:\Clash\save\2.dat` offset `0x07C6FA` active `2` any-owner-flag `2` bit2 `1` flags_1a0 `0x01, 0x16`
- `C:\Clash\save\3.dat` offset `0x07C6FA` active `2` any-owner-flag `2` bit2 `1` flags_1a0 `0x01, 0x16`
- `C:\Clash\save\4.dat` offset `0x07C6FA` active `5` any-owner-flag `0` bit2 `0` flags_1a0 `0x00`
- `C:\Clash\save\5.dat` offset `0x07C6FA` active `5` any-owner-flag `5` bit2 `5` flags_1a0 `0x0B, 0x17, 0x1F`

## Action-Eligible Records

- `C:\Clash\save\2.dat` offset `0x07C6FA` index `1` pos `(1,23)` owner `1` flags_1a0 `0x16` flags_1a4 `0x00` byte_4 `2`
- `C:\Clash\save\3.dat` offset `0x07C6FA` index `1` pos `(1,23)` owner `1` flags_1a0 `0x16` flags_1a4 `0x00` byte_4 `2`
- `C:\Clash\save\5.dat` offset `0x07C6FA` index `0` pos `(14,20)` owner `0` flags_1a0 `0x0B` flags_1a4 `0x01` byte_4 `2`
- `C:\Clash\save\5.dat` offset `0x07C6FA` index `1` pos `(90,7)` owner `1` flags_1a0 `0x17` flags_1a4 `0x00` byte_4 `2`
- `C:\Clash\save\5.dat` offset `0x07C6FA` index `2` pos `(60,46)` owner `2` flags_1a0 `0x1F` flags_1a4 `0x00` byte_4 `2`
- `C:\Clash\save\5.dat` offset `0x07C6FA` index `3` pos `(90,72)` owner `3` flags_1a0 `0x1F` flags_1a4 `0x00` byte_4 `2`
- `C:\Clash\save\5.dat` offset `0x07C6FA` index `4` pos `(47,80)` owner `4` flags_1a0 `0x1F` flags_1a4 `0x00` byte_4 `2`

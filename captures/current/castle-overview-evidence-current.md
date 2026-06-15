# Castle Overview Evidence Matrix

- Overall: FAIL
- Generated: `2026-06-15T22:14:23+02:00`
- Stage: `castlecenter-all`
- Promotion status: `validation_stage_only`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, or visible windows

## Patch Stage

- Status: FAIL
- Executable: `C:\ClashTests\cdb-castle-overview-nativerender-flags1f-multihit\clash95_hd_surfdump_20260515_105557.exe`
- Resolved stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- SHA-256: `None`
- Patches: patched=? original=? unexpected=? total=?

## Overview Visual

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260515-105041`
- Commands: 0x63, 0x86, 0x87, 0x99, 0x9C, 0x9F, 0xA6
- Surface size: `[800, 600]`
- Centered geometry: PASS

![castle overview surface](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260515-105041\surface.png)

## Input Hitboxes

- Focused command `0x86`: PASS
- Focused displayed wrapper proof: `True`
- Visible commands `0x86`, `0x63`, `0x87`: PASS
- Visible target completion: `index 0 0x86/0xF8 completion=True, index 1 0x63/0xFE completion=True, index 2 0x87/0xFF completion=True`
- Dormant commands `0x99`, `0x9C`, `0x9F`, `0xA6`: PASS
- Dormant target completion: `index 0 0x99/0xFA completion=True, index 1 0x9C/0xFB completion=True, index 2 0x9F/0xFC completion=True, index 3 0xA6/0xFD completion=True`

## Owner/Hitmap State

- Current owner records: PASS
- Active records: `4`
- Interesting feature-flag records: `0`
- Forced owner-feature hitmap: PASS
- Present forced raw IDs: 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF

## Additional Screenshots

![focused overview hitbox surface](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260515-105411\surface.png)

![visible-command overview multi-hit surface](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260515-105458\surface.png)

![dormant-command overview multi-hit surface](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260515-105557\surface.png)

## Failures

- patch_stage: candidate executable does not exist: C:\ClashTests\cdb-castle-overview-nativerender-flags1f-multihit\clash95_hd_surfdump_20260515_105557.exe

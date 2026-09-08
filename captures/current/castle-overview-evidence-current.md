# Castle Overview Evidence Matrix

- Overall: FAIL
- Generated: `2026-09-08T11:21:09+02:00`
- Stage: `castlecenter-all`
- Promotion status: `validation_stage_only`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, or visible windows

## Patch Stage

- Status: PASS
- Executable: `C:\ClashTests\cdb-castle-overview-nativerender\clash95_hd_surfdump_20260712_144019.exe`
- Source: `reports\castlecenter_all_patch_stage_20260712_144019.json`
- Archived report: `True`
- Resolved stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- SHA-256: `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`
- Patches: patched=134 original=0 unexpected=0 total=134

## Overview Visual

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260712-144019`
- Commands: 0x63, 0x86, 0x87, 0x99, 0x9C, 0x9F, 0xA6
- Surface size: `[800, 600]`
- Centered geometry: PASS

![castle overview surface](C:\Users\andrz\.codex\worktrees\7d0c\clash-hd\captures\archive\cdb-surface-dump-20260712-144019\surface.png)

## Input Hitboxes

- Focused command `0x86`: PASS
- Focused displayed wrapper proof: `True`
- Visible commands `0x86`, `0x63`, `0x87`: PASS
- Visible target completion: `index 0 0x86/0xF8 completion=True, index 1 0x63/0xFE completion=True, index 2 0x87/0xFF completion=True`
- Dormant commands `0x99`, `0x9C`, `0x9F`, `0xA6`: PASS
- Dormant target completion: `index 0 0x99/0xFA completion=True, index 1 0x9C/0xFB completion=True, index 2 0x9F/0xFC completion=True, index 3 0xA6/0xFD completion=True`

## Owner/Hitmap State

- Current owner records: FAIL
- Active records: `None`
- Interesting feature-flag records: `None`
- Forced owner-feature hitmap: FAIL
- Present forced raw IDs:

## Additional Screenshots

![focused overview hitbox surface](C:\Users\andrz\.codex\worktrees\7d0c\clash-hd\captures\archive\cdb-surface-dump-20260712-144151\surface.png)

![visible-command overview multi-hit surface](C:\Users\andrz\.codex\worktrees\7d0c\clash-hd\captures\archive\cdb-surface-dump-20260712-144245\surface.png)

![dormant-command overview multi-hit surface](C:\Users\andrz\.codex\worktrees\7d0c\clash-hd\captures\archive\cdb-surface-dump-20260712-144327\surface.png)

## Failures

- owner_records: missing owner records raw dump: captures\current\castle-owner-records-current.raw
- forced_hitmap: missing forced hitmap raw dump: captures\archive\castle-overview-hitmap-flags1f.raw

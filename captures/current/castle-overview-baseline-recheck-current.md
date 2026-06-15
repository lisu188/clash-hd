# Castle Overview Baseline Recheck

- Overall: FAIL
- Generated: `2026-06-15T22:36:03+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows

## Overview Visual Baseline

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260515-105041`
- Surface size: `[800, 600]`
- Overview post-draw size: `[800, 600]`
- Commands: 0x63, 0x86, 0x87, 0x99, 0x9C, 0x9F, 0xA6
- Centered geometry: PASS
- Barracks baseline through overview gate: PASS

## Barracks Controlled Stop Baseline

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260512-082418`
- Ready: `True`
- Descriptor click: `True`
- Controlled 004356c0 stop: `True`
- Failure exits: `0`
- Access violations: `0`

## Latest Castle Overview Matrix

- Status: FAIL
- Stage: `castlecenter-all`
- Promotion status: `validation_stage_only`
- Candidate SHA-256: `None`
- Patches: patched=? original=? unexpected=? total=?
- Visible target completion: index 0 0x86/0xF8 completion=True, index 1 0x63/0xFE completion=True, index 2 0x87/0xFF completion=True
- Dormant target completion: index 0 0x99/0xFA completion=True, index 1 0x9C/0xFB completion=True, index 2 0x9F/0xFC completion=True, index 3 0xA6/0xFD completion=True

## Failures

- latest_castle_overview_matrix: patch_stage: candidate executable does not exist: C:\ClashTests\cdb-castle-overview-nativerender-flags1f-multihit\clash95_hd_surfdump_20260515_105557.exe

## Screenshot

![castle overview baseline](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260515-105041\surface.png)

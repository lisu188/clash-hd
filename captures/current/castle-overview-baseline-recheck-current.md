# Castle Overview Baseline Recheck

- Overall: PASS
- Generated: `2026-07-18T10:18:05+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows

## Overview Visual Baseline

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260712-144019`
- Surface size: `[800, 600]`
- Overview post-draw size: `[800, 600]`
- Commands: 0x63, 0x86, 0x87, 0x99, 0x9C, 0x9F, 0xA6
- Centered geometry: PASS
- Barracks baseline through overview gate: PASS

## Barracks Controlled Stop Baseline

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260712-144445`
- Ready: `True`
- Descriptor click: `True`
- Controlled 004356c0 stop: `True`
- Failure exits: `0`
- Access violations: `0`

## Latest Castle Overview Matrix

- Status: PASS
- Stage: `castlecenter-all`
- Promotion status: `validation_stage_only`
- Candidate SHA-256: `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`
- Patches: patched=134 original=0 unexpected=0 total=134
- Visible target completion: index 0 0x86/0xF8 completion=True, index 1 0x63/0xFE completion=True, index 2 0x87/0xFF completion=True
- Dormant target completion: index 0 0x99/0xFA completion=True, index 1 0x9C/0xFB completion=True, index 2 0x9F/0xFC completion=True, index 3 0xA6/0xFD completion=True

## Screenshot

![castle overview baseline](C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-144019\surface.png)

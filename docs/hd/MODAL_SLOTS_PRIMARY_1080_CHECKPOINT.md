# Hidden primary checkpoint at 1920x1080: retained F failure

The September 13 F run **failed**. Its initial and complete final traces passed,
but the three-sample primary audit rejected overlapping memory-region claims.
Generated PNGs and matching bytes do not establish primary pixel correctness.

The small, candidate-bound record is
[`captures/current/modal-slots-primary-1920x1080-20260913.json`](../../captures/current/modal-slots-primary-1920x1080-20260913.json).
It binds the original reports, scripts, packet, source snapshot, captures and
preservation checks. Raw captures and proprietary files remain outside the
repository at
`C:/ClashCaptures/hd-completion/slots-primary-1920x1080-20260913-f/`.

## Identity and original result

- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-modalslots-validation`.
- Resolution: `1920x1080`; recipe: `owned_barracks_dirty_slots_v1`.
- Candidate SHA-256: `32dea2c12a9a2afd2e2856c327cf3d610e2d02061d2d00960255228a6d6fa688`.
- Route: barracks, castle index 0, controlled `construct_all` availability.
- Capture: paused hidden-CDB reads through the pinned nonpresenting proxy;
  debugger-controlled native dispatch, without OS input.

The original `summary.json` retains:

> Three matched primary/native/physical snapshots failed source-bound validation.

The original `primary-audit.json` retains:

> primary triplet: overlapping memory-region claims

This was an explicit audit failure, with an audit report produced. It was not
the earlier D run's offline-validator timeout. D's timeout and separate strict
header failure remain preserved and are not superseded by F.

## Bounded observations

The initial map trace, twelve-slot trace and primary Lock sequence passed in
the original evaluator reports. The complete final trace also passed and its
raw log preserves the paused prefix. This checkpoint cross-checks those
existing reports and hashes; it does not rerun the game or reconstruct traces.

All three recorded primary region lists contain both
`[0x0420d000, 0x0429f000)` and `[0x0429e000, 0x0429f000)`, with committed,
read-write attributes. These are distinct claims sharing the final 4096-byte
page. The strict reader rejects them. Their origin needs a separate producer
investigation; the original claims have not been removed, merged or rewritten.

The three samples have identical hashes within each native, physical, primary,
attached-palette and primary-PNG layer. This establishes retained byte
stability only. It does not establish correct placement, complete composition,
frame borders, modal controls, visible-wrapper colors or real input.

The retained cleanup identities match the recorded debugger and child. Their
receipts report both processes absent, both retained handles closed, and the
hidden desktop closed. The checkpoint made no independent native process query.

All 41 saved source files and their 41 current counterparts matched the F
preflight during review. The original executable was unchanged. The live save
directory retained exactly 15 unchanged files; the isolated save directory
retained exactly four, with no added or missing files. The review rechecked
214 bound files without finding a changed artifact.

The primary triplet remains unaccepted. Primary composition, ordinary/manual
controls, modal destruction and exit, healthy map return, continuity,
endurance and release eligibility remain incomplete. The protected stage and
800x600 launcher default remain unchanged.

# Right-Bottom Controlled Grid Hit

- Status: PASS
- Generated: `2026-07-18T10:17:28+02:00`
- Runtime policy: existing hidden-desktop CDB/proxy evidence only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Run: `captures\archive\cdb-surface-dump-20260712-150240`
- Log: `captures\archive\cdb-surface-dump-20260712-150240\cdb-surface-dump.log`
- Screenshot: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-150240\surface.png`
- Screenshot policy: diagnostic CDB/proxy frame only; not visual acceptance proof for the final action-menu layout.
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- Candidate SHA-256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- Surface: `[800, 600]`
- Fast-forward startup: `True`
- Map validation skipped: `True`
- Grid hit ok: `True`
- Last grid entry: `[450, 73]`
- Last grid result: `0`
- Forced hidden flip gates: `1`
- Failure exits: `0`
- Draw rows: `5`
- AV count: `0`

## Classification

- native grid coordinate was installed by the probe
- right-bottom owner/action route entered 00435BC0
- right-bottom panel/grid/status/action drawing rows fired
- hidden-desktop DD flip gate was reached
- hidden-desktop DD flip gate was debugger-forced
- right-bottom grid hit-test was reached
- grid hit-test returned expected cell 0 at native coordinate (450, 73)
- grid result was accepted and the probe armed loop exit
- grid selection update was not observed
- surface dump reached ready state

# HD Hidden-CDB Host Soak Report

- **environment=hidden_cdb_host** (never a visible-runtime or guest soak)
- Evidence class: `approved_hidden_cdb_host_soak`
- Overall: FAIL
- Generated: `2026-09-05T11:42:50.643517+00:00`
- Tier / route: `custom` / `map-idle`
- Duration seconds: `7200`
- Sample interval seconds: `30`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-114207-433-map-idle`

## Honesty contract

- Input responsiveness: `not_applicable_hidden` (hidden-desktop run delivers no user input; responsiveness cannot be measured and is recorded as the sentinel, never fabricated)
- FORCED entry (disclosed): `cdb_breakpoint_forced_loader_entry` load_slot=2
- Pan mechanism (disclosed): `none` forced=False events=0
- Surface base / read method: `0x0a4d0030` / `host_readprocessmemory`
- Memory-only proxy SHA / present_enabled: `CC702F8C0556917A596C73E65F5F1621EC6F34AF80E9340BDDDC8D05D5104BB6` / `False`
- Nonblack definition: percent of surface bytes with a nonzero 8-bit palette index, computed from real ReadProcessMemory surface bytes (palette index 0 is the engine clear color)

## Render evidence (real ReadProcessMemory surface reads)

- Frame samples: `239`
- Unique frame hashes (computed from rows): `221`
- Frame stability class: `progressing`
- Nonblack min/max: `97.339` / `97.34`
- Unique sampled colors min/max: `166` / `198`
- Heartbeats: `383`

## Host process metrics (required)

- Process samples: `239`
- Working set growth bytes: `409600`
- Private memory growth bytes: `225280`
- Handle growth: `-5`
- Process exited unexpectedly: `False`
- Clean stop: `False` (`verified_game_and_cdb_termination`)
- Artifact bytes: `4079414` (limit `262144000`)

## Edge frames

- frame-0001: nonblack=97.34 colors=166 hash=b70cad486105b226f695a6c1e993e915925d69546861747947c7edb014ac5a86
  ![frame-0001](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-114207-433-map-idle\frames\frame-0001.png)
- frame-0002: nonblack=97.339 colors=198 hash=ee89880c6cc28b20c1ded82a563e362d4f84deab553a6b83d159f1cb679a60c7
  ![frame-0002](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-114207-433-map-idle\frames\frame-0002.png)
- frame-0003: nonblack=97.339 colors=198 hash=8f4987ae3a30a243d3de223e96caa10f17bb8a687327305ae79a7ff25bc96292
  ![frame-0003](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-114207-433-map-idle\frames\frame-0003.png)
- frame-0237: nonblack=97.339 colors=197 hash=acbc7a44641a13025bd18eea19156f06e654b1b9c507585ebcc03de2956caa44
  ![frame-0237](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-114207-433-map-idle\frames\frame-0237.png)
- frame-0238: nonblack=97.339 colors=197 hash=ade358e6579684b199005ce1001f3af93e5eb837c18f04d80f79df336c6545b9
  ![frame-0238](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-114207-433-map-idle\frames\frame-0238.png)
- frame-0239: nonblack=97.339 colors=198 hash=c0502abc4c7b8c8bfd78badec974879e134743924eb517083d98b9a1badd4b9c
  ![frame-0239](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-114207-433-map-idle\frames\frame-0239.png)

## Failures

- failed to stop process 1336: process 1336 did not exit within 5 seconds
- cleanup contains 1 error(s)
- the harness did not stop the run cleanly after SOAK_ROUTE_END

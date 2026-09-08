# HD Hidden-CDB Host Soak Report

- **environment=hidden_cdb_host** (never a visible-runtime or guest soak)
- Evidence class: `approved_hidden_cdb_host_soak`
- Overall: PASS
- Generated: `2026-09-05T09:38:35.366898+00:00`
- Tier / route: `short30` / `map-pan`
- Duration seconds: `1800`
- Sample interval seconds: `15`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-110757-602-map-pan`

## Honesty contract

- Input responsiveness: `not_applicable_hidden` (hidden-desktop run delivers no user input; responsiveness cannot be measured and is recorded as the sentinel, never fabricated)
- FORCED entry (disclosed): `cdb_breakpoint_forced_loader_entry` load_slot=2
- Pan mechanism (disclosed): `cdb_forced_scroll_write` forced=True events=179
- Surface base / read method: `0x0a610030` / `host_readprocessmemory`
- Memory-only proxy SHA / present_enabled: `CD3859E82F8920FD4B081EA5313282994707AA4CBBF0DFB9E0589D2DE59C71B2` / `False`
- Nonblack definition: percent of surface bytes with a nonzero 8-bit palette index, computed from real ReadProcessMemory surface bytes (palette index 0 is the engine clear color)

## Render evidence (real ReadProcessMemory surface reads)

- Frame samples: `119`
- Unique frame hashes (computed from rows): `119`
- Frame stability class: `progressing`
- Nonblack min/max: `97.339` / `97.341`
- Unique sampled colors min/max: `197` / `206`
- Heartbeats: `96`

## Host process metrics (required)

- Process samples: `119`
- Working set growth bytes: `192512`
- Private memory growth bytes: `0`
- Handle growth: `-10`
- Process exited unexpectedly: `False`
- Clean stop: `True` (`verified_game_and_cdb_termination`)
- Artifact bytes: `4084869` (limit `262144000`)

## Edge frames

- frame-0001: nonblack=97.339 colors=197 hash=a552d1df23619cded3f400cae01ee2719adc22f700c4726683107ef7037b981c
  ![frame-0001](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-110757-602-map-pan\frames\frame-0001.png)
- frame-0002: nonblack=97.34 colors=206 hash=4facb6bc86d6011049c5a2600294f70b8c9ee829801fa742405e39b0141939cc
  ![frame-0002](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-110757-602-map-pan\frames\frame-0002.png)
- frame-0003: nonblack=97.34 colors=201 hash=7e22bae39c011abf3d5fa1b347902b56d7d3b8dd59551b8515831b48d6f3a1fa
  ![frame-0003](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-110757-602-map-pan\frames\frame-0003.png)
- frame-0117: nonblack=97.341 colors=200 hash=459e4ff5a289f9cda01659f418052155a7fcb7aac6a1d435d213ffb970fe3121
  ![frame-0117](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-110757-602-map-pan\frames\frame-0117.png)
- frame-0118: nonblack=97.341 colors=200 hash=24c4feea042eb3f0134b169df4d81f76e0ff2b29073a2e58691bfe5c23d71c11
  ![frame-0118](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-110757-602-map-pan\frames\frame-0118.png)
- frame-0119: nonblack=97.341 colors=200 hash=f0c56e6c2aa51b9aceed916469d84971c5d074b44936c5710bdb7610910e0d04
  ![frame-0119](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-110757-602-map-pan\frames\frame-0119.png)

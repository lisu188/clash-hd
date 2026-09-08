# HD Hidden-CDB Host Soak Report

- **environment=hidden_cdb_host** (never a visible-runtime or guest soak)
- Evidence class: `approved_hidden_cdb_host_soak`
- Overall: PASS
- Generated: `2026-09-05T08:11:17.443827+00:00`
- Tier / route: `short10` / `map-pan`
- Duration seconds: `600`
- Sample interval seconds: `15`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-100041-704-map-pan`

## Honesty contract

- Input responsiveness: `not_applicable_hidden` (hidden-desktop run delivers no user input; responsiveness cannot be measured and is recorded as the sentinel, never fabricated)
- FORCED entry (disclosed): `cdb_breakpoint_forced_loader_entry` load_slot=2
- Pan mechanism (disclosed): `cdb_forced_scroll_write` forced=True events=59
- Surface base / read method: `0x0a390030` / `host_readprocessmemory`
- Memory-only proxy SHA / present_enabled: `0B66979CFC512198F9205E6590FD85D6BA2137DB2D6C17BFB223EF300BFFE655` / `False`
- Nonblack definition: percent of surface bytes with a nonzero 8-bit palette index, computed from real ReadProcessMemory surface bytes (palette index 0 is the engine clear color)

## Render evidence (real ReadProcessMemory surface reads)

- Frame samples: `41`
- Unique frame hashes (computed from rows): `41`
- Frame stability class: `progressing`
- Nonblack min/max: `97.34` / `97.34`
- Unique sampled colors min/max: `164` / `166`
- Heartbeats: `32`

## Host process metrics (required)

- Process samples: `41`
- Working set growth bytes: `200704`
- Private memory growth bytes: `208896`
- Handle growth: `-6`
- Process exited unexpectedly: `False`
- Clean stop: `True` (`verified_game_and_cdb_termination`)
- Artifact bytes: `3896428` (limit `262144000`)

## Edge frames

- frame-0001: nonblack=97.34 colors=166 hash=b90ffb293ea463b1d662334e8cb52c02ab1ea83b5afb4951444e7d18cafc7036
  ![frame-0001](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-100041-704-map-pan\frames\frame-0001.png)
- frame-0002: nonblack=97.34 colors=166 hash=f40e21d478af7a63c8ed090cc2c94f0e76b244a81dd412bbc38c4b46ad8fe8ac
  ![frame-0002](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-100041-704-map-pan\frames\frame-0002.png)
- frame-0003: nonblack=97.34 colors=165 hash=d3720453de7def6a5328dce99ac4357cf15a3115c1645fe0635d2d096a2838cf
  ![frame-0003](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-100041-704-map-pan\frames\frame-0003.png)
- frame-0039: nonblack=97.34 colors=164 hash=15bb26cd1164497455c0bc27f4f4e11500dad475e1449e4b3a3e868c247ffd32
  ![frame-0039](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-100041-704-map-pan\frames\frame-0039.png)
- frame-0040: nonblack=97.34 colors=164 hash=1c16572a837f09a36d0d9b37df68680be5e091496b698273cc53f54b32e0dd7b
  ![frame-0040](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-100041-704-map-pan\frames\frame-0040.png)
- frame-0041: nonblack=97.34 colors=164 hash=03f6ec59b7fbb72396f9e535c5abc23f819c8a1be2fd4c7adbc766247d68c80e
  ![frame-0041](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-100041-704-map-pan\frames\frame-0041.png)

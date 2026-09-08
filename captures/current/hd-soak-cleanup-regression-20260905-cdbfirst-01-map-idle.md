# HD Hidden-CDB Host Soak Report

- **environment=hidden_cdb_host** (never a visible-runtime or guest soak)
- Evidence class: `approved_hidden_cdb_host_soak`
- Overall: PASS
- Generated: `2026-09-05T12:06:11.169579+00:00`
- Tier / route: `short2` / `map-idle`
- Duration seconds: `120`
- Sample interval seconds: `10`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-140338-409-map-idle`

## Honesty contract

- Input responsiveness: `not_applicable_hidden` (hidden-desktop run delivers no user input; responsiveness cannot be measured and is recorded as the sentinel, never fabricated)
- FORCED entry (disclosed): `cdb_breakpoint_forced_loader_entry` load_slot=2
- Pan mechanism (disclosed): `none` forced=False events=0
- Surface base / read method: `0x0a390030` / `host_readprocessmemory`
- Memory-only proxy SHA / present_enabled: `8DE4D268A1E284AD6CBC17CB5A06EAA26FC5D2D7797CE1C07FE788489EB6B7F4` / `False`
- Nonblack definition: percent of surface bytes with a nonzero 8-bit palette index, computed from real ReadProcessMemory surface bytes (palette index 0 is the engine clear color)

## Render evidence (real ReadProcessMemory surface reads)

- Frame samples: `13`
- Unique frame hashes (computed from rows): `13`
- Frame stability class: `progressing`
- Nonblack min/max: `97.339` / `97.34`
- Unique sampled colors min/max: `166` / `198`
- Heartbeats: `6`

## Host process metrics (required)

- Process samples: `13`
- Working set growth bytes: `45056`
- Private memory growth bytes: `106496`
- Handle growth: `-6`
- Process exited unexpectedly: `False`
- Clean stop: `True` (`verified_game_and_cdb_termination`)
- Artifact bytes: `3939767` (limit `262144000`)

## Edge frames

- frame-0001: nonblack=97.34 colors=166 hash=497a00ae335ee8f675cd78f44f879b7b5fad62a4d714c8bda46c2356693785a5
  ![frame-0001](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-140338-409-map-idle\frames\frame-0001.png)
- frame-0002: nonblack=97.34 colors=166 hash=15c02447287d707841476496caf94e4de44dc26de72c582a64a2f6724edbe4e1
  ![frame-0002](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-140338-409-map-idle\frames\frame-0002.png)
- frame-0003: nonblack=97.34 colors=166 hash=1ed0675a01b07d18d0d49b29d9612503cbd725f9d02b16bf74f0efcdbfacc905
  ![frame-0003](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-140338-409-map-idle\frames\frame-0003.png)
- frame-0011: nonblack=97.34 colors=166 hash=d2b3b1352506f197209f8f4eb2eb75f0f3752892c80bc8ef7afe8f494ba556c9
  ![frame-0011](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-140338-409-map-idle\frames\frame-0011.png)
- frame-0012: nonblack=97.339 colors=198 hash=85db77318866176d1fec5cd7d937698f63520cdb751f13c503c70b2b0d661c83
  ![frame-0012](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-140338-409-map-idle\frames\frame-0012.png)
- frame-0013: nonblack=97.339 colors=198 hash=ec8f928d418ed4fdf1e9b03351b96ecd4288f13e43b55f209a471250ef003fea
  ![frame-0013](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-140338-409-map-idle\frames\frame-0013.png)

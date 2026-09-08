# HD Hidden-CDB Host Soak Report

- **environment=hidden_cdb_host** (never a visible-runtime or guest soak)
- Evidence class: `approved_hidden_cdb_host_soak`
- Overall: PASS
- Generated: `2026-09-05T07:58:43.424019+00:00`
- Tier / route: `short10` / `map-idle`
- Duration seconds: `600`
- Sample interval seconds: `15`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-094801-748-map-idle`

## Honesty contract

- Input responsiveness: `not_applicable_hidden` (hidden-desktop run delivers no user input; responsiveness cannot be measured and is recorded as the sentinel, never fabricated)
- FORCED entry (disclosed): `cdb_breakpoint_forced_loader_entry` load_slot=2
- Pan mechanism (disclosed): `none` forced=False events=0
- Surface base / read method: `0x0a390030` / `host_readprocessmemory`
- Memory-only proxy SHA / present_enabled: `B4C39141C1C743F13DA1F899E4CD377023C85C71161DA2ADC8C92BD29E33A6AA` / `False`
- Nonblack definition: percent of surface bytes with a nonzero 8-bit palette index, computed from real ReadProcessMemory surface bytes (palette index 0 is the engine clear color)

## Render evidence (real ReadProcessMemory surface reads)

- Frame samples: `41`
- Unique frame hashes (computed from rows): `32`
- Frame stability class: `progressing`
- Nonblack min/max: `97.339` / `97.34`
- Unique sampled colors min/max: `166` / `198`
- Heartbeats: `33`

## Host process metrics (required)

- Process samples: `41`
- Working set growth bytes: `110592`
- Private memory growth bytes: `-102400`
- Handle growth: `-9`
- Process exited unexpectedly: `False`
- Clean stop: `True` (`verified_game_and_cdb_termination`)
- Artifact bytes: `4054990` (limit `262144000`)

## Edge frames

- frame-0001: nonblack=97.34 colors=166 hash=c99d50dcc43963d0ee9d4b5a6e1b6a1ca037df6b1e4d6697d31e626c8dddfff2
  ![frame-0001](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-094801-748-map-idle\frames\frame-0001.png)
- frame-0002: nonblack=97.339 colors=197 hash=7b7de4dc3a4b2370b0f35417ad01d8076d6c5fb9345f45a9bde5e7ba021fee88
  ![frame-0002](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-094801-748-map-idle\frames\frame-0002.png)
- frame-0003: nonblack=97.339 colors=197 hash=26bef1017d67d6f5ad8055857b6c66177bcd153a3aa290d601466cc05d0c582b
  ![frame-0003](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-094801-748-map-idle\frames\frame-0003.png)
- frame-0039: nonblack=97.339 colors=198 hash=6b5c32255118436e7bd79bde71d8380b42fb03638b484134a80b051437f329de
  ![frame-0039](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-094801-748-map-idle\frames\frame-0039.png)
- frame-0040: nonblack=97.339 colors=197 hash=0b0434b31f666c9ab8c32f7ebd25fa6191b35d8267a8174ca4f911eb2069862a
  ![frame-0040](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-094801-748-map-idle\frames\frame-0040.png)
- frame-0041: nonblack=97.339 colors=197 hash=302a0e5a0861ff082f6e7d734295daaef89cefca71ca224d837462b3e44c9d06
  ![frame-0041](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-094801-748-map-idle\frames\frame-0041.png)

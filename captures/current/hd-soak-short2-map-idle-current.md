# HD Hidden-CDB Host Soak Report

- **environment=hidden_cdb_host** (never a visible-runtime or guest soak)
- Evidence class: `approved_hidden_cdb_host_soak`
- Overall: PASS
- Generated: `2026-09-05T07:32:55.491107+00:00`
- Tier / route: `short2` / `map-idle`
- Duration seconds: `120`
- Sample interval seconds: `15`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-092939-516-map-idle`

## Honesty contract

- Input responsiveness: `not_applicable_hidden` (hidden-desktop run delivers no user input; responsiveness cannot be measured and is recorded as the sentinel, never fabricated)
- FORCED entry (disclosed): `cdb_breakpoint_forced_loader_entry` load_slot=2
- Pan mechanism (disclosed): `none` forced=False events=0
- Surface base / read method: `0x0ac90030` / `host_readprocessmemory`
- Memory-only proxy SHA / present_enabled: `78E52FE74888CBB57496D7ADF006F6DA53DE98039ADE14246932BED05B38CC07` / `False`
- Nonblack definition: percent of surface bytes with a nonzero 8-bit palette index, computed from real ReadProcessMemory surface bytes (palette index 0 is the engine clear color)

## Render evidence (real ReadProcessMemory surface reads)

- Frame samples: `9`
- Unique frame hashes (computed from rows): `9`
- Frame stability class: `progressing`
- Nonblack min/max: `97.34` / `97.34`
- Unique sampled colors min/max: `166` / `166`
- Heartbeats: `6`

## Host process metrics (required)

- Process samples: `9`
- Working set growth bytes: `-8192`
- Private memory growth bytes: `-102400`
- Handle growth: `-11`
- Process exited unexpectedly: `False`
- Clean stop: `True` (`verified_game_and_cdb_termination`)
- Artifact bytes: `3864072` (limit `262144000`)

## Edge frames

- frame-0001: nonblack=97.34 colors=166 hash=9858014a78b7ce3412b15b9719ae5385891a04a4abaaa32dc368a0fcda16ddb3
  ![frame-0001](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-092939-516-map-idle\frames\frame-0001.png)
- frame-0002: nonblack=97.34 colors=166 hash=81aaa1592b8ba18ceb30686de974f2f628a42065f00e06f2c4df9f6038dd8ce9
  ![frame-0002](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-092939-516-map-idle\frames\frame-0002.png)
- frame-0003: nonblack=97.34 colors=166 hash=a7991d39514f22f5b1b7d1fc063b10bf50f3e8bf1f9c7a5e5cb64d24adb73e18
  ![frame-0003](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-092939-516-map-idle\frames\frame-0003.png)
- frame-0007: nonblack=97.34 colors=166 hash=5e4ad18dd7f257a74831434eac9566578c846c430f8e416ebe6143e7ef19cfdf
  ![frame-0007](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-092939-516-map-idle\frames\frame-0007.png)
- frame-0008: nonblack=97.34 colors=166 hash=668b9881f5067873e0080314b33301871f496063cf08acddf3dfb146de9f2388
  ![frame-0008](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-092939-516-map-idle\frames\frame-0008.png)
- frame-0009: nonblack=97.34 colors=166 hash=ec601f676930e898f2082a8474f4547dac2e6132fbaa5a2467874683f26c3e3e
  ![frame-0009](C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-092939-516-map-idle\frames\frame-0009.png)

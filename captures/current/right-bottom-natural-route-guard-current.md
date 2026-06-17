# Right-Bottom Natural Route Guard

- Status: PASS
- Generated: `2026-06-17T09:47:21+02:00`
- Runtime policy: repo-only; reads existing hidden-desktop CDB artifacts and does not launch Clash95, CDB, wrappers, or visible windows
- Guard policy: natural right-bottom action routing must be classified as save-state gated only when command 99 reaches the owner loop, the exact 00433C20 owner-loop descriptor model is present, the 004338E0 action descriptor is parked at (1000,426), owner flag bits are zero, no owner/action renderer rows fire, and the run has no AV rows
- Run: `captures\archive\cdb-surface-dump-20260518-213418`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter`
- Candidate SHA-256: `D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C`
- State gated by owner flag: `True`
- Expected owner-loop descriptors: `{'d0': {'x': 39, 'y': 426, 'callback': '004338c0'}, 'd1': {'x': 1000, 'y': 426, 'callback': '004338e0'}, 'd2': {'x': 1000, 'y': 426, 'callback': '00433a40'}}`
- Owner entry flag: `0x00`
- Owner flag test: `{'owner_flag': '0x00', 'bit2': 0, 'bit1': 0, 'bit8': 0}`
- Action descriptor: slot `d1`, x/y `(1000,426)`, callback `004338e0`
- Descriptor result: `{'result': 0, 'owner': '041bc71a', 'owner_flag': '0x00', 'surface': [800, 600]}`
- Owner/action renderer rows: `0`
- AV rows: `0`

![surface dump](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260518-213418\surface.png)

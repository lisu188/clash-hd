# Castle Overview Hitmap Summary Tests

- Status: PASS
- Generated: `2026-07-18T10:18:01+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the castle overview hitmap parser recognizes raw command IDs, counts, bounding boxes, centered displayed coordinates, required present/absent flags, and wrong raw dimensions

## Tests

- `castle_overview_hitmap_summary maps raw IDs to commands, presence, counts, bounding boxes, and centered displayed coordinates`
- `castle_overview_hitmap_summary CLI writes JSON/Markdown and passes required present/absent flags on a good raw hitmap`
- `castle_overview_hitmap_summary rejects missing required raw IDs, present IDs required absent, and wrong raw dimensions`

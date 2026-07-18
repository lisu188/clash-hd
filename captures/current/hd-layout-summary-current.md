# HD Layout CDB Summary

- Generated: `2026-07-18T21:35:22+02:00`
- Log: `captures\archive\cdb-surface-dump-20260713-072428\cdb-surface-dump.log`
- Target: `800x600`
- Result: `PASS`
- Tooltip draw required: `false` (the init marker is the anchor proof)

## Checks

| Check | Result | Evidence |
| --- | --- | --- |
| `no_access_violation` | `PASS` | markers=0 |
| `tooltip_init_anchor` | `PASS` | matching=1/1 |
| `panel_setup` | `PASS` | matching=1/1 |
| `panel_draws` | `PASS` | descriptors=6/6, invalid_rows=0 |
| `panel_hitscan_anchor` | `PASS` | matching=19/19 |
| `panel_redraw_clip` | `PASS` | required=true, invoke=1, redraw=0, allowed=1 |

## Marker Counts

| Marker | Count |
| --- | ---: |
| `tooltip_init` | 1 |
| `tooltip_draw` | 0 |
| `panel_setup` | 1 |
| `panel_redraw_invoke` | 1 |
| `panel_draw` | 6 |
| `panel_redraw` | 0 |
| `panel_redraw_allowed` | 1 |
| `panel_hitscan` | 19 |
| `access_violation` | 0 |

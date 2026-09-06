# HD Layout CDB Summary

- Generated: `2026-09-05T12:27:30+02:00`
- Log: `C:\ClashCaptures\hd-completion\layout-hidden-combined\cdb-surface-dump-20260905-122508\cdb-surface-dump.log`
- Target: `800x600`
- Result: `FAIL`
- Tooltip draw required: `false` (the init marker is the anchor proof)

## Checks

| Check | Result | Evidence |
| --- | --- | --- |
| `no_access_violation` | `PASS` | markers=0 |
| `tooltip_init_anchor` | `PASS` | matching=1/1 |
| `panel_setup` | `PASS` | matching=1/1 |
| `panel_draws` | `PASS` | descriptors=6/6, invalid_rows=0 |
| `panel_hitscan_anchor` | `FAIL` | matching=0/0 |
| `panel_redraw_clip` | `PASS` | required=false, invoke=0, redraw=0, allowed=0 |

## Marker Counts

| Marker | Count |
| --- | ---: |
| `tooltip_init` | 1 |
| `tooltip_draw` | 0 |
| `panel_setup` | 1 |
| `panel_redraw_invoke` | 0 |
| `panel_draw` | 6 |
| `panel_redraw` | 0 |
| `panel_redraw_allowed` | 0 |
| `panel_hitscan` | 0 |
| `access_violation` | 0 |

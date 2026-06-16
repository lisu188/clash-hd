# First Mission Minimap Surface Summary

- Overall: PASS
- Log: `captures\archive\cdb-surface-dump-20260616-153751\cdb-surface-dump.log`
- Ready seen: `True`
- AV free: `True`
- Unit selected: `True`
- Minimap anchor OK: `True`
- Backing size OK: `True`
- Map surface OK: `True`
- Minimap bounds: `[[586, 16, 799, 229]]`
- Backing black-like samples: `83.333`%
- Final minimap black-like samples: `100.0`%
- Right-panel black-like samples: `100.0`%
- Bottom black-like samples: `66.667`%
- Coverage JSON: `captures\archive\cdb-surface-dump-20260616-153751\map-tile-coverage-full.json`
- Visibility JSON: `captures\archive\cdb-surface-dump-20260616-153751\visibility-coverage-full.json`
- Blank active cells: `['r3c10', 'r3c11', 'r4c10', 'r4c11', 'r5c10', 'r5c11', 'r6c10', 'r6c11', 'r7c10', 'r7c11', 'r8c0', 'r8c10', 'r8c11']`
- Visibility unexplained blank cells: `[]`
- All blank cells visibility-explained: `True`
- Interpretation: minimap backing is already mostly black-like before final HD surface sampling
- Blocker: right/bottom map blanks are visibility-zero explained; remaining UI work is tooltip/status owner-state and natural panel composition

## Coverage

- Gameplay frame likely: `True`
- Flagged active cells: `13`
- Measurable active cells: `99`
- Visibility status counts: `{'visibility_zero': 13}`

## Counts

- `av`: `0`
- `dirty`: `192`
- `dirty_unavailable`: `0`
- `done`: `1`
- `full`: `5`
- `init`: `1`
- `ready`: `1`
- `select`: `1`

## Sample Values

- `backing_sample_counts`: 0x01=960, 0x21=192
- `dirty_map_sample_counts`: 0x01=749, 0x00=305, 0xc1=98
- `full_minimap_sample_counts`: 0x01=20
- `full_right_panel_sample_counts`: 0x01=15
- `full_bottom_sample_counts`: 0x01=10, 0xc1=5

# Border Frame-Restore Evidence Check

- Overall: PASS
- Generated: `2026-07-17T15:36:29+02:00`
- Runtime policy: repo-only committed-evidence validation; does not launch Clash95, CDB, wrappers, or visible windows
- Guard policy: committed frame-restore band evidence must keep every border band region, filled HD extension bands with passing histogram authenticity gates at or above the frozen thresholds, and a real-runtime frame reference that still resolves inside the repository
- Patch group: `frame-restore-bands`
- Validation stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-framerestore`
- Real-runtime frames: `['captures/archive/visual-smoke-20260713-150843/after-map-path.png']`

## Checks

### proxy_surface_evidence

- Status: PASS
- Evidence: `captures\current\border-frame-restore-current.json`
- Required run token: `cdb-surface-dump-`
- Analyzed images: `1`
- Frame `captures/archive/cdb-surface-dump-20260713-151040/surface.png` (exists=`True` gate=`True`): extension nonblack `{'left_frame_hd_extension': 100.0, 'top_right_extension': 100.0}`, similarity `{'left_frame_hd_extension': 0.6841, 'top_right_extension': 0.7867}`

### real_runtime_evidence

- Status: PASS
- Evidence: `captures\current\border-frame-restore-realruntime-current.json`
- Required run token: `visual-smoke-`
- Analyzed images: `1`
- Frame `captures/archive/visual-smoke-20260713-150843/after-map-path.png` (exists=`True` gate=`True`): extension nonblack `{'left_frame_hd_extension': 100.0, 'top_right_extension': 100.0}`, similarity `{'left_frame_hd_extension': 0.6759, 'top_right_extension': 0.7993}`

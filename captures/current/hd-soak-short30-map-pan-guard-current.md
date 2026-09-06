# HD Hidden-CDB Host Soak Report Guard

- Overall: PASS
- Generated: `2026-09-06T03:57:57.710641+00:00`
- Runtime policy: `repo-only hidden-cdb soak report inspection; grades hidden-desktop CDB host soak frames read via host ReadProcessMemory surface reads plus full host process telemetry; input responsiveness is not measurable on a hidden desktop and is recorded not_applicable_hidden, never faked; forced-entry mechanics are disclosed, never hidden; does not launch anything`
- Environment: `hidden_cdb_host` (expected `hidden_cdb_host`)
- Evidence class: `approved_hidden_cdb_host_soak` (expected `approved_hidden_cdb_host_soak`)

> **ENVIRONMENT: hidden_cdb_host** -- this is a hidden-desktop CDB host soak,
> NOT a visible-runtime soak and NOT a guest soak. Input responsiveness is
> `not_applicable_hidden` (never measured, never faked on a hidden desktop).
> Forced-entry mechanics are disclosed below, not hidden.

- Entry mechanism (disclosed forcing): `cdb_breakpoint_forced_loader_entry`
- Pan mechanism (disclosed forcing): `cdb_forced_scroll_write`
- Input responsiveness: `not_applicable_hidden`
- Source report: `captures\current\hd-soak-short30-map-pan-current.json`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Tier / route: `short30` / `map-pan`
- Duration seconds: `1800`
- Sample interval seconds: `15`

## Checks

- `executed`: `PASS`
- `source_status`: `PASS`
- `schema`: `PASS`
- `environment`: `PASS`
- `protected_stage`: `PASS`
- `tier_route`: `PASS`
- `patch_evidence`: `PASS`
- `promotion_boundary`: `PASS`
- `artifact_locations`: `PASS`
- `capture_integrity`: `PASS`
- `wrapper_provenance`: `PASS`
- `marker_provenance`: `PASS`
- `cleanup_provenance`: `PASS`
- `frame_inventory`: `PASS`
- `render_metrics`: `PASS`
- `frame_progression`: `PASS`
- `forced_entry_disclosure`: `PASS`
- `input_responsiveness`: `PASS`
- `process_liveness`: `PASS`
- `process_growth`: `PASS`
- `elapsed_coverage`: `PASS`
- `summary_consistency`: `PASS`
- `artifact_budget`: `PASS`

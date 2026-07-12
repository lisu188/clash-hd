# HD Soak Report Guard Tests

- Status: PASS
- Generated: `2026-07-12T19:23:38+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves executed soak reports must carry protected-stage patch evidence, base/candidate SHA-256s, a passing source status, external artifact locations, stable/progressing frame metrics, clean process stop, elapsed frame/process sample coverage, valid route/input probe rows, and non-promoting input status with bounded working-set, private-memory, handle growth, artifact budget, valid capture/frame inventories, and consistent raw/sample summary metrics

## Tests

- `hd_soak_report accepts only executed protected-stage reports with passing patch evidence`
- `hd_soak_report rejects executed reports whose source status is failed or carries failures`
- `hd_soak_report rejects unexpected process exits`
- `hd_soak_report rejects raw process samples that already exited`
- `hd_soak_report rejects missing sample intervals or insufficient elapsed sample coverage`
- `hd_soak_report rejects repository-local candidates and raw artifacts`
- `hd_soak_report rejects noncanonical input, workdir, candidate, and output roots`
- `hd_soak_report rejects capture errors, invalid frame hashes, and bad probe exit codes`
- `hd_soak_report rejects invalid tier, route, or duration combinations`
- `hd_soak_report rejects weak render/palette metrics`
- `hd_soak_report allows stable idle frames but requires progression for map-pan`
- `hd_soak_report rejects missing or excessive process growth metrics`
- `hd_soak_report rejects missing, mismatched, or excessive artifact budget metrics`
- `hd_soak_report rejects missing or excessive route input drift metrics`
- `hd_soak_report rejects final route markers that do not match the last route/input row`
- `hd_soak_report rejects empty route evidence and summary/detail metric mismatches`
- `hd_soak_report rejects patch-stage manifests with original/unexpected bytes or failed HD gate`
- `hd_soak_report rejects missing patch-stage manifests`
- `hd_soak_report classifies pending approval without runtime metric noise`

# HD Soak Report Guard Tests

- Status: PASS
- Generated: `2026-06-15T22:14:55+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves executed soak reports must carry protected-stage patch evidence, base/candidate SHA-256s, external artifact locations, stable frame metrics, clean process stop, and non-promoting input status

## Tests

- `hd_soak_report accepts only executed protected-stage reports with passing patch evidence`
- `hd_soak_report rejects unexpected process exits`
- `hd_soak_report rejects repository-local candidates and raw artifacts`
- `hd_soak_report rejects weak render/palette metrics`
- `hd_soak_report rejects patch-stage manifests with original/unexpected bytes or failed HD gate`
- `hd_soak_report rejects missing patch-stage manifests`

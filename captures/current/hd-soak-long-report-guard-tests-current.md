# HD Soak Long Report Guard Tests

- Status: PASS
- Generated: `2026-07-18T10:42:42+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves 2h+ representative-route soak evidence remains locked until the short ladder passes and approved long map-idle/map-pan soak report guards pass for the same candidate SHA-256

## Tests

- `hd_soak_long_report_guard fails closed while the short ladder and long proof are missing`
- `hd_soak_long_report_guard accepts a valid future two-route 2h+ proof fixture`
- `hd_soak_long_report_guard accepts candidate SHA-256 from nested patch-evidence summaries`
- `hd_soak_long_report_guard rejects mixed candidate SHA-256s across representative routes`
- `hd_soak_long_report_guard rejects missing representative long routes`
- `hd_soak_long_report_guard rejects short duration and failed required checks`
- `hd_soak_long_report_guard rejects unprotected stages`
- `hd_soak_long_report_guard CLI writes JSON/Markdown and respects --require-pass`

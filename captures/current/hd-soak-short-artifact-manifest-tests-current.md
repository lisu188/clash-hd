# HD Soak Short Artifact Manifest Tests

- Status: PASS
- Generated: `2026-07-12T19:23:38+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves each short soak ladder step has durable current report, guard, and triage paths, with execution commands gated by -Execute -AllowVisibleRuntime

## Tests

- `hd_soak_short_artifact_manifest emits unique canonical report paths for every short ladder step`
- `hd_soak_short_artifact_manifest pins report outputs, input-drift limits, and keeps execution approval-gated`
- `hd_soak_short_artifact_manifest fails closed on duplicate canonical paths`
- `hd_soak_short_artifact_manifest fails closed when outputs leave captures/current`
- `hd_soak_short_artifact_manifest CLI writes JSON/Markdown and respects --require-pass`

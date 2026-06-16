# HD Soak Intro-Skip Rerun Readiness Tests

- Status: PASS
- Generated: `2026-06-16T18:05:30+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves a classified intro-skip input-drift failure can become a rerun approval packet only after repo-only harness, dry-run, visible-runtime, process, and exe-artifact guards pass

## Tests

- `hd_soak_intro_skip_rerun_readiness passes only when the classified failure and guards support an explicit visible rerun`
- `hd_soak_intro_skip_rerun_readiness rejects wrong failure classifications`
- `hd_soak_intro_skip_rerun_readiness rejects approval-command intro-skip drift`
- `hd_soak_intro_skip_rerun_readiness CLI writes JSON/Markdown and respects --require-pass`

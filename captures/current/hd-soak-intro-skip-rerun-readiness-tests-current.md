# HD Soak Intro-Skip Rerun Readiness Tests

- Status: PASS
- Generated: `2026-09-06T05:58:05+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves a classified intro-skip input-drift failure can become a rerun approval packet only after repo-only harness, dry-run, visible-runtime, process, and exe-artifact guards pass

## Tests

- `hd_soak_intro_skip_rerun_readiness: ready packet passes`
- `hd_soak_intro_skip_rerun_readiness: input environment denied map attempt preserves readiness`
- `hd_soak_intro_skip_rerun_readiness: intro transition failure preserves readiness after harness fix`
- `hd_soak_intro_skip_rerun_readiness: unexpected process exit is not applicable not rerun ready`
- `hd_soak_intro_skip_rerun_readiness: rejects wrong triage classification`
- `hd_soak_intro_skip_rerun_readiness: rejects intro skip command drift`
- `hd_soak_intro_skip_rerun_readiness: rejects visible runtime token drift`
- `hd_soak_intro_skip_rerun_readiness: rejects visible runtime expiry drift`
- `hd_soak_intro_skip_rerun_readiness: completed ladder requires real bound reports but no current approval packet`
- `hd_soak_intro_skip_rerun_readiness: completed ladder rejects forged stale or mismatched evidence`
- `hd_soak_intro_skip_rerun_readiness: real predecessor reports make intro readiness historical`
- `hd_soak_intro_skip_rerun_readiness: later step label cannot replace canonical predecessor proof`
- `hd_soak_intro_skip_rerun_readiness: cli writes outputs`

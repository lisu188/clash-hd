# Launcher Core Tests

- Status: PASS
- Generated: `2026-07-18T21:30:38+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the launcher patch/deploy/launch core enforces its safety refusals

## Tests

- `launcher core refuses repo/game-dir candidate roots and unknown stages`
- `launcher core builds, byte-gates, reuses, and rebuilds candidates`
- `launcher core refuses base executables with unexpected SHA-256`
- `launcher core launch gate requires confirmed=True and a deployed wrapper`
- `launcher core reports missing wrapper DLLs without failing deploy`
- `launcher environment report classifies base/wrapper/process state`
- `launcher settings round-trip and recover from corrupt files`
- `launcher single-instance lock handles live and stale owners`
- `launcher dxcfg rendering rejects unverified scaling modes`
- `launcher candidate cleanup stays inside the candidates root`

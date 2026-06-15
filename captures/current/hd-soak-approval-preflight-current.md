# HD Soak Approval Preflight

- Overall: PASS
- Generated: `2026-06-15T20:14:56.369072+00:00`
- Runtime policy: repo-only visible-runtime approval preflight; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `ready_for_explicit_approval`
- Current step: `short2_menu_idle`
- Current step status: `pending_approval_legacy_compat`
- Stable stage should change: `False`
- Right-bottom promotion blocked: `True`

## Approval Prompt

Approve the first short2 menu-idle visible-runtime soak using the exact approval-gated command in this report. It will generate a patched candidate under C:\ClashTests\hd-soak and raw frame artifacts under C:\ClashCaptures\hd-soak; it must not modify C:\Clash\clash95.exe.

## Safe Dry Run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -Json
```

## Approval-Gated Runtime Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -Execute -AllowVisibleRuntime -RequirePass -Json
```

## Post-Run Validation

- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_report.py captures\current\hd-soak-short2-menu-idle-current.json --write-json captures\current\hd-soak-short2-menu-idle-guard-current.json --write-markdown captures\current\hd-soak-short2-menu-idle-guard-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_failure_triage.py captures\current\hd-soak-short2-menu-idle-current.json --write-json captures\current\hd-soak-short2-menu-idle-triage-current.json --write-markdown captures\current\hd-soak-short2-menu-idle-triage-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\current_evidence_refresh.py --write-json captures\current\current-evidence-refresh-current.json --write-markdown captures\current\current-evidence-refresh-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\evidence_index_check.py captures\current\hd-map-evidence-current.md --require-pass`
- `git diff --check`

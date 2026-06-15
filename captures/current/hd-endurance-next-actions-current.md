# HD Endurance Next Actions

- Overall: PASS
- Generated: `2026-06-15T20:36:18.607483+00:00`
- Runtime policy: repo-only endurance next-action triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `waiting_for_explicit_visible_runtime_approval`
- Full game complete: `False`
- Open requirements: `10`

## Next Action

- `run_short2_menu_idle_soak`: `approval_required`
- Requires visible runtime: `True`
- Requires explicit user approval: `True`
- Why: The release checklist cannot progress until one protected-stage short2 menu-idle soak produces frame/process evidence.

Safe dry-run command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -Json
```

Approval-gated runtime command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -Execute -AllowVisibleRuntime -RequirePass -Json
```

Post-run validation:

- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_report.py captures\current\hd-soak-short2-menu-idle-current.json --write-json captures\current\hd-soak-short2-menu-idle-guard-current.json --write-markdown captures\current\hd-soak-short2-menu-idle-guard-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_failure_triage.py captures\current\hd-soak-short2-menu-idle-current.json --write-json captures\current\hd-soak-short2-menu-idle-triage-current.json --write-markdown captures\current\hd-soak-short2-menu-idle-triage-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\current_evidence_refresh.py --write-json captures\current\current-evidence-refresh-current.json --write-markdown captures\current\current-evidence-refresh-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\evidence_index_check.py captures\current\hd-map-evidence-current.md --require-pass`
- `git diff --check`

## Open Requirement Groups

- `endurance`: `short2_menu_idle_soak, long_soak_representative_routes`
- `manual input`: `stable_menu_real_input, stable_hd_map_real_input`
- `screen route`: `right_bottom_action_menu, castle_and_barracks_centered_input, tactical_battle_entry_return`
- `state continuity`: `save_load_roundtrip, turn_advancement, campaign_routes`

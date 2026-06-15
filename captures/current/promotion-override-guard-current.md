# Promotion Override Guard

- Overall: PASS
- Generated: `2026-06-15T22:36:16+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: current evidence must keep CDB-only promotion overrides inactive until manual proof or an explicit override decision is intentionally supplied

## Checks

- `right_bottom_compose_promotion_decision`: `PASS` override=`False` stable_change=`False` proof_valid=`False`
- `castle_overview_promotion_decision`: `PASS` override=`False` stable_change=`False` proof_valid=`False`
- `manual_directinput_checklist`: `PASS` override=`False` stable_change=`False` proof_valid=`False`

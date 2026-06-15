# HD Soak Short-Tier Report

- Overall: FAIL
- Generated: 2026-06-15T20:15:44+02:00
- Runtime policy: opt-in visible runtime soak; raw frames stay outside the repository by default
- Tier / route: short2 / menu-idle
- Duration seconds: 120
- Stage: gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch
- Candidate SHA-256: None
- Output directory: C:\ClashCaptures\hd-soak\pending-approval
- Frame samples: 0
- Unique frame hashes: 0
- Nonblack min/max: 0.0 / 0.0
- Unique sampled colors min/max: 0 / 0
- Working-set growth bytes: None
- Handle growth: None
- Artifact bytes: 0
- Unexpected exit: False
- Clean stop: False
- Route marker: pending_approval
- Input proof class: not_run_visible_runtime_approval_required_not_manual_directinput_release_proof
- Right-bottom promotion remains blocked: True

## Failures

- short2 menu-idle soak was not executed because visible-runtime escalation was not approved

## Ready Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 `
  -Tier short2 `
  -Route menu-idle `
  -Execute `
  -AllowVisibleRuntime `
  -RequirePass
```

## Frame Samples

No frame samples exist yet.

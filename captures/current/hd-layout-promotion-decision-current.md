# HD Layout Promotion Decision

- Decision record: `PASS`
- Decision: `defer_stable_promotion`
- Stable stage should change: `False`
- Current stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Validation stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-hdlayout`
- Candidate SHA-256: `911A4F1CFB3CFEE7974F50742CC98FDD16DCC82EAA95C88F748E0976140E6FBD`
- Manual DirectInput proof: `False`
- Manual checklist: `0/5`
- Command-click alignment: `False`
- Panel callback proof: `False`
- Promotion ready: `False`
- Override accepted: `False`

## Required Checks

- `patch_manifest`: `PASS`
- `candidate_identity`: `PASS`
- `hidden_geometry`: `PASS`
- `visible_composition`: `PASS`
- `failed_command_click`: `PASS`
- `automated_hover_scope`: `PASS`
- `manual_directinput_pending`: `PASS`
- `promotion_state`: `PASS`
- `process_hygiene`: `PASS`
- `stable_stage_protection`: `PASS`
- `no_override`: `PASS`

## Evidence Boundary

- Tooltip patch group: `{'patched': 12, 'total': 12}`
- Panel patch group: `{'patched': 8, 'total': 8}`
- Current HD map gate: `True`
- Hidden redraw clip proved: `True`
- Visible composition passed: `True`
- Failed click requested / actual / error: `[760, 560]` / `[716, 493]` / `[-44, -67]`
- Failed click alignment: `False`
- Visible composition PASS is not command-input, callback, manual DirectInput, or promotion proof.

## Reasons

- the exact HD-layout patch and current HD map gate are passing
- hidden CDB geometry proves the tooltip anchor, all six panel coordinates, and the redraw clip
- authentic visible frames prove the relocated tooltip and active lower-right panel composition
- the descriptor-5 click attempt was clamped from [760, 560] to [716, 493] and failed alignment
- no relocated command callback or manual DirectInput proof exists
- the manual DirectInput checklist remains 0/5 and promotion readiness remains false
- the protected stable stage remains unchanged and no override is accepted

## Next Actions

- keep the protected stable stage unchanged
- obtain a correctly aligned real command click and observed callback before reconsidering promotion
- complete the five-item manual DirectInput checklist with separately approved visible validation

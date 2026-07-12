# Castle Overview Promotion Decision

- Decision record: PASS
- Decision: `defer_stable_promotion`
- Stable stage should change: `False`
- Generated: `2026-07-12T20:47:37+02:00`
- Current stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Validation stage: `castlecenter-all`
- Resolved validation stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Candidate SHA-256: `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`
- Evidence matrix: `captures\current\castle-overview-evidence-current.json`
- Matrix status: `True`
- Matrix promotion status: `validation_stage_only`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, or visible windows
- Focused displayed-wrapper proof: `True`
- Visible target completion proof: `True`
- Visible target count: `3`
- Dormant target completion proof: `True`
- Dormant target count: `4`
- Manual input proof: `None`
- Manual input proof supplied: `False`
- Manual input proof valid: `False`
- Manual input proof SHA-256: `None`
- Manual input proof checked items: `0`
- CDB-only promotion override: `False`
- Bare CDB-only promotion blocked: `False`
- Promotion override manifest: `None`
- Promotion override manifest supplied: `False`
- Promotion override manifest valid: `False`
- Promotion override scope: `None`
- Promotion override SHA-256: `None`

## Reasons

- castle overview evidence matrix is passing
- focused displayed-wrapper and multi-hit completion proof is present
- current proof is repo-only CDB/proxy evidence
- manual/visible DirectInput validation has not been supplied
- promotion override manifest has not been supplied
- visible/manual runs require explicit user approval

## Next Actions

- keep the patcher default stable HD map stage unchanged
- keep castle overview wrappers scoped to castlecenter-all
- continue with repo-only or hidden-desktop/CDB evidence only
- request explicit approval before any visible/manual input validation

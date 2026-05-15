# Battle UI Patch Manifest

Generated: 2026-05-15

No battle-specific binary patches have been added.

The validation stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
currently selects the same patch groups as `castlecenter-all` so hidden CDB
probes can target a stable map+castle candidate without changing battle bytes.

## Deferred Patch Groups

- `battle-ui-center-present`: blocked until a battle-only draw/present callsite is proven.
- `battle-ui-ensure-800-surface`: blocked until battle surface ownership/size is proven.
- `battle-ui-centered-input`: blocked until battle descriptor hit-test callsite is proven.
- `battle-grid-centered-input`: blocked until tactical-grid hit/conversion route is proven.
- `battle-modal-centered-input`: blocked until a separate battle modal hit-test path is proven.
- `battle-present-bounds`: blocked until stale right/bottom battle present/copy bounds are proven.

Every future battle patch must document file offset, VA/RVA, old bytes, new
bytes, stage, rationale, observed effect, and must pass old-byte verification.

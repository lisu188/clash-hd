# Battle UI Probe Lane

Generated: 2026-05-15

Battle UI support remains probe-first. The current validation target is safe
complete mode: keep the native 640x480 battle UI intact, center it inside the
800x600 HD surface at `(80,60)`, and prove command, tactical-grid, and modal
input routes before adding any battle-specific patch group.

## Stage

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`

This stage intentionally selects the same patch groups as `castlecenter-all`.
It adds no battle-specific bytes and exists so hidden CDB probes can target a
stable map+castle candidate while collecting battle rows.

## Artifacts

- `probes/cdb/battle/clash95_battle_ui_catalog_extra.cdb`
- `probes/cdb/battle/clash95_battle_ui_present_extra.cdb`
- `probes/cdb/battle/clash95_battle_ui_input_extra.cdb`
- `tools/battle_ui_summary.py`
- `tools/battle_ui_gate.py`
- `tools/test_battle_ui_summary.py`
- `tools/test_battle_ui_gate.py`

## Required Evidence Before Patching

- Deterministic hidden/no-popup route into a battle screen.
- `BATTLE_READY` plus battle surface pointer and size.
- Centered-native visual proof or an explicit unclassified/native result.
- Battle draw/present/copyback rows with battle-scoped callsites.
- Command descriptor and command-hit rows.
- Tactical-grid hit or coordinate-conversion rows.
- Modal hit or explicit modal-path classification.
- Zero AV rows.
- Patch-stage report for the battle stage with `original=0` and `unexpected=0`.
- Existing HD map smoke evidence still passing.

No `battle-ui-*` patch group should be added until these rows identify exact
addresses and old bytes.

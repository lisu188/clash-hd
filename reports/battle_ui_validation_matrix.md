# Battle UI Validation Matrix

Generated: 2026-05-15

Status: probe-first scaffold created, battle runtime proof pending.

| Gate | Status | Evidence |
| --- | --- | --- |
| Branch safety | PASS | branch `complete-hd-battle-ui-20260515`; dirty worktree preserved |
| Base executable SHA | PASS | `C:\Clash\clash95.exe` SHA-256 `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE` |
| Battle stage defined | PASS | `battlecenter` stage exists and has no battle-specific patch groups |
| Battle route inventory | PASS | `reports\battle_ui_route_inventory.md` |
| Battle CDB templates | PASS | `clash95_battle_ui_catalog_extra.cdb`, `clash95_battle_ui_present_extra.cdb`, `clash95_battle_ui_input_extra.cdb` |
| Battle summary parser | PASS | `tools\battle_ui_summary.py` compiles and parses fixture-style rows |
| Battle gate | PASS scaffold | `tools\battle_ui_gate.py` fails closed until battle evidence exists |
| Battle mode reached | PENDING | requires hidden/no-popup CDB capture |
| Battle visual mode | PENDING | requires `BATTLE_SURFACE` and centered/expanded classification |
| Battle command input | PENDING | requires `BATTLE_COMMAND_HIT` |
| Battle tactical-grid input | PENDING | requires `BATTLE_GRID_HIT` |
| Battle modal/dialog | PENDING | requires `BATTLE_MODAL_HIT` or `BATTLE_MODAL_CLASSIFIED` |
| Stable HD-map regression | PASS current | existing current evidence refresh remains the regression anchor |
| Castle/interior regression | PASS current | fixed May 15 castlecenter-all evidence remains current |

Do not claim battle UI release completion until the pending rows pass.

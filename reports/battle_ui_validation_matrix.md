# Battle UI Validation Matrix

Generated: 2026-05-15
Updated: 2026-05-20

Status: deterministic battle force-entry and the initial native-center battle
present now pass. Command-button descriptor hits, descriptor-to-callback
activation, and a harness-forced enabled-command callback result are proven on
the centered frame. Tactical-grid hit-test entry is now classified under the
centered frame: displayed `(144,108)` reaches cell `(1,1)`, while native
`(64,48)` reaches cell `(0,0)`. The same forced route now classifies the
modal/input path as `input_update_seen_no_modal` at `004605D0`. The natural
save-state callback still records `precondition-disabled` for unit type `5`
(`avail=8`, `enabled=0`), so natural/manual enabled-command cadence, actual
centered input transforms, and later battle-loop redraw centering remain
pending.

| Gate | Status | Evidence |
| --- | --- | --- |
| Branch safety | PASS | branch `codex/battle-ui-evidence-next-20260515`; dirty worktree preserved |
| Base executable SHA | PASS | `C:\Clash\clash95.exe` SHA-256 `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE` |
| Battle stage defined | PASS | `battlecenter` stage includes narrow `battle-ui-center-present-wrapper` only |
| Battle patch-stage bytes | PASS | `captures\patch-stage-battlecenter-current.json`; `136` patched, `0` original, `0` unexpected; battle group `2/2` patched |
| Battle route inventory | PASS | `reports\battle_ui_route_inventory.md` |
| Battle CDB templates | PASS | `probes\cdb\battle\clash95_battle_force_attack_entry_extra.cdb` plus catalog/present/input templates; static probe register guard passes |
| Battle summary parser | PASS | `tools\battle_ui_summary.py` compiles and parses fixture-style rows |
| Battle gate | PASS scaffold | `tools\battle_ui_gate.py` fails closed until battle evidence exists |
| Battle catalog smoke | PASS | `captures\cdb-surface-dump-20260515-114101`; hidden/no-popup run passed with 800x600 surface and no AV |
| Battle mode reached | PASS | `captures\cdb-surface-dump-20260518-214535` and `captures\cdb-surface-dump-20260518-221018` log forced `Unit_Attack`, `BATTLE_OWNER_ENTRY`, and `BATTLE_READY` |
| Battle visual mode | PASS initial | `captures\battle-ui-force-entry-current.md` classifies `centered-native-640x480`, offset `[80, 60]`, with wrapper return `0051ba63` |
| Battle command input | PASS harnessed | `captures\battle-ui-command-hit-current.md`; visual command hit and native-coordinate command hit both return `2` after controlled turn-banner/frame skips |
| Battle command callback | PASS harnessed/disabled | `captures\battle-ui-command-callback-current.md`; descriptor `00514b78` reaches callback `0042d4e0`, then records `branch=precondition-disabled`, `unit_type=5`, `avail=8`, `enabled=0` |
| Battle enabled-command callback | PASS harnessed/forced | `captures\battle-ui-command-enabled-callback-current.md`; temporary unit type `8` records `avail=10`, `enabled=3`, skips the render-begin lock under CDB, then reaches `branch=state2` with `state=0x02` and no AV |
| Battle tactical-grid input | PASS harnessed/classified | `captures\battle-ui-grid-hit-current.md`; `captures\cdb-surface-dump-20260520-103155` logs visual `(144,108)` to cell `(1,1)` and native `(64,48)` to cell `(0,0)` through `0042CB50`, with no AV |
| Battle modal/dialog | PASS classified/no-hit | `captures\battle-ui-modal-classified-current.md`; `captures\cdb-surface-dump-20260520-103714` logs `BATTLE_MODAL_CLASSIFIED status=input_update_seen_no_modal` at `004605D0`, with no AV |
| Battle combined evidence matrix | PASS current | `captures\battle-ui-evidence-current.md`; repo-only matrix combines force-entry, command hit/callback, enabled callback, grid classification, modal classification, patch-stage bytes, and stable HD-map smoke |
| Battle redraw loop | PENDING | initial present is centered; later redraw/copyback callsites remain probe-only |
| Stable HD-map regression | PASS current | existing current evidence refresh remains the regression anchor |
| Castle/interior regression | PASS current | fixed May 15 castlecenter-all evidence remains current |

Do not claim battle UI release completion until the pending rows pass and a
natural/manual input route replaces the current harnessed command-hit and
callback-gate proof.

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
(`avail=8`, `enabled=0`). The actual centered input wrappers are now
validation-proven under CDB, but helper bodies are skipped after entry, so
natural/manual enabled-command cadence remains pending. A post-ready
redraw/copyback sample now passes after `BATTLE_READY`, and command
availability plus save-slot scans show the currently routed local battle states
have zero naturally enabled command units. A direct read-only save-file
inventory also finds zero naturally enabled command units across all six local
save files.

| Gate | Status | Evidence |
| --- | --- | --- |
| Branch safety | PASS | branch `codex/battle-ui-evidence-next-20260515`; dirty worktree preserved |
| Base executable SHA | PASS | `C:\Clash\clash95.exe` SHA-256 `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE` |
| Battle stage defined | PASS | `battlecenter` stage includes narrow `battle-ui-center-present-wrapper` only |
| Battle patch-stage bytes | PASS | `captures\current\patch-stage-battlecenter-current.json`; `136` patched, `0` original, `0` unexpected; battle group `2/2` patched |
| Battle inputprobe stage bytes | PASS | `captures\current\patch-stage-battlecenter-inputprobe-patched-current.json`; `140` patched, `0` original, `0` unexpected; input wrapper groups `2/2` patched |
| Battle route inventory | PASS | `reports\battle_ui_route_inventory.md` |
| Battle CDB templates | PASS | `probes\cdb\battle\clash95_battle_force_attack_entry_extra.cdb` plus catalog/present/input templates; static probe register guard passes |
| Battle summary parser | PASS | `tools\battle_ui_summary.py` compiles and parses fixture-style rows |
| Battle gate | PASS scaffold | `tools\battle_ui_gate.py` fails closed until battle evidence exists |
| Battle catalog smoke | PASS | `captures\archive\cdb-surface-dump-20260515-114101`; hidden/no-popup run passed with 800x600 surface and no AV |
| Battle mode reached | PASS | `captures\archive\cdb-surface-dump-20260518-214535` and `captures\archive\cdb-surface-dump-20260518-221018` log forced `Unit_Attack`, `BATTLE_OWNER_ENTRY`, and `BATTLE_READY` |
| Battle visual mode | PASS initial | `captures\current\battle-ui-force-entry-current.md` classifies `centered-native-640x480`, offset `[80, 60]`, with wrapper return `0051ba63` |
| Battle command input | PASS harnessed | `captures\current\battle-ui-command-hit-current.md`; visual command hit and native-coordinate command hit both return `2` after controlled turn-banner/frame skips |
| Battle command callback | PASS harnessed/disabled | `captures\current\battle-ui-command-callback-current.md`; descriptor `00514b78` reaches callback `0042d4e0`, then records `branch=precondition-disabled`, `unit_type=5`, `avail=8`, `enabled=0` |
| Battle enabled-command callback | PASS harnessed/forced | `captures\current\battle-ui-command-enabled-callback-current.md`; temporary unit type `8` records `avail=10`, `enabled=3`, skips the render-begin lock under CDB, then reaches `branch=state2` with `state=0x02` and no AV |
| Battle tactical-grid input | PASS harnessed/classified | `captures\current\battle-ui-grid-hit-current.md`; `captures\archive\cdb-surface-dump-20260520-103155` logs visual `(144,108)` to cell `(1,1)` and native `(64,48)` to cell `(0,0)` through `0042CB50`, with no AV |
| Battle centered input wrappers | PASS validation-only | `captures\current\battle-ui-centered-input-current.md`; `captures\archive\cdb-surface-dump-20260520-111115` logs grid visual `(144,108)` to inner `(64,48)` and descriptor visual `(588,440)` to inner `(508,380)`, then restores both visual coordinates, with no AV |
| Battle post-ready redraw/copyback | PASS harnessed | `captures\current\battle-ui-post-ready-redraw-current.md`; `captures\archive\cdb-surface-dump-20260520-195244` logs `BATTLE_READY`, 9 post-ready presents, 6 post-ready copybacks, forced grid point `(144,108)->(64,48)`, final present return `0042CB46`, and no AV |
| Battle command availability scan | PASS explanatory | `captures\current\battle-command-availability-current.md`; 18 natural battle unit records parsed, selected unit type `5` has `availability=8`, `enabled=0`, naturally enabled unit count is `0`, and the executable table scan identifies 11 enabled unit types through type `31`: Dragon cavalry, Archer, Crossbower, Musketeer, Catapult, Cannon, Forester, Cyklop, Wizard, Winger, Dragon |
| Battle save-slot scan | PASS explanatory | `captures\current\battle-slot-scan-current.md`; 6 local save-slot attempts, 3 routed slots with unit rows, 3 timeouts before unit scan, and natural enabled command unit count `0` |
| Battle save-file inventory | PASS explanatory | `captures\current\battle-save-unit-inventory-current.md`; read-only parse of six `C:\Clash\save\*.dat` files, 63 unit records, save offset `0x00023EF6`, natural enabled command unit count `0`; local saves currently contain Peasant, Light infantry, Light cavalry, Highlander, Builder |
| Battle constructed save fixture | PASS isolated fixture | `captures\current\battle-constructed-save-fixture-current.md`; copied-save change at offset `0x00023EFC` changes unit index `0` from Light cavalry (`enabled=0`) to Dragon cavalry (`enabled=3`) under `C:\ClashTests\battle-enabled-fixture-20260520-210728`, leaving `C:\Clash\save` untouched |
| Battle constructed fixture unit scan | PASS isolated runtime | `captures\current\battle-constructed-fixture-unit-scan-current.md`; hidden CDB run `captures\archive\cdb-surface-dump-20260520-210816` loads slot `0` from the isolated work dir and parses one naturally enabled Dragon cavalry unit (`availability=10`, `enabled=3`) |
| Battle constructed fixture command callback | PASS harnessed/visual-click inputprobe/natural render-begin | `captures\current\battle-constructed-fixture-command-callback-current.md`; hidden CDB run `captures\archive\cdb-surface-dump-20260520-220459` starts from displayed `(588,440)`, reaches pre-gate native `(508,380)` through the inputprobe wrapper, reaches `0042D4E0` with unit type `8`, `avail=10`, `enabled=3`, observes click gate `eax=1`, records `branch=state1`, has zero unit-type or click-gate force rows, has no pre-gate rearm, releases the synthetic click state, and enters/exits `Render_Begin` naturally without the old skip or lost guard |
| Battle modal/dialog | PASS classified/no-hit | `captures\current\battle-ui-modal-classified-current.md`; `captures\archive\cdb-surface-dump-20260520-103714` logs `BATTLE_MODAL_CLASSIFIED status=input_update_seen_no_modal` at `004605D0`, with no AV |
| Battle combined evidence matrix | PASS current | `captures\current\battle-ui-evidence-current.md`; repo-only matrix combines force-entry, command hit/callback, enabled callback, grid classification, centered-input wrapper proof, post-ready redraw/copyback, availability scan, slot scan, save-file inventory, constructed-fixture planning/runtime unit scan/command callback, modal classification, battlecenter/inputprobe patch-stage bytes, and stable HD-map smoke |
| Manual battle command cadence | PENDING | isolated fixture now proves enabled command callback without the type-8 CDB override, forced click gate, pre-gate rearm, direct render-begin skip, or render-begin lost guard; the remaining gap is replacing the synthetic hidden-CDB click/release with natural/manual input cadence |
| Stable HD-map regression | PASS current | existing current evidence refresh remains the regression anchor |
| Castle/interior regression | PASS current | fixed May 15 castlecenter-all evidence remains current |

Do not claim battle UI release completion until the pending natural/manual row
passes and a natural input route replaces the current harnessed command-hit,
callback-gate, and helper-body-skip wrapper proof.

# Right-Bottom Slot Fixture Plan

- Status: PASS
- Generated: `2026-07-12T19:42:51+02:00`
- Runtime policy: repo-only fixture planner; reads generated evidence JSON and writes only JSON/Markdown reports; does not copy saves, launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only while the slot-5 route-compatible save remains blocked before LOADSAVE, the row-0 natural route remains proven, and the proposed copied save stays isolated and non-promoting
- Candidate matrix: `captures\current\right-bottom-natural-route-candidate-matrix-current.json`
- Load-slot route limit: `captures\current\load-slot-route-limit-current.json`

## Decision

- Preferred next step: `copy_slot5_save_as_isolated_slot0_then_run_row0_hidden_probe`
- Proof class: `non_natural_isolated_fixture`
- Promotion ready: `False`
- stable_stage_should_change: `False`
- Source save: `C:\Clash\save\5.dat`
- Fixture save: `C:\ClashTests\right-bottom-slot5-as-slot0-fixture\save\0.dat`
- Target load slot: `0`
- Target row already proven: `True`

## Evidence Inputs

- Baseline route index: `0`
- Route candidate: save slot `5`, record `0`, position `[14, 20]`, flags `0x0B`
- Slot 2 status: `loads_but_click_misses_castle`
- Slot 5 status: `timeout_before_loadsave`
- Recent slot-5 blocked: `True`

## Follow-Up Requirements

- create the isolated workdir outside the repository
- copy only the selected save as save\0.dat inside that workdir
- run the hidden-desktop row-0 right-bottom natural-route probe from the isolated workdir
- require LOADSAVE/PlayGame, nonzero owner-flag bit 0x02, owner/action draw rows, and no AV rows
- keep the result labeled non-natural fixture evidence until rows 3-5 naturally enter the load menu

## Promotion Blockers Preserved

- manual DirectInput proof is still absent
- natural slot-5 menu loading is still blocked before LOADSAVE
- fixture evidence must not change the stable stage by itself

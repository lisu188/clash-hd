# HD Endurance Next Actions

- Overall: PASS
- Generated: `2026-09-06T03:58:07.729431+00:00`
- Runtime policy: repo-only endurance next-action triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `repo_only_followup_available`
- Current short step: `None`
- Full game complete: `False`
- Open requirements: `6`

## Next Action

- `resolve_stable_menu_real_input`: `needs_planning`
- Requires visible runtime: `False`
- Requires explicit user approval: `False`
- Why: collect approved manual menu-load proof or keep promotion blocked

Focused post-run validation:

- `tools\hd_endurance_release_checklist.py`

## Open Requirement Groups

- `endurance`: `long_soak_representative_routes`
- `manual input`: `stable_menu_real_input, stable_hd_map_real_input`
- `screen route`: `right_bottom_action_menu, castle_and_barracks_centered_input, tactical_battle_entry_return`

## Open Requirement Details

- `long_soak_representative_routes` (`endurance`, `blocked`): 2h+ representative-route soak blocked (blocked_missing_long_proof): 2h+ representative-route soak evidence is locked or missing Next probe: add long-tier reports only after short2/short10/short30 are stable
- `stable_menu_real_input` (`manual input`, `blocked`): menu-load proof remains pending manual DirectInput validation Next probe: collect approved manual menu-load proof or keep promotion blocked
- `stable_hd_map_real_input` (`manual input`, `blocked`): HD map input proof remains pending manual DirectInput validation Next probe: collect approved manual map input proof after short soak is stable
- `right_bottom_action_menu` (`screen route`, `blocked`): right-bottom action/menu remains validation-only or manual-proof blocked Next probe: replace debugger-forced action-click proof with natural or approved manual input proof
- `castle_and_barracks_centered_input` (`screen route`, `blocked`): castle/barracks centered input remains validation-only or manual-proof blocked Next probe: collect approved centered castle/barracks input proof
- `tactical_battle_entry_return` (`screen route`, `blocked`): battle promotion evidence is absent or remains validation-only; callback proof alone is not promotion Next probe: prove battle entry, UI use, return, and post-return map health on an approved route

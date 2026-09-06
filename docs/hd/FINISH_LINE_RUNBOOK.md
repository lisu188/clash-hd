# HD release validation runbook

The finish line now has two distinct execution boundaries. Map render/process
endurance can use the approved `hidden_cdb_host` class without an unlocked
interactive desktop. Manual DirectInput, visible composition, and promotion
still require an unlocked session plus fresh visible/manual approval. Never use
hidden evidence to satisfy those latter claims.

## Evidence and remaining requirements

Read `captures/current/current-evidence-refresh-current.json` for the latest
check results. The July 18 baseline had two failing checks; the September 5
preparation refresh exposed additional unfinished soak integration and
environment failures. A check count is not the definition of a complete HD
release. `reports/hd_completion_audit.md` records the wider acceptance gaps.

| Check | Needs |
|---|---|
| `hd_soak_long_report_guard` | short ladder complete, then 2h+ tiers on BOTH `map-idle` and `map-pan`, then `captures/current/hd-soak-long-proof-current.json` |
| `hd_endurance_release_checklist` | 9/15 requirements pass; the 6 blocked ones are the long soak, four manual-DirectInput proofs, and `tactical_battle_entry_return` |

`tactical_battle_entry_return` is NOT waiting on more battle evidence — the
natural click-to-callback is proven (`c5fe1d70`). `battle_ready` requires
`promotion_status != validation_stage_only`, so it waits on promotion, which
waits on the manual proof.

## Step 1 — Hidden-CDB map short ladder (~52 min)

The existing visible `short2_menu_idle` pass remains the first rung. The four
remaining map rungs may use the hidden-CDB host runner. Its dry-run is the
default; only `-Execute` patches an isolated candidate, builds the non-presenting
memory proxy, and starts CDB on a hidden desktop. Raw artifacts stay under
`C:\ClashCaptures\hd-soak\hidden` and candidates under
`C:\ClashTests\hd-soak\hidden`.

```powershell
## Inspect the resolved hidden plan first; omit -Execute.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_hidden_soak.ps1 `
  -Route map-idle -DurationSec 120 -FrameIntervalSec 15

## Execute only the reviewed hidden_runtime_command emitted by the ladder.
python tools/hd_soak_short_validation_refresh.py
python tools/hd_soak_short_step_status.py
```

Rungs in order: `short2_map_idle` (120s) → `short10_map_idle` (600s) →
`short10_map_pan` (600s) → `short30_map_pan` (1800s). Use 15-second frame
sampling and 10-second forced-pan intervals. Verify no task-owned process remains
between rungs. On any failed marker, proxy, frame, process, cleanup, or shared
guard check, stop and preserve the failing report instead of weakening a gate.

The earlier visible-wrapper question remains separate: on the last unlocked
attempt (21:09) the route got
furthest ever — menu verified 60.49% nonblack, cursor probe converged,
`load-button` click landed a real transition (463k pixels, 60.33% → 97.09%) —
then the window went missing and `load-slot0` never ran. Whether the window
*returns* after the load dialog opens is still unmeasured for the visible GOG
wrapper. Hidden soak success does not answer or erase that failure.

## Step 2 — Long soak tiers (~4h+)

After the short status is 5/5, run hidden `map-idle` and `map-pan` sequentially
for at least 7,200 seconds each with 30-second surface/process sampling and a
shared candidate SHA. Publish the two compact environment-aware guards, then
assemble `hd-soak-long-proof-current.json` with both `report_guards`. The long
guard must keep the hidden environment, proxy, forced-entry, elapsed-coverage,
and `not_applicable_hidden` checks visible. It proves endurance, not input.

## Step 3 — Manual DirectInput, 5 targets (needs its own fresh approval)

Commands are emitted by `python tools/manual_directinput_run_plan.py` (see
`captures/current/manual-directinput-run-plan-current.md`). All five now run the
pulse lane (`-InputMode pulse`) — the OS-cursor lane could never register a
click, since the engine reads the DirectInput accumulator, not the OS cursor
(`589f5700`).

Targets and their gotchas:
1. `stable_menu_load` — cheapest; gates everything below.
2. `stable_hd_map_input` — edge-scroll semantics still need a human read of the frames.
3. `right_bottom_validation_input` — stage `-rightbottomcompose`; **stage the slot5-as-slot0 fixture first** (`scripts/smoke/prepare_right_bottom_slot_fixture.ps1`).
4. `castle_overview_centered_input` — stage `-castlecenter-all`.
5. `castle_barracks_centered_input` — same stage. Barracks descriptor `0x86` IS
   present in the live slot-0 castle; aim `(398,228)` (region interior), with the
   twice-proven `(371,107)` as fallback. Record it as passing only if the frames
   show the build sub-screen actually entered (callback `0044FE70` executing).

Then fill `captures/current/manual-directinput-proof-current.json` and validate:

```powershell
python tools/manual_directinput_checklist.py --require-pass --require-promotion-ready
```

Exact `stage` strings per item matter — a mismatch is the easiest way to fail an
honest run. Also: `PLACEHOLDER_RE` rejects any field containing `replace_` or
`placeholder`, so avoid those words even in prose.

**Honesty note the operator must settle:** the validator has NO input-mechanism
check — it cannot distinguish pulse-injected `SendInput` from a human hand. The
harness therefore tags its rows
`automated_visible_runtime_engine_aim_evidence_not_manual_directinput_release_proof`.
Whether automated-but-real engine input satisfies the `manual_directinput`
evidence class for RELEASE is a judgment call for the repo owner, not something
the tool can decide. Do not quietly relabel it.

Also unresolved: the castle-entry point `(470,397)` has discredited provenance
(it came from the 2026-07-12 session that never loaded the save) and is a
starting aim point awaiting pulse-mode re-verification, not documented evidence.

## Step 4 — Promotion and final refresh

The new `-combinedui-validation` stage combines the existing
HD-layout/frame-restoration, right-bottom, castle, and battle/input groups.
Its [candidate byte report](../../captures/current/combinedui-validation-patch-stage-current.json)
records 166 patched records and zero original/unexpected bytes. This is a
validation candidate, not promoted or runtime-proven composition. See
[COMBINED_UI_VALIDATION.md](COMBINED_UI_VALIDATION.md) for its identity and
remaining route requirements.

With real manual proof valid, run the promotion decisions
(`hd_layout_promotion_decision.py`, `right_bottom_compose_promotion_decision.py`,
`castle_overview_promotion_decision.py`) and inspect affirmative decision
artifacts. A successful command can merely mean that a deferred decision was
evaluated correctly. Before release, require the combined candidate's affected
routes, input, save/load and day transitions, composition, and endurance to pass
on that exact SHA. Validate each advertised resolution against matching
dimensions, stage, and candidate identity. The new frame-restoration recipe has
passing isolated byte builds for the four advertised larger presets and a
partial-tile custom case; those builds still need dimension-aware runtime,
composition, input, and continuity evidence.

Refresh the aggregate after sources and evidence are settled. Investigate each
failure honestly and perform a final acceptance audit across the supported
configurations. Neither a green aggregate nor the finite endurance checklist's
`full_game_complete` field substitutes for that audit or an explicit promotion
decision.

Never promote the stable stage without the real evidence; an honest red beats a
fabricated green.

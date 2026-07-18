# Finish-Line Runbook — the last 2 checks (163/165 → 165/165)

Everything below is blocked on ONE precondition: **an unlocked interactive
session**. Windows denies `SetCursorPos`/`SendInput` into a locked session, so
the intro-skip never lands, the intro auto-plays, and the GOG wrapper dies on its
intro→menu mode switch with a modal `DirectDraw Error DDERR_UNSUPPORTED`
(reproduced 3/3 on 2026-07-18; see commit `e9afefde`). `run_hd_soak.ps1` now
refuses to launch while locked rather than producing a false render/route
failure. Check with `Get-Process LogonUI,LockApp` — absent means unlocked.

## Remaining failing checks

| Check | Needs |
|---|---|
| `hd_soak_long_report_guard` | short ladder complete, then 2h+ tiers on BOTH `map-idle` and `map-pan`, then `captures/current/hd-soak-long-proof-current.json` |
| `hd_endurance_release_checklist` | 9/15 requirements pass; the 6 blocked ones are the long soak, four manual-DirectInput proofs, and `tactical_battle_entry_return` |

`tactical_battle_entry_return` is NOT waiting on more battle evidence — the
natural click-to-callback is proven (`c5fe1d70`). `battle_ready` requires
`promotion_status != validation_stage_only`, so it waits on promotion, which
waits on the manual proof.

## Step 1 — Soak short ladder (~52 min of soak + rests)

Per rung, canonical two-step, **direct invocation only**. Never `Start-Job` or
any detached wrapper: that strips input standing, silently denies
`SetForegroundWindow`, and starves the game's foreground-mode DirectInput (this
caused a full false-failure cycle on 2026-07-18).

```powershell
python tools/hd_soak_dry_run_plan.py          # mint plan
python tools/hd_soak_approval_preflight.py    # emits the tokened -Execute command
# run the emitted command verbatim, directly
python tools/hd_soak_short_validation_refresh.py
python tools/hd_soak_short_step_status.py
python tools/current_evidence_refresh.py      # twice
```

Rungs in order: `short2_map_idle` (120s) → `short10_map_idle` (600s) →
`short10_map_pan` (600s) → `short30_map_pan` (1800s). Rest 5–10 min between
launches — the wrapper degrades across rapid relaunches. On failure: rest 10+
min, retry once, then stop and report rather than burning the wrapper.

**Known open question:** on the last unlocked attempt (21:09) the route got
furthest ever — menu verified 60.49% nonblack, cursor probe converged,
`load-button` click landed a real transition (463k pixels, 60.33% → 97.09%) —
then the window went missing and `load-slot0` never ran. Whether the window
*returns* after the load dialog opens is UNMEASURED. Answer it in one run with
`scratchpad/run_window_timeline_probe.ps1` (250 ms sampling: hwnd, `IsWindow`,
`IsWindowVisible`, `IsIconic`, client rect, style, class) before tuning any
retry budget. Note the wrapper does not destroy its window on a failed mode
switch — it clears `WS_VISIBLE` on the same hwnd — so "missing" may mean hidden.

## Step 2 — Long soak tiers (~4h+)

Two approved 2h+ runs (`map-idle`, `map-pan`, each `duration_sec >= 7200`,
shared candidate SHA), then assemble `hd-soak-long-proof-current.json` with both
`report_guards`. Overnight-friendly.

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

With the manual proof valid, run the promotion decisions
(`hd_layout_promotion_decision.py`, `right_bottom_compose_promotion_decision.py`,
`castle_overview_promotion_decision.py`), then
`python tools/current_evidence_refresh.py` twice. Target **165/165** with
`hd_endurance_release_checklist` `full_game_complete: true`.

Never promote the stable stage without the real evidence; an honest red beats a
fabricated green.

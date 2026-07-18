# Clash95 HD Completion Plan

Generated: 2026-05-22

> Update 2026-06-30: the open questions below were resolved by a full
> disassembly cross-check. See `reports/hd_completion_certainty.md` for the
> ground-truth answers (right-bottom `addon_flags` gate, battle unit-capability
> gate, the natural DirectInput click path, and the exact fixture recipes) and
> `reports/disassembly_cross_check_hd_next_steps.md` for the per-route validation.
>
> Update 2026-07-17 (`c5fe1d70`): **the "real visible click-to-callback proof"
> blocker named throughout this file is closed.** Run
> `captures/archive/battle-visible-input-present-20260717-133221` shows
> `BATTLE_COMMAND_CLICK_GATE_OBSERVED desc=00514b78 eax=1` →
> `BATTLE_COMMAND_CALLBACK eip=0042d4e0` with zero
> `BATTLE_COMMAND_CLICK_GATE_FORCE` rows; `battle_visible_input_summary.py
> --require-click-consumed` passes (command-ready `1/1`, click-consumed `1/1`,
> invalid `0`) and the focused lane figure is `99.95%`, not `99.91%`. The
> `2/3` / `0/3` / `99.91%` figures below are the dated 2026-05-22 state.
> Manual DirectInput proof (`0/5`) and stable promotion remain open.

## Current State

- Branch: `complete-hd-mod-20260515`.
- Original executable: `C:\Clash\clash95.exe`; verified SHA-256 `500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
- Stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
- Castle validation stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`.
- Battle/right-bottom validation stages:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
  and the matching `-battlecenter-inputprobe` stage.
- Validation-only stages remain out of stable: `rightbottomcompose`, `castlecenter`, `castlecenter-hitbox`, `castlecenter-all`, `battlecenter`, and `battlecenter-inputprobe`.
- Runtime policy: repo-only and hidden/no-popup by default. Visible/manual runtime requires a fresh explicit approval immediately before launch.
- Focused battle/right-bottom command-lane completion: `99.91%`; full-game reverse engineering is not `100%`.

## Passing Evidence

- Stable HD-map baseline rebuilt at `C:\ClashTests\hd-map-smoke\clash95_hd_smoke_20260515_103606.exe`.
- Stable candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Stable patch-stage gate: `118` patched, `0` original, `0` unexpected.
- Stable smoke matrix: `captures\current\hd-map-smoke-current.json` and `captures\current\hd-map-smoke-current.md`, PASS.
- Castle validation candidate rebuilt at `C:\ClashTests\cdb-castle-overview-nativerender\clash95_hd_surfdump_20260515_105041.exe`.
- Castle validation SHA-256: `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`.
- Castlecenter-all patch-stage gate: `reports\castlecenter_all_patch_stage_20260515_105041.json`, `134` patched, `0` original, `0` unexpected.
- Fresh hidden castle overview catalog run: `captures\archive\cdb-surface-dump-20260515-105041`, PASS with DirectDraw-palette screenshot and stripe visual-integrity gate.
- Fresh focused overview hitbox run: `captures\archive\cdb-surface-dump-20260515-105411`, PASS.
- Fresh visible-command overview multi-hit run: `captures\archive\cdb-surface-dump-20260515-105458`, PASS.
- Fresh dormant-command overview multi-hit run: `captures\archive\cdb-surface-dump-20260515-105557`, PASS.
- Battle/right-bottom matrix: `captures\current\battle-ui-evidence-current.json` and
  `captures\current\battle-ui-evidence-current.md`, PASS with promotion status
  `validation_stage_only`.
- Visible battle command readiness:
  `captures\current\battle-visible-input-current.json` and
  `captures\current\battle-visible-input-summary-current.md`, partial evidence with
  command-ready runs `2/3`, click-consumed runs `0/3`, invalid runs `1`, and
  focused completion `99.91%`. The invalid raw-send run has one post-`g`
  `80000003` break-instruction exception and 52 CDB breakpoint insert/remove
  failures.
- Visible runtime launcher guard:
  `captures\current\visible-runtime-launcher-guard-current.md`, PASS with
  `scripts/cdb/run_cdb_battle_visible_input_probe.ps1` included in the guarded launcher
  inventory and zero unclassified risky root PowerShell scripts.
- Visible battle harness guard:
  `captures\current\battle-visible-harness-guard-current.md`, PASS. The visible
  battle input harness now fails closed when the CDB log reports breakpoint
  insert/remove failures or a post-`g` `80000003` break-instruction exception
  before command readiness.
- Current no-popup boundary before this batch: `6` core guards, `44` supporting reports, `50` required reports, PASS.

## Known Blockers

- Manual DirectInput proof is still pending for all five required target IDs:
  `stable_menu_load`, `stable_hd_map_input`, `right_bottom_validation_input`,
  `castle_barracks_centered_input`, and `castle_overview_centered_input`.
- `rightbottomcompose` and `castlecenter-all` are still validation-only because current proof is repo-only CDB/proxy evidence, not approved manual input evidence.
- `battlecenter` and `battlecenter-inputprobe` are still validation-only. The
  visible command window is proven ready, but no run yet proves a real visible
  OS click is consumed by the command descriptor and reaches callback
  `0042D4E0`.
- No CDB-only promotion override manifest is active.
- A release can document a reproducible validation build, but it cannot honestly claim complete manual-input release readiness until the manual proof manifest passes or the user explicitly approves a strict override.

## Completion Gates

- Stable HD map: base SHA matches, candidate is outside repo, patch-stage gate passes with `118/118`, smoke matrix passes, no `.exe` appears in the repo.
- Castle/interior: `castlecenter-all` patch-stage report has `0` original and `0` unexpected bytes, `castle_overview_gate.py --require-pass` passes including visual-integrity/stripe detection, focused hitbox and multi-hit parsers pass, no AV/failure-exit rows appear.
- Battle/right-bottom: battle evidence matrix passes, visible-input summary
  records at least one command-ready run, and promotion remains blocked until
  `battle_visible_input_summary.py --require-click-consumed` passes.
- Input: valid manual proof manifest records displayed/native coordinates, selected descriptor or hitbox, callback/state transition, no crash, and no stale process result for all five target IDs.
- Release packaging: README and progress docs explain prerequisites, patch command, smoke command, candidate output path, cleanup, evidence artifacts, limitations, and the no-proprietary-artifacts boundary.

## Coordinator Decisions

- Do not patch `00422305` unless a future hidden/no-popup probe proves that native allocation path is release-blocking.
- Treat `castlecenter-all` as covering the currently proven overview routes: `00422020` redraw callsites through the native-render-then-center `castle-overview-center-present-wrapper` and `00422520` descriptor hit-test through `castle-overview-centered-input`.
- Treat `battlecenter-inputprobe` as covering currently proven battle routes:
  centered 640x480 battle presentation, centered grid/descriptor input
  wrappers, constructed enabled-command callback under hidden CDB, and visible
  command readiness. ~~Do not promote it until real visible click-to-callback
  proof exists.~~ *(That proof landed 2026-07-17, `c5fe1d70`.)* Promotion is
  still gated on manual DirectInput proof and an approved promotion decision.
- Keep stable default unchanged until either manual proof or an explicit override manifest passes.

## Completion Summary

- Focused battle/right-bottom command lane: ~~`99.91%`~~ → `99.95%` as of
  2026-07-17.
- Full-game reverse engineering: not `100%` (still true).
- ~~Current blocker: real visible click-to-callback proof.~~ **Closed
  2026-07-17 (`c5fe1d70`).** Current blockers: manual DirectInput proof
  (`0/5` targets) and stable promotion.

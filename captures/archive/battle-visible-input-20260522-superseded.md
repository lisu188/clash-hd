# Battle Visible Input Current

Date: 2026-05-22

Focused completion: 99.91% for the battle/right-bottom command lane. Full-game
reverse engineering is not 100%.

## Current proof

- Hidden no-popup callback proof remains:
  `captures/archive/cdb-surface-dump-20260520-220459/`
- Screenshot artifact:
  `captures/archive/cdb-surface-dump-20260520-220459/surface.png`
- Visible loader/control proof remains:
  `captures/archive/battle-visible-input-loaderonly-20260521-233400/`
- New visible command-readiness proof:
  `captures/archive/battle-visible-input-quiet-20260521-231521/`
  and `captures/archive/battle-visible-input-minimal-20260521-232626/`
- Generated parser summary:
  `captures/current/battle-visible-input-current.json`
  and `captures/current/battle-visible-input-summary-current.md`
- Integrated battle evidence matrix:
  `captures/current/battle-ui-evidence-current.json`
  and `captures/current/battle-ui-evidence-current.md` now include `visible_input`
  plus open items for click-to-callback proof.
- Visible runtime safety guard:
  `captures/current/visible-runtime-launcher-guard-current.md` now includes
  `scripts/cdb/run_cdb_battle_visible_input_probe.ps1` in the guarded launcher inventory.
- Visible battle harness guard:
  `captures/current/battle-visible-harness-guard-current.md` verifies the harness
  fails fast on CDB breakpoint insert/remove failures and post-`g` `80000003`
  break-instruction exceptions.

Both quiet/minimal visible probes reached:

- natural DirectInput mouse acquire (`BATTLE_DIRECTINPUT_MOUSE_ACQUIRE`)
- save load return (`SURFDUMP_LOADSAVE_RETURN`)
- gameplay surface transition (`SURFDUMP_PLAYGAME`)
- battle route setup (`BATTLE_FORCE_ATTACK_CALL`)
- battle owner entry (`BATTLE_OWNER_ENTRY`)
- command descriptor window (`BATTLE_COMMAND_INPUT_WINDOW`)

The command row shows the expected target:

- displayed click point: `(588,440)`
- native/descriptor-space point: `(508,380)`
- descriptor/list pointer: `00514b78`
- command callback: `0042d4e0`
- surface size: `800x600`

## Open gap

The current visible pass has not yet proven that a real visible `SendInput`
click is consumed by the battle command descriptor gate.

Failed/invalid attempts:

- `captures/archive/battle-visible-input-quiet-20260521-231521/` reached command
  readiness, but the harness timed out before `mouse_path_probe.py` wrote JSON.
- `captures/archive/battle-visible-input-minimal-20260521-232626/` reached command
  readiness faster, but the helper blocked while trying to use HWND/window
  operations during the CDB hot-loop battle state.
- `captures/archive/battle-visible-input-rawsend-20260521-233247/` is invalid as
  evidence because CDB stopped after a post-`g` `80000003`
  break-instruction exception at `ntdll!NtReleaseMutant`, then failed to
  insert/remove 52 software breakpoints (`Win32 299` and `Win32 5`) and did
  not reach the command window.

## Next pass

Avoid HWND-dependent operations after battle command readiness. Capture or fix
the visible window/screen origin before entering the hot battle loop, then send
raw OS cursor/click input without calling `MoveWindow`, `GetClientRect`, or
other HWND operations while CDB is repeatedly stopping the UI thread.

Helper prepared for that next pass:

- `tools/raw_sendinput_click.py --screen-points 668,520 --click-hold-ms 300 --click-repeat 3`
- `scripts/cdb/run_cdb_battle_visible_input_probe.ps1 -InputMode raw-screen -RawScreenPoints 668,520`
- `tools/battle_visible_harness_guard.py --require-pass`
- `tools/battle_visible_input_summary.py ... --require-command-ready`
- `tools/visible_runtime_launcher_guard.py --require-pass`

Completion summary after this pass: focused battle/right-bottom command lane
99.91%; remaining 0.09% is real visible click-to-callback proof plus broader
manual cadence validation.

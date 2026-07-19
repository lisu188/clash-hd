# HD VM Validation Runbook

This runbook completes the Clash95 HD mod by capturing the one thing that is
still outstanding: **approved, real, visible mouse-click ("manual DirectInput")
evidence** for the five required targets, plus the battle click-consumed gate,
feeding the promotion-decision tools. The mod is already mechanically complete
and disassembly-verified (`reports/hd_completion_certainty.md`); this is the
evidence-capture step, run in a VM.

Two runners are provided. The **Windows Sandbox** runner is authoritative. The
**Linux/wine** runner is the "run it here" attempt and carries a fidelity caveat.

## Prerequisites (both runners)

- The proprietary `clash95.exe` matching the base SHA-256
  `500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`. It is not
  in the repo (source-only policy) and must be supplied by you. Never commit it.
- Explicit approval to run a **visible** runtime. Record the approval note/link;
  every runner requires it (`-AllowVisibleRuntime` / `--allow-visible-runtime`).
- A source save to build the right-bottom fixture from (e.g. `C:\Clash\save\5.dat`).
- Never mutate `C:\Clash\clash95.exe` or `C:\Clash\save`; all candidates and
  fixtures live under `C:\ClashTests\...`.

## What the run must prove

The five manual targets (`tools/manual_directinput_checklist.py`):

| Target ID | Stage | What a real click proves |
| --- | --- | --- |
| `stable_menu_load` | stable | centered 640×480 menu hitboxes respond to held clicks |
| `stable_hd_map_input` | stable | map edge-scroll / minimap / selection align with 800×600 |
| `right_bottom_validation_input` | `…-rightbottomcompose` | recovered lower/right action UI responds (needs the addon_flags save fixture) |
| `castle_barracks_centered_input` | `…-castlecenter-all` | centered barracks descriptor/action callbacks reachable |
| `castle_overview_centered_input` | `…-castlecenter-all` | centered overview commands respond without debugger-forced state |

Plus the battle click-consumed gate (`tools/battle_visible_input_summary.py
--require-click-consumed`) from a battle command run, using a real melee+range
roster (e.g. Dragon cavalry) — never a faked/enabled-command override.

Guardrails from the disassembly cross-check (do not violate): use the
`addon_flags & 0x02` save fixture instead of forcing the right-bottom panel; use
a real roster instead of faking an enabled battle command; keep the single
centered mouse-offset model; and never hand-write a passing observation — the
assembler fails closed.

## Runner A — Windows Sandbox (authoritative)

On a Windows host with the "Windows Sandbox" feature
(`Containers-DisposableClientVM`) enabled:

```powershell
# 1. Generate the sandbox config only (no launch) to review it first.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke\run_clash_hd_full_validation.ps1 -NoLaunch

# 2. Run the full five-target session in the disposable VM.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke\run_clash_hd_full_validation.ps1 `
    -ApprovalRecord "approved by <you> on <date>: visible manual DirectInput validation" `
    -SourceSave C:\Clash\save\5.dat -RightBottomBuildingIndex <owned-building-index> `
    -AllowVisibleRuntime
```

Inside the disposable VM this: copies the game (host `C:\Clash` mapped
read-only), builds the three candidate stages, prepares the right-bottom
addon_flags fixture, runs all five targets through `run_clash_visual_smoke.ps1`
with real DirectInput, and writes
`captures\archive\full-validation-<stamp>\run-manifest.json`.

## Runner B — Linux/wine ("run it here")

On a Linux host with the supplied `clash95.exe`:

```bash
# 0. One-time deps. Wine 9.0's new WoW64 runs the 32-bit clash95.exe from the
#    amd64 wine package alone, so the i386 stack is not required (and may be
#    blocked behind restricted mirrors on Ubuntu 24.04).
sudo apt-get update && sudo apt-get install -y wine xvfb xdotool x11-utils ffmpeg
# Verified end to end here: wine launches a Windows program on a headless Xvfb
# display, xdotool drives a real click, and ffmpeg captures a frame. The only
# remaining input is a legitimately owned clash95.exe (base SHA below).

# 1. Dry-run: plan only, no launch, no binary needed. Verifies the target/stage wiring.
python tools/run_hd_linux_validation.py --dry-run

# 2. Real run (requires the binary + approval). Starts Xvfb, patches per stage,
#    launches under wine, drives xdotool clicks, captures frames.
python tools/run_hd_linux_validation.py --execute --allow-visible-runtime \
    --source-exe /path/to/clash95.exe --source-save /path/to/5.dat \
    --approval-record "approved by <you> on <date>" \
    --run-dir captures/archive/linux-wine-run
```

**Fidelity caveat:** wine may not reproduce the Windows DirectDraw/DirectInput
click-consumption path exactly. If any target cannot be observed faithfully
here, fall back to Runner A on Windows and assemble from that run instead.

## After the run (either runner)

1. Review each target's captured frames (`before.png` / `after-*.png`) and, for
   every target in the run manifest, fill in a real `observed_result`,
   `evidence` (screenshot filename or notes), `pass_fail_notes`, set
   `no_crash: true`, and `status: "pass"`. You may edit the run manifest in place
   or supply a separate `--observations` JSON with the same per-target fields.

2. Assemble and validate the proof, then run every promotion gate in one step:

   ```bash
   python tools/complete_hd_promotion.py \
       --run-manifest captures/archive/<run>/run-manifest.json \
       --battle-run-dir captures/archive/<battle-run-dir> \
       --update-checklist --require-pass
   ```

   This writes `captures/current/manual-directinput-proof-current.json`, runs
   `manual_directinput_checklist.py --require-promotion-ready`,
   `battle_visible_input_summary.py --require-click-consumed`, and both
   promotion-decision tools with the proof. On a full pass it checks the two
   remaining boxes in `reports/final_hd_release_checklist.md`.

3. On `promotion-ready: True`, both decision tools report
   `eligible_for_stable_promotion`. Promote the validation patch groups
   (`rightbottomcompose`, `castlecenter-all`) into the stable stage intentionally,
   or cut the `complete-hd` alias — and the mod is release-complete.

If the assembler or any gate fails, it reports exactly which target/field is
missing. Nothing here fabricates evidence: a target only passes when the
approved run actually observed a consumed real click.

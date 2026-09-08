# HD VM Validation Runbook

This runbook describes an approval-gated VM validation lane for the five
manual-input targets. Automated pulse clicks and captured frames require
separate human observations and matching evidence before they can support
manual DirectInput proof. Read [AGENT_HANDOFF.md](AGENT_HANDOFF.md) for current
completion gaps and existing battle evidence; this lane alone does not finish
the HD mod or authorize stable promotion.

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

Use the existing battle click-consumed evidence identified in the current
handoff when it matches the required candidate and proof scope. The historical
callback result is resolved; this runbook does not make it a new task. Any
separately required battle run must use a real melee+range roster and preserve
the `tools/battle_visible_input_summary.py --require-click-consumed` gate.

Guardrails from the disassembly cross-check (do not violate): use the
`addon_flags & 0x02` save fixture instead of forcing the right-bottom panel; use
a real roster instead of faking an enabled battle command; keep the single
centered mouse-offset model; and never invent a passing observation — the
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
`C:\ClashCaptures\windows-sandbox\full-validation-<stamp>-<guid>\run-manifest.json`
on the host. Both Sandbox callers accept an external `-OutRoot` override and
reject output roots inside the repository. Each unique host run directory is
mapped to `C:\ClashCaptures\run` in the guest, keeping raw captures, generated
scripts and manifests outside the repository.

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
    --run-dir /path/to/external/linux-wine-run
```

**Fidelity caveat:** wine may not reproduce the Windows DirectDraw/DirectInput
click-consumption path exactly. If any target cannot be observed faithfully
here, fall back to Runner A on Windows and assemble from that run instead.

## After the run (either runner)

1. Review each target's captured frames and fill in the actual
   `observed_result`, `evidence` and `pass_fail_notes`. Set `no_crash: true`
   and `status: "pass"` only when matching observations support those claims;
   retain failures and missing observations. You may edit the run manifest or
   supply a separate `--observations` JSON with the same per-target fields.

2. Assemble and validate the proof, then run the scoped component decisions:

   ```bash
   python tools/complete_hd_promotion.py \
       --run-manifest /path/to/external/run/run-manifest.json \
       --battle-run-dir /path/to/matching/battle-evidence \
       --require-pass
   ```

   This evaluates fresh, candidate-bound manual and component decision reports.
   Inspect `component_promotion_ready` and each report's failures. Whole-HD
   `promotion_ready` remains false; `--update-checklist` stays blocked in this
   component mode. It does not check release boxes. The separate release-manifest
   mode is described in [COMPLETE_HD_EVIDENCE.md](COMPLETE_HD_EVIDENCE.md) and
   still has incomplete acceptance adapters.

3. Follow [FINISH_LINE_RUNBOOK.md](FINISH_LINE_RUNBOOK.md) and the current
   handoff for the remaining whole-HD evidence. Any stable-stage promotion
   requires a separate explicit decision supported by the required evidence;
   component eligibility alone does not establish release completion.

If the assembler or a gate fails, inspect its reported target and field
failures. The assembler validates supplied records; it cannot independently
prove that a person made a click. Every passing observation must be supported
by the approved run and matching evidence.

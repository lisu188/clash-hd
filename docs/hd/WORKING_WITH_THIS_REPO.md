# Working With This Repo (Read This First)

Concise operating guide for agents touching the Clash95 HD mod. `AGENTS.md` is
the full project-specific guide; this is the short, prescriptive version. When
the two conflict, `AGENTS.md` wins.

## What this project is

A reverse-engineering and binary-patching project that makes the 32-bit Windows
game `clash95.exe` render at HD resolutions instead of native 640x480. The
repository ships only source, documentation, tests, and small evidence
manifests—never the game binary, patched executables, wrapper DLLs, saves, copied
game assets, or large dumps.

## The five rules you must not break

1. **Never modify `C:\Clash\clash95.exe`** (the user's original) and never
   commit any `.exe`/`.dll`/`.dat`/`.raw`/dump. `.gitignore` blocks them; do not
   force-add. Build candidates under `C:\ClashTests\...` or run a
   distinctly-named copy from `C:\Clash`.
2. **Honesty over green gates.** Never make a check pass by weakening it to
   ignore a real failure, pointing it at unrelated evidence, or fabricating
   data. If a gate is red for a real reason, leave it red and document why.
3. **Never fabricate approval or consent.** Manifest fields such as
   `approved: true`, `approval_record`, and visible/manual-runtime runs require
   real, fresh user approval.
4. **The stable stage is protected.** The default stable stage is
   `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
   New patch work belongs in a validation stage. Promotion requires hidden-CDB
   and approved visible-runtime evidence.
5. **Every byte patch verifies old bytes before writing new bytes.** Record the
   executable SHA, file offset, VA/RVA, old bytes, new bytes, stage, rationale,
   and observed effect.

## Check the current state without launching the game

```powershell
python tools/current_evidence_refresh.py
python -c "import json;d=json.load(open('captures/current/current-evidence-refresh-current.json',encoding='utf-8'));print(sum(1 for v in d['checks'].values() if not v.get('passed')),'/',len(d['checks']),'failing')"
```

Run individual fixtures with `python tools/test_<name>.py`.

## Environment constraints

- The shell uses `NoDefaultCurrentDirectoryInExePath=1`. Invoke local batch and
  executable files by explicit path.
- Sandbox restrictions can block child-process chains. PowerShell game/CDB
  harnesses must run only in an approved environment.
- Under the GOG/dgVoodoo DirectDraw wrapper,
  `Process.MainWindowHandle` can remain null. Find the visible titled window for
  the process with `EnumWindows`.
- PowerShell reserves `$pid`; use `$procId` or another variable name.
- **Input injection does reach the game** (commit `589f5700`). The engine reads
  the DirectInput *accumulator*, so `SetCursorPos` and absolute `SendInput`
  moves are invisible to it — they move only the OS cursor. Pulse-mode relative
  injection works (per-poll accumulator reset to screen centre, injected deltas
  applied x8 and read /4; see `-RawMoveMode servo|pulse` in
  `raw_sendinput_click.py`). Older notes blaming `[WinError 5]`, exclusive
  DirectInput, or missing environment privilege for "automation is impossible"
  are **wrong**; treat a `logical_delta` of `[0,0]` with
  `move_method=setcursor` as the signature of that old bug.
- The surfdump proxy under `src/ddraw_surfdump_proxy/` is memory-only and works
  with CDB. The user-owned GOG/dgVoodoo wrapper creates a visible window but can
  prevent useful CDB logging. Use the correct path for the evidence required.

## Capture paths and limitations

- **Hidden CDB surfdump** (`scripts/cdb/run_cdb_surface_dump.ps1`) captures the
  8-bit software surface. It does not capture every minimap, tooltip, or HUD
  layer and can alter palette presentation. Do not classify proxy-only black
  regions as real rendering defects without visible-runtime corroboration.
- **Hidden CDB soak** (`scripts/cdb/run_hidden_soak.ps1`) is a separate,
  additive endurance evidence class. It runs on a hidden desktop with the
  non-presenting memory proxy, samples the software surface through host
  `ReadProcessMemory`, and keeps full host process telemetry. It must record
  `environment=hidden_cdb_host` and
  `input_responsiveness=not_applicable_hidden`; it never proves manual input,
  visible composition, or promotion readiness. The script is dry-run-only
  unless `-Execute` is supplied.
- **Visible runtime** requires explicit approval. It provides real colors and
  final composition, but GDI capture can tear on animated screens. Always
  check a visible grab for tearing before trusting it: run
  `python tools/capture_tear_check.py <frame.png> [--rect L T R B]`, which
  flags a frame when row-to-row diff energy exceeds column-to-column
  (calibrated on the castle overview: torn grab ratio ~2.05 vs clean CDB dump
  ~1.37). For a clean frame, take 2-3 back-to-back grabs and pass them all --
  a consecutive pixel-identical pair (`clean_stable_pair`) is the strongest
  tear-free signal. Prefer the hidden CDB surfdump for geometry; it never
  tears. Tearing is a capture artifact, not a render defect.

## Current frontier

The active September integration is documented in
[`AGENT_HANDOFF.md`](AGENT_HANDOFF.md). Its complete-HD candidate and failing
runtime evidence are separate from the historical component results below.
The stable stage and 800x600 default remain unchanged.

- Terrain tooltip and selected-unit action-panel anchoring have validation-stage
  implementations and hidden/visible layout evidence. They remain outside the
  protected stable stage pending the separate manual-input promotion boundary.
- Right-bottom composition: the rows-present vs rows-absent gate-design
  contradiction is **resolved**. The user's 2026-07-14 ruling (commit
  `96a3d078`) accepts the slot5-as-slot0 fixture run
  `captures/archive/cdb-surface-dump-20260712-155528` as natural-draw evidence,
  and all 7 required promotion checks now pass. Stable promotion is still
  `defer_stable_promotion` — deferred **by decision** pending manual input
  proof (`manual_input_proof_valid=false`), not by an open design question. The
  fixture's own `proof_class` remains `non_natural_isolated_fixture`.
- Battle click-to-callback is **PROVEN** (commit `c5fe1d70`, run
  `captures/archive/battle-visible-input-present-20260717-133221`): a genuine
  `BATTLE_COMMAND_CLICK_GATE_OBSERVED desc=00514b78 eax=1` followed by
  `BATTLE_COMMAND_CALLBACK eip=0042d4e0`, with `BATTLE_COMMAND_CLICK_GATE_FORCE`
  absent from the entire run. This is no longer constrained by the
  visible-window/CDB wrapper split — the `CLASH_PROXY_PRESENT` painting proxy
  (present-on-`Unlock`) resolved that. Manual DirectInput proof for the five
  checklist targets is still outstanding.
- The hidden-CDB soak class may provide map render/process endurance without a
  visible-runtime approval, but it must complete the ordered short ladder and
  both 2h routes honestly. Visible/manual continuity and the five manual-input
  targets still require fresh approval and remain separate claims.

## Safe default actions

Prefer read-only evidence checks, `tools/test_*.py`, documentation maintenance,
and regenerating/repointing evidence reports. Do not alter the stable stage,
weaken gate logic, modify patch bytes, or launch visible/manual runtime unless
the task explicitly requires it and the relevant approval exists.

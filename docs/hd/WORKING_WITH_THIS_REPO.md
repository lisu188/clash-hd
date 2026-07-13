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
- The surfdump proxy under `src/ddraw_surfdump_proxy/` is memory-only and works
  with CDB. The user-owned GOG/dgVoodoo wrapper creates a visible window but can
  prevent useful CDB logging. Use the correct path for the evidence required.

## Capture paths and limitations

- **Hidden CDB surfdump** (`scripts/cdb/run_cdb_surface_dump.ps1`) captures the
  8-bit software surface. It does not capture every minimap, tooltip, or HUD
  layer and can alter palette presentation. Do not classify proxy-only black
  regions as real rendering defects without visible-runtime corroboration.
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

- Terrain tooltip and selected-unit action-panel anchoring still need a
  validation-stage implementation and evidence.
- Right-bottom composition guards contain an unresolved ownership/design
  conflict.
- Battle click-to-callback proof remains constrained by the visible-window/CDB
  wrapper split.
- Long-duration continuity and soak runs require fresh approval.

## Safe default actions

Prefer read-only evidence checks, `tools/test_*.py`, documentation maintenance,
and regenerating/repointing evidence reports. Do not alter the stable stage,
weaken gate logic, modify patch bytes, or launch visible/manual runtime unless
the task explicitly requires it and the relevant approval exists.

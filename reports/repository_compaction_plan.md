# Repository Compaction Plan

Generated: 2026-06-15

## Current Clutter And Problems

- The repository already has a partial compact layout (`scripts/`, `probes/cdb/*`, `tools/`, `reports/`, `cloud/fixtures/`), but newer HD work left duplicate root-level `.ps1` launchers and `.cdb` probes.
- Durable HD notes were mixed into the root: `CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md`, `CLASH95_MENU_LOAD_ROUTE_NOTES.md`, `CLASH95_HD_MOD_ANALYSIS.md`, `HD_MOD_PROGRESS.md`, and `AUTONOMOUS_HD_MOD_CODEX_PROMPT.md`.
- The patcher implementation lives at root as `patch_clash95_hd.py`; this is useful as a compatibility entrypoint, but the implementation belongs under `src/patcher/`.
- DirectDraw proxy source belongs under `src/ddraw_surfdump_proxy/`.
- Current evidence summaries and historical evidence are mixed together in flat `captures/`. Recent cleanup already archived many stale generated captures outside the repo, but the source tree still needs a current/archive split for navigation.
- `tools/repo_structure.py` is currently descriptive only. It needs to become a guard for approved root contents, required directories, wrappers, forbidden artifacts, current evidence links, and stale old-path references.

## Target Tree

```text
README.md
AGENTS.md
.gitignore
patch_clash95_hd.py              # thin compatibility wrapper
docs/hd/                         # durable HD docs and architecture notes
src/patcher/                     # patcher implementation
src/ddraw_surfdump_proxy/         # DDraw surface-dump proxy source
scripts/build/
scripts/capture/
scripts/cdb/
scripts/debug/
scripts/install/
scripts/smoke/
probes/cdb/startup/
probes/cdb/menu/
probes/cdb/mouse/
probes/cdb/map/
probes/cdb/castle/
probes/cdb/battle/
probes/cdb/ui/
probes/cdb/render/
probes/cdb/key-scroll/
tools/
reports/
captures/current/
captures/archive/
cloud/fixtures/
raw/
wiki/
meta/
```

## Files To Keep In Root

- `README.md`, `AGENTS.md`, `.gitignore`
- `patch_clash95_hd.py` as a thin wrapper that invokes `src/patcher/patch_clash95_hd.py`
- `dxcfg_windowed.ini` as a small config file
- `dxcfg_windowed.ini` as a small stable wrapper/config file

## Files To Move

- Move patcher implementation:
  - `patch_clash95_hd.py` -> `src/patcher/patch_clash95_hd.py`
  - Add root wrapper `patch_clash95_hd.py`
- Move DirectDraw proxy source:
  - `ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp` -> `src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp`
  - `ddraw_surfdump_proxy/ddraw_surfdump_proxy.def` -> `src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.def`
- Move durable HD docs to `docs/hd/`:
  - `docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md`
  - `docs/hd/CLASH95_MENU_LOAD_ROUTE_NOTES.md`
  - `docs/hd/CLASH95_HD_MOD_ANALYSIS.md`
  - `docs/hd/HD_MOD_PROGRESS.md`
  - `docs/hd/AUTONOMOUS_HD_MOD_CODEX_PROMPT.md`
- Move or reconcile root PowerShell launchers:
  - `build_ddraw_surfdump_proxy.ps1` -> `scripts/build/build_ddraw_surfdump_proxy.ps1`
  - `capture_clash_client_frame.ps1` -> `scripts/capture/capture_clash_client_frame.ps1`
  - `capture_clash_window.ps1` -> `scripts/capture/capture_clash_window.ps1`
  - `prepare_hd_map_smoke_candidate.ps1` -> `scripts/smoke/prepare_hd_map_smoke_candidate.ps1`
  - `prepare_right_bottom_slot_fixture.ps1` -> `scripts/smoke/prepare_right_bottom_slot_fixture.ps1`
  - `run_cdb_*.ps1` -> `scripts/cdb/`
  - `run_clash_visual_smoke.ps1`, `run_clash_windows_sandbox.ps1` -> `scripts/smoke/`
- Move root `.cdb` probes by domain:
  - startup/boot/crash/stall probes -> `probes/cdb/startup/`
  - menu/load-route probes -> `probes/cdb/menu/`
  - mouse/DirectInput probes -> `probes/cdb/mouse/`
  - map/minimap/post-owner-tile probes -> `probes/cdb/map/`
  - castle/barracks/owner/action probes -> `probes/cdb/castle/`
  - battle probes -> `probes/cdb/battle/`
  - border/descriptor/right-bottom/unit-selection UI probes -> `probes/cdb/ui/`
  - surface/viewport/DirectDraw geometry probes -> `probes/cdb/render/`
  - key scroll probes -> `probes/cdb/key-scroll/`
- Move flat current evidence reports to `captures/current/` where references/tests can be updated mechanically.
- Move historical repo-needed capture fixtures to `captures/archive/` only when they are not already represented under `cloud/fixtures/evidence/`.

## Files To Delete

- No evidence, reports, or fixtures are deleted as part of the source-layout move.
- Root `.cdb` probes are deleted only when they are exact byte-for-byte duplicates
  of already grouped `probes/cdb/<domain>/` files. Conflicting root variants are
  preserved under a `legacy-root/` subdirectory.
- Ignored Python caches may be deleted if Windows permissions allow it:
  - `__pycache__/`
  - `tools/__pycache__/`
  - `captures/tmp-tests-probe/`
- Any deletion must be documented in the final response and in the compaction report. If a file is merely stale evidence, prefer archive/move over deletion.

## Wrappers Needed

- Root `patch_clash95_hd.py` must remain usable with the existing command shape:

```powershell
python .\patch_clash95_hd.py --input C:\Clash\clash95.exe --output C:\ClashTests\...\candidate.exe --stage <stage>
```

- The wrapper must import/run `src/patcher/patch_clash95_hd.py` without changing arguments, stage definitions, patch bytes, or output behavior.
- Existing script wrappers are optional. Prefer updating docs and references to `scripts/<group>/...` rather than keeping many root launchers.

## References To Update

- Replace source references to root patcher implementation with `src/patcher/patch_clash95_hd.py` only when referring to implementation internals; keep user-facing patch commands using the root wrapper.
- Replace root script references such as `.\run_cdb_surface_dump.ps1` with `.\scripts\cdb\run_cdb_surface_dump.ps1`.
- Replace root smoke references such as `.\prepare_hd_map_smoke_candidate.ps1` with `.\scripts\smoke\prepare_hd_map_smoke_candidate.ps1`.
- Replace root probe references such as `probes/cdb/render/clash95_surface_dump_probe.cdb` with the corresponding `probes/cdb/<domain>/...` path.
- Update build scripts that compile the DirectDraw proxy to read sources from `src/ddraw_surfdump_proxy/`.
- Update tests, guards, reports, docs, and evidence link checks for `captures/current/` if current summaries are moved.
- Do not rewrite historical CDB logs or generated run summaries unless a validator explicitly depends on a current path.

## Validation Commands

Use the bundled Python if `python` is unavailable:

```powershell
$PY = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
```

Required validation:

```powershell
& $PY tools\wiki_lint.py
Get-ChildItem tools\test_*.py | ForEach-Object { & $PY $_.FullName }
& $PY tools\repo_structure.py --require-pass
& $PY tools\evidence_index_check.py captures\current\hd-map-evidence-current.md --require-pass
& $PY tools\current_evidence_refresh.py --require-pass
git diff --check
git status --short
rg "patch_clash95_hd.py|ddraw_surfdump_proxy|run_cdb_|run_clash_|prepare_hd_map_smoke_candidate|clash95_.*\.cdb" README.md AGENTS.md docs reports scripts tools probes captures cloud wiki
```

If a validation fails because of pre-existing evidence state or unavailable runtime tooling, record the exact failure and confirm it is non-behavioral.

## Behavioral Invariants

- Do not change patch bytes, stage names, patch grouping, CDB probe contents, or validator semantics except mechanical path/import updates.
- Do not mutate `C:\Clash\clash95.exe` or any user-owned game install.
- Do not stage or commit forbidden proprietary artifacts.
- Preserve the current stable stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.

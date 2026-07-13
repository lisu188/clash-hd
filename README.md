# Clash95 HD

Reverse-engineering and binary-patching project for the 32-bit Windows game
`clash95.exe`. The project extends the original 640x480 renderer to larger
resolutions, expands the gameplay viewport, relocates UI elements, corrects
input coordinates, and verifies each stage with reproducible evidence.

The repository contains source code, patch scripts, launcher code,
documentation, tests, probes, and small evidence manifests. It does **not**
distribute the original game, patched executables, wrapper DLL binaries, saves,
copied assets, CD/ISO contents, cracks, memory dumps, or large raw captures.

## Known-good input

The patcher expects a user-owned `C:\Clash\clash95.exe` with SHA-256:

```text
500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae
```

Never overwrite that file. Generated candidates belong under
`C:\ClashTests\...` or as distinctly named local copies under `C:\Clash`.

## Launcher

Run the Tkinter launcher:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\launcher\run_launcher.ps1
```

The launcher verifies the base executable, creates an isolated candidate under
`C:\ClashTests\launcher\<WxH>`, validates the expected patch bytes, renders the
wrapper configuration, and launches only after an explicit Play action.

Resolution status is defined in `src/launcher/resolutions.json`. The stable
800x600 path remains the reference implementation; other presets and custom
sizes remain experimental until their complete evidence lanes pass.

See `docs/hd/LAUNCHER.md` for setup, controls, packaging boundaries, and local
build instructions.

## Patcher

The patcher creates a new candidate and refuses unknown input bytes:

```powershell
python .\patch_clash95_hd.py --help
```

Patch work must preserve old-byte verification and remain in validation stages
until hidden and visible evidence supports promotion.

The protected stable stage is:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch
```

## Repo-only validation

Regenerate the current evidence reports without launching the game:

```powershell
python tools/current_evidence_refresh.py
```

Print the aggregate failure count:

```powershell
python -c "import json;d=json.load(open('captures/current/current-evidence-refresh-current.json',encoding='utf-8'));print(sum(1 for v in d['checks'].values() if not v.get('passed')),'/',len(d['checks']),'failing')"
```

Run focused fixture tests with:

```powershell
python tools/test_<name>.py
```

Repo-only checks must not launch Clash95, CDB, wrappers, PowerShell runtime
harnesses, or visible windows.

## Runtime evidence

Hidden CDB and visible runtime prove different things:

- `scripts/cdb/run_cdb_surface_dump.ps1` provides repeatable hidden route,
  crash, and software-surface evidence. Its proxy can omit separately composed
  minimap, tooltip, and HUD layers and can alter palette presentation.
- Visible runtime provides final colors and composition but requires explicit
  approval and can produce torn GDI captures on animated screens.

Do not treat proxy-only black regions as live rendering defects without visible
corroboration. Do not treat a successful route as proof of final visuals or
manual input behavior.

## Project layout

```text
src/          Launcher and DirectDraw proxy source
scripts/      Launcher, smoke, CDB, packaging, and runtime harnesses
probes/       CDB and debugger probes
patches/      Patch definitions and metadata
tools/        Evidence generators, guards, parsers, and fixture tests
docs/hd/      Engineering documentation and operating guides
reports/      Current analyses, plans, matrices, and release checklists
captures/     Small current and archived evidence artifacts
cloud/        Portable fixture material used by repository checks
```

## Documentation

Start with:

- `docs/hd/WORKING_WITH_THIS_REPO.md`
- `AGENTS.md`
- `docs/hd/LAUNCHER.md`
- `docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md`
- `docs/hd/HD_MOD_PROGRESS.md`
- `reports/final_hd_validation_matrix.md`
- `reports/final_hd_release_checklist.md`

## Safety and contribution rules

- Never modify `C:\Clash\clash95.exe` in place.
- Never commit proprietary binaries, saves, copied assets, or dumps.
- Verify the input SHA and old bytes before every patch.
- Keep experimental work out of the stable stage.
- Never weaken evidence gates to hide a real failure.
- Never fabricate approval, runtime observations, screenshots, or promotion
  evidence.
- Visible/manual runtime requires fresh explicit approval.

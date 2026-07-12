# Clash95 HD Launcher

The launcher is the user-facing way to build and start the Clash95 HD mod. It
verifies the base game, patches an isolated candidate, deploys the DirectDraw
wrapper config next to it, and starts the game — all from a small Tkinter GUI.
It replaces the manual verify/patch/copy/launch loop for end users.

## Start The Launcher

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\launcher\run_launcher.ps1
```

or directly:

```powershell
python .\src\launcher\run.py
```

Useful flags: `--dry-run` prints the environment report and candidate plan as
JSON without writing anything; `--gui-selftest` constructs and destroys the
widget tree headlessly. A headless launch needs the explicit double flag
`--launch --yes-launch`.

## What It Does

1. Verifies `C:\Clash\clash95.exe` against the known-good SHA-256
   (`500055d7…cdaf3ae`). On mismatch the launcher refuses to patch and offers
   no override; the CLI patcher's `--allow-unknown-sha` remains the only
   deliberate escape hatch outside the launcher.
2. Patches the stable HD stage into a launcher-owned candidate under
   `C:\ClashTests\launcher\<WxH>\clash95_hd_<WxH>.exe`, reusing the existing
   candidate when its SHA already matches. Every build passes a byte-manifest
   gate (all selected patch bytes present, zero original, zero unexpected)
   before the launcher will start it.
3. Copies the user's DirectDraw wrapper `ddraw.dll` from `C:\Clash` next to
   the candidate and renders `dxcfg.ini` from the tracked
   `dxcfg_windowed.ini` template. The launcher never ships or downloads DLLs
   or executables; if the wrapper is missing it shows instructions instead of
   launching.
4. Starts the candidate with `C:\Clash` as the working directory when the
   user presses Play.

Game resolution and window scaling are separate concepts in the UI: the game
resolution is the true engine canvas selected by the patch stage, while
window scaling is handled by the wrapper (`scaling=` in `dxcfg.ini`) and does
not change game pixels. Only wrapper vocabulary verified against a real
install is offered; until then the template value (`integer`) is used
verbatim.

## Resolution Status Badges

`src/launcher/resolutions.json` is the committed status manifest consumed by
both the GUI and `tools/resolution_manifest_guard.py`:

- `stable` — the default 800x600 stage, backed by the full archived evidence
  set. Exactly one resolution is `stable`.
- `validated` — a resolution whose hidden-desktop CDB evidence lane passed;
  the manifest links its run directories and smoke matrix.
- `experimental` — offered behind a warning dialog; no runtime evidence yet.
  Custom typed resolutions are always treated as experimental and never
  appear in the manifest.

## Runtime Policy Carve-Out

The launcher is a user-facing interactive tool, not an evidence harness. Its
visible game launch is user-initiated by definition: the process starts only
from the GUI Play button or the CLI `--launch --yes-launch` double flag, and
`core.launch_game` refuses anything that does not pass `confirmed=True` from
those paths. The launcher is never part of the evidence refresh; evidence
lanes remain hidden-desktop CDB only. It writes only under
`C:\ClashTests\launcher\` and `%LOCALAPPDATA%\ClashHD\`, and it never
modifies `C:\Clash\clash95.exe`. `tools/launcher_policy_guard.py` enforces
all of this from source.

## User State

Settings (last resolution, scaling mode, paths, window geometry) persist in
`%LOCALAPPDATA%\ClashHD\settings.json`; a PID lock file in the same folder
prevents concurrent launcher instances. `C:\ClashTests\launcher\` holds only
regenerable candidates and can be deleted at any time (the GUI's "Clean
candidates" button removes the selected resolution's folder).

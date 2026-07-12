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

## Per-Resolution Evidence Lanes

Preset resolutions stay `experimental` until their hidden-desktop evidence
lane passes and `src/launcher/resolutions.json` flips them to `validated`.
The lane per preset (1024x768 first — smallest offsets, cheapest discriminator
for the partial right column — then the 1920x1080 flagship):

1. Build the candidate: `python patch_clash95_hd.py --input
   C:\Clash\clash95.exe --output C:\ClashTests\launcher\<WxH>\clash95_hd_<WxH>.exe
   --resolution <WxH>` and gate it with `python tools/patch_stage_report.py
   --exe <candidate> --stage <stable stage> --resolution <WxH>
   --require-current-hd-map` (the gate's tile expectation derives from the
   resolution profile).
2. Hidden-desktop CDB normal run. The surface-dump probe already sizes the
   dump from the live surface header (`SURFDUMP_READY` computes
   width*height and `.writemem` uses that length), so a normal run needs no
   probe edits; `scripts/cdb/run_cdb_surface_dump.ps1` still needs a
   `-Resolution` parameter threaded into its internal patcher call before it
   can build non-800x600 candidates itself, and the forced-visible-edge
   sampling rows hardcode an 800-byte stride that must be parameterized
   before forced runs are meaningful at other sizes.
3. Audit/extend the dump consumers for the new cell grid before gating:
   `tools/cdb_surface_dump_to_png.py` dimensions and the
   `tools/map_tile_coverage.py` minimap region must derive from the
   resolution profile.
4. Gate with `python tools/hd_map_smoke_matrix.py --resolution <WxH>
   --normal-run <run> --forced-run <run> --require-pass --write-json
   captures/current/hd-map-smoke-<WxH>-current.json` (non-default
   resolutions refuse the archived 800x600 default runs).
5. Flip the manifest entry to `validated` with the evidence paths;
   `tools/resolution_manifest_guard.py` verifies the runs are hidden-desktop
   and the matrix passes. `stable` stays exclusive to 800x600.

Run evidence lanes only when no other Clash95/CDB session is active on the
machine — concurrent manual or visible sessions make process-hygiene
snapshots ambiguous.

## User State

Settings (last resolution, scaling mode, paths, window geometry) persist in
`%LOCALAPPDATA%\ClashHD\settings.json`; a PID lock file in the same folder
prevents concurrent launcher instances. `C:\ClashTests\launcher\` holds only
regenerable candidates and can be deleted at any time (the GUI's "Clean
candidates" button removes the selected resolution's folder).

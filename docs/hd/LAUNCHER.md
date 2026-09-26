# Clash95 HD Launcher

The launcher verifies a user-owned game, prepares an isolated patched candidate
and starts it after an explicit Play action. [Development and verification](DEVELOPMENT.md)
covers Python discovery and source-only checks; the [documentation index](README.md)
links the implementation and evidence guides.

## Start The Launcher

Use Python with Tkinter (CI uses Python 3.12), a complete game installation and
its user-owned DirectDraw wrapper. Run from the repository root:

```powershell
python -B src/launcher/run.py
```

The PowerShell wrapper accepts an explicit interpreter when the PATH command is
missing or points at a Windows Store alias:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\launcher\run_launcher.ps1 -Python C:\path\to\python.exe
```

| Operation | Behavior |
| --- | --- |
| `--list-resolutions` | Lists profile-scoped eligibility and status without game files or writes |
| `--describe-plan --resolution 1920x1080` | Inspects geometry without game files or writes |
| `--dry-run` | Reports the local environment and candidate plan without writes; missing game/source prerequisites can return failure |
| `--prepare` / GUI **Create HD exe** | Builds/deploys a candidate without starting the game |
| GUI **Play** / `--launch --yes-launch` | Explicitly starts a visible game process |
| `--gui-selftest` | Constructs and destroys a withdrawn Tk window; still needs a working Tk display |

CLI launch does not make the game headless. `--prepare` cannot be combined with
`--launch`, `--dry-run` or `--gui-selftest`. Preparation can succeed without a
wrapper and reports `runtime_deployed=false`; Play requires the wrapper.
The [UI guide](LAUNCHER_UI.md) explains controls, path settings and diagnostics.

## Renderer profiles

The [resolution registry](../../src/launcher/resolutions.json) and source
backends own recipe eligibility. Profile selection alone does not change the
saved Classic defaults or grant runtime acceptance.

| Profile | Scope and status | Recipe guide |
| --- | --- | --- |
| `classic` | Default; 800x600 is the sole stable entry. Other sizes remain experimental. Source-tree presets at least 1144 pixels wide use the separate wide-menu recipe. | [Wide Classic menus](CLASSIC_MENU_LAUNCHER.md) |
| `framed` | Four-sided adventure frame and minimap correction; all sizes experimental. | [Framed launcher](FRAMED_LAUNCHER.md) |
| `completehd` | Integrated framed adventure map, minimap, owned native modal canvas and army panel; all sizes experimental. | [Complete candidate](COMPLETE_HD_CANDIDATE.md) |
| `modalwidgets` | Adds primary composition, barracks quantity text and context-bound widget comparisons to the Complete HD foundation; all sizes experimental. | [Modal-widget launcher](MODAL_WIDGET_LAUNCHER.md) |

Complete HD and Modal widgets admit exactly 800x600, 1024x768, 1280x720,
1280x960, 1920x1080 and the 802x602 fixture size. Their native menu, castle and
battle layouts remain centered. Expanded battle is a separate validation lane,
not a launcher profile. Use `--profile <name> --list-resolutions` for the
selected recipe's eligibility rather than applying another profile's presets.

## Complete-HD Validation Profile

Inspect the profile without executing a game or writing candidate files:

```powershell
python -B src/launcher/run.py --profile completehd --resolution 1920x1080 --describe-plan
python -B src/launcher/run.py --profile completehd --list-resolutions
```

Prepare its candidate and available user-owned wrapper without starting a game:

```powershell
python -B src/launcher/run.py --profile completehd --resolution 1920x1080 --prepare
```

The shared builder and source-bound verification are documented in
[COMPLETE_HD_CANDIDATE.md](COMPLETE_HD_CANDIDATE.md). Existing files are reused
only when byte-identical; changed recipes need a distinct candidates root or
reviewed cleanup. Candidate, probe, metadata, sources and deployment identities
must match before reuse or Play. A build or prepared bundle does not establish
release eligibility; see [COMPLETE_HD_EVIDENCE.md](COMPLETE_HD_EVIDENCE.md).

## What It Does

1. Verifies the original `C:\Clash\clash95.exe` against SHA-256
   `500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
   The launcher refuses unknown originals and offers no hash override.
2. Selects the profile/resolution recipe and verifies the candidate bytes and
   metadata. It creates an isolated candidate outside the repository and never
   overwrites the original.
3. Copies the user's `ddraw.dll` when available and renders `dxcfg.ini` from
   [the tracked wrapper template](../../dxcfg_windowed.ini). It never downloads
   or supplies executable game or wrapper binaries.
4. Starts the prepared candidate with the game installation as its working
   directory only on Play or the explicit CLI launch flags.

Default output directories are separate:

| Recipe | Under `C:\ClashTests\launcher\` |
| --- | --- |
| Classic scalar path | `<WxH>\` |
| Classic wide-menu extension | `classic-menu-validation\<WxH>\` |
| Framed | `framed-minimap\<WxH>\` |
| Complete HD | `completehd-validation\<WxH>\` |
| Modal widgets | `modalwidgets-validation\<WxH>\` |

Game resolution is the engine canvas. Wrapper scaling changes window
presentation without changing game pixels; the existing verified template uses
`integer` scaling. Profile implementation details belong in the linked recipe
guides.

## Resolution Status Badges

Status is scoped to a recipe and resolution:

- `stable`: the protected Classic 800x600 reference entry.
- `validated`: a resolution whose required evidence lane has been accepted in
  the registry; this is not automatic whole-release promotion.
- `experimental`: acceptance is incomplete. There may already be source,
  hidden or failed visible observations; the badge does not mean no tests exist.

At this checkpoint the registry has no `validated` entries. Custom dimensions
are experimental where a profile permits them. The current handoff records
which source fixes are integrated and which candidates still lack matching
runtime, ordinary input, continuity or release evidence.

## Runtime Policy Carve-Out

The launcher is a user-facing tool. Its explicit Play action or
`--launch --yes-launch` combination is the documented launch boundary.
`tools/launcher_policy_guard.py` checks that policy from source. Creating a
launcher plan is not runtime authorization, and a normal launch is not an
evidence capture. Automated runtime and manual/visible validation follow
[AGENTS.md](../../AGENTS.md) and their own protocol guides.

## Per-Resolution Evidence Lanes

Keep each lane bound to the selected stage, recipe, resolution, exact candidate
and source revision. Follow [the current handoff](AGENT_HANDOFF.md) and the
[owning protocol guide](README.md#evidence-and-release-work) before executing a
lane. Historical Classic 800x600 observations cannot validate Framed, Complete
HD, Modal widgets or expanded battle by implication.

Promotion requires the actual prescribed evidence and an explicit decision.
Do not flip a registry badge after only a successful build, a source fixture or
an unrelated archived smoke result. Review report provenance and missing local
artifacts before planning a new run.

## User State

Settings persist in `%LOCALAPPDATA%\ClashHD\settings.json`; a PID lock file in
the same folder prevents concurrent launcher instances. The GUI offers folder
selection and selected-candidate cleanup with confirmation.

Before cleanup, check for active users and whether exact candidates, metadata or
source snapshots are still referenced by retained evidence. A directory holding
regenerable executables can also contain provenance needed for replay; its name
alone does not make it disposable. Follow [the disk and artifact policy](../../AGENTS.md).

## Local launcher packaging

The [packaging helper](../../scripts/launcher/build_launcher_exe.ps1) prints a
dry-run plan by default:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\launcher\build_launcher_exe.ps1 -Python C:\path\to\python.exe
```

After installing PyInstaller in the selected Python environment, add `-Execute`
to build locally. Outputs default to `C:\ClashTests\launcher\build`; the helper
refuses a repository output directory. Do not commit the generated executable.
The packaged launcher exposes Classic only; experimental source recipes and
wide-menu source composition require their complete checkout. Building a
launcher package does not certify gameplay or release acceptance.

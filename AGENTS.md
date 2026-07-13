# LLM Wiki Agent Operating Schema

> New here, or a smaller/lower-tier model? Read
> `docs/hd/WORKING_WITH_THIS_REPO.md` first — a short, prescriptive guide to the
> five hard rules (never touch the original exe, honesty over green gates, never
> fabricate approval, the stable stage is sacred, verify old bytes), the
> environment gotchas, and the safe actions. This file is the full spec.

## Project Purpose

This repository is a personal, Obsidian-compatible, LLM-maintained markdown wiki.
The user curates durable source material in `raw/`. Codex and future LLM agents
read those sources, extract stable knowledge, and maintain `wiki/` as a
compounding knowledge base with summaries, entities, concepts, contradictions,
backlinks, syntheses, comparisons, questions, and a chronological log.

The wiki is not a transient chat answer and not just a search index. Treat it as
the user's long-lived memory artifact.

## Directory Ownership Rules

- `raw/`: User-owned source of truth. Do not edit raw files.
- `raw/inbox/`: New user-provided sources waiting for ingest.
- `raw/processed/`: Sources moved here only after explicit user approval.
- `raw/assets/`: User-provided images, PDFs, media, and other supporting files.
- `wiki/`: Agent-maintained markdown knowledge base.
- `wiki/sources/`: One source-summary page per ingested source.
- `wiki/entities/`: People, organizations, projects, products, places, works,
  datasets, and other named things.
- `wiki/concepts/`: Reusable ideas, terms, methods, patterns, and theories.
- `wiki/syntheses/`: Cross-source synthesis pages.
- `wiki/questions/`: Open questions, research threads, and unresolved decisions.
- `wiki/comparisons/`: Structured comparisons between entities, concepts,
  sources, or options.
- `meta/templates/`: Page templates. Update when page conventions evolve.
- `meta/workflows/`: Human-readable workflows for ingest, query, lint, and
  contradiction handling.
- `tools/`: Small dependency-free helper scripts.
- Clash95 HD mod files in the repository root are engineering artifacts for the
  Windows game patching work. Do not overwrite the original
  `C:\Clash\clash95.exe` unless the user explicitly asks.
- Do not track proprietary `.exe` files, game assets, saves, CD/ISO contents,
  cracks, dumps, or copied game resources in git. The repository ignores
  root-level `.exe` files so candidates can be generated locally without being
  committed.
- Build and test patched executables in `C:\Clash` or isolated
  `C:\ClashTests\...` folders. If the user explicitly asks for a local handoff
  executable in the repository root, keep only one freshest untracked `.exe`
  artifact, document it, and remove stale executable artifacts before commit.
- Launcher policy carve-out: the end-user launcher (`src/launcher/`,
  `scripts/launcher/run_launcher.ps1`, `docs/hd/LAUNCHER.md`) is a user-facing
  interactive tool, not an evidence harness. Its visible game launch is
  user-initiated by definition (`core.launch_game` requires `confirmed=True`
  from the GUI Play button or the CLI `--launch --yes-launch` double flag), it
  writes only under `C:\ClashTests\launcher\` and `%LOCALAPPDATA%\ClashHD\`,
  it never modifies `C:\Clash\clash95.exe`, never ships or downloads
  binaries, and is never invoked by the evidence refresh. Agents keep using
  the hidden-desktop no-popup boundary; the launcher's `--dry-run` is the only
  launcher path agents run without fresh explicit user approval.
  `tools/launcher_policy_guard.py` enforces this from source.

<!-- clash-hd-windows-toolchain-start -->

### Windows debugger/toolchain workflow

Use Windows-host tools for executable/runtime evidence. Prefer isolated test folders:

- `C:\Clash` for the user-owned game install.
- `C:\ClashTests\base`
- `C:\ClashTests\ddrawcompat`
- `C:\ClashTests\dxwnd`
- `C:\ClashTests\dgvoodoo2`
- `C:\ClashDumps`
- `C:\ClashCaptures`
- `C:\Tools`

Never copy wrapper DLLs into `System32`. Never mutate the original executable. Copy patched executables and wrapper DLLs only into isolated test folders.

Tool discovery:
- CDB x86: `%ProgramFiles(x86)%\Windows Kits\10\Debuggers\x86\cdb.exe`
- WinDbg: `windbgx.exe` or Windows Kits WinDbg
- GFlags: `%ProgramFiles(x86)%\Windows Kits\10\Debuggers\x64\gflags.exe` or sibling debugger folders
- Sysinternals: `C:\Tools\Sysinternals\procdump.exe`, `procmon.exe`, `procexp.exe`
- x64dbg/x32dbg: use `x32dbg.exe` for `clash95.exe`
- Portable tools: look under `C:\Tools`
- Use `where.exe cdb`, `where.exe procdump`, `where.exe procmon`,
  `where.exe procexp`, `where.exe x32dbg`, and `where.exe windbgx`.
- If PATH is incomplete, recursively search `C:\Tools` and Windows Kits
  folders.

CDB / WinDbg:
- Use x86 CDB for Clash95 because it is a 32-bit target.
- Use CDB for repeatable crash logs and scripted evidence.
- Current active workflow is CDB-only. Use host CDB, hidden-desktop CDB,
  local CDB probes, and CDB-only harnesses for new validation.
- For no-popup runtime evidence, prefer `scripts/cdb/run_cdb_surface_dump.ps1`, hidden
  desktop CDB launches, local CDB probes, and CDB-only harnesses.
- Avoid semicolons in CDB `.echo` lines. CDB command files are
  semicolon-sensitive, and a semicolon inside an echo message can stop the probe
  before breakpoints are installed.
- Standard crash command pattern:
  `& $CDB -y "srv*C:\Symbols*https://msdl.microsoft.com/download/symbols" -c "sxe av; g; .exr -1; .ecxr; kb; lm; !analyze -v; q" "C:\Clash\clash95_hd_candidate.exe" > "C:\ClashDumps\cdb_candidate.log"`
- For dump analysis, open WinDbg and run: `!analyze -v`, `.ecxr`, `kb`, `lm`, `u eip-20 eip+20`, `dd esp`.
- Record exception code, faulting module, EIP, stack, loaded wrapper DLLs,
  exact patched executable hash, and whether the crash reproduces.

GFlags:
- Use only for targeted crash/debug sessions.
- Enable per-image page heap only for a candidate exe:
  `gflags /p /enable clash95_hd_candidate.exe /full`
- Disable after the session:
  `gflags /p /disable clash95_hd_candidate.exe`
- Never leave broad/system-wide flags enabled.

ProcDump:
- Use for crash/hang dumps:
  `procdump -accepteula -ma -e -x C:\ClashDumps C:\Clash\clash95_hd_candidate.exe`
  `procdump -accepteula -ma -h -w clash95_hd_candidate.exe C:\ClashDumps`
- Save dumps outside the repo unless explicitly requested.
- Commit only scripts, manifests, and docs, not dump files.

ProcMon:
- Use filters:
  - `Process Name is clash95_hd_candidate.exe`
  - `Operation is Load Image`
  - `Operation is CreateFile`
  - `Operation is RegQueryValue`
  - `Path contains ddraw`
  - `Path contains clash`
- Use ProcMon to prove file access, registry access, DLL loading, wrapper
  behavior, and missing-resource issues.
- Prefer summary/manifests in `captures/`, not huge raw PML files.

Process Explorer:
- Verify loaded DLLs, especially:
  - local `ddraw.dll`
  - system `ddraw.dll`
  - DirectInput DLLs
  - DDrawCompat DLLs/configs
  - dgVoodoo DLLs
  - unexpected user/system DLLs
- Record process bitness and command line.

x32dbg:
- Use for interactive 32-bit stepping.
- Breakpoints worth trying: `DirectDrawCreate`, `DirectDrawCreateEx`, `CreateWindowExA`, `SetWindowPos`, `MoveWindow`, `GetClientRect`, `GetWindowRect`, `GetCursorPos`, `ScreenToClient`, `ClientToScreen`, `SetCursorPos`, `DirectInputCreateA`, `GetMessageA`, `PeekMessageA`, `BitBlt`, `StretchBlt`.
- Correlate runtime VA, RVA, file offset, old bytes, new bytes, and observed behavior before changing patch scripts.

Ghidra:
- Import the original base executable first, not random patched copies.
- Use patched copies only for deliberate binary comparison.
- Name functions/constants using evidence from:
  - `clash-disassembly`
  - CDB traces
  - x32dbg traces
  - patch notes
  - captures
- Use Ghidra to distinguish:
  - menu constants
  - surface dimensions
  - gameplay viewport loops
  - scroll clamps
  - input coordinate transforms
  - DirectDraw setup
- Keep Ghidra project files out of commits unless the repo explicitly tracks them.

HxD / PE-bear / Dependencies / Detect It Easy:
- HxD: verify bytes, search constants, inspect candidate executables, and
  compare patched files manually.
- PE-bear: inspect PE sections, image base, imports, RVA/file-offset mapping,
  checksum, and overlays.
- Dependencies: inspect import/load issues and wrapper DLL dependencies.
- Detect It Easy: record compiler/packer/PE metadata only; do not treat it as proof of patch correctness.

DirectDraw wrapper experiments:
- DDrawCompat:
  - Copy extracted `ddraw.dll` next to the candidate exe in an isolated folder.
  - Use process-local config such as `DDrawCompat.ini` or exe-specific config
    if supported by the installed version.
  - Do not configure globally first.
- DxWnd:
  - Create a profile pointing to the candidate exe.
  - Use logs and hook settings for A/B comparison of fullscreen, window,
    mouse, and palette behavior.
- dgVoodoo2:
  - Copy x86 DirectX wrapper DLLs from its package into an isolated test folder
    only.
  - Use `dgVoodooCpl.exe` for test config.
  - Record exactly which DLLs were copied and from where.
- RenderDoc:
  - Use only after output is routed through D3D11/D3D12 wrappers such as
    dgVoodoo2.
  - It is not direct proof for raw DirectDraw output.
- API Monitor:
  - Use the x86 monitor for the 32-bit game.
  - Watch DirectDraw, GDI, windowing, and input APIs.
  - Treat it as intrusive; always compare against a non-monitored run.

Evidence rules:
- A nonblack frame is not enough.
- Prefer client size, render bounds, menu panel bounds, tile counts, hitbox
  alignment, crash logs, input traces, and DLL-load proof.
- When a probe needs hot render breakpoints such as `004024E0`, do not arm them
  from process start. Route to gameplay first, then late-arm the hot breakpoints
  or the menu/AVI path can stall under CDB before the target evidence appears.
- Treat timeout exit 124 as acceptable only for intentional liveness tests.
- Every patch must verify old bytes before writing new bytes.
- Record SHA, file offset, VA/RVA, old bytes, new bytes, stage, rationale, and observed effect.
- If tools are unavailable, implement repo-only helpers:
  - patch-byte verifier
  - capture geometry analyzer
  - smoke-matrix parser
  - wrapper manifest generator
  - docs/state cleanup

<!-- clash-hd-windows-toolchain-end -->

## Clash95 HD Debugging Workflow

The game is a 32-bit Windows executable. Prefer x86 debugging tools and run
patched executables from `C:\Clash` so the game can find its data files.

Use this default loop for engine patch work:

1. Build or copy a uniquely named patched executable, for example
   `clash95_hdmap12_novswitch_relinput.exe`.
2. Place or run it under `C:\Clash` with `C:\Clash` as the working directory.
3. Kill stale game/debugger instances before each automated run unless the task
   is specifically about attaching to an existing process.
4. Skip the startup animation before judging menu or input behavior. The current
   automation sends repeated center clicks plus `Space` pulses for this.
5. Verify visuals with frame dumps first, then verify crashes/input with CDB
   probes. PowerShell `SendInput`/`PostMessage` clicks are useful test signals
   but are not proof that manual DirectInput mouse behavior works.
6. Stop any newly launched game/debugger process before ending the task.

Preferred headless debugger:

- Use x86 CDB at
  `C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe`.
- Use `.cdb` scripts in this repository for repeatable probes.
- x32dbg is useful for interactive GUI investigation, but CDB is the practical
  choice for repeatable headless logs.

Useful commands:

```powershell
.\scripts\cdb\run_cdb_menu_probe.ps1 `
  -Exe 'C:\Clash\clash95_hdmap12_novswitch_relinput.exe' `
  -Probe .\probes\cdb\startup\clash95_hd_crash_probe.cdb `
  -Log 'C:\Clash\hd-cdb-menu.log' `
  -RunSeconds 10
```

```powershell
.\scripts\cdb\run_cdb_mouse_probe.ps1 `
  -Exe 'C:\Clash\clash95_hdcentered_hitboxes.exe' `
  -Log 'C:\Clash\hd-cdb-mouse-probe.log' `
  -NoWait
```

```powershell
.\scripts\smoke\run_clash_test.ps1 `
  -Exe 'C:\Clash\clash95_hddisplay_absinput.exe' `
  -Probe `
  -MenuWaitSec 8 `
  -AutoCloseSec 5
```

If a run hangs, clean up with a targeted process kill:

```powershell
Get-Process -ErrorAction SilentlyContinue |
  Where-Object {
    $_.ProcessName -like 'clash95*' -or
    $_.ProcessName -eq 'cdb'
  } |
  Stop-Process -Force -ErrorAction SilentlyContinue
```

## Clash95 Ghidra Workflow

Use Ghidra for static analysis and decompiler-assisted patch discovery. Use CDB
for runtime proof. Treat Ghidra addresses as virtual addresses until converted
and verified against original executable bytes.

Known local reverse-engineering artifacts:

- `C:\Clash\reverse\README.md`: notes for the current Ghidra export.
- `C:\Clash\reverse\ghidra\ExportClash95Facts.java`: headless post-script that
  applies names from `clash95.map` and exports metadata, imports, functions, and
  selected decompilation.
- `C:\Clash\reverse\ghidra-out\metadata.txt`: image base, language, entry
  points, and memory blocks. Current export says image base `00400000`,
  language `x86:LE:32:default`, compiler spec `windows`.
- `C:\Clash\reverse\ghidra-out\imports.csv`: imported Win32, DirectX, AVI, and
  audio symbols.
- `C:\Clash\reverse\ghidra-out\functions.csv`: function inventory after applying
  map names. Current export has 3,204 analyzed functions.
- `C:\Clash\reverse\ghidra-out\selected_decompilation.c`: decompiler output for
  selected high-value functions.

Find a Windows Ghidra install with:

```powershell
Get-ChildItem 'C:\Program Files','C:\Program Files (x86)','C:\Tools',$env:LOCALAPPDATA,$env:ProgramData `
  -Recurse -Filter analyzeHeadless.bat -ErrorAction SilentlyContinue |
  Select-Object -First 10 FullName
```

If `analyzeHeadless.bat` is not found, ask the user for the exact Ghidra install
path. Do not assume `winget install --id NSA.Ghidra` works; that package id may
not exist on the user's winget source.

Headless export command once the Ghidra path is known:

```powershell
$GhidraHeadless = 'C:\Path\To\ghidra_XX.X_PUBLIC\support\analyzeHeadless.bat'
& $GhidraHeadless `
  'C:\Clash\reverse\ghidra-projects' `
  'clash95' `
  -import 'C:\Clash\clash95.exe' `
  -overwrite `
  -scriptPath 'C:\Clash\reverse\ghidra' `
  -postScript ExportClash95Facts.java 'C:\Clash\clash95.map' 'C:\Clash\reverse\ghidra-out'
```

GUI workflow:

1. Start `ghidraRun.bat`.
2. Create or open a project under `C:\Clash\reverse\ghidra-projects`.
3. Import `C:\Clash\clash95.exe`; Ghidra should identify it as a 32-bit Windows
   PE, `x86:LE:32:default:windows`.
4. Run default analysis.
5. Run `ExportClash95Facts.java` with arguments
   `C:\Clash\clash95.map C:\Clash\reverse\ghidra-out`.
6. Use the Symbol Tree, Decompiler, Function Graph, Defined Strings, and
   References views to investigate viewport, DirectDraw, DirectInput, menu, and
   tile-drawing code.

How to use Ghidra results for the HD mod:

- Start from `imports.csv` to find DirectDraw and DirectInput call sites, then
  inspect callers in Ghidra.
- Search `functions.csv` and the Symbol Tree for known names such as
  `Render_CreateSurface`, `PlayGame`, `PlayGame_Dispatch`, AVI startup
  functions, menu functions, map loading, and drawing helpers.
- Add newly discovered high-value function names to `SELECTED_NAMES` in
  `ExportClash95Facts.java`, rerun headless export, and inspect the refreshed
  `selected_decompilation.c`.
- Use Ghidra virtual addresses directly for CDB breakpoints when the module is
  loaded at its normal base, for example `bp 00401020`.
- Never patch by virtual address alone. Convert VA to file offset using PE
  section headers or an offset helper, then verify expected original bytes before
  writing a patch.
- Record function names, Ghidra addresses, file offsets, original bytes, patched
  bytes, and rationale in `docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md`.
- For each candidate patch, connect the evidence chain: Ghidra decompilation
  suggests the constant/global, CDB proves it is reached at runtime, frame dumps
  prove the visual/input effect.

Useful future Ghidra helpers:

- Extend `ExportClash95Facts.java` to export references to constants `640`,
  `480`, `800`, `600`, DirectDraw calls, DirectInput calls, and writes to known
  viewport globals.
- Add an export for function call graph edges around render/menu/input
  functions.
- Add a CSV with `virtual_address`, `rva`, `section`, and `file_offset` for
  patch candidates.
- Add a targeted decompile script that accepts function names or addresses so
  agents can refresh only the functions currently under investigation.

## Clash95 Frame Dumping And Click Tests

Use `test_clash_menu_click.ps1` as the main visual regression harness. It starts
the target executable, optionally copies it into `C:\Clash`, kills old
`clash95*`/`cdb` processes by default, skips the intro animation, captures
before/after PNG frames, attempts a menu click, writes `results.json` and
`results.csv`, and kills the new instance when done.

Typical HD menu check:

```powershell
.\test_clash_menu_click.ps1 `
  -Exe .\clash95_hdmap12_novswitch_relinput.exe `
  -WorkDir 'C:\Clash' `
  -Click centered-exit `
  -MenuWaitSec 6 `
  -SurfaceWidth 800 `
  -SurfaceHeight 600 `
  -ClickMode SendInput
```

Multi-executable comparison:

```powershell
.\test_clash_menu_click.ps1 `
  -Exe .\clash95_hdmenu_centered_safe_absinput.exe,.\clash95_hdmap12_novswitch_relinput.exe `
  -Click native-exit,centered-exit `
  -SurfaceWidth 800 `
  -SurfaceHeight 600
```

Frame dump outputs are written under `captures/clicktest-YYYYMMDD-HHMMSS/`.
Inspect:

- `before.png` for final menu placement after intro skipping.
- `after.png` for click result when the process remains alive.
- `results.csv` or `results.json` for `ClientWidth`, `ClientHeight`,
  `RenderX`, `RenderY`, `RenderScale`, capture dimensions, hashes,
  `PreClickStable`, `PreClickReady`, `ClickAttempted`, `ChangedPercent`,
  `ExitedAfterClick`, `Passed`, and `Error`.
- `geometry.json` from `tools/capture_geometry.py` for exact nonblack bounds,
  changed bounds, click-target probes, full-frame warnings, and before-frame
  hash reuse.

Harness window handles:

- `MainWindowHandle` can temporarily refresh to null/zero for Clash95 wrapper
  runs even when a visible top-level game window still exists.
- `test_clash_menu_click.ps1` must reacquire the window by enumerating visible
  windows for the target process id before calling `GetClientRect`,
  `ClientToScreen`, `MoveWindow`, or `PostMessage`.
- Treat a null-handle error as a harness failure first; rerun after handle
  reacquisition before drawing conclusions about the game patch.

Use `-CaptureFullClient` when debugging letterboxing, window sizing, or scaling.
Without it, the harness captures the logical rendered surface derived from
`-SurfaceWidth` and `-SurfaceHeight`.

Use `capture_clash_window.ps1` for a one-off screenshot of an already visible
game window:

```powershell
.\capture_clash_window.ps1 `
  -ProcessName clash95_hdmap12_novswitch_relinput `
  -Output 'C:\Clash\clash-window.png' `
  -WaitSec 2
```

Progress reports for the Clash95 HD work should include at least one screenshot
when a capture, surface dump, or visual-smoke artifact exists. Prefer a fresh
surface-dump PNG or game frame, and use an absolute path in Markdown so the
Codex desktop app can render it.

Frame dumping limitations:

- The first visible state may be the startup animation, not the menu. Keep the
  skip-click/skip-key pulses enabled unless intentionally testing the intro.
- `run_clash_visual_smoke.ps1` supports `-MoveMode setcursor|sendinput-absolute|auto|none`,
  `-ClickMode sendinput|postmessage|both`, and `-PostIntroWaitSec`. Prefer
  `-MoveMode auto -ClickMode sendinput` for real cursor/input smoke. If the
  Codex desktop runner gets `[WinError 5]` from `SetCursorPos`, `SendInput`, or
  `GetCursorPos`, use `-MoveMode none -ClickMode postmessage` only as a
  fallback liveness/menu-flow check; it is not DirectInput proof and may not
  enter gameplay.
- `scripts/capture/capture_clash_client_frame.ps1` may report
  `CaptureMode=windowdc-contaminated-fallback` when another top-level window
  covers the target center. Treat that as weaker visual evidence than
  `CaptureMode=screen`; inspect the PNG and nonblack bounds before drawing
  conclusions.
- **Always check a visible-runtime capture for tearing before treating it as
  evidence.** `capture_clash_client_frame.ps1` grabs the desktop front buffer
  with `Graphics.CopyFromScreen`, which lands mid page-flip on the
  dgVoodoo-wrapped surface. On animated screens (castle courtyard, battle) the
  moving region shears into horizontal displacement bands while static chrome
  stays crisp; the render itself is correct (the hidden CDB surfdump of the same
  screen is coherent), so tearing is a capture artifact, not an HD defect. Run
  `python tools/capture_tear_check.py <frame.png> [--rect L T R B]` to flag it
  (row-vs-column mean-diff ratio; torn castle grab ≈ 2.05 vs clean CDB dump ≈
  1.37). For a clean frame, take 2–3 back-to-back grabs and pass them all — a
  consecutive pixel-identical pair (`clean_stable_pair`) is the strongest
  tear-free signal. Prefer the hidden CDB surface dump for geometry evidence; it
  never tears. Note `tools/castle_overview_gate.py` gates only VERTICAL stripe
  metrics and will pass a horizontally torn frame — use `capture_tear_check.py`
  for horizontal tearing.
- `SendInput` or `PostMessage` failures can be artifacts of how the game reads
  input. Treat them as automation results, then confirm real input issues with
  manual testing or CDB/memory probes.
- Use `tools/mouse_path_probe.py` when the question is whether automation is
  moving or clicking at the intended Win32 coordinates. It records requested
  client/screen points, actual `GetCursorPos`, actual `ScreenToClient`, and
  optional click down/up phases.
- Use a `SCROLL_VISDUMP` CDB row plus `db` memory dump when a far-edge HD map
  capture is mostly black and breakpoint-based per-tile visibility probes do
  not fire. `tools/visibility_coverage.py` can expand that dump into per-cell
  observations using `vis_base + player*1423 + map_x*13 + (map_y >> 3)`.
  Treat `visibility_zero` rows as fog/unexplored-state evidence, not as tile
  draw failure.
- Use `scripts/cdb/run_cdb_python_mouse_map.ps1` when the question is whether those exact
  Python-forced clicks line up with the engine's `MOUSE`/`MENUHIT` rows. Held
  clicks are better evidence than instantaneous down/up pairs because the game
  can miss a click between DirectInput polling frames.
- Common HD/windowed mouse bug procedure: if the cursor snaps to a corner/edge
  or clicks work while movement is wrong, run `scripts/cdb/run_cdb_python_mouse_map.ps1`
  with `-ClickHoldMs 250 -ClickRepeat 2` and compare Python
  `actual_screen`/`actual_client` with CDB `MOUSE dx/dy` and logical `x/y`.
  A typical wrapper failure is `DirectInputSample ~= screen / 4` instead of
  client coordinates. Confirm the live game HWND at `0x005452DC` with
  `probes/cdb/mouse/clash95_hwnd_origin_probe.cdb`, then use or refine the
  `gameplay-menu640-centered-map12-dynorigin` stage. A good mouse validation
  has exact Python path coordinates, `MOUSE` rows matching requested client
  points, `MENUHIT` button rows, and zero menu-hit out-of-bounds rows.
- For `sub_407B90` mouse-edge scroll probes, do not let debugger-forced mouse
  globals drift outside the currently safe cursor/redraw region. A repeatable
  proof should use a small safe drag gesture such as logical
  `(400,300)->(480,380)`, let the function apply its scroll delta, then reset
  `dword_544CFC`/`dword_544D00` to a safe center before `sub_418700` redraws.
  If the probe crashes in `Render_FillRect` or a copy helper after the forced
  mouse reaches the lower/right client edge, treat the probe as suspect before
  blaming the HD map patch.
- Common DirectInput bug procedure under the current CDB-only workflow: run
  `probes/cdb/mouse/clash95_directinput_probe.cdb` only through a host or hidden-desktop CDB
  harness. Compare exclusive and nonexclusive stages. `Acquire=0x80070005`
  means the mouse device was not enabled; a successful `Acquire` plus
  `button0=0x80` but `raw=(0,0,0)` means injected button state reached
  DirectInput but cursor placement did not generate relative movement. In that
  case, test a relative `SendInput` mover before changing engine mouse math. If
  the OS cursor verifies but the game cursor starts near `(1,1)`, try
  `tools/mouse_path_probe.py --move-mode sendinput-client-delta` as a
  calibration-only route. That mode emits relative deltas from logical client
  points instead of stopping when the Win32 cursor reaches a screen coordinate.
  Treat it as debugger evidence, not proof that manual mouse movement works.
- Key-scroll boundary proof procedure: do not write `gameData+140008` or
  `gameData+140012` when proving input-driven map clamps. First use
  `probes/cdb/key-scroll/clash95_key_scroll_probe.cdb` to prove `sub_407D20` accepts key-state rows
  for at least one real game scroll step. For boundary proof, use
  `probes/cdb/key-scroll/clash95_key_scroll_boundary_probe.cdb`, which repeatedly invokes the
  patched key-scroll helper under a CDB-only harness while keeping right/down
  key-state bytes active. Validate with
  `tools\key_scroll_summary.py --require-hd-boundary`. If the final lower-right
  screenshot is mostly black, sample visibility/fog before treating it as a
  rendering failure.
- Do not trust instant frame-click failure by itself. If the CDB/Python probe
  sees held button rows but `test_clash_menu_click.ps1` does not exit, treat it
  as either a harness cadence/target issue or a menu-flow issue until CDB proves
  the internal cursor and descriptor tested at the specific click point.
- Cursor position can change frame hashes. Prefer visible placement and
  geometry checks over hash equality alone.
- If a click-test case has a unique pre-click hash while sibling cases share a
  different hash, treat the pass/fail result as state-readiness evidence first.
  Add a menu/frame-stability gate before using it as hitbox proof.
- The harness should not perform result clicks until the pre-click frame is
  stable and menu-ready. `PreClickReady=false` or `ClickAttempted=false` means
  the run is harness/readiness evidence, not gameplay input evidence.
- Keep `captures/` results when they document an important regression or fix;
  otherwise summarize the important run in notes before pruning.

## Clash95 No-Popup CDB Surface Dumps

Use `scripts/cdb/run_cdb_surface_dump.ps1` when the goal is to test a no-popup capture path
without placing a Clash95 window on the active desktop.
The harness creates a timestamped `captures/archive/cdb-surface-dump-*/` folder, builds
a uniquely named candidate outside the repo, generates a per-run CDB script,
starts x86 CDB on a separate hidden Windows desktop with `CreateDesktop` /
`CreateProcessW`, and refuses visible-desktop fallback unless
`-AllowVisibleDesktop` is passed.

Preferred no-popup map-surface command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts/cdb/run_cdb_surface_dump.ps1 `
  -UseDdrawProxy `
  -NoSkipStartAnims `
  -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch `
  -CandidateDir C:\ClashTests\cdb-surface-dump `
  -RunSeconds 120
```

Use `-UseDdrawProxy` for hidden-desktop map dumps. It builds a process-local
32-bit fake DirectDraw `ddraw.dll` from `src/ddraw_surfdump_proxy/` into the
isolated candidate directory. The proxy owns simple dumpable 8-bit surface
memory and logs DirectDraw surface creation, palette attachment, locks, blits,
and flips to `C:\ClashTests\cdb-surface-dump\ddraw_surfdump_proxy.log`.
Never place this proxy in `C:\Clash`, `System32`, or `SysWOW64`.

Use `-NoSkipStartAnims` for normal visibility-classification runs. Full startup
is slower and can intermittently stall before menu routing, but it preserves
startup resource initialization. Use `-FastForwardStartAnims` for controlled
debugger-only visible-edge runs; the current implementation skips startup/AVI
sleep waits while still letting AVI/resource initialization execute. Do not
restore the older blunt `UI_StartAnims` or AVI-call skip route; that path can
leave render/resource state uninitialized and trigger the known `0x38`
memset-style AV at `00487cf4`.

If the probe reaches gameplay, it dumps `dword_5202E0` as raw 8-bit surface
memory, converts it with `tools\cdb_surface_dump_to_png.py`, runs
`tools\map_tile_coverage.py`, runs `tools\visibility_coverage.py` against the
same CDB log, and writes `summary.json` plus `RUN-SUMMARY.md`. The PNG uses a
grayscale index palette; treat it as tile/fog/blank evidence, not authentic
color evidence.

Normal no-popup runs now treat active blank cells as a validation question, not
an automatic failure. If `map_tile_coverage.py` reports active blank cells and
`-ForceVisibleEdges` is not enabled, the harness invokes
`tools\visibility_coverage.py --require-explained`. The run fails loudly when
any blank active cell lacks same-run visibility, fog, or clip evidence. A good
normal dark-corner result has `VisibilityRequireExplained=True`,
`VisibilityExplainedGate.Passed=True`, and `VisibilityUnexplainedBlankCells=[]`.
Do not patch tile drawing for a dark cell until this gate says the blank is not
explained by fog/unexplored state.

For post-owner action captures, use
`probes/cdb/map/clash95_post_owner_tile_visibility_extra.cdb` through the hidden-desktop
surface-dump harness when the right/bottom cells look like missing UI or tile
draw. It logs focused `APVIS_CELL` rows for the current seven blank cells and
emits a `SCROLL_VISDUMP` before the post-owner dump. A good fog/visibility
classification has `tools\visibility_coverage.py --require-explained` passing,
`status_counts.visibility_zero` covering the blank cells, and focused rows with
`hit=00` plus `sample=01`. Do not patch render loops, present bounds, or
action-box copyback for those cells while same-run visibility evidence says
they are unexplored/fogged.

Use `-PostOwnerForceVisibleSeven` only as a debugger proof switch with
`probes/cdb/map/clash95_post_owner_tile_visibility_extra.cdb`. The switch injects exact
visibility bytes for `r6c10`, `r6c11`, `r7c10`, `r7c11`, `r8c0`, `r8c10`, and
`r8c11` through the base PlayGame CDB breakpoint before the HD redraw; it must
not become a normal gameplay patch. Validate archived proof with:

```powershell
python tools\post_owner_forced_visible_summary.py `
  captures\archive\cdb-surface-dump-20260506-200426\map-tile-coverage.json `
  --log captures\archive\cdb-surface-dump-20260506-200426\cdb-surface-dump.log `
  --require-post-owner-forced-visible
```

Current post-owner forced-visible evidence:
`captures\archive\cdb-surface-dump-20260506-201114\RUN-SUMMARY.md` passed with no
visible desktop window, `PostOwnerForceVisibleSeven=True`, `blank_active_cells`
empty, and the harness-reported `Post-owner forced-visible gate: passed`. The
focused rows show nonzero hits for all seven cells, for example `r8c11` has
`hit=02` and `center_sample=c0`. This proves the same HD map path fills those
cells when save visibility permits them.

Use `tools\post_owner_evidence_matrix.py --require-pass` as the compact
post-owner dark-cell gate. It pairs the latest normal visibility-zero proof
with the latest seven-cell forced-visible proof and prints both screenshot
paths. The current passing report is
`captures\current\post-owner-evidence-current.md`, pairing
`captures\archive\cdb-surface-dump-20260506-190037` with
`captures\archive\cdb-surface-dump-20260506-201114`.

Use `tools\hd_map_smoke_matrix.py --require-pass` as the current repo-only HD
map smoke gate. It combines `tools\patch_stage_report.py
--require-current-hd-map` for the candidate recorded by the evidence captures
with `tools\post_owner_evidence_matrix.py --require-pass`. Current passing
outputs are `captures\current\hd-map-smoke-current.json` and
`captures\current\hd-map-smoke-current.md`. This command does not launch CDB or the
game.

Fresh-base reproduction for that gate is documented in `README.md` under
`Clash95 HD Map Smoke Reproduction`. The required sequence is: verify
`C:\Clash\clash95.exe` against SHA-256
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`, build a
unique candidate under `C:\ClashTests\hd-map-smoke`, run
`tools\patch_stage_report.py --require-current-hd-map --write-json
captures\current\patch-stage-current-hd-map.json` to create the old/new byte manifest,
then run `tools\hd_map_smoke_matrix.py --patch-exe <candidate> --normal-run
captures\archive\cdb-surface-dump-20260506-190037 --forced-run
captures\archive\cdb-surface-dump-20260506-201114 --require-pass`. Do not commit the
generated candidate executable.
Use `scripts/smoke/prepare_hd_map_smoke_candidate.ps1` as the dry-run launcher for this path.
Default mode only prints the plan, verifies the base SHA when accessible, and
refuses candidate output inside the repository. Use `-Execute` only from a
normal Windows shell when writing to `C:\ClashTests\hd-map-smoke` is allowed.
Use `tools\patch_manifest_compare.py` to compare two
`tools\patch_stage_report.py --write-json` outputs. It is repo-only and
highlights changed offsets, groups, expected old/new bytes, actual bytes,
status transitions, and any `original` / `unexpected` records. The current
example report is `captures\current\patch-manifest-compare-current-vs-partial12.md`.
Use `captures\current\hd-map-evidence-current.md` as the compact front page for current
HD map evidence. It links the smoke matrix, post-owner evidence matrix,
patch-manifest comparison, and current screenshot artifacts.
Use `tools\evidence_index_check.py captures\current\hd-map-evidence-current.md
--require-pass` after editing that index. It verifies local Markdown links and
referenced screenshot artifacts without launching CDB or reading executables.

Current successful evidence:
`captures\archive\cdb-surface-dump-20260429-111340\RUN-SUMMARY.md` reports a hidden
desktop DirectDraw-proxy run that dumped an 800x600 `dword_5202E0` surface with
host-side `ReadProcessMemory` and reconstructed `surface.png`. The CDB log
shows `SURFDUMP_PLAYGAME`, `SURFDUMP_READY`, `SCROLL_VISDUMP`, and
`SURFDUMP_HOST_READY`; `map_tile_coverage.py` reports
`gameplay_frame_likely=True`, `active=108`, `measurable=99`, and `blank=13`.
`visibility_coverage.py` reports `observation_points=108`, all 13 blank cells
explained, `unexplained_blank_cells=[]`, and
`status_counts.visibility_zero=13`. Direct validation with
`--require-explained` exits successfully for this run; the same command exits 2
if the log lacks visibility evidence. The reconstructed PNG is a required
screenshot artifact for no-popup progress reports.

Fresh normal-gate evidence:
`captures\archive\cdb-surface-dump-20260429-140916\RUN-SUMMARY.md` reran the normal
hidden-desktop route with `-UseDdrawProxy -NoSkipStartAnims -RequireGameplay`.
It passed with `VisibilityRequireExplained=True`,
`VisibilityExplainedGate.Passed=True`, 13 active blank cells, zero unexplained
blank cells, and `status_counts.visibility_zero=13`. Use this as the current
normal no-popup dark-corner baseline.

Use `tools\no_popup_map_evidence_matrix.py --require-pass` as the compact
no-popup HD map smoke gate. It selects the freshest normal
`VisibilityExplainedGate` pass and freshest forced-visible `ForcedVisibleGate`
pass, then prints both screenshot paths and key counts. The current matrix pairs
`captures\archive\cdb-surface-dump-20260429-140916` with
`captures\archive\cdb-surface-dump-20260429-135242` and passes.
Use `--write-markdown captures\current\no-popup-map-evidence-current.md` when a durable
human-readable report with embedded screenshot links is needed.

Use `probes/cdb/castle/clash95_castle_owner_setup_extra.cdb`,
`probes/cdb/castle/clash95_castle_screen_invoke_extra.cdb`, and
`tools\castle_owner_setup_summary.py` when investigating the missing
right-bottom castle/action owner UI. The full castle screen routine starts at
`00422180` and installs render hook `00422020`; `00422020` is the render hook,
not the full screen entry. The owner setup route is command `0x63` descriptor
setup at `00422709` -> callback `00433C20`, which writes `dword_532150`,
`dword_53214C`, and `dword_532154`; the later action route enters
`004338E0 -> 00433914 -> sub_435BC0`. A normal hidden-desktop load-slot run at
`captures\archive\cdb-surface-dump-20260506-121909` reached `SURFDUMP_READY` but did
not observe castle setup. A controlled hidden-desktop run at
`captures\archive\cdb-surface-dump-20260506-141239` used
`-FastForwardStartAnims -SkipMapValidation`, invoked castle index `0`, proved
command `0x63` installs `00433C20`, observed all three owner-global writes, and
dumped a 640x480 castle screen PNG. This proves the owner setup path is native
castle-screen state, not the normal 800x600 gameplay map route. Do not patch
the right-bottom draw/present constants until a CDB route proves whether the
`004338E0 -> 00433914 -> sub_435BC0` action path can draw on the HD gameplay
surface.

For centered castle/barracks UI input work, prefer the
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`
stage and validate with hidden-desktop CDB probes. The key coordinate proof is
displayed `(530,133)` over the top-left barracks grid cell, which must map to
native `(450,73)` while the owner-poll and `00435A17 -> 00435580` grid helper
wrappers run. Use `probes/cdb/castle/clash95_castle_barracks_click_extra.cdb` plus
`tools\castle_barracks_hitbox_summary.py` with `--require-ready`,
`--require-raw-gate`, `--forbid-forced-gate`, and `--require-grid-hit` when
proving the click path. This
probe may set the click-state byte at `00544D04`, but it must not rewrite
`eax` at `00435A0E`; the passing row is
`APBARRACKS_HITBOX_GRID_GATE raw_result=1 forced_result=none`.

For centered castle/barracks action-button probes, use
`probes/cdb/castle/clash95_castle_barracks_click_consume_trace_extra.cdb` or a successor probe
that does not perform descriptor-local click rearm. The shared
`probes/cdb/render/clash95_surface_dump_probe.cdb` `00419B80` post-gameplay cleanup is guarded
with `@$t18 == 0`; this prevents the base harness from clearing `005451C0` and
`00544D04` after an extra UI probe has entered its active phase. If a future
probe sees `click_flag=1` immediately after injection but `click_flag=0` at
descriptor `0051519a`, inspect the generated CDB script before blaming the game
or the centered-input patch. The current clean action-button proof is
`captures\archive\cdb-surface-dump-20260511-162846`, where `0051519a` reaches callback
`00435620` and sets `dword_532210=1` without descriptor-local rearm.
For a second bottom action-button proof, use
`probes/cdb/castle/clash95_castle_barracks_second_action_extra.cdb` with
`tools\castle_barracks_action_click_summary.py --expect-desc 0x005151cf
--expect-callback 0x004356c0`. Current evidence
`captures\archive\cdb-surface-dump-20260511-163846` proves centered `(276,501)` maps
to native `(196,441)`, stock gate returns `1`, and callback `004356c0` is
entered. That callback currently returns through its availability-failed path
for `selected_addon=0`; proving the success branch requires selecting a
compatible addon/unit first or choosing another descriptor.

For the broader castle-interior centering pass, use stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`.
It uses the proven `castlecenter-hitbox` input transforms, but its visual path
must use the clean present/redraw wrapper, not the older pre-present copy. Keep
`castlecenter-hitbox` as the regression reference for the older byte set.

Common castle/barracks centering bug: centering before a stock
present/render callback can leave duplicated or blurry native-origin UI when
the stock path draws the unit list/stat panel again. The fix is to call the
stock castle render callback first, then copy the freshly rendered native
640x480 frame into scratch, clear the full 800x600 target, and copy it back at
`(80,60)`. For the barracks route this currently means both the initial
`00435DAA` `Render_Present` callback pointer and the per-frame `00435DDE`
loop redraw call route through wrapper `0051316F`. Do not remove the loop hook
when fixing castle UI echo; the screenshot can look native-origin even if the
initial present callback is wrapped correctly.

Use `probes/cdb/castle/clash95_castle_interior_catalog_extra.cdb` with
`tools\castle_interior_catalog_summary.py` to enumerate castle-screen
descriptors reachable from the current save. Current full-overview evidence
`captures\archive\cdb-surface-dump-20260512-101803` found commands `0x63`, `0x86`,
`0x87`, `0x99`, `0x9C`, `0x9F`, and `0xA6` with no AV rows, logged
`CASTLECAT_OVERVIEW_POST_DRAW` on an 800x600 main surface, and passed
`tools\castle_overview_gate.py` with the barracks baseline
`captures\archive\cdb-surface-dump-20260512-082418`.

Current `castlecenter-all` full-overview visual patch is
`castle-overview-center-present-wrapper`: `0042232E` and `00422674` route the
two full-overview `00422020` redraw calls through cave `0051B6D0`. The cave
allocates/stores an 800x600 `dword_5202E0` if the route still owns a native
surface, calls stock `00422020`, then copies the native 640x480 overview layer
to scratch, clears the 800x600 target, and copies it back at `(80,60)`.
Do not re-add the experimental full-overview input wrapper without a dedicated
hitbox probe; the May 12 attempt caused the forced catalog route to AV before
dumping.

Use `tools\castle_ui_center_geometry.py --require-centered` on fresh
`surface.png` files when validating centered castle/barracks interiors. The
gate must fail native-origin echo: top/left margins outside the centered
`(80,60)-(719,539)` frame should be mostly blank, with default
`--max-echo-percent 5.0`.

Current `castlecenter-all` barracks no-echo evidence is
`captures\archive\cdb-surface-dump-20260512-082418`. It passed hidden-desktop CDB,
dumped an 800x600 surface, and passed
`centered_gate=PASS image=800x600 centered_nonblack=71.228%
max_margin_nonblack=0.0%`. The selected-index-1 action probe is intentionally
controlled at `004356C0` for this screenshot and should be checked with
`--require-4356c0-controlled-stop`; the older
`captures\archive\cdb-surface-dump-20260511-170759` remains the success-branch
reference, but it also demonstrates the native-origin echo that the stricter
geometry gate now rejects.

Use `tools\patch_stage_report.py --require-current-hd-map` before spending
runtime on a candidate that claims to be the current HD map stage. The gate
requires all selected bytes to be patched, no selected bytes to remain original
or unexpected, 12x9 map loops/helpers, 800x600 input and viewport setup, the
dynamic map-surface viewport switch, widened full-redraw present bounds, the
right-anchored minimap, and the post-menu map-surface scroll clamp. A good
current baseline is:

```powershell
& $PY tools\patch_stage_report.py `
  --exe C:\ClashTests\cdb-surface-dump\clash95_hd_surfdump_20260429_140916.exe `
  --stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch `
  --require-current-hd-map
```

Experimental visible-edge proof command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts/cdb/run_cdb_surface_dump.ps1 `
  -UseDdrawProxy `
  -FastForwardStartAnims `
  -ForceVisibleEdges `
  -RequireGameplay `
  -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch `
  -CandidateDir C:\ClashTests\cdb-surface-dump `
  -RunSeconds 120
```

`-ForceVisibleEdges` is debugger-only validation, not a gameplay patch. It
targets the current load-slot-0 viewport at `scroll=(10,17)` and temporarily
sets player-0 visibility bytes for the right/bottom cells that image coverage
usually flags. It also freezes the forced proof's scroll globals at `(10,17)`
during redraw so edge-scroll drift cannot move the dump to a different
viewport. A passing proof should have no target cells in
`CoverageBlankActiveCells`, no unexplained blank cells, `SURFDUMP_READY` at
`map0=(10,17)`, matching `SURFDUMP_VEDGE_VISRET` / `SURFDUMP_VEDGE_POST`
evidence, and a fresh screenshot artifact.

Current forced-visible evidence:
`captures\archive\cdb-surface-dump-20260429-135242\RUN-SUMMARY.md` passed on the hidden
desktop with `-FastForwardStartAnims -ForceVisibleEdges`. It dumped an 800x600
surface, `map_tile_coverage.py` reported `gameplay_frame_likely=True`,
`active=108`, `measurable=99`, `blank=0`, and
`tools\forced_visible_summary.py` required `map0=(10,17)`, 54
`SURFDUMP_VEDGE_VISRET` rows, 54 `SURFDUMP_VEDGE_POST` rows, 54 nonzero
visibility returns, and 54 nonblack post samples before the harness reported
success. This proves the HD 12x9 map path can draw bright right/bottom cells
when the save visibility permits them; do not turn this debugger-only
visibility forcing into a normal gameplay patch.

Use `tools\forced_visible_summary.py` directly to validate archived
forced-visible evidence:

```powershell
python tools\forced_visible_summary.py `
  captures\archive\cdb-surface-dump-20260429-135242\map-tile-coverage.json `
  --log captures\archive\cdb-surface-dump-20260429-135242\cdb-surface-dump.log `
  --require-forced-visible
```

Default dump method is host-side `ReadProcessMemory` after `SURFDUMP_READY`.
This avoids the older nested-CDB `.writemem` command-tail problem and lets the
harness stop the launched CDB/game promptly after a nonempty raw dump appears.
Use `-UseCdbWriteMem` only to debug the old CDB-only dump path. CDB filename
rule for that legacy path: when `.writemem` is generated inside a breakpoint
command, use an unquoted forward-slash path such as `C:/.../surface.raw`.
Backslash paths are consumed by CDB's nested command parser, and quoted paths
can write the raw file but leave a syntax tail that prevents `q` from exiting
cleanly.

Evidence-file portability: archived `cdb-surface-dump.log` files are tracked in
git (see the `.gitignore` evidence exceptions), but the castle `.raw` dumps stay
local-only because the packaging boundary excludes memory dumps. After a
workspace move, regenerate them with hidden-desktop runs before the refresh:

- `captures/current/castle-owner-records-current.raw`: run the
  `castlecenter-all` stage with
  `probes/cdb/castle/clash95_castle_owner_records_dump_extra.cdb`, then copy
  `C:\Clash\castle-owner-records-current.raw` into `captures/current/`.
- `captures/archive/castle-overview-hitmap-flags1f.raw` (and the
  `hitmap-current` / `hitmap-index1` variants): run the matching
  `clash95_castle_overview_hitmap_*_extra.cdb` probe, then copy the raw file
  the probe writes into `C:\Clash` (CDB working directory) into the recorded
  `captures/` location.

## Clash95 Windows Sandbox UI Testing

Use `run_clash_windows_sandbox.ps1` when the game window should not disrupt the
host desktop. This implements the preferred disposable UI test route:

- It generates a run folder under `captures/sandbox-YYYYMMDD-HHMMSS/`.
- It maps the repository into the sandbox as `C:\Repo` with write access so
  logs, screenshots, and JSON results can return to the host.
- It maps the user-owned `C:\Clash` install into the sandbox as
  `C:\HostClash` read-only.
- It copies those game files only into the disposable sandbox-local
  `C:\Clash` working directory, skipping obvious `crack.exe` / `keygen.exe`
  names. Do not copy game files into the repo.
- It maps the bundled Python runtime directory read-only as `C:\HostPython`.
- Inside the sandbox it builds a patched candidate from the read-only original,
  runs `run_clash_visual_smoke.ps1`, and then runs
  `tools\map_tile_coverage.py` against `after-map-path.png` when that frame
  exists.

Dry-run/config generation:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_clash_windows_sandbox.ps1 -NoLaunch
```

Launch a sandbox run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_clash_windows_sandbox.ps1
```

If `WindowsSandbox.exe` is missing, enable the Windows feature
`Containers-DisposableClientVM` from an elevated shell, reboot, then rerun the
script. Use hidden-desktop testing only through `scripts/cdb/run_cdb_surface_dump.ps1` and
treat a hidden-desktop DirectDraw failure as evidence, not as a reason to fall
back to a visible host-window run.

After every completed task, show the user a current UI screenshot artifact in
the progress or final report. Prefer a fresh CDB surface-dump PNG or
visual-smoke frame from the current run; if the task was docs-only or no fresh
frame was produced, reuse the latest relevant UI capture and say why it is
being reused.
Close incidental desktop popups such as OneDrive before relying on visual
coverage or screenshots. They do not invalidate CDB coordinate evidence, but
they can contaminate captured frames and confuse image-based coverage checks.

## Clash95 HD Mod Development Aids

Future work should favor small, repeatable probes over long manual debugging
sessions. Add helper scripts when a question will recur more than once.

High-value debugger probes:

- DirectDraw lifecycle probe: log calls around display mode setup, primary/back
  surface creation, blits, flips, pitch, width, height, and surface pointers.
  This helps separate "window/client size is right" from "render surface or blit
  rectangle is still native 640x480".
- DirectInput and Win32 mouse probe: log raw cursor coordinates, translated game
  coordinates, clip bounds, button state, and any writes to mouse globals. Use
  this when the cursor snaps to the upper-left corner or clicks work while
  movement feels wrong.
- Viewport global write probe: use CDB hardware breakpoints such as `ba w4` on
  suspected viewport width, height, scroll, origin, and clamp variables once
  their addresses are known. Record the writer address, register state, and
  nearby disassembly.
- Crash triage probe: run CDB with first-chance access violation handling, then
  dump `.ecxr`, `r`, `kv`, `ub eip`, `u eip`, and any relevant surface/viewport
  globals. Save the log next to the frame dump that triggered the crash.
- Patch-offset verifier: before launching a patched executable, assert the
  expected original bytes or patched bytes at every known offset. Refuse to run
  when the file hash or byte pattern does not match the patch script's expected
  baseline.
- CDB log parser: convert repeated `.printf` debugger output into CSV/JSON so
  coordinate, surface, and crash probes can be compared across executables.

High-value frame dumping improvements:

- Golden baseline set: keep one native 640x480 menu frame and one last-known-good
  HD menu/gameplay frame. Compare new runs against both, using masks for the
  cursor and animated regions.
- Geometry analyzer: write a small script that reads `before.png` and reports
  black-bar bounds, rendered-surface bounds, menu panel bounds, and approximate
  button centers. This would catch "menu is correct but shifted down/right"
  without relying on eyeballing screenshots.
- Full-client plus logical-surface captures: run important tests once with the
  default logical HD surface capture and once with `-CaptureFullClient`. The pair
  reveals whether a bug is in engine rendering, window scaling, or letterboxing.
- Frame manifest: store executable name, SHA256, patch group names, command
  line, client size, render size, skip settings, click mode, and timestamp beside
  every capture directory.
- Visual diff summaries: create a small diff image or crop sheet for before vs
  after frames, focused on menu buttons, right map edge, bottom map edge, and
  cursor region.
- Gameplay tile-count frames: capture deterministic map/gameplay views and count
  visible tile rows/columns or tile-center markers. Use this to prove the HD mod
  draws additional map tiles rather than only enlarging the window.

High-value automated tests:

- Smoke test matrix: maintain a simple JSON or CSV list of patched executables,
  expected client size, expected logical surface size, click points, and expected
  outcome. Have `test_clash_menu_click.ps1` or a wrapper run the matrix.
- Startup/menu test: launch, kill stale instances, skip intro, capture menu, and
  assert no crash, expected client size, expected render bounds, and centered menu
  geometry.
- Input sanity test: after the menu is visible, move/click a few known points and
  check CDB/memory logs for plausible translated coordinates. Do not rely only on
  `SendInput` exit-click success.
- Map viewport test: enter or load a deterministic game state, capture a gameplay
  frame, and validate that right/bottom edge tiles are drawn and selectable.
- Right-bottom gameplay UI test: use
  `tools\right_bottom_ui_bounds.py` on screenshots such as
  `captures\map-minimapaction-minimapright-dynvswitch-v2-frame-20260424.png`
  to measure the minimap, right-side panel, bottom strip, and bottom-right
  12x9 cells. Use `probes/cdb/ui/clash95_right_bottom_ui_probe.cdb` only through a CDB-only
  launcher or hidden-desktop harness when changing action-panel or bottom-right
  UI constants; it late-arms `UI_DrawActionBox`, `UI_GetGridIndexFromMouse`,
  action-panel draw functions, `sub_460D80`, and `Render_BlitSurface` after
  gameplay routing. Do not visually move the action grid without moving and
  proving `UI_GetGridIndexFromMouse` hitboxes too.
- Scroll/clamp test: drive scrolling toward every map edge and confirm the camera
  clamps cleanly without old 640x480 limits, wrapped coordinates, or blank
  regions.
- CDB-only scroll matrix: use a host/hidden-desktop harness that route-injects
  load slot 0, writes debugger-only scroll targets, captures one frame or
  surface dump per target, and runs `tools\visibility_coverage.py` so fog is
  not mistaken for an HD render gap. Boundary evidence proves debugger-forced
  12x9 draw/clamp math; it does not prove real keyboard or mouse scrolling
  reaches those limits.
- Center-on-unit test: trigger any function that recenters the camera on a unit
  and verify the viewport math uses the HD dimensions.
- Regression gate: for each patch group, run the patch verifier, menu smoke
  test, frame dump comparison, CDB crash probe, and a short manual mouse check
  before calling the patch stable.

Development notes for future agents:

- Keep patch groups separable. A small patch that only changes surface/display
  dimensions is easier to debug than a combined surface, menu, input, and map
  patch.
- Do not key menu-centering logic only on `eax == dword_5202E0`. The HD map
  path can swap `dword_5202E0` from the native 640x480 menu surface to an
  800x600 gameplay surface after menu dispatch. Menu blit guards must also
  check that the surface is still 640 pixels wide before applying the 80,60
  centering offset.
- Record original bytes, patched bytes, addresses, and rationale in
  `docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md` whenever a patch changes.
- When a test fails, preserve the exact executable, frame directory, CDB log, and
  command used. The failure artifact is often more valuable than another manual
  run.
- Prefer adding deterministic helpers to the repo over depending on chat memory.
  Useful candidates are `tools/verify_patch_bytes.py`,
  `tools/analyze_capture_geometry.py`, `tools/compare_frame_sets.py`, and
  `tools/parse_cdb_probe_log.py`.

## Safety Rules For Raw Sources

- Never modify, rewrite, normalize, OCR, rename, delete, or move files under
  `raw/` unless the user explicitly asks.
- Moving a file from `raw/inbox/` to `raw/processed/` requires explicit user
  approval for that specific file or batch.
- If a raw source appears corrupt, duplicated, or misnamed, document the issue in
  `wiki/questions/` or `wiki/log.md`; do not fix the raw file silently.
- Derived pages in `wiki/` may quote only small excerpts as needed and should
  prefer paraphrase plus precise citations.

## Markdown Conventions

- Prefer plain markdown that reads well in Obsidian and any text editor.
- Every page under `wiki/` must have YAML frontmatter.
- Prefer Obsidian wikilinks for internal links: `[[Page Name]]`.
- Use descriptive Title Case page headings.
- Use kebab-case filenames for source pages and new wiki pages.
- Keep sections skimmable: short paragraphs, compact lists, and explicit status
  labels.
- Avoid creating empty pages unless they are required index/log/overview files or
  user-requested placeholders.
- Do not fabricate facts, source titles, people, organizations, or citations.

## Source Citation Rules

Every factual claim derived from a source needs a citation.

Acceptable citation forms:

- Raw source path: `[source: raw/inbox/file-name.ext]`
- Source summary page: `[source page: [[Source Title]]]`
- Combined citation for important claims:
  `[source: raw/processed/file-name.ext; source page: [[Source Title]]]`

Citation expectations:

- Cite claims at the bullet or paragraph level.
- Page-level `source_path:` frontmatter is useful but not enough for new claims.
- Synthesis pages must distinguish sourced facts from interpretation.
- If a claim is inferred from multiple pages, cite all relevant source pages.
- If no source supports a statement, label it as interpretation, uncertainty, or
  an open question.

## Ingest Workflow

Use this flow when the user asks to ingest one or more files from `raw/inbox/`.

1. Identify the exact raw source path(s).
2. Read the source material without modifying it.
3. Create or update one page in `wiki/sources/` per source using
   `meta/templates/source-summary.md`.
4. Extract durable entities into `wiki/entities/` and concepts into
   `wiki/concepts/` when they are likely to recur.
5. Update or create synthesis, question, and comparison pages only when the
   source supports them.
6. Add backlinks between related pages using wikilinks.
7. Record contradictions instead of overwriting conflicting claims.
8. Append an entry to `wiki/log.md`.
9. Run `python tools/wiki_lint.py`.
10. Ask before moving source files from `raw/inbox/` to `raw/processed/`.

## Wiki Check Workflow

Use this flow when the user asks to check the wiki, inspect the knowledge base,
or verify wiki health/discoverability.

1. Start from `wiki/index.md` and `wiki/log.md` to understand the current
   catalog and recent maintenance.
2. Check whether `raw/inbox/` has new user-owned sources waiting for ingest, but
   do not edit, move, or normalize anything under `raw/`.
3. Search for the user's topic with `python tools/wiki_search.py "<query>"`.
   For broad health checks, also use `rg` over `wiki/` for likely terms,
   stale placeholders, `TODO`, `TBD`, `Open question`, `Contradiction`, and
   uncited-looking claims.
4. Read the most relevant source summaries, concept pages, syntheses, question
   pages, and cited source paths before drawing conclusions.
5. Run `python tools/wiki_lint.py` and fix errors if the task includes wiki
   maintenance. Review warnings and either fix them or explicitly note why they
   are acceptable.
6. If `python` is not on `PATH`, use the bundled Codex runtime when available:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\wiki_lint.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\wiki_search.py "<query>"
```

7. For read-only checks, report gaps and suggested updates without editing.
   For maintenance requests, update the appropriate wiki pages, `wiki/index.md`,
   and `wiki/log.md`, then rerun the linter.

## Query Workflow

Use this flow when the user asks a question against the wiki.

1. Search the wiki with `python tools/wiki_search.py "<query>"`.
2. Read the most relevant wiki pages and their cited source summaries.
3. If the answer depends on raw sources, inspect the cited raw files as needed.
4. Answer from the wiki first, with citations to source pages or raw paths.
5. Separate sourced facts, interpretation, uncertainty, contradictions, and open
   questions when the answer is not straightforward.
6. If the query reveals a durable insight or gap, update the appropriate wiki
   page and append to `wiki/log.md`.

## Lint Workflow

Run:

```powershell
python tools/wiki_lint.py
```

Fix errors before considering maintenance work done. Warnings should be reviewed
and either fixed or consciously left in place when they are conservative false
positives.

The linter checks:

- Missing `wiki/index.md` or `wiki/log.md`
- Empty required files
- Missing YAML frontmatter in `wiki/**/*.md`
- Broken Obsidian wikilinks
- Possible orphan pages
- Raw file paths mentioned without citation syntax

## Contradiction Handling

Never silently replace an older claim with a conflicting newer claim.

When sources disagree:

1. Keep the older claim with its citation.
2. Add the newer conflicting claim with its citation.
3. Add a `Contradictions` section or update the existing one.
4. State exactly what conflicts and which source says what.
5. Add or update a page in `wiki/questions/` if resolution requires more work.
6. Link affected pages to the contradiction note.
7. Append the contradiction to `wiki/log.md`.

Use labels:

- `Sourced fact`
- `Interpretation`
- `Uncertainty`
- `Contradiction`
- `Open question`

## Logging Format

`wiki/log.md` is append-only. Add newest entries near the top unless the user
chooses another convention.

Use:

```markdown
## [YYYY-MM-DD] ingest | Source Title
- Source: raw/path
- Pages created:
- Pages updated:
- Contradictions:
- Open questions:
```

For non-ingest maintenance:

```markdown
## [YYYY-MM-DD] maintenance | Short Title
- Trigger:
- Pages created:
- Pages updated:
- Checks run:
- Notes:
```

## Page Templates

Use templates from `meta/templates/`:

- `source-summary.md`
- `entity.md`
- `concept.md`
- `synthesis.md`
- `question.md`
- `comparison.md`

Templates are conventions, not cages. Preserve required frontmatter and source
citation sections, but adapt section detail to the source.

## Naming Rules

- Source summary filename: kebab-case source title, for example
  `wiki/sources/source-title.md`.
- Entity filename: kebab-case canonical name, for example
  `wiki/entities/jane-doe.md`.
- Concept filename: kebab-case concept name.
- Synthesis filename: kebab-case thesis or topic.
- Question filename: kebab-case short question.
- Comparison filename: `a-vs-b.md` or a clear descriptive comparison name.
- H1 heading: human-friendly Title Case.
- Wikilink text should usually match the target page H1.

## Done Criteria

An agent maintenance task is done when:

- Raw sources were not mutated.
- Relevant wiki pages were created or updated.
- Claims include citations or are labeled as interpretation/uncertainty.
- Contradictions and open questions are recorded.
- `wiki/log.md` has an entry when durable wiki state changed.
- `wiki/index.md` links important new pages.
- `python tools/wiki_lint.py` passes without errors.
- The final response summarizes changed pages and any residual uncertainty.

## Updating This File

When the workflow evolves, update `AGENTS.md` in the same change as the workflow
or tool update. Future agents should not have to reconstruct project rules from
chat history.

# LLM Wiki Agent Operating Schema

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
  Windows game patching work. Keep patched executables uniquely named
  `clash95_*.exe`; do not overwrite the original `C:\Clash\clash95.exe` unless
  the user explicitly asks.
- Keep only one freshest `.exe` artifact in the repository. Do not accumulate
  old patched executables, experiment builds, or copied game binaries in git;
  document the useful result in notes, keep the newest handoff executable, and
  remove stale `.exe` files before committing. Temporary test executables may
  live in `C:\Clash` while debugging.

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
.\run_cdb_menu_probe.ps1 `
  -Exe 'C:\Clash\clash95_hdmap12_novswitch_relinput.exe' `
  -Probe .\clash95_hd_crash_probe.cdb `
  -Log 'C:\Clash\hd-cdb-menu.log' `
  -RunSeconds 10
```

```powershell
.\run_cdb_mouse_probe.ps1 `
  -Exe 'C:\Clash\clash95_hdcentered_hitboxes.exe' `
  -Log 'C:\Clash\hd-cdb-mouse-probe.log' `
  -NoWait
```

```powershell
.\run_clash_test.ps1 `
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
  bytes, and rationale in `CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md`.
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
  `ChangedPercent`, `ExitedAfterClick`, `Passed`, and `Error`.

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

Frame dumping limitations:

- The first visible state may be the startup animation, not the menu. Keep the
  skip-click/skip-key pulses enabled unless intentionally testing the intro.
- `SendInput` or `PostMessage` failures can be artifacts of how the game reads
  input. Treat them as automation results, then confirm real input issues with
  manual testing or CDB/memory probes.
- Cursor position can change frame hashes. Prefer visible placement and
  geometry checks over hash equality alone.
- Keep `captures/` results when they document an important regression or fix;
  otherwise summarize the important run in notes before pruning.

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
- Scroll/clamp test: drive scrolling toward every map edge and confirm the camera
  clamps cleanly without old 640x480 limits, wrapped coordinates, or blank
  regions.
- Center-on-unit test: trigger any function that recenters the camera on a unit
  and verify the viewport math uses the HD dimensions.
- Regression gate: for each patch group, run the patch verifier, menu smoke
  test, frame dump comparison, CDB crash probe, and a short manual mouse check
  before calling the patch stable.

Development notes for future agents:

- Keep patch groups separable. A small patch that only changes surface/display
  dimensions is easier to debug than a combined surface, menu, input, and map
  patch.
- Record original bytes, patched bytes, addresses, and rationale in
  `CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md` whenever a patch changes.
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

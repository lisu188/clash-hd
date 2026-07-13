# Clash95 HD Agent Guide

Read `docs/hd/WORKING_WITH_THIS_REPO.md` before changing the repository. This
file defines the project-specific operating rules for automated contributors.

## Project purpose

`clash-hd` is a reverse-engineering and binary-patching project for the 32-bit
Windows game `clash95.exe`. The goal is to support larger render resolutions,
expanded gameplay viewports, correctly anchored UI, reliable input transforms,
and reproducible evidence without distributing proprietary game material.

## Repository boundaries

- Track source code, scripts, documentation, tests, patch metadata, and small
  evidence manifests.
- Do not commit original or patched executables, wrapper DLL binaries, saves,
  copied game assets, CD/ISO contents, cracks, memory dumps, or large raw
  captures.
- Never modify `C:\Clash\clash95.exe` in place.
- Build and test candidates under `C:\ClashTests\...` or as distinctly named
  local copies under `C:\Clash`.
- Keep generated launcher builds outside the repository.
- Store debugger dumps and temporary runtime artifacts outside the repository
  unless a small, reviewable evidence file is explicitly intended for source
  control.

## Protected stable stage

The default stable stage is:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch
```

New patch work must use a validation-stage suffix. Do not add experimental
bytes to the stable stage or change the default stage silently. Promotion
requires suitable repo-only checks, hidden-CDB evidence, approved visible
runtime evidence where required, and an explicit promotion decision.

## Patch integrity

Every binary patch must:

1. Verify the expected input executable SHA-256.
2. Verify the old bytes before writing.
3. Record file offset and VA/RVA.
4. Record old bytes and new bytes.
5. Identify the patch group and stage.
6. Explain the rationale and expected behavior.
7. Produce a candidate outside the repository.
8. Fail closed when the executable or old bytes do not match.

Do not weaken byte checks to accommodate an unknown executable.

## Evidence integrity

- An honest failing gate is better than a fabricated pass.
- Do not change a test or parser merely to hide a real defect.
- Do not point a guard at unrelated evidence.
- Do not manufacture approval records, runtime observations, screenshots, or
  success markers.
- Treat route evidence, draw evidence, visual evidence, input evidence, and
  promotion evidence as separate claims.
- A nonblack frame alone is not proof of correct rendering.
- Record exact candidate SHA, stage, resolution, launch mode, wrapper, input
  method, and observed markers.
- Keep validation-only results out of the stable-stage claim.

## Approval boundary

Visible/manual runtime, cursor control, foreground-window manipulation,
`SendInput`, `PostMessage`, and live screen capture require fresh explicit user
approval unless the command is a documented user-initiated launcher path.

Do not set `approved: true`, populate `approval_record`, or convert a template
into proof without real approval and matching evidence.

The launcher is a user-facing exception:

- `src/launcher/`
- `scripts/launcher/run_launcher.ps1`
- `docs/hd/LAUNCHER.md`

The launcher may start the game only after an explicit GUI Play action or the
CLI `--launch --yes-launch` combination. Its dry-run path is safe for automated
repo-only use. It must never overwrite the original executable or download or
ship game binaries.

## Toolchain and environment

Clash95 is a 32-bit Windows target. Prefer x86 tooling.

Common locations:

- CDB x86: `%ProgramFiles(x86)%\Windows Kits\10\Debuggers\x86\cdb.exe`
- WinDbg: `windbgx.exe` or Windows Kits WinDbg
- x32dbg: use `x32dbg.exe`, not the 64-bit debugger
- Sysinternals tools: commonly under `C:\Tools\Sysinternals`
- User-owned game install: `C:\Clash`
- Isolated candidates: `C:\ClashTests\...`
- Dumps: `C:\ClashDumps`
- Temporary captures: `C:\ClashCaptures`

Environment constraints:

- `NoDefaultCurrentDirectoryInExePath=1` may prevent bare command names from
  resolving from the current directory. Use explicit paths.
- PowerShell reserves `$pid`; use `$procId` or another name.
- Under the GOG/dgVoodoo wrapper, `Process.MainWindowHandle` may remain null.
  Find the process window with `EnumWindows`.
- Sandbox restrictions can block debugger and child-process chains. Do not
  interpret sandbox failures as game behavior.

## Debugging workflow

Use this default loop:

1. Generate a uniquely named candidate from the known-good executable.
2. Place it in an isolated test directory with the required local wrapper and
   configuration.
3. Kill stale candidate/debugger processes before the run unless attachment is
   the explicit purpose.
4. Run repo-only and byte-gate checks first.
5. Use hidden CDB for repeatable route, crash, and software-surface evidence.
6. Use visible runtime only with approval and only for claims that hidden CDB
   cannot prove.
7. Stop processes started by the task.
8. Record results without changing the stable stage unless promotion criteria
   are satisfied.

CDB guidance:

- Use x86 CDB.
- Avoid semicolons inside `.echo` text in command files.
- Late-arm hot render breakpoints after reaching the target route.
- On crashes, record exception code, EIP, stack, modules, candidate SHA, stage,
  and wrapper state.
- Treat timeout exit 124 as acceptable only for an intentional liveness test.

## Capture interpretation

Two capture paths have different properties:

### Hidden CDB software-surface dump

`scripts/cdb/run_cdb_surface_dump.ps1` captures the software surface used by the
hidden validation path. It can omit separately composed minimap, tooltip, and
HUD layers and can present a modified palette. Proxy-only black regions are not
proof of a live rendering defect.

### Visible runtime

The visible wrapper provides final colors and composition, but GDI capture can
tear on animated screens. Use static frames where possible and separate visual
proof from input callback proof.

## Repository checks

Run the aggregate repo-only evidence refresh:

```powershell
python tools/current_evidence_refresh.py
```

Inspect the generated summary:

```powershell
python -c "import json;d=json.load(open('captures/current/current-evidence-refresh-current.json',encoding='utf-8'));print(sum(1 for v in d['checks'].values() if not v.get('passed')),'/',len(d['checks']),'failing')"
```

Run focused fixtures with:

```powershell
python tools/test_<name>.py
```

Do not launch Clash95, CDB, wrappers, PowerShell runtime harnesses, or visible
windows as part of a repo-only check.

## Launcher and resolution work

- Keep the patcher as the source of resolution constraints and generated patch
  tables.
- `src/launcher/resolutions.json` defines the user-facing resolution status.
- A resolution remains experimental until its byte gate and evidence lane pass.
- Custom resolutions must satisfy patcher constraints and remain experimental
  unless explicitly validated and promoted.
- Launcher output belongs under `C:\ClashTests\launcher\` and user settings under
  `%LOCALAPPDATA%\ClashHD\`.

## Documentation and state

- Update relevant files under `docs/hd/`, `reports/`, `captures/current/`, and
  patch metadata when a durable engineering claim changes.
- Prefer direct file paths and exact evidence identifiers over narrative claims
  without supporting artifacts.
- Distinguish current evidence from archived diagnostics.
- Do not reactivate obsolete evidence as a current blocker or current proof.
- Keep handoff documents aligned with the actual stable stage and active
  validation frontier.

## Completion criteria

A change is complete only when:

- proprietary material remains untracked;
- the original executable remains untouched;
- old-byte verification is preserved for patch changes;
- relevant repo-only tests have been run or the inability to run them is stated;
- evidence claims match the artifacts produced;
- no approval or visible/manual observation has been fabricated;
- validation-only work has not been silently promoted;
- documentation reflects the resulting project state.

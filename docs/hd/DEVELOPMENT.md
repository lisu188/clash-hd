# Development and verification

Run commands from the repository root. Read [AGENTS.md](../../AGENTS.md),
[the operating guide](WORKING_WITH_THIS_REPO.md) and
[the current handoff](AGENT_HANDOFF.md) before changing source or evidence.
Inspect `git status --short` and preserve unrelated work. Use a separate task
branch/worktree when the shared checkout is busy. Check disk reserve before
builds or large test batches under the root guide's policy.

## Python and dependencies

CI uses Python 3.12 on Windows and Ubuntu. Pure Python documentation and planner
fixtures need no game installation. Tkinter is required only for launcher UI
work; native x86 fixtures and runtime validation have additional prerequisites
documented by their individual lanes.

On Windows, select an installed interpreter while skipping WindowsApps aliases:

```powershell
$clashPythonCommand = Get-Command python,python3,py -CommandType Application -ErrorAction SilentlyContinue |
    Where-Object { $_.Source -notlike (Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\*') } |
    Select-Object -First 1
if ($clashPythonCommand) {
    $clashPython = $clashPythonCommand.Source
} else {
    $clashPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
}
if (-not (Test-Path -LiteralPath $clashPython)) {
    throw 'Locate an installed Python interpreter or ask Codex for its bundled workspace runtime path.'
}
& $clashPython -B -c "import sys; print(sys.executable); print(sys.version)"
```

The bundled fallback is workstation-specific; use Codex's workspace-dependency
lookup if it is absent. The commands below use `python` for an interpreter
already on PATH. Substitute `& $clashPython` when using the explicit path.

For reproducible synthetic image fixtures, create an isolated environment and
install the pinned [fixture requirements](../../tools/requirements-framed-offline.txt):

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r tools/requirements-framed-offline.txt
```

Use `.venv/Scripts/python.exe` for subsequent Windows fixture commands, or
`.venv/bin/python` on Linux. Do not change a shared interpreter's dependencies
to make one historical fixture pass. No API key is needed.

## Start with inspection

These commands inspect source-defined plans without game files or GUI startup:

```powershell
python -B patch_clash95_hd.py --help
python -B src/launcher/run.py --list-resolutions
python -B src/launcher/run.py --profile modalwidgets --resolution 1920x1080 --describe-plan
```

Read the saved aggregate before deciding to regenerate it:

```powershell
python -B -c "import json; from pathlib import Path; d=json.loads(Path('captures/current/current-evidence-refresh-current.json').read_text(encoding='utf-8')); print(d['generated_at']); print([k for k,v in d['checks'].items() if not v.get('passed')])"
```

The aggregate's timestamp and bound sources define its scope. Later handoff
entries can describe newer work without a new aggregate. The
[handoff's availability record](AGENT_HANDOFF.md#castle-admission-and-local-evidence-availability--2026-09-26)
also explains missing workstation artifacts; a fresh clone is not a complete
runtime-evidence environment.

## Choose checks for the change

| Change | Focused checks |
| --- | --- |
| Documentation/navigation | `python -B tools/test_handoff_freshness_guard.py`; `python -B tools/test_docs_consistency_guard.py` |
| Launcher policy and core | `python -B tools/test_launcher_core.py`; `python -B tools/test_launcher_policy_guard.py` |
| Patcher stages/resolutions | `python -B tools/test_patch_resolution.py`; `python -B tools/test_patch_definition_guard.py`; `python -B tools/test_stable_stage_guard.py` |
| Measured ordinary-input planning | `python -B tools/test_ordinary_map_input_plan.py -v` |
| Framed renderer/image evidence | [Offline validation guide](FRAMED_OFFLINE_VALIDATION.md) and its selected suite runner |
| A specific runtime/evidence protocol | The owning topic guide's fixtures before any separately authorized execution |

Fixtures test the guards' behavior. To evaluate the actual checkout docs, run
both guards with outputs redirected to task scratch:

```powershell
$clashDocCheckRoot = Join-Path ([IO.Path]::GetTempPath()) ('clash-hd-docs-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $clashDocCheckRoot | Out-Null
python -B tools/handoff_freshness_guard.py --require-pass --write-json "$clashDocCheckRoot/handoff.json" --write-markdown "$clashDocCheckRoot/handoff.md"
if ($LASTEXITCODE -ne 0) { throw 'Handoff guard failed; inspect its report.' }
python -B tools/docs_consistency_guard.py --require-pass --write-json "$clashDocCheckRoot/docs.json" --write-markdown "$clashDocCheckRoot/docs.md"
if ($LASTEXITCODE -ne 0) { throw 'Documentation guard failed; inspect its report.' }
git diff --check
```

These checks read documents, source and saved metadata. They do not verify every
Markdown link, launch a game or replay archived pixels; inspect changed links
and evidence claims separately.

The broad [framed offline CI workflow](../../.github/workflows/framed-offline.yml)
runs source-bound fixtures on Windows and Ubuntu with the pinned dependencies.
Other [workflows](../../.github/workflows) are path-filtered or opt-in and some
need original-game fixtures, native tooling or explicit runtime inputs. A green
documentation or offline job does not establish complete runtime coverage.

## Reports and broad refreshes

`python -B tools/current_evidence_refresh.py` regenerates reports under
`captures/current/`. It is an explicit evidence-writing operation, not a
read-only startup check. Some constituent checks require local artifacts or
tools and may honestly fail after checkout or cleanup. Review every generated
change; do not overwrite a historical failure to improve a count.

The optional `tools/repo_test_sweep.py` runs the broad `tools/test_*.py` set in
Python child processes. Use `--write-json`, `--write-markdown` and
`--require-pass` to choose report destinations and propagate failure. The full
sweep is larger than the documentation check set and can expose unrelated
environment or source-pin gaps. Neither sweep nor refresh grants runtime
authorization or proves stable promotion.

## Building local candidates

There is no distributable game binary build from this repository. The
[launcher](LAUNCHER.md) or root `patch_clash95_hd.py` wrapper patches a verified
user-owned executable into an external candidate. Source implementations live
in `src/patcher/`; use the root wrapper for user-facing patch commands.

Launcher `--prepare` writes a candidate without starting the game;
`--describe-plan` writes nothing and needs no game files. Native proxy builds,
CDB runs, screenshots and manual-input sessions belong to their specific
guides and authorization boundaries. Preserve exact source/candidate identities
and retained failed evidence when moving from tests to runtime work.

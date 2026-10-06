# Development and verification

Run commands from the repository root. Read [AGENTS.md](../../AGENTS.md) and
[the operating guide](WORKING_WITH_THIS_REPO.md) before changing source.

## Python

Public CI uses Python 3.12. Source-defined plans, patch metadata, launcher policy,
and synthetic tests do not require a game installation.

For optional image-processing tests that generate their own synthetic inputs,
create an isolated environment and install the pinned requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r tools/requirements-framed-offline.txt
```

## Source-only inspection

```powershell
python -B patch_clash95_hd.py --help
python -B src/launcher/run.py --list-resolutions
python -B src/launcher/run.py --profile modalwidgets --resolution 1920x1080 --describe-plan
python -B tools/check-public-boundary.py
```

## Focused checks

Use checks proportionate to the change. Typical source-only examples are:

```powershell
python -B tools/test_launcher_core.py
python -B tools/test_launcher_policy_guard.py
python -B tools/test_patch_resolution.py
python -B tools/test_patch_definition_guard.py
python -B tools/test_resolution_manifest_guard.py
python -B tools/test_stable_stage_guard.py
python -B tools/test_classic_all_presets_candidate.py
python -B tools/test_framed_all_presets_candidate.py
python -B tools/test_complete_hd_all_presets_candidate.py
python -B tools/test_modal_widgets_all_presets_candidate.py
python -B tools/test_resolution_release_matrix.py
python -B tools/test_battle_profile_context.py
python -B tools/test_ordinary_map_observation.py
python -B tools/test_ordinary_map_read_replay.py
python -B tools/test_resolution_playability.py
```

Some older tests and guides were designed around archived runtime evidence.
Those are local validation aids and are not a public CI requirement after the
repository-boundary cleanup.

## Local runtime validation

There is no distributable game binary build from this repository. The launcher
or root `patch_clash95_hd.py` wrapper patches a verified user-owned executable
into an external candidate.

Keep all of the following outside the checkout:

- original and patched executables;
- wrapper DLL binaries;
- screenshots and software-surface captures;
- debugger logs and memory dumps;
- extracted retail assets and saves;
- reverse-engineering database/export files.

Local runtime checks may record hashes and concise conclusions in working notes,
but raw proprietary evidence must not be committed. Public CI must never fetch
the original executable or runtime from another repository.

The hidden input diagnostic's `--retain-raw-observations` option retains bounded
memory-read records, undecorated decoded observations and their offline replay
results outside the repository. It uses the same held native phase and input
guards as the default diagnostic. This opt-in requires an independently
reconstructed `--prepared-matrix-candidate` or
`--prepared-small-world-candidate` bundle; legacy `--prepared-build` launcher
receipts do not qualify. Each read is bound to the actual candidate,
canonical probe, process identity, lease and frozen decoder sources; failed
reads remain partial diagnostics. Opt-in retention adds 32 MiB to the existing
128 MiB scratch allowance and does not waive the greater-than-10-percent free
space requirement. Dry runs still perform no native execution. Recorded-byte
replay can establish consistency, but it grants no live, manual, geometry,
endurance or promotion acceptance.

The ordinary-map pause client treats an `OSError` from the owned host-liveness
or retained-target identity query as a terminal lease failure. It revokes the
active lease, prevents further reads or resume requests, and raises `LeaseError`
with the complete original exception in `original_error` and `__cause__`.
`native_failures` retains that same failure. A terminating process can make its
image-path query fail before the host exit becomes observable; this does not
authorize a retry or a successful cleanup claim. Owning host/job cleanup remains
required separately.

## Generated reports

The joined initial-loader v3 workflow has separate portable and hosted Windows
synthetic lanes. The portable commands are safe source checks:

```powershell
python -B tools/test_hidden_soak_loader_v3.py
python -B tools/test_hidden_soak_loader_v3_engine.py EngineSourceTests
```

The hosted native lane requires `GITHUB_ACTIONS=true`, both
`CLASH_LOADER_V3_ENGINE_TEST=1` and `CLASH_LOADER_V3_ENGINE_INTEGRATION=1`, an
external artifact parent and separate x64/x86 compiler environments. It records
only allowlisted toolchain environment variables and preserves original
success/failure artifacts outside the checkout. One native fixture must complete
all eleven joined cases without skips. It uses marked public synthetic
executables, terminates at the initial loader hold and never runs the game or
probe. Native fixture completion supplies no resolution runtime, manual-input,
endurance, release or promotion acceptance. Its preflight and per-write reserve
must pass before producing compiler or diagnostic artifacts; local disk limits
remain in force.

Source-only tools may generate temporary JSON/Markdown reports. Redirect them to
a task-local temporary directory when possible. Runtime/capture reports belong
outside the repository.

Before committing:

```powershell
python -B tools/check-public-boundary.py
git diff --check
```

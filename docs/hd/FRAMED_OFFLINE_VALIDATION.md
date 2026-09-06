# Framed renderer offline validation

The source integration in PR #24 is not evidence of game-runtime correctness.
`tools/run_framed_offline_tests.py` provides a repeatable, source-bound baseline
for its 23 fixture modules. It never builds or launches the game itself, changes
patch bytes, repins implementation sources, or updates a promotion decision.

## Run

From the repository root:

```powershell
python tools/test_run_framed_offline_tests.py -v
python tools/run_framed_offline_tests.py --report-json C:\ClashTests\reports\framed-offline.json
```

A focused geometry run can demand that every selected test actually succeeds:

```powershell
python tools/run_framed_offline_tests.py --suite test_framed_viewport --require-complete
```

The per-suite worker timeout defaults to 180 seconds and can be changed with
`--timeout`. Each suite runs in a separate Python process so its import state
cannot contaminate the next suite. The runner continues after a failed suite
and records available tracebacks, nonzero exits, missing worker reports, and
timeouts. Its output is JSON, with progress on stderr. A requested JSON report
is replaced atomically; the report writer does not follow a preexisting output
symlink into another file.

## Source identity

Before importing fixture modules, the runner parses the existing builder's
literal `PINNED_SOURCES`, `MINIMAP_SOURCE`, and `MINIMAP_SOURCE_SHA256` declarations
without executing the builder. It checks raw file bytes, including line endings.
Both ordinary and optional minimap implementation pins must match. Missing,
malformed, conflicting, or changed pins stop the run before any suite starts.
There is no repinning or hash-override option.

The report records expected and actual source hashes and the builder's hash.
This preflight is a source-integrity check, not a proof that an original game
executable matches or that the generated x86 executes correctly.

## Interpret the report

`offline_passed` requires a passing source preflight, an outcome from every
selected suite, no unexpected failures/errors/successes, and at least one
successful test. Expected failures and absent-fixture skips remain explicit.
A wholly skipped run is not accepted as an offline pass.

`selected_coverage_complete` additionally requires every discovered test in the
selected suites to succeed, without skips or expected failures. The optional
`--require-complete` switch makes incomplete coverage a nonzero exit even when
the available offline cases pass. `full_suite_selected` says whether the whole
23-module set was requested, rather than a focused subset.

`successful_tests` counts recorded successful test cases, not test methods that
were merely discovered. `skipped_records` is deliberately not called a skipped
test count: unittest may produce one skip record for an entire class whose
`setUpClass` raises `SkipTest`. Individual reasons and identities are retained.

The `game_runtime_executed`, `manual_input_proof`, and `promotion_ready` fields
remain false. An offline pass cannot promote a resolution, complete any of the
five manual DirectInput checklist targets, or replace hidden-CDB or approved
visible-runtime evidence.

## Environment-dependent coverage

The existing tests retain their own requirements. Cases that need the
user-owned original executable, native resource data, or the Windows x86
fixture environment may skip when those requirements are absent. Some Windows
fixtures compile and execute synthetic ABI helpers in temporary directories;
these are not the game or a visible runtime session. No retail material is
installed, downloaded, synthesized as game evidence, or uploaded by this lane.

The GitHub workflow runs on Ubuntu 24.04 and Windows Server 2022 with Python
3.12. It tests the runner first, then checks source pins and runs the framed
fixture set. The job summary exposes per-suite outcomes and the completeness
flag. Only the JSON report is uploaded, with seven-day retention. Actions are
commit-pinned; permissions are read-only and checkout credentials are not
persisted. No branch protections or existing release gates are changed.

This lane supplements `tools/current_evidence_refresh.py`; it does not rewrite
that tool's historical runtime reports or reclassify known failures.

## Next evidence step

After the offline baseline, build an exact 1280x720 validation candidate on the
Windows game host, record whether the minimap viewport hook is enabled, and
collect the rendering, input, and transition evidence described in the project
guides. Keep 800x600 as the protected regression reference. Visible capture and
manual input still require fresh approval.

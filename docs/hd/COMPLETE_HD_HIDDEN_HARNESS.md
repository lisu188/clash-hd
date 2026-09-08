# Complete candidate hidden capture lane

`scripts/cdb/run_cdb_surface_dump.ps1 -CompleteHdValidation` selects the shared
`patch_clash95_hd.py` complete builder. It requires the exact
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-validation`
stage, an explicit resolution, `-UseDdrawProxy`, isolated candidate/work folders
under `C:\ClashTests`, and raw output under `C:\ClashCaptures`. It enables the
framed partial/initial painting and minimap observation lanes together. Custom
probes, skipped map checks, forced visibility, visible desktop, nonzero load
slots and post-dump continuation remain disallowed in this bounded lane.

The builder creates a new `.exe`, `.candidate.json` and canonical `.cdb` bundle.
Preflight and output SHA must agree. The generated run probe combines the
existing framed geometry recipe with the unchanged complete loaded-byte probe
and read-only minimap observers. Canonical and composed probe hashes are
recorded separately. A new `completehd-runtime-probe.cdb` explicitly uses ASCII
and CRLF for CDB while preserving canonical and intermediate probe files.
ARMY, COMPLETEHD and PTILE contract identities and ordering
are checked; inherited PTILE events keep their original army-stage identity.
Trace geometry uses the framed four-border contract and its 148-byte full-paint
stack relationship. No repeated or unmatched events are removed.

Optional `-NoopProgressDiagnostic` adds the source-bound native no-op observer
at free breakpoint 82 after the two minimap observers. Its separate report and
probe retain all existing trace records. Diagnostic progress markers cannot
override a failed trace or establish acceptance.

The initial trace verifier, minimap observer and map coverage CLI accept a
`--candidate-manifest` context. They reconstruct the complete candidate from the
known original before using inherited geometry or probe contracts. Coverage
retains its framed geometry profile and records the actual complete candidate
identity separately. A reconstructed candidate is not a successful runtime run.

Every postprocessing exception, including conversion or coverage exit 2, writes
`summary.json` and `RUN-SUMMARY.md` with `Passed=false`, the original exception,
candidate identity, trace result and artifact paths, then rethrows. Existing
summaries and raw failure artifacts are preserved. A nonzero post-dump
validation result also exits with failure rather than printing a passed run.
Host exceptions retain their message, exception identifier and stack before
flowing through the failed run summary. Cleanup checks the launched debugger
ID/path/start time and candidate path/start time for up to five seconds. A
surviving process or unavailable identity fails cleanup; unrelated processes
are neither stopped nor counted as task-owned survivors.

This integration supplies a bounded initial ordinary-map capture path. It does
not prove minimap movement/erasure, all map scroll/clamp/clear routes, modal or
army transitions, battle return, visible colors, manual input or release
eligibility. Those requirements remain separate evidence lanes. No new runtime
result or screenshot is claimed by the source fixtures.

Offline checks: `tools/test_complete_hd_hidden_harness.py`,
`tools/test_render_cdb_surface_probe.py`, `tools/test_initial_map_paint_trace.py`,
`tools/test_map_tile_coverage.py` and `tools/test_framed_minimap_integration.py`.
The PowerShell fixture parses the harness and executes only extracted summary
helper code against synthetic temporary files; it never invokes the harness,
Clash95 or CDB.

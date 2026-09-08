# Source-bound gameplay evidence for the complete candidate

`tools/framed_gameplay_evidence.py --candidate-manifest <candidate.candidate.json>`
extends the existing framed gameplay evaluator to the integrated validation
candidate. Supply the original executable, run summary, coverage JSON, log,
installed probe, native frame resource and command resource through its existing
arguments. The output must be a new JSON file; all supplied artifacts remain
read only.

The shared candidate context reconstructs the executable, manifest and sibling
probe from the current source recipe. The evaluator checks the summary's exact
manifest path/hash, candidate, resolution, recipe and probe, then verifies the
source-pinned hidden run plan. The plan command requires `-CompleteHdValidation`,
the exact complete stage, hidden proxy, slot zero and bounded observation flags.
Explicit partial/initial/framed/minimap switches are allowed as redundant
complete-mode flags. Visible, forced and custom probe routes remain outside this
evaluator's accepted lane.

The run plan must pin the candidate manifest's `source_hashes`, the historical
`PRODUCER_SOURCES` listed in the evaluator, and its additive
`COMPLETE_PRODUCER_SOURCES`. The latter cover the shared runtime context,
candidate-evidence reader and minimap probe generator. Runtime producer edits
invalidate an older plan until a new source-bound run is prepared.

The log must contain exactly one matching army, complete and partial-tile loaded
contract in the canonical order. The initial-paint evaluator then checks all
native call identities, events and closure without dropping duplicates. The
complete candidate retains the inherited framed geometry: the coverage report
records that predecessor geometry stage and a separate exact complete candidate
context. Frame/footer pixels and all six action cells are independently compared
with the native resources.

Blank terrain is explained only by the single complete visibility-memory span
at the paused capture boundary. The measured minimap state determines its mask.
Earlier zero-visibility events cannot excuse a currently visible blank cell,
and missing, duplicate or mismatched snapshot observations fail. Out-of-world
clearing remains a separate acceptance requirement; this evaluator requires
the whole ceiling window to remain in the world.

A guarded software gameplay result preserves `input_passed`, `input_error` and
any original `Failures` list. It does not change the original runtime verdict,
prove final visible composition or controls, or accept modal/army transitions,
cleanup, continuity, endurance or promotion. The complete candidate's inherited
modal and army implementation remains experimental until those independent
requirements pass.

Run `python -B tools/test_framed_gameplay_evidence.py` and
`python -B tools/test_action_bar_surface_audit.py` for offline verification.
The integrated fixtures exercise the real artifact/context, trace, snapshot,
pixel and coverage checks with an explicitly synthetic candidate builder and
synthetic resources. No game or debugger runs in these fixtures.

The preserved component implementation was imported from the read-only local
source checkout before this additive integration. Its source snapshot digests
were `1ccf89a08475a8995e0f2822d25e497768c1c829deafc2f331af96d3add0f469`
for the evaluator and
`0ea37df2d32b77fdb45c4c287432ac03e08431ead9d0d0677456f25e04fc7061`
for its fixtures. These identify the import, not the extended files or a runtime
candidate.

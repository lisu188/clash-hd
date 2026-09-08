# Complete-HD evidence evaluation

`tools/complete_hd_promotion.py --release-manifest <index.json>
--candidate-manifest <candidate.candidate.json> --write-json <new-report.json>`
evaluates the fixed 1920x1080 acceptance set without launching a process,
capturing a screen, injecting input, or changing the release stage. The index
uses `complete_hd_release_manifest_v1` and contains immutable `path`/`sha256`
references for the base executable, candidate, exact builder metadata, probe,
and all 16 lane reports. The shared candidate context rebuilds actual candidate
bytes and the probe with the complete builder; identity text alone is rejected.

The release index cannot choose validation code. A lane must have a fixed
repository verifier that recomputes its required checks from original artifacts.
A report containing passing booleans, a pinned arbitrary log, and the hash of a
file under `tools/` does not establish acceptance. Unsupported verifiers remain
explicit failures. Currently the resolution lane rechecks the actual launcher
profile, recipe, resolution, default and experimental status. The 15 runtime,
composition, input, continuity and endurance adapters are still incomplete.
Historical component reports are not rewritten into integrated proof.
The current launcher supports Classic and Framed profiles; it does not yet
support a complete-HD profile matching this candidate. The resolution lane
also remains unsatisfied, and a launcher-rejected profile cannot establish
evidence. No complete-release eligibility is established by the current code.

`candidate_manifest_context()` in `tools/complete_hd_evidence.py` loads the
complete builder's `.candidate.json`, `.exe` and `.cdb` bundle. It delegates
deterministic reconstruction to `tools/complete_hd_runtime_context.py`, the
same verifier used by the hidden runtime consumers. Missing or changed files,
mixed candidates, other resolutions, changed recipe/source hashes, and altered
probe bytes fail. The original executable is read only and candidates must be
isolated under `C:/ClashTests`.

Evidence readiness, eligibility, and explicit promotion approval remain
separate fields. Approval must bind the exact candidate and acceptance digest,
and follow the reviewed reports. An incomplete or deferred whole-release result
returns exit code 2 even without `--require-pass`. Release evaluation creates a
fresh output and refuses to replace prior evidence; the default output gets a
unique evaluation path. It never checks release checklist boxes. The historical
`--run-manifest` component mode retains its existing behavior.

The imported observation protocol remains scoped to its existing 800x600
component stages. It checks native descriptor, X/Y hit test, pressed-input gate,
dispatch, callback and thread identity against an observation-only probe and
owned-process receipt. It is not yet an integrated 1080p producer. Its planner
does not execute; actual observation still requires fresh approval and human
input. Neither its callback result nor synthetic offline fixtures count as the
five-target manual release proof.

Relevant offline checks are `test_complete_hd_evidence.py`,
`test_complete_hd_promotion.py`, `test_hd_endurance_release_checklist.py`,
`test_hd_layout_command_input_summary.py`, and
`test_hd_layout_observation_manifest.py`. Positive policy fixtures inject test
verifiers explicitly; the production verifier registry rejects their invented
green envelopes. Raw game material and runtime captures remain external.

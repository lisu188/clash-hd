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
profile, recipe, resolution, default and experimental status. The panel-command
lane now reruns its native callback parser over the original recorded log,
loaded-byte guards, approval, plan and owned-process receipt. The other 14
runtime, composition, input, continuity and endurance adapters remain incomplete.
Historical component reports are not rewritten into integrated proof.
The launcher now exposes an experimental `completehd` profile. Resolution
metadata is checked through the actual launcher validator; unknown or malformed
profiles cannot establish evidence. This metadata coverage does not satisfy
the remaining incomplete runtime adapters or establish complete-release eligibility.

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

The observation protocol retains its historical 800x600 component mode and
adds `--candidate-manifest` for the complete candidate. The planner, producer,
and parser derive target bounds and capture dimensions from the framed
geometry. They bind the exact candidate stage, resolution, recipe, metadata and
probe hashes through the approved plan, raw log and owned-process receipt.
The release probe keeps the reconstructed loaded-byte guards and the existing
native descriptor, X/Y hit test, pressed-input gate, dispatch and callback
breakpoints. It omits the map diagnostic body and never forces a route or
callback. Missing or reordered native observations cannot be replaced by a
caller-authored passing result.

For planning, use `tools/hd_layout_observation_manifest.py` (or the PowerShell
adapter) with `--candidate-manifest`, the matching `--candidate` and `--stage`,
and the existing local wrapper, configuration, debugger, isolated assets and
output arguments. `--input-method manual_directinput` describes a human
operator; `--input-method win32_sendinput_relative` describes a separately
approved relative pulse driver. The observer itself injects nothing. The plan
is read only until `--write-plan` is requested. Actual observation requires
fresh approval bound to that saved plan and both execution switches.

Evaluate its recorded manifest with
`tools/hd_layout_command_input_summary.py <command-input-manifest.json>
--candidate-manifest <candidate.candidate.json>`. A release lane references this
original command manifest as both `command_manifest` and a `source_artifacts`
item, and identifies `tools/hd_layout_command_input_summary.py` as its producer.
It reuses the original approval reference; no second approval record is
invented for evaluation. Callback proof accepts disclosed pulse input and
remains separate from all five human-operated manual targets. Synthetic offline
fixtures and a generated observation plan are never actual callback proof.

Relevant offline checks are `test_complete_hd_evidence.py`,
`test_complete_hd_promotion.py`, `test_hd_endurance_release_checklist.py`,
`test_hd_layout_command_input_summary.py`, and
`test_hd_layout_observation_manifest.py`, plus
`test_complete_hd_command_input.py`. Positive policy fixtures inject test
verifiers explicitly; the production verifier registry rejects their invented
green envelopes. Raw game material and runtime captures remain external.

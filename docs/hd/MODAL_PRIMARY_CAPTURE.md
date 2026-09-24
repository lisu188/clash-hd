# Owned modal primary runtime capture

The new `scripts/cdb/run_modal_primary_capture.ps1` observes the experimental
`owned_modal_primary_v1` candidate described in
[MODAL_PRIMARY_COMPOSITION.md](MODAL_PRIMARY_COMPOSITION.md). It requires the
new candidate's exact `.candidate.json`, sibling executable and loaded-byte
probe. The slots-stage consumer and its retained failed D/F runs keep their
original meaning.

## Four actual draw boundaries

The host pauses the same candidate at four ordered boundaries:

| Checkpoint | Native state and comparison |
| --- | --- |
| `full-published` | The HD blitter has returned, before its added cursor redraw and before all twelve barracks slot copies. Compare the entire primary with the measured physical mirror. |
| `placeholder-before` | Twelve native dirty slot copies and the panel cursor-rectangle operation have completed. Retain the actual arguments immediately before `CALL [ESI+34]` at `00432F9E`. |
| `placeholder-after` | The native sprite call returned at `00432FA1`. Compare its actual before/after pixels with the original source sprite at the observed centered destination. |
| `final-ready` | The first native barracks presentation returned at `00433E77`. Retain three matched native, physical and cached-primary samples, including final cursor state. |

The first three stops each have one pixel sample surrounded by paired identity
reads. They are not a stable pair of screenshots. The final stop requires three
matching pixel samples. Every checkpoint retains the current attached palette,
owned canvas state and headers, primary backend/COM headers, native cursor
descriptor, selected sprite header and 64x64 cursor backing. The auditor uses
the original `minimum.res` cursor and `maximum.res` barracks placeholder to
check draw order; it does not exclude a rectangle merely because a cursor or
overlay might occupy it.

The first three boundaries precede native barracks fade-in. When the actual
attached palette has zero RGB values, the PNG converter labels its output
`grayscale-index-empty-palette`: this shows retained indices, not captured
colors. The host and auditor derive that mode from the exact palette bytes,
retain their hash and bind the resulting RGB preview. A nonempty palette must
use `directdraw-palette`; neither mode establishes final-wrapper composition.

The native archive loader accepts bounded trailing bytes after complete
26-byte directory entries. Asset parsing follows that original floor rule,
while retaining extent, count and unique-member checks. Original asset files
and decoded member identities remain required.

The initial unselected placeholder path exercises three of the five installed
patch sites. The selected-panel rectangle and partial-copy paths need a later
selection case. Installed bytes, observed branches, correct pixels and ordinary
input are separate claims.

## Hidden execution and process ownership

Without `-Execute`, the host performs preparation and returns a concrete plan.
It does not create a desktop, start CDB or the game, read process memory, or
create candidate/capture directories. It uses the exact previously supported
non-presenting proxy, SHA-256
`b173a9dd4ce772eb5b56f341acdf4b329ed4ffdd638c1fce5cc37dd332804b70`,
with its genuine build manifest and recorded/current source bytes.

An executed run retains the debugger and candidate handles, verifies their
path, parent and creation identity, and uses a private hidden desktop. The
child receives only the explicit stdin/NUL handle list through Windows
[extended process attributes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).
After a validated prefix and complete paused capture, the host sends exactly
`g` plus CR/LF through its private debugger pipe. This resumes the authentic
instruction stream; it adds no OS input or render call. The inherited controlled
castle dispatch and one forced flipping-gate result remain explicitly logged.

The plan bounds the launched run to 600 seconds, including four full candidate
prefix validations. Each offline validator has its own 120-second bound.
Early failures retain the final available debugger trace and verified cleanup.
Captured raw pixels are retained and converted even when a later check fails.
If saving the final summary fails, stdout retains the actual execution and
cleanup records with a failing verdict; it cannot become a preparation-only
failure that incorrectly says the game never ran.
Only task-owned processes are stopped, and the debugger pipe and desktop are
closed. Reuse neither a candidate directory nor an output directory.

The first runtime attempt stopped at the unchanged cursor-rectangle guard.
Its rejecting operands were not recorded. New probes emit 22 scalar diagnostic
fields only on that rejection path, before the existing rejection marker and
quit. The validator retains the fields and always rejects that diagnostic;
it cannot make a failed route acceptable or change a successful route's event
requirements. See the [failed attempt](../../captures/current/modal-primary-1024x768-20260919-attempt-a.json)
and [updated source checks](../../captures/current/modal-primary-runtime-source-validation-20260919-b.json).
The [second actual attempt](../../captures/current/modal-primary-1024x768-20260919-attempt-b.json)
retains the diagnostic and fails at the same guard. Its first-checkpoint pixels
match attempt A exactly. All three PNG receipts now bind the measured empty
palette correctly, but the bottom-frame artwork defect and incomplete route
remain failures.

B's printed 32-bit operands match the expected guard inputs. Earlier retained
x86 CDB observations, already handled by the army-selection probe, corroborate
a sign-extension diagnosis: `poi` can return `ffffffffffffffff` for the native
DWORD `-1`, while the unsigned literal is `00000000ffffffff`. The primary probe
now masks only that selected DWORD and the four native `-1` placeholder
arguments before exact equality. Its regression evaluates the emitted guards
with both read forms and rejects other DWORD values. B itself did not print
the upper 32 bits. A and B remain failed, and this source correction still
requires fresh runtime evidence. See the
[post-diagnostic checks](../../captures/current/modal-primary-runtime-source-validation-20260919-c.json).

## Preparation and verification

Build the primary candidate with the source builder first. Then pass that
bundle, the genuine proxy build manifest, a fresh isolated game working
directory, and new candidate/capture paths to the host. For example, omit
`-Execute` when reviewing a plan:

```powershell
powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -File scripts/cdb/run_modal_primary_capture.ps1 `
  -InputCandidate C:/ClashTests/<primary-bundle>/candidate.exe `
  -CandidateManifest C:/ClashTests/<primary-bundle>/candidate.candidate.json `
  -ProxyBuildManifest C:/ClashTests/<genuine-proxy-build>/ddraw_surfdump_proxy.build.json `
  -WorkDir C:/ClashTests/<isolated-game> `
  -CandidateDir C:/ClashTests/<new-runtime-candidate> `
  -OutDir C:/ClashCaptures/<new-primary-run> `
  -Resolution 1024x768 -Route barracks -CastleIndex 0 -Availability existing_flags
```

These placeholders are documentation, not a runtime or approval record. Follow
the repository's runtime approval boundary for the concrete run. The final
source-bound audit entry point is `tools/modal_primary_surface_audit.py
--summary <out-dir>/summary.json`. It checks the unchanged files, full final
log, nested checkpoint prefixes, paired reads, regions, cleanup, source-backed
pixel composition and actual PNG pixels. Its result remains limited to this
hidden controlled route. Visible-wrapper composition, normal mouse input,
selected-panel behavior, other buildings, modal exit, continuity, endurance
and explicit stable promotion remain separate work.

Show the actual primary, physical and native screenshots after meaningful
captures. Label the stage, resolution, checkpoint and method. Inspect the
centered canvas perimeter, all outer margins and the five applicable bottom
modal controls; do not apply the ordinary-map six-cell action-bar claim to a
modal screen.

## Strict admission and retained failures (2026-09-24)

The primary context, route, capture and surface consumers now decode external
JSON with one strict object reader. Duplicate decoded keys at any depth,
non-object roots, non-finite or overflowing numbers and excessive nesting fail
before they can be interpreted as a candidate, packet or artifact report.
Typed manifest comparison still distinguishes booleans, integers and floats.

Trace admission discovers every reserved MCAP, MPCAP, MPRI and MPRIMARY
occurrence, including malformed attached prefixes. It retains repeated rows
and rejects them through the existing sequence/cardinality checks. The native
trace also rejects the same anchored debugger-command failures recognized by
the host; this is not a claim to recognize every possible debugger diagnostic.

Failed capture and checkpoint-prefix evaluations retain the unchanged underlying
route reports and every raw MPRI row, even when the earlier native route already
failed. Capture and surface-report exception boundaries expose those failure-only
diagnostics. Accepted report shapes remain unchanged. Raw rejected records are
diagnostic data and do not acquire source or runtime authenticity by being kept.

The focused staged validation passed 54 tests with no skips and preserved all
28 before/after accepted synthetic report comparisons. Its source snapshots,
86 synthetic logs, independent-review reproduction and follow-up, and the failed
nesting-fixture attempt are retained outside the repository in
`C:/ClashCaptures/completehd-integration-20260924/admission-ledger-source-checks-v1/`.
The preservation manifest SHA-256 is
`90268b64d89c96a70afa60a89aad5f73443b2ab3a4815d6bf7429721ed87c062`.
The failed fixture assumed the decoder rejected 1,200 nested objects; the final
negative case uses an actually excessive depth. That original failure is retained.

These source changes require fresh source-bound packets. Existing A/B captures,
source snapshots, frozen candidate recipes, bytes and legacy reports stay
unchanged. Parser checks do not establish corrected primary pixels, natural
controls, manual input, continuity, endurance or release acceptance.

After integration, all six canonical suites have passing results: 83 tests in
total, without skips, including actual 1024x768 reconstruction and native asset
checks. The first combined report retains one failed trace fixture. Its reused
historical sidecar had three absolute source-binding paths from a different
checkout; source hashes and candidate content did not drift. The fixture now
builds fresh local inputs, and the full 26-test trace module passes with both
producer and validator still rebuilding independently. The historical bundle
and original executable remain unchanged.

The combined failure, successful trace rerun, exact path-difference diagnosis,
source snapshots and original/historical-file rechecks are retained in
`C:/ClashCaptures/completehd-integration-20260924/admission-integration-checks-v1/`.
Its preservation manifest SHA-256 is
`3bbf11434e8dc6f68f7d70a93623a99e6af589347d507b7045aa3be37498438a`.
This is a set of focused source checks, not a passing whole-repository or game
release evaluation.

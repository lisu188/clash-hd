# Native quantity observations for the text candidate

[`modal_primary_text_observer.py`](../../tools/modal_primary_text_observer.py)
prepares a read-only debugger fragment for the separate
`-completehd-modalprimarytext-validation` candidate. Its protocol is
`modal_primary_text_observation_v1`. It does not launch a game or provide a
complete capture host. Actual text-stage gameplay and glyph composition remain
unverified.

## Candidate and command binding

`build_fragment` first invokes the [exact context reader](MODAL_PRIMARY_TEXT_CONTEXT.md).
The packet binds the actual candidate, stage, recipe, resolution, raw manifest,
loaded-byte probe, all recipe sources, context reader and observer source. It
then verifies the installed quantity CALL, emitted adapter and delegation tail,
native formatter spans, caller cleanup and `%d` format bytes.

The caller supplies the occupied breakpoint IDs and addresses. Three distinct
new IDs, normally 150/151/152, observe adapter entry, native formatter entry
restricted to return address `00432C6B`, and that native return. All definitions
start disabled. Explicit arm and disarm commands are returned separately. The
surrounding host must authenticate its complete command inventory and run the
exact candidate loaded-byte probe before arming the fragment.

The generated fragment uses **CRLF bytes**, with every command line below the
debugger's 4,096-byte limit. Preserve those exact bytes when exporting or
validating the fragment. The CLI reads the fragment as raw ASCII bytes, without
universal-newline conversion. The source files themselves use LF.

The sequence evaluator requires exactly `ADAPTER`, `NATIVE`, `RETURN`, with
matching thread, stack, return address, active canvas ownership, render device
and surface geometry. It checks original native argument bounds, the three
translated coordinates, unchanged alignment, format and signed quantity, and
the registers and flags preserved by the adapter/native formatter. DWORD reads
use `dwo`, avoiding pointer sign-extension ambiguity.

Repeated, missing, reordered, malformed, prefixed and rejected observations
fail. Debugger failures and mixed predecessor startup markers also fail. Their
raw lines remain in the result; no duplicate event is discarded. The standalone
sequence evaluator always reports `source_authenticated=false`. Only
`validate_trace`, which reconstructs the context and regenerates the exact
packet and fragment, can bind a passing triplet to the candidate. Its text hash
covers the supplied Unicode text; the outer host must also bind the untouched
raw log bytes.

## Verification and preserved failure

The 16 pure source fixtures pass. A separate opt-in test,
[`test_modal_primary_text_observer_engine.py`](../../tools/test_modal_primary_text_observer_engine.py),
uses the system x86 debugger engine and a marked synthetic PE32 target. It
parses the exact disabled definitions, evaluates all three event expressions,
exercises pointer rejection and ignores an unrelated native formatter caller.
For this fixture only, standalone `gc` commands become a labeled echo. The
target stays paused at the same instruction, with its executable unchanged.
This validates debugger grammar and expressions; it does not execute the
native game text call or prove continuation behavior.

The first engine attempt failed because its LF command transport truncated
command prefixes. That report remains unchanged at
`C:/ClashCaptures/completehd-integration-20260919/primary-text-observer-dbgeng-20260919-a.json`,
SHA-256 `178443380842c5be7ad47f51b0526c4db3fdf2156d4947a78a7eb93d525196fe`.
The final CRLF check passed in 1.483 seconds. Its report is
`C:/ClashCaptures/completehd-integration-20260919/primary-text-observer-dbgeng-20260919-c.json`,
SHA-256 `aa85f54d707f4e3592d249bb51da95b0b714016a67f0f3f92d37ea08b952b263`.
The intermediate successful report remains separate. The native engine test
requires its own explicit opt-in and is excluded from the repo-only aggregate.

All three reports and the exact final three source files are archived under
`C:/ClashCaptures/completehd-integration-20260919/primary-text-observer-source-freeze-20260919/`.
Its manifest SHA-256 is
`874035872c01c6c38249010145c0232aa7609ec4e51cc9fdeb61e4ccf3b586b8`.
The failed attempt's three source versions were reconstructed afterward and
matched against the hashes already recorded in its report; the archive labels
them as reconstructed, not contemporaneous snapshots.

## Remaining integration

The four-checkpoint capture host needs an explicit text-stage profile. Its
first `full-published` checkpoint precedes the text draw; that prefix cannot
require a complete quantity triplet. Later source-confirmed checkpoints and
the final trace must require the full triplet. Primary and cursor query ledgers,
unchanged source/candidate checks, stable captures and owned cleanup remain
independent host requirements.

Pixel acceptance must establish the intended native glyphs at the translated
destination and their absence at the old position, with source-verified cursor
backing handled separately. Observation preparation or a valid triplet does
not establish composition, ordinary input, modal exit, continuity, endurance
or release eligibility.

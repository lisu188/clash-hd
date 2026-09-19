# Text observer cdecl ABI follow-up — 2026-09-19

## Change

PR #98's return predicate checked EBX/ECX/EDX/EBP. It now checks
EBX/ESI/EDI/EBP, the x86 cdecl callee-saved general registers. EAX, ECX
and EDX may change across the native formatter. The separate adapter-entry
predicate still requires all seven incoming general registers and its existing
arithmetic/direction flag mask to survive unchanged.

Reference: [Microsoft x86 argument-passing conventions](https://learn.microsoft.com/en-us/cpp/cpp/argument-passing-and-naming-conventions?view=msvc-170).

Only `evaluate_sequence` changes in the production observer. Candidate builders,
patch bytes, native spans, source authentication, loaded-byte probes, breakpoint
expressions, CRLF transport, stack geometry, and raw-record retention are not
changed. Classic/800x600 and the protected stable stage are not changed.

## Regression coverage

Three methods were added to the existing `TextObserverTests` class already
selected by the framed offline runner. They add 186 subtest combinations over
800x600, 1024x768, 1280x720, 1280x960, 1920x1080 and 802x602:

- 120 volatile-register cases: EAX, ECX, EDX, separately and together, with
  quantities 0, 250, -1, INT32_MIN and INT32_MAX. Signed quantity, complete raw
  return observations, and the absence of runtime/promotion claims are checked.
- 24 saved-register cases: independent EBX, ESI, EDI and EBP corruption must
  retain the failing return record and reject the native ABI.
- 42 adapter cases: every incoming general register remains mandatory at the
  adapter-to-native boundary, including the cdecl volatile registers.

## Local validation and its boundary

The two pre-edit files were reconstructed from GitHub and matched their exact
Git blob identities before editing:

- Observer: `d84c5ce505d0f730c189d2d860aa76258aab0a2b`.
- Tests: `134dbf36d50a44d9cfa8cb024e3e9cdba84f910d`.

The local Linux environment could not clone GitHub and has no game installation
or x86 CDB. The local run therefore imported the exact observer/test files with
explicit test doubles for the builder context, patcher constants and PE loader.
Constants came from the same PR source revision. Unexpected real reconstruction
or PE loading was configured to fail; existing test-level mocks remained in
place. This is isolated unit validation, not the full repository fixture run.

With the new tests and the old predicate: 19 methods ran, 102 failing subtest
records, zero errors and zero skips. With the one-line fix: 19 methods passed,
zero failures, errors or skips. `py_compile`, `git diff --check`, and an AST
comparison confirming that only `evaluate_sequence` changed also passed.

Updated source SHA-256 identities:

- `tools/modal_primary_text_observer.py`:
  `b92fbe6fce1c73301ed53873c6739a3b3408662c8f29021abcde9482ff0d491d`.
- `tools/test_modal_primary_text_observer.py`:
  `7f62f10369e6c5ae42208eb0d21147db76722f5bc60a4fb5a2f94713b4eae9dc`.

GitHub Actions is the separate full-checkout validation lane; use the checks for
the exact PR head rather than interpreting this local receipt as a CI pass.

## Historical evidence remains historical

The earlier native debugger transport report and failed LF attempt are retained
unchanged with their original source identities. They are not new native
execution evidence for this observer revision. Observer packets include the
producer source hash, so regenerate packets/fragments for new runs instead of
relabeling retained logs. No fresh game execution, glyph composition, cursor,
manual-input, whole-runtime acceptance or stable promotion is claimed.

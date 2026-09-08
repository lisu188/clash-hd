# Framed unit-selection diagnostic

Observed 2026-09-06T07:35:59Z–07:37:33Z at **1024x768** on candidate
`c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d`.
The [manifest](framed-unit-selection-diagnostic-current.json) binds both
attempts, exact probe/host/source files, screenshots, pixel checks and cleanup.

**Native selection succeeds; portrait composition fails.** The known slot0
army3 at world16,19 changes selection from -1 to3, with native occupancy3,
player0 and EAX1. The native panel route runs `40A500 -> 423B00 -> 423420`;
prior selection becomes3 and the lower-row owner becomes1. Eight portraits
appear at the old native y400..463 position. The following map redraw erases
them. Within x32..415/y400..463, 24,568 of24,576 pixels change.

| Capture | Action bar | Frame audit |
| --- | --- | --- |
| Before redraw | 6/6 cells match | Top/bottom/right match; left has198 mismatches |
| After redraw | 6/6 cells match | Top5,771, left8,519 and bottom484 mismatches; right matches |
| Final selection return | 6/6 cells match | Identical pixels to after-redraw capture |

All three full frame gates fail. Native selected-army rows are outside the
candidate's accepted ordinary-map composition context. This is a newly
observed selected-army defect; it does not reopen the resolved historical
right-bottom gate-design question.

The corrected run's initial-map trace passes. Both retained CDB/game handles
report process absence and closure; the hidden desktop closes. The original,
candidate and existing58 workdir files remain unchanged, with no added files.
The controlled probe changes scroll to10,17 and logical mouse data to448,176,
then invokes native selection and the updater. It never forces the native
selection predicate. This is **not** an OS-click or manual-input result.
Software E0 captures are not final visible-wrapper composition.

The earlier attempt, 07:32:19Z–07:34:21Z, remains failed with no captures.
Incorrect debugger breakpoints at423B31/423B3B lay inside CALL operands;
the first produced exception addressCD423420. This is instrumentation failure,
not a game defect. Correct boundaries423B32/423B3C were derived from verified
five-byte calls and independently disassembled before the second run.

See [selected-army HD work](../../docs/hd/UNIT_SELECTION_HD.md) for the exact
overwrite mechanism and remaining implementation. No patch bytes, stable
stage, manual-proof record or promotion decision changed in these tests.

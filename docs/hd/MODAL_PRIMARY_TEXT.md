# Center the native barracks quantity text

The separate `-completehd-modalprimarytext-validation` stage, recipe
`owned_modal_primary_text_v1`, adds one coordinate adapter above the exact
`owned_modal_primary_v1` candidate. It preserves the old primary recipe and
all earlier candidate bytes. The protected stable stage, Complete HD v1 and
800x600 launcher default remain unchanged.

The [2026-09-19 source-validation checkpoint](../../captures/current/modal-primary-text-source-validation-20260919.json)
binds 46 passing focused tests, all six exact builder resolutions and the three
prepared 800x600, 1024x768 and 1920x1080 bundles. It also retains the initial
BSS-predicate failure and distinguishes recovered tool-output receipts from
contemporaneously saved test reports. All 34 recipe sources plus the five
fixture/preservation helpers are archived outside the repository. The new
1080p candidate SHA-256 is
`21add69c3c8d61b3c57114dd33ff71255660598e103f7a3561bc5cf0798ccf0a`.
No game process was launched for these checks or bundle builds.

The retained 2026-09-19 primary captures at 1024x768 and 1920x1080 show the
quantity `250` in the top margin even though the wall and twelve portrait
slots are centered. This new stage addresses that one native text call.
Its emitted-code, PE and loaded-byte checks do not establish actual glyph
composition, manual input, complete modal routes, native exit or promotion.

## Native call and adapter

At `00432C32`, the barracks routine selects cached primary device `0051D4C0`
and font 5. After the twelve slot copies it calls `UI_DrawTextFmt` at
`0040C150` through `00432C66` (file offset `00032066`, old bytes
`E8 E5 94 FD FF`). The six cdecl arguments are:

| Argument | Native value | New value in an authenticated owned canvas |
| --- | --- | --- |
| Left text bound | 545 | 545 + `(width - 640) / 2` |
| Right text bound | 613 | 613 + `(width - 640) / 2` |
| Y origin | 53 | 53 + `(height - 480) / 2` |
| Alignment | 3 | Unchanged |
| Format | `%d` at `004EFC3A` | Unchanged |
| Signed quantity | DWORD at castle pointer + `1B6` | Unchanged |

The three corrected values are `(737,805,197)` at 1024x768 and
`(1185,1253,353)` at 1920x1080. These are formatting bounds and the y origin;
the centered glyph's first x coordinate depends on the native font and value.

The adapter saves registers and flags, verifies the inherited active canvas
and zero fault, primary render device, saved EBP, return address and original
argument shape, then updates only the three coordinates. It restores machine
state and tail-jumps to the native formatter. Return remains `00432C6B`; the
original caller consumes all six arguments with `ADD ESP,18h`. Rejected
contexts retain their native arguments. The inherited ownership validator's
documented fault-4 latch remains in effect for invalid active ownership.

The emitter authenticates the full predecessor and four native instruction
spans, including formatting, centering and per-character dispatch. It does not
replace glyph resources, font selection, quantities or rendering callbacks.

## Build and verification boundaries

[`build_framed_modal_primary_text_candidate.py`](../../tools/build_framed_modal_primary_text_candidate.py)
reconstructs the entire predecessor, cross-checks the emitter's source and
candidate identity, appends the fourteenth RX section `.hdptxt`, and installs
one five-byte CALL replacement. All thirteen old section headers, inherited
HIGHLOW fields and the historical relocation directory remain intact.

The new loaded-byte probe verifies every inherited predicate before changing
only explicitly recorded edit bytes. It adds the new section/header, native
text spans, format bytes and `MPRIMARYTEXT` contract. Original zero-filled BSS
is read according to PE loader semantics even when its legacy raw-size field
is nonzero. Unknown input, wrong native bytes, invalid allocation, conflicting
relocations, changed source, undeclared probe edits and output collisions fail
closed. Output must be an absolute `.exe` path under `C:/ClashTests`, outside
the active checkout; executable, manifest and probe are created exclusively.

The aggregate registry contains six separate emitted-x86 profile groups and
six exact-build profile groups, plus portable PE/probe/output fixtures. The
600-second per-suite deadline is unchanged. Actual native formatter-recorder
execution proves argument placement and ABI preservation; it does not draw
native glyphs or count as gameplay evidence. Exact builds additionally check
record replay, source bindings, independent relocation, and Windows
`SEC_IMAGE` admission without starting or mapping an executable process.

## Required fresh runtime evidence

The [exact text context reader](MODAL_PRIMARY_TEXT_CONTEXT.md) now rebuilds the
new candidate and preserves the actual identity of each inherited context.
The existing first-present prototype and four-checkpoint primary consumer
still authenticate primary-v1. They must reject this new text candidate until
their explicit stage integration is implemented. Replacing markers in an old
log or supplying the predecessor manifest would invalidate the evidence.

The new consumer must rebuild the exact text bundle and bind its manifest,
loaded probe, recipe, sources and resolution. Read-only observations should
cover the adapter entry, native formatter entry restricted to return
`00432C6B`, and native return. Match thread, stack, render/canvas identity and
all six arguments, including unchanged quantity/alignment/format and the
expected three translated coordinates. Use fresh v2 raw-query ledgers and
stable native/physical/primary captures. A text-aware pixel oracle must check
the intended destination and absence at the old position while accounting
for source-verified cursor backing separately. Old primary captures and all
failed receipts remain historical evidence.

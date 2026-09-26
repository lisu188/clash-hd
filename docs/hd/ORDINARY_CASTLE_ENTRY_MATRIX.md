# Native castle-entry resolution matrix

The additive `owned_ordinary_castle_entry_matrix_v1` recipe admits the native
Building_GetInto caller into the inherited owned castle canvas. It supports
`completehd` and `modalwidgets` at 800x600, 1024x768, 1280x720, 1280x960,
1920x1080 and 802x602. This is a validation-only builder; launcher integration,
4K, bounded small-world composition and game runtime acceptance remain pending.
The protected stable stage and original executable are unchanged.

The [exact 1024 predecessor](ORDINARY_CASTLE_ENTRY.md) explains the mismatch:
the native caller installs renderer 004617A0 before calling the root, whereas
the inherited guard expects ordinary renderer 0040AD40. The matrix successor
reconstructs the original-bound native-present parent for each profile and
resolution and follows its typed metadata chain to the owned modal canvas.
It derives the authenticated wrapper, admission and state addresses rather
than borrowing addresses from the 1024 candidate.

## Patch and verifier contracts

The successor verifies the native call/return and saved-owner instructions,
then replaces the six-byte rejection branch with a jump to a 96-byte caller
guard. It extends only the last RX section at the next image page. Declared
PE size/header fields change; old section payloads outside the dispatch hook
and the complete HIGHLOW inventory remain unchanged. The new guard is position
independent, preserves GPRs, flags and stack, and writes no live owner state.
The inherited allocation, fault, surface, thread and rollback checks still run.

The generated initial-breakpoint verifier checks final headers, file-backed
executable bytes and legacy wrapper spans against the actual loaded base.
HIGHLOW words are rebased, including high-bit DWORDs. Ordered chunk completion
is mandatory: missing, reordered, corrupted or unreadable checks cannot emit
the final acceptance marker. Mutable data and imported libraries are outside
this contract. The verifier now emits CRLF because the actual Windows debugger
command-file reader failed positive LF-only scripts even when block mode passed.

## Verification and reproduction

Run the portable fixtures without game assets, then the independent gate CPU
cases with an installed Unicorn 2.1.4 environment:

```powershell
python -B tools/test_ordinary_castle_entry_matrix.py PortableTests -v
python -B tools/test_ordinary_castle_entry_gate_cpu.py --require-machine-tools -v
```

The portable suite passed 8/8 methods. The independent gate suite passed
10/10 methods and 160 synthetic cases across the exact and matrix emitters,
two load bases, valid and invalid callers, and two flags states. These CPU
cases check only the gate ABI; they do not execute the inherited castle body.

The synthetic Windows debugger suite requires an x86 MSVC environment and
`CLASH_DEBUGGER_INTEGRATION=1`. It only loads marked artificial PE32 fixtures,
keeps them paused without executing their entry instructions, and checks that
instruction pointer and memory remain unchanged. The
[explicit seven-case result](../../reports/ordinary-castle-entry-matrix-engine-20260926-c.json)
records passing file/block execution, actual relocation, corruption, omitted or
reordered chunks, and unreadable memory. The
[initial failed engine report](../../reports/ordinary-castle-entry-matrix-engine-20260926-a.json)
and [first corrected report](../../reports/ordinary-castle-entry-matrix-engine-20260926-b.json)
remain separate artifacts; harness exit zero alone does not mean verifier pass.

The [corrected original-backed matrix report](../../reports/ordinary-castle-entry-matrix-verification-20260926-b.json)
completed all 12 profile/resolution cases on 2026-09-26 in 945.860 seconds.
Its `completed` and `passed` fields are both true. It records parent and candidate
hashes, derived entry addresses, exact patch replay, unchanged relocations,
probe identity and the source snapshot. All 560 captured source identities, the
original executable hash and the pre-commit HEAD remained unchanged through
the batch; candidates and generated probes were built only in memory. The
[interrupted first matrix run](../../reports/ordinary-castle-entry-matrix-verification-20260926.json)
remains failed after the LF verifier defect was discovered. Its eight completed
construction cases do not establish command-file execution or a complete matrix.

A one-case in-memory preflight writes no bundle:

```powershell
python -B tools/build_ordinary_castle_entry_matrix_candidate.py --original C:/Clash/clash95.exe --profile completehd --resolution 1280x720 --preflight
```

An explicit `--output` instead creates a new candidate, manifest and verifier
under C:/ClashTests. Existing bundle members, repository destinations and
symlink/junction paths are rejected. Check disk reserve first. No command here
launches Clash95 or supplies runtime approval.

## Remaining acceptance

Construction, gate execution in synthetic memory and debugger command parsing
are separate evidence classes. They do not prove ordinary input, coherent
castle/building rendering, normal root return, surface restoration, balanced
allocation/free, native owner restoration, visible composition or promotion.
The exact-1024 inherited-entry suite now passes all 15 methods, but a fresh
runtime must still verify exit/free restoration and every interior. The deleted
C:/ClashTests and C:/ClashCaptures runs cannot supply current screenshots.

Keep regenerated bundles bounded. Regularly inspect owned inactive intermediates
for cleanup under the root guide's disk policy, retaining required manifests,
source provenance and unique failing diagnostics. Do not silently turn missing
raw files into current verified evidence.

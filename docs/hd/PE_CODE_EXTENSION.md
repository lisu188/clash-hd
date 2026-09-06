# Additive storage for partial-tile validation code

Status on 2026-09-05: the offline [builder](../../src/patcher/pe_extension.py)
and its [fourteen fixtures](../../tools/test_pe_extension.py) pass. It returns
bytes and exact change records in memory, optionally including explicitly
supplied hook patches. It does not write an executable, integrate a stage into
the main patcher, change the stable stage, or establish runtime correctness.

The partial-tile renderer has outgrown the existing small verified caves.
The builder allocates a separate `.hdcode` section instead of assuming another
zero-filled region is unused game state. The original PE has seven sections,
`SizeOfImage=162000h`, image base `00400000h`, and 512-byte file/4096-byte
section alignment. The next code VA is therefore `00562000h`. Its new 40-byte
section header occupies file offsets `280h..2A7h`, before the diagnostic
scratch at `300h`; all new header bytes must originally be zero.

The public `extend_combined_candidate` entry accepts the known original bytes,
candidate bytes, expected candidate and patcher-source SHA-256 values, the
combined validation stage, canonical resolution, emitted code/VA, and explicit
relocations. It reconstructs the complete candidate from the pinned patcher
recipe, verifies every original patch byte and nonoverlap, and requires exact
candidate equality. A supplied SHA alone cannot admit arbitrary candidate edits.

The new section is executable/readable and not writable. It contains code,
alignment padding, a copy of the complete original base-relocation directory,
and new HIGHLOW blocks for declared absolute address fields. Original sections,
their headers, their raw contents, and the old relocation bytes are preserved.
Changes are limited to NumberOfSections, SizeOfCode, SizeOfImage, the relocation
directory reference, the new section header, and appended bytes. Each edit
records its file offset, RVA/VA, exact old/new bytes and purpose; appended bytes
have an empty old span at the verified original file end.

This follows the [Microsoft PE format](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format):
section file offsets and RVAs differ, section/raw extents have distinct
alignment rules, and HIGHLOW rebasing adjusts a 32-bit absolute field. Relative
branch displacements are verified but are not converted into HIGHLOW entries.
The known Watcom image uses zero VirtualSize fields, including an unbacked BSS
extent with a nonzero size and raw pointer zero. The mapper recognizes BSS as
memory and refuses to treat its addresses as file-backed bytes.

Validation rejects unsupported or malformed layouts, nonzero new header space,
overlays/signatures, invalid alignment/overflow, missing/duplicate/overlapping
relocations, unmapped targets and mismatched relocation values. Its independent
fixture parser maps the output and simulates positive and negative rebases,
checking that only declared absolute fields change. Tests also reconstruct
800×600, 1024×768 and 802×602 combined candidates from the actual known original,
and inspect the existing v5 candidate read-only. All 32,435 original HIGHLOW
entries are retained by the allocation-only path. Five additional fixtures
exercise explicit hook edits and independently demonstrate the jump corruption
caused by retaining a displaced operand's old relocation.

The emitter must supply complete relocation metadata, including cloned vtable
entries and address-valued immediates. This builder deliberately does not infer
missing relocations by scanning arbitrary instruction bytes. It also does not
prove that pre-existing patched operands or future overwritten hook spans have
correct relocation entries; integration must audit those separately.

Read-only inspection has already identified two concrete hook operands that
need relocation changes during installation:

| Proposed hook | Exact displaced bytes | Existing HIGHLOW field |
| --- | --- | --- |
| Full redraw `004187A0`, file `00017BA0` | `83 3D 90 69 52 00 00` | `004187A2` |
| Full presentation `004187B7`, file `00017BB7` | `A1 FC 4C 54 00` | `004187B8` |
| Incremental entry `00418A90`, file `00017E90` | `53 51 56 57 55 83 EC 08` | None in these eight bytes |

A relative jump replacing either absolute operand must not retain the old
HIGHLOW at that location. Otherwise rebasing would alter jump displacement
bytes. Replayed absolute operands in the trampoline need their own declared
HIGHLOW fields. The following original incremental instruction's operand at
`00418A9A` lies outside its proposed hook and must remain intact. These are
observed file-format prerequisites, not runtime proof.

`extend_combined_candidate_with_hooks` now supports those operations in memory
under an explicitly distinct validation-stage identity. It accepts exact
`HookPatch` file-offset/RVA/VA/old/new records and explicit replacement-field
relocations. The caller must supply exactly the old HIGHLOW entries wholly
displaced by its hook spans: missing or extra removals, duplicate entries and
partial overlaps fail closed. The builder merges the new relocation directory
by page, retains every unrelated original fixup and keeps the original raw
`.reloc` bytes unchanged. Every removed operand's old bytes remain in metadata.
The original allocation-only API and its verbatim table-preservation tests
continue to pass. Actual hook semantics still need their own native ABI tests
and runtime validation.

The new eighth section intentionally fails the current diagnostic probe's
exact seven-section contract. A future installed rendering stage needs its own
bound probe contract and full byte report. Do not relax the existing diagnostic
to accept arbitrary images. `installation_ready` remains false until the
caller hooks, native rendering behavior, required evidence and promotion
decision are handled under their existing boundaries.

Keep returned executable bytes and bulk relocation/edit payloads outside Git.
Use compact hashes, identities, counts, and reviewed patch metadata for durable
reports; the builder's in-memory result is not a request to track a game binary.

# Primary and cursor checkpoint query ledgers

[`modal_primary_checkpoint_ledger.py`](../../tools/modal_primary_checkpoint_ledger.py)
is an offline reader for a new, explicit text-stage capture contract. It admits
only `-completehd-modalprimarytext-validation`, recipe
`owned_modal_primary_text_v1`, and the six existing fixture resolutions. It
does not launch a process or modify any input or artifact.

This is preparation for host integration. No host currently produces this
fresh receipt contract. The canonical primary-v1 four-checkpoint receipts and
the frozen slots-v2 reader retain their existing formats and evidence. They
cannot be relabeled as new checkpoint-ledger receipts.

## API and scope

```python
audit_checkpoint_ledger(
    receipt,
    stream="primary",  # Or exactly "cursor".
    capture_dir=capture_directory,
    expected_binding=authenticated_outer_binding,
)
```

The caller must obtain `expected_binding` from its own authenticated candidate,
host plan and paused trace. There is no arbitrary read-list parameter. The
reader checks exact agreement with those expectations; it does not independently
establish that the named process was alive, that the trace is semantically
valid, or that a native memory-query call actually occurred.

The binding has exactly these fields:

| Field | Required value |
| --- | --- |
| `stage`, `recipe_revision`, `resolution` | The text-stage identity and one of the six supported fixture resolutions |
| `candidate_sha256` | A lowercase SHA-256 from the outer candidate context |
| `run_id` | A bounded run identifier |
| `checkpoint` | Exact `name` and integer `index`: `full-published`/0, `placeholder-before`/1, `placeholder-after`/2, or `final-ready`/3 |
| `capture_index` | Integer 1, 2 or 3 at every checkpoint |
| `game_identity` | Exact `process_id`, absolute executable `path`, `creation_filetime`, `creation_utc`, and `handle_retained=true` from the outer retained-handle observation |
| `trace` | Exact paused-prefix artifact `path`, byte count and SHA-256 |

The UTC creation timestamp must agree with the integer Windows FILETIME. This
consistency check does not authenticate a live process handle. The reader hashes
the actual trace file; trace semantics remain the outer validator's responsibility.

The directory must be outside the active checkout and end with
`<checkpoint>/capture-N`. Its parent's `capture-prefix.log` is the bound trace.
All file paths must be absolute, with no reparse-point ancestors or aliases
between distinct artifact files. Files and pinned sources are checked again
before returning, including file identity and timestamps as well as bytes.

Each result covers one sample. The outer host must require three consecutive
captures and compare stability at every visual checkpoint. Accepting sample 1,
2 or 3 does not establish a stable pair or a complete capture triplet.

## Fresh receipt and ledger format

The receipt has exactly `revision`, `region_scheme`, `stream`, `binding`,
`reads`, `regions`, and `query_ledger`; a primary receipt additionally has
`pixels`. Its revision is `modal_primary_checkpoint_ledger_v1`, and its region
scheme is `primary_virtual_query_ledger_v1`.

The ledger filename is `primary-query-ledger.jsonl` or
`cursor-query-ledger.jsonl` in the individual capture directory. Its artifact
record contains `path`, `bytes`, `sha256`, `records`, and `scheme`. The reader
requires a hash-bound, nonempty UTF-8 JSONL file with LF line endings and a final
newline, at most 32 MiB and 65,536 rows. Duplicate JSON keys, non-finite values,
blank lines and non-object rows fail. Typed comparisons keep integers distinct
from booleans and floating-point values.

The first row contains exactly `kind="header"`, `revision`, `scheme`, `stream`,
the complete `binding`, `page_size=4096`, and `mbi_bytes` of 28 or 48. Historical
headers without the new binding and revision fail.

Each query retains the existing raw-query shape: `kind="query"`, `read_index`,
`query_index`, requested artifact `path`/`address`/`bytes`, `cursor`, requested
and returned MBI byte counts, and the complete returned region. A completed read
is `kind="read"`, its `read_index`, and the exact artifact receipt including
path, address, byte count and SHA-256. Every requested byte must be covered by
ordered, successful queries before that completed read. Failed, missing,
reordered, repeated or extra query/read rows fail; a supplied certificate cannot
hide them.

## Closed read sequences

Primary samples require these nine reads before pixels and the same nine after
pixels, for **19 total reads**:

| Order within each phase | Name | Bytes |
| --- | --- | --- |
| 1 | `primary` | 220 |
| 2 | `backend` | 176 |
| 3 | `surface_full` | 32 |
| 4 | `palette` | 1,036 |
| 5 | `proxy_header` | 512 |
| 6 | `proxy_getpalette` | 83 |
| 7 | `surface` | 4 |
| 8 | `surface_vtable` | 144 |
| 9 | `palette_vtable` | 28 |

The middle pixel artifact is `primary.raw`, exactly width times height bytes.
Metadata filenames are `primary-before-<name>.raw` and
`primary-after-<name>.raw`.

Cursor samples require these nine reads before and after the enclosing capture,
for **18 total reads**:

| Order within each phase | Name | Bytes |
| --- | --- | --- |
| 1 | `state` | 68 |
| 2 | `descriptor` | 40 |
| 3 | `resource` | 4,112 |
| 4 | `sprite_header` | 10 |
| 5 | `backing_header` | 188 |
| 6 | `backing_pixels` | 4,096 |
| 7 | `barracks_pointer` | 4 |
| 8 | `barracks_resource` | 4,112 |
| 9 | `placeholder_sprite_header` | 10 |

Cursor filenames use `cursor-before-<name>.raw` and
`cursor-after-<name>.raw`, except `barracks_pointer` is written as
`barracks-pointer`. This order matches the canonical host's actual reads; that
host inserts the barracks pointer into its receipt dictionary last, which does
not change when the pointer was read. Paired before/after artifacts must have
identical addresses, byte counts and hashes.

## Certificates and failure preservation

The only reused implementation is the pure `region_certificate` logic in the
source-pinned `modal_slots_primary_capture.py`, together with its frozen primary
reader dependency. Neither frozen file is modified. The new reader independently
validates every query, its requested range, full returned attributes and MBI
counts before reconstructing the disjoint certificate.

Compatible nested query tails remain valid. Overlaps must agree on state,
protection, allocation base, allocation protection and type. Unreadable or
uncommitted pages, gaps, invalid page boundaries and 32-bit wraparound fail.
Both primary and cursor receipts must contain the exact complete certificate;
cursor region coverage is never optional.

The reader raises `LedgerError` on rejection. Once a ledger has passed file
hash/size and bounded row-count admission, `error.diagnostics` retains its bound
path/hash and all raw ledger rows, including malformed JSON and rejected queries.
Excessive JSON nesting is retained as a row parse failure, together with all
following rows. A file exceeding the 65,536-row limit retains its bound path/hash
without expanding the rows into diagnostics. Files rejected at earlier admission
remain untouched on disk. Future host integration must append
and close each raw query before checking it or attempting the read, and retain
partial ledgers in the failed-run summary. The offline reader cannot recover a
query that the host never recorded.

A successful result sets `ledger_valid=true` only. Source authentication,
live-process authentication, runtime acceptance, primary composition, manual
input and promotion flags remain false. Pointer-chain checks, proxy layout,
artwork comparison, rendered text placement, cleanup and three-capture stability
need their separate outer audits.

## Focused verification

```powershell
python -B tools/test_modal_primary_checkpoint_ledger.py
```

The 2026-09-19 run passed **19 tests in 11.833 seconds**, without skips.
It covers both streams, six resolutions, both MBI layouts, all checkpoint/sample
indices, compatible nested and multiple-query reads, negative sequence and
identity cases, strict JSON, mandatory cursor regions, artifact aliases and
file/source drift. A follow-up review reproduced an uncaught JSON nesting
failure; the reader now reports it through `LedgerError` while retaining all
admitted rows. Additional fixtures cover deeply nested arrays and objects and
bounded rejection of excessive row counts. The 2026-09-24 rerun passed
**21 tests in 17.007 seconds**, without skips. These are synthetic file-backed
checks; they do not provide game-runtime evidence.

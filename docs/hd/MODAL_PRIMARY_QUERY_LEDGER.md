# Primary query ledger, fresh v2 capture contract

The primary capture host now prepares `slots_cached_primary_v2` packets and v2
plan, snapshot and triplet receipts. Their required memory observation scheme
is `primary_virtual_query_ledger_v1`. The game candidate recipe and frozen
`tools/modal_slots_primary_surface.py` reader are unchanged.

`VirtualQueryEx` groups pages beginning at the requested page. A later query
can therefore return a contained suffix of a previous range. Its returned
byte count and every region attribute remain observations that must be
validated. See Microsoft's [VirtualQueryEx documentation](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualqueryex)
and [MEMORY_BASIC_INFORMATION fields](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-memory_basic_information).

Each fresh `capture-N/primary-query-ledger.jsonl` is created exclusively. The
host appends and closes each query record **before** validating it or calling
`ReadProcessMemory`. Records contain the requested read path/address/count,
ordered read and query indexes, query cursor, requested and returned MBI byte
counts, and the unmodified returned BaseAddress, RegionSize, AllocationBase,
AllocationProtect, State, Protect and Type. Every repeat survives. Completed
reads add their exact file path, address, byte count and SHA-256. The first row
binds the held process identity, run, paused trace, page size and host MBI size.

The host checks each read for committed readable page coverage and rejects
gaps, overflow, invalid pages or contradictory overlapping attributes before
RPM. A deterministic disjoint certificate joins only compatible overlapping
or adjacent regions. Compatibility includes allocation base, allocation
protection and type; current readable protection alone is insufficient.
Neither the raw ledger nor the source observations are normalized or replaced.

The consumer hashes and parses the actual ledger, rejects duplicate JSON keys
and incomplete records, validates every ordered query, and requires exactly
the nineteen expected completed reads: nine headers before pixels, pixels,
and nine headers after pixels. It independently reconstructs the full-attribute
certificate and requires exact equality with the receipt. Only this checked
certificate is projected into the frozen reader's four-field `Region` type.
An extra, missing, failed, contradictory or unaccounted query cannot be hidden
by supplying an otherwise plausible certificate.

Partial ledgers remain on disk when capture fails before a snapshot receipt is
returned. The final run summary binds every existing partial ledger by path,
byte count and hash after task-owned cleanup. No completed snapshot or runtime
acceptance is inferred from that preservation.

Historical v1 receipts retain direct strict frozen-reader checks. Full v1
replay requires its frozen producer sources; current preparation and probe
reconstruction require v2, preventing a coordinated receipt-version downgrade.
The failed
1080p F run of 2026-09-13 remains unchanged and failed: its nested queried
ranges `[0420d000,0429f000)` and `[0429e000,0429f000)` are diagnosis evidence,
not retroactively generated v2 proof. PR82's compatible range union did not
record every query or authenticate those observations in the consumer; this
fresh contract closes those provenance gaps without repinning historical runs.

Validation uses synthetic consumer files and extracted production PowerShell
functions with managed query/RPM stand-ins. It covers contained/repeated and
multiple-page queries, each differing overlap attribute, failed-query
preservation, precise artifact binding, coverage gaps, malformed/truncated
ledgers, MBI counts, invalid ranges, and mixed v1/v2 receipts. No fixture
launches the game or produces runtime, visible, manual-input or promotion proof.

# Memory-query provenance in the four-checkpoint primary capture

Read-only review on 2026-09-19 of the separate, concurrently developed
four-checkpoint implementation in `C:/Users/andrz/git/clash-hd`. The reviewed
files and SHA-256 values were:

| Source | SHA-256 |
| --- | --- |
| `scripts/cdb/run_modal_primary_capture.ps1` | `86bf334846cbc51e8a27c84d51e40522a44dd004570ffc2ccd1eefb870f66e0e` |
| `tools/modal_primary_capture.py` | `cc81240e799371e11e8e075ee7269a4eb398eba77a68bfc0a394fbe6a7408e3e` |
| `tools/modal_primary_surface_audit.py` | `67f045205fffb427c98016f30f07dc99c514c608a30732d8a0f6bbd343155908` |

The host records `full-published`, `placeholder-before`, `placeholder-after`
and `final-ready` checkpoints. This review did not edit those sources, launch
or inspect the live game, modify artifacts, or evaluate rendering correctness.
Existing v1 receipts, failures and source-bound results remain unchanged. A
new query-ledger contract cannot be assigned retroactively to their evidence.

## What the current region handling establishes

`Read-PrimaryArtifact` (host lines 615-638 at the reviewed hash) collects
`address`, `size`, `state` and `protect`, keyed by returned base address.
The host normalizes compatible overlaps before passing a disjoint certificate
to the strict frozen reader. Primary and cursor receipts retain the resulting
certificate and the dictionary's region observations (lines 735-737 and
797-798). This representation can describe legitimate nested query tails.

`region_set` in `modal_primary_surface_audit.py` (lines 109-134) independently
reconstructs the four-attribute union when observations are supplied, and
compares it with the receipt certificate. The outer audit calls `paired_reads`
for primary samples as well as cursor samples. Thus the outer audit does check
provided primary observations; the issue is incomplete original observations,
not an absence of any union validation.

## Remaining provenance gaps

- Query results are checked before being recorded. Invalid or failed queries
  therefore have no durable raw-query receipt. A dictionary also overwrites
  repeated base addresses. It cannot preserve every returned record or its
  chronological association with a read.
- The four recorded attributes omit allocation base, allocation protection and
  type. Query cursor, requested artifact/range, and requested/returned MBI byte
  counts are also absent. The consumer cannot detect conflicts confined to
  those missing attributes or reconstruct each exact read's query coverage.
- `region_set` accepts absent observations. More specifically, `paired_reads`
  (line 139 onward) makes all region coverage checks conditional on the receipt
  containing `regions`. A cursor receipt without `regions` skips this check.
  The primary snapshot later reaches the strict reader and requires its own
  regions, so the omitted-region finding applies to cursor coverage.

These are source-review findings, not observed faults in the concurrent run.
No negative fixture was executed against the original checkout during review.

## Bounded integration for a new contract

Keep the existing v1 protocol and evidence reproducible. After its upstream
checkpoint is available, introduce a distinct fresh receipt/contract revision
that requires the append-only, hash-bound
[`primary_virtual_query_ledger_v1` contract](MODAL_PRIMARY_QUERY_LEDGER.md)
at each applicable checkpoint and capture. Write every complete raw query
before checking it or attempting the read, including rejected queries. Bind
the ledger to the checkpoint trace prefix, process identity and artifact reads;
preserve partial ledgers and their hashes in failed-run summaries.

Primary snapshots require the existing exact **19 reads**: nine before,
primary pixels, and nine after. Cursor snapshots require an explicit exact
**18-read** contract: nine before and nine after. Within each cursor phase the
actual host call order is state, descriptor, resource, sprite header, backing
header, backing pixels, barracks pointer, barracks resource, and placeholder
sprite header. Receipt dictionary insertion order is not a substitute for
that observed read order.

The frozen v2 primary consumer's `audit_query_ledger` deliberately fixes the
19-read primary sequence and filename. Reuse its reviewed pure full-attribute
certificate logic, but add a separately checked cursor sequence or an explicit
new bounded interface; do not modify frozen producers or silently feed cursor
receipts through the primary-only contract. Require cursor regions and their
ledger in the new revision, then independently reconstruct each read sequence
and its exact disjoint certificate.

Focused fixtures must reject omitted cursor regions, missing or reordered
reads, omitted contradictory query records, incomplete/truncated ledgers,
wrong artifact or checkpoint bindings, allocation-attribute conflicts, gaps,
invalid pages, wraparound and v1 substitution for the new revision. Include
extracted-host-function tests proving a rejected query is appended before the
failure and retained after cleanup. Compatible nested tails must still pass
without dropping any raw record. These checks establish memory provenance;
overlay-aware composition acceptance remains a separate claim.

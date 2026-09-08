# Initial paint and frame preservation review

Recorded 2026-09-05T19:48:46.323285+00:00. Compared the initial **3806 files**: **none missing**, **10 intentionally changed**, **3796 unchanged**, **27 new source/document/JSON files** before this review's own two outputs. No unexpected path changes were found.

The original executable, core patcher/partial adapters/PE emitter, base probe, shared Astra configuration and ignore rules retain their initial hashes. The previous screenshot inventory was copied byte-for-byte into a dated archive before its current update. Existing failures retain their original status.

Scoped Git diff and new-text whitespace checks pass, as do both documentation guard fixture suites. Initial-paint runtime source pins and all frozen frame source/fixture pins match the tested sources. This is a path/hash preservation review; the initial contents were not saved separately for a per-hunk diff.

The aggregate was not repeated here: its saved 2026-09-05T20:39:17+02:00 observation remains 164/166, failing only the long-soak and release-checklist gates. The new [frame preparation](four-sided-frame-preparation-current.md) passes 31 focused tests / 903 synthetic x86 executions, but remains uninstalled. Both actual captures retain the missing right/bottom frame.

The later read-only CIM process inventory was denied by the sandbox. No new absence assertion was made; the initial-paint report retains its previously recorded terminal receipts and their differing PID provenance.

No prior artifacts were deleted, no game files were tracked, and no commit/push or promotion was performed. Exact paths and before/after hashes are in the [JSON review](initial-paint-frame-preservation-review-current.json).

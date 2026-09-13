# Complete candidate manual attachment

`tools/complete_hd_manual_attach.py` is a separate observation adapter for an
already running, separately approved complete-v1 candidate. It leaves the
five-target planner and historical visual, map and modal producers unchanged.
Default preparation reads files only. There is no launch command, debugger,
input driver, automatic focus/window placement, process termination or global
cleanup path.

The adapter addresses the attachment gaps listed in
`COMPLETE_HD_HUMAN_OBSERVATION_PLAN.md`: an exact positive PID and creation
FILETIME, process image path/SHA, loaded module/code identity, local wrapper and
configuration bytes, HWND, measured client origin/size, and each actual target
point are bound to a saved reviewable plan. A fresh external user approval must
match that saved plan before Win32 or capture APIs initialize. A runtime switch
alone never supplies approval.

## Preparation inputs

The user or separately approved owner first supplies the existing process PID,
creation FILETIME, HWND and measured client origin. The adapter never guesses
them, searches other processes, starts the candidate to obtain them, or claims
that preparation has measured them. Execution independently checks them using
a retained query/read process handle. The process owner retains responsibility
for its original launch approval and eventual cleanup.

Prepare an external target file with exactly these fields:

- `schema`: `complete_hd_attachment_targets_v1`.
- `candidate_identity`: the exact shared complete manifest context identity,
  including stage, resolution, candidate/base SHA, recipe, metadata SHA and
  canonical probe SHA.
- `target_id`: one of the five existing manual checklist identifiers.
- `points`: one through 32 records. Each record has a unique bounded `id`, an
  integer logical `[x,y]` within the candidate client, and a `basis` file
  reference containing the absolute external `path` and its `sha256`.

The basis retains the actual target observation or source analysis for review;
an arbitrary file cannot establish a native hitbox. The adapter always records
`native_hitbox_accepted: false`. Unknown castle/menu/minimap targets remain
unimplemented until the target has been observed and bound; do not fill them
with historical pulse coordinates. Target JSON is capped at 64 KiB, rejects
duplicate keys, and cannot contain unbounded target counts or coordinates.

Use explicit measured values and existing files with this preparation interface:

```text
python tools/complete_hd_manual_attach.py
  --candidate-manifest <existing complete-v1 .candidate.json>
  --wrapper <same candidate directory/ddraw.dll>
  --configuration <same candidate directory/actual selected configuration>
  --target-file <external bounded targets.json>
  --pid <existing positive PID> --creation-filetime <measured creation FILETIME>
  --hwnd <measured HWND> --client-origin <measured X> <measured Y>
  --output-dir <new directory under C:/ClashCaptures> --run-id <unique identifier>
  --checkpoints 1 --interval-ms 1000 --duration-seconds 60
  --write-plan <new external plan.json outside the planned run directory>
```

This is an interface example with unresolved values, not a runnable session or
approval. Inspect the emitted plan, its saved SHA, targets, ownership and
limitations before requesting fresh approval. Checkpoints are bounded to
1 through 12, with three consecutive original-size captures per checkpoint;
the capture interval is capped at 300 seconds. Use another reviewed plan when
the HWND, placement, target or candidate changes.

## Approval and execution boundary

The external approval record follows the existing repository convention:
`record_kind: user_approval`, a real affirmative `approved` value, actual user
`approval_text`, timezone-aware `approved_at` and `expires_at`, and `identity`.
No command in this adapter creates, amends or supplies an approval record.
Unit-test approval objects are explicitly synthetic fixtures in temporary
directories and are never usable runtime evidence.

The approval identity must contain exactly the saved `execution_plan_sha256`,
`candidate_identity`, `attachment`, `input_method: manual_directinput`, and
`scope: capture_existing_process_only`. The plan SHA also binds wrapper/config,
target basis artifacts, source hashes, output path and runtime schedule. The
fresh interval cannot exceed 12 hours and must cover the complete bounded run
plus 30 seconds for closing the observation handle. Missing, stale, changed or
mismatched approval fails before constructing a Windows session.

Only after actual fresh approval, execution takes this form:

```text
python tools/complete_hd_manual_attach.py --plan <saved plan.json>
  --approval <existing actual user approval.json>
  --execute --allow-visible-runtime
```

The user operates the physical mouse and keyboard. This adapter never calls
an input API. It reuses the existing observation-only path's original-pixel
capture and target accessibility primitives, with new checks around every
capture. It does not invoke the historical shell harness or its PID-zero
launch path. It checks all four client corners, the center and every listed
target, with per-monitor coordinates and exact native client dimensions.
The approval/deadline check runs again after placement measurements and
immediately before a single native image-grab attempt. No inherited capture
retry can start a new screenshot beyond the permitted interval.
Window recreation, relocation, resize, process exit and target occlusion stop
observation; they never trigger automatic window movement or reacquisition.
The exact HWND is checked directly; the historical helper's fallback window
search is not used, even with a zero retry count.

## Loaded identity and evidence limits

The retained handle is opened only for query, synchronization and memory read.
Creation FILETIME and actual process image path are measured from that handle
before and after loaded module verification. Exact candidate and local
`ddraw.dll` module paths, module allocations and on-disk SHA values must match.
Headers, every immutable executable section, and read-only canonical probe
guard ranges are compared to the authenticated image with PE32 HIGHLOW
relocations applied at the actual load base. The exact canonical probe itself
remains bound to the reconstructed complete manifest.

Writable runtime state and loader-resolved imports must differ from their
prelaunch bytes during ordinary play. Those canonical writable-state guards
are counted separately and excluded explicitly. The adapter does not emit the
full startup probe pass marker, hash an imagined pristine live image, or claim
that live mutable state passed its initial-state guard. The stored executable
SHA describes the actual on-disk candidate; separate loaded-range hashes
describe the memory that was checked. Configuration bytes are pinned, but this
adapter cannot infer whether the wrapper consumed that file. Runtime memory
reads are observations of a running process, not an atomic debugger snapshot.

The immutable `capture-receipt.json` is written immediately after observation
and handle cleanup, retaining partial frames and the original runtime failure.
Offline tear analysis then produces a separate `summary.json`, preserving all
earlier failures. Unexpected native, capture, handle-cleanup and analysis
exceptions produce failed summaries as well. Screenshots retain exact paths/hashes and stage, resolution,
capture method, target and result labels. A suspected tear remains a capture
failure; no duplicate frame or identical pair clears it. Share actual frames
and inspect all four borders and the applicable controls.

`passed` means only that these bounded attachment/capture checks passed.
`manual_input_accepted`, `release_ready`, `runtime_ready` and
`external_process_cleanup_verified` remain false, including after successful
captures. Native callback behavior, actual human input, screen return, live
save continuity, eventual owner cleanup and release eligibility remain separate
requirements. This source implementation has no visible runtime validation.

Offline fixtures: `python tools/test_complete_hd_manual_attach.py`. They cover
relocated immutable code versus mutable state, changed code/wrapper/config,
stale/reused process identity, missing/stale/mismatched approval, inaccessible
actual targets, changed placement, bounded target inputs, exact three-frame
capture, partial failure preservation and handle-only cleanup. Every native,
process and image-capture boundary is synthetic in those fixtures.

Both preparation and execution reconstruct the candidate from the current
recipe sources. A retained manifest whose source pins differ from the checkout
cannot be reused by changing its hashes or merely regenerating this attachment
plan. Prepare a new complete builder bundle, or replay the retained plan with
its exact historical sources. The September 8 prepared 1080p bundle is a
historical identity; later source integration requires this freshness check
before any new observation plan or approval request.

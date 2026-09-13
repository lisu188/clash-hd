# Slots-stage hidden barracks capture

This separate consumer accepts only `completehd-modalslots-validation`, its
`owned_barracks_dirty_slots_v1` recipe, and a matching `.candidate.json` bundle.
It does not broaden the older modal or complete-HD consumers. The builder,
legacy stages and their failed artifacts remain unchanged.

The first concrete 1024x768 bundle is
`C:/ClashTests/hd-completion/modal-slots-1024x768-v1-20260908-foundation/clash95_slots_1024x768.exe`,
SHA-256 `8148cfeacf893e4b006ae5b09c71612e5ac0841f491397ca2c844c9397888515`.
Its manifest and canonical builder probe are adjacent. The current-source rebuild
at `C:/ClashTests/hd-completion/modal-slots-1024x768-v1-20260908-current/clash95_slots_1024x768_current.exe`
has identical executable and canonical probe bytes; its manifest SHA is
`209e9c2bbce819b338a862744ce22d69b984f2335cb5e0a823d7e0b0c5448d08`.
The original source-bound manifest remains unchanged. This document describes
preparation and checks; it records no repaired-pixel runtime pass.

## Explicit bounded claim

The host traverses a disclosed debugger-forced overview/barracks route. Optional
`construct_all` changes only the selected isolated castle availability bytes,
with original/changed observations. The native entry, artwork-load branches,
full blits, first present, thread, stack and owned native canvas are observed.

Breakpoint 102 observes the new helper after its actual dirty copy and before
destination translation. Exactly twelve ordered calls are required: x=126,197,
268,339,410,481 at y=75,206, native source, inclusive right=x+32 and bottom=y+64,
original destination=(x,y), owner thread, ESP=map-handoff ESP−212, slot return
`00432C10` and producer return `00432DE7`. No debugger counter substitutes for
these events. Missing, repeated, malformed, shifted or additional events fail.

Every original initial-map and modal failure is retained. The initial evaluator
receives one exact stage-token projection only after the full new candidate,
manifest, source and generated command file are authenticated; every other log
record is preserved. This is a reuse of the unchanged framed initial-map ABI,
not acceptance of a mislabeled old candidate.

At the first barracks present, the debugger stays paused. Three distinct native
640x480 and physical-resolution pixel pairs are read, each surrounded by exact
state, E0 and header reads. Each pair retains both independent strides. All six
raw files and repeated ownership headers must agree across captures. This proves
only a bounded native/physical mirror, not primary text/cursor composition.

The game and debugger are identified using retained handles, exact image paths,
parent and creation identity. Cleanup verifies both process absence and handle
closure, followed by hidden desktop closure. Killing the forensic first-present
run is process cleanup; it does not prove natural modal exit/destruction or map
return. The deadline is 300 seconds with bounded offline validators.

## Root-operated preparation and runtime

The capture script's default is a plan. `-Execute` is required to start its
hidden desktop. Supply a fresh isolated work directory for game writes; the
existing `C:/ClashTests/completehd-validation-20260908/workdir-1024x768` may be
used as a read-only asset source when preparing that work directory. Candidate
and output directories must not already exist. For example, after preparing
the fresh work directory:

```powershell
& scripts/cdb/run_modal_slots_barracks_capture.ps1 `
  -InputCandidate C:/ClashTests/hd-completion/modal-slots-1024x768-v1-20260908-foundation/clash95_slots_1024x768.exe `
  -CandidateManifest C:/ClashTests/hd-completion/modal-slots-1024x768-v1-20260908-foundation/clash95_slots_1024x768.candidate.json `
  -ProxyBuildManifest C:/ClashTests/completehd-validation-20260908/candidate-1024x768-d/ddraw_surfdump_proxy.build.json `
  -WorkDir C:/ClashTests/completehd-validation-20260908/slots-barracks-work `
  -CandidateDir C:/ClashTests/completehd-validation-20260908/slots-barracks-candidate `
  -OutDir C:/ClashCaptures/hd-completion/slots-barracks-1024x768-new-run `
  -Resolution 1024x768 -CastleIndex 0 -Availability construct_all
```

Review the concrete plan, then use the same arguments with `-Execute` for the
authorized hidden run. Outputs include `packet.json`, `plan.json`, the exact
command file, `cdb.log`, immutable `capture-prefix.log`, trace/final-trace reports,
`capture-1` through `capture-3` each containing `surface.raw`, `native-surface.raw`
and surrounding state/header reads, the first physical `surface.png`, and
`summary.json`. Failures and completed raw captures are preserved; a generated
summary does not mean success.

After cleanup, independently run:

```powershell
python tools/modal_slots_surface_audit.py --summary C:/ClashCaptures/hd-completion/slots-barracks-1024x768-new-run/summary.json
```

Keep its JSON output outside the repository. The audit rebuilds/re-evaluates the
exact trace and verifies raw paths, hashes, pointers, strides, repeated ownership,
process identities and cleanup. It requires native/physical equality over the
centered 640x480 canvas, zero pixels in all four outer regions, and actual nonzero
native artwork in each of the twelve portrait interiors. Matching blank images
cannot pass. The original 24,576 missing-pixel fixture remains a negative case.

Show the actual PNG with stage, 1024x768 resolution, hidden paused software-surface
method, and the audit result. Its palette and missing primary-only layers limit
the screenshot claim. Court, recruitment, peasants, real selection/input, primary
composition, return and release eligibility remain separate.

## Source port and checks

The observer/trace/host retain reviewed portions of these read-only source
snapshots from `C:/Users/andrz/git/clash-hd`, imported under new filenames:

- `tools/framed_modal_canvas_probe.py`: `52edf115a5240111a62882069fff548460116ad2d7ee7a06d775f25494c36fe6`.
- `tools/framed_modal_canvas_trace.py`: `2f0ef571acdbc6892c775cc97698d535b56355c8086080713d3dfec040a6d3ba`.
- `scripts/cdb/run_framed_modal_canvas_capture.ps1`: `8873f885d7a5405a8a570e70e3b09e31081dcbd339b33b9e92b465274b58d9ba`.

New code adds exact slots manifest/source binding, the twelve-copy observation,
triple captures, and the pixel audit. It removes the obsolete fixed-harness
digest in favor of packet-bound current startup source and exact regenerated
commands. It does not remove a trace record or change a failure into acceptance.

The first offline preparation failed at a 4,101-byte CDB line and is preserved
at `C:/ClashCaptures/modal-slots-prepare-20260908.json`. Compacting only whitespace
between late breakpoint-arm commands retained every observer/guard. The second
preparation passed with a maximum compiled line of 4,063 bytes; its preserved
packet predates later consumer source checks and must be regenerated for runtime.

The retained hidden run at
`C:/ClashCaptures/hd-completion/slots-barracks-1024x768-20260908-b/`
failed before any pixel capture. Its original `trace.json` reports
`slots loaded contract/scope missing, repeated, malformed or mismatched` even
though `cdb.log` lines 96 and 97 contain the exact required `SLOTS_CONTRACT_PASS`
and `SLOTS_SCOPE` records. The old case-insensitive `\bSLOTS_` scan also selected
line 101, the legitimate `MCAP_CONTRACT`, because its field value is
`protocol=slots_barracks_owned_canvas_v1`. It therefore compared three selected
lines against the two required startup records. This was a parser defect;
neither required startup event was missing.

The repaired scan recognizes whitespace-delimited record tokens, retaining
case-insensitive detection of malformed records and exact content/order checks.
It does not deduplicate observations or alter the producer. Read-only diagnosis
of that unchanged log passes its 32 modal records and twelve slot-copy records;
recompiling its saved packet produces the identical saved command file. These
diagnostic functions do not authenticate the full source context or authorize
host capture. The original failure, packet and source snapshot at
`C:/ClashCaptures/completehd-integration-20260908/source-snapshot-slots-barracks-b/`
remain unchanged. There are no pixels from this run to audit, and a fresh
source-bound run remains required.

The repair adds three synthetic startup regression groups covering the legitimate
protocol field, missing/duplicate/reordered/malformed records, and exact
revision/candidate/protocol values. All ten pure-Python capture tests passed on
2026-09-13. The full 13-test invocation also reached three existing extracted
PowerShell boundary tests, which failed under the restricted host's script
execution policy before their fixture bodies ran. That environment failure is
retained separately from the passing parser checks; no fixture starts a game or
debugger, and these checks provide no runtime or pixel acceptance.

The root's subsequent full fixture run outside that restrictive sandbox passed
all 13 tests on 2026-09-13, including the three extracted PowerShell mock tests.
It started no game, debugger, capture or input. The earlier environment failures
remain distinct from this successful source validation.

`tools/test_modal_slots_barracks_capture.py` covers exact/missing/duplicate/shifted
copy events, manifest/sidecar mismatch, wrong stages/resolutions, all four outside
regions, blank images, the original 24,576-pixel failure, PowerShell syntax without
execution, three distinct capture records, changed ownership and retained-handle
cleanup failures using synthetic native boundaries. No fixture starts runtime.

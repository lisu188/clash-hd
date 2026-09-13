# Slots-stage cached-primary capture consumer

This is an additive hidden observation consumer for the separate
`-completehd-modalslots-validation` candidate. It retains the candidate-bound
barracks route, native canvas, physical mirror and twelve dirty-copy checks,
then observes the proxy primary at the same paused boundary. It does not
change Complete HD v1 or the protected stable stage.

The entry point is `scripts/cdb/run_modal_slots_primary_capture.ps1`.
Its default returns an offline plan without creating a desktop, starting a
target, reading process memory or creating capture/candidate directories.
Only `-Execute` enters its hidden runtime path. The underlying route uses
the disclosed controlled barracks dispatch; this is not ordinary selection
or manual-input proof. This consumer adds observation breakpoints only:
no forced Lock, render call, target memory write or OS input is introduced.

## Supported proxy and exact source identity

`tools/modal_slots_primary_surface.py` is a byte-preserved port of
`tools/framed_primary_surface.py`, SHA-256
`d905d43e2781849ed54d862e78725af98f188b7d47ec3f5dae3796c01ee10442`.
The consumer pins that file. Its private FakeSurface/FakePalette layout
supports only proxy SHA-256
`b173a9dd4ce772eb5b56f341acdf4b329ed4ffdd638c1fce5cc37dd332804b70`,
with source SHA-256
`407d41d0d548e6217c6041181efb6466efa90f447110c5b8857bf92714ecb8eb`.

Use the genuine historical build manifest at
`C:/ClashTests/hd-completion/framed-minimap-v1-1024x768-20260906-031649/candidate/ddraw_surfdump_proxy.build.json`.
Preparation verifies its actual output bytes, recorded source bytes, current
source bytes and the pinned GetPalette implementation. Another build of the
same source, including the newer `2ff588…` proxy, is not supported by this
private-layout reader. Editing the manifest to name another binary does not
make that binary acceptable.

The slots candidate manifest remains mandatory. Its existing context builder
reconstructs the original-to-framed-to-modal-to-army-to-slots recipe and verifies
candidate/probe sidecars. The primary packet additionally binds its reader,
producer, host, exact native Lock bytes and historical proxy manifest.
Compilation and evaluation reconstruct the entire inherited probe plus the
additive observers; a rehashed arbitrary script is not accepted.

## Capture and acceptance boundaries

The host retains the exact debugger and child process handles, verifies child
path/parent/creation time, and launches on a hidden desktop using the
non-presenting proxy. It requests read/query, synchronization and owned-process
cleanup rights; it does not request memory-write or memory-operation rights.
Explicit x86 module enumeration uses the retained handle from the 64-bit host.

Before any pixel read, the initial-map trace, modal sequence, exactly twelve
slot events and primary Lock/ready sequence must all pass. Duplicate or
unmatched events stay in the log and fail their original gate. A successful
native full-primary Lock must follow this facility entry, return with the
expected stdcall stack adjustment, and match the current cached descriptor.
`MPRI_HOST_READY` is distinct from earlier map and physical-mirror readiness.

Three samples each contain the owned native 640x480 canvas, the centered HD
physical mirror and cached primary pixels. They also retain the native state,
E0 ownership, native/physical headers, primary backend/COM headers and vtables,
current attached palette, proxy header/GetPalette bytes and readable-memory
regions. Header/palette reads surround the pixel reads. Every read must return
its exact bounded count; changed ownership, pointers, module bounds, palette,
headers or any sample bytes fail acceptance. Each primary PNG uses that
sample's captured attached palette. The physical-mirror PNG uses the matching
first sample's attached primary palette to visualize its indexed pixels;
the receipt records that palette path/hash, sample number and primary-pixel
hash. This does not claim that the software mirror owns a separate palette
or that the visible wrapper's palette was observed. The independently written
global proxy palette file is not used to color these PNGs.

The triplet audit binds all paths, source hashes, candidate/probe identities,
process identities and cleanup receipts. It compares all three samples and
checks native-to-physical pixels, including the twelve slot interiors. It also
requires the full final log to preserve the paused prefix and re-evaluates the
entire final trace. A passing paused prefix cannot conceal a later trace
failure. A host failure remains a failure even if cached pixels are readable.

Debugger command errors are classified separately from native game failures.
The original failed prefix is retained before cleanup. Cleanup targets only
retained handles, stops the debugger first, checks absence and closes handles
and the owned desktop. The host always attempts a final summary after creating
its new output directory, including after parser failure. Offline child
failure JSON is retained without copying large prepared probes into the error.

## Reproducible preparation

Choose a new candidate directory and capture directory, plus an existing
isolated game work directory. Pass these to the script with the exact slots
candidate, its `.candidate.json`, and the historical proxy build manifest:

```powershell
powershell.exe -NoProfile -NonInteractive -File scripts/cdb/run_modal_slots_primary_capture.ps1 `
  -InputCandidate C:\ClashTests\<slots-bundle>\candidate.exe `
  -CandidateManifest C:\ClashTests\<slots-bundle>\candidate.candidate.json `
  -ProxyBuildManifest C:\ClashTests\hd-completion\framed-minimap-v1-1024x768-20260906-031649\candidate\ddraw_surfdump_proxy.build.json `
  -WorkDir C:\ClashTests\<isolated-game> `
  -CandidateDir C:\ClashTests\<new-primary-candidate> `
  -OutDir C:\ClashCaptures\<new-primary-run> `
  -Resolution 1024x768 -Route barracks -CastleIndex 0 -Availability existing_flags
```

These placeholders describe offline preparation, not an executed command or
runtime approval. Keep every run's raw captures and proprietary inputs outside
the repository. Freeze and retain the concrete plan before an authorized run.
Show actual native/physical/primary screenshots after capture, label the stage,
resolution and hidden method, and inspect all four margins and applicable
modal controls. Those controls are separate from ordinary-map action cells.

## Tests and unresolved evidence

Run `python -B tools/test_modal_slots_primary_capture.py` and
`python -B tools/test_modal_slots_primary_host.py`. The first reuses the frozen
reader's synthetic PE/memory corpus and adds sequence, manifest, whole-probe,
final-log and matched-triplet negatives. The second parses PowerShell without
executing its entry point and exercises extracted functions with replaced
native boundaries. No game, debugger, target process or live capture runs in
these fixtures. Optional original/proxy byte assertions only read existing
user-owned files and skip when those files are unavailable.

The retained `C:/ClashCaptures/hd-completion/primary6-barracks-20260906-104000/`
attempt failed initial-map trace validation at the recorded 498/501 events
and produced no primary pixels. It remains failed. This source implementation
does not reclassify that run or establish actual repaired primary composition.

Even a successful new triplet establishes only its bounded hidden native,
physical and cached-primary observations. Primary pixels still need a separate
source-backed placement/composition audit. Ordinary barracks input, all castle
routes, allocation failure, native exit/restoration/destruction, visible
composition, continuity, endurance and promotion remain separate requirements.

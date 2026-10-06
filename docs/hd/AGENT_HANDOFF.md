# Public project handoff

This file intentionally contains only source-level project state.

## Public repository state

- The repository contains independently authored patcher/launcher source,
  source-only tests, documentation, and minimal patch metadata.
- Original or patched executables, retail assets, saves, screenshots, runtime
  captures, debugger dumps, decompiler output, and disassembler exports are not
  public project artifacts.
- Public CI must not download or reconstruct the original game from another
  repository.
- Runtime validation is performed locally against a user-supplied lawful copy
  and its raw evidence remains outside source control.

## Stable public entry points

- [README](../../README.md)
- [Development and verification](DEVELOPMENT.md)
- [Launcher](LAUNCHER.md)
- [Resolution release matrix](RESOLUTION_RELEASE_MATRIX.md)
- [Release runbook](FINISH_LINE_RUNBOOK.md)
- [Contributor rules](../../AGENTS.md)

## Engineering state

The source tree remains the authority for implemented patch stages and
resolution behavior. `src/launcher/resolutions.json` is the user-facing
resolution registry. The patcher must verify the expected input executable
identity and old bytes before applying changes.

The four all-preset source constructors are
[`classic_all_presets_candidate.py`](../../src/patcher/classic_all_presets_candidate.py),
[`framed_all_presets_candidate.py`](../../src/patcher/framed_all_presets_candidate.py),
[`complete_hd_all_presets_candidate.py`](../../src/patcher/complete_hd_all_presets_candidate.py)
and [`modal_widgets_all_presets_candidate.py`](../../src/patcher/modal_widgets_all_presets_candidate.py).
Classic retains the actual scalar predecessor at 800x600 and 1024x768, and the
menu-widget predecessor at the seven wider presets. Framed retains its inset
four-border map/minimap and native modal fallback; it borrows no owned-modal
bytes from the other profiles.
The Modal Widgets successor carries the full owned slots, primary surface,
text and widget chain across the nine canonical presets. All use separate
validation identities and retain the frozen recipes. They do not install the
expanded-battle successor or change launcher defaults or stable status.

[`battle_profile_context.py`](../../src/patcher/battle_profile_context.py)
independently reconstructs those parents and derives profile-specific code/state
allocation plans. Classic and Framed need fresh RX and RW sections; Complete HD
and Modal Widgets can reserve a disjoint region in the authenticated existing
state page. The plan checks header bounds, zero state, declared fields and the
active relocation inventory. It installs no battle code. Dynamic state lifetime,
loader behavior, animation/dialog/exit routing and runtime acceptance remain
separate unfinished requirements.

[`battle_profile_lifecycle.py`](../../src/patcher/battle_profile_lifecycle.py)
emits an uninstalled lifecycle component from independently authenticated
profile parents. It stages a private native-size backing, checks the complete
inactive modal owner, and prepares separate cleanup paths for native allocation
failure and normal battle return. The allocation-failure path preserves native
termination. Normal cleanup retains a receipt until the native epilogue restores
the saved owner and globals. Synthetic x86 fixtures use explicit callback models;
they establish no native lifetime or healthy map-return proof. Drawing, input,
camera, animation, dialogs/results and all quit paths still need atomic
integration before an expanded-battle candidate can be installed.

[`battle_profile_routing.py`](../../src/patcher/battle_profile_routing.py)
prepares admission checks, private HUD target routing and native-size chrome
copies for those authenticated parents. It snapshots owner records, headers,
globals and arena geometry around its thread query. It owns no additional state
fields and emits only two uninstalled initial-target hook descriptions. The
synthetic pixel oracle covers the four frame edges, top/right sidebar and
bottom/right command slice while preserving field and interior bytes. These
buffers are not runtime captures. Field drawing, per-step presentation, input,
camera, dialogs/results and quit handling remain installation requirements.
Both lifecycle and routing exclude the complete 4096-byte state allocation
from dynamic surface, backing and battle ownership; unused page bytes cannot
become substitute heap receipts. Changed fixed owner/global receipts reject
before routing rereads cached heap headers after its thread query.

[`battle_profile_field.py`](../../src/patcher/battle_profile_field.py)
prepares separate terrain loops and coordinate queries for the authenticated
profile/routing chain. It checks the current world cell before calling the
original native tile routine, keeps 64-pixel tiles at `(32,16)`, and limits the
field to seven rows and the actual arena width. Drawing snapshots the complete
owner records, surface headers, globals and arena geometry around each tile
and ownership query. Receipt loss returns a distinct failure without another
tile call, presentation, native fallback or unauthorized target restoration.
These helpers install no hooks, clear no pixels and make no runtime claim.
The original tile's neighbor, unit/type and resource-provider accesses require
separate preconditions before atomic integration; a synthetic tile pattern
does not prove native artwork or array safety. Camera repair, clearing, HUD,
animation, input, presentation, dialogs/results and termination remain required.
The frozen v1 metadata overstates disabled native clipping. The original-backed
audit found seven Tile sprite sites with disabled clips, one Tile site with a
finite cell clip, and a finite 64-pixel cell clip on the ordinary Unit path.
Current v2 metadata records these separate cases. An arena adapter must
intersect existing clips with arena bounds; that integration remains unverified
and required before these loops can qualify a candidate. The v1 source remains
unchanged for reproducibility.
At 4K the frozen v1 Complete HD/Modal Widgets components occupy 112,481 bytes of
the authenticated 128 KiB RX reservation, leaving 18,591 bytes. Remaining
families need shared bounded helpers or a separately reviewed allocation
contract; an installer must reject overflow or missing families.

[`battle_profile_field_v2.py`](../../src/patcher/battle_profile_field_v2.py)
is a separate successor that preserves the frozen v1 emission and native
dependencies. It shares invocation capture/check helpers using the outer
stack frame. Each private helper consumes its own return address before the
outer loop handles failure; its private entrypoints require that frame and
cannot supply independent admission. Paired synthetic fixtures compare pixels,
coordinates, callback order, relocations and register/stack behavior across
all 36 geometries at two image bases, including ownership loss inside nested
calls. At 4K the complete chain uses 53,713 RX bytes for Classic/Framed and
72,993 for Complete HD/Modal Widgets, leaving 77,359 and 58,079 bytes
respectively in the same 128 KiB reservation. It installs no hooks and leaves
the same clipping, content, presentation and runtime requirements unfinished.

The matrix can authenticate these fixed source recipes separately from the
launcher-resolved recipes. Unadvertised presets, missing production verifiers
and missing expanded-battle evidence remain failures. The complete target is
all four profiles at all nine presets, with actual functional, composition,
human-input, continuity and endurance evidence on each final candidate. See
[the matrix contract](RESOLUTION_RELEASE_MATRIX.md) for the acceptance scope.

[`ordinary_map_read_replay.py`](../../tools/ordinary_map_read_replay.py) can
retain and replay every bounded ordinary-map read, including rereads and lease
checkpoints. Its context must come from the owning authenticated runtime host;
an artifact's own hashes and passing report flags cannot substitute. Successful
offline replay establishes recorded-byte consistency only. It keeps live lease,
native/manual input, full geometry, release and promotion claims false. Raw
records and failed-read diagnostics belong outside source control.
The hidden diagnostic can opt in with `--retain-raw-observations` only on an
independently reconstructed `--prepared-matrix-candidate` or
`--prepared-small-world-candidate` bundle. Legacy launcher hash receipts remain
outside this raw-retention path. See [Development](DEVELOPMENT.md) for its disk
allowance and evidence limits.

[`hidden_soak_process_lease.py`](../../tools/hidden_soak_process_lease.py)
prepares bounded retained-handle cleanup for a future hidden-soak producer.
The caller must independently authenticate its in-memory run authority;
artifact hashes and report flags cannot supply it. Process adoption checks the
PID, creation time, image identity and retained parent generation. Cleanup
attempts the debugger first and replays ordered source, adoption, termination,
wait, enumeration and close receipts. Unknown children of an exited parent,
PID reuse, incomplete receipts and native failures keep verification false.
The fixtures model Windows paths and API results; actual Windows behavior is
unverified. File-path hashing does not prove loaded candidate or probe bytes.
Complete host cleanup still requires the existing no-breakaway job host's
authenticated assignment, membership and drain receipts. This component
registers no production evidence lane and makes no runtime or release claim.

[`hidden_soak_frame_ledger.py`](../../tools/hidden_soak_frame_ledger.py)
prepares full-frame retention through caller-supplied read and storage adapters.
Its fixed map-idle schedule requires 241 periodic frames at 30-second intervals
from zero through two hours, followed by a separate terminal frame. Each
container retains original packed indexed8 bytes and typed read receipts;
failed reads and partial writes stay failures. Replay requires independently
retained run authority and collector bindings, checks every supplied byte, and
establishes archive consistency only. It supplies no native or filesystem
adapter. Coherent native capture, loaded candidate/probe identity, process
health, job cleanup and producer provenance remain required. Pending original
bytes after persistence failure remain in memory and are not durable evidence.
This host-monotonic schedule does not prove two hours of running time; a future
producer must measure running intervals and exclude capture pauses.
The budget includes all frames, an atomic temporary file, scratch, metadata
and external runtime assets, with the strict disk reserve checked before each
write. No endurance, runtime, manual-input or promotion claim is established.

[`hidden_soak_running_time.py`](../../tools/hidden_soak_running_time.py)
prepares a separate versioned transcript of supplied native QPC and debugger
pause/resume receipts. It credits only acknowledged GO intervals before a
break request, excludes command and held intervals, and debits each endpoint
by one counter tick. All 242 independently bound capture epochs and the full
two-hour running schedule are required; failed calls, missing transitions,
changed generations and shortened schedules fail. Original signed or unsigned
HRESULT values and QPC samples remain unchanged. This is receipt arithmetic,
not measured native endurance: producer provenance, host-awake coverage and
render/process health remain unverified. It adds 8 MiB for retained transcript
and atomic temporary bytes to the frozen frame-ledger budget; native-host and
other producer costs are additional. It installs no adapter or production
evidence lane and keeps runtime, manual-input and promotion claims false.

[`hidden_soak_loaded_image.py`](../../tools/hidden_soak_loaded_image.py)
prepares an initial-loader byte comparison for the four frozen all-preset
parent recipes, including Classic's distinct narrow and wide recipes. Public
admission reconstructs the exact candidate, typed metadata, canonical probe
and source closure privately; caller-selected spans or passing flags cannot
supply them. Replay requires every original PEB ImageBase, header and
executable-section read, complete HIGHLOW relocation fields and original
before/after query results in the held pre-probe epoch. Failed HRESULTs and
partial reads remain failures. Nonexecutable sections and alignment gaps are
explicitly excluded. Native read issuance, actual loader/header behavior,
runtime data and preferred/nonpreferred probe execution remain unverified.
This component supplies no reader, run or production evidence lane and keeps
loaded-candidate, whole-image, runtime, manual-input and promotion claims false.

[`battle_profile_stack_lease.py`](../../src/patcher/battle_profile_stack_lease.py)
prepares an uninstalled stack lease around the frozen V2 battle field. It binds
the owning thread, bounded native frame ancestry and exact CALL/RET operands,
copies primitive arguments and checks receipts after normal native return.
Fixed authorities and thread/control checks precede cached heap/world reads.
It preserves the original owner pages and RX reservation. A latched loss yields
outer status 2, but does not stop frozen V2's next Tile or unadapted native
continuations. Receiver/argument validity, physical-only clipping, standalone
callsite admission and RLE/provider cancellation remain unfinished. This is
source preparation without hooks, safe native replacement, runtime or promotion.

[`hidden_soak_loaded_read_session.py`](../../tools/hidden_soak_loaded_read_session.py)
prepares an adapter-only initial-loader read session. Canonical reconstruction
can precede launch through a privately issued, identity-bound read plan; copied
JSON or a caller-selected inventory cannot substitute. The original held-start
QPC tick remains fixed, including when preparation occurs after that tick.
The collector retains actual supplied owner sequences, all five ordered native
query results, breakpoint counts, architecture results and complete raw read
attempts before validation. A failed query with a stale zero, a partial read,
changed source or generation, or an expired 20-second hold stops collection.
Original failures and capacity debt remain retained; missing after-read phases
are never invented. Its raw/metadata allowance adds 33,619,971 bytes, including
an atomic metadata temporary, before native-host and other producer costs.
This supplies no native or storage adapter. Genuine initial-event, owner,
clock and coherent-read provenance remain unfinished. Source replay, pending
RAM and synthetic receipts cannot establish loaded-candidate, endurance,
runtime, manual-input, release or promotion acceptance.

Use the public boundary and cloud checks before focused source fixtures:

```powershell
python -B tools/check-public-boundary.py
python -B tools/cloud_check.py --mode cloud
python -B tools/test_classic_all_presets_candidate.py
python -B tools/test_framed_all_presets_candidate.py
python -B tools/test_modal_widgets_all_presets_candidate.py
python -B tools/test_resolution_release_matrix.py
python -B tools/test_battle_profile_context.py
python -B tools/test_battle_profile_lifecycle.py --require-machine-tools
python -B tools/test_battle_profile_routing.py --require-machine-tools
python -B tools/test_battle_profile_field.py --require-machine-tools
python -B tools/test_battle_profile_field_v2.py --require-machine-tools
python -B tools/test_ordinary_map_read_replay.py
python -B tools/test_hidden_soak_process_lease.py
python -B tools/test_hidden_soak_frame_ledger.py
python -B tools/test_hidden_soak_running_time.py
python -B tools/test_hidden_soak_loaded_image.py
python -B tools/test_hidden_soak_loaded_read_session.py
python -B tools/test_battle_profile_stack_lease.py --require-machine-tools
```

The optional original-backed constructor lane builds only in memory from a
user-supplied local executable. It supplies no runtime, loader, screenshot,
manual-input or promotion evidence. Keep every candidate bundle, runtime log
and capture outside the repository and preserve the disk reserve before use.

Historical runtime experiments, screenshots, raw debugger sessions, and
workstation-specific evidence that formerly accompanied this project are not
part of the public repository. Do not recreate them in public source control.

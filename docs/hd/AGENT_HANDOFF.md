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

`tools/resolution_recipe_authentication.py` privately reconstructs the legacy
and all-preset Complete HD recipes from a pinned 27-source graph. The matrix
captures its canonical source loader before public helper or builder aliases
can replace it, and checks source identity before and after reconstruction.
The legacy recipe retains its five supported presets; its successor supports
all nine. Byte, metadata and probe authentication supplies no runtime proof.

[`battle_profile_context.py`](../../src/patcher/battle_profile_context.py)
independently reconstructs those parents and derives profile-specific code/state
allocation plans. Classic and Framed need fresh RX and RW sections; Complete HD
and Modal Widgets can reserve a disjoint region in the authenticated existing
state page. The plan checks header bounds, zero state, declared fields and the
active relocation inventory. It installs no battle code. Dynamic state lifetime,
loader behavior, animation/dialog/exit routing and runtime acceptance remain
separate unfinished requirements.

[`battle_profile_context_v2.py`](../../src/patcher/battle_profile_context_v2.py)
is the versioned allocation successor for future complete re-emission. It
privately reconstructs the frozen parents and reserves 256 KiB of fresh RX and
64 KiB of fresh RW space for every profile and preset. The first RW page
protects a future 128-byte battle record; the remaining 60 KiB is an unpopulated
provider reservation with no proven record schema, capacity or lifetime.
Modal Widgets grows `SizeOfHeaders` from `0x400` to `0x800` in memory. An exact
old/new file-offset inventory covers section storage and supported COFF, line,
security and debug fields; unknown resources fail closed. Loaded RVAs and
HIGHLOW operands remain fixed. No new section, code, state, provider, candidate
file or hook is installed. Historical emitters must be re-emitted and fully
relocated for these new addresses before a complete installer can use them.
The original context and protected default remain unchanged.

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

[`battle_profile_lifecycle_v2.py`](../../src/patcher/battle_profile_lifecycle_v2.py)
privately reconstructs the versioned allocation context and re-emits the frozen
lifecycle at fresh RX/RW addresses. The bounded source transformation and
complete operand inventory retain original native callback targets and planned
whole-byte hook checks. The first 128-byte owned and inherited records are
compared completely; all remaining new RW bytes must stay zero because no
provider records exist. Nonzero inherited modal tail is explicitly unsupported
by this restrictive admission, and does not prove native dynamic-field lifetime.
Checks run after each modeled callback before following cached headers. The
component's maximum added helper stack is 456 bytes; its 4K code occupies 27,252
bytes for Classic/Framed or 45,962 for Complete HD/Modal Widgets. Those are
component bounds, not complete-chain capacity. Synthetic fixtures cover all 36
geometries at two image bases, including actual outer-adapter stack and null
failure routes with modeled callbacks. The optional original-backed lane
reconstructs only in RAM. No hook, section, provider or candidate is installed;
native lifetime, full battle integration and all runtime acceptance remain open.

[`battle_profile_routing_v2.py`](../../src/patcher/battle_profile_routing_v2.py)
re-emits the frozen routing after the privately authenticated fresh lifecycle.
It protects the complete new RX/RW spans and the separate inherited modal page,
checks full 128-byte records and exact-zero tails before cached accesses, and
rechecks after modeled thread callbacks. Query status zero requires exact virgin
records without a callback; owned/history/callback loss returns status two.
Neither status authorizes a native target write: both initial adapters restore
the incoming ABI and reach an explicit unsafe endpoint. That endpoint establishes
no production cancellation, healthy fallback or map restoration. Six routing
entries retain 1280-byte local frames with a complete typed operand inventory;
nested source allowances are not a full-chain or native capacity proof. Public
fixtures use modeled callbacks and synthetic pixel buffers, with the original
RAM lane separately opt-in. No hook, provider or candidate is installed. Frozen
predecessors, all runtime gates and the protected default remain unchanged.

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

The ordinary-map pause client retains original acknowledgment read errors.
While waiting for readiness, pause or resume, missing files and replacement
permission errors may retry only within that request's original absolute
deadline, with retained-owner and host checks on every iteration. A late valid
acknowledgment cannot publish a receipt. An acknowledgment read failure during
an active paused interval immediately revokes its authority; it cannot retry or
resume from a cached acknowledgment. Portable fixtures cover these paths.
Synthetic CI failures remain historical diagnostics, separate from game input,
runtime, endurance and promotion evidence.

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

[`hidden_soak_job_lease.py`](../../tools/hidden_soak_job_lease.py) prepares a
WIN64-only transcript of supplied native job receipts. It requires suspended
host creation, assignment and membership before resume; retained debugger and
candidate generations; complete original limit, PID and accounting buffers;
bounded termination/drain; and every owned handle close. Failed native calls,
unknown children, missing operations and cleanup debt remain failures, including
after a later successful retry. The complete original transcript is retained.
Its serialized transcript and atomic temporary add 8 MiB to other budgets.
The unchanged host does not emit this future protocol. Genuine native issuance,
per-frame/whole-run membership, durable storage and full no-breakaway cleanup
remain unfinished. The adapter must retain oversized originals before bounded
record construction. Replay establishes supplied-receipt consistency only and
keeps runtime, endurance, manual-input, release and promotion claims false.

[`hidden_soak_loader_native.py`](../../tools/hidden_soak_loader_native.py) prepares
a fixed x86 initial-loader read batch from privately reconstructed candidate
contracts. Its opaque request identities bind the exact source closure and read
inventory. The paired archive adapter retains original native callback, query,
QPC, generation and full-capacity read buffers, including failed and truncated
archives, before checking their supplied receipts. A separate Windows CI fixture
uses only a marked synthetic executable and requires actual initial-event reads
and independent target-handle adoption while that target still exists.

This preparatory batch executes no canonical probe, issues no GO, forces no game
callbacks and injects no input. Comparison takes place after termination, so it
cannot establish comparison during the native hold, whole-candidate loaded proof or healthy
runtime. Real instrumented ownership/job receipts, durable storage and integration
remain unfinished. The shared journal plus its complete known failure tail and
atomic metadata allowance adds 35,717,123 bytes. A second complete raw archive
copy needs its own additional allowance. Candidate/assets, compiler outputs,
independent receipts and unknown output debt are also excluded. Local source fixtures
launch no processes; native CI success cannot grant endurance, manual-input,
release or promotion acceptance.

[`hidden_soak_loader_expected.py`](../../tools/hidden_soak_loader_expected.py)
privately reconstructs the exact parent candidate, resolved recipe and canonical
probe before issuing opaque expected-image payloads. Narrow and wide Classic
keep distinct recipe identities. The bounded stream contains canonical metadata,
headers/RX chunks and whole selected HIGHLOW fields; no report boolean supplies
its byte authority. Fresh replay rejects resealed candidate/probe substitutions,
changed sources, capability clones and malformed or incomplete payloads. Source
loss after modeling publishes no chunks and retains the complete original.

Its exact maximum payload is 17,121,324 bytes. Payload plus atomic temporary,
existing native journal and a separate complete raw archive need 96,239,710 bytes
of known allowance. Assets, compiler, RAM, generation/job/clock receipts and
unknown original output remain additional costs. No filesystem/native adapter
or reserve bypass is installed. The preferred header ImageBase remains unchanged;
the PEB four-byte base read is independently mandatory. Nonexecutable data,
provider/RW/IAT regions and alignment gaps remain excluded.

The 2026-10-06 first audit reconstructed all 36 combinations at three modeled
addresses on its baseline source. After source-isolation and post-model rejection
repairs, five representative final-source admissions passed separately. These
RAM checks establish no genuine native generation, read coherence, comparison
during the hold, whole candidate/probe, cleanup, runtime, endurance, manual-input,
release or promotion acceptance. All broader claims remain false.

The synthetic debugger interpreter fixtures retain each pending case, exact
candidate and CRLF probe before launch under an explicit external CI artifact
directory. Original compiler outputs, stdout/stderr bytes and partial timeout
outputs remain separate from diagnostic text; unavailable output is distinct
from an observed empty buffer. The 35-second case deadline and native byte and
relocation comparisons remain unchanged. Fixed QPC/HRESULT boundaries locate
the last completed operation, and missing boundaries or failed clock/flush calls
fail the diagnostic. Logging failure cannot suppress the fallback termination
attempt. Eight pending small-world or seven pending Castle case names cannot
establish completion. All three inherited verifier workflows set their external
artifact directory in the execution step; it is not a job-level runner context.

PR #162 first exposed a Castle dependency failure before any native case ran,
then two workflows failed validation without creating jobs. Their diagnostics
remain retained outside the repository. The corrected source requires all five
Castle test methods and all seven distinct terminal case receipts; changing the
workflow does not turn either earlier failure into a pass.
The next head exposed LF-only diagnostic anchors on original Windows CRLF
output. The parser now accepts complete LF or CRLF lines while retaining their
original bytes and rejecting malformed or duplicate markers. Those failed run
reports remain failed; raw phase parsing after the fix is a separate check.
The Framed verifier emits one canonical identity header before its result. Both
are checked separately for identity, order and uniqueness; the header cannot be
mistaken for an extra result or omitted from its negative fixtures.

The retained PR #161 first-attempt timeout and its one unchanged successful rerun
are historical synthetic diagnostics, not proof of the timeout cause or game
health. These fixtures reserve 512 MiB for retained outputs plus 64 MiB for an
atomic write, above the strict free-space reserve; unknown oversized output
remains retention debt. Upload after hard runner loss is not guaranteed.
Production ownership, native cleanup and runtime acceptance remain separate.

[`battle_profile_content.py`](../../src/patcher/battle_profile_content.py)
prepares 28 fixed native body-site content reads around the authenticated stack
lease. It checks current terrain occupancy, unit indices/types, owner bytes and
unit coordinates after fixed owner, thread, stack and complete current field
receipts. Outside neighbors return the native empty sentinel without reading
occupancy or unit payload; malformed data returns a distinct failure. Coordinates
must fit the actual current arena, and owner bytes retain their full byte domain.
The value/status ABI preserves the other registers and flags but differs from
the original full or partial MOV destinations. Future adapters must handle failure
and restore those destinations before continuation; these helpers replay no
native instruction and install no hooks. Shared checks keep the same owner page
and RX reservation, leaving 50,001 bytes for Classic/Framed and 30,086 for
Complete HD/Modal Widgets at 4K. Count-entry reads, native continuation and
provider cancellation, clipping and atomic installation remain unfinished.
Synthetic body CALLs and in-memory reconstruction supply no runtime acceptance.

[`battle_profile_continuation.py`](../../src/patcher/battle_profile_continuation.py)
prepares the next uninstalled component: 28 original operand adapters, Count's
three early reads, 43 post-normal-return checks and two loss-aware field CALL
receipts. It restores the original full/subregister destinations and flags,
replays authenticated whole instructions and records all absolute relocations.
Complete pre-callback control snapshots prevent cached payload reads after
ownership loss; callback rejection preserves the captured incoming EAX. Unknown
control reaches an explicit UD2 endpoint and remains an installation gap.

At 4K it uses 20,260 continuation bytes for Classic/Framed and 20,319 for
Complete HD/Modal Widgets, leaving 29,740 and 9,761 bytes respectively in the
unchanged 128 KiB RX reservation. The final six-byte owner-CMP parser correction
changed no emitted bytes, relocation or immutable receipts across all 36 models.
Count's other callers and the native unit -1/type -1 predecessor paths are not
silently admitted: WORLD+821 overlaps header fields and is not a proven empty
unit record. Provider/RLE cancellation, receiver and argument validity, arena
clipping, full installation and healthy native return remain unfinished. No
hooks or expanded-battle candidates are installed by this preparation.

The separate `tools/hidden_soak_loader_compare_native.py` and
`tools/hidden_soak_loader_compare_native_adapter.py` v2 preparation compares the
immutable expected payload inside the original command-free loader hold. Its
shared private issuer registry rejects public inspectors, identical-binding
requests from other registries and reconstructed clones. Full requested native
read capacity and original HRESULT/count receipts precede each comparison.
Canonical headers, executable raw/zero extents and complete HIGHLOW fields are
checked at the separately read actual PEB base. Other image regions remain
excluded, and the preferred header ImageBase policy awaits native verification.

The earliest initial debugger callback supplies the sole 20-second epoch.
Comparison and the actual post-EndSession counter must fit that epoch; later
execution-status queries, waits, process times and closes do not acquire a new
deadline or complete lifecycle proof. Each journal frame retains original
WriteFile/FlushFileBuffers receipts. A footer cannot recursively attest its own
append/flush, and failed initial magic writes retain explicit output debt.

The known peak allowance is 112,870,182 bytes including request/payload atomic
temporaries, the failure-capable journal and a separate complete archive copy.
Compiler/source/object/binary outputs, candidate/assets, RAM, independent job
and generation receipts, and unknown native output debt require extra space.
The Windows CI fixture adds 256 MiB for its own compiler/report/source costs and
runs only a marked synthetic executable. Portable replay and that scoped fixture
establish no production producer provenance, full job/host cleanup, durable
storage, loaded-candidate/probe, map-ready, runtime/endurance, human-input,
release or promotion acceptance. No missing production verifier is registered.

`src/patcher/battle_profile_primitive_request.py` recomposes the baseline 74
continuation adapters and 13 primitive queries through one shared guarded
authority. The new owning thunk is 116 bytes with a separate 64-byte live
request; its 640-byte helper retains an 864-byte callback snapshot within a
1712-byte maximum stack extent. V2 field/lease frames and the protected owner
page stay unchanged. Original Tile/Unit/Tracking/Charge ancestry, whole argument
windows and native partial-register/flag outcomes remain authenticated.

Sprite requests preserve signed finite clips and the native all-minus-one
sentinel, with distinct malformed/empty/prepared status. Line requests preserve
native unsigned16 coordinates, Y-selected axis, plain inclusive and dashed
exclusive endpoints and absolute dash phase. Queries check the exact current
physical field receiver and reject literal primary state, but dereference no
sprite or provider payload and draw no pixels. Request records expire at their
own thunk RET; no arbitrary caller or previous frame padding supplies storage.

At 4K the recomposed RX totals are 106,495 bytes for Classic/Framed and 126,474
for Complete HD/Modal Widgets, leaving 24,577 and 4,598 bytes in the unchanged
128 KiB reservation. All hooks remain absent. Whole pre/post callsite integration,
native primitive replay, provider/allocation ownership, intracallback cancellation,
fatal shutdown and healthy restoration remain unfinished. Unknown control still
stops at exact UD2. Source/synthetic request acceptance is not installed expanded
battle, runtime, input, endurance, release or promotion proof.

`src/patcher/battle_profile_line_replay.py` prepares two direct calls to the
authenticated callback-free memory-line closure, while every installed hook
list remains empty. Its whole 8-byte and 11-byte call/cleanup windows replace
the overlapping planned post hooks at `430AD8` and `430B0A`. Clipped arguments
are duplicated for native RET8 without changing the original caller arguments;
native output registers and flags are retained before post-helper checks.
Both intrinsic paths require zero latched loss after complete thread/control
admission and before cached current-receipt reads. Unknown loss reaches UD2.
The public API captures a privately compiled canonical issuer and checks the
original SHA before reconstructing dependencies. Replacing public helper aliases
cannot choose its implementation; canonical source is checked before and after.

The final 4K RX totals are 106,941/126,920 bytes, leaving 24,131/4,152 bytes
within the same reservation and frame sizes. Source checks authenticate the
complete line/fill spans and memory vtable, and synthetic fixtures model pixel
writes and normal RET8. They do not execute the original native body or prove
Windows rendering. RLE/provider ownership, full battle installation, healthy
map return, runtime/input/endurance and promotion remain unfinished.

`tools/test_battle_profile_native_line_original.py` supplies a separate opt-in
CPU fixture. With the exact user-owned original, it executes the authenticated
line/fill instructions and relocated memory vtable at two image bases against
synthetic owned surfaces. It does not intercept the native line target or use
a callback to draw its pixels. Checks cover clipped arguments, native outputs,
flags, RET8, bounded stack ownership, small arenas, gutters and mutation paths.
Thread queries remain modeled and every production hook remains uninstalled.
Without `--original-backed` it runs only three authoring contracts and reports
`original_opcode_cpu_verified=False`; public CI uses that mode. The optional
local command below writes no candidate or capture and starts no Windows game
process. CPU proof supplies no sprite/provider lifetime,
Windows rendering, visual/input, endurance, release or promotion acceptance.

```powershell
python -B tools/test_battle_profile_native_line_original.py --original-backed C:/Clash/clash95.exe
```

Use the public boundary and cloud checks before focused source fixtures:

`tools/current_evidence_refresh.py` retains completed check results when a later
builder raises on missing or malformed local evidence. It records failed
collection diagnostics with the original exception and bounded traceback, then
continues the existing check order. An earlier collection exception remains
failed if a repeated check later succeeds. Missing private evidence stays a
failure; no approval, runtime observation or evidence document is synthesized.
The existing CLI overrides and default report/`--require-pass` exit policy are
unchanged. Focused collection fixtures mock the expensive builders; they do
not execute the aggregate or establish its actual evidence status.

```powershell
python -B tools/check-public-boundary.py
python -B tools/cloud_check.py --mode cloud
python -B tools/test_current_evidence_refresh_collection.py
python -B tools/test_classic_all_presets_candidate.py
python -B tools/test_framed_all_presets_candidate.py
python -B tools/test_modal_widgets_all_presets_candidate.py
python -B tools/test_resolution_release_matrix.py
python -B tools/test_resolution_recipe_authentication.py SourceTests
python -B tools/test_battle_profile_context.py
python -B tools/test_battle_profile_context_v2.py
python -B tools/test_battle_profile_lifecycle.py --require-machine-tools
python -B tools/test_battle_profile_lifecycle_v2.py --require-machine-tools
python -B tools/test_battle_profile_routing_v2.py
python -B tools/test_battle_profile_routing.py --require-machine-tools
python -B tools/test_battle_profile_field.py --require-machine-tools
python -B tools/test_battle_profile_field_v2.py --require-machine-tools
python -B tools/test_ordinary_map_read_replay.py
python -B tools/test_hidden_soak_process_lease.py
python -B tools/test_hidden_soak_frame_ledger.py
python -B tools/test_hidden_soak_running_time.py
python -B tools/test_hidden_soak_loaded_image.py
python -B tools/test_hidden_soak_loaded_read_session.py
python -B tools/test_hidden_soak_job_lease.py
python -B tools/test_hidden_soak_loader_native.py
python -B tools/test_hidden_soak_loader_native_engine.py EngineSourceTests
python -B tools/test_hidden_soak_loader_expected.py
python -B tools/test_hidden_soak_loader_compare_native.py
python -B tools/test_hidden_soak_loader_compare_native_engine.py EngineSourceTests
python -B tools/test_probe_engine_retention.py
python -B tools/test_framed_loaded_probe_engine.py ExecutableFixtureTests
python -B tools/test_battle_profile_stack_lease.py --require-machine-tools
python -B tools/test_battle_profile_content.py --require-machine-tools
python -B tools/test_battle_profile_continuation.py --require-machine-tools
python -B tools/test_battle_profile_primitive_request.py --require-machine-tools
python -B tools/test_battle_profile_line_replay.py --require-machine-tools
python -B tools/test_battle_profile_native_line_original.py
```

The optional original-backed constructor lane builds only in memory from a
user-supplied local executable. It supplies no runtime, loader, screenshot,
manual-input or promotion evidence. Keep every candidate bundle, runtime log
and capture outside the repository and preserve the disk reserve before use.

Historical runtime experiments, screenshots, raw debugger sessions, and
workstation-specific evidence that formerly accompanied this project are not
part of the public repository. Do not recreate them in public source control.

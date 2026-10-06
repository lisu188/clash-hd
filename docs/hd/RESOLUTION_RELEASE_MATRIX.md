# Mandatory resolution release matrix

The October 1 release target is all four launcher profiles at all nine presets:
Classic, Framed, Complete HD and Modal Widgets at 800x600, 1024x768, 1280x720,
1280x960, 1366x768, 1920x1080, 2560x1440, 3440x1440 and 3840x2160.
These are 36 independent acceptance combinations. The 802x602 partial-tile
fixture and arbitrary custom dimensions remain experimental.

## Read-only inspection and evaluation

```powershell
python -B tools/resolution_release_matrix.py
python -B tools/complete_hd_promotion.py --matrix-manifest C:/ClashTests/release/matrix.json
```

Both commands are stdout-only by default. Incomplete matrix evaluation returns
exit 2 without requiring `--require-pass`. An explicit `--write-json` creates a
fresh report and refuses to overwrite an existing file. Neither command runs a
game, debugger, input driver, capture tool or promotion operation.

The matrix index uses `resolution_release_matrix_v1` and immutable `path` and
`sha256` references. Every row identifies its `profile/WxH` id, candidate bundle
and original release index. Repository code selects the reconstruction recipe;
a manifest cannot select executable code or replace missing proof with passing
booleans. Candidate authentication and release acceptance are separate results.
Wide Classic uses its actual resolved menu-widget recipe rather than borrowing
the narrow Classic identity. A candidate or source change invalidates the
matching acceptance evidence.

The fixed source registry also admits `classic_all_presets_v1`,
`framed_all_presets_v1`, `complete_hd_all_presets_v1` and
`modal_widgets_all_presets_v1` for candidate reconstruction under their exact
profile, preset, stage and repository source identity. This is explicitly
reported as `unregistered_source_validation_recipe`; it does not substitute
for the launcher-resolved recipe or advertise a missing preset. Legacy
acceptance cannot qualify these successors, and the matrix remains failed
without all applicable production evidence and a promotion decision.

For `complete_hd_v1` and `complete_hd_all_presets_v1`, the matrix privately
executes the pinned `tools/resolution_recipe_authentication.py` source and
reconstructs its complete 27-source graph. Public builder and helper aliases
cannot choose the implementation. Canonical paths, reparse status, source
bounds, identity stamps and hashes are checked before and after reconstruction.
The legacy recipe retains five supported presets and its successor supports
all nine; the other recipes retain their existing reconstruction paths.

## Current implementation limits

The matrix adds mandatory inventory, exact candidate reconstruction, existing
complete-HD release replay and refusal of unsupported acceptance. The separate
source successors cover all four profiles at the nine presets;
they remain outside launcher registration. The matrix does not install the
expanded-battle successor, implement the fourteen missing runtime verifiers,
or supply fresh runtime evidence. Existing
legacy acceptance cannot qualify the required expanded-battle release.

The current catalog advertises 28 of the 36 preset combinations. Complete HD
and Modal Widgets each lack 1366x768, 2560x1440, 3440x1440 and 3840x2160.
The existing release evaluator implements two of sixteen production lane
verifiers; the remaining fourteen still fail explicitly. No new stable status,
whole-release pass or promotion is established by this checkpoint.

## Subsequent source preparation

`src/patcher/classic_all_presets_candidate.py` preserves the narrow scalar
and wide menu-widget recipes as distinct authenticated predecessors. Its
initial probe binds the final image to the selected predecessor and source
identity. The protected Classic 800x600 fallback and its launcher selection
remain unchanged. Inherited scalar patches do not declare every instruction
operand; exact source/byte reconstruction is not a complete loader audit.

`src/patcher/framed_all_presets_candidate.py` reconstructs the frozen Framed
map/input/minimap recipe with four inset bands and native modal fallback. An
independent second reconstruction binds every declared operand, hook and
typed metadata field before PE and original-to-final replay checks. Only the
known top-level legacy wall-clock field is omitted. It preserves the exact
source-owned DGROUP fallback and documents its deployment execution limit.
Both constructors retain their existing candidate bytes, add no battle hooks
and remain outside launcher registration.

`src/patcher/complete_hd_all_presets_candidate.py` provides a separately versioned
nine-preset Complete HD constructor. It reconstructs exact frozen producer
snapshots in a private namespace, verifies the final PE and declared relocation
inventory, and replays original-to-final byte records. The old six-size recipe
is unchanged. The new constructor remains outside the launcher registry; its
inherited initial-map probe uses preferred addresses and is not
the loader-rebased final verifier of the newer small-world chain. The Modal
Widgets successor in `src/patcher/modal_widgets_all_presets_candidate.py`
adds the complete owned slot/primary/text/widget chain under its own validation
identity. It authenticates supplied predecessor contexts instead of recursively
rebuilding the frozen six-size recipes, verifies each RX extension and inherited
owned state, replays original-to-final edits and rebinds the canonical initial
probe to the final image. Four RX layers leave fifteen PE sections and only one
additional header slot. Expanded-battle RX/RW allocation needs a separate design.
Constructor fixtures and source authentication establish no composition,
input, runtime or promotion acceptance.

`src/patcher/framed_battle_saved_views.py` supplies two uninstalled initial-camera
adapters. With complete phase-2 ownership admission, right-start X is actual
arena columns minus visible columns. Rejection preserves the original subtraction
and continuation. CPU fixtures cover all nine presets, small arenas, relocation
at two bases, registers, flags and inert state. Rendering, animation, HUD, input,
presentation and restoration must be installed atomically before these adapters
can become an expanded-battle recipe.

`src/patcher/battle_profile_lifecycle.py` supplies a separate uninstalled
ownership component for the four source successors. Its production API derives
addresses from a freshly authenticated profile parent; caller-supplied plans
and the old fixed army/state layout are not authority. Entry snapshots and
revalidates globals, thread and the inherited modal owner around private
allocations. A null native battle allocation retires the prepared private
backing before replaying the original fatal branch. Normal retirement restores
borrowed rendering before destruction and waits for the native epilogue to
verify restoration. Its guarded synthetic x86 fixtures cover all nine presets
and both image bases with explicit callback models. No lifecycle hook is
installed, and unimplemented quit interception or other battle hook families
remain required; this cannot supply runtime, healthy map-return or release proof.

`src/patcher/battle_profile_routing.py` derives its code and state addresses from
that fixed lifecycle and parent. Read-only prepared/bound admission checks and
private HUD targeting validate complete owner snapshots before and after the
thread query. Chrome composition copies native artwork to all four edges and
the two anchored sidebar slices; it preserves arena and unused interior pixels.
No state counters or fields are added. Two initial render-target hook
descriptions remain uninstalled. The independent synthetic pixel oracle is a
source contract, separate from runtime screenshots, final-wrapper composition
and healthy screen return. All remaining battle families must still be
installed together under a new candidate identity.
The complete state page remains protected from dynamic object aliases.
Protected-page fixtures also require changed owner/global receipts to reject
before cached heap headers or arena words are dereferenced after a callback.

`src/patcher/battle_profile_field.py` adds uninstalled terrain loops and
read-only coordinate queries, independently reconstructed from those fixed
parents. Native tile calls require strict bound ownership and a valid visible
world cell. The scoped physical target is restored only while the exact
invocation receipts remain valid. Receipt loss has a distinct result and never
permits another tile, fallback or presentation. Synthetic tile patterns check
call coordinates, native-size projection and untouched regions; they establish
no native rendering or artwork proof. The original tile's unchecked neighbor
and unit/type accesses, cold resource providers and fatal sprite paths require
separate validation and termination integration. The frozen v1 metadata's
blanket disabled-clipping statement is corrected by the current original-backed
v2 audit: seven Tile sprite sites disable clips, Tile `0x430733` keeps cell
bounds, and ordinary Unit `0x42FC1B` keeps a finite 64-pixel cell clip. Explicit
arena clipping must intersect those existing bounds and still requires
installation and verification. The v1 source remains unchanged. Clearing and
all remaining battle families still need one atomic installer before any
candidate can be qualified.

The separate `src/patcher/battle_profile_field_v2.py` successor shares private
invocation receipt helpers without changing v1, its native dependency spans or
the allocation contract. Nested failures return through each helper's own
CALL frame before the outer draw reports ownership loss. The synthetic tests
compare the two versions' pixels, coordinate results, callback order and outer
ABI at every preset/profile and two image bases, and verify internal and
external relocation operands. At 4K the shared version leaves 58,079 RX bytes
for Complete HD/Modal Widgets and 77,359 for Classic/Framed. Private helper
addresses are frame-dependent implementation details, not caller-selected
admission authority. This successor remains uninstalled and does not discharge
the native clipping, content/provider, quit or complete-family requirements.

`tools/complete_hd_evidence.py::audit_hidden_soak_raw` replays the existing
samples/log format and recomputes every supplied raw frame's hash and histogram,
sample timing and process growth. It remains a diagnostic helper: its overall
pass, candidate authentication, cleanup verification and release acceptance are
always false. The producer lacks complete-candidate loaded contracts, every-frame
raw references, PID/path/creation-bound termination receipts, an authenticated
candidate/probe/wrapper run envelope and the menu-idle ladder route. These gaps
cannot be filled by passing report booleans; all fourteen production lane
verifiers remain unimplemented.

`tools/hidden_soak_process_lease.py` prepares one part of a replacement
producer's cleanup contract. It retains handles rather than terminating by
reusable PID, checks parent generations, bounds adoption/reconciliation and
recomputes scoped cleanup from the ordered receipt stream. Its external run
authority must come from the fixed authenticated producer. Mocked tests do
not establish native process behavior, loaded candidate/probe identity or
genuine artifact provenance. Full host cleanup additionally requires original
no-breakaway job assignment, membership and drain receipts. The component
keeps host cleanup, runtime, manual-input, release and promotion claims false;
it does not fill or register any of the missing production verifiers.

`tools/hidden_soak_frame_ledger.py` prepares the replacement producer's complete
map-idle archive. Its fixed policy requires 241 periodic captures from zero
through 7200 seconds and one separate terminal capture, with a two-second
maximum lateness window. Source policy admits the nine presets and packed
indexed8 frames only; a changed native header or pitch remains a failure.
Typed read leases, complete raw bytes, native read results, partial failures
and atomic storage receipts are retained without retries or replacement.
Replay binds the external run authority and original collector output, checks
every byte and rejects missing, reordered, shortened or substituted records.
Passing report flags cannot replace these records.

The source budget at 4K is 2,183,376,919 bytes plus independently supplied
runtime assets, covering all raw frames, an atomic temporary file, 128 MiB
scratch and 32 MiB metadata. The complete next payload must fit the remaining
retention allowance, and the strict disk reserve plus remaining peak allowance
must remain available. Failed persistence keeps partial files and original
pending bytes in memory; those bytes still require safe durable retention by
the outer host. The component provides no actual reader or filesystem adapter.
Archive consistency does not establish native provenance, coherent rendering,
loaded candidate/probe bytes, process health or no-breakaway job cleanup. All
broader acceptance flags remain false, and no production lane is registered.
The host-monotonic envelope is not measured process running time. A future
producer must retain native pause/resume receipts and exclude paused or unknown
intervals from the required two-hour running duration; the frozen archive
schedule cannot supply that proof.

`tools/hidden_soak_running_time.py` adds a separate v2 receipt-arithmetic
contract without changing the frozen frame ledger. Its independently retained
QPC epoch, source pins, process generations, readiness artifact and 242 capture
bindings constrain the complete pause/resume sequence. Only acknowledged GO
intervals ending before a break request contribute; command windows, held
reads and unknown transitions do not. Each interval loses one QPC tick at each
endpoint. Periodic captures follow the fixed 30-second running-time schedule
through 7200 seconds, with a distinct terminal pause, bounded held/read windows
and no retiming of original samples. Native HRESULT failures remain raw in
their original signed or unsigned form and cannot count as successful calls.

The transcript allowance adds 8 MiB to the frame-ledger peak budget for one
4 MiB retained transcript and one atomic temporary. Native-host/source/RAM and
other producer receipts need their own additional allowances. Replaying these
supplied receipts establishes arithmetic consistency only; it does not prove
native issuance, host-awake or asynchronous-event coverage, CPU/render health,
frame pixels, loaded bytes or full job cleanup. All broader endurance, runtime,
manual-input, release and promotion claims remain false. No missing production
lane is implemented or registered by this component.

`tools/hidden_soak_loaded_image.py` prepares a source-owned comparison at the
initial held loader checkpoint, before probe commands or code breakpoints.
It privately reconstructs the four frozen all-preset parent recipes and their
exact candidate, typed metadata, canonical probe and source inventory; Classic
uses its actual narrow or wide recipe. Other successor/legacy recipes remain
outside this admission path. Caller-selected ranges, exemptions and resealed
report flags cannot substitute for this reconstruction.

The comparison requires the PEB ImageBase DWORD, all canonical headers and all
executable raw/zero extents. It validates complete HIGHLOW fields and applies
the actual base delta without rewriting REL32 fields. Nonexecutable sections
and alignment intervals are explicitly excluded; writable executable sections
fail. Original bytes, partial counts, signed or unsigned HRESULTs, and all five
ordered native query results before and after every read remain retained.
Changed generations, selection, architecture, probe/breakpoint sequence or
the independently bound 20-second held epoch fail.

The strict preferred ImageBase value in mapped headers and executable zero
tails remain policies awaiting native-loader verification. This component
installs no native collector or filesystem adapter, executes no probe and
does not prove readonly constants, runtime RW/IAT/provider state or genuine
native issuance. Source comparison is separate from loaded-candidate,
whole-image, runtime, manual-input, release and promotion proof; those claims
remain false and no missing production verifier is registered.

`src/patcher/battle_profile_stack_lease.py` prepares an uninstalled owning stack
lease around the exact frozen V2 field. Its 192-byte descriptor and 512-byte
helper frame bind the root stack, owning thread, source VA, field lifetime and
bounded Tile/Unit/Adjacent/effect/primitive ancestry. Public construction
privately reconstructs the actual parent and authenticates 36 original native
CALL sites and ten complete RET operands. The field frame stays 1280 bytes;
the protected 4096-byte owner page and 128 KiB RX reservation remain unchanged.
At 4K, remaining RX space is 65,983 bytes for Classic/Framed and 46,127 bytes
for Complete HD/Modal Widgets.

The primitive wrappers copy original arguments and preserve native register
outputs and flags after normal return and resource cleanup. Fixed receipts,
thread identity and stack control precede cached heap/world reads. Unknown
ancestry, changed descriptors and callbacks that poison those cached pages
fail the scoped check. A retained loss returns outer status 2; it cannot stop
the next frozen V2 Tile, unadapted Unit/Tile continuations or RLE/provider work
before normal return. Receiver/argument validity, physical-only clipping,
installed external callsite admission and immediate cancellation remain
explicitly unverified. No hooks, header/owner-state changes, clear/present,
safe standalone native replacements, expanded-battle acceptance or promotion
are supplied by this preparatory component.

`tools/hidden_soak_loaded_read_session.py` prepares the supplied-reader side of
the initial-loader comparison. Its public preparation privately reconstructs
the frozen canonical request inventory before launch and issues an opaque,
identity-bound capability; clones or artifact JSON cannot create admission.
The fixed original held-start QPC tick and epoch are never moved. Preparation
performed under an existing hold consumes that same 20-second budget, with
exact rational projection retaining fractional counter remainders.

Every owner observation, ordered native query, breakpoint count, architecture
result and raw read attempt is retained before its success predicate. Failed
HRESULTs with matching stale values, nonzero or missing owner sequences,
changed sources/generations, partial reads and capacity failures stop further
reader calls. Original failed and incomplete attempts remain available; no
successful after-read phase is synthesized. The additional 33,619,971-byte
allowance covers the 16 MiB raw scope, a 65,539-byte raw temporary, 8 MiB metadata
and its 8 MiB atomic temporary. Native-host, assets, other producer receipts and
over-capacity pending originals require separate allowance.

This component installs no native reader or durable storage. Supplied receipts
do not prove actual initial-loader events, owner authority, coherent reads,
host-awake coverage or native clock precision. A future native capture followed
by offline Python comparison must not claim that the later comparison ran
inside the historical held epoch. All broader loaded-candidate, endurance,
runtime, manual-input, release and promotion claims remain false; no production
lane is registered.

`tools/hidden_soak_job_lease.py` prepares an ordered WIN64-only job transcript.
It retains supplied native scalars and complete original buffers, including
unused PID-buffer capacity. Suspended creation, no-breakaway limit readback,
assignment and membership must precede resume. Retained process generations,
startup/precleanup membership and accounting, bounded termination/drain, final
empty queries after known waits, and all owned closes are required. Missing,
duplicate or reordered operations, failed calls, unknown children and handle
debt fail even when later receipts look successful. Existing cleanup booleans
cannot supply these receipts.

The 4 MiB transcript and its atomic temporary add 8 MiB to the other producer
budgets. Source/native RAM, oversized originals and other costs remain additional.
This installs no native adapter, and the unchanged host does not emit the
future protocol. Oversized buffers/errors must be retained before constructing
bounded records; a rejected constructor does not prove that retention. Supplied
Python authority aliases do not establish genuine producer issuance. Startup
and precleanup snapshots do not cover the per-frame or whole-run membership
schedule. Native no-breakaway cleanup, endurance, runtime, manual-input, release
and promotion remain unverified, and no production lane is registered.

`tools/hidden_soak_loader_native.py` prepares a fixed x86 command-free initial
loader batch from the private canonical candidate/read-plan chain. Opaque
source-issued request identities reject reconstructed clones and changed source
bytes. `tools/hidden_soak_loader_native_adapter.py` retains original framed
stdout bytes and strictly checks source, candidate, launch, callback, generation,
QPC and complete read-buffer bindings before replaying the supplied receipts.
Failed native calls and malformed or truncated archives cannot become passes.
Native callback strings, full-capacity buffers and the original initial-stop
clock remain distinct from parser-derived values.

The native batch writes one regular-file journal and includes a reserved complete
failure tail. Its shared raw/metadata journal plus atomic metadata allowance adds
35,717,123 bytes; a second complete raw-archive copy requires additional space.
Assets, compiler outputs, independent generation/job/clock receipts and unknown
original-output debt are additional costs. The Windows CI
fixture launches only a marked synthetic executable, adopts its target handle
while still live and checks actual original read bytes. It compares them after
termination. Canonical comparison during the native hold, real instrumented
generation/job ownership, durable raw storage and whole-candidate/probe/runtime
acceptance remain false. No production lane or stable status is registered by
this source preparation or its synthetic native CI fixture.

`tools/hidden_soak_loader_expected.py` prepares the exact source-owned immutable
image payload after private original/candidate/recipe/probe reconstruction.
Narrow and wide Classic retain distinct parents. Opaque live capabilities reject
clones, changed sources and substituted public aliases; fresh replay rejects even
consistently resealed candidate/probe replacements. Complete original payload
bytes remain retained in RAM, and source loss after modeling publishes no chunks.

The CLHDLE1 stream has a 48-byte prefix, at most 65,536 metadata bytes, 511
32-byte chunk descriptors, 65,536 four-byte HIGHLOW locations, 16 MiB minus four
raw bytes and a 32-byte SHA trailer, with no padding. Its exact maximum is
17,121,324 bytes. Expected payload and atomic temporary plus the existing native
journal and separate full raw-archive copy require 96,239,710 bytes of known
allowance. Assets/compiler/RAM/independent receipts and unknown output debt are
additional. This is a cost bound, not filesystem storage or budget approval.

Modeled rebasing applies complete selected HIGHLOW DWORDs modulo 32 bits. The
preferred header ImageBase stays unchanged, and actual PEB.ImageBaseAddress must
be read separately. Nonexecutable data, provider/RW/IAT regions and alignment
gaps remain outside the checked scope. No native adapter, comparison during the
hold, whole-image/probe, ownership/cleanup, runtime/endurance, manual-input,
release lane or promotion is established by these source fixtures.

The inherited synthetic verifier harness now retains pending and terminal cases
outside the repository before its unchanged 35-second process invocation. Exact
source, compiler, candidate, CRLF probe and original output bytes accompany a
sticky failure ledger; partial timeout output and unavailable streams cannot be
replaced with a passing report. QPC and original HRESULT boundaries around the
existing debugger calls distinguish a missing return from later callback flush,
inspection or termination failures. Clock/flush diagnostics add strict checks;
all original byte, relocation and rejection comparisons remain required.

Only completed distinct small-world and Castle cases with retained raw outputs
and complete diagnostic boundaries can satisfy their synthetic reports. Castle
requires five native test methods and seven distinct cases, plus successful
compiler retention and no sticky failure or retention debt. The workflows
configure their external directory in the executing step, where RUNNER_TEMP is
available. Prior missing-directory and workflow-validation failures remain
historical diagnostics, not accepted receipts. Native LF/CRLF parsing preserves
the full original output bytes and rejects malformed/duplicate markers. Repairing
a parser cannot rewrite an earlier sticky failed report as accepted. The Framed
identity header and final result are separate source-bound records, with strict
order, uniqueness and matching identities. The known retained-output
and atomic-write allowances are 512 MiB and 64 MiB respectively, in addition to
the strict free-space reserve. Oversized output remains failed retention debt;
hard runner loss can still prevent upload. These changes improve future timeout
diagnostics. They do not establish the cause of historical timeouts, native game
cleanup, any production lane, release acceptance or stable promotion.

`src/patcher/battle_profile_content.py` prepares 28 fixed operand helpers from
the authenticated stack-lease chain. Exact whole original/parent instructions,
native CALL/RET ancestry and neighbor tables are authenticated independently.
Fixed owner/global receipts, owning thread and bounded stack/control checks
precede the complete current field receipt and any terrain/unit payload read.
Native Tile coordinates must match its actual source-owned field invocation.
The original signed empty sentinel, valid unit/type limits, unsigned owner-byte
domain and actual-arena coordinate bounds remain distinct from malformed data.
Out-of-arena neighbors read no occupancy, unit, type, owner or neighbor payload.

The helper returns its value in EAX and denied/valid/fault status in EDX, preserving
other registers, flags and stack balance. This is a preparatory ABI: future
adapters must restore each original full or partial MOV/MOVSX destination and
handle failure before native continuation. No instruction replay, hooks, owner
writes, clipping, provider validation or cancellation are installed. Count's
earlier input-record reads and non-draw callers remain outside this family.
The emitted component uses 15,967 RX bytes for Classic/Framed and 16,026 for
Complete HD/Modal Widgets. At 4K, 50,001 and 30,086 bytes remain respectively in
the unchanged 128 KiB reservation. Source and synthetic x86 checks do not
establish native rendering, expanded-battle acceptance, healthy return or
promotion; all installation and broader acceptance claims remain false.

`src/patcher/battle_profile_continuation.py` prepares 74 adapters and receipts
around 72 planned native windows: 28 operand reads, 43 post-normal-return checks,
Count entry and two field CALL receipts. Original full/subregister destinations,
flags, CALL/RET ancestry, whole stolen instructions and relocation fields are
authenticated before replay. Count's +2/+4/+6 early reads are checked before
their native use. Thread callbacks retain a bounded complete pre-call control
snapshot; lost control permits no cached payload read or replay. Validated
rejection preserves incoming EAX, while unknown control reaches exact UD2 and
remains unsuitable for installation.

This component consumes 20,260 RX bytes for Classic/Framed and 20,319 for
Complete HD/Modal Widgets. Chained 4K totals are 101,332 and 121,311, leaving
29,740 and 9,761 bytes in the unchanged 128 KiB reservation. The source/synthetic
suite covers all 36 geometries, two bases, scalar/subregister/flag replay,
bounded arrays, post-return ownership loss, independently decoded relocations
and stack canaries. A final exact six-byte CMP length fix left all emitted bytes
and immutable receipts unchanged; actual Classic 1024x768 metadata changed only
in its own source hash.

All hooks remain absent. Non-draw Count callers, unit -1/type -1 predecessor
invariants, provider/RLE cancellation, receiver/arguments, physical clipping,
atomic integration and native restoration remain unverified. Header-overlap
bytes at WORLD+821 must not be relabelled as a harmless sentinel unit. This
preparation establishes no expanded-battle candidate, runtime/input/composition,
endurance, healthy map return, release lane or promotion.

`tools/hidden_soak_loader_compare_native.py` and its separate private adapter
prepare a v2 command-free immutable comparison from the authenticated expected
payload. Preparation and replay share one private capability registry; public
inspectors, cross-registry requests with identical JSON and clones cannot admit
a request. The generated x86 batch retains complete requested read capacity
before interpreting original HRESULT/count results, then compares every selected
byte at the actual PEB base. Canonical preferred header ImageBase, raw/zero
executable extents and complete HIGHLOW relocation policy remain explicit;
readonly/RW/IAT/provider regions and alignment gaps remain excluded.

The sole 20-second anchor is the earliest initial loader callback. All byte
comparisons and the actual counter after EndSession must fit that original
epoch. Later execution-status queries, waits, process times and closes remain
outside its attested duration. No loader hold proves map readiness or the
required process running time. Original journal write/flush results remain
retained, but a footer cannot attest its own append/flush recursively. Initial
magic-write failures retain original bytes and separate sticky output debt.

The exact known peak is 112,870,182 bytes including request and expected-payload
atomic temporaries, a failure-capable journal and a separate complete archive
copy. Compiler/source/object/binary outputs, candidate/assets, RAM, independent
generation/job receipts and unknown native output debt require extra allowance.
The Windows CI fixture adds 256 MiB for fixture compiler/report/source outputs,
requires the strict free-space reserve and runs only a marked public synthetic
executable. Supplied receipt replay and this scoped fixture do not establish
production native provenance/read coherence, full job/host cleanup, durable
storage, loaded-candidate/probe, runtime/endurance, manual-input, release or
promotion proof. All broader flags remain false and no production verifier is
registered. The fourteen missing production verifiers remain unfinished.

`src/patcher/battle_profile_primitive_request.py` adds a versioned shared-guard
recomposition of all 74 baseline adapters plus 13 uninstalled primitive queries.
Exact native argument windows and HIGHLOW inventories authenticate Tile, Unit,
Tracking and Charge ancestry. A new 116-byte owning thunk retains its 64-byte
request separately from native arguments; the 640-byte helper preserves a full
864-byte callback snapshot within a 1712-byte maximum stack extent. V2 field,
lease and owner-page sizes remain unchanged.

The query layer preserves original register/stack arguments and flags while
returning status in EDX. Finite signed sprite clips and all-minus-one native
clips remain distinct; malformed and empty intersections cannot become prepared
draws. Native unsigned16 line coordinates, Y-only axis selection, inclusive plain
and exclusive dashed endpoints and absolute dash phase are preserved. Exact
current physical-field receiver checks reject primary state, but provide no
sprite/payload/allocation provenance and perform no primitive replay or pixels.

At 4K the recomposed RX totals are 106,495/126,474 bytes with 492/493 relocation
receipts, leaving 24,577/4,598 bytes in the unchanged 128 KiB reservation. Original
three-byte indirect primitive calls differ from proposed five-byte query calls;
whole pre/post windows must be installed atomically by a future reviewed recipe.
All hooks remain absent. Provider lifetime, intracallback cancellation, fatal
shutdown, healthy restoration and full battle integration remain unverified.
Unknown control reaches exact UD2. Passing query/continuation fixtures establish
no installed battle, runtime/input/composition, endurance, release or promotion.

`src/patcher/battle_profile_line_replay.py` prepares two direct memory-line
invocations from the versioned request producer. The original callback-free
line/fill closure and memory vtable are authenticated against the original and
rebuilt parent, including all 15 vtable HIGHLOW fields. Complete 8-byte and
11-byte call/cleanup windows replace the overlapping planned post hooks; both
genuine intrinsic call PCs remain separately bound. Clipped RET8 arguments are
duplicated in the owning frame and original caller arguments remain unchanged.

Both line paths require zero latched loss after full thread/control admission,
before cached current-receipt reads. Native outputs and flags are saved before
post-helper admission; unknown control or receipt loss stops at exact UD2.
The public API captures its canonical issuer privately and checks the exact
original before dependency reconstruction. Public helper aliases cannot select
the implementation; canonical source is checked before and after emission.
At 4K the unchanged reservation uses 106,941/126,920 bytes, leaving 24,131/4,152.
Synthetic pixels and RET8 are modeled rather than original opcode execution.
All installed-hook lists remain empty. This supplies no native rendering,
RLE/provider ownership, complete battle, healthy map return, runtime/input,
endurance, release or promotion proof.

The separate `tools/test_battle_profile_native_line_original.py` fixture can
execute genuine authenticated line/fill instructions in Unicorn at two image
bases with `--original-backed` and the exact local original. Native pixels,
registers, flags, RET8, CALL/RET ownership and bounds are checked against an
independent oracle; the line entrypoint is not replaced by a pixel callback.
The surrounding thread queries remain modeled. All installed-hook lists remain
empty and this establishes no sprite/provider, Windows rendering, full battle,
healthy return, visual/input, endurance, release or promotion acceptance.
Its default public-CI mode checks three authoring contracts only and explicitly
reports `original_opcode_cpu_verified=False`. It reads no original in that mode,
writes no game artifact and launches no native process. Original-backed CPU
results remain a separate local evidence class, not a matrix runtime lane.

`src/patcher/battle_profile_context_v2.py` supplies a separate allocation
successor for the remaining battle families. It reconstructs the frozen parent
and plans fresh 256 KiB RX plus 64 KiB RW reservations at all 36 combinations.
Its first RW page protects a future 128-byte record; the remaining 60 KiB is an
unpopulated provider reservation with no proven schema, capacity or lifetime.
Modal header growth to `0x800` retains loaded RVAs and HIGHLOW operands while
recording every supported file-offset edit with old-byte verification. Unknown
auxiliary, overlapping or overlay resources reject. The context emits only
the in-memory parent relayout: no new section, battle code, state, providers,
hooks or saved candidate. Every future emitter needs complete re-emission and
relocation for these new addresses. The parent probe belongs to the unchanged
parent and supplies no proof for a future battle candidate. Nine portable
fixtures cover the geometry, schema, ownership and rejection contracts; the
optional genuine-original RAM lane remains separate from public CI and all
runtime acceptance. The frozen predecessors and protected default are retained.

## Required acceptance and next work

The uninstalled `src/patcher/battle_profile_lifecycle_v2.py` re-emits the pinned
lifecycle template for the new allocation context. Complete source/operand and
native transfer inventories, full 128-byte record snapshots, protected RX/RW
alias rejection and callback checks retain the frozen original's ABI and
allocation-null fatal route. All new RW tail/provider bytes must remain zero;
nonzero inherited modal tail is an explicitly unsupported admission case.
This cannot establish dynamic native-field compatibility or transient-write
prevention. The 456-byte helper stack and 4K component code bounds are not a
completed full-chain budget. Synthetic callbacks and optional original-backed
RAM reconstruction supply no installed battle, provider lifetime, native
cleanup/healthy return, visual/input, endurance, release or promotion proof.

The uninstalled `src/patcher/battle_profile_routing_v2.py` re-emits six routing
entries after the fresh lifecycle, using complete new allocation spans and the
separate inherited modal page. Full record/tail checks surround modeled thread
callbacks. Exact virgin query denial and receipt loss remain separate, but
neither authorizes a native target write; both initial adapters restore ABI and
reach an explicit unsafe endpoint. This is no healthy fallback or production
cancellation proof. Typed scalar/address/branch inventories and 1280-byte local
frames supply component checks only. The remaining field/lease/content/primitive
and line families still require a fresh canonical join and complete-chain
capacity verification. Provider/RLE ownership and every runtime gate stay open.

The uninstalled `src/patcher/battle_profile_field_v3.py` re-emits terrain after
fresh routing, with full typed transfers and actual post-Tile return receipts.
Fixed/global/pointer/control/tail checks precede callback and cached reads;
modeled loss stops later Tiles without unauthorized target restoration. Query
failure and draw denial/loss keep their separate return conventions. The
explicit 1280-byte frame and observed component extents establish no native or
complete-chain capacity. Remaining frozen families cannot authenticate this
fresh field without versioned joins and rebuilt return descriptors. Native
sprites/clips, provider/RLE ownership, cancellation/quit/healthy return, atomic
installation and every runtime lane remain unfinished.

The uninstalled `src/patcher/battle_profile_stack_lease_v2.py` joins the pinned
stack-only template to fresh field V3 with complete typed transfers and actual
field/lease post-CALL descriptors. Independent control/descriptor shadows and
full fixed/tail/pointer checks reject modeled callback corruption before cached
reads. Unknown private-control loss reaches an unsafe terminal, not a verified
healthy unwind. Its 192-byte lease, 512-byte helper, 1280-byte field and numeric
helper interval establish no native or complete-chain capacity. Field V3 does
not consume latched lease loss; next-Tile/intra-Tile cancellation, native ABI,
receiver/argument validity, provider/RLE lifetime and the remaining component
joins stay unfinished. Nothing is installed and every runtime gate remains open.

Each final candidate needs actual native acquisition/read, selection/movement,
scrolling and focus recovery; map frame/footer, all six action cells, panel and
minimap alignment; castle and every supported building route; expanded battle
commands/outcome/healthy return; isolated save/load and player/day continuity;
approved final-wrapper composition and genuine human input; and the ordered
short ladder followed by two-hour map-idle and map-pan runs with owned cleanup.
The unchanged endurance schedule totals 176.4 measured hours across 36 cells.
Passing source or CPU fixtures cannot satisfy these requirements.

Expanded battles retain native 64-pixel tiles, seven rows and the actual arena
width capped at twenty columns. Their right HUD uses native-size top and bottom
slices, including bottom-anchored commands. Existing modular geometry tests now
cover all nine presets, but their native hook/routing integration remains
uninstalled. Preserve historical standalone battle recipes and diagnostics.

Resolve the current input failure using the prepared activation observer before
changing input behavior. Require fresh disk measurements before any compiler,
bundle, copy or game run; preserve the greater-than-ten-percent reserve and
next-operation allowance. Prior hidden/debugger authorization does not grant a
new visible/manual session. Prepare concrete candidate-bound human plans and
obtain fresh approval before those observations and live capture.

Preserve the frozen Classic 800x600 fallback, protected stable stage and current
default. Further source checkpoints may merge while unfinished entries remain
experimental. A stable entry requires accepted exact-candidate evidence and an
explicit promotion decision, rather than a successful build or process exit.

See [the handoff](AGENT_HANDOFF.md), [current evidence evaluation](COMPLETE_HD_EVIDENCE.md)
and [the contributor rules](../../AGENTS.md) for the existing operating boundaries.

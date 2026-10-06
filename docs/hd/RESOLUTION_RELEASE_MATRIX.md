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

## Required acceptance and next work

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

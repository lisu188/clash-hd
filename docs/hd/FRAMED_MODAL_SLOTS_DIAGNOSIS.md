# Barracks dirty-slot diagnosis and separate validation builder

2026-09-08. This change provides source-bound emitted x86, a synthetic ABI
fixture, and a separate validation builder. It does not run the game, change
complete-HD v1 or resolve the outstanding release evidence.

## Demonstrated stale mirror

The preserved 1024x768 barracks run is
`C:/ClashCaptures/hd-completion/framed-modal-canvas-v2-barracks-1024x768-castle0-20260906-062843/`.
Its candidate SHA-256 is
`c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d`,
stage `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-modalcanvas-validation`.
This was a forced-route hidden CDB software-surface capture, not visible or
manual-input proof. The original failing artifacts are unchanged.

The native canvas (`native-surface.raw`, SHA-256
`d63e0d1f10622f8c001fe51acd8de4c464c9afdf9886a3ca5140c94026d4067e`)
and centered physical mirror (`surface.raw`, SHA-256
`8d973937a26820abe14403823bfd51591ec26162231737f71314b6d33cfb3a02`)
differ at exactly 24,576 palette indices. Every mismatch is a nonzero native
pixel and a zero physical pixel. In native coordinates they form exactly twelve
32x64 rectangles: x=126,197,268,339,410,481 and y=75,206. Physical coordinates
add (192,144). All 479,232 pixels outside the centered native rectangle are zero.
The saved `surface.png` confirms the twelve empty interiors, intact four outer
margins, and five present bottom controls. Those controls are not accepted input
evidence; ordinary-map borders/action-bar gates do not apply to this modal.

The log shows full blit return `00433E3F` with mirror count 3, followed by native
slot work and first present `00433E72`/`00433E77`, still at count 3. The native
producer `00432940` draws the slots into the owned native canvas and directly
calls partial blitter `004024E0` at `00432C0B`. This bypasses the existing
full-blit mirror hook. The stale mirror is therefore demonstrated by matching
pixels and source/trace ordering, rather than inferred from a black screenshot.

The same direct call supplies uncentered primary destination coordinates.
Its misplacement on the final primary is a static inference: the preserved
primary-capture attempt `C:/ClashCaptures/hd-completion/primary6-barracks-20260906-104000/`
never produced primary pixels because its initial-map trace failed. That
failure remains intact; cached primary-lock readiness is not composition proof.

## Narrow adapter contract

`src/patcher/framed_modal_slots.py` authenticates the original SHA and rebuilds
the entire complete-HD v1 predecessor before accepting it. It additionally
verifies the exact call bytes `E8 D0 F8 FC FF` at `00432C0B`, the native slot
producer span and partial-blit ABI span. The declared validation stage is
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-modalslots-validation`.

The CALL adapter uses the frozen canvas `is_active` validator to
check owner thread, object and pixel ownership, native and physical dimensions,
disjoint nonwrapping allocation extents, and primary context. A preexisting
fault prevents additional work. It accepts only the twelve actual slot origins,
native source, zero primary-destination sentinel, matching native destinations,
and exact right/bottom arguments. The native blitter uses inclusive right and
bottom coordinates, so the copied dirty rectangle is 33x65; its nonzero missing
art occupies the inner 32x64. The adapter copies that rectangle using each
surface's own stride, then translates only this call's two primary destination
stack operands. It restores incoming registers/flags and tail-delegates to the
original partial blitter, preserving its return, register clobbers and RET 16.

Inactive canvas, failed allocation, completed destruction, sticky fault, failed
ownership or unexpected call arguments retain the original call unchanged.
The adapter allocates nothing and changes no canvas ownership or mirror counters.
It neither clears unrelated physical pixels nor recopies primary text/cursor
layers. A global partial-blit hook would double-center the existing full-blit
wrapper; an unconditional late full-primary copy could erase primary-only work.

The emitted-code fixture executes the actual frozen canvas ownership validator,
constructors, destruction and rollback adapters in synthetic memory. It exercises
every slot at all six fixture resolutions, including 802x602, verifies the
inclusive pixel rectangle and untouched surroundings, records exact register and
stack arguments, deliberately clobbers native volatile registers/flags, checks
stack cleanup, and tests allocation failures, invalid ownership, unexpected
arguments, destruction and byte/allocation rejection. A native-blit ABI recorder
does not constitute proof of primary pixels or controls.

The frozen army allocator deliberately accepts only its ten-section modal
predecessor. A separate `pe_modal_slots_extension.py` accepts the exact
eleven-section complete layout and appends a twelfth `.hdslots` RX section.
Its header fits at file offsets `0x320..0x347`, within the existing 1024-byte
header. Old section headers and raw bytes remain unchanged except for the one
slot CALL and explicit PE metadata edits. Every old HIGHLOW relocation survives;
new absolute operands join a new complete relocation directory in `.hdslots`.
It allocates no additional writable state.

`tools/build_framed_modal_slots_candidate.py` reconstructs and authenticates
complete-HD v1, binds the slot emitter to its exact source and modal ownership
addresses, checks every edit, and writes an exclusive `.exe`, `.candidate.json`
and `.cdb` bundle under `C:/ClashTests`. For example:

```powershell
python tools/build_framed_modal_slots_candidate.py --original C:/Clash/clash95.exe --resolution 1024x768 --output C:/ClashTests/modal-slots/new-unique-run/clash95_slots.exe
```

The new probe checks current loaded PE metadata, every inherited hook/extension,
owned modal state, new code and relocation bytes, and the complete native slot
producer/partial-blit spans. It emits `SLOTS_CONTRACT_PASS` and a PTILE marker
for this exact new stage. It never emits a complete-HD v1 or army-v1 pass marker
for modified bytes. A new-stage runtime consumer is still required; an old
modal or complete probe must not be treated as compatible by changing its name.

Independent fixtures verify all six resolutions, every old/new relocation at
two rebases, exact edit replay, loaded-byte checks, negative allocation/identity
cases, and Windows read-only `SEC_IMAGE` section admission without mapping or
executing an image. Historical source pins, builders, candidate identities,
probes, failed evidence and stable selection are unchanged.

## Other castle routes remain separate

Read-only audit of the dirty source's `FRAMED_CASTLE_REMAINING_ROUTES.md` confirms:

- Court callback `0044FE70` has an identified native route and first present,
  but primary player/prisoner artwork and text follow the early full blit;
  graph drawing uses further partial copies. Court needs route admission and
  completed primary capture before a composition correction can be justified.
- Recruitment `004338E0` to `00435BC0` requires the initialized barracks loop
  after all three initial presents. The preserved barracks stop precedes that
  state. Capability, native eligible-type selection and changing stack depth
  must be observed; recruitment also draws primary-only layers and retains older
  centering wrappers whose interaction requires its own evidence.
- Peasants callback `0042B0A0` is already inventoried in the source modal producer
  (command 0x87, first present `0042B35E`), but the located 2026-09-06 run plan is
  unexecuted. An inventory entry does not prove entry, composition or exit.

After installation, collect matching native/physical/primary captures before and
after slot selection, and prove exit, destruction and healthy map return. Keep
allocation failure, route, mirror, primary composition, visible controls, input
callbacks and promotion as separate claims. This narrow fix does not cover
court/recruitment, all barracks text, castle exit or the final 1080p release.

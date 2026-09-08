# Native modal canvas: diagnosis and uninstalled lifecycle adapter

Recorded 2026-09-06. The [bound diagnosis](../../captures/current/framed-modal-packed-loader-diagnosis-20260906.json)
preserves existing captures; it does not launch a game, extract assets, repair
an image, or change either runtime verdict. The current framed candidate is
`69899e07f70dde2094264be694300e00c7a778f1391ac7797b74c59c56ee1ce0`
at 1024x768, with minimap-viewport support. See the
[screen inventory](FRAMED_SCREEN_VALIDATION.md) and
[remaining route contracts](FRAMED_REMAINING_SCREEN_ROUTES.md).

## Exact packed-background proof

The overview run `castle_overview-1024x768-castle0-20260906-040923` and hospital
run `hospital-1024x768-castle0-20260906-041248`, under
`C:/ClashCaptures/hd-completion/framed-screens-20260906-034725`, passed their
bounded route/capture checks. Their actual images remain visually incorrect.
Expected black margins around a centered 640x480 modal, and absence of the
ordinary-map frame or six-cell bar, are separate observations.

The source asset is the authenticated user-owned
`C:/Clash/DATA/maximum.res` member `/GFX/CASTLE.CHR/DW_20.GFX`: offset
1,358,128, length 175,520, SHA-256
`760bb8908b34b6f268fd4dc75fc676a30e7f10435c9d0591e0ba3a66e0baec3a`.
Its PCX header specifies 640x480, 8-bit indices, one plane and 640 bytes per
line. Directory traversal and RLE decoding were performed only in memory.

Compare each decoded index at `k = 1024*y + x` with the recorded hospital raw
index at the same `k`. This tests the erroneous placement, not a corrected
image. Results:

| Comparison | Exact matches | Compared | Mismatches |
| --- | ---: | ---: | ---: |
| Entire packed 307,200-byte background | 291,499 | 307,200 | 15,701 |
| Physical x=640..1023, y=0..299, outside native-position text | 115,200 | 115,200 | 0 |

The first comparison includes subsequent title/text/sprite overlays; its
mismatches are retained. The second proves that the stripes are already in
the paused software surface. Palette choice and PNG conversion cannot explain
this exact indexed-pixel identity. 640×480 bytes occupy exactly 300 physical
1024-pixel rows, matching the observed background boundary.

The coherent July overview baseline is
`captures/archive/cdb-surface-dump-20260712-144019`. For x=0..639 and y=80..259
inside the new centered crop, let `k=1024*y+x`. Compare new raw
`[(144+y)*1024+192+x]` with archived raw
`[(60+floor(k/640))*800+80+(k%640)]`: 113,245/115,200 indices match.
This supplemental comparison retains 1,955 differences from different route
timing and overlays. Unlike the new route, the historical log explicitly
entered the overview wrapper with a 640x480 target before map allocation.

## Source mechanism

Known original SHA-256:
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
The diagnosis records original/candidate VA, RVA, file offset, length and
hashes for every cited machine-code span. The relevant loader and iterator
code is unchanged in the candidate.

* The memory vtable at `0050EE24`, slot `+30`, selects PCX loader `004020A0`.
  Overview `004213B4..004213C1` and hospital `0043DD22..0043DD39` use it.
* `004020A0` obtains a write iterator at destination (0,0), decodes a single
  packed stream and stops at PCX width×height (`00402395`). It does not add
  a destination-row adjustment when the source row ends.
* `00403EF0` initializes the iterator from the actual surface width. Iterator
  advance `004057D0` is `01 50 04 C3`: add EDX to its pixel pointer, return.
* Overview call `0042232E` is redirected to `0051B6D0`. That wrapper calls
  native `00422020` first, then copies its top-left 640x480 through scratch,
  clears/centers onto HD. It never establishes a native target before loading.
* Hospital first present `0043DE4E` remains the native call. The existing
  castle present-wrapper group covers recruitment/action polling at
  `00435DAA/00435DDE`, not all castle facilities. Thus hospital adds native
  coordinates and stale prior content to the shared loader mismatch.

The selected candidate contains no `0051B7E0` alternate native-action wrapper.
That other recipe allocates a temporary canvas around `00435BC0`, but restores
and copies only after the entire modal returns. It is not a solution for
first-present or active-modal composition.

## Native allocation and destruction contract

These are register-call x86 routines, with no caller-pushed arguments.
Preserve caller GPRs, flags and ESP around new adapter work; do not infer
callee preservation from an IDA name alone.

| Routine | Actual contract and failure behavior |
| --- | --- |
| `00473FF0` `_nmalloc_` | EAX=size, EAX=pointer or zero; explicitly saves/restores EBX, ECX, EDX, ESI, EDI, EBP and ES/FS/GS. Its direct null return is distinct from the fatal wrapper below. |
| `00461C00` `Mem_Alloc` | Calls `00473FF0`; allocation failure logs and calls `App_RequestQuit` at `00461C52`. It is **not** a graceful optional allocation API. |
| `00401E00` base constructor | EAX=188-byte header, DX=width, BX=height; writes dimensions, zero pixel pointer and constructs the member at header+8 through `00473250`; returns the same header in EAX. No allocation. |
| `00473250` member constructor | EAX=header+8; initializes the member vtable and null COM pointer, with no allocation or external call. Preserve these initialized fields rather than inventing a four-field header. |
| `00403D70` memory constructor | EAX=header, DX=width, BX=height. Calls the base constructor, sets vtable `0050EE24`, allocates width×height via `00473FF0`, and zeroes pixels. Pixel allocation failure calls `App_RequestQuit` at `00403E27`/`00403E40`; it is not a graceful null-return recipe. |
| `00403E50` memory destructor | EAX=constructed header, EDX=2 for scalar deletion. Frees pixel pointer through `004740DD`, zeroes +4, destroys header+8 through `004732E0`, then frees the header through `00461C70`→`004740DD`. Never use vector-delete flag 4. |
| `004740DD` `_nfree_` | EAX=owned allocation; native deallocator, also used for header-allocation rollback before construction. |

A nonfatal adapter can allocate header 188 and pixels 307,200 using
`00473FF0`, checking each result before changing any game global. If the
second allocation fails, free only the first block. After both succeed,
zero the pixel allocation, call the authenticated base constructor, assign
the actual pixel pointer and memory vtable, and commit ownership. This is a
explicit equivalent of the successful memory-constructor path in the
[uninstalled emitter](../../src/patcher/framed_modal_canvas.py). Its focused
fixture executes cloned native constructor/destructor instructions with
allocation recorders, including both allocation failures. Do not call a destructor on an unconstructed
header, free pixels twice, or free the borrowed HD surface.

## Canvas lifetime and borrowed state

Allocate one root canvas before the first native instruction of `00422180`
executes. The source entry begins `53 51 52 56 57 55 83 EC 20`: a hook over
the first five pushes must replay those five instructions and expose a new
post-prologue observation point. The existing probe's `00422181` breakpoint
would no longer describe that candidate and must be replaced explicitly.

The separate validation module owns a supplied, zero-initialized
RW state record and two heap allocations. It does not select an apparent
zero cave, write `.hdcode` RX storage, or claim its state allocation exists.
The later PE installer must bind the declared writable region. A state record
retains phase, native pointer, borrowed physical pointer, original render
pointer, root entry ESP, owner thread, and diagnostic statuses/counters. It
also retains the exact allocated native pixel pointer and entered physical
pixel pointer. Every mirror/free checks these identities, nonwrapping,
disjoint pixel ranges, and the constructor-initialized null COM member at
native header+`AC`. A changed pointer or unexpected COM member is a failed
ownership check; neither copying nor destruction proceeds.

`005202E0` is the active memory target; save its exact HD pointer before
replacing it with the native canvas. `00511230` is `g_RenderDevice`; save its
exact entry value and direct native-canvas drawing there where needed.
`0051D4C0` is the physical primary object, not an owned memory canvas: keep its
physical width/height/backend unchanged. Admission must authenticate the
physical memory header, primary vtable/depth/backend, native dimensions,
ordinary-map owner and current thread. Original import
`GetCurrentThreadId` has IAT slot `004EA4E8`.

Native `00526A68` is the separately owned hit-test surface: the overview
allocates it, destroys it before each facility, recreates it after facility
return and destroys it on final exit. Never alias it to the adapter canvas
or free it in adapter cleanup. Likewise the game owns castle resources and
its render-hook/resource-mode save/restore protocol. Do not reset the
castle's gameplay state, alter feature bits, or replace those native lifetimes.

Facilities entered through `0042262C` share the active root canvas. Their
return target is `0042262E`; the overview then recreates its hit map, redraws
at `00422674`, and presents at `004226D3`. No extra canvas allocation or
destruction belongs at a facility return. Unsupported nested castle roots,
thread changes or ownership mismatches require a failed diagnostic, not an
unbounded nesting assumption or a fabricated restore.

**Restore before map redraw, not after root return.** Native overview exit
restores `g_RenderHook` at `004224A3` and primary resource mode at
`004224AD`, then calls `0040AD40` at **`004224B2`**, old bytes
`E8 89 88 FE FF`. Restore the borrowed physical target and render pointer,
detach and free the owned canvas before that call. Both normal return
`004224CD` and the optional movie branch ending `00422874` follow this
boundary. Preserve all native register/stack effects and the map redraw.
Process-terminating faults/quit paths are failed runs, not successful callable
cleanup. A reentry/incorrect root-stack identity must never free another
invocation's canvas.

## Presentation and old-wrapper interaction

`Render_Present` (`00460EA0`) and `DD_Pump` perform cursor composition and
polling; they are not interchangeable with a full background copy. The
ordinary full-surface copy is memory vtable `+24` → `00401E30` → the current
HD-aware helper `004E9920`. That helper already centers a native-width E0
source onto primary. Retain its primary behavior. The new active-canvas path
also needs a freshly cleared physical **memory** mirror with 640 source pitch,
physical W destination pitch, and offsets `(W−640)/2,(H−480)/2`.

| Route | Full-surface blit | First cursor present → return | Native modal return |
| --- | --- | --- | --- |
| Overview | `004220C3` | `0042239A` → `0042239F`; after facility `004226D3` → `004226D8` | `004224CD` or `00422874`, both after restore boundary |
| Hospital | `0043DE0D` | `0043DE4E` → `0043DE53` | `0043DE9F` → parent `0042262E` |
| School | `0043DA0D` | `0043DA4E` → `0043DA53` | `0043DA9F` → parent `0042262E` |
| Workshop | `0043E00D` | `0043E04E` → `0043E053` | `0043E09F` → parent `0042262E` |
| Smith | `0043DC0D` | `0043DC4E` → `0043DC53` | `0043DC9F` → parent `0042262E` |
| Barracks | `00433E3C` | `00433E72`, `00433E86`, `00433E95`, each return +5 | `00433F92` or `00434101` → parent `0042262E` |
| Peasants | `0042B1A6` | `0042B35E` → `0042B363` | `0042B3C7` → parent `0042262E` |

Some native operations occur after the full blit. Mirror again after the
complete overview `00422020` returns (`004220F7`), while retaining its native
result registers. The first cursor-present stop remains a route boundary;
it does not itself prove every separately composed primary layer is mirrored.

While—and only while—the admitted native canvas is active, bypass the
upgrade/center portion of old overview wrapper `0051B6D0`, retaining its stock
`00422020` work; otherwise it allocates/replaces E0 and centers twice.
Similarly bypass only the center-copy portion of the selected barracks callback
wrapper, retaining original `00435B90` polling. The exact candidate binds this
wrapper through the MOV EBX at `00435DAA`: it is `0051316F` at 800x600 and
`0051BC20` at larger profiles. Outside the active
canvas, preserve the exact old wrapper paths. Do not silently add the
alternative native-action group. The protected stable/default recipe and all
old candidate bytes remain unchanged; installation requires a separate stage.

## Uninstalled API and focused verification

`emit_modal_canvas(original, candidate, *, base_va, state_va, width, height)`
returns code, explicit absolute/relative relocations, six canonical
`pe_extension.HookPatch` records, entries, observer VAs, exact candidate SHA,
and a source contract. The candidate must match a complete in-memory
reconstruction of the existing framed builder, including the selected minimap
profile. `installation_ready` remains false. All six hooks are indivisible;
none displaces an existing original HIGHLOW field.

The caller provides an aligned RX code base and a separate zero-initialized
RW page at `state_va = base_va + 0x20000`.

The RX section's `VirtualSize` must cover the complete `0x20000` reservation,
even though its raw file contains only code and relocations. The first builder
used the payload length as its virtual extent, leaving a gap before the state
section; Windows rejected that candidate with error 193. The
[preserved failure and correction](../../captures/current/framed-modal-canvas-loader-correction-20260906.json)
and [nonexecuting Windows image-section observations](../../captures/current/framed-modal-canvas-sec-image-20260906.json)
record the exact four-byte header correction. The allocator now checks
adjacent virtual extents; its 18-group fixture includes native `SEC_IMAGE`
admission for all twelve resolution/minimap variants. This is executable-format
validation, separate from game/runtime evidence. The emitter uses 128 bytes
of state:

| Offset | Field | Offset | Field |
| ---: | --- | ---: | --- |
| 0 | phase | 4 | physical header |
| 8 | native header | 12 | saved render pointer |
| 16 | root entry ESP | 20 | owner OS TID |
| 24 | enter status | 28 | mirror status |
| 32 | leave status | 36 | latched fault |
| 40 | allocation count | 44 | free count |
| 48 | mirror count | 52 | pending header |
| 56 | pending pixels | 60 | owned native pixels |
| 64 | entered physical pixels | 68..127 | reserved zero bytes |

Public `try_enter(EAX=root entry ESP)`, `mirror()` and
`try_leave(EAX=exit-hook entry ESP)` return 0/1 while preserving other GPRs,
EFLAGS and caller ESP. `root_after_replayed_pushes` observes ESP=root ESP−20;
the original caller sentinel is at observed ESP+20. Cleanup admits only the
exact root ESP−60 call boundary. `overview_after_native_draw` and
`before_restored_map_redraw` provide separate observation points. Unknown
reentry latches a failed diagnostic without a second allocation. It is not a
supported recursively nested castle invocation.

The [focused fixture](../../tools/test_framed_modal_canvas.py) has 11 test
groups. It executes emitted x86 plus authenticated cloned base/member
constructors and scalar/member destructors in synthetic memory. Allocation,
primary blit and game-body calls are recorders. Checks cover both allocation
failures, no partial global commit, exact pixel/COM ownership, nested facility
reuse, ESP/TID rejection, native640 fallback under an HD profile, inactive old
wrappers, GPR/flags/stack preservation and cleanup before the map-call
recorder. The pixel oracle independently checks source pitch640, physical
pitchW, black margins and canaries at 800x600, 1024x768, 1280x720, 1280x960,
1920x1080 and 802x602. Declared relocation targets are remapped to synthetic
code/data; these fixtures do not execute the native allocator, game bodies or
primary renderer and are not runtime evidence.

Then a distinct candidate/probe protocol must observe native640 during each
load, the true full-blit and post-render boundaries, physical mirror dimensions,
and matching lifecycle state. Runtime/pixel/manual/promotion claims remain
separate. Existing failed images and bounded capture reports remain immutable.

The [2026-09-06 runtime checkpoint](../../captures/current/framed-modal-canvas-runtime-current.md)
has six 1024x768 captures under the complete native-artwork protocol. Overview,
hospital, school, workshop and smiths pass the exact native/physical comparison.
Barracks passes its bounded runtime/capture binding but **fails the mirror
comparison by 24,576 slot pixels** written after the full-blit mirror. All
outer margins match index zero. Its empty physical slot interiors cannot be
accepted as complete visual composition.

The expanded protocol authenticates native421240 entry/return, both required
artwork loads and a third when signed castle byte+4 equals1. The observed
castle0 byte is2, so these actual runs exercise two loads; the third branch is
fixture-covered only. The first protocol's missing later-load observations,
its hospital rejection and all earlier failures remain in the preserved
predecessor. Another hospital attempt remains failed for an initial-map
duplicate input/status event before capture. No game bytes changed for the
expanded debugger protocol. Native exit/free and complete primary composition
remain separate work.

## Pending route diagnostics

The [court and recruitment native contracts](FRAMED_CASTLE_REMAINING_ROUTES.md)
record exact entry/load/return boundaries, recruitment initialization, and
the remaining primary-composition capture limits. They are source diagnostics,
not additional implemented routes or visual passes.

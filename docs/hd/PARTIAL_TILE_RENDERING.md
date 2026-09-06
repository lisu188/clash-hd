# Partial map tiles: native evidence and standalone clipping code

Status on 2026-09-05: `src/patcher/partial_tile_clip.py` emits tested x86
clipping adapters, full/partial cell dispatch and a map composition tail for
command sprites and the AI-turn banner. It does not patch an executable,
reserve a game code cave, or install a hook. `installation_ready` is deliberately
false. The separate hook emitter, PE allocator and
`tools/build_partial_tile_candidate.py` now assemble a distinct
`-combinedui-partialtiles-validation` candidate. A separate initial-paint stage
now has bounded runtime passes, detailed below; modal-owner support and full
rendering acceptance remain outstanding. The earlier
[800x600](../../captures/current/partialtiles-noop-v4-800-action-bar-audit-current.json)
and [1024x768](../../captures/current/partialtiles-noop-v4-1024-action-bar-audit-current.json)
v4b action-bar audits each pass **6/6 complete cells**, matching their source
sprites exactly. Both runtimes remain **FAIL** on trace integrity and lack a full
convergence/presentation pair. Each diagnostic PNG is a separate conversion
of its observed raw surface with the recorded palette; its summary preserves
`Passed=false` and the original failed summary SHA. This proves only those
software-surface pixels, not full hidden-runtime acceptance, visible output,
manual input or promotion. The protected stable stage is unchanged.

The [initial map paint implementation](INITIAL_MAP_PAINT.md) adds a first-entry-only
post-UI native paint in the distinct
`-combinedui-partialtiles-initialpaint-validation` stage. The
[2026-09-05 runtime observation](../../captures/current/initial-map-paint-runtime-current.json)
records bounded hidden passes for runs `210832` at 800x600 and `211004` at
1024x768, with candidate SHAs
`e72a57fd3bb26509179e0b4360fc9134bef804e152ac338fcd755cdfa41c548f` and
`5ebbaf23ad999a97209a5e0ca8883e8d42e31190fb3891f03cfc3c38001bc338`.
Each passes loaded-byte, partial-status and initial-trace gates: **140 events**,
one complete initial convergence/presentation pair, 49 incremental calls and
37 matched native offscreen no-op exits, ending before the four-update
software capture. Return EAX is recorded without interpreting it as success.
Both [800x600](../../captures/current/initial-map-paint-800-action-bar-audit-current.json)
and [1024x768](../../captures/current/initial-map-paint-1024-action-bar-audit-current.json)
action-bar audits pass **6/6 complete source-matching cells**. Neither run
observed an AV or timeout. The 800x600 receipt verifies absence of recorded
game/CDB PIDs; 1024x768 verifies exact candidate-path/matching-debugger absence
after completion only, because its live query did not capture PIDs.

**The complete frame remains visibly incomplete in the saved software PNGs.**
User and agent inspection found the bottom frame missing and the right frame
discontinuous; the source cause is under investigation. The action-bar audit
does not check frame continuity. These captures do not establish full-frame
or final visible-wrapper composition, every terrain/scroll/world-edge case,
modal/army support, manual input, endurance or promotion. The new initial-paint
passes leave the earlier failed traces and their separate pixel results intact.

The [18:26Z screenshot inventory](../../captures/current/action-bar-complete-screenshot-inventory-current.json)
verifies the eight PNGs then present in its resolution capture roots:
six old failures and two v4b pixel passes. Another 12 saved soak frames
are separately audited failures. Those **20 screenshots** were checked without
reclassifying any earlier failure or treating pixel matches as runtime proof.
The two later initial-paint captures have separate audits linked above.

The first 800x600 run, `20260905-142409`,
[failed during pre-HD initialization](../../captures/current/partialtiles-800-pre-hd-failure-current.json).
Candidate SHA `B273C16822843D8AA684191E4C2F357E2F7C581BBC3AD7F4175C8D6B057ECAE8`
encountered a 640x480 surface, owner `004617A0`, and convergence status 0.
The guarded native fallback was reached before HD map initialization; the
diagnostic was armed prematurely. No AV or screenshot was recorded, and both
recorded processes stopped. Preserve that failed result; it supplies no
requested-resolution terrain or action-bar proof.

The generated probe now authenticates the five native bytes at `0040B88A`,
where the ordinary map owner has been installed before `UI_SetCurrentPlayer`.
Status and guard/exit breakpoints 70-72 and 74-75 remain disabled until that join observes owner
`0040AD40` and the exact requested surface dimensions. It emits one
`PTILE_MAP_READY owner=0040ad40 size=(W,H)`, enables the status breakpoints,
and disables the readiness breakpoint. The harness requires that exact
resolution-specific marker once, after the loaded contract and before every
status; missing, repeated, malformed, wrong-owner/dimension or out-of-order
readiness fails. The final v4b checkpoint passes the
[builder's 16 fixtures](../../tools/test_build_partial_tile_candidate.py)
and [harness's nine fixtures](../../tools/test_partial_tile_surface_harness.py)
covering 199 log cases, with synthetic evidence and mocked runtime boundaries.

The subsequent [v2 run `20260905-195041`](../../captures/current/partialtiles-latearm-v2-800-failure-20260905-195041.json),
under its [immutable run plan](../../captures/current/partialtiles-latearm-v2-run-plan-20260905-194900.json),
used the same candidate SHA and emitted
`PTILE_MAP_READY owner=0040ad40 size=(800,600)`. Four incremental status-1
returns were followed by status 0 and `PTILE_REJECT incremental`; no full
convergence/presentation pair or screenshot was reached. There was no observed AV,
and the terminal exit code was 1. Matching processes were absent afterward,
but live PIDs were not captured; the saved observation cannot establish
exact-PID cleanup retrospectively.

Status 0 has multiple source paths, including an offscreen world-tile
notification. The v2 log did not record the original world coordinates, so it
cannot establish that this particular rejection was offscreen or harmless.
The [v3 run `20260905-195807`](../../captures/current/partialtiles-inputdiag-v3-800-failure-20260905-195807.json)
records world `(90,7)`, map `(100,100)` and scroll `(10,17)` at the rejected
status-0 call. That cell lies outside the ceiling viewport, whose world bounds
are X=10..21 and Y=17..26. This identifies an offscreen notification; it does
not prove successful native fallback. Neither a composition-guard return nor
the native no-op exit was observed. The run remains **FAIL**, with no PNG or
full convergence/presentation pair, no observed AV, and recorded CDB PID 32676
and game PID 42256 absent at the terminal observation. Preserve all three
failed runs and their raw logs unchanged.

The final probe retains every raw input/status row and observes the authenticated
composition-guard return and native exit at `00418AFA`. The harness matches
guard, input, status and exit by actual thread, normalized native stack,
caller, world cell and context. Status 0 is accepted only for an in-world cell
wholly outside the ceiling viewport, with the exact normal-map owner, zero
callbacks, player 0 and native memory vtable, followed by its matching native
exit. It supplies no draw or present credit. Visible partial cells must draw;
status 2 is restricted to a visible out-of-world clear. Missing, duplicate,
unmatched or malformed events still fail, and a separate full convergence/
presentation pair remains mandatory. These observations do not change candidate
bytes or force game state.

The [immutable v4b plan](../../captures/current/partialtiles-noop-v4b-run-plan-current.json)
pins source/fixture/probe hashes and the unchanged 800x600 and 1024x768
candidate SHAs. Its [800x600 run `20260905-201619`](../../captures/current/partialtiles-noop-v4-800-observation-current.json) ended with exit 1 and the
strict error `incremental input or native exit lacks its guard and invocation`.
It recorded 327 incremental inputs, 327 incremental statuses, 244 native
no-op exits and 326 guards, including repeated/unmatched events and a pending
guard at host stop. It recorded zero full convergence/presentation markers.
The base `SURFDUMP_REDRAW` marker at `00406FA0` is a simulation observation,
not proof that the full redraw hook ran. An 800x600 raw surface was captured,
with no AV or timeout. Recorded CDB PID 42988 and game PID 38892 were absent
at **18:21:27Z**. Preserve the original failed summary and all trace rows;
the separate pixel audit must not deduplicate events or turn runtime green.
The [1024x768 run `20260905-202225`](../../captures/current/partialtiles-noop-v4-1024-observation-current.json)
also ended with exit 1: `repeated or out-of-order incremental input`. It
recorded 361 inputs, 361 incremental statuses, 359 guards and 266 native exits, with zero
full convergence/presentation markers. It captured a 1024x768 raw surface,
without AV or timeout. Recorded CDB PID 28444 and game PID 35832 were absent
at **18:25:10Z**. Its separate exact six-cell pixel pass leaves the failed
runtime summary and all trace rows unchanged. The saved plan remains a
preparation record; the linked terminal observations record execution. Every
saved screenshot still needs the complete source-pixel action-bar audit;
hidden software composition cannot prove visible output, manual input or
promotion.

## Why the earlier floor-loop candidates miss partial strips

The source is the user-owned original `C:\Clash\clash95.exe`, SHA-256
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
The local IDA exports `C:\Clash\clash95.asm` and `C:\Clash\clash95.c` explain
the control flow; the module verifies the actual PE bytes independently.

The gameplay viewport begins at `(32,16)`. Native `sub_418700` draws floor
counts of 64-pixel tiles. Its later right/bottom strip blocks call
`Render_FillRect` (`004024E0`) to copy already-rendered pixels; they do not
draw another terrain tile. Therefore the comment describing partial strips in
the existing resolution profile is not evidence that those strips render.

| Native VA / file offset | Original bytes | 1024x768 recipe | Meaning |
| --- | --- | --- | --- |
| `0041876E` / `00017B6E` | `83 F9 09 7C C4` | `83 F9 0F 7C C4` | 15 full columns |
| `0041877F` / `00017B7F` | `83 FF 06 7C A1` | `83 FF 0A 7C A1` | Ten initial full rows |
| `004189FD` / `00017DFD` | `83 F9 06 7C C3` | `83 F9 0F 7C C3` | Optional eleventh full row |
| `00418AA4` / `00017EA4` | `83 C1 09 39 C8 7D 4F` | `83 C1 0F 39 C8 7D 4F` | Incremental column admission |
| `00418AB1` / `00017EB1` | `83 C1 07 39 CA 7D 42` | `83 C1 0B 39 CA 7D 42` | Incremental row admission |

At 1024x768 the missing right strip is `x=992..1023`, and the missing bottom
strip is `y=720..767`. Their union contains 27 partial cells, counting the
bottom-right corner once. At 800x600 there are twelve bottom partial cells at
`y=592..599`. Existing floor-based present limits stop at `(991,719)` and
`(799,591)` respectively.

Increasing the loop counts alone is unsafe. The software write iterator at
`00403EF0` forms `pixels + width*y + x` without clipping. At maximum scroll,
an extra column/row also lies beyond the actual world width/height. Changing
the scroll clamp to ceiling counts would instead make part of the final world
tile unreachable. The helper keeps the full-tile clamp and clears the remaining
outside-world rectangle deterministically with native fog/background index 1.
That clear is not terrain-render evidence.

## Native write coverage

The memory surface has unsigned 16-bit width/height at `+0/+2`, a pixel pointer
at `+4`, and a vtable pointer at `+B8`. The authenticated memory table is
`0050EE24`; it does not have a general-purpose clip rectangle.

| Reachable write path | Scoped handling |
| --- | --- |
| `00416850` terrain, fog, buildings, grids | Sprite slot `+34`, fill `+1C`, line `+14` |
| `00415EA0`, `00415F20`, `00416750` units/effects | The same sprite slot, directly or through `00405510` |
| `00459ED0` effect entry | `00405560` preserves the sprite clip arguments |
| `0045C000`, `0045D430`, `0045F190`, `00419000` | Sprite slot, including the effect wrappers |
| `UI_DrawText` through `0040BC00` | Glyph sprites through `+34` |
| Registered tile callback `00429EC0` | Line `+14`, outline `+18`, sprite `+34` |
| Registered tile callback `00425120` | Road descriptor draw callback `004191F0`, then sprite `+34` |
| Tile tail `0040D560` | Existing authenticated minimap intersection before direct `004024E0`; outline goes through `+18` |

The tile callback at `0052698C` is accepted only when it is null, `00425120`,
or `00429EC0`. Unknown callbacks fail closed. Road descriptors `005142B8`,
`005142ED`, `00514322`, and `00514357` must retain draw callback `004191F0`
at `+1C`. Both road redraw calls pass `EDX=0`, so the descriptor drawer does
not immediately present a primary-surface rectangle. `00419D60` must retain
its original instructions with its x limit explicitly equal to the requested
surface width; retaining x<640 silently omits right-side road sprites.

The IDA name `Map_DestroyTile` at `0040DB80` is misleading in this graph: its
instructions classify/read terrain and call `0040F060`; they do not destroy a
tile or start a redraw. This conclusion comes from its instructions, not its
inferred name. Query helpers and sprite lookup are distinct from surface writes.

The minimap direct copy bypasses primitive clipping, so the original eight-byte
entry at `0040D560` must already be replaced by the established
`minimap-right-clip` hook `E9 1B C4 0D 00 90 90 90` and its exact 64-byte cave
at `004E9980`. Its original lower-edge intersection and remaining routine are
preserved. The helper is not permission to change minimap geometry, buffer
allocation, callback code, or the other native drawing graph. Its prerequisite
checks supplement the patcher's complete candidate byte gate; they do not
replace that gate or validate arbitrary game state.

## Emitted ABI and bounds

`emit_adapters(original, base_va=..., width=..., height=..., clip_origin=(0,0))`
returns code, exact entry VAs and relocation records. The edge bundle uses
`clip_origin=(32,16)`. Physical surface bounds `[0,0,W-1,H-1]` and gameplay
bounds `[32,16,W-1,H-1]` are separate contracts.

Line/fill/outline use `EAX=surface`, `EDX=left`, `ECX=right`, `EBX=top`, then
stack arguments bottom and color/flags. Callee cleanup is 8 bytes. Lines are
axis-aligned; dashed flags and absolute coordinate phase are retained. Outline
clipping applies to the four original segments, avoiding a new border along a
clipped edge.

Sprite uses `EAX=surface`, `EDX=sprite`, `EBX=x`, `ECX=y`, followed by inclusive
left/top/right/bottom clip arguments and the three original mode arguments.
Callee cleanup is 28 bytes. The all-minus-one quartet becomes the bounded
viewport, and explicit clips are intersected. Sprite decoding remains native.
This path accepts memory surfaces only: the DirectDraw primary-surface clipped
sprite implementation can request application shutdown and is not substituted.

`emit_edge_dispatch(original, candidate, base_va=..., width=..., height=...)`
also includes a cloned 20-entry memory vtable and these entries:

| Entry | Inputs | Result |
| --- | --- | --- |
| `edge` | `EAX=screen column`, `EBX=screen row`, `ESI=present` (0 or 1) | 1 drawn, 2 outside-world clear, 0 rejected |
| `edge_full` | `EAX=present` (0 or 1) | 1 only if every partial cell was handled |
| `edge_incremental` | `EAX=world x`, `EDX=world y` | Same result as `edge`; presents the partial cell |
| `cell` | Same inputs as `edge` | Also admits full cells for owner-safe incremental redraw |
| `cell_incremental` | Same inputs as `edge_incremental` | Admits visible full and partial cells |

The dispatcher validates dimensions, full-tile scroll bounds, the 100x100
backing-grid limit, callback class, and native lower-row ownership. It checks
actual world bounds before forming `gameData + 1400*x + 14*y`. Only valid
cells call native `00416850` with `AX=screen x`, `DX=screen y`, `EBX=tile`.
Outside-world cells use a bounded fill and never form a tile pointer. They then
call the authenticated `0040D560` minimap intersection with `AX=left`, `DX=top`,
`CX=bottom`, `BX=right` while the scoped map target is active. This retains the
right-anchored minimap where it intersects a far-world clear rectangle.

The current map vtable and `g_RenderDevice` are saved, replaced for the scoped
tile call, and restored exactly, including an already-active cloned context.
Caller registers other than EAX are preserved on return. When presentation is
requested, the native order is dirty helper `00460BB0` (exclusive right/bottom),
copy `004024E0` (inclusive source bounds), then `00460EA0` if the cursor was
visible. No instruction in the module is written to a candidate by these APIs.

## Source-backed map composition

`emit_map_composition(...)` adds a usable policy for the native map
to the edge bundle. It rejects other owners before making a drawing call:
`g_RenderHook` at `005199D8` must be `0040AD40`, the post-tile callback
`00526990` and lower-row owner `00526994` must be zero, the current player must
index one of the five native player records. That player's command-panel flag
at `gameData + 1423*player + 22313h` selects the native command-list or AI branch.
For the command list, the sprite set must be initialized and all six descriptor
positions/draw pointers plus the list terminator must match the authenticated
relocated layout. The AI branch requires its separate sprite set `005202DC`.

This restriction follows the original owners. `0040AD40` selects the command
list when the flag is set; otherwise it draws the AI-turn banner through
`0040A600`. Army display `00423760` / `00423B00` sets `00526994=1`. Modal
status/action composition is owned by the separate `004352B3` / `00435DA5`
routes. Re-entering those owners or update routine `0040ADF0` from a tile draw
would risk state/input processing and recursion. They are not used as redraw
callbacks here and are not claimed supported by this composition policy.

For an admitted map, `compose_panel` scopes the map target and clipped vtable,
then calls `00419D80` on `00511D40`. The native list drawer passes `EDX=0` to
each `004191F0` draw function. Existing state and hover bits select the sprites;
there is no hit test, click gate, callback activation or selected-unit mutation.
This redraw comes after edge terrain and minimap intersection. It also fixes
the ordering risk in the original initialization sequence `0040A400`, which
draws the command list before calling full terrain redraw.

The AI branch uses an authenticated clone of only `0040A600..0040A72A`.
Calling native `0040A600(EAX=0)` is insufficient: it skips the animation loop
but still reaches an unconditional primary copy at `0040A7B3`. The clone ends
before `0040A72B` (`Time_Now`) and appends the native register/render-target
restoration. It contains neither timing/animation nor primary presentation.
Its optional turn-number branch lands on that replacement epilogue. All six
direct calls and fifteen native HIGHLOW operands are independently checked
against the original instructions and relocation table.

The native banner begins at `(416,400)`, exactly the original first command
descriptor. The authenticated HD dock begins at `(W-192,H-72)`, so the clone
translates its nine sprite/text coordinates by `(W-608,H-472)`. This differs
from merely adding the physical resolution increase. The first sprite becomes
`(W-192,H-72)`, the second `(W-40,H-68)`, and the optional turn label
`(W-187,H-67)`. The formatted text retains its native relative layout, including
its right extent of `W`. Every coordinate change checks its native opcode and
old immediate; coordinate values are not loader relocations.

The tooltip requires different handling. `00422880` creates its saved
background and sets `00526EF8/EFC/F00/F04`. `004229A0` composes text directly
on the managed primary `0051D4C0`; `00422AC0` restores the primary background.
Those pixels are not part of the map software surface. `present_map_rect`
therefore subtracts the initialized tooltip rectangle from map copies, using
up to four disjoint rectangles. It copies every requested map pixel outside
that rectangle exactly once. The software map still contains fresh terrain
under it; primary-only tooltip pixels are preserved. This is an engine draw
policy, not a mask applied to a capture or a coverage result.

The tooltip pointer may be null before initialization. When nonnull, the
recorded bounds must be the actual source-defined HD map region:
`(160+(W-640)/2, H-14)..(473+(W-640)/2, H-1)`. Stale modal or unsupported
bounds fail closed. The presenter uses native dirty/copy ordering and draws
the cursor once after all accepted map rectangles.

| Additional entry | Contract |
| --- | --- |
| `compose_panel` | Validate owner, redraw current command sprites or docked AI banner offscreen; return 1/0 |
| `turn_banner_offscreen` | Internal scoped-target entry; EAX must be zero; authenticated drawing prefix only |
| `present_map_rect` | EAX left, EBX top, ECX right, EDX bottom, inclusive and already within gameplay bounds; preserve initialized primary tooltip; return 1/0 |
| `edge_composed` | EAX column, EBX row, ESI present 0/1; edge draw/clear, panel, then bounded presentation; return original edge status |
| `edge_full_composed` | EAX present 0/1; all partial cells, panel, then full gameplay presentation if requested; return 1/0 |
| `cell_composed` | Same contract as `edge_composed`, also admitting full cells |
| `cell_incremental_composed` | EAX world x, EDX world y; full or partial cell, panel, tooltip-preserving presentation |

All these entries preserve caller registers other than EAX. Rejection is an
observable unsupported state, never a rendering success. Frame gutters remain
outside their gameplay rectangle and belong to the existing frame-band hook.

## Caller integration contract

`src/patcher/partial_tile_hooks.py` implements the following three trampolines;
the separate candidate builder installs them with explicit displaced-relocation
handling. The clipping module alone still performs no installation.

The full-redraw convergence point `004187A0` (file offset `00017BA0`) starts
with `83 3D 90 69 52 00 00`: the seven-byte comparison of the post-tile callback
`00526990`. The byte-checked trampoline saves flags and registers, calls
`edge_full_composed` with present=0, records the exact result in the authenticated
per-call native stack local, restores flags and registers, replays
that exact comparison, and returns to `004187A7`. This places edge terrain and
clears before the callback and the existing frame-restore convergence at
`004187AF`; it does not replace either owner. Presentation requires an exact
successful convergence result from the same native stack frame.

After owner composition and frame restoration, full-redraw presentation must
use `present_map_rect(32,16,W-1,H-1)` or equivalent exact native rectangle
partitioning, rather than the current last-full-tile limits. Presenting edge
cells before composition while leaving the old full present limits would show
uncomposed tails. The existing frame bands, right-bottom status/actions and
minimap order must be retained.

The incremental admission path `00418A90` must route visible full and partial
cells through `cell_incremental_composed` before its native full-tile rejection.
This performs the supported panel/tooltip policy before exposing the changed
area, including full tiles overlapping relocated UI. The helper does not
silently patch the old full-tile path. Modal and army-row states still need
their own source-backed owner policy before a complete rendering stage can
support them.
A world-tile notification cannot clear a nonexistent world cell, so full/scroll
refreshes must also refresh outside-world tails. These caller changes, code
allocation and old-byte records are implemented by the separate builder, not
installed by the clipping module. A distinct validation-stage
suffix, complete byte gate, hidden rendering/coverage evidence, and separately
approved visible/manual evidence remain required. Nothing here is promotion.

## Verification completed

`python -B tools/test_partial_tile_clip.py` passed 22 focused tests on
2026-09-05. The suite compiles a temporary no-window x86 C# fixture and executes
the emitted machine code on synthetic memory. Native game entrypoints are
replaced by ABI recorders, except the authenticated AI drawing prefix itself
which executes with its downstream sprite/text calls recorded. An independent raster oracle checks bounded primitive
operations. Tests cover original SHA/bytes, missing minimap/changed callbacks,
descriptor width, all partial cells, far-world clearing, invalid context,
register/stack preservation, exact context restoration, native map ownership,
draw-only panel ordering, far-world minimap restoration, offscreen AI behavior
with and without turn text, and exhaustive pixel-set comparison for boundary and
randomized tooltip intersections. AI dock anchoring executes at 800x600,
1024x768, 1280x720, 1280x960, 1920x1080 and 802x602. This proves generated-code behavior with the stated native ABI. It
does not execute native sprite decoding or prove final game rendering.

Read-only prerequisite checks also passed against these existing candidates:

- Combined 800x600: SHA-256
  `0a75cf35f42efe1e44fba1ac4031eaae5323cdff51aa19d261c36c5bb84691c2`.
- Combined 1024x768: SHA-256
  `4f8fe0899593b2e2f7477518ee1ea05e1d0f21b0ceea9091507361d4a3504120`.

The edge-only bundles are 2510 and 3035 bytes respectively; adding the tested
map composition tail produces 4709 and 5234 bytes. Every composed bundle
declares 113 absolute and 18 relative operands, including all seventeen nonzero
cloned-vtable entries. The suite executes the emitted code again after applying
only its declared HIGHLOW fields at image delta `02000000`, checking table
pointers, callbacks, drawing context, text literals and native-call behavior.
The relocation validator also rejects invalid, duplicate and mismatched fields.

[PE code allocation](PE_CODE_EXTENSION.md) documents the independent allocator.
The [six-resolution allocation checkpoint](../../captures/current/partial-tile-allocation-current.json)
records successful in-memory construction against the earlier source SHA
`00006c157c35bfefd2e6f464df5e7c63ff00db400075c2afe8e4d9d7ead7d457`.
That diagnostic predates the nine AI coordinate changes; its payload hashes
are historical and must not be represented as the current anchored payload.
The code sizes and relocation locations are unchanged. Caller hooks and
displaced native relocation fields have separate exact contracts in
`src/patcher/partial_tile_hooks.py` and `src/patcher/pe_extension.py`; the
historical allocation checkpoint does not validate a later installed candidate.

These checks did not
alter either candidate or the original executable, and did not start the game,
CDB, a wrapper, input, or capture. All compiler and fixture binaries were
temporary; no proprietary binary is added to the repository.

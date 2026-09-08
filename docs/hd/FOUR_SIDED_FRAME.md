# Four-sided native map frame

Source integration updated 2026-09-06; native artwork audit dated 2026-09-05.
The separate framed builder now integrates geometry, frame drawing, terrain
clipping, mouse admission, initial/full painting and presentation. Its exact
validation stage is:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation
```

The [six-resolution matrix](../../captures/current/framed-map-resolution-matrix-current.md)
now contains bounded hidden runtime passes at **1024x768 and 802x602**, an
**800x600 runtime trace failure**, and **three wider-resolution gameplay
coverage heuristic failures**. All six software screenshots match all four
frame bands, the separate footer and six action-bar cells exactly. Pixel
success does not repair failed runtime gates or establish minimap-rectangle,
modal-screen, manual-input or promotion proof. The protected stable/default
stage and prior evidence remain unchanged.

## Implemented components

- [framed_viewport.py](../../src/patcher/framed_viewport.py) provides immutable
  `FramedViewport`, its disjoint frame/terrain rectangles, command footprints,
  dynamic minimap placement, full/ceiling cells and separate native-full-loop
  world admission.
- [frame_surface_audit.py](../../tools/frame_surface_audit.py) authenticates
  and decodes the user's actual FRAME resource in memory. Its
  `native_four_border_tiles_v1` oracle preserves corners, repeats only native
  edge strips, and draws footer 5 once. It distinguishes exact structural
  borders from footer background/text uncertainty; a footer mismatch does not
  become a full pass.
- [four_sided_frame.py](../../src/patcher/four_sided_frame.py) implements
  `frame_draw_plan(layout)` and
  `emit_frame_helper(original, *, base_va, width, height)`. The returned
  `AdapterBundle` contains `entries['draw_frame']`, emitted bytes and complete
  absolute/relative relocation records, with `installation_ready=False`.
  It neither modifies a candidate nor installs a native hook.
- [framed_recipe.py](../../src/patcher/framed_recipe.py) reconstructs a
  source-bound intermediate candidate in memory, changing only the declared
  terrain-count, scroll, command and minimap records. Physical surface and
  cursor dimensions retain their existing meanings. This base is not itself
  a complete framed runtime recipe.
- [framed_input.py](../../src/patcher/framed_input.py) emits the three mouse
  CALL wrappers and two fixed-panel JGE removals described below. The base
  recipe preserves the original input routines so all five later changes can
  be authenticated together.
- [framed_full_paint.py](../../src/patcher/framed_full_paint.py),
  [partial_tile_clip.py](../../src/patcher/partial_tile_clip.py) and
  [partial_tile_hooks.py](../../src/patcher/partial_tile_hooks.py) integrate
  framed clipping into native full and incremental drawing, then compose edge
  cells, frame and command/AI artwork in the admitted map context.
- [framed_presentation.py](../../src/patcher/framed_presentation.py) supplies
  guarded frame-band presentation and the separate native frame-entry wrapper.
  [initial_map_paint.py](../../src/patcher/initial_map_paint.py) connects the
  admitted first PlayGame paint after UI and HD readiness.
- [build_framed_candidate.py](../../tools/build_framed_candidate.py) is the
  explicit validation installer. It binds reviewed source hashes, canonical
  recipe bytes, emitted code, all hook/scalar records and PE relocations before
  producing a new candidate outside the repository. Individual emitters remain
  uninstalled components; the builder establishes their combined identity.

`draw_frame` has no arguments and reads the current map surface. It rejects
null/primary targets, wrong physical W/H, null pixel storage and any vtable
other than native memory `0050EE24`. Before the first draw, all five required
FRAME descriptor pointers must be non-null, have the exact native width/height,
encoding word zero at +4, and a non-null encoded-stream pointer at +0Ah.
The descriptors are cached only on the invocation stack. These checks assume
a live table owned by the native resource loader; they are not arbitrary
pointer validation or an authentication of runtime asset contents.

The helper draws explicitly clipped base sprites followed by footer 5,
always to the admitted memory map. It preserves the exact entry render-device
pointer, stack, flags and all GPR except its result EAX. It saves EBP across
every native call and clears DF immediately before each sprite call, then
restores the caller's original flags on return. Status 0 means admission
rejected before drawing; status 1 means the admitted calls returned. Neither
status alone proves resulting pixels or presentation. There are no primary
calls, vtable edits, resource allocations or persistent caches.

The earlier **31-test standalone checkpoint** comprised
[test_framed_viewport.py](../../tools/test_framed_viewport.py),
[test_frame_surface_audit.py](../../tools/test_frame_surface_audit.py), and
[test_four_sided_frame.py](../../tools/test_four_sided_frame.py), plus
[test_four_sided_frame_x86.py](../../tools/test_four_sided_frame_x86.py):
10 geometry, 10 pixel-oracle, 7 draw-plan and 4 emitted-x86 tests.
The frame-plan fixtures compare native 640 and all six HD cases against an
independent source-pixel oracle and check unchanged terrain pixels.

The current integrated source has these separate focused passing checkpoints:

| Scope | Focused fixture result |
| --- | --- |
| Canonical framed records | [11 recipe tests](../../tools/test_framed_recipe.py) |
| Mouse wrappers | [7 tests / 800 synthetic x86 cases](../../tools/test_framed_input.py) |
| Native full entry and restoration | [11 full-paint tests](../../tools/test_framed_full_paint.py) |
| Framed terrain, real frame helper and composition | [10 partial-tile tests](../../tools/test_framed_partial_tile.py) |
| Frame entry and primary presentation | [6 tests / 642 synthetic invocations](../../tools/test_framed_presentation.py) |
| Bound candidate construction | [14 builder tests](../../tools/test_build_framed_candidate.py) |
| Ordered initial-paint evidence | [17 trace tests](../../tools/test_initial_map_paint_trace.py) |
| Dimension-aware probe copy | [15 renderer tests](../../tools/test_render_cdb_surface_probe.py) |
| Stage-bound screenshot consumers | [8 coverage tests](../../tools/test_map_tile_coverage.py), [10 action-bar tests](../../tools/test_action_bar_surface_audit.py) |

The current PE fixture also passed 14 tests; the legacy partial builder and
initial candidate fixtures passed 16 and 4 respectively. These are distinct
source/integrity checkpoints, not a release-wide aggregate. The new framed
surface-harness fixture was still under review at this documentation checkpoint.
Synthetic x86 tests execute emitted instructions in isolated test memory; they
do not launch the game or provide manual-input observations.

## Evidence and scope

The [six-resolution manifest](../../captures/current/framed-map-resolution-matrix-current.json),
recorded 2026-09-06T02:52:50Z, binds the complete initial ordinary-map matrix:

| Resolution | Runtime gate | Initial trace | Four borders/footer | Action bar |
| --- | --- | --- | --- | --- |
| 800x600 | FAIL: duplicate native exit | FAIL | Exact PASS | 6/6 exact |
| 1024x768 | PASS | PASS | Exact PASS | 6/6 exact |
| 1280x720 | FAIL: coverage heuristic, no final summary | PASS | Exact PASS | 6/6 exact |
| 1280x960 | FAIL: coverage heuristic, no final summary | PASS | Exact PASS | 6/6 exact |
| 1920x1080 | FAIL: coverage heuristic, no final summary | PASS | Exact PASS | 6/6 exact |
| 802x602 | PASS | PASS | Exact PASS | 6/6 exact |

The three wide runs retain `low_overall_gameplay_coverage` and their original
logs/coverage reports; the harness stopped before producing final summaries.
Their separate diagnostic summaries do not replace missing successful
summaries. Each has 140 trace events and one full convergence/presentation
pair. A source-bound fog/coverage decision is under development, without
reclassification of these failures. The 802x602 run `044603`, candidate SHA
`dd54a298c4ab8e40db67ffff28672854b062c29554a16556a43f872ab28d4e3c`,
has an original passing final summary. The
[additional immutable plan](../../captures/current/framed-map-run-plan-20260906-023937.json)
binds those four candidates and source pins. Live PIDs were not recorded for
the additional runs; later exact-candidate/matching-CDB absence is the bounded
cleanup observation recorded in the matrix.

The [first two framed runs](../../captures/current/framed-map-runtime-current.json)
bind the detailed 800/1024 results to all 25 source pins in the
[immutable plan](../../captures/current/framed-map-run-plan-20260906-023304.json).

| Run | Candidate SHA-256 | Bounded result |
| --- | --- | --- |
| 800x600 `043323` | `7fad16f167205fb34ecbc99a6a1ff6180c710807f99b19f25efb48a8b1c8d15b` | Runtime FAIL; diagnostic frame/footer and 6/6 action cells PASS |
| 1024x768 `043513` | `3e9969a1e9285a9e65290072ea89cb2a3f224bd118ef267794fd1028ac5d7053` | Hidden surface, partial-status and initial-trace PASS; frame/footer and 6/6 action cells PASS |

The [800 frame audit](../../captures/current/framed-v1-800-frame-audit-20260906.json)
matches 57,092 structural border pixels plus all 4,860 footer pixels. The
[1024 audit](../../captures/current/framed-v1-1024-frame-audit-20260906.json)
matches 75,012 plus 4,860. The
[action-bar audit](../../captures/current/framed-v1-action-bar-audit-20260906.json)
matches every pixel in all six cells at each resolution. The 800 diagnostic
summary retains `Passed=false` and binds the unchanged failed original summary;
only its previously captured raw surface was converted to a separate PNG.

The 1024 log has 140 events, one initial full pair, 49 incremental inputs and
37 native no-op exits. The 800 log has 141 events and 38 exits: events 81/82
repeat the same native exit at EIP `00418AFA`, TID `2A28`, ESP `000EDC7C`,
world `(60,47)`. The second has no fresh guard/invocation and fails the strict
trace at line 395. That failure remains recorded without deduplication.
Neither run reports an AV or timeout. The recorded CDB/game PIDs
14244/39120 and 33104/31664 were all absent in explicit `Get-Process` checks at
2026-09-06T02:39:37.7159976Z. The report retains raw and LF-normalized probe
hashes, because Windows CRLF materialization differs from the planned LF text.
These results do not establish manual input, final wrapper composition,
far-world visibility or modal/army owner behavior.

The two earlier, unframed initial-paint runs in
[initial-map-paint-runtime-current.json](../../captures/current/initial-map-paint-runtime-current.json)
prove their recorded hidden route, initial full-paint trace, and software
action-bar composition. The separate
[frame asset audit](../../captures/current/initialpaint-frame-asset-audit-current.json)
finds the requested right and bottom frame incomplete. This does not invalidate
the bounded action-bar results, or reopen the resolved July right-bottom
promotion-gate design question.

The 1024 screenshot's left band below row 600 matches all 5,376 expected source
pixels; its top extension matches all 6,144. There is no supported left-cutoff
defect. The installed 217-byte C5 cave has the correct `SHIFTY=288` and
`SHIFTX=384`. A dark seam near the old 640-wide boundary is not established as
native frame artwork. The integrated framed source and new frame-pixel results
address that layout; these old runs themselves prove no new framed behavior.
Their top/left audit uses the old 160/120-pixel extension recipe; it is not a
pass against the new oracle's 576/448-pixel interior-strip tiling phase.

Native source: user-owned `C:/Clash/clash95.asm`, function `00406740`, and the
known original `C:/Clash/clash95.exe`, SHA-256
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
All addresses below are preferred-base VAs unless explicitly labeled file
offset. Source and asset hashes are also bound by the frame audit. No game
assets are copied into the repository.

## Native artwork and draw contract

The map frame is the **root** `FRAME.S32` member of `C:/Clash/DATA/GFX3.RES`:

- Archive SHA-256: `31489538e8b98d180b434151db8260d00edf5ce9dd98e9f80e1d4e0607e3f525`.
- Member offset `0x1CC2CF`, length 89,593, SHA-256
  `8501cbae69c35aa5a804823227bbd56fb21e84b4f1e5c0f15e4419f522c4053d`.
- It is not the battle `GFX/BATTLE/FRAME.S32` member in `minimum.res`.

`0040B003` loads the frame table stored at `005202BC`. `00406740` draws the
following sprites first to map surface `005202E0`, then to primary `0051D4C0`:

| Sprite | Native origin | Dimensions | Role |
| --- | --- | --- | --- |
| 0 | 0, 0 | 314 x 237 | Upper-left part |
| 1 | 314, 0 | 326 x 238 | Upper-right part |
| 2 | 0, 237 | 315 x 243 | Lower-left part |
| 3 | 315, 238 | 325 x 242 | Lower-right part |
| 5 | 155, 465 | 324 x 15 | Separate tooltip footer |

The opaque union of sprites 0..3 is exactly the native 32-pixel left/right
bands plus 16-pixel top/bottom bands: 49,152 pixels. Their interior
`(32,16)..(607,463)` is transparent. The footer is a separate overlay, not a
source strip to repeat across the bottom border.

`DLX_GetSpriteForChar` at `00405EC0` is `MOV EAX,[EAX+EDX*4]; RET`: EAX is the
resource table and EDX is the sprite index. It does not validate the entry.
The memory sprite primitive at `00402E80` takes EAX=surface, EDX=sprite,
EBX=destination X and ECX=destination Y. Its seven stack arguments are
inclusive clip left, top, right, bottom, then native mode values `1,0,0`.
Push them in reverse order; the callee returns with `RET 1Ch`. Source decoder
entry bytes are `56575589e581ec0401000083ed6a`.

Explicit clipping is suitable for the authenticated memory target. It is not
a safe direct-primary recipe: when `0051D018 != 0` and the target is primary,
the native sprite path requests quit for explicit clips. Draw clipped frame
pieces into the memory map surface, then use the native blit for presentation.
Do not leave the terrain-clipped vtable installed while drawing the frame.

The implemented map-only helper follows the preserving contract above. The
sprite routine's incidental EAX is not a success result. Runtime descriptor
dimensions have **width in the low word, height in the high word**:
`00406260` copies the ten-byte S32 header unchanged, then installs the stream
pointer at +0Ah. Decompiled `DLX_GetSpriteWidth`/`DLX_GetSpriteHeight` labels
are misleading. For example, sprite 0 starts `3A01ED00000001000000`, giving
width 314, height 237 and encoding 0; transposing those dimensions must reject.

## Physical surface and gameplay layout

The independent [framed_viewport.py](../../src/patcher/framed_viewport.py)
provides the pure `FramedViewport` geometry. It installs nothing. Keep W/H as
the physical allocation, stride, display and cursor dimensions; do not change
the global meanings of the existing patcher's `W` and `H` formulas.

| Item | Framed formula, inclusive unless stated |
| --- | --- |
| Physical surface | `(0,0)..(W-1,H-1)` |
| Terrain | `(32,16)..(W-33,H-17)` |
| Terrain dimensions | `W-64`, `H-32` |
| Full native tile counts TX/TY | `floor((W-64)/64)`, `floor((H-32)/64)` |
| Complete-tile right/bottom | `32+64*TX-1`, `16+64*TY-1` |
| Edge cell counts | `ceil((W-64)/64)`, `ceil((H-32)/64)` |
| Partial strip widths | `(W-64)%64`, `(H-32)%64` |
| Six command cells | X=`W-224+64*column`, Y=`H-80+32*row`, 64 x 32 |
| Command footprint | `(W-224,H-80)..(W-33,H-17)` |
| Minimap right anchor | `W-32`, **exclusive** |
| Footer sprite 5 | `155+(W-640)/2`, `H-15` |

For the footer, preserve the native three-pixel center asymmetry; do not
substitute `(W-324)/2`. Existing tooltip text starts at `160+OFFX,H-13`, with
right coordinate `473+OFFX`, so the footer retains its native five-pixel
left and two-pixel top inset. The four current tooltip initializer contexts
already use these translations and need no framed-stage shift.

| Resolution | Full tiles | Ceiling tiles | Partial right/bottom | First command |
| --- | --- | --- | --- | --- |
| 640 x 480, geometry oracle only | 9 x 7 | 9 x 7 | 0 / 0 | 416,400 |
| 800 x 600 | 11 x 8 | 12 x 9 | 32 / 56 | 576,520 |
| 1024 x 768 | 15 x 11 | 15 x 12 | 0 / 32 | 800,688 |
| 1280 x 720 | 19 x 10 | 19 x 11 | 0 / 48 | 1056,640 |
| 1280 x 960 | 19 x 14 | 19 x 15 | 0 / 32 | 1056,880 |
| 1920 x 1080 | 29 x 16 | 29 x 17 | 0 / 24 | 1696,1000 |
| 802 x 602 | 11 x 8 | 12 x 9 | 34 / 58 | 578,522 |

Native `0040D330` sets minimap Y=16 and backing width/height to
`scale*world_dimension+14`, where scale is 4 for world area <=2500, otherwise
2. `0040D390` subtracts that width from exclusive-right anchor 608. The
100x100 backing is 214x214; FRAME sprite 4 is 214x213. Do not confuse them or
hardcode the backing dimensions. Preserve the existing right-clip correction
and use the actual runtime backing dimensions for draw and hit exclusion.

The **viewport rectangle has a separate optional correction and six exact
pixel passes**, documented in [MINIMAP_VIEWPORT.md](MINIMAP_VIEWPORT.md) and
the [runtime matrix](../../captures/current/framed-minimap-runtime-current.md).
Native `0040D560` adds 7 to scroll Y and 9 to scroll X, describing the old
9x7 window. The opt-in `--minimap-viewport` revision hooks its active path
after backing repair at `0040D633`, projects actual framed pixels including
partial tiles, and leaves the unreferenced `0040D450` path unchanged. Candidate
`69899e07f70dde2094264be694300e00c7a778f1391ac7797b74c59c56ee1ce0`
has a [bound actual outline](../../captures/current/framed-minimap-v1-1024x768-viewport-20260906.json)
at `(804,56)..(835,80)`, with **110/110 perimeter pixels** matching index `4C`.
Its 960x736 terrain pixels project to 30x23 at measured scale 2. All six
new-revision captures also pass their separate frame/footer/action-bar checks,
but runtime passes only at 800x600, 1024x768 and 802x602. The two 1280 coverage
failures and 1920x1080 strict trace failure remain unchanged. Actual
panning/old-outline erasure, scale-4 runtime and far-world captures remain
pending; bounded pixel passes cannot substitute for those checks. The stage
remains validation-only and no stable promotion follows from these results.

Keep scroll limits based on **full**, not ceiling, counts. At the far world
edge, the last valid full tile remains complete and any partial tail outside
the world is deterministically cleared inside the terrain rectangle. A
geometry plan for a smaller world is not permission to call the native full
loop: current admission additionally requires world dimensions 1..100,
world >= full counts, and `0 <= scroll <= world-full_counts`. Supporting
smaller worlds needs guarded drawing/clearing of full cells too.

## Exact existing recipe inventory

The source registry is
[patch_clash95_hd.py](../../src/patcher/patch_clash95_hd.py), `RECIPES` and
`STAGE_GROUPS[DEFAULT_STAGE + '-combinedui-validation']`.
[framed_recipe.py](../../src/patcher/framed_recipe.py) derives the separate
framed base from these source-bound records, authenticating the original SHA,
original bytes and expected combined candidate bytes. It does not register a
new default selection or search/replace coordinates. The existing values below
describe the protected combined base; the following are **file offsets**.

| Formula | Existing sites that must use framed terrain counts |
| --- | --- |
| TX, main loops | `6423,674B,683A,6907,69CF,6AC1,6BEF` |
| TY, main loops | `63E9,66F7,6814,68E1,69A9,6A93,6B9F` |
| TX, full redraw | `17B70,17DFF` |
| TY-1, full redraw | `17B81` |
| TX, helpers | `7080,71D5,EF4E,F35B,17EA6,17EDB,18009,18067,18112` |
| TY, helpers | `70B4,7268,EF66,F39E,17EB3,18016,18080,1812A` |
| -TX / -TY | `7087,EF9D` / `70BB,EF6D` |
| TX/2 / TY/2, integer floor | `EF01` / `EF18` |
| TY-1, helpers | `17ECC,17EEC` |
| -(TY+1) / -(TX+1) | `18087,18131` / `180C2,18163` |
| Complete-tile right | `17CDE,17D6C,17D82,17E68` |
| Complete-tile bottom | `17D99,17E5E` |

The single-byte count records have signed-imm8 encoding. Preserve their
range checks. Native old TX/TY are 9/7; the specialized native last row uses
6. The full-redraw right/bottom old dwords are `5F020000` / `CF010000`
(607/463). These remain complete-tile boundaries, distinct from the clipped
partial-tail boundary.

Additional selected records:

- `helpers D0B0`: old `83EE09`, replace its TX immediate. `D0DA,D124`:
  old `83EA07`, replace TY. These are minimap scrolling paths, not menu input.
- `map-surface-upgrade-scrollclamp E8C80`: change only the source-declared
  `SUB EBX,TX/TY` slots. Keep its W/H width test and allocations physical.
- `minimap-hd-right-anchor C790`: VA `0040D390`, old `BA60020000`; the
  framed instruction is `MOV EDX,W-32`, not the current `MOV EDX,W`.
- Command descriptor XY pairs at `10FF40,10FF75,10FFAA,10FFDF,110014,110049`
  are VA `00511D40+53*i`. Their native coordinates are the 3x2 grid at
  X=416/480/544, Y=400/432. Replace the current `W-192/W-128/W-64` and
  `H-72/H-40` with `W-224/W-160/W-96` and `H-80/H-48`. Preserve all other
  descriptor fields, callbacks and the shared native draw/hit linkage.
- Descriptor redraw clips `19165,1918E` can retain physical W: moved sprite
  bounds provide the stricter footprint. They are not a general terrain clip.
- Physical records stay physical: display `3A64,3A69,60EAD,60EB2`, shared
  allocation `E4D,E62`, gameplay allocation `A3BF,A3C4`, global mouse bounds
  `5F826,5F82D`, viewport initializer `5F92D,5F93B`, and the W/H allocation
  fields in dynamic viewport cave `E8DC0`. Menu/castle/battle OFFX/OFFY remain
  centering of native 640x480 in the actual physical surface.

Do not silently reuse the resolved `right-bottom-compose-proof` owner-copy
coordinates as a framed proof. Its `1114E0` cave copies source
`(401,288)..(593,357)` (193x70) to `(W-214,H-72)`, ending at `(W-22,H-3)`;
its `112080` cave copies `(285,350)..(450,425)` (166x76) to `(285,H-76)`,
ending at H-1. Both overlap the newly reserved border. Their owner-specific
destinations need a separate explicit mapping and matching input/composition
proof, not clipped-away pixels or an assumed command-grid delta. An initial
ordinary-map validation retains a strict owner admission limit while this
integration remains incomplete. Specifically, modal calls `004352B3` to
`005132E0` and `00435DA5` to `00513E80` retain the overlapping copies above.
The army route `00423860` retains native Y=400..463 and a separate, unwrapped
input path. These are unfinished framed-owner work, not reopened July gate
design questions. Native fallback for these owners is not framed layout or
input proof.

## Mouse admission is part of the new stage

Changing TX/TY or the physical cursor maximum does not establish terrain
input bounds. Native logical coordinates are mouse globals `00544CFC` and
`00544D00`, shifted by `0054512C`; world conversion is
`scroll + (logical-(32,16))/64`.

- `004084A0` checks only X>=32/Y>=16 before conversion and world checks. It
  retains a native row-6/column>=6 panel exclusion. It has no matching new
  right/bottom frame exclusion.
- The mouse branch of `00407D20`, at `00407F4C`, converts coordinates and
  then accesses world data after the native mouse gate. Keep its earlier
  keyboard scroll handling intact.
- `00408030` also converts directly and retains the fixed native panel
  exclusion. `0040DD60` excludes the enabled minimap using its runtime bounds;
  it is not a general terrain/frame guard.

The emitted input bundle authenticates these instruction-aligned sites. The
framed builder installs all five together, after reconstructing the canonical
base with unchanged native input routines:

| VA | RVA / file offset | Native bytes | Framed role |
| --- | --- | --- | --- |
| `004084A9` | `84A9 / 78A9` | `E8B2580000` | Wrap CALL `40DD60`, retaining native minimap result and adding frame/control/world admission |
| `00407F3C` | `7F3C / 733C` | `E81F5E0000` | Same wrapper, only after keyboard handling |
| `00408039` | `8039 / 7439` | `E8B2880500` | Preserve CALL `4608F0` native click gate; additionally deny invalid terrain/overlays before world access |
| `0040855D` | `855D / 795D` | `0F8D86020000` | Replace fixed panel-exclusion JGE with six NOPs, bound to the replacement pixel guard |
| `004080AA` | `80AA / 74AA` | `0F8D86000000` | Same fixed-panel exclusion in the second route |

These five spans contain no original HIGHLOW field. The three replacement
CALL displacements are rel32; emitted absolute references have explicit HIGHLOW
records. The minimap wrapper returns 1 to deny and 0 to continue; the click
wrapper returns 0 to deny and 1 to continue. The latter calls native `4608F0`
first with its original EAX object argument. Native minimap results and order
are retained. Wrappers preserve the stack, entry flags and all GPR except EAX;
the native callers consume the result with `TEST EAX`.

Admission requires the physical memory map, ordinary owner `40AD40`, zero
lower/post callbacks, accepted tile callbacks `0/425120/429EC0`, and current
player 0..4 with its interactive flag set. The independent minimap player
selector at game data +`23EC7` must also be 0..4. Its enabled flag is game data
+`2230F + selector*58F`. Runtime minimap X/Y/W/H are unsigned words at
`00523344/346/348/34A`. The native strict-interior minimap gate is retained,
and the wrapper additionally excludes the complete enabled backing, including
its boundary pixels, at `W-32-backing_width,16`.

Signed, shifted mouse coordinates must lie inside the framed terrain and
outside the relocated command/minimap footprints before world access. World
dimensions 1..100, full-count scroll limits and the partial outside-world tail
are checked before forming world pointers. Fixtures execute the actual native
predicates and emitted wrappers, including newly valid old row-6/column-6
terrain, relocated controls and invalid contexts. Keyboard/menu routes remain
unchanged; no input injection or manual proof is supplied by these tests.

## Frame composition and integration order

The existing combined-stage C5 `frame-restore-bands` replaces native VA
`004187AF`, file `17BAF`,
old bytes `85ED0F84EC010000`, with a jump to `0051BE00` (file `11A000`). It
extends only left/top by copying from the already drawn native map. It cannot
restore right/bottom pixels that terrain has overwritten. Its original hook
span contains no HIGHLOW. The framed full-entry integration bypasses this C5
only when the per-native-invocation success latch is 1. Other paths retain its
native fallback. The protected combined recipe remains unchanged.

Native frame entry `00406740`, RVA `6740`, file `5B40`, starts
`5351525657` (PUSH EBX/ECX/EDX/ESI/EDI). The framed presentation bundle emits
the guarded five-byte entry hook, installed by the validation builder. It
replays those instructions and falls back to `00406745` before admission;
no HIGHLOW is displaced. Its first
subsequent `MOV EAX,[005202E0]` has a relocation, so do not extend the stolen
span without accounting for it.

The two implemented contracts remain distinct. Native `406740` draws both
targets and leaves `g_RenderDevice=primary`; the admitted native-entry wrapper
preserves that poststate after drawing the memory frame and presenting its
bands. The map-only helper restores the caller's exact device pointer.
Owner `40AD40` calls native frame drawing before descriptor drawing/full
redraw; PlayGame also draws the frame before the HD surface is ready. An
entry hook alone therefore cannot supply the first complete HD frame.

The implemented helper and oracle supply the crop/repeat recipe: explicitly
clipped sprite 0..3 pieces into the authenticated memory map, then sprite 5
once, preserving corner ownership, native palette indices and transparency.
They embed no proprietary artwork in emitted code and do not sample an
already composed footer as a repeat strip.

The guarded full entry at `00418700` authenticates and replays the nine-byte
native prologue before body `00418709`. It scopes the clipped vtable around
the native full loop, then convergence restores the memory vtable for edge,
frame and panel drawing. The outer entry restores the exact saved vtable and
native return/register/flags/stack contract. Its additional 60-byte stack scope
makes the framed full-status-to-initial-caller offset 148 bytes, distinct from
the old trace's 88; the generated contract and verifier use that distinction.

The admitted ordinary-map/AI path implements this composition sequence:

1. Draw complete and partial terrain with all transitive writes clipped to
   `FramedViewport.terrain`; clear out-of-world tails only inside that rect.
2. Rebuild all four frame bands and the footer on the memory surface after
   initial HD readiness and admitted full-map restoration.
3. Compose the admitted command/AI panel and retain native minimap/tooltip
   ordering. Unsupported modal/army owners remain on native fallback and do
   not satisfy this framed claim. Drawing the footer after tooltip text would
   erase that text.
4. Present both terrain and changed frame/footer bands when the caller's
   present flag requires it. A map-interior-only present omits the new borders.
   Offscreen requests must perform zero primary writes. Restore original
   vtable, surface pointer and render-device state according to each entry's
   contract. The full-map presenter preserves the primary tooltip rectangle;
   the native frame-entry wrapper separately reproduces native footer drawing.

Frame-band presentation validates a distinct same-size 8-bit primary with its
native backend, surface and Lock/Restore/Unlock entries. It does not pretend the
primary has memory-map pixel storage. Four disjoint native blits cover the
bands; present=0 returns without primary access. Completed native calls remain
separate from proof of resulting visible pixels.

For incremental draws, a correctly clipped terrain cell cannot overwrite the
frame. Keep existing post-cell command/minimap composition; do not redraw the
footer on every tile and erase its text. The native blitter `004024E0` uses
EAX=source, EDX=destination (0 means primary), EBX/ECX=source left/top;
stack args are source right/bottom and destination left/top, all inclusive,
with `RET 10h`. Memory iterators `00403EB0/00403EF0` use actual width as
stride and do not enforce a 600-pixel bottom cutoff. They also do not rescue
an invalid caller rectangle: every transfer needs explicit source/destination
bounds.

## Integrated builder, consumers and remaining validation

The standalone geometry, asset oracle and frame helper remain independently
testable. The validation builder now verifies the chain from known original
through canonical combined records, explicit framed scalar/data overrides,
emitted frame/input/partial/initial hooks, and the added PE code section.
[pe_extension.py](../../src/patcher/pe_extension.py) reconstructs and binds the
framed base explicitly. It preserves unrelated relocation entries and original
relocation bytes, removes only declared complete displaced HIGHLOW fields,
and records new absolute and relative fixups separately. This does not excuse
an unexplained candidate or infer fixups by scanning instruction bytes.

The builder's `--preflight` reconstructs the candidate in memory and reports
its identity. Its output path requires a distinct candidate under
`C:/ClashTests`, with source/probe metadata outside the repository; output
files must not already exist. No proprietary artwork is embedded or extracted
into the repository. Runtime and promotion flags remain false in build-only
metadata.

The integrated consumers select the exact framed stage rather than interpreting
every HD surface as framed:

- The partial/full/initial emitters take `FramedViewport` explicitly and
  authenticate the source-canonical framed base. Native full counts and scroll
  limits use floor counts; clipped edge work uses ceiling counts. Their map
  size and allocation checks retain physical W/H. Existing default profiles
  retain their prior emitted bytes and geometry.
- [render_cdb_surface_probe.py](../../tools/render_cdb_surface_probe.py) renders
  a copy of the base probe, including the framed 800x600 case. Physical stride
  and native menu/load-slot coordinates remain unchanged. Full-loop/end-grid
  observations use floor counts; visibility dumps cover ceiling cells.
- [initial_map_paint_trace.py](../../tools/initial_map_paint_trace.py) binds
  stage, dimensions, candidate SHA and generated probe to the declared framed
  scope. It requires ordered admission, readiness, matched full converge and
  present, native return and a complete-call trace closure. Event identity,
  stack differences and all duplicate/out-of-order records remain visible;
  generic surface success cannot replace this trace contract.
- [run_cdb_surface_dump.ps1](../../scripts/cdb/run_cdb_surface_dump.ps1) exposes
  explicit `-FramedValidation` together with the partial-tile and initial-paint
  validation flags. It runs pure preflight before candidate/proxy construction,
  compares the actual build SHA to preflight and keeps the existing hidden-run,
  original-file, load-route and error boundaries. The final dump is paused at
  the update-entry complete-call boundary. It requires exactly one
  `FRAMED_MINIMAP enabled=0|1 origin=(X,Y) size=(W,H)` observation, with the
  source-derived selector/enabled checks and actual unsigned-word dimensions.
- [map_tile_coverage.py](../../tools/map_tile_coverage.py) requires the exact
  stage and observed minimap enabled state, plus actual backing dimensions
  when enabled. It checks the clipped ceiling grid inside the terrain, masks
  the relocated command footprint and enabled backing, and rejects explicit
  grid/arbitrary-mask overrides for this profile. Masked UI pixels remain
  unmeasured terrain, not a terrain pass.
- [action_bar_surface_audit.py](../../tools/action_bar_surface_audit.py) selects
  the framed first cell at `W-224,H-80` and compares all six cells against the
  authenticated source artwork. Raw surface, PNG, palette, dimensions and
  candidate identity remain bound to the supplied summary. The separate frame
  oracle checks all four borders and footer. A pixel pass never changes an
  original failed runtime summary into a runtime pass.

The **current screenshot lane requires every ceiling cell to be in the world**
at its capture boundary, with the existing player-0 visibility scope. The
native bitmap is a 100x100 world stored with 13 bytes per column; outside-world
padding cannot be treated as visibility evidence. The renderer therefore
rejects a far-edge capture whose partial ceiling cell is outside the world,
even though native scroll limits correctly remain based on full counts and
synthetic rendering tests cover cleared partial tails. Current screenshot
coverage does not prove those far-world clears. Supporting that capture lane
requires an explicit outside-world visibility/clear contract.

The focused checks above cover native artwork reconstruction, all six listed
HD geometries, clipped primitive execution, unchanged terrain/frame canaries,
register/flags/stack preservation, relocation rebasing, rejected targets and
present=0 primary-write exclusion. They establish source readiness for bounded
validation, not game input or visible composition. The current actual evidence
is the six-resolution matrix above: two bounded runtime passes and six exact
frame/action-bar pixel passes, with the four failed runtime outcomes preserved.
Failed resolution gates, the minimap rectangle, broader owner restoration,
far-world captures, approved visible composition and manual callback/input
proof remain separate claims. The requested castle, building and battle
coverage has its own [source-bound screen inventory and pending matrix](FRAMED_SCREEN_VALIDATION.md).
The existing framed map harness does not admit those modal routes. No stable
promotion is asserted here.

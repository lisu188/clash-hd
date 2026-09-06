# Tactical battle HD: horizontal viewport and edge controls

On **2026-09-06**, the user selected: **“Use more screen width, keep crisp
native-size sprites, and anchor controls to the edges.”** This is the design
direction for a new validation stage. It is not stable-stage promotion.

The implemented [geometry model](../../src/patcher/framed_battle_viewport.py)
is currently **uninstalled**: it changes no game bytes. Its
[six focused fixture groups](../../tools/test_framed_battle_viewport.py) passed
on 2026-09-06. This document distinguishes that geometry and native source
inspection from the rendering, input, animation, and runtime work still needed.

## Geometry contract

Keep the field origin at `(32,16)`, with native `64×64` cells and **seven
actual arena rows**. Retain the battle's actual column count, which is at most
20. Define a separate visible-column count:

```text
visible_columns = min(world_columns, floor((width - 32 - 160) / 64))
max_scroll_x = world_columns - visible_columns
field = (32,16)..(31 + 64 * visible_columns,463), inclusive
```

| Resolution | Visible columns when the arena has 20 | Actual rows |
| --- | ---: | ---: |
| 640×480 | 7 | 7 |
| 800×600 / 802×602 | 9 | 7 |
| 1024×768 | 13 | 7 |
| 1280×720 / 1280×960 | 17 | 7 |
| 1920×1080 | 20 | 7 |

Whole cells avoid introducing partial-cell rendering in this first lane.
Space below the field and any gap before the HUD are decorative and inert;
they do not add combat rows or columns. Reject coordinates outside the exact
field rectangle **before** calculating an index into native battle arrays.
Clamp every scroll origin to `0..max_scroll_x`, including saved player views,
keyboard/drag movement, selected-unit centering, and ranged-attack centering.

The geometry model gives the 160-pixel HUD its own native backing. Its source
and destination rectangles are inclusive, with no scaling:

| Native HUD source | Destination | Purpose |
| --- | --- | --- |
| `(480,0)..(639,367)` | `(W-160,0)..(W-1,367)` | Top widget and unit statistics |
| `(480,368)..(639,479)` | `(W-160,H-112)..(W-1,H-1)` | Bottom command panel |

The intervening vertical gap has no native descriptor coordinates. Input maps
each admitted HUD slice back to its original coordinates; it must not pass
padding through to a widget. Native battle content reaches x623/624. Therefore
the proposed outer frame uses a **16-pixel right band**, 32-pixel left band,
and 16-pixel top/bottom bands. These are geometry contracts only. A source-pixel
composition recipe must still define edge and corner ownership. Painting the
ordinary map's 32-pixel right frame over the HUD would cover its content.

## Native source and byte observations

The inspection used the user's local `clash95.asm`, `clash95.c`, and executable
on 2026-09-06. The executable was read only and has SHA-256
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
Decompiler names are hints; the register ABI, assembly, bytes, and asset headers
take precedence. No proprietary source or asset is added by this document.

The inspected 1024×768 framed modal-canvas candidate has SHA-256
`c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d`.
It still has the inherited centered battle presentation and input wrappers.
It is not a tactical HD candidate.

| Native boundary | Observed behavior and required expansion |
| --- | --- |
| `0042E9E0` battle runner | Allocates battle state at `[00532048]`. State `+800` is assigned 7 rows; `+804` is the actual column count inferred from arena data, up to 20. `+808/+812` are scroll X/Y. Do not enlarge the combat-world fields to represent viewport dimensions. |
| `00430C20` full redraw | Selects `[005202E0]` as `g_RenderDevice`. `00430C39` loads EDI=7, shared by **both** column and row loops. Replacing this one immediate would incorrectly expand rows. The X addition at `00430C4F` and Y addition at `00430C66` need separate treatment. |
| `0042FFB0` tile draw | Computes screen X/Y from world coordinates minus scroll, scaled by 64, plus `(32,16)`. Uses the current render device and per-cell clipping for layered artwork. Reuse native sprite scale and tile composition; do not enlarge the art. |
| `0042C0F0` visibility | Native X limit uses `ADD EBX,7` at `0042C104`; the separate Y limit remains seven rows. Visibility must match the new field for animation and selected-unit routing. |
| `00430B20` incremental redraw | X `ADD ESI,7` is at `00430B33`; Y's identical instruction is at `00430B46`. This path redraws a cell and copies/presents its native-size rectangle. Updating only full redraw would leave animated/newly changed columns stale. |
| `0042C840` pan/drag | Right-key X limit is at `0042C942`; drag X limit is at `0042CAA5`, followed by the old `world_columns-7` clamp. The corresponding Y limits stay unchanged. At `0042C870`, native mouse-to-cell conversion precedes an unchecked occupancy lookup: add field admission before that lookup, including on calls during movement animation. |
| `0042CB50` tactical hit | X `CMP EBP,7` is at `0042CBAA`; Y `CMP EAX,7` is at `0042CBB3`. The native division truncates signed values; explicit pixel bounds must precede division so pixels just left/above the field cannot become cell zero. |
| `00426E20` center on unit | Uses X minus 3 and clamps to `world_columns-7`; replace the X center/clamp together. Preserve Y behavior. |
| `00428880` shot animation | Has a separate midpoint-centering block with X minus 3 and `world_columns-7`. It does not exclusively use `00426E20`. The expanded visibility and this fallback centering must agree. |
| `0042E9E0` / `0042E3C0` saved player views | Initial player origins at state `+3934+2*player` use `world_columns-7`; turn entry restores them into `+808`. Normalize these origins against the current visible-column count. |

`00430C20` also clips and copies to the primary around the software cursor.
Its right exclusive bound is 480 and inclusive bound is 479. All matching X
copy/clip bounds must become the expanded field bounds, while 463 remains the
last field row. This includes the no-cursor-overlap copy branch at `00430E5E`;
changing only the tile loop would still present the original seven columns.

Do not perform a numeric search-and-replace for 640/480/7. For example,
`00426FC0` contains 640 as a combat-effectiveness threshold, not a viewport
dimension. Combat rules, formations, terrain arrays, and attack outcomes remain
outside this layout change.

## HUD ownership and native composition

The supported `minimum.res` contains LLRS member `GFX/BATTLE/FRAME.S32` at
offset **380010**, length **137759**, with SHA-256
`e169a8df7d3247dda1d5a96d408684eb154ea617ac4a209c2d3739cca6cdb9b4`.
The source inspection followed its directory and decoded sprites in memory;
it wrote no extracted asset. Sprites 0–3 have sizes `335×243`, `305×243`,
`335×237`, `305×237` and native placements `(0,0)`, `(335,0)`, `(0,243)`,
`(335,243)`. This is the battle frame, distinct from the ordinary map frame.

`0042E8B0` is the battle redraw owner. It draws frame pieces to the primary
`0051D4C0`, draws the command descriptors, calls `00430F80` and `00430C20`,
then applies the palette. The initial runner has its own frame-draw sequence.

`00430F80` is not already an isolated HUD renderer. It changes
`g_RenderDevice` to `[005202E0]`, redraws frame sprites 1 and 3 starting at
**x335**, draws statistics near x498–624, and copies/presents HUD content.
Widening the field while leaving these writes in place would damage newly
visible columns. `0042DEC0` additionally animates HUD overlays directly on the
primary, using coordinate pairs at `00514DA4`; `0042E160` checks fixed native
statistic-hover rectangles. Both belong in the HUD routing inventory.

The command list begins at `00514B78` and uses 53-byte descriptors:

| Descriptor VA | Native position | Callback | Proposed anchor |
| --- | --- | --- | --- |
| `00514B78` | `(498,370)` | `0042D4E0` | Right and bottom |
| `00514BAD` | `(561,370)` | `0042D3A0` | Right and bottom |
| `00514BE2` | `(498,401)` | `0042D5B0` | Right and bottom |
| `00514C17` | `(498,432)` | `0042D670` | Right and bottom |
| `00514C4C` | `(561,401)` | `0042D560` | Right and bottom |
| `00514C81` | `(505,0)` | `0042D6F0` | Right and top |

Apply `(W-640,H-480)` to the first five widgets and `(W-640,0)` to the last.
Rendering, hover, descriptor dispatch, and native callback coordinates must
use the same transform. Do not shift the whole list vertically.

The existing `0042F2F5` call targets centering wrapper `0051BA00`. That wrapper
copies E0's native 640×480 rectangle to the primary, clears E0, copies that
primary rectangle back into E0 at the centered offset, and presents. It runs
at the initial boundary, not every battle
update. An expanded stage must replace this behavior and preserve subsequent
native composition. Likewise, inherited input wrappers at `0051BAA0` and
`0051BAF0`, reached from `0042E4ED` and `0042E501`, subtract whole-screen
centering offsets; they are not suitable for the proposed field/HUD split.

Despite its decompiler name, `Render_FillRect 004024E0` is a rectangle-copy
boundary: EAX is source, EDX is destination, and a null surface resolves to the
primary. Existing field, HUD, cursor, and overlay calls must be classified by
ownership before installing any shared copy hook.

## Proposed validation implementation and evidence

Keep the expanded field on a correctly sized memory surface. Isolate native
HUD drawing in a real 640×480 backing with a 640-byte indexed pitch, then copy
the two admitted HUD slices to their edge anchors. A native HUD backing alone
is insufficient: scoped draw/copy routing must also cover primary-only frame
setup, descriptors, HUD animation, hover, and presentation. Preserve and restore
surface/render pointers and owner-thread identity across nested calls. The
castle canvas's lifetime and state must remain independent.

Reuse the existing checked assembler, relocation metadata, original SHA checks,
old-byte verification, explicit RX code/RW state separation, and synthetic x86
ABI fixtures. The existing PE builders authenticate specific input stages;
they do **not** automatically accept a new extension of the modal-canvas
candidate. A new builder needs exact reconstruction, hook/relocation checks,
and Windows image-admission verification for its own candidate. Do not bypass
their checks or silently reuse a stable-stage identifier.

Before claiming implementation, capture and authenticate the current battle
baseline, including the primary where battle chrome is composed. Then verify
the new candidate's complete field draw and presentation, right and bottom
controls, all four frame edges, and source-pixel native-size sprite geometry.
Exercise incremental animation beyond column seven, both scroll limits,
selected-unit and shot centering, turn-restored views, hover/callback routes,
and battle exit restoring the map. Geometry fixtures alone prove none of those
runtime claims.

Show actual screenshots during this work and label resolution, candidate,
capture path, bottom-right control result, and all four frame-edge results.
Hidden CDB/software evidence remains separate from final visible composition,
manual input, and promotion. Preserve the resolved historical battle
click-to-callback proof; it does not require reopening, and it does not prove
the new HD layout. Follow [AGENTS.md](../../AGENTS.md) for runtime approval and
original-executable protections. No stable promotion or automatic commit/push
is authorized by this design choice.

## Offline preparation on 2026-09-06

The pure `src/patcher/framed_battle_viewport.py` geometry and uninstalled
`src/patcher/framed_battle_coordinates.py` helpers have six passing fixture
groups each; the coordinate suite executes the emitted x86 with register,
flags, stack and memory-canary checks. No helper is installed in a candidate.

`tools/framed_battle_initial_probe.py` and `framed_battle_initial_trace.py`
prepare and validate one disclosed slot0 unit0/unit4 baseline. Their8/9
fixture groups pass. They support only the initial centered E0 software
capture, not primary composition or expanded battle acceptance. The new
`scripts/cdb/run_framed_battle_initial_capture.ps1` is still an untested host
draft and must not be executed yet.

The separate pure `tools/framed_primary_surface.py` helper has13 passing
fixture groups for paired primary/backend/COM/palette reads, native Lock
observations, source-pinned proxy identity and readable pixel bounds. It is
not integrated with a live host and establishes no runtime or visual result.
The latest user request shifted runtime work to the
[selected-army portrait diagnostic](UNIT_SELECTION_HD.md); tactical runtime
and expanded-layout implementation remain unfinished.

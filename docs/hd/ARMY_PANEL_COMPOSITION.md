# Army panel: bounded cache and integration contract

Historical design diagnostic. The 2026-09-06 implementation frontier is
[UNIT_SELECTION_HD.md](UNIT_SELECTION_HD.md): a source-bound draw-only suffix
for the player's own army, anchored inside all four frame bands. The cache,
writable storage and frame-overlapping coordinates proposed below were never
installed. They are not current implementation instructions or proof.

Status on 2026-09-05: source-backed design for the remaining army owner. No
army cache, writable section, or hook is installed. The frozen 22-test partial
tile renderer and its separate three-hook validation builder are unchanged.
Their native fallback for this owner remains an unsupported result, not proof
of complete HD rendering.

## Why a cache is needed

The original is `C:\Clash\clash95.exe`, SHA-256
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
Its actual bytes and the local IDA ASM establish these boundaries:

- `00423760` and `00423B00` set lower-row owner `00526994=1` and call
  `00423420`, followed by full terrain redraw `00418700`.
- The start of `00423420` selects `00526FA0`, updates highlight state, and
  may call `00423370` to switch the displayed player's `INFO<n>.S32` set.
  `00423370` frees the old set and loads another; it is not a harmless draw
  callback. The corresponding native tail restores the current player's set.
- `0042355A..00423714` draws the backdrop, unit icons, counts, and markers.
  `00423715` is reached after those draws and before the player-resource
  restoration. This is the point to copy completed pixels, including enemy
  army icons while their correct resource is still represented in the surface.
- `00423B40` clears the owner and triggers terrain redraw. `0040AED0` loads map
  resources; `0040B020` tears them down. A cache must be invalidated across all
  three transitions, even if later heap allocations reuse the same addresses.

The backdrop is `MARKS.S32` sprite 35, drawn at `(29,400)`. Read-only decoding
of the existing resource through `tools/hd_layout_asset_composition.py` found
exactly **387×66 opaque pixels**: no transparent runs. Resource identity:

- `C:\Clash\DATA\minimum.res` SHA-256:
  `86b43f5e01350d9d9dfbf02a91fd3f83809050474875c2f3c4e640519f437116`.
- Native LLRS member `GFX/MARKS.S32` SHA-256:
  `026e2d549427163b5b9642a1c92f89c98b65885eec54b36a0e28fee812bc7667`.

The rectangle `(29,400)..(415,465)` is therefore UI content, rather than a
capture of terrain visible through a transparent panel. Its opacity must
remain an input prerequisite. An unknown or modified resource must fail closed.
No screenshot or extracted proprietary asset is needed in the repository.

## The three-pixel frame dependency

The army backdrop overlaps the native left frame at `x=29..31`. The existing
HD frame-restoration cave copies `x=0..31,y=360..479` to extend the left gutter.
A snapshot taken only after the army draw would leave army pixels in that
source strip and repeat them into the HD gutter. Merely restoring the whole
cached panel after the frame hook would not repair that contamination.

The producer must therefore have paired entry and completion hooks:

1. At `00423420`, invalidate the previous panel and save the untouched **3×66**
   frame strip at `(29,400)..(31,465)`. Arm capture only after validating the
   source map surface and its pixel buffer.
2. At `00423715`, validate the completed owner's identity and copy the full
   **387×66** panel to packed cache storage. Restore the saved 3×66 strip to
   its original map position before returning to native code. Publish cache
   validity only after both copies finish.
3. The subsequent terrain redraw must overwrite the remaining legacy panel
   region `x=32..415,y=400..465`. This is inside the gameplay viewport; copying
   the cache without that redraw would leave a second panel at the old anchor.
4. After terrain, minimap, command-dock composition, and frame restoration,
   restore the cached army pixels at **`x=29,y=H-72`**. This matches the command
   dock's vertical origin. It ends at `x=415,y=H-7`; the three left-frame pixels
   are deliberately composed last.
5. Present the restored UI rectangle through the native managed target and
   cursor ordering. The gameplay-only presenter starts at x=32 and cannot
   present this panel's three leftmost columns. Its primary tooltip policy
   remains separate and must be retained.

The map software surface, gameplay viewport, and this opaque UI rectangle are
different claims. Terrain beneath the restored opaque panel must not be counted
as visible terrain coverage or substituted for manual-input proof.

## Writable storage and identity

Use a **separate new read/write, non-executable PE section** in a further
explicit validation stage. Do not put mutable bytes into the frozen `.hdcode`
RX section or weaken its characteristics. A proposed layout is:

| Offset | Size | Contents |
| --- | --- | --- |
| 0 | 64 | Version, valid/armed state, lifecycle epoch and exact context fields |
| 64 | 25,542 | Packed 387×66 indexed panel pixels |
| 25,606 | 198 | Packed 3×66 pre-draw legacy-frame strip |
| 25,804 | remainder | Zero alignment padding; no executable content |

At 4096-byte section alignment this occupies seven pages. The allocator must
prove disjoint original, RX-code, RW-cache, and relocation-directory extents;
declare every absolute code reference to the new storage; update PE sizes and
HIGHLOW entries; and preserve all unrelated bytes and relocation fields. The
current eight-section builder does not yet implement this additional section.

Cache validity must bind the surface object, pixel pointer, width/height, game
data pointer, displayed army record, displayed ID `00514194`, current player
`005202EC`, army-owner byte, and lifecycle epoch. The native record relation is
`gameData + 23EE6h + 725*army_id`; construction initializes 500 such records,
so an accepted ID must be in `0..499`. Pointer equality alone does not establish
identity across map teardown/reload.

Entry must invalidate before drawing. Completion must reject unarmed capture,
a changed map buffer or identity, unknown surface type, and unsupported owner
state. An early native return must leave the cache invalid. A nested owner
draw needs an explicit per-call/depth policy; it must not publish an outer
capture using an inner call's saved strip or identity. All frame-copy loops
must validate dimensions, buffer overflow and cache/source aliasing first.
Use a valid flag published last; failure is observable and cannot become a
successful cache restore. Do not call `00423420`, player-resource loaders,
highlight routines, or input/update owners from a terrain callback.

## Candidate hook spans, still uninstalled

These are actual original bytes, not guessed instruction lengths. An installer
must recheck them against its exact source-reconstructed input candidate.

| Purpose | Native VA / file offset | Whole displaced instructions | Original HIGHLOW fields |
| --- | --- | --- | --- |
| Begin paired capture | `00423420` / `00022820` | `53 51 52 56 57 55` | None |
| Snapshot and repair legacy frame | `00423715` / `00022B15` | `A1 A0 6F 52 00 8A 40 04` | `00423716` |
| Clear-owner invalidation | `00423B47` / `00022F47` | `B9 FF FF FF FF` | None |
| Map-resource initialization | `0040AED0` / `0000A2D0` | `52 E8 1A 15 00 00` | None; E8 targets `0040C3F0` |
| Map-resource teardown | `0040B020` / `0000A420` | `51 52 E8 C9 13 00 00` | None; E8 targets `0040C3F0` |

The completion trampoline must replay both displaced instructions before
continuing at `0042371D`; remove its old HIGHLOW at `00423716` and declare the
replacement absolute operand in appended code. The initialization/teardown
trampolines must recalculate their displaced relative calls, retain original
register/flag and stack behavior, and continue at `0040AED6` / `0040B027`.
The clear-owner hook is after `UI_ClearTileHighlight`, whose native routine
only clears its highlight array, and before the owner-zero writes and redraw.

For a bounded native-code audit, the inspected immutable intervals have these
SHA-256 values (end addresses exclusive):

| Interval | SHA-256 |
| --- | --- |
| `00423420..00423760` | `175f1a3d74e1de677238c9146933cc9b5507c50fdf6b96358e5447500b983f03` |
| `00423370..004233E0` | `f6cb345db7cbeb49ac50dce500d5add5c180d9636fcd50df35df05379afe3276` |
| `00423B00..00423B80` | `758fac93c490dd1a880f5cb1e8255b2522941b91f5e7ce2bf6f4e1bbd313efc1` |
| `0040AED0..0040B020` | `aecb35db0067a7dbae5d4a3fd0ab7642bc87bfa483e251ae46bb0dd62008b797` |
| `0040B020..0040B0A0` | `9a45fa3f8a96663d98b203037770363993c459494ed079fc6fb8ff1e89f11934` |

## Work needed before execution

The next implementation must provide the separate RW allocator contract,
paired-capture state machine and bounded copy code, plus owner-aware terrain
and presentation integration. In particular, the frozen renderer currently
rejects `00526994=1`; adding a cache does not by itself admit the suppressed
last full row or partial edges. Do not replace that failure with native
fallback and label the stage complete.

Offline fixtures should execute the copy/state machine and trampolines with
canaries, exact old-byte/relocation assertions, and a rebased synthetic image.
They must show entry→completed snapshot→terrain overwrite→frame repair→docked
restore, enemy-player snapshot without resource-loader calls, clear/reload and
pointer-reuse invalidation, early return, nested entry rejection, and no writes
outside the two proven UI/frame regions. Actual approved hidden and visible
evidence comes afterward; every resulting screenshot still needs the full
bottom-right action-bar audit. This design neither supplies that evidence nor
changes the accepted historical battle/right-bottom rulings.

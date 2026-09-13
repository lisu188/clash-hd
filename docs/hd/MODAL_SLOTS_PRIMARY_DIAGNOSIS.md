# Barracks cached-primary diagnosis: retained D, 1024x768

The controlled hidden run `slots-primary-1024x768-20260913-d` reached the
barracks first-present checkpoint with three byte-identical capture sets.
Its cached-primary buffer retains the outer adventure map and has the first
two lower portrait interiors overwritten. The owned native canvas and centered
physical mirror contain all twelve portrait interiors. These are retained-file
diagnostic observations, not an accepted runtime or primary-composition pass.

The durable identities and measurements are in
[`modal-slots-primary-1024x768-20260913.json`](../../captures/current/modal-slots-primary-1024x768-20260913.json).
All binaries, game artwork, raw buffers and PNGs remain external. No captured
producer, existing recipe, evaluator or original artifact was changed by this
diagnosis.

## Evidence and limits

The candidate is stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-modalslots-validation`,
recipe `owned_barracks_dirty_slots_v1`, SHA-256
`8148cfeacf893e4b006ae5b09c71612e5ac0841f491397ca2c844c9397888515`.
The route is castle index 0, barracks, `construct_all`, debugger-controlled
native dispatch, stopped at `00433E77`. The nonpresenting memory proxy and
paused `ReadProcessMemory` captures do not prove visible-wrapper composition,
natural entry, manual input, native exit, canvas destruction or promotion.

Retain both original failures:

- `C:/ClashCaptures/hd-completion/slots-primary-1024x768-20260913-d/summary.json`
  is failed: `Offline Python validation exceeded its bounded deadline.` The
  frozen host caps the offline validator at 120000 ms; its source is preserved
  in the 41-file preflight snapshot. A complete triplet exists, but it does not
  turn this host failure into a pass.
- `C:/ClashCaptures/completehd-integration-20260913/slots-primary-independent-audit-d.json`
  is failed: `primary triplet: loaded proxy header/GetPalette implementation differs`.
  Direct comparison finds only two differing header bytes, offsets 302 and
  303: the four-byte PE `ImageBase` field at offset 300 is `10000000` on disk
  and `6ED10000` in captured memory, matching the receipt's loaded module base.
  This explains the header comparison failure; it does not authorize rewriting
  that report or accepting the uncompleted primary audit. The separate
  consumer investigation owns any loader-aware verification change.

The snapshot directory is
`C:/ClashCaptures/completehd-integration-20260913/source-snapshot-slots-primary-d`.
Its 41 files match the preflight's hashes. The original executable and all
15 recorded live save files were rehashed read-only for the checkpoint;
comparison results and time are recorded there. Cleanup is reported as game
absent, CDB absent, both handles closed and hidden desktop closed. Cleanup
does not prove the game's native modal-exit path ran.

Earlier B and C failures are retained in their original files and checkpoints.
This D record supersedes none of them.

## Measured pixels

The native canvas is 640x480, centered at offset `(192,144)` inside 1024x768;
its half-open destination is `[192,144,832,624)`. All three primary buffers
have SHA-256 `d9fad8d0bef003bff55a31dec21516296370b0ab1bdf305c94cf4cfb7296cfc9`.
All three native and all three physical buffers are also identical within
their respective groups; their distinct hashes are in the checkpoint.

For each native 32x64 portrait interior, compare primary at the centered
position against native at its original position:

| Native row | Native x positions | Primary/native mismatching pixels |
| --- | --- | --- |
| y=75 | 126, 197, 268, 339, 410, 481 | 0, 0, 0, 0, 0, 0 |
| y=206 | 126, 197, 268, 339, 410, 481 | 1888, 1888, 0, 0, 0, 0 |

Each affected interior differs in exactly its top 32x59 pixels. Its last five
rows still match. These pixels are overwritten, not zero-filled. Native and
physical agree across the complete centered 640x480 rectangle. Physical has
zero nonzero pixels outside it; primary has 474635 nonzero pixels among the
479232 outside pixels. Its nonoverlapping top, bottom, left and right bands
contain 147427, 143060, 92148 and 92000 nonzero pixels respectively.

Primary and physical differ at 24061 pixels inside the native rectangle;
the portrait and margin measurements are bounded claims, not a whole-screen
equality gate. Primary-only text and other overlays need their own sources.

Actual inspection used the retained physical
`C:/ClashCaptures/hd-completion/slots-primary-1024x768-20260913-d/surface.png`
and the cached-primary visualization
`C:/ClashCaptures/completehd-integration-20260913/slots-primary-d-visualization/primary-1.png`.
All four primary outer borders retain map content, including the minimap and
six bottom-right map action cells. Physical has four clear outer margins.
Both show the five modal button artworks. These observations establish no
button callback or manual-control behavior and are subject to the failed
primary audit above. The three identical paused buffers establish stability
of those captured bytes; they are not approved live-screen captures.

## The portrait overwrite is native sprite 25 at the old origin

Read-only LLRS directory traversal of the supported user-owned
`C:/Clash/DATA/maximum.res`, SHA-256
`44f545780f11081cd0d45421eb8b7ed985221ef776319573bbfd89ff6431ccf2`,
finds member `GFX/CASTLE.CHR/DW_12.S32` at absolute offset 262793,
length 148422, SHA-256
`00215de437943ec7ec009324fa534a865d2be89d0dcc0b79d59ef0b78f8b9776`.
The existing `tools/hd_layout_asset_composition.py` decoder reads sprite 25
as an opaque 203x120 image. No extracted asset was written.

All 24360 source pixels match primary exactly at **(220,289)** in each
capture. At the correctly centered **(412,433)** position, 24208 pixels
differ. The native canvas also differs at 24208 pixels at its own (220,289)
position: this is a later primary-only operation. The wrong primary rectangle
is `[220,289,423,409)`. It overlaps each of the first two lower portrait
interiors by exactly 32x59 pixels, explaining both 1888-pixel differences.

The authenticated native path explains the placement:

1. `00433E3F` calls `00432DC0`, which constructs all twelve slots. The existing
   slot adapter at `00432C0B` mirrors each native dirty rectangle and translates
   its primary destination. The D trace retains all twelve copy events.
2. `00433E49` subsequently calls `00432ED0`. With selected index
   `[00532188]=-1`, its no-selection branch takes `00432F09`.
3. `00432F09` loads cached primary `0051D4C0`; `00432F1E` makes it the temporary
   render device. The source sprite set is `[00532144]`, index 25.
4. `00432F5C` calls the native cursor dirty-rectangle helper with native bounds.
   `00432F94` sets y=289, `00432F99` sets x=220, and `00432F9E` draws through
   the primary device's vtable at +34h. This later primary write overwrites
   the already-correct slot interiors at their centered positions.

Changing the twelve-slot adapter again would address the wrong boundary.
The no-selection sprite's destination and associated cursor rectangle need
centering while retaining the native source pixels and call semantics.

## Why the outer map remains in primary

The frozen modal `mirror` helper clears the entire physical buffer, then copies
native 640x480 into its center. Its `full_blit` wrapper calls that helper but
restores the original EAX, which is the owned native canvas, before jumping to
the older HD-aware blit at `004E9920`.

The actual D candidate's `004E9920` recognizes a 640x480 source equal to
`[005202E0]` and calls `004024E0` with source bounds 0..639/0..479 and destination
(192,144). Thus it updates only the centered primary rectangle. The physical
buffer's cleared margins are never copied into primary by this call. The
captured outer map content is consistent with that exact copy boundary.

Publish the full authenticated physical buffer at initial barracks composition,
before slot and later primary-only overlays. A late whole-buffer recopy would
erase those native primary overlays and would require a separate justification.

## Proposed additive emitter boundary — not implemented here

Build a new validation stage and recipe above the exact reconstructed
`owned_barracks_dirty_slots_v1` candidate. Preserve existing recipes and their
hashes. Allocate a separate checked PE extension, verify original SHA and all
expected bytes, bind native call-site windows and the predecessor's canvas
state/validator/primary-blit bytes, and record every hook and relocation.

| Proposed hook | Expected predecessor bytes | Purpose and continuation |
| --- | --- | --- |
| `00433E3F`, file offset `0003323F`, 5 bytes | `E8 7C EF FF FF` | Before original `00432DC0` slot construction, publish full physical canvas via authenticated `004E9920`, then tail-delegate to `00432DC0`. |
| `00432F5C`, file offset `0003235C`, 5 bytes | `E8 4F DC 02 00` | Translate this no-selection cursor rectangle, then tail-delegate to original `00460BB0`. |
| `00432F94`, file offset `00032394`, 10 bytes | `B9 21 01 00 00 BB DC 00 00 00` | Replay y=289/x=220, conditionally center, and resume native sprite call at `00432F9E`. |

The first wrapper must require the authenticated active owner, zero latched
fault and successful mirror state. Preserve incoming registers/flags around
the extra full-physical publication and preserve native slot-call return and
clobbers through tail delegation. It must not swap the owned canvas global,
increment lifecycle counters or republish after the later overlays.

For the second wrapper, native `00460BB0` takes EAX=cursor object `00544CD8`,
EDX=left, EBX=top, ECX=right, and stack `[entry ESP+4]=bottom`; it reads the
coordinate low words and consumes the single stack argument with `RET 4`.
The caller supplies right=left+sprite width and bottom=top+sprite height.
Translate both x bounds by `(width-640)//2` and both y bounds by
`(height-480)//2`, with nonwrapping coordinate checks. Preserve all other
incoming state; tail delegation retains the original helper's return, flags
and register clobbers.

The third hook replaces two complete MOV instructions with a jump and padding.
Replay them on every path. Only in authenticated active barracks no-selection
context should their values gain the center offset. Preserve EAX=primary,
EDX=sprite pointer, ESI=vtable, other registers, flags and all seven existing
sprite-call stack arguments; resume the untouched indirect call. The renderer
continues to own its stack cleanup. Inactive, failed ownership, sticky fault
and unexpected-context paths must preserve the original behavior.

Focused future fixtures should execute emitted bytes against modeled native
calls: exact arguments/stack/flags, owner and fault rejection, source guards,
old-byte and PE allocation rejection, all presets plus 802x602, initial
full-publication order, all twelve slot interiors, and the exact sprite/dirty
rectangle destination. Preserve sentinel primary overlays drawn after the
initial publication. New runtime probes must bind the new candidate and
observe all three adapters; D remains the unchanged predecessor failure.

This bounded fix does not establish selected-unit detail refresh (including
the later `00433273` partial copy), ordinary barracks entry/input, peasants,
court/recruitment routes, native exit, 1080p behavior or release eligibility.

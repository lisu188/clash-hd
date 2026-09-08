# Bounded small-world full repaint (rendering-only validation)

The opt-in `-bounded-paint-validation` stage adds an actual x86 drawing path
for worlds smaller than the selected framed viewport. It is not selected by
the launcher, is not stable, and does not enable the existing small-world
mouse gate. It is a renderer experiment, not a claim of playable small maps.

## Dispatch and rendering

The original initial/full-entry prefixes remain byte-identical. Existing
composition-owner, resource and surface checks still run first. The new world
admission validates both world dimensions in 1..100 before writing either
camera axis, then clamps each camera to max(0, world - full_viewport_tiles).
It distinguishes fitting worlds from smaller worlds. Invalid dimensions reject
without changing camera coordinates.

Fitting worlds continue through the existing native full loop and framed
composition, with camera recovery. Small-world full redraws bypass that unsafe
loop and traverse every ceiling-coverage cell using the existing emitted `cell`
helper. The helper checks world coordinates before forming a native tile
pointer, draws valid cells, and clears outside-world full or partial cells.
Its existing minimap tail runs after each clear so the minimap is not erased.
No new tile-pointer arithmetic or unbounded native loop is added.

Each cell is rendered offscreen. Only exact status 1 (drawn) or 2 (cleared)
continues. After all cells complete, the renderer draws the four-sided frame,
then the command panel or supported AI banner, then optionally presents the
physical surface using the existing tooltip-preserving presenter. Every stage
must return its exact success value. A rejected cell/frame/panel/presentation
returns failure; it is not rerouted to the unsafe native loop. A failure after
some work may leave partial offscreen pixels but does not approve or present
them through the new path. It is not a transactional pixel rollback.

The bounded entry requires present=0 or 1 and only handles small worlds.
Each invocation keeps loop counters and saved state on the stack. It restores
non-result registers, caller flags, the exact entry render pointer, and the
exact map vtable, including an already clipped table in nested calls. The
memory vtable is used for frame/overlay drawing and the entry table is restored
on both success and failure. No shared mutable latch or cache is introduced.

## Construction and integrity

The public builder accepts only the known original executable SHA-256. It
checks the reviewed parent builder and its 14 existing implementation pins,
plus the unchanged camera module's raw source SHA. Scoped `.gitattributes`
entries preserve the new source dependency bytes on either host; no original
source hash is repinned.

The framed scalar base is independently reconstructed by the existing
source-bound PE binder. Parent code, hooks and relocation metadata must replay
to the exact parent image. The new builder then rebuilds the same single RX
extension with appended helpers and two equal-size 124-byte dispatch edits.
The parent gate prefixes, old bytes and relocation-overlap checks remain in
force. Existing helper and hook addresses are preserved; the final relocation
table and PE size fields are recalculated for the longer payload. No second
extension section is added. This differs from the camera-only patch, whose
file size and relocation table are unchanged.

Metadata records the original/scalar/final image identities, intermediate
parent hash, selected scalar edits, final PE edits, parent-payload guard edits,
appended-helper hash and entries, and complete explicit relocation inventory.
Apply selected scalar patches to the original, then the final PE `edits` to
reconstruct the final image. `payload_edits` explain changes relative to the
intermediate parent; do not apply them a second time to the final PE payload.

## Commands

In-memory verification without output files or game launch:

```powershell
python tools/build_framed_bounded_candidate.py --original C:\Clash\clash95.exe --resolution 1366x768 --preflight
```

Write a new isolated candidate and report:

```powershell
python tools/build_framed_bounded_candidate.py --original C:\Clash\clash95.exe --resolution 1366x768 --output C:\ClashTests\bounded-1366\clash95_bounded_1366x768.exe --report-json C:\ClashTests\bounded-1366\bounded-build.json
```

Both output files must be new, distinct, outside the game/repository and under
C:/ClashTests. There is no overwrite or unknown-original override. Preflight
never writes files, even when output arguments are supplied. An interrupted
write may leave an incomplete isolated artifact; subsequent runs reject it.
Neither command starts the game, a debugger, a wrapper, or a visible window.
Parent-stage probes and evidence cannot be reused for this new stage.

## Tests and limitations

```powershell
python tools/test_framed_bounded_paint.py -v
```

Byte tests use synthetic PE images and the actual existing full/initial Python
emitters. They check parent replay, old-byte rejection, complete final-image
reconstruction, preserved prior code spans, new relocation fields, and an
independent loader's relocation behavior. They do not build a retail image.

The native test lane runs source-built 32-bit workers on Windows and Linux.
It executes the new admission/dispatcher plus the ACTUAL existing `cell` and
clipping adapter instructions with test-local synthetic admission. Native game
drawing primitives and frame/panel/presentation calls are replaced by explicit
ABI recorders, not game material. Tests compare every drawn tile pointer and
cleared rectangle, minimap-after-clear order, present=0/1 behavior, failures,
register/flag preservation, memory sentinels, and restored nested vtables.
Ten resolutions include 802x602, 1366x768, ultrawide and 3840x2160. The dedicated
workflow rejects skips; unsupported local i386 execution is reported separately.

No pixel-accurate gameplay, native asset decoding, live screen transition,
manual input or stable-promotion claim is made. The current input helper still
rejects small-world map clicks, and the launcher/display planner intentionally
retain their old small-world warning. A source-bound observation recipe,
small-world input review, and real runtime qualification are subsequent work.
Unsupported screen owners still follow the unchanged native fallback and are
outside this bounded ordinary-map rendering contract.

Format reference: Microsoft PE/COFF specification:
https://learn.microsoft.com/en-us/windows/win32/debug/pe-format

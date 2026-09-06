# Mouse admission for bounded small-world rendering

`tools/build_framed_bounded_input_candidate.py` adds ordinary-map mouse
admission to the existing bounded repaint candidate. This is an opt-in native
x86 patch under `-bounded-paint-input-validation`, not a launcher default or a
stable resolution promotion.

## What changes

The previous bounded stage can repaint worlds smaller than the full viewport,
but its inherited mouse guards still reject those worlds. The new candidate
retains the 1..100 world-dimension bounds and uses
`max(0, world_dimension - full_viewport_tiles)` as the legal camera maximum
for each axis. A small axis therefore permits only camera zero. The input
routine never clamps or writes a camera: stale positions reject until the
existing repaint path corrects them.

World coordinates still have to lie inside the actual map. On a 3x2 world,
the valid terrain ends at x=223 and y=143 when the camera is zero. A click at
(224,143) or (223,144) cannot become a native tile selection, even though those
cleared pixels lie inside the HD rendering surface. Full and partial outside-
world cells are equally noninteractive.

All preceding checks are unchanged: renderer owner, surface identity, vtable,
callback, current player, native minimap selector, shifted signed mouse bounds,
frame borders, six action-bar footprints and the complete enabled minimap
footprint. The native click predicate still runs first for selection input;
the native minimap predicate retains its original position and result semantics.
Unknown owners, stale minimap anchors, disabled players and unsupported contexts
remain rejected. No keyboard, edge-scroll, minimap-navigation, modal-screen or
callback implementation is changed. Passing these guards does not establish
that a complete gameplay interaction succeeded.

## Byte contract

The public builder accepts only the known original executable SHA-256. It
verifies the bounded renderer source hash, the existing camera source hash,
and the original parent builder plus its 14 implementation source pins. It
constructs the bounded repaint parent in memory, then authenticates the exact
existing input world gate using its declared entry and denial addresses.

Only two 16-byte spans change: the X and Y full-viewport limit calculations.
Each old `world >= full_tiles` condition and subtraction is replaced with a
bounded subtraction, zero-on-negative operation and padding. The encompassing
190-byte gate, including both dimension checks, stale-camera tests, tile-bound
checks and success/denial tails, is reconstructed and verified before editing.
The new code adds no calls, global writes, absolute address operands or CPU
extension requirement. Existing saved-register/flags frames remain unchanged.

Executable size, PE headers, section layout, renderer payload outside the two
spans, hooks and the base-relocation directory remain identical to the bounded
parent. Any HIGHLOW or declared-relocation intersection rejects the edit. No
existing source pin is changed, and this patch cannot be applied twice.

The report records final and intermediate hashes, code hash, source identities,
file offsets, VA/RVA and old/new bytes. `parent_build` describes the bounded
repaint intermediate image. Apply its edits and then the new top-level edits
to reconstruct the final image. Old parent debugger probes and evidence are
not reusable; `parent_probe_reusable=false`. Input scope and unverified runtime
claims are explicit in the report.

## Commands

Verify an in-memory candidate from the locally owned original, without writing
or starting anything:

```powershell
python tools/build_framed_bounded_input_candidate.py --original C:\Clash\clash95.exe --resolution 1366x768 --preflight
```

Create new isolated outputs:

```powershell
python tools/build_framed_bounded_input_candidate.py --original C:\Clash\clash95.exe --resolution 1366x768 --output C:\ClashTests\bounded-input-1366\clash95_bounded_input_1366x768.exe --report-json C:\ClashTests\bounded-input-1366\build.json
```

Both files must be new and distinct under `C:/ClashTests`, outside the game
folder and repository. Links and existing targets are rejected. Interrupted
writes can leave an incomplete isolated artifact; it is not silently reused.
The preflight mode never writes, even when output arguments are provided.
Neither command launches the game, a wrapper, debugger or visible window.

## Tests and evidence boundary

```powershell
python tools/test_framed_bounded_input.py -v
```

Source-only tests authenticate the unchanged parent sources and compare the
reconstructed world gate to the real existing Python input emitter. Input
construction uses explicitly synthetic original-admission fixtures; it does
not bypass the public builder's original-executable checks. Synthetic PE tests
verify whole-image reconstruction, unchanged rendering/relocation bytes,
tampering rejection, duplicate application and output-file boundaries.

Native tests execute the entire emitted mouse wrappers, context checks and
pixel/world checks in source-built 32-bit workers, reusing the bounded renderer
suite's worker transport. The click predicate uses its source-declared
instructions; the minimap predicate is an ABI recorder with configurable
return, not a retail native minimap execution. Tests check call order and
argument preservation as well as GPR/flags restoration and read-only target
memory. Cases cover ten resolutions, small/narrow/tall worlds, large-map parity,
stale cameras, raw shifted coordinates, frame and HUD exclusion, enabled
minimap bounds, malformed state and rebased fixture code.

A host unable to execute i386 records a skip. The dedicated Windows/Linux CI
lane rejects skipped new tests. These tests do not construct from a real
original or execute the full game, live input, or pixel-accurate retail drawing.
The candidate still needs a stage-bound observation recipe and actual gameplay,
transition, scrolling and manual-input qualification before launcher adoption.

Reference for PE relocation integrity:
https://learn.microsoft.com/en-us/windows/win32/debug/pe-format

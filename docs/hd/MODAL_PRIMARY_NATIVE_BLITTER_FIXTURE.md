# Inherited primary blitter regression coverage

The primary adapter fixture now executes the exact inherited `4E9920`
instruction stream from its authenticated predecessor candidate. An independent
native partial-copy leaf models its inclusive bounds and `RET 16` calling
convention. Synthetic memory checks cover pixels, all four margins, register
and flag preservation, stack canaries, and cursor remove/copy/redraw order.
This strengthens source-level ABI coverage; it does not execute Clash95 or
provide runtime, input, or release acceptance.

The main fixture covers 1024x768, 1920x1080 and 802x602. A separate registered
fixture covers 800x600, 1280x720 and 1280x960, including the shorter immediate
instructions in the historical 800x600 wrapper. Splitting the six exact
reconstructions keeps each suite within the existing 600-second aggregate
deadline. No timeout or assertion was relaxed.

The fixture extracts the owned native-canvas instructions from the exact
reconstructed slots predecessor rather than independently rebuilding the same
owner again. It authenticates the code hash, entry addresses, geometry, state
layout and relocation operands. Negative cases reject changed code, invalid
entries, mismatched geometry and out-of-bounds relocations. Production builder,
allocator, renderer and candidate bytes remain unchanged.

Run the two suites with:

```powershell
python -B tools/test_framed_modal_primary.py
python -B tools/test_framed_modal_primary_extra_profiles.py
```

These fixtures require the user's known original and the Windows x86 fixture
compiler. Environments without them report explicit skips. The fixtures never
launch the game, a debugger, a wrapper or a visible window.

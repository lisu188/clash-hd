# Owned native modal widget bounds

The additive `framed_modal_widget_bounds.py` emitter prepares two uninstalled
six-byte CMP replacements at `00419D63` (single descriptor) and `00419D8C`
(descriptor list). The input is reconstructed from the exact frozen
`owned_modal_primary_text_v1` builder. The existing stage and its candidates
remain unchanged.

The broad HD width operands admit the native disabled-control coordinate
`x=1000` at 1024 and 1920 pixels. That coordinate must stay outside the private
640x480 modal canvas. Restoring 640 globally is incorrect because ordinary HD
map controls and road overlays still need their expanded coordinates.

Each new CALL/NOP adapter preserves all general registers and ESP, then returns
the flags of a signed CMP. If the render target is the inherited owned native
canvas, its phase and fault must be valid and the inherited `is_active` helper
must accept its thread, surfaces and ownership. The effective bound is then
640. An inactive, faulted or rejected owned target returns equality flags, so
the existing signed comparison branch suppresses the draw. Other targets retain
the original HD-width comparison. Negative coordinates keep their original
signed semantics; descriptor values, availability flags, callbacks, list
iteration and target selection are never rewritten.

The helper retains its existing fault4 latch when it finds invalid active
ownership. No new allocation, surface write, thread API, input path or callback
is introduced. Only the inherited ownership validator may be called.

`tools/test_modal_widget_bounds.py` includes native i386 CPU fixtures on Windows
and x86 Linux. Linux uses a small generated ELF32 image; Windows uses a bounded
x86 .NET host with RX code and RW data. The owner validator is a clearly labeled
stub in this fixture, not native game execution. Cases cover both dispatchers,
six resolutions, coordinate boundaries, all supported ModRM base registers,
all GPRs, ESP, arithmetic/direction flags, owner calls, fault behavior and the
old x=1000 regression. A dedicated workflow fails on skipped selected tests.

This checkpoint does not install the guards or establish corrected game pixels.
A separate PE extension, exact loaded-byte probe, new candidate and corresponding
runtime consumer remain necessary. The protected stable stage, Classic/800x600,
previous failed captures, text placement and all manual-input requirements are
unchanged.

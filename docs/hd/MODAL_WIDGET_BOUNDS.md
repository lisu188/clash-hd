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

The emitter does not install the guards or establish corrected game pixels.
The separate [widget candidate builder](MODAL_WIDGET_CANDIDATE.md) installs them
above the frozen text predecessor with its own PE section and loaded-byte probe.
A matching runtime consumer and fresh visual evidence remain necessary. The
protected stable stage, Classic/800x600, previous failed captures and all
manual-input requirements are unchanged.

## Installed guards with the real inherited owner

The separate `tools/test_modal_widget_owner_integration.py` fixture builds the
exact widget candidate and executes its installed guard/CALL-NOP instructions
with the actual inherited `is_active`, `try_enter` and `try_leave` code in
synthetic x86 memory. Allocator, thread and game-body dependencies remain labeled
recorders. It checks original JL bytes separately; its RET continuation captures
comparison flags rather than executing a game screen.

The final source passed five tests without skips at both 1024x768 and 1920x1080
on 2026-09-24. Each profile covers 316 hook observations across 156 cases,
including both hook orders, invalid ownership/fault latching, allocation failure,
GPR/ESP/flags and canaries, and restoration from both primary and physical
original targets. The original executable remained unchanged and synthetic
children/directories were cleaned up. This closes the owner-call fixture gap;
corrected barracks pixels and actual game lifecycle remain unproved.

Run the module directly on Windows with the user-owned original and x86 .NET
compiler. `CLASH_WIDGET_RESOLUTION` selects a canonical profile; its default is
1024x768. Missing prerequisites are explicit skips in the aggregate registry.
See [widget candidate preparation](MODAL_WIDGET_CANDIDATE.md) for candidate
binding and the remaining runtime consumer requirements.

The exact final reports and source snapshots are retained under
`C:/ClashCaptures/completehd-integration-20260924/widget-context-owner-checks-v1/`.
Its preservation manifest SHA-256 is
`da83dd3d300b7c357b7288514a69cbc586b1399a96fc88874ad72a15e7e371ea`.
The `clash-widget-owner-final-1024-xnqazk0c` and
`clash-widget-owner-final-1080-pc3f1mvq` subdirectories contain the actual CPU
fixture reports; the separate context draft receipts in that archive do not
provide evidence for the subsequently merged canonical context reader.

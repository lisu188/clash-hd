# QEMU guest manual-DI lane: two structural walls (2026-07-27)

Tablet-free (-NoUsb) guest, paced driver. Both blockers that stop the 5
manual-DI targets are now proven with numbers, not speculation.

## Lever 1 - -NoUsb does NOT restore accumulation or extend range (FAILED)
PS/2 relative input is deterministic per-delta, does NOT accumulate: repeated
same-direction moves oscillate in place (pos = 4*delta+14, delta 30->134,
31->138). Single delta saturates at cursor-center x~=522 / y~=521 for any
delta >=130 (tested to 650). Click hotspot tops near x~=508/y~=508. So x=780
(map-right-edge, minimap 760,560) and y=560 (map-bottom 400,580) are
STRUCTURALLY UNREACHABLE by PS/2 relative input, tablet or no tablet.

## Lever 2 - the load dialog is deaf to synthetic input (FAILED)
The menu LOAD click lands cleanly (game's own DirectInput cursor, drivable),
transitioning menu->load dialog. But the load/slot dialog HIDES the cursor
(moves produce 0 pixel change) AND ignores everything: QMP send-key (down/up/
home/end/Enter/Esc) all produce 0 frame change, and blind mouse clicks on the
slots / load button / back arrow hit-test nothing. So no save loads -> no map
-> no castle sub-screen -> no manual-DI target reachable in the guest.
Likely mechanism: the dialog hit-tests a pointer that neither PS/2 relative
(unbound) nor the usb-tablet (never binds in Win98) drives.

## What the guest DID prove (committed earlier)
HD 800x600 real Win9x DirectDraw render (a0a67e31); input reaches the engine +
a precise verified LOAD click (794119cd). Those stand.

## Net
The guest completes the HD-render proof but CANNOT complete the manual-DI
targets: the ~522px cursor clamp and the input-deaf load dialog are hard
QEMU/cirrus/Win98-DirectInput limits, not driver bugs. The manual-DI 5 targets
+ soak need either the host visible lane (workstation must be UNLOCKED - the
proven 21:09 host run reached the map) or a fundamentally different guest input
device that drives the dialog's hit-test.

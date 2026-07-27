# QEMU Win98 guest: HD render + input-reaches-engine (2026-07-27)

Headless guest `C:\clash-hd-vm` (QMP 127.0.0.1:4445, `-display none`, cirrus VGA),
staged stable HD candidate launched via the Win98 Run MRU.

## Proven
1. **HD 800x600 real Win9x DirectDraw render.** `hd-menu-800x600.png` — the game's
   main menu (CLASH banner, load/campain/exit/options/multi player/credits shield)
   at 800x600, true color, from a QMP screendump (framebuffer header 800x600,
   190 colors, 61.9% nonblack). The host dgVoodoo wrapper cannot even complete
   this mode switch; the memory-only surfdump proxy never does a real switch.
   This is the first real-display-mode HD proof.
2. **Hypervisor input reaches the engine.** Null test: 3 consecutive screendumps
   with NO input are byte-identical (menu is static, no ambient animation), so a
   frame change is attributable to input. A PS/2 relative `moverel` moves the
   game cursor sprite: after homing to the top-left corner, a +300,+200 relative
   move shifted the 45x51 cursor sprite (diff bbox (16,32)..(60,82)).
   `cursor-homed.png` -> `cursor-after-move.png`.

## Notes for the next step (precise aiming)
- The usb-tablet absolute path (`clickabs`) does NOTHING — Win98 does not bind the
  USB tablet as its pointer; the guest reads the PS/2 relative mouse only. This is
  the same DirectInput-accumulator model as the host (commit 589f5700).
- Relative gain is low and acceleration-curved, so a single large jump saturates.
  Landing a precise click on a target (e.g. the load button ~300,208) needs the
  frame-feedback aim loop (tools/vm_guest_click.py), homing then walking with
  per-step cursor-position feedback and gain re-estimation in-guest.
- This directory is a fundamentals proof, NOT yet a manual-DI target pass (no
  button click landed / no dialog opened yet).

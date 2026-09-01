# VM HD manual-DirectInput: LOAD button click LANDED (Stage A)

Date: 2026-07-27. Guest: `clash-hd-vm`, headless QEMU Win98, QMP tcp 127.0.0.1:4445,
cirrus VGA, HD 800x600 real DirectDraw. PS/2 relative mouse only (usb-tablet
confirmed unbound / absolute input does nothing).

## Result (decisive)

A frame-feedback-aimed **relative-mouse click on the main-menu LOAD button
landed and was verified by a real UI state change** to the load / slot-selection
dialog (10 save slots + a "load" button + a back arrow). This is not a click at a
coordinate alone: the whole screen transitioned (51,260 changed pixels outside the
cursor footprint).

- `01-before-menu.png`  - static 800x600 HD main menu (cursor parked; before click).
- `02-after-load-dialog.png` - the load/slot-selection dialog shown AFTER the click.

The load-button placement converged deterministically to blob-center ~(306,212),
inside the load ellipse (x 255-373, y 197-222), then clicked in place.

## How aiming was solved (the engine input model)

The engine cursor is driven by the DirectInput accumulator, and under this QEMU
guest the reachable behaviour is:

1. Absolute (usb-tablet) input does NOTHING - sprite never moves. (Confirmed.)
2. PS/2 relative input does NOT accumulate. Because an unbound usb-tablet resets
   the per-axis baseline, the sprite position on each axis is a DETERMINISTIC,
   REPEATABLE function of the most-recent nonzero delta on that axis:
   `sprite_pos ~= 4.0 * delta + 14` (linear, ~4px per unit), saturating near 521.
   x and y are independent: rel(dx,0) sets x, rel(0,dy) sets y; a zero-delta axis
   stays put. See `calibration-curve.json`.
3. QEMU drops a rel event identical to its immediate predecessor (dedup); vary the
   delta each event.
4. Addressable sprite range is ~x in [78,521], y in [77,521]; the far right/bottom
   of the 800x600 screen is UNREACHABLE by this method.

The cursor is located reference-free by diffing the live frame against a
per-pixel MEDIAN cursorless background (`menu-background-median.png`); the changed
blob center is the cursor.

Driver code: `det.py` (deterministic placement), `aimdrive.py` (closed-loop
variant), `qmpclient.py` (persistent QMP + logging). QMP input events are logged
under `qmp-input-logs/`.

## What is NOT proven here

- The load *route* (select slot 0 + confirm + reach the map) was not completed:
  the load dialog HIDES the game cursor, so there is no frame feedback on that
  screen and blind clicks did not register a verifiable transition.
- No formal manual-DirectInput proof manifest / promotion was produced. The other
  four targets (map input, right-bottom, castle barracks/overview) were not driven
  because (a) their per-target save fixtures require re-staging via
  `scripts/vm/hd_vm_stage.ps1`, which refuses to run while QEMU is up, and (b) the
  right/bottom follow-up points sit outside the addressable cursor range.

No host `C:\Clash\clash95.exe` or `C:\Clash\save` file was modified. No in-guest
save was written.

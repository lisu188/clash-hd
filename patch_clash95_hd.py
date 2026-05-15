#!/usr/bin/env python3
"""Create a non-destructive Clash95 800x600 HD viewport test executable.

The default patch stage is intentionally conservative:

- grow the main 640x480 render/window surfaces to 800x600
- grow the map viewport rectangle to 800x600
- grow the main adventure-map redraw loops from 9x7 tiles to 12x9 tiles

If menu graphics break, try ``--stage gameplay``. It avoids resizing the
shared/default and menu/game surfaces while still growing the display object,
window, gameplay surface, map viewport, and visible map loops. If the menu
draws in the wrong place or the mouse is trapped in the old top-left area, try
``--stage gameplay-menu640``. That keeps the later menu/cursor switch at the
original 640x480 size while preserving the larger gameplay display patches.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch``
is the current HD map proof path when the wrapper is configured for
windowed/application display mode: it keeps menus on their native-safe 640x480
surface, dynamically fixes wrapper mouse coordinates, swaps gameplay to an
800x600 map surface after menu dispatch, widens the proven full-redraw present
rectangles, moves the minimap to the HD upper-right corner, and conditionally
keeps the later viewport switch at 640x480 for menu metadata but 800x600 for
the CDB-proven map metadata object.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose``
adds a validation-only right-bottom composition proof: the stock post-owner
action route still draws at native coordinates, then two narrow copy hooks move
the status/action regions into the HD bottom strip. Keep it out of the stable
HD map stage until hidden-desktop evidence proves it broadly.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter``
adds a narrow castle/barracks presentation proof that recenters the native
640x480 castle UI layer inside the 800x600 surface after the action-panel draw.
Treat it as visual proof until matching castle hitbox/input offsets are added.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox``
adds a local castle/barracks mouse transform for that centered presentation:
the owner-poll and descriptor hit-test calls temporarily see mouse coordinates
shifted back by the 80x60 visual offset while the rendered frame stays centered.
It also wraps the barracks grid hit-test call so the hardcoded native grid at
`00435580` receives the same transformed coordinate.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all``
is the castle-interior validation target. It keeps the `castlecenter-hitbox`
input transforms, but replaces the earlier pre-present visual copy with a
present-callback wrapper so the stock castle/barracks render hook runs first
and the freshly rendered native UI is centered exactly once. It also wraps the
full castle overview redraw calls around `00422180` / `00422020`. That wrapper
lets stock rendering draw into its native 640x480 target first, then copies the
native layer into an 800x600 target at `(80,60)` before the catalog/present
evidence is dumped.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter``
is a probe-first battle UI validation target. It intentionally selects the same
bytes as `castlecenter-all` until battle draw/input routes are proven by CDB
evidence; do not add battle patch groups or promote this stage without a
passing battle gate.
``--stage gameplay-menu640-centered-map12-novswitch-relinput`` is the older
menu-safe map path: it expands the adventure map drawing/scroll helpers to
12x9 tiles, but deliberately leaves the later global cursor/view switch at
640x480 and therefore collapses gameplay mouse bounds after the map surface
swap.
``--stage gameplay-menu640-centered-map12-nonexclusive`` keeps the same
map/menu patches but changes the DirectInput mouse cooperative level from
exclusive to nonexclusive as a diagnostic.
``--stage gameplay-menu640-centered-map12-absnonexclusive`` keeps the same
map/menu patches, changes mouse capture to nonexclusive, and assigns the
DirectInput X/Y samples as absolute coordinates instead of accumulating them.
``--stage gameplay-menu640-centered-map12-absinput`` keeps the same map/menu
patches but assigns the DirectInput X/Y samples as absolute game coordinates.
Use it when CDB shows large absolute-style mouse samples reaching
``sub_460A50``.
``--stage gameplay-menu640-centered-map12-deltaclamp`` keeps the same map/menu
patches but clamps each DirectInput relative delta to +/-32 before the engine's
mouse-speed multiplier is applied. Use it as a diagnostic when CDB shows huge
relative samples pinning the cursor to a menu clamp.
``--stage gameplay-menu640-centered-map12-absquarter`` keeps the same map/menu
patches but assigns DirectInput X/Y samples as quarter-scale absolute
coordinates. Use it when CDB shows positive absolute-like samples around
roughly 900..1400 for an 800x600 client.
``--stage gameplay-menu640-centered-map12-screenorigin`` is a temporary
diagnostic built from CDB evidence for the current DDraw wrapper/window
placement. It treats DirectInput samples as quartered screen coordinates and
subtracts the traced client origin `(880,407)`. Do not ship this stage; use it
only to prove the coordinate transform before replacing the hard-coded origin.
``--stage gameplay-menu640-centered-map12-dynorigin`` is the follow-up
diagnostic: it calls the existing USER32 `ClientToScreen` import on the live
game HWND and subtracts that dynamic client origin from quartered screen
coordinates.
``--stage gameplay-menu640-centered-map12-dynorigin-sharedscratch`` is a
runtime crash diagnostic that also grows the default/scratch render surface at
`unk_51D4C0` to 800x600 while leaving the menu/game surface at 640x480.
``--stage gameplay-menu640-centered-map12-dynorigin-menusurface`` is a
follow-up crash diagnostic: it also grows the 0x447DC0 menu/game surface after
CDB stream-constructor evidence showed the remaining map-copy AV writes through
a 640x480 stream backed by that surface. Expect menu risk; use it for evidence.
``--stage gameplay-menu640-centered-map12-dynorigin-menusurface-scrollclamp``
adds a permanent PlayGame saved-scroll restoration clamp. It is the first
standalone candidate for the 12x9 HD map path: it clamps restored scroll to
`map_width - 12` / `map_height - 9` before the first redraw, then keeps the
menusurface stream at 800x600.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp``
keeps the main-menu allocation at 640x480, then uses the saved-scroll hook to
swap the map target to an 800x600 surface after menu dispatch and before the
first gameplay redraw. Use it to avoid the stripey menu regression from the
global `menu-surface` patch. It also uses a stricter center-blit helper that
only centers `dword_5202E0` while that surface is still 640 pixels wide and
copies the full 800x600 rectangle once gameplay swaps in the larger map target.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds``
adds a narrow diagnostic patch for the `sub_418700` full-redraw present
rectangles after CDB proved that the tiles draw to the 800x600 surface but the
copy rectangles still stop at the native right/bottom edges.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapclip``
adds a targeted minimap dirty-rectangle right-edge clamp after CDB proved that
the widened full-redraw rectangle made `sub_40D560` copy past the 214-wide
minimap backing surface and duplicate the minimap across the HD top-right area.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright``
also moves the minimap anchor from the native 608-pixel right edge to the
800-pixel right edge by changing the `sub_40D330` right-anchor immediate.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch``
is the same minimap-right diagnostic with the later `sub_460D80`
viewport-switch immediates enabled. It is not promoted by default; use it to
test whether gameplay mouse bounds must be widened after the menu-safe map
surface swap.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch``
replaces that later `sub_460D80` hardcoded 640x480 reset with a conditional
helper: keep native bounds for the menu metadata object, but switch to 800x600
when CDB-proven map metadata `005196A0` is selected.
``--stage gameplay-menu640-centered-map12-hybridmouse-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch``
is the same current HD map proof stack, but swaps the dynamic-origin mouse
transform for the older hybrid relative/absolute DirectInput diagnostic. Use it
for windowed diagnostic runs where Win32 cursor placement is exact but CDB shows
the engine mouse still pinned near `(1,1)`.
``--stage gameplay-menu640-centered-map12-relinput`` also changes that later
viewport switch to 800x600 and is now a diagnostic build only.
``--stage gameplay-menu640-centered-hitboxes`` is the same menu/input fix
without the later map helper and viewport-switch patches.
``--stage gameplay-menu640-centered-visual-absinput`` centers only the menu
background blit, without moving menu button descriptors, for visual isolation.
``--stage display-absinput`` is a tighter diagnostic that only grows the
window/display and applies the mouse input experiment.
The `isolate-*` stages add one HD patch group at a time on top of
`display-absinput`.

The scroll/click/center helper constants are available with
``--stage helpers`` after the first build boots and draws correctly.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXPECTED_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
DEFAULT_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch"
)


@dataclass(frozen=True)
class Patch:
    group: str
    offset: int
    old_hex: str
    new_hex: str
    note: str

    @property
    def old(self) -> bytes:
        return bytes.fromhex(self.old_hex)

    @property
    def new(self) -> bytes:
        return bytes.fromhex(self.new_hex)


PATCHES: tuple[Patch, ...] = (
    # Group A: grow core render/window buffers.
    Patch("display", 0x003A64, "e0010000", "58020000", "0x404660 render object height 480 -> 600"),
    Patch("display", 0x003A69, "80020000", "20030000", "0x404660 render object width 640 -> 800"),
    Patch("shared-surface", 0x000E4D, "e0010000", "58020000", "0x401A40 default surface height 480 -> 600"),
    Patch("shared-surface", 0x000E62, "80020000", "20030000", "0x401A40 default surface width 640 -> 800"),
    Patch("display", 0x060EAD, "e0010000", "58020000", "0x461A20 window height 480 -> 600"),
    Patch("display", 0x060EB2, "80020000", "20030000", "0x461A20 window width 640 -> 800"),
    Patch("gameplay-surface", 0x00A3BF, "e0010000", "58020000", "0x40AED0 area gameplay surface height 480 -> 600"),
    Patch("gameplay-surface", 0x00A3C4, "80020000", "20030000", "0x40AED0 area gameplay surface width 640 -> 800"),
    Patch("menu-surface", 0x0471D7, "e0010000", "58020000", "0x447DC0 area menu/game surface height 480 -> 600"),
    Patch("menu-surface", 0x0471DC, "80020000", "20030000", "0x447DC0 area menu/game surface width 640 -> 800"),
    Patch("center-blit", 0x001233, "6a00", "6a3c", "0x401E30 full-screen 640 blit dest Y 0 -> 60"),
    Patch("center-blit", 0x001235, "6a00", "6a50", "0x401E30 full-screen 640 blit dest X 0 -> 80"),
    Patch(
        "menu-only-center-blit",
        0x001230,
        "5351526a006a0068df010000bac0d45100687f02000031c931dbe8910600005a595bc38d80000000008d920000000090",
        "53515231c93b05e002520075066a3c6a50eb02515168df010000bac0d45100687f02000031dbe8850600005a595bc390",
        "0x401E30 conditional center: dword_5202E0 menu surface -> dest 80,60 else 0,0",
    ),
    Patch(
        "menu-only-center-blit-640only",
        0x001230,
        "5351526a006a0068df010000bac0d45100687f02000031c931dbe8910600005a595bc38d80000000008d920000000090",
        "e9eb7a0e00" + "00" * 43,
        "0x401E30 jump to center only when eax==dword_5202E0 and surface width is 640",
    ),
    Patch(
        "menu-only-center-blit-640only",
        0x0E8D20,
        "00" * 64,
        (
            "6031c93b05e0025200750d668138800275066a3c6a50eb025151"
            "68df010000bac0d45100687f02000031dbe8908bf1ff61c3"
            + "00" * 14
        ),
        "0x4E9920 code cave: center 640x480 dword_5202E0 menu blits, leave upgraded 800x600 map blits at 0,0",
    ),
    Patch(
        "surface-blit-hd-aware",
        0x001230,
        "5351526a006a0068df010000bac0d45100687f02000031c931dbe8910600005a595bc38d80000000008d920000000090",
        "e9eb7a0e00" + "00" * 43,
        "0x401E30 jump to HD-aware full-surface blit helper",
    ),
    Patch(
        "surface-blit-hd-aware",
        0x0E8D20,
        "00" * 96,
        (
            "6089c6bddf010000bf7f02000066813e2003751266817e025802750a"
            "bd57020000bf1f03000031c931db3b35e0025200750d66813e8002"
            "75066a3c6a50eb02515155bac0d451005789f0e8718bf1ff61c3"
            + "00" * 15
        ),
        "0x4E9920 code cave: copy 800x600 sources as 799x599, keep 640x480 menu centering at 80,60",
    ),
    Patch(
        "castle-ui-center-present",
        0x0351A5,
        "b8d84c5400",
        "e9c5d30d00",
        "0x435DA5 castle action present hook -> center native 640x480 UI layer before original Render_Present",
    ),
    Patch(
        "castle-ui-center-present",
        0x11136F,
        "00" * 86,
        (
            "a1e00252006a006a0068df010000bac0d45100687f02000031c931db"
            "e850f3eeffff35e00252008b0424e8c2eceeff5a6a3c6a5068df"
            "010000687f02000031c931dbb8c0d45100e825f3eeffb8d84c5400"
            "e9e52bf2ff"
        ),
        "0x51316F DGROUP cave: copy dword_5202E0 640x480 to scratch, clear target, copy back at 80,60, then resume Render_Present",
    ),
    Patch(
        "castle-ui-center-present-wrapper",
        0x0351AA,
        "bb905b4300",
        "bb6f315100",
        "0x435DAA castle action present callback 0x435B90 -> wrapper 0x51316F",
    ),
    Patch(
        "castle-ui-center-present-wrapper",
        0x11136F,
        "00" * 86,
        (
            "60e81b2af2ff6160"
            "a1e00252006a006a0068df010000bac0d45100687f02000031c931db"
            "e848f3eeffff35e00252008b0424e8baeceeff5a6a3c6a5068df"
            "010000687f02000031c931dbb8c0d45100e81df3eeff61c3"
        ),
        "0x51316F DGROUP callback wrapper: call stock 0x435B90, restore callback-entry regs, then center freshly rendered 640x480 castle UI at 80,60",
    ),
    Patch(
        "castle-ui-center-present-wrapper",
        0x0351DE,
        "e8adfdffff",
        "e88cd30d00",
        "0x435DDE barracks loop redraw call 0x435B90 -> wrapper 0x51316F so per-frame castle UI is centered after stock redraw",
    ),
    Patch(
        "castle-ui-centered-input",
        0x034F90,
        "52b8c0d45100",
        "e98bd60d0090",
        "0x435B90 owner-poll entry hook -> temporarily subtract centered castle UI mouse offset",
    ),
    Patch(
        "castle-ui-centered-input",
        0x034FB3,
        "5ac38d8000",
        "e9a8d60d00",
        "0x435BB3 owner-poll exit hook -> restore mouse offset before returning",
    ),
    Patch(
        "castle-ui-centered-input",
        0x0351F5,
        "e8c63ffeff",
        "e9cbd30d00",
        "0x435DF5 descriptor hit-test call hook -> temporarily subtract centered castle UI mouse offset",
    ),
    Patch(
        "castle-ui-centered-input",
        0x034E17,
        "e864fbffff",
        "e86ed80d00",
        "0x435A17 barracks grid hit-test call hook -> temporarily subtract centered castle UI mouse offset",
    ),
    Patch(
        "castle-ui-centered-input",
        0x1113C5,
        "00" * 84,
        (
            "51528a0d2c515400ba50000000d3e22915fc4c5400ba3c000000d3e2"
            "2915004d54005a59e8d26bf0ff5051528a0d2c515400ba50000000d3e2"
            "0115fc4c5400ba3c000000d3e20115004d54005a5958e9e12bf2ff"
        ),
        "0x5131C5 DGROUP cave: wrap 0x419DC0 descriptor hit tests with logical mouse -80,-60 and restore",
    ),
    Patch(
        "castle-ui-centered-input",
        0x111420,
        "00" * 47,
        (
            "51528a0d2c515400ba50000000d3e22915fc4c5400ba3c000000d3e2"
            "2915004d54005a5952b8c0d45100e94729f2ff"
        ),
        "0x513220 DGROUP cave: enter 0x435B90 owner poll with logical mouse -80,-60, then run original prologue",
    ),
    Patch(
        "castle-ui-centered-input",
        0x111460,
        "00" * 40,
        (
            "5051528a0d2c515400ba50000000d3e20115fc4c5400ba3c000000d3e2"
            "0115004d54005a59585ac3"
        ),
        "0x513260 DGROUP cave: restore centered castle UI mouse offset, pop original edx, return",
    ),
    Patch(
        "castle-ui-centered-input",
        0x11148A,
        "00" * 80,
        (
            "51528a0d2c515400ba50000000d3e22915fc4c5400ba3c000000d3e2"
            "2915004d54005a59e8cd22f2ff5051528a0d2c515400ba50000000d3e2"
            "0115fc4c5400ba3c000000d3e20115004d54005a5958c3"
        ),
        "0x51328A DGROUP cave: wrap 0x435580 barracks grid hit test with logical mouse -80,-60 and restore",
    ),
    Patch(
        "castle-overview-center-present-wrapper",
        0x02172E,
        "e8edfcffff",
        "e89d930f00",
        "0x42232E full castle overview initial 0x422020 redraw call -> 0x51B6D0 HD target/centering wrapper",
    ),
    Patch(
        "castle-overview-center-present-wrapper",
        0x021A74,
        "e8a7f9ffff",
        "e857900f00",
        "0x422674 full castle overview action-loop 0x422020 redraw call -> 0x51B6D0 HD target/centering wrapper",
    ),
    Patch(
        "castle-overview-center-present-wrapper",
        0x1198D0,
        "00" * 208,
        (
            "60e84a69f0ff6160a1e00252006a006a0068df010000bac0d45100"
            "687f02000031c931dbe8e76deeffa1e002520085c074076681382003"
            "7428b8bc000000e8ed64f4ff85c0741a53bb58020000ba20030000"
            "e84986eeff5b85c07405a3e0025200ff35e00252008b0424e82167"
            "eeff5a6a3c6a5068df010000687f02000031c931dbb8c0d45100e884"
            "6deeff61c3"
            + ("00" * 66)
        ),
        "0x51B6D0 DGROUP cave: call stock 0x422020 on its native 640x480 target first, copy that result to scratch, then ensure an 800x600 dword_5202E0 and center-copy the native overview at 80,60",
    ),
    Patch(
        "castle-overview-centered-input",
        0x021920,
        "8b1d004d54008a0d2c5154008b15fc4c5400a330125100d3fb8bb8b8000000d3faff5710",
        "e97b920f00" + ("90" * 31),
        "0x422520 full castle overview descriptor hit-test block -> 0x51B7A0 centered input wrapper",
    ),
    Patch(
        "castle-overview-centered-input",
        0x1199A0,
        "00" * 64,
        (
            "8b1d004d54008a0d2c5154008b15fc4c5400a330125100d3fb"
            "8bb8b8000000d3fa83ea5083eb3cff5710e9756df0ff"
            + ("00" * 17)
        ),
        "0x51B7A0 DGROUP cave: wrap full castle overview descriptor hit test with logical mouse -80,-60",
    ),
    Patch(
        "right-bottom-compose-proof",
        0x0346B3,
        "bac0d45100",
        "e928e00d00",
        "0x4352B3 post-owner status setup -> 0x5132E0 HD bottom-strip status copy hook",
    ),
    Patch(
        "right-bottom-compose-proof",
        0x1114E0,
        "00" * 64,
        (
            "60a1e00252006810020000684a020000686501000089c26851020000"
            "bb91010000b920010000e8d5f1eeff61bac0d45100e9a21ff2ff"
            + ("00" * 10)
        ),
        "0x5132E0 DGROUP cave: copy native status rect 401,288,593,357 to HD bottom-strip destination 586,528 then resume 0x4352B8",
    ),
    Patch(
        "right-bottom-compose-proof",
        0x0351A5,
        "b8d84c5400",
        "e9d6e00d00",
        "0x435DA5 post-owner action-box setup -> 0x513E80 HD bottom-strip action copy hook",
    ),
    Patch(
        "right-bottom-compose-proof",
        0x112080,
        "00" * 64,
        (
            "60b8c0d45100680c020000681d01000068a90100008b15e0025200"
            "68c2010000bb1d010000b95e010000e831e6eeff61b8d84c5400"
            "e9f01ef2ff"
            + ("00" * 6)
        ),
        "0x513E80 DGROUP cave: copy native action-box rect 285,350,450,425 to HD bottom-strip destination 285,524 then resume 0x435DAA",
    ),
    # Group A2: shift start-menu button descriptors to match centered 640x480 menu art.
    # These are 53-byte UI descriptors copied to stack by PlayGame_Dispatch.
    # The same x/y fields drive both sub_419D80 drawing and sub_419DC0 hit testing.
    # main menu: VA 0x5181C0
    Patch("menu-center-hitboxes", 0x1163C0, "9f000000", "ef000000", "0x5181C0 main menu entry 0 X 159 -> 239"),
    Patch("menu-center-hitboxes", 0x1163C4, "88000000", "c4000000", "0x5181C4 main menu entry 0 Y 136 -> 196"),
    Patch("menu-center-hitboxes", 0x1163F5, "98000000", "e8000000", "0x5181F5 main menu entry 1 X 152 -> 232"),
    Patch("menu-center-hitboxes", 0x1163F9, "a8000000", "e4000000", "0x5181F9 main menu entry 1 Y 168 -> 228"),
    Patch("menu-center-hitboxes", 0x11642A, "b9000000", "09010000", "0x51822A main menu entry 2 X 185 -> 265"),
    Patch("menu-center-hitboxes", 0x11642E, "cc000000", "08010000", "0x51822E main menu entry 2 Y 204 -> 264"),
    Patch("menu-center-hitboxes", 0x11645F, "65010000", "b5010000", "0x51825F main menu entry 3 X 357 -> 437"),
    Patch("menu-center-hitboxes", 0x116463, "88000000", "c4000000", "0x518263 main menu entry 3 Y 136 -> 196"),
    Patch("menu-center-hitboxes", 0x116494, "58010000", "a8010000", "0x518294 main menu entry 4 X 344 -> 424"),
    Patch("menu-center-hitboxes", 0x116498, "a8000000", "e4000000", "0x518298 main menu entry 4 Y 168 -> 228"),
    Patch("menu-center-hitboxes", 0x1164C9, "84010000", "d4010000", "0x5182C9 main menu entry 5 X 388 -> 468"),
    Patch("menu-center-hitboxes", 0x1164CD, "cc000000", "08010000", "0x5182CD main menu entry 5 Y 204 -> 264"),
    # new/load submenu: VA 0x518338
    Patch("menu-center-hitboxes", 0x116538, "98000000", "e8000000", "0x518338 new/load submenu entry 0 X 152 -> 232"),
    Patch("menu-center-hitboxes", 0x11653C, "17010000", "53010000", "0x51833C new/load submenu entry 0 Y 279 -> 339"),
    Patch("menu-center-hitboxes", 0x11656D, "80010000", "d0010000", "0x51836D new/load submenu entry 1 X 384 -> 464"),
    Patch("menu-center-hitboxes", 0x116571, "17010000", "53010000", "0x518371 new/load submenu entry 1 Y 279 -> 339"),
    # multiplayer setup: VA 0x5184F0
    Patch("menu-center-hitboxes", 0x1166F0, "f9000000", "49010000", "0x5184F0 multiplayer setup entry 0 X 249 -> 329"),
    Patch("menu-center-hitboxes", 0x1166F4, "87010000", "c3010000", "0x5184F4 multiplayer setup entry 0 Y 391 -> 451"),
    Patch("menu-center-hitboxes", 0x116725, "49010000", "99010000", "0x518525 multiplayer setup entry 1 X 329 -> 409"),
    Patch("menu-center-hitboxes", 0x116729, "98010000", "d4010000", "0x518529 multiplayer setup entry 1 Y 408 -> 468"),
    Patch("menu-center-hitboxes", 0x11675A, "88010000", "d8010000", "0x51855A multiplayer setup entry 2 X 392 -> 472"),
    Patch("menu-center-hitboxes", 0x11675E, "81010000", "bd010000", "0x51855E multiplayer setup entry 2 Y 385 -> 445"),
    Patch("menu-center-hitboxes", 0x11678F, "af010000", "ff010000", "0x51858F multiplayer setup entry 3 X 431 -> 511"),
    Patch("menu-center-hitboxes", 0x116793, "81010000", "bd010000", "0x518593 multiplayer setup entry 3 Y 385 -> 445"),
    # multiplayer scenario: VA 0x518690
    Patch("menu-center-hitboxes", 0x116890, "b4000000", "04010000", "0x518690 multiplayer scenario entry 0 X 180 -> 260"),
    Patch("menu-center-hitboxes", 0x116894, "f6000000", "32010000", "0x518694 multiplayer scenario entry 0 Y 246 -> 306"),
    Patch("menu-center-hitboxes", 0x1168C5, "b4000000", "04010000", "0x5186C5 multiplayer scenario entry 1 X 180 -> 260"),
    Patch("menu-center-hitboxes", 0x1168C9, "18010000", "54010000", "0x5186C9 multiplayer scenario entry 1 Y 280 -> 340"),
    Patch("menu-center-hitboxes", 0x1168FA, "b4000000", "04010000", "0x5186FA multiplayer scenario entry 2 X 180 -> 260"),
    Patch("menu-center-hitboxes", 0x1168FE, "38010000", "74010000", "0x5186FE multiplayer scenario entry 2 Y 312 -> 372"),
    Patch("menu-center-hitboxes", 0x11692F, "b4000000", "04010000", "0x51872F multiplayer scenario entry 3 X 180 -> 260"),
    Patch("menu-center-hitboxes", 0x116933, "58010000", "94010000", "0x518733 multiplayer scenario entry 3 Y 344 -> 404"),
    Patch("menu-center-hitboxes", 0x116964, "f8000000", "48010000", "0x518764 multiplayer scenario entry 4 X 248 -> 328"),
    Patch("menu-center-hitboxes", 0x116968, "88010000", "c4010000", "0x518768 multiplayer scenario entry 4 Y 392 -> 452"),
    Patch("menu-center-hitboxes", 0x116999, "49010000", "99010000", "0x518799 multiplayer scenario entry 5 X 329 -> 409"),
    Patch("menu-center-hitboxes", 0x11699D, "98010000", "d4010000", "0x51879D multiplayer scenario entry 5 Y 408 -> 468"),
    # multiplayer confirm: VA 0x518808
    Patch("menu-center-hitboxes", 0x116A08, "f9000000", "49010000", "0x518808 multiplayer confirm entry 0 X 249 -> 329"),
    Patch("menu-center-hitboxes", 0x116A0C, "88010000", "c4010000", "0x51880C multiplayer confirm entry 0 Y 392 -> 452"),
    Patch("menu-center-hitboxes", 0x116A3D, "49010000", "99010000", "0x51883D multiplayer confirm entry 1 X 329 -> 409"),
    Patch("menu-center-hitboxes", 0x116A41, "98010000", "d4010000", "0x518841 multiplayer confirm entry 1 Y 408 -> 468"),
    # Group A3: DirectInput mouse format.
    # DIDF_ABSAXIS=1, DIDF_RELAXIS=2; DIDFT_RELAXIS=1, DIDFT_AXIS=3.
    Patch("mouse-relative-format", 0x0E87F8, "01000000", "02000000", "0x4E93F0 mouse DIDATAFORMAT absolute axes -> relative axes"),
    Patch("mouse-relative-format", 0x0E8538, "03ffff80", "01ffff80", "0x4E9130 mouse X object DIDFT_AXIS -> DIDFT_RELAXIS"),
    Patch("mouse-relative-format", 0x0E8548, "03ffff80", "01ffff80", "0x4E9140 mouse Y object DIDFT_AXIS -> DIDFT_RELAXIS"),
    Patch("mouse-relative-format", 0x0E8558, "03ffff80", "01ffff80", "0x4E9150 mouse Z object DIDFT_AXIS -> DIDFT_RELAXIS"),
    # Group A3a: actual mouse device data format at 0x4E80F0. This is a
    # diagnostic for wrappers that can expose window/client absolute positions
    # when DIDF_ABSAXIS is requested.
    Patch("mouse-absolute-format", 0x0E74F8, "02000000", "01000000", "0x4E80F0 mouse DIDATAFORMAT relative axes -> absolute axes"),
    # Group A3b: in windowed wrapper mode, exclusive foreground mouse capture
    # can warp/clamp the cursor while the original engine expects relative
    # deltas. The mouse data format at 0x4E80F0 is already DIDF_RELAXIS; keep
    # that and only change SetCooperativeLevel DISCL_EXCLUSIVE|FOREGROUND (5)
    # to DISCL_NONEXCLUSIVE|FOREGROUND (6) for the mouse device at a1+8.
    Patch("mouse-nonexclusive-coop", 0x07B15B, "05", "06", "0x47BD5A mouse SetCooperativeLevel 5 -> 6"),
    # Group A4: DirectInput wrappers can return absolute-style client coords
    # while this engine expects relative deltas. Store nonzero scaled absolute X/Y.
    Patch(
        "mouse-absolute-assign",
        0x05FE61,
        "a1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28",
        "a1a851540085c07406c1e006894224a1ac51540085c07406c1e006894228c7422c0000000090",
        "0x460A50 assign nonzero absolute mouse X/Y instead of accumulating deltas",
    ),
    Patch(
        "mouse-absolute-quarter",
        0x05FE61,
        "a1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28",
        "a1a851540085c07406c1e004894224a1ac51540085c07406c1e004894228c7422c0000000090",
        "0x460A50 assign nonzero quarter-scale absolute mouse X/Y instead of accumulating deltas",
    ),
    Patch(
        "mouse-screenorigin-diagnostic",
        0x05FE61,
        "a1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28",
        "e9aa8d0800909090909090909090909090909090909090909090909090909090909090909090",
        "0x460A50 jump to screen-quarter minus traced client-origin diagnostic updater",
    ),
    Patch(
        "mouse-screenorigin-diagnostic",
        0x0E8C10,
        "00" * 90,
        (
            "a1a851540085c0740bc1e0082d00dc0000894224"
            "a1ac51540085c0740bc1e0082dc0650000894228"
            "c7422c00000000e93e72f7ff"
            + "00" * 38
        ),
        "0x4E9810 code cave: nonzero logical=(DirectInputSample*4)-clientOrigin(880,407), stored at shift=6",
    ),
    Patch(
        "mouse-dynamic-origin",
        0x05FE61,
        "a1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28",
        "e9aa8d0800909090909090909090909090909090909090909090909090909090909090909090",
        "0x460A50 jump to screen-quarter minus dynamic ClientToScreen origin updater",
    ),
    Patch(
        "mouse-dynamic-origin",
        0x0E8C10,
        "00" * 90,
        (
            "89d76a006a0054ff35dc525400ff15e0a34e00"
            "a1a851540085c07411c1e0022b0424c1e0063b47187703894724"
            "a1ac51540085c07412c1e0022b442404c1e0063b471c7703894728"
            "c7472c0000000083c40889fae91e72f7ff"
            + "00"
        ),
        "0x4E9810 code cave: logical=(DirectInputSample*4)-ClientToScreen([0x5452DC], 0,0), skip zero/out-of-bounds transformed samples",
    ),
    Patch(
        "mouse-hybrid-input",
        0x05FE61,
        "a1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28",
        "e9aa8d0800909090909090909090909090909090909090909090909090909090909090909090",
        "0x460A50 jump to hybrid relative/absolute mouse updater",
    ),
    Patch(
        "mouse-hybrid-input",
        0x0E8C10,
        "00" * 90,
        (
            "a1a851540083f8407f0e83f8c07c090faf4220014224eb0f"
            "85c0740b8a8a54040000d3e0894224"
            "a1ac51540083f8407f0e83f8c07c090faf4220014228eb0f"
            "85c0740b8a8a54040000d3e0894228"
            "c7422c00000000e91d72f7ff"
        ),
        "0x4E9810 code cave: small samples stay relative, large samples become absolute coords",
    ),
    Patch(
        "mouse-delta-clamp",
        0x05FE61,
        "a1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28",
        "e9aa8d0800909090909090909090909090909090909090909090909090909090909090909090",
        "0x460A50 jump to relative mouse updater with +/-32 delta clamp",
    ),
    Patch(
        "mouse-delta-clamp",
        0x0E8C10,
        "00" * 90,
        (
            "a1a851540083f8207e05b82000000083f8e07d05b8e0ffffff"
            "0faf42200142248b7220"
            "a1ac51540083f8207e05b82000000083f8e07d05b8e0ffffff"
            "0fafc68b7a28c7422c0000000001c7897a28"
            "e92472f7ff"
            "00000000000000"
        ),
        "0x4E9810 code cave: clamp DirectInput dx/dy to +/-32, then use original relative integration",
    ),
    # Group B: grow map/DD viewport pixel bounds.
    Patch("input-bounds", 0x05F826, "7f020000", "1f030000", "0x460410 max X 639 -> 799"),
    Patch("input-bounds", 0x05F82D, "df010000", "57020000", "0x460410 max Y 479 -> 599"),
    Patch("viewport-init", 0x05F92D, "e0010000", "58020000", "0x460490 viewport bottom 480 -> 600"),
    Patch("viewport-init", 0x05F93B, "80020000", "20030000", "0x460490 viewport right 640 -> 800"),
    Patch("viewport-switch", 0x060212, "e0010000", "58020000", "0x460D80 viewport bottom 480 -> 600"),
    Patch("viewport-switch", 0x06021E, "80020000", "20030000", "0x460D80 viewport right 640 -> 800"),
    Patch(
        "viewport-switch-dynamic-surface",
        0x060211,
        "68e0010000c7402000000000b9800200008b463c31db31d2c7401c0000000089f0e8e9fcffff",
        "e9aa8b0800" + "90" * 33,
        "0x460D80 jump to conditional viewport switch keyed off map metadata pointer",
    ),
    Patch(
        "viewport-switch-dynamic-surface",
        0x0E8DC0,
        "00" * 64,
        (
            "81faa0965100740c"
            "68e0010000b980020000eb0a"
            "6858020000b920030000"
            "8b463c31db31d2"
            "c7402000000000"
            "89f0e82d71f7ffe93f74f7ff"
            + "00" * 8
        ),
        "0x4E99C0 code cave: use 800x600 for map metadata 005196A0, else native 640x480",
    ),
    # Group C: grow main visible tile loops in 0x406FA0 from 9x7 to 12x9.
    Patch("main-loops", 0x0063E9, "07", "09", "map redraw Y loop +7 -> +9"),
    Patch("main-loops", 0x0066F7, "07", "09", "map redraw Y loop +7 -> +9"),
    Patch("main-loops", 0x006814, "07", "09", "map redraw Y loop +7 -> +9"),
    Patch("main-loops", 0x0068E1, "07", "09", "map redraw Y loop +7 -> +9"),
    Patch("main-loops", 0x0069A9, "07", "09", "map redraw Y loop +7 -> +9"),
    Patch("main-loops", 0x006A93, "07", "09", "map redraw Y loop +7 -> +9"),
    Patch("main-loops", 0x006B9F, "07", "09", "map redraw Y loop +7 -> +9"),
    Patch("main-loops", 0x006423, "09", "0c", "map redraw X loop +9 -> +12"),
    Patch("main-loops", 0x00674B, "09", "0c", "map redraw X loop +9 -> +12"),
    Patch("main-loops", 0x00683A, "09", "0c", "map redraw X loop +9 -> +12"),
    Patch("main-loops", 0x006907, "09", "0c", "map redraw X loop +9 -> +12"),
    Patch("main-loops", 0x0069CF, "09", "0c", "map redraw X loop +9 -> +12"),
    Patch("main-loops", 0x006AC1, "09", "0c", "map redraw X loop +9 -> +12"),
    Patch("main-loops", 0x006BEF, "09", "0c", "map redraw X loop +9 -> +12"),
    # Group C2: grow the full map repaint helper at 0x418700. Without this,
    # the first gameplay frame still paints the native 9x6 area plus a
    # clipped 6-tile bottom row, and later partial repaints only gradually
    # touch the new right/bottom HD area.
    Patch("full-redraw-12x9", 0x017B70, "09", "0c", "0x418700 full redraw columns 9 -> 12"),
    Patch("full-redraw-12x9", 0x017B81, "06", "08", "0x418700 full redraw full rows 6 -> 8"),
    Patch("full-redraw-12x9", 0x017DFF, "06", "0c", "0x418700 clipped bottom row columns 6 -> 12"),
    # Group C3: grow only the full-redraw present/copy rectangles proved by
    # CDB to remain native-sized after the 12x9 tile draw. Do not mix this
    # with the older broad sub_418700 experiment unless the narrow group has
    # already been validated.
    Patch("full-redraw-present-bounds-800", 0x017CDE, "5f020000", "1f030000", "0x4188DD full redraw top/right present edge 607 -> 799"),
    Patch("full-redraw-present-bounds-800", 0x017D6C, "5f020000", "1f030000", "0x41896A full redraw right-edge compare 607 -> 799"),
    Patch("full-redraw-present-bounds-800", 0x017D82, "5f020000", "1f030000", "0x418981 full redraw right strip present edge 607 -> 799"),
    Patch("full-redraw-present-bounds-800", 0x017D99, "cf010000", "4f020000", "0x418997 full redraw bottom-edge compare 463 -> 591"),
    Patch("full-redraw-present-bounds-800", 0x017E5E, "cf010000", "4f020000", "0x418A5D full redraw bottom strip present edge 463 -> 591"),
    Patch("full-redraw-present-bounds-800", 0x017E68, "5f020000", "1f030000", "0x418A67 full redraw bottom strip right edge 607 -> 799"),
    # Group C4: keep the minimap dirty-rectangle helper from reading past its
    # own backing surface when full-redraw present rectangles are wider than
    # the original native minimap box.
    Patch(
        "minimap-right-clip",
        0x00C960,
        "56558b35e4025200",
        "e91bc40d00909090",
        "0x40D560 jump to minimap right-edge clamp before original dirty-rect helper",
    ),
    Patch(
        "minimap-right-clip",
        0x0E8D80,
        "00" * 64,
        (
            "56558b35e4025200"
            "668b2d4433520066032d48335200664d6639e8770d"
            "6639eb76036689ebe9be3bf2ffe9183df2ff"
            + "00" * 17
        ),
        "0x4E9980 code cave: skip minimap dirty chunks past right edge, clamp partial right edge, then return",
    ),
    Patch(
        "minimap-hd-right-anchor",
        0x00C790,
        "ba60020000",
        "ba20030000",
        "0x40D390 minimap right anchor 608 -> 800 before left = anchor - minimap_width",
    ),
    # Group D: scroll/click/center helpers. Apply after the first stage is proven.
    Patch("helpers", 0x007080, "09", "0c", "scroll clamp X +9 -> +12"),
    Patch("helpers", 0x007087, "f7", "f4", "scroll clamp map_width -9 -> -12"),
    Patch("helpers", 0x0070B4, "07", "09", "scroll clamp Y +7 -> +9"),
    Patch("helpers", 0x0070BB, "f9", "f7", "scroll clamp map_height -7 -> -9"),
    Patch("helpers", 0x0071D5, "09", "0c", "keyboard scroll right clamp map_width -9 -> -12"),
    Patch("helpers", 0x007268, "07", "09", "keyboard scroll down clamp map_height -7 -> -9"),
    Patch("helpers", 0x00D0B0, "83ee09", "83ee0c", "minimap action clamp map_width -9 -> -12"),
    Patch("helpers", 0x00D0DA, "83ea07", "83ea09", "minimap action clamp map_height -7 -> -9"),
    Patch("helpers", 0x00D124, "83ea07", "83ea09", "minimap action alt-path map_height -7 -> -9"),
    Patch("helpers", 0x00EF01, "04", "06", "center-on-unit X offset 4 -> 6"),
    Patch("helpers", 0x00EF18, "03", "04", "center-on-unit Y offset 3 -> 4"),
    Patch("helpers", 0x00EF4E, "09", "0c", "center-on-unit X +9 -> +12"),
    Patch("helpers", 0x00EF9D, "f7", "f4", "center-on-unit map_width -9 -> -12"),
    Patch("helpers", 0x00EF66, "07", "09", "center-on-unit Y +7 -> +9"),
    Patch("helpers", 0x00EF6D, "f9", "f7", "center-on-unit map_height -7 -> -9"),
    Patch("helpers", 0x00F35B, "09", "0c", "secondary key-scroll right clamp map_width -9 -> -12"),
    Patch("helpers", 0x00F39E, "07", "09", "secondary key-scroll down clamp map_height -7 -> -9"),
    Patch("helpers", 0x017EA6, "09", "0c", "single-tile repaint X +9 -> +12"),
    Patch("helpers", 0x017EB3, "07", "09", "single-tile repaint Y +7 -> +9"),
    Patch("helpers", 0x017ECC, "06", "08", "single-tile repaint last visible row 6 -> 8"),
    Patch("helpers", 0x017EDB, "06", "0c", "single-tile repaint last-row X cutoff 6 -> 12"),
    Patch("helpers", 0x017EEC, "06", "08", "single-tile repaint last visible row 6 -> 8"),
    Patch("helpers", 0x018009, "09", "0c", "area helper width test 9 -> 12"),
    Patch("helpers", 0x018016, "07", "09", "area helper height test 7 -> 9"),
    Patch("helpers", 0x018067, "09", "0c", "area helper X +9 -> +12"),
    Patch("helpers", 0x018080, "07", "09", "area helper Y +7 -> +9"),
    Patch("helpers", 0x018087, "f8", "f6", "area helper map_height -8 -> -10"),
    Patch("helpers", 0x0180C2, "f6", "f3", "area helper map_width -10 -> -13"),
    Patch("helpers", 0x018112, "09", "0c", "center helper X +9 -> +12"),
    Patch("helpers", 0x01812A, "07", "09", "center helper Y +7 -> +9"),
    Patch("helpers", 0x018131, "f8", "f6", "center helper map_height -8 -> -10"),
    Patch("helpers", 0x018163, "f6", "f3", "center helper map_width -10 -> -13"),
    # Group E: PlayGame restores saved per-player scroll before movement/helper
    # clamps can run. Clamp that restored value to the 12x9 viewport edge before
    # the first map redraw, preserving the original registers for the call that
    # used to live at 0x40B76A.
    Patch("saved-scroll-clamp", 0x00AB6A, "e8e1200000", "e911e10d00", "0x40B76A jump to saved 12x9 scroll clamp"),
    Patch(
        "saved-scroll-clamp",
        0x0E8C80,
        "00" * 80,
        (
            "60a1e402520085c07436"
            "8b98e022020083eb0c790231db3998e82202007e068998e8220200"
            "8b98e422020083eb09790231db3998ec2202007e068998ec220200"
            "61e88a3ff2ffe9a41ef2ff"
            + "00" * 5
        ),
        "0x4E9880 code cave: clamp restored scroll to max(0,map_width-12/map_height-9), call 0x40D850, return",
    ),
    # Variant of the saved-scroll hook that also upgrades the PlayGame-owned
    # map surface after the main menu has finished using its native 640x480
    # backing store. This deliberately replaces the global menu-surface patch.
    Patch("map-surface-upgrade-scrollclamp", 0x00AB6A, "e8e1200000", "e911e10d00", "0x40B76A jump to map-surface upgrade and saved 12x9 scroll clamp"),
    Patch(
        "map-surface-upgrade-scrollclamp",
        0x0E8C80,
        "00" * 144,
        (
            "60a1e002520085c0740766813820037428"
            "b8bc000000e86583f7ff85c0741a53bb58020000ba20030000"
            "e8c1a4f1ff5b85c07405a3e0025200"
            "a1e402520085c07436"
            "8b98e022020083eb0c790231db3998e82202007e068998e8220200"
            "8b98e422020083eb09790231db3998ec2202007e068998ec220200"
            "61e8523ff2ffe96c1ef2ff"
            + "00" * 13
        ),
        "0x4E9880 code cave: after menu dispatch allocate/store 800x600 dword_5202E0 if needed, clamp restored scroll, call 0x40D850, return",
    ),
)


VIEWPORT_GROUPS = ("input-bounds", "viewport-init", "viewport-switch")
MENU_SAFE_VIEWPORT_GROUPS = ("input-bounds", "viewport-init")
DYNAMIC_VIEWPORT_GROUPS = ("input-bounds", "viewport-init", "viewport-switch-dynamic-surface")


STAGE_GROUPS = {
    "display": ("display",),
    "display-absinput": ("display", "mouse-absolute-assign"),
    "display-centered-visual-absinput": ("display", "menu-only-center-blit", "mouse-absolute-assign"),
    "isolate-gameplay-surface-absinput": ("display", "gameplay-surface", "mouse-absolute-assign"),
    "isolate-viewport-init-absinput": (
        "display",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "mouse-absolute-assign",
    ),
    "isolate-input-bounds-absinput": (
        "display",
        "input-bounds",
        "mouse-absolute-assign",
    ),
    "isolate-viewport-call-absinput": (
        "display",
        "viewport-init",
        "mouse-absolute-assign",
    ),
    "isolate-main-loops-absinput": ("display", "main-loops", "mouse-absolute-assign"),
    "isolate-surface-viewport-absinput": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "mouse-absolute-assign",
    ),
    "gameplay-menu640": ("display", "gameplay-surface", *MENU_SAFE_VIEWPORT_GROUPS, "main-loops"),
    "gameplay-menu640-centered": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "menu-only-center-blit",
    ),
    "gameplay-menu640-centered-hitboxes": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "menu-only-center-blit",
        "menu-center-hitboxes",
    ),
    "gameplay-menu640-centered-relinput": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "menu-only-center-blit",
        "menu-center-hitboxes",
    ),
    "gameplay-menu640-centered-map12-relinput": (
        "display",
        "gameplay-surface",
        *VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
    ),
    "gameplay-menu640-centered-map12-novswitch-relinput": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
    ),
    "gameplay-menu640-centered-map12-nonexclusive": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-nonexclusive-coop",
    ),
    "gameplay-menu640-centered-map12-absinput": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-absolute-assign",
    ),
    "gameplay-menu640-centered-map12-absnonexclusive": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-nonexclusive-coop",
        "mouse-absolute-assign",
    ),
    "gameplay-menu640-centered-map12-absformat": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-absolute-format",
        "mouse-nonexclusive-coop",
        "mouse-absolute-assign",
    ),
    "gameplay-menu640-centered-map12-hybridmouse": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-nonexclusive-coop",
        "mouse-hybrid-input",
    ),
    "gameplay-menu640-centered-map12-deltaclamp": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-delta-clamp",
    ),
    "gameplay-menu640-centered-map12-absquarter": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-absolute-quarter",
    ),
    "gameplay-menu640-centered-map12-screenorigin": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-screenorigin-diagnostic",
    ),
    "gameplay-menu640-centered-map12-dynorigin": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
    ),
    "gameplay-menu640-centered-map12-dynorigin-sharedscratch": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
    ),
    "gameplay-menu640-centered-map12-dynorigin-menusurface": (
        "display",
        "shared-surface",
        "gameplay-surface",
        "menu-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
    ),
    "gameplay-menu640-centered-map12-dynorigin-menusurface-scrollclamp": (
        "display",
        "shared-surface",
        "gameplay-surface",
        "menu-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "saved-scroll-clamp",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapclip": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "minimap-hd-right-anchor",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "minimap-hd-right-anchor",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *DYNAMIC_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "minimap-hd-right-anchor",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *DYNAMIC_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "minimap-hd-right-anchor",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
        "right-bottom-compose-proof",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *DYNAMIC_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "minimap-hd-right-anchor",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
        "castle-ui-center-present",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *DYNAMIC_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "minimap-hd-right-anchor",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
        "castle-ui-center-present",
        "castle-ui-centered-input",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *DYNAMIC_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "minimap-hd-right-anchor",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
        "castle-ui-center-present-wrapper",
        "castle-ui-centered-input",
        "castle-overview-center-present-wrapper",
        "castle-overview-centered-input",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *DYNAMIC_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "minimap-hd-right-anchor",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-dynamic-origin",
        "map-surface-upgrade-scrollclamp",
        "castle-ui-center-present-wrapper",
        "castle-ui-centered-input",
        "castle-overview-center-present-wrapper",
        "castle-overview-centered-input",
    ),
    "gameplay-menu640-centered-map12-hybridmouse-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch": (
        "display",
        "shared-surface",
        "gameplay-surface",
        *DYNAMIC_VIEWPORT_GROUPS,
        "main-loops",
        "full-redraw-12x9",
        "full-redraw-present-bounds-800",
        "minimap-right-clip",
        "minimap-hd-right-anchor",
        "helpers",
        "surface-blit-hd-aware",
        "menu-center-hitboxes",
        "mouse-nonexclusive-coop",
        "mouse-hybrid-input",
        "map-surface-upgrade-scrollclamp",
    ),
    "gameplay-menu640-absinput": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "mouse-absolute-assign",
    ),
    "gameplay-menu640-centered-visual-absinput": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "menu-only-center-blit",
        "mouse-absolute-assign",
    ),
    "gameplay-menu640-centered-mousefix": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-relative-format",
    ),
    "gameplay-menu640-centered-nonexclusive": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-nonexclusive-coop",
    ),
    "gameplay-menu640-centered-absinput": (
        "display",
        "gameplay-surface",
        *MENU_SAFE_VIEWPORT_GROUPS,
        "main-loops",
        "menu-only-center-blit",
        "menu-center-hitboxes",
        "mouse-absolute-assign",
    ),
    "gameplay": ("display", "gameplay-surface", *VIEWPORT_GROUPS, "main-loops"),
    "gameplay-helpers": ("display", "gameplay-surface", *VIEWPORT_GROUPS, "main-loops", "helpers"),
    "core": ("display", "shared-surface", "gameplay-surface", "menu-surface", *VIEWPORT_GROUPS),
    "draw": ("display", "shared-surface", "gameplay-surface", "menu-surface", *VIEWPORT_GROUPS, "main-loops"),
    "helpers": (
        "display",
        "shared-surface",
        "gameplay-surface",
        "menu-surface",
        *VIEWPORT_GROUPS,
        "main-loops",
        "helpers",
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def select_patches(stage: str) -> list[Patch]:
    groups = set(STAGE_GROUPS[stage])
    return [patch for patch in PATCHES if patch.group in groups]


def validate_input(data: bytes, patches: Iterable[Patch]) -> None:
    errors: list[str] = []
    for patch in patches:
        actual = data[patch.offset : patch.offset + len(patch.old)]
        if actual != patch.old:
            errors.append(
                f"0x{patch.offset:06X}: expected {patch.old.hex(' ').upper()}, "
                f"found {actual.hex(' ').upper()} ({patch.note})"
            )
    if errors:
        details = "\n".join(errors)
        raise SystemExit(f"Refusing to patch: {len(errors)} byte validation failure(s).\n{details}")


def apply_patches(data: bytes, patches: Iterable[Patch]) -> bytes:
    patched = bytearray(data)
    for patch in patches:
        patched[patch.offset : patch.offset + len(patch.new)] = patch.new
    return bytes(patched)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an 800x600 Clash95 HD viewport test executable."
    )
    parser.add_argument(
        "--input",
        default="clash95.exe",
        type=Path,
        help="source executable to patch, default: clash95.exe",
    )
    parser.add_argument(
        "--output",
        default="clash95_hdtest.exe",
        type=Path,
        help="patched executable to write, default: clash95_hdtest.exe",
    )
    parser.add_argument(
        "--stage",
        choices=tuple(STAGE_GROUPS),
        default=DEFAULT_STAGE,
        help=(
            "patch stage: gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch=current "
            "HD map proof path with centered 640x480 menus, dynamic wrapper mouse origin, "
            "post-menu 800x600 map surface, 12x9 redraw/scroll helpers, moved HD minimap, "
            "and metadata-conditional viewport switch; "
            "display=render/window only; gameplay-menu640="
            "HD gameplay with native 640x480 menu/cursor switches; "
            "display-absinput=display only plus absolute mouse diagnostic; "
            "isolate-* stages add one suspicious group at a time; "
            "gameplay-menu640-centered centers the 640x480 menu-surface blit only; "
            "gameplay-menu640-centered-hitboxes/relinput also moves start-menu buttons; "
            "gameplay-menu640-centered-map12-relinput additionally expands the later viewport switch; "
            "gameplay-menu640-centered-map12-novswitch-relinput keeps that switch native; "
            "gameplay-menu640-centered-map12-nonexclusive also changes mouse cooperative level 5->6; "
            "gameplay-menu640-centered-map12-absnonexclusive combines 5->6 with absolute X/Y assignment; "
            "gameplay-menu640-centered-map12-absformat also requests absolute axes from the actual mouse format; "
            "gameplay-menu640-centered-map12-hybridmouse uses a code cave to keep small relative deltas and assign large samples; "
            "gameplay-menu640-centered-map12-deltaclamp clamps relative mouse dx/dy to +/-32 before speed scaling; "
            "gameplay-menu640-centered-map12-absquarter assigns DirectInput X/Y as quarter-scale absolute coords; "
            "gameplay-menu640-centered-map12-dynorigin subtracts the live ClientToScreen origin from quartered screen coords; "
            "gameplay-menu640-centered-map12-dynorigin-menusurface also grows the 0x447DC0 menu/game surface; "
            "gameplay-menu640-centered-map12-dynorigin-menusurface-scrollclamp also patches PlayGame saved-scroll restore; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp upgrades that surface only after menu dispatch; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds also widens proven sub_418700 present rectangles; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch makes the later sub_460D80 viewport switch use 800x600 for the map metadata object; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose adds validation-only status/action composition copies into the HD bottom strip; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter also recenters the native castle/barracks UI layer visually; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox additionally wraps castle/barracks polling, descriptor hit tests, and the barracks grid hit-test call with the matching -80,-60 mouse transform; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all is the current broad castle-interior validation target and uses a present-callback wrapper so stock castle/barracks rendering runs before the 80,60 centering copy, plus a native-render-first full-overview 00422020 visual wrapper and 00422520 hit-test wrapper; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter is a probe-first battle validation stage with no battle-specific patch groups until battle routes are proven; "
            "gameplay-menu640-centered-map12-hybridmouse-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch keeps that stack but tests hybrid DirectInput; "
            "gameplay-menu640-centered-map12-absinput assigns large DirectInput X/Y samples as coordinates; "
            "gameplay-menu640-absinput keeps native menu placement with absolute mouse; "
            "gameplay-menu640-centered-visual-absinput centers only the 640x480 menu blit; "
            "gameplay-menu640-centered-mousefix also sets DirectInput mouse axes relative; "
            "gameplay-menu640-centered-absinput assigns absolute mouse coords as a diagnostic; "
            "gameplay=menu-safer display+gameplay surface+viewport+loops; "
            "core=broad A+B; draw=legacy broad A+B+C; helpers/"
            "gameplay-helpers add experimental interaction helpers"
        ),
    )
    parser.add_argument(
        "--allow-unknown-sha",
        action="store_true",
        help="skip whole-file SHA-256 guard; per-offset byte validation still runs",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="allow replacing an existing output file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = args.input
    output_path = args.output

    if not source_path.is_file():
        raise SystemExit(f"Input file does not exist: {source_path}")
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"Output already exists: {output_path} (use --overwrite to replace it)")
    if source_path.resolve() == output_path.resolve():
        raise SystemExit("Refusing to patch in place. Choose a different --output path.")

    data = source_path.read_bytes()
    actual_sha = sha256(data)
    if actual_sha != EXPECTED_SHA256 and not args.allow_unknown_sha:
        raise SystemExit(
            "Input SHA-256 does not match the analyzed Clash95 executable.\n"
            f"Expected: {EXPECTED_SHA256.upper()}\n"
            f"Actual:   {actual_sha.upper()}\n"
            "Use --allow-unknown-sha only if you know this build has the same offsets."
        )

    patches = select_patches(args.stage)
    validate_input(data, patches)
    patched = apply_patches(data, patches)
    output_path.write_bytes(patched)

    print(f"Wrote {output_path}")
    print(f"Stage: {args.stage}")
    print(f"Patches applied: {len(patches)}")
    print(f"Input SHA-256:  {actual_sha.upper()}")
    print(f"Output SHA-256: {sha256(patched).upper()}")


if __name__ == "__main__":
    main()

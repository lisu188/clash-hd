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
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbar``
adds a validation-only first-mission selected-unit proof: the 00406980
text/morale action panel route renders natively first, then a narrow copyback
places that panel in the 800x600 bottom strip for hidden-desktop evidence.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw``
extends that validation lane by re-running the selected-unit panel after the
full map redraw exits, so the final dumped surface can prove the action bar
survives the normal redraw cadence at the bottom of the screen.
``--stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose-unitselectactionbarpostredraw``
combines those validation lanes so a first-mission dump can show which right,
bottom, and minimap black patches remain after the controlled bottom-strip
composition hooks and the fixed selected-unit bottom redraw both run.
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
is the battle UI validation target. It includes the castlecenter-all byte set
plus a battle-present centering wrapper after hidden CDB evidence proved the
`Unit_Attack -> 0x42E9E0` route.
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
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Iterable


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
    Patch(
        "right-bottom-action-descriptor-anchor",
        0x01918E,
        "80020000",
        "20030000",
        "0x419D8C descriptor draw x clip 640 -> 800 for HD right-bottom action descriptors",
    ),
    Patch(
        "right-bottom-action-descriptor-anchor",
        0x113330,
        "3701000018000000",
        "d701000090000000",
        "0x515130 action descriptor 0 position (311,24) -> (471,144)",
    ),
    Patch(
        "right-bottom-action-descriptor-anchor",
        0x113365,
        "370100004e000000",
        "d7010000c6000000",
        "0x515165 action descriptor 1 position (311,78) -> (471,198)",
    ),
    Patch(
        "right-bottom-action-descriptor-anchor",
        0x11339A,
        "29000000a9010000",
        "c900000021020000",
        "0x51519A action descriptor 2 position (41,425) -> (201,545)",
    ),
    Patch(
        "right-bottom-action-descriptor-anchor",
        0x1133CF,
        "9c000000a9010000",
        "3c01000021020000",
        "0x5151CF action descriptor 3 position (156,425) -> (316,545)",
    ),
    Patch(
        "right-bottom-action-descriptor-anchor",
        0x113404,
        "86010000a9010000",
        "2602000021020000",
        "0x515204 action descriptor 4 position (390,425) -> (550,545)",
    ),
    Patch(
        "right-bottom-action-descriptor-anchor",
        0x113439,
        "fd010000a9010000",
        "9d02000021020000",
        "0x515239 action descriptor 5 position (509,425) -> (669,545)",
    ),
    Patch(
        "right-bottom-action-descriptor-anchor",
        0x11346E,
        "c201000074010000",
        "62020000ec010000",
        "0x51526E action descriptor 6 position (450,372) -> (610,492)",
    ),
    Patch(
        "right-bottom-action-descriptor-anchor",
        0x1134A3,
        "6200000074010000",
        "02010000ec010000",
        "0x5152A3 action descriptor 7 position (98,372) -> (258,492)",
    ),
    Patch(
        "right-bottom-action-native-center-wrapper",
        0x032D14,
        "e8a7220000",
        "e8c77e0e00",
        "0x433914 post-owner action call 0x435BC0 -> native 640x480 temp-surface wrapper at 0x51B7E0",
    ),
    Patch(
        "right-bottom-action-native-center-wrapper",
        0x1199E0,
        "00" * 192,
        (
            "6083ec08a1e0025200890424b8bc000000e80a64f4ff85c00f8474000000"
            "bbe0010000ba80020000e86385eeff89442404a3e00252008b442424"
            "8b4c24208b54241c8b5c24188b6c24108b74240c8b7c2408e889a3"
            "f1ff894424248b34248b7c24048935e00252006a3c6a5068df010000"
            "687f02000031c931db89f289f8e87d6ceeffb8d84c5400e83356f4ff"
            "83c40861c383c40861e945a3f1ff"
            + "00" * 37
        ),
        "0x51B7E0 DGROUP cave: allocate a temporary 640x480 action surface, run stock 0x435BC0 there, restore the 800x600 map surface, center-copy native action UI at 80,60, then present",
    ),
    Patch(
        "battle-ui-center-present-wrapper",
        0x02E6F5,
        "e8a61b0300",
        "e806c70e00",
        "0x42F2F5 battle initial Render_Present call -> 0x51BA00 battle-only native-centering present wrapper",
    ),
    Patch(
        "battle-ui-center-present-wrapper",
        0x119C00,
        "00" * 160,
        (
            "833d48205300007506e89254f4ffc360a1e00252006a006a0068df"
            "010000bac0d45100687f02000031c931dbe8af6aeeffa1e002"
            "5200e82564eeff8b15e00252006a3c6a5068df010000687f0200"
            "0031c931dbb8c0d45100e8836aeeff61e83d54f4ffc3"
            + ("00" * 60)
        ),
        "0x51BA00 DGROUP cave: when dword_532048 marks the battle UI live, copy the native 640x480 battle frame to scratch, clear the 800x600 target, center-copy at 80,60, then Present",
    ),
    Patch(
        "battle-grid-centered-input",
        0x02D8ED,
        "e85ee6ffff",
        "e8aed50e00",
        "0x42E4ED battle tactical-grid hit-test call 0x42CB50 -> centered mouse wrapper 0x51BAA0",
    ),
    Patch(
        "battle-grid-centered-input",
        0x119CA0,
        "00" * 80,
        (
            "51528a0d2c515400ba50000000d3e22915fc4c5400ba3c000000d3e2"
            "2915004d54005a59e88710f1ff5051528a0d2c515400ba50000000d3e2"
            "0115fc4c5400ba3c000000d3e20115004d54005a5958c3"
        ),
        "0x51BAA0 DGROUP cave: wrap 0x42CB50 battle tactical-grid hit tests with logical mouse -80,-60 and restore",
    ),
    Patch(
        "battle-ui-centered-input",
        0x02D901,
        "e8bab8feff",
        "e9ead50e00",
        "0x42E501 battle descriptor hit-test call 0x419DC0 -> centered mouse wrapper 0x51BAF0",
    ),
    Patch(
        "battle-ui-centered-input",
        0x119CF0,
        "00" * 84,
        (
            "51528a0d2c515400ba50000000d3e22915fc4c5400ba3c000000d3e2"
            "2915004d54005a59e8a7e2efff5051528a0d2c515400ba50000000d3e2"
            "0115fc4c5400ba3c000000d3e20115004d54005a5958e9c229f1ff"
        ),
        "0x51BAF0 DGROUP cave: wrap 0x419DC0 battle descriptor hit tests with logical mouse -80,-60, restore, then resume 0x42E506",
    ),
    Patch(
        "unit-selection-action-bar-map-surface",
        0x005E1A,
        "bbc0d45100ba57010000",
        "e9315111009090909090",
        "0x406A1A selected-unit info/action setup -> use dword_5202E0 as the draw target",
    ),
    Patch(
        "unit-selection-action-bar-map-surface",
        0x119D50,
        "00" * 16,
        "8b1de0025200ba57010000e9c4aeeeff",
        "0x51BB50 DGROUP cave: load EBX from dword_5202E0, restore text Y, then resume 0x406A24",
    ),
    Patch(
        "unit-selection-action-bar-map-surface",
        0x005E24,
        "e877bf0100",
        "e847511100",
        "0x406A24 selected-unit text panel call 0x4229A0 -> map-surface copyback wrapper",
    ),
    Patch(
        "unit-selection-action-bar-map-surface",
        0x119D70,
        "00" * 96,
        (
            "bbc0d45100ff74240cff74240cff74240ce81a6ef0ff83c40c608b15e002"
            "520085d2743866813a2003723131c031db31c98b3d006f5200"
            "2b3df86e5200be1300000090909090909090684402000068d7"
            "00000090905657e81469eeff61c3"
            + "00" * 2
        ),
        "0x51BB70 DGROUP cave: draw stock 0x4229A0 to the default surface, then crop source rows 0..19 and copy its native text panel to dword_5202E0 at centered bottom-edge destination 215,580",
    ),
    Patch(
        "unit-selection-action-bar-post-redraw",
        0x00A23F,
        "b8c0d4510089cae8f59bffff5a59c3",
        "e98c0d1100" + "90" * 10,
        "0x40AE3F common sub_40ADF0 exit -> post-redraw selected-unit action-bar wrapper 0x51BBD0",
    ),
    Patch(
        "unit-selection-action-bar-post-redraw",
        0x00A26E,
        "b8c0d4510089cae8c69bffff5a59c3",
        "e95d0d1100" + "90" * 10,
        "0x40AE6E game-state-11 sub_40ADF0 exit -> post-redraw selected-unit action-bar wrapper 0x51BBD0",
    ),
    Patch(
        "unit-selection-action-bar-post-redraw",
        0x119DD0,
        "00" * 64,
        (
            "b8c0d4510089cae8648eeeff9c60833de4025200007419"
            "833de0025200007410833d581b5100ff740731ede880adeeff"
            "619d5a59c3"
            + "00" * 11
        ),
        "0x51BBD0 DGROUP cave: restore 0051D4C0 render handle, then rerun 0x406980 after full redraw when a unit is selected",
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
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction": (
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
        "right-bottom-action-descriptor-anchor",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter": (
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
        "right-bottom-action-native-center-wrapper",
        "castle-ui-centered-input",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter-no-castleinput": (
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
        "right-bottom-action-native-center-wrapper",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbar": (
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
        "unit-selection-action-bar-map-surface",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw": (
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
        "unit-selection-action-bar-map-surface",
        "unit-selection-action-bar-post-redraw",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose-unitselectactionbarpostredraw": (
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
        "unit-selection-action-bar-map-surface",
        "unit-selection-action-bar-post-redraw",
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
        "battle-ui-center-present-wrapper",
    ),
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe": (
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
        "battle-ui-center-present-wrapper",
        "battle-grid-centered-input",
        "battle-ui-centered-input",
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


# ---------------------------------------------------------------------------
# Resolution parameterization.
#
# The legacy PATCHES table above is the frozen byte-for-byte source of truth
# for the 800x600 resolution; it is never modified. Other resolutions are
# generated from it through the RECIPES registry: each parameterized patch
# entry carries a recipe describing which bytes are resolution-dependent and
# which formula produces them. Recipes verify the legacy value before
# splicing, so a wrong recipe fails loudly instead of emitting silent bytes.
# ---------------------------------------------------------------------------

LEGACY_RESOLUTION = (800, 600)
RESOLUTION_PRESETS = ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080")

MENU_NATIVE_WIDTH = 640
MENU_NATIVE_HEIGHT = 480
TILE_SIZE = 64
TILE_ORIGIN_X = 32
TILE_ORIGIN_Y = 16


class ResolutionError(ValueError):
    """Invalid resolution or a recipe/legacy-table mismatch."""


class ResolutionNotSupportedError(ResolutionError):
    """The requested stage/group cannot be generated for this resolution yet."""


@dataclass(frozen=True)
class ResolutionProfile:
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 800 or self.height < 600:
            raise ResolutionError(
                f"Resolution {self.width}x{self.height} is below the 800x600 minimum "
                "(native 640x480 screens must fit centered)."
            )
        if self.width % 2 or self.height % 2:
            raise ResolutionError(
                f"Resolution {self.width}x{self.height} must have even width and "
                "height so the 640x480 centering offsets stay integral."
            )
        if self.width >= 32768 or self.height >= 32768:
            raise ResolutionError(
                f"Resolution {self.width}x{self.height} exceeds imm16 comparison slots."
            )

    @property
    def key(self) -> str:
        return f"{self.width}x{self.height}"

    # Centering offset for native 640x480 screens: (80, 60) at 800x600.
    @property
    def off_x(self) -> int:
        return (self.width - MENU_NATIVE_WIDTH) // 2

    @property
    def off_y(self) -> int:
        return (self.height - MENU_NATIVE_HEIGHT) // 2

    # Right-bottom action descriptor shift: full delta from the native canvas.
    @property
    def shift_x(self) -> int:
        return self.width - MENU_NATIVE_WIDTH

    @property
    def shift_y(self) -> int:
        return self.height - MENU_NATIVE_HEIGHT

    # Visible full tiles: 64px tiles drawn from map origin (32, 16).
    @property
    def tiles_x(self) -> int:
        return (self.width - TILE_ORIGIN_X) // TILE_SIZE

    @property
    def tiles_y(self) -> int:
        return (self.height - TILE_ORIGIN_Y) // TILE_SIZE

    # Full-tile-grid present edges. formula-justified: at 800x600 EDGEX=799
    # coincides with W-1 but EDGEY=591 differs from H-1=599, proving the
    # sub_418700 present rectangles end on the tile grid, not the screen edge.
    @property
    def edge_x(self) -> int:
        return TILE_ORIGIN_X + TILE_SIZE * self.tiles_x - 1

    @property
    def edge_y(self) -> int:
        return TILE_ORIGIN_Y + TILE_SIZE * self.tiles_y - 1

    @property
    def max_x(self) -> int:
        return self.width - 1

    @property
    def max_y(self) -> int:
        return self.height - 1

    # Leftover partial-tile strips (diagnostic; drawn by the engine's native
    # right-strip/bottom-row code paths).
    @property
    def partial_col_px(self) -> int:
        return (self.width - TILE_ORIGIN_X) % TILE_SIZE

    @property
    def partial_row_px(self) -> int:
        return (self.height - TILE_ORIGIN_Y) % TILE_SIZE


def parse_resolution(text: str) -> ResolutionProfile:
    match = re.fullmatch(r"(\d{3,5})x(\d{3,5})", text.strip())
    if not match:
        raise ResolutionError(f"Resolution must look like 800x600, got: {text!r}")
    return ResolutionProfile(int(match.group(1)), int(match.group(2)))


PROFILE_800 = ResolutionProfile(*LEGACY_RESOLUTION)

FORMULAS: dict[str, Callable[[ResolutionProfile], int]] = {
    "W": lambda p: p.width,
    "H": lambda p: p.height,
    "W-1": lambda p: p.max_x,
    "H-1": lambda p: p.max_y,
    "OFFX": lambda p: p.off_x,
    "OFFY": lambda p: p.off_y,
    "SHIFTX": lambda p: p.shift_x,
    "SHIFTY": lambda p: p.shift_y,
    "TX": lambda p: p.tiles_x,
    "TY": lambda p: p.tiles_y,
    "-TX": lambda p: -p.tiles_x,
    "-TY": lambda p: -p.tiles_y,
    "-(TX+1)": lambda p: -(p.tiles_x + 1),
    "-(TY+1)": lambda p: -(p.tiles_y + 1),
    "TX//2": lambda p: p.tiles_x // 2,
    "TY//2": lambda p: p.tiles_y // 2,
    "TY-1": lambda p: p.tiles_y - 1,
    "EDGEX": lambda p: p.edge_x,
    "EDGEY": lambda p: p.edge_y,
    # Right-bottom compose strip destinations, anchored to the screen edges:
    # 586=W-214 (214px status/minimap art width), 528=H-72, 524=H-76.
    "W-214": lambda p: p.width - 214,
    "H-72": lambda p: p.height - 72,
    "H-76": lambda p: p.height - 76,
    # Unit-selection action bar: bottom edge dest 580=H-20, centered X
    # 215=(W-370)//2 for the 370px-wide native text panel.
    "H-20": lambda p: p.height - 20,
    "(W-370)//2": lambda p: (p.width - 370) // 2,
}


@dataclass(frozen=True)
class PatternSlot:
    """One resolution-dependent immediate inside a composite patch.

    `pattern` is a hex substring of the LEGACY new bytes (it includes the
    legacy value bytes at offset `at`), so a pattern match simultaneously
    locates the slot and proves the legacy value is what the formula predicts.
    """

    pattern: str
    at: int
    width: int
    value: str
    count: int
    signed: bool = False


@dataclass(frozen=True)
class Recipe:
    kind: str  # "value" | "old-plus" | "fixed" | "splice" | "cave-pending"
    value: str = ""
    signed: bool = False
    deltas: tuple[str, ...] = ()
    slots: tuple[PatternSlot, ...] = ()


def _encode_int(value: int, width: int, signed: bool, context: str) -> bytes:
    try:
        return value.to_bytes(width, "little", signed=signed)
    except OverflowError as exc:
        raise ResolutionError(
            f"{context}: value {value} does not fit in {width} byte(s) "
            f"(signed={signed})"
        ) from exc


# Whole-value 4-byte little-endian entries: (group, offset) -> formula key.
_VALUE_RECIPES: dict[tuple[str, int], str] = {
    ("display", 0x003A64): "H",
    ("display", 0x003A69): "W",
    ("display", 0x060EAD): "H",
    ("display", 0x060EB2): "W",
    ("shared-surface", 0x000E4D): "H",
    ("shared-surface", 0x000E62): "W",
    ("gameplay-surface", 0x00A3BF): "H",
    ("gameplay-surface", 0x00A3C4): "W",
    ("input-bounds", 0x05F826): "W-1",
    ("input-bounds", 0x05F82D): "H-1",
    ("viewport-init", 0x05F92D): "H",
    ("viewport-init", 0x05F93B): "W",
    # formula-justified: EDGEX/EDGEY are tile-grid edges (32+64*TX-1,
    # 16+64*TY-1), not W-1/H-1 — legacy 591 != 599 proves the Y formula.
    ("full-redraw-present-bounds-800", 0x017CDE): "EDGEX",
    ("full-redraw-present-bounds-800", 0x017D6C): "EDGEX",
    ("full-redraw-present-bounds-800", 0x017D82): "EDGEX",
    ("full-redraw-present-bounds-800", 0x017D99): "EDGEY",
    ("full-redraw-present-bounds-800", 0x017E5E): "EDGEY",
    ("full-redraw-present-bounds-800", 0x017E68): "EDGEX",
    # Descriptor draw x clip grows to the full screen width.
    ("right-bottom-action-descriptor-anchor", 0x01918E): "W",
}

# Resolution-independent entries (hooks with rel32 jumps/calls into fixed cave
# addresses, and caves that read all geometry from live memory).
_FIXED_RECIPES: frozenset[tuple[str, int]] = frozenset(
    {
        ("surface-blit-hd-aware", 0x001230),
        ("minimap-right-clip", 0x00C960),
        ("minimap-right-clip", 0x0E8D80),
        ("viewport-switch-dynamic-surface", 0x060211),
        ("mouse-dynamic-origin", 0x05FE61),
        ("mouse-dynamic-origin", 0x0E8C10),
        ("map-surface-upgrade-scrollclamp", 0x00AB6A),
        ("castle-ui-centered-input", 0x034F90),
        ("castle-ui-centered-input", 0x034FB3),
        ("castle-ui-centered-input", 0x0351F5),
        ("castle-ui-centered-input", 0x034E17),
        ("castle-overview-center-present-wrapper", 0x02172E),
        ("castle-overview-center-present-wrapper", 0x021A74),
        ("castle-overview-centered-input", 0x021920),
        ("right-bottom-compose-proof", 0x0346B3),
        ("right-bottom-compose-proof", 0x0351A5),
        ("right-bottom-action-native-center-wrapper", 0x032D14),
        ("battle-ui-center-present-wrapper", 0x02E6F5),
        ("battle-grid-centered-input", 0x02D8ED),
        ("battle-ui-centered-input", 0x02D901),
        ("unit-selection-action-bar-map-surface", 0x005E1A),
        ("unit-selection-action-bar-map-surface", 0x119D50),
        ("unit-selection-action-bar-map-surface", 0x005E24),
        ("unit-selection-action-bar-post-redraw", 0x00A23F),
        ("unit-selection-action-bar-post-redraw", 0x00A26E),
        ("unit-selection-action-bar-post-redraw", 0x119DD0),
    }
)

# Centered-input mouse offsets: mov edx, OFFX/OFFY before the shifted
# subtract/add against dword_544CFC/dword_544D00 (the single shared mouse
# model). Each wrapper subtracts on entry and adds back on exit.
_MOUSE_OFFX = "ba50000000"
_MOUSE_OFFY = "ba3c000000"


def _mouse_offset_slots(count: int) -> tuple[PatternSlot, ...]:
    return (
        PatternSlot(_MOUSE_OFFX, 1, 4, "OFFX", count),
        PatternSlot(_MOUSE_OFFY, 1, 4, "OFFY", count),
    )


_SPLICE_RECIPES: dict[tuple[str, int], tuple[PatternSlot, ...]] = {
    # mov edx, 800: minimap right anchor = screen width.
    ("minimap-hd-right-anchor", 0x00C790): (
        PatternSlot("ba20030000", 1, 4, "W", 1),
    ),
    # Conditional viewport switch cave: push H / mov ecx, W for the map
    # metadata branch (native 480/640 branch untouched).
    ("viewport-switch-dynamic-surface", 0x0E8DC0): (
        PatternSlot("6858020000", 1, 4, "H", 1),
        PatternSlot("b920030000", 1, 4, "W", 1),
    ),
    # Map-surface upgrade + scroll clamp cave: cmp word width, alloc H/W,
    # clamp scroll to map_width-TX / map_height-TY. The 83-group imm8 slots
    # are sign-extended by the CPU, so they are signed even when positive.
    ("map-surface-upgrade-scrollclamp", 0x0E8C80): (
        PatternSlot("6681382003", 3, 2, "W", 1),
        PatternSlot("bb58020000", 1, 4, "H", 1),
        PatternSlot("ba20030000", 1, 4, "W", 1),
        PatternSlot("83eb0c", 2, 1, "TX", 1, signed=True),
        PatternSlot("83eb09", 2, 1, "TY", 1, signed=True),
    ),
    # helpers entries whose sub imm8 keeps its opcode prefix in the patch.
    ("helpers", 0x00D0B0): (PatternSlot("83ee0c", 2, 1, "TX", 1, signed=True),),
    ("helpers", 0x00D0DA): (PatternSlot("83ea09", 2, 1, "TY", 1, signed=True),),
    ("helpers", 0x00D124): (PatternSlot("83ea09", 2, 1, "TY", 1, signed=True),),
    # Right-bottom compose strip destinations (native source rects untouched).
    ("right-bottom-compose-proof", 0x1114E0): (
        PatternSlot("6810020000", 1, 4, "H-72", 1),
        PatternSlot("684a020000", 1, 4, "W-214", 1),
    ),
    ("right-bottom-compose-proof", 0x112080): (
        PatternSlot("680c020000", 1, 4, "H-76", 1),
    ),
    # Unit-selection action bar copyback destination.
    ("unit-selection-action-bar-map-surface", 0x119D70): (
        PatternSlot("6844020000", 1, 4, "H-20", 1),
        PatternSlot("68d7000000", 1, 4, "(W-370)//2", 1),
    ),
    # Centered-input wrapper caves (mov imm32 mouse offsets).
    ("castle-ui-centered-input", 0x1113C5): _mouse_offset_slots(2),
    ("castle-ui-centered-input", 0x111420): _mouse_offset_slots(1),
    ("castle-ui-centered-input", 0x111460): _mouse_offset_slots(1),
    ("castle-ui-centered-input", 0x11148A): _mouse_offset_slots(2),
    ("battle-grid-centered-input", 0x119CA0): _mouse_offset_slots(2),
    ("battle-ui-centered-input", 0x119CF0): _mouse_offset_slots(2),
}

@dataclass(frozen=True)
class TemplateSlot:
    at: int
    width: int
    value: str
    signed: bool = False


@dataclass(frozen=True)
class CaveTemplate:
    """Re-authored parameterized cave with a fixed imm32 layout.

    `template_hex` is the parameterized encoding carrying the 800x600 values
    in its slots, padded with zeros to the cave allotment. The branch tables
    record every control-flow instruction of both variants (offset, kind,
    absolute target VA); rel32/rel8 displacements were recomputed once at
    authoring time from these targets and are verified by
    tools/test_patch_resolution.py against both byte encodings.
    """

    template_hex: str
    slots: tuple[TemplateSlot, ...]
    legacy_va: int
    param_va: int
    legacy_branches: tuple[tuple[int, str, int], ...]
    param_branches: tuple[tuple[int, str, int], ...]
    new_offset: int | None = None


# The two 86-byte castle-present caves at file 0x11136F are hard-adjacent to
# the castle-ui-centered-input cave at 0x1113C5 and cannot grow in place;
# their imm32 variants relocate to the zero region at file 0x119E20
# (VA 0x51BC20, verified all-zero in the source executable and enforced
# fail-closed by the old-bytes validation at patch time).
_RELOCATED_CASTLE_PRESENT_OFFSET = 0x119E20
_RELOCATED_CASTLE_PRESENT_VA = 0x51BC20

_CAVE_TEMPLATES: dict[tuple[str, int], CaveTemplate] = {
    ("surface-blit-hd-aware", 0x0E8D20): CaveTemplate(
        template_hex=(
            "6089c6bddf010000bf7f02000066813e2003751266817e025802750a"
            "bd57020000bf1f03000031c931db3b35e00252007513"
            "66813e8002750c683c0000006850000000eb02515155bac0d45100"
            "5789f0e86b8bf1ff61c3" + "00" * 9
        ),
        slots=(
            TemplateSlot(16, 2, "W"),
            TemplateSlot(24, 2, "H"),
            TemplateSlot(29, 4, "H-1"),
            TemplateSlot(34, 4, "W-1"),
            TemplateSlot(58, 4, "OFFY"),
            TemplateSlot(63, 4, "OFFX"),
        ),
        legacy_va=0x4E9920,
        param_va=0x4E9920,
        legacy_branches=(
            (18, "jcc8", 0x4E9946),
            (26, "jcc8", 0x4E9946),
            (48, "jcc8", 0x4E995F),
            (55, "jcc8", 0x4E995F),
            (61, "jcc8", 0x4E9961),
            (74, "call", 0x4024E0),
        ),
        param_branches=(
            (18, "jcc8", 0x4E9946),
            (26, "jcc8", 0x4E9946),
            (48, "jcc8", 0x4E9965),
            (55, "jcc8", 0x4E9965),
            (67, "jcc8", 0x4E9967),
            (80, "call", 0x4024E0),
        ),
    ),
    ("castle-ui-center-present", 0x11136F): CaveTemplate(
        template_hex=(
            "a1e00252006a006a0068df010000bac0d45100687f02000031c931db"
            "e89f68eeffff35e00252008b0424e81162eeff5a"
            "683c0000006850000000"
            "68df010000687f02000031c931dbb8c0d45100e86e68eeff"
            "b8d84c5400e92ea1f1ff" + "00" * 4
        ),
        slots=(TemplateSlot(49, 4, "OFFY"), TemplateSlot(54, 4, "OFFX")),
        legacy_va=0x51316F,
        param_va=_RELOCATED_CASTLE_PRESENT_VA,
        legacy_branches=(
            (28, "call", 0x4024E0),
            (42, "call", 0x401E60),
            (71, "call", 0x4024E0),
            (81, "jmp32", 0x435DAA),
        ),
        param_branches=(
            (28, "call", 0x4024E0),
            (42, "call", 0x401E60),
            (77, "call", 0x4024E0),
            (87, "jmp32", 0x435DAA),
        ),
        new_offset=_RELOCATED_CASTLE_PRESENT_OFFSET,
    ),
    ("castle-ui-center-present-wrapper", 0x11136F): CaveTemplate(
        template_hex=(
            "60e86a9ff1ff6160a1e00252006a006a0068df010000bac0d45100"
            "687f02000031c931dbe89768eeffff35e00252008b0424e80962eeff5a"
            "683c0000006850000000"
            "68df010000687f02000031c931dbb8c0d45100e86668eeff61c3"
            + "00" * 4
        ),
        slots=(TemplateSlot(57, 4, "OFFY"), TemplateSlot(62, 4, "OFFX")),
        legacy_va=0x51316F,
        param_va=_RELOCATED_CASTLE_PRESENT_VA,
        legacy_branches=(
            (1, "call", 0x435B90),
            (36, "call", 0x4024E0),
            (50, "call", 0x401E60),
            (79, "call", 0x4024E0),
        ),
        param_branches=(
            (1, "call", 0x435B90),
            (36, "call", 0x4024E0),
            (50, "call", 0x401E60),
            (85, "call", 0x4024E0),
        ),
        new_offset=_RELOCATED_CASTLE_PRESENT_OFFSET,
    ),
    ("castle-overview-center-present-wrapper", 0x1198D0): CaveTemplate(
        template_hex=(
            "60e84a69f0ff6160a1e00252006a006a0068df010000bac0d45100"
            "687f02000031c931dbe8e76deeffa1e002520085c07407"
            "66813820037428b8bc000000e8ed64f4ff85c0741a53"
            "bb58020000ba20030000e84986eeff5b85c07405a3e0025200"
            "ff35e00252008b0424e82167eeff5a"
            "683c0000006850000000"
            "68df010000687f02000031c931dbb8c0d45100e87e6deeff61c3"
            + "00" * 60
        ),
        slots=(
            TemplateSlot(53, 2, "W"),
            TemplateSlot(73, 4, "H"),
            TemplateSlot(78, 4, "W"),
            TemplateSlot(113, 4, "OFFY"),
            TemplateSlot(118, 4, "OFFX"),
        ),
        legacy_va=0x51B6D0,
        param_va=0x51B6D0,
        legacy_branches=(
            (1, "call", 0x422020),
            (36, "call", 0x4024E0),
            (48, "jcc8", 0x51B709),
            (55, "jcc8", 0x51B731),
            (62, "call", 0x461C00),
            (69, "jcc8", 0x51B731),
            (82, "call", 0x403D70),
            (90, "jcc8", 0x51B731),
            (106, "call", 0x401E60),
            (135, "call", 0x4024E0),
        ),
        param_branches=(
            (1, "call", 0x422020),
            (36, "call", 0x4024E0),
            (48, "jcc8", 0x51B709),
            (55, "jcc8", 0x51B731),
            (62, "call", 0x461C00),
            (69, "jcc8", 0x51B731),
            (82, "call", 0x403D70),
            (90, "jcc8", 0x51B731),
            (106, "call", 0x401E60),
            (141, "call", 0x4024E0),
        ),
    ),
    ("castle-overview-centered-input", 0x1199A0): CaveTemplate(
        template_hex=(
            "8b1d004d54008a0d2c5154008b15fc4c5400a330125100d3fb"
            "8bb8b8000000d3fa81ea5000000081eb3c000000ff5710e96f6df0ff"
            + "00" * 11
        ),
        slots=(TemplateSlot(35, 4, "OFFX"), TemplateSlot(41, 4, "OFFY")),
        legacy_va=0x51B7A0,
        param_va=0x51B7A0,
        legacy_branches=((42, "jmp32", 0x422544),),
        param_branches=((48, "jmp32", 0x422544),),
    ),
    ("right-bottom-action-native-center-wrapper", 0x1199E0): CaveTemplate(
        template_hex=(
            "6083ec08a1e0025200890424b8bc000000e80a64f4ff85c0"
            "0f847a000000bbe0010000ba80020000e86385eeff89442404"
            "a3e00252008b4424248b4c24208b54241c8b5c24188b6c2410"
            "8b74240c8b7c2408e889a3f1ff894424248b34248b7c2404"
            "8935e0025200683c0000006850000000"
            "68df010000687f02000031c931db89f289f8e8776ceeff"
            "b8d84c5400e82d56f4ff83c40861c383c40861e93fa3f1ff"
            + "00" * 31
        ),
        slots=(TemplateSlot(105, 4, "OFFY"), TemplateSlot(110, 4, "OFFX")),
        legacy_va=0x51B7E0,
        param_va=0x51B7E0,
        legacy_branches=(
            (17, "call", 0x461C00),
            (24, "jz32", 0x51B872),
            (40, "call", 0x403D70),
            (82, "call", 0x435BC0),
            (126, "call", 0x4024E0),
            (136, "call", 0x460EA0),
            (150, "jmp32", 0x435BC0),
        ),
        param_branches=(
            (17, "call", 0x461C00),
            (24, "jz32", 0x51B878),
            (40, "call", 0x403D70),
            (82, "call", 0x435BC0),
            (132, "call", 0x4024E0),
            (142, "call", 0x460EA0),
            (156, "jmp32", 0x435BC0),
        ),
    ),
    ("battle-ui-center-present-wrapper", 0x119C00): CaveTemplate(
        template_hex=(
            "833d48205300007506e89254f4ffc360a1e00252006a006a00"
            "68df010000bac0d45100687f02000031c931dbe8af6aeeff"
            "a1e0025200e82564eeff8b15e0025200"
            "683c0000006850000000"
            "68df010000687f02000031c931dbb8c0d45100e87d6aeeff"
            "61e83754f4ffc3" + "00" * 54
        ),
        slots=(TemplateSlot(66, 4, "OFFY"), TemplateSlot(71, 4, "OFFX")),
        legacy_va=0x51BA00,
        param_va=0x51BA00,
        legacy_branches=(
            (7, "jcc8", 0x51BA0F),
            (9, "call", 0x460EA0),
            (44, "call", 0x4024E0),
            (54, "call", 0x401E60),
            (88, "call", 0x4024E0),
            (94, "call", 0x460EA0),
        ),
        param_branches=(
            (7, "jcc8", 0x51BA0F),
            (9, "call", 0x460EA0),
            (44, "call", 0x4024E0),
            (54, "call", 0x401E60),
            (94, "call", 0x4024E0),
            (100, "call", 0x460EA0),
        ),
    ),
}

# Hook patches that must retarget when their cave relocates. Values are the
# parameterized new bytes (jmp/call rel32 or mov imm32 aimed at the relocated
# cave VA); at 800x600 the legacy hook bytes are used unchanged.
_CAVE_HOOKS: dict[tuple[str, int], str] = {
    ("castle-ui-center-present", 0x0351A5): "e9765e0e00",
    ("castle-ui-center-present-wrapper", 0x0351AA): "bb20bc5100",
    ("castle-ui-center-present-wrapper", 0x0351DE): "e83d5e0e00",
}

# Single-byte tile immediates keyed by (old_hex, new_hex). The formula choice
# comes from the patch notes' disassembly semantics, not the byte values:
#   07->09 map_height loops +7 -> TY        09->0c map_width loops +9 -> TX
#   06->08 full rows 6 -> TY-1              06->0c clipped-row columns -> TX
#   04->06 center-on-unit X 4 -> TX//2      03->04 center-on-unit Y 3 -> TY//2
#   f7->f4 map_width-9 -> -TX               f9->f7 map_height-7 -> -TY
#   f8->f6 area helper -8 -> -(TY+1)        f6->f3 area helper -10 -> -(TX+1)
# All these single-byte immediates are sign-extended by the CPU (83-group and
# push imm8 forms), so every slot is signed and the practical tile-count
# ceiling is 127.
_SINGLE_BYTE_TILE_FORMULAS: dict[tuple[str, str], tuple[str, bool]] = {
    ("07", "09"): ("TY", True),
    ("09", "0c"): ("TX", True),
    ("06", "08"): ("TY-1", True),
    ("06", "0c"): ("TX", True),
    ("04", "06"): ("TX//2", True),
    ("03", "04"): ("TY//2", True),
    ("f7", "f4"): ("-TX", True),
    ("f9", "f7"): ("-TY", True),
    ("f8", "f6"): ("-(TY+1)", True),
    ("f6", "f3"): ("-(TX+1)", True),
}


def _build_recipes() -> dict[tuple[str, int], Recipe]:
    recipes: dict[tuple[str, int], Recipe] = {}
    for key, formula in _VALUE_RECIPES.items():
        recipes[key] = Recipe("value", value=formula)
    for key in _FIXED_RECIPES:
        recipes[key] = Recipe("fixed")
    for key, slots in _SPLICE_RECIPES.items():
        recipes[key] = Recipe("splice", slots=slots)
    for key in _CAVE_TEMPLATES:
        recipes[key] = Recipe("cave-template")
    for key in _CAVE_HOOKS:
        recipes[key] = Recipe("cave-hook")

    for patch in PATCHES:
        key = (patch.group, patch.offset)
        if key in recipes:
            continue
        if patch.group == "menu-center-hitboxes":
            delta = int.from_bytes(patch.new, "little") - int.from_bytes(
                patch.old, "little"
            )
            if delta == PROFILE_800.off_x:
                recipes[key] = Recipe("old-plus", deltas=("OFFX",))
            elif delta == PROFILE_800.off_y:
                recipes[key] = Recipe("old-plus", deltas=("OFFY",))
            else:
                raise ResolutionError(
                    f"menu hitbox at 0x{patch.offset:06X} shifts by {delta}, "
                    "expected the 80/60 centering offset"
                )
        elif (
            patch.group == "right-bottom-action-descriptor-anchor"
            and len(patch.old) == 8
        ):
            recipes[key] = Recipe("old-plus", deltas=("SHIFTX", "SHIFTY"))
        elif (
            patch.group in ("main-loops", "full-redraw-12x9", "helpers")
            and len(patch.new) == 1
        ):
            pair = (patch.old_hex, patch.new_hex)
            if pair not in _SINGLE_BYTE_TILE_FORMULAS:
                raise ResolutionError(
                    f"{patch.group} at 0x{patch.offset:06X} has unmapped tile "
                    f"immediate {pair}"
                )
            formula, signed = _SINGLE_BYTE_TILE_FORMULAS[pair]
            recipes[key] = Recipe("value", value=formula, signed=signed)
    return recipes


RECIPES: dict[tuple[str, int], Recipe] = _build_recipes()

# Stages that can be generated for non-legacy resolutions: the stable stage
# plus its validation lanes. Everything else (isolation ladders, mouse
# diagnostics, legacy centering experiments) stays 800x600-only.
_STABLE_STAGE_PREFIX = DEFAULT_STAGE
PARAMETERIZED_STAGES: tuple[str, ...] = (
    _STABLE_STAGE_PREFIX,
    _STABLE_STAGE_PREFIX + "-rightbottomcompose",
    _STABLE_STAGE_PREFIX + "-rightbottomaction",
    _STABLE_STAGE_PREFIX + "-rightbottomaction-nativecenter",
    _STABLE_STAGE_PREFIX + "-rightbottomaction-nativecenter-no-castleinput",
    _STABLE_STAGE_PREFIX + "-unitselectactionbar",
    _STABLE_STAGE_PREFIX + "-unitselectactionbarpostredraw",
    _STABLE_STAGE_PREFIX + "-rightbottomcompose-unitselectactionbarpostredraw",
    _STABLE_STAGE_PREFIX + "-castlecenter",
    _STABLE_STAGE_PREFIX + "-castlecenter-hitbox",
    _STABLE_STAGE_PREFIX + "-castlecenter-all",
    _STABLE_STAGE_PREFIX + "-castlecenter-all-battlecenter",
    _STABLE_STAGE_PREFIX + "-castlecenter-all-battlecenter-inputprobe",
)
PARAMETERIZED_GROUPS: frozenset[str] = frozenset(
    group for stage in PARAMETERIZED_STAGES for group in STAGE_GROUPS[stage]
)


def _apply_value_recipe(
    patch: Patch, recipe: Recipe, profile: ResolutionProfile
) -> Patch:
    width = len(patch.new)
    formula = FORMULAS[recipe.value]
    context = f"{patch.group} @ 0x{patch.offset:06X} ({recipe.value})"
    expected_legacy = _encode_int(
        formula(PROFILE_800), width, recipe.signed, context
    )
    if expected_legacy != patch.new:
        raise ResolutionError(
            f"{context}: formula predicts legacy bytes "
            f"{expected_legacy.hex()} but table has {patch.new_hex}"
        )
    new = _encode_int(formula(profile), width, recipe.signed, context)
    return replace(patch, new_hex=new.hex())


def _apply_old_plus_recipe(
    patch: Patch, recipe: Recipe, profile: ResolutionProfile
) -> Patch:
    context = f"{patch.group} @ 0x{patch.offset:06X} (old-plus)"
    if len(patch.old) != 4 * len(recipe.deltas):
        raise ResolutionError(
            f"{context}: expected {len(recipe.deltas)} dword field(s)"
        )
    fields = []
    for index, delta_key in enumerate(recipe.deltas):
        formula = FORMULAS[delta_key]
        old_value = int.from_bytes(
            patch.old[index * 4 : index * 4 + 4], "little"
        )
        legacy_value = int.from_bytes(
            patch.new[index * 4 : index * 4 + 4], "little"
        )
        if old_value + formula(PROFILE_800) != legacy_value:
            raise ResolutionError(
                f"{context}: field {index} legacy delta is "
                f"{legacy_value - old_value}, formula {delta_key} predicts "
                f"{formula(PROFILE_800)}"
            )
        fields.append(
            _encode_int(old_value + formula(profile), 4, False, context)
        )
    return replace(patch, new_hex=b"".join(fields).hex())


def _apply_splice_recipe(
    patch: Patch, recipe: Recipe, profile: ResolutionProfile
) -> Patch:
    legacy = patch.new
    data = bytearray(legacy)
    for slot in recipe.slots:
        pattern = bytes.fromhex(slot.pattern)
        context = (
            f"{patch.group} @ 0x{patch.offset:06X} slot {slot.value} "
            f"({slot.pattern})"
        )
        legacy_value = int.from_bytes(
            pattern[slot.at : slot.at + slot.width], "little", signed=slot.signed
        )
        formula = FORMULAS[slot.value]
        if formula(PROFILE_800) != legacy_value:
            raise ResolutionError(
                f"{context}: pattern encodes {legacy_value} but formula "
                f"predicts {formula(PROFILE_800)} at 800x600"
            )
        positions = [
            index
            for index in range(len(legacy) - len(pattern) + 1)
            if legacy[index : index + len(pattern)] == pattern
        ]
        if len(positions) != slot.count:
            raise ResolutionError(
                f"{context}: found {len(positions)} occurrence(s), "
                f"expected {slot.count}"
            )
        encoded = _encode_int(formula(profile), slot.width, slot.signed, context)
        for position in positions:
            start = position + slot.at
            data[start : start + slot.width] = encoded
    return replace(patch, new_hex=bytes(data).hex())


def _apply_cave_template(
    patch: Patch, profile: ResolutionProfile
) -> Patch:
    template = _CAVE_TEMPLATES[(patch.group, patch.offset)]
    data = bytearray(bytes.fromhex(template.template_hex))
    for slot in template.slots:
        context = (
            f"{patch.group} @ 0x{patch.offset:06X} template slot {slot.value}"
        )
        formula = FORMULAS[slot.value]
        current = int.from_bytes(
            data[slot.at : slot.at + slot.width], "little", signed=slot.signed
        )
        if current != formula(PROFILE_800):
            raise ResolutionError(
                f"{context}: template carries {current}, formula predicts "
                f"{formula(PROFILE_800)} at 800x600"
            )
        data[slot.at : slot.at + slot.width] = _encode_int(
            formula(profile), slot.width, slot.signed, context
        )
    offset = template.new_offset if template.new_offset is not None else patch.offset
    return replace(
        patch,
        offset=offset,
        old_hex="00" * len(data),
        new_hex=bytes(data).hex(),
    )


def _apply_recipe(
    patch: Patch, recipe: Recipe, profile: ResolutionProfile
) -> Patch:
    if recipe.kind == "fixed":
        return patch
    if recipe.kind == "value":
        return _apply_value_recipe(patch, recipe, profile)
    if recipe.kind == "old-plus":
        return _apply_old_plus_recipe(patch, recipe, profile)
    if recipe.kind == "splice":
        return _apply_splice_recipe(patch, recipe, profile)
    if recipe.kind == "cave-template":
        if (profile.width, profile.height) == LEGACY_RESOLUTION:
            return patch
        return _apply_cave_template(patch, profile)
    if recipe.kind == "cave-hook":
        if (profile.width, profile.height) == LEGACY_RESOLUTION:
            return patch
        return replace(patch, new_hex=_CAVE_HOOKS[(patch.group, patch.offset)])
    raise ResolutionError(f"Unknown recipe kind: {recipe.kind}")


def generate_patches(profile: ResolutionProfile) -> tuple[Patch, ...]:
    """Generate the full patch table for a resolution (no legacy shortcut).

    Entries in non-parameterized groups are passed through verbatim; they are
    only reachable through legacy-only stages, which select_patches_for
    refuses for non-legacy resolutions.
    """
    generated: list[Patch] = []
    for patch in PATCHES:
        key = (patch.group, patch.offset)
        if patch.group not in PARAMETERIZED_GROUPS:
            generated.append(patch)
            continue
        recipe = RECIPES.get(key)
        if recipe is None:
            raise ResolutionError(
                f"No resolution recipe for {patch.group} @ 0x{patch.offset:06X}"
            )
        generated.append(_apply_recipe(patch, recipe, profile))
    return tuple(generated)


def build_patches(profile: ResolutionProfile) -> tuple[Patch, ...]:
    if (profile.width, profile.height) == LEGACY_RESOLUTION:
        return PATCHES
    return generate_patches(profile)


def select_patches_for(stage: str, profile: ResolutionProfile) -> list[Patch]:
    if (
        profile.width,
        profile.height,
    ) != LEGACY_RESOLUTION and stage not in PARAMETERIZED_STAGES:
        raise ResolutionNotSupportedError(
            f"Stage {stage!r} supports only the legacy 800x600 resolution; "
            "parameterized stages are the stable stage and its validation lanes."
        )
    groups = set(STAGE_GROUPS[stage])
    return [patch for patch in build_patches(profile) if patch.group in groups]


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
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbar adds a validation-only first-mission selected-unit text/morale action-panel copyback to the HD map surface; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw reruns that selected-unit panel after sub_40ADF0 full-redraw exits and expects the panel in the bottom strip; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose-unitselectactionbarpostredraw combines those validation lanes for first-mission black-patch inspection without changing the stable stage; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction moves the live 00515130 action descriptors by +160,+120 and widens their draw clip to 800 as a validation replacement for the bad copyback layout; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter runs the live action owner on a temporary native 640x480 surface, center-copies it to the HD map surface, and reuses centered castle/action input wrappers; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter-no-castleinput is a diagnostic comparison stage that keeps the native-center action wrapper but omits castle/action centered input wrappers; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter also recenters the native castle/barracks UI layer visually; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox additionally wraps castle/barracks polling, descriptor hit tests, and the barracks grid hit-test call with the matching -80,-60 mouse transform; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all is the current broad castle-interior validation target and uses a present-callback wrapper so stock castle/barracks rendering runs before the 80,60 centering copy, plus a native-render-first full-overview 00422020 visual wrapper and 00422520 hit-test wrapper; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter adds the battle initial-present wrapper after hidden CDB evidence proved the Unit_Attack route and native 640x480 battle frame; "
            "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe adds validation-only battle grid and descriptor hit-test mouse wrappers; "
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
        "--resolution",
        default="800x600",
        help=(
            "target resolution WxH; default 800x600 uses the frozen legacy "
            "patch table byte-for-byte. Other resolutions generate the table "
            "from resolution recipes and are limited to the stable stage and "
            "its validation lanes."
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

    try:
        profile = parse_resolution(args.resolution)
    except ResolutionError as exc:
        raise SystemExit(str(exc)) from exc
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

    try:
        patches = select_patches_for(args.stage, profile)
    except ResolutionError as exc:
        raise SystemExit(str(exc)) from exc
    validate_input(data, patches)
    patched = apply_patches(data, patches)
    output_path.write_bytes(patched)

    print(f"Wrote {output_path}")
    print(f"Stage: {args.stage}")
    print(f"Resolution: {profile.key}")
    print(f"Patches applied: {len(patches)}")
    print(f"Input SHA-256:  {actual_sha.upper()}")
    print(f"Output SHA-256: {sha256(patched).upper()}")


if __name__ == "__main__":
    main()

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
``--stage gameplay-menu640-centered-map12-novswitch-relinput`` is the current HD map
path when the wrapper is configured for windowed/application display mode: it
leaves the menu surface at 640x480, centers the 640x480 menu blit at 80,60 only
when the source is the dedicated menu surface, shifts the menu descriptor table
by the same amount, keeps the engine's native relative mouse path, expands the
adventure map drawing/scroll helpers to 12x9 tiles, and deliberately leaves the
later global cursor/view switch at 640x480 for menu safety.
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
    # Group A4: DirectInput wrappers can return absolute-style client coords
    # while this engine expects relative deltas. Store nonzero scaled absolute X/Y.
    Patch(
        "mouse-absolute-assign",
        0x05FE61,
        "a1a85154000faf42200142248b7220a1ac5154000fafc68b7a28c7422c0000000001c7897a28",
        "a1a851540085c07406c1e006894224a1ac51540085c07406c1e006894228c7422c0000000090",
        "0x460A50 assign nonzero absolute mouse X/Y instead of accumulating deltas",
    ),
    # Group B: grow map/DD viewport pixel bounds.
    Patch("input-bounds", 0x05F826, "7f020000", "1f030000", "0x460410 max X 639 -> 799"),
    Patch("input-bounds", 0x05F82D, "df010000", "57020000", "0x460410 max Y 479 -> 599"),
    Patch("viewport-init", 0x05F92D, "e0010000", "58020000", "0x460490 viewport bottom 480 -> 600"),
    Patch("viewport-init", 0x05F93B, "80020000", "20030000", "0x460490 viewport right 640 -> 800"),
    Patch("viewport-switch", 0x060212, "e0010000", "58020000", "0x460D80 viewport bottom 480 -> 600"),
    Patch("viewport-switch", 0x06021E, "80020000", "20030000", "0x460D80 viewport right 640 -> 800"),
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
    # Group D: scroll/click/center helpers. Apply after the first stage is proven.
    Patch("helpers", 0x007080, "09", "0c", "scroll clamp X +9 -> +12"),
    Patch("helpers", 0x007087, "f7", "f4", "scroll clamp map_width -9 -> -12"),
    Patch("helpers", 0x0070B4, "07", "09", "scroll clamp Y +7 -> +9"),
    Patch("helpers", 0x0070BB, "f9", "f7", "scroll clamp map_height -7 -> -9"),
    Patch("helpers", 0x00EF01, "04", "06", "center-on-unit X offset 4 -> 6"),
    Patch("helpers", 0x00EF18, "03", "04", "center-on-unit Y offset 3 -> 4"),
    Patch("helpers", 0x00EF4E, "09", "0c", "center-on-unit X +9 -> +12"),
    Patch("helpers", 0x00EF9D, "f7", "f4", "center-on-unit map_width -9 -> -12"),
    Patch("helpers", 0x00EF66, "07", "09", "center-on-unit Y +7 -> +9"),
    Patch("helpers", 0x00EF6D, "f9", "f7", "center-on-unit map_height -7 -> -9"),
    Patch("helpers", 0x017EA6, "09", "0c", "single-tile repaint X +9 -> +12"),
    Patch("helpers", 0x017EB3, "07", "09", "single-tile repaint Y +7 -> +9"),
    Patch("helpers", 0x017ECC, "06", "08", "single-tile repaint last visible row 6 -> 8"),
    Patch("helpers", 0x017EDB, "06", "09", "single-tile repaint last-row X cutoff 6 -> 9"),
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
)


VIEWPORT_GROUPS = ("input-bounds", "viewport-init", "viewport-switch")
MENU_SAFE_VIEWPORT_GROUPS = ("input-bounds", "viewport-init")


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
        default="gameplay-menu640-centered-map12-novswitch-relinput",
        help=(
            "patch stage: gameplay-menu640-centered-map12-novswitch-relinput=current recommended "
            "HD gameplay with centered 640x480 menu, native relative mouse input, "
            "12x9 redraw loops, map scroll/repaint helpers, and menu-safe viewport switch; "
            "display=render/window only; gameplay-menu640="
            "HD gameplay with native 640x480 menu/cursor switches; "
            "display-absinput=display only plus absolute mouse diagnostic; "
            "isolate-* stages add one suspicious group at a time; "
            "gameplay-menu640-centered centers the 640x480 menu-surface blit only; "
            "gameplay-menu640-centered-hitboxes/relinput also moves start-menu buttons; "
            "gameplay-menu640-centered-map12-relinput additionally expands the later viewport switch; "
            "gameplay-menu640-centered-map12-novswitch-relinput keeps that switch native; "
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

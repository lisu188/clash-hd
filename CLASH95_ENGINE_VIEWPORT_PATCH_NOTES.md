# Clash95 Engine Viewport Patch Notes

Goal: make `clash95.exe` render a larger gameplay coordinate view with the
smallest practical binary patch, closer to a Heroes3 HD-style engine patch than
to a scaler/wrapper.

This note targets the workspace copy of `clash95.exe`:

- SHA-256: `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`
- Image base: `0x00400000`
- `AUTO` section raw mapping: for code addresses in `AUTO`,
  `file_offset = VA - 0x400C00`

## Local Reverse Sources

Useful local material found in `C:\Clash`:

- `C:\Clash\clash95.c`: IDA-style decompilation for the Windows executable.
- `C:\Clash\clash95.asm`: full disassembly.
- `C:\Clash\clash95.map`: public symbols, including render/window functions.
- `C:\Clash\reverse\ghidra-out\functions.csv`: 3204 Ghidra functions.
- `C:\Clash\DATA\output`: extracted game data/assets.

There is also a local `clash-disassembly` checkout next to this workspace, but
its remote is Bitbucket:

`https://andrzej_lis3@bitbucket.org/andrzej_lis3/clash-disassembly.git`

That checkout contains a single older `clash.c` and is useful for historical
logic comparison. The Windows target should be driven from `C:\Clash\clash95.c`
and the map/Ghidra metadata.

## Core Finding

The engine has two separate resolution concepts that both matter:

1. Pixel buffers/mode/window: the DirectDraw main surface, software render
   surfaces, and the Win32 window.
2. Gameplay viewport in map tiles: the main adventure map assumes a 9 by 7 tile
   visible area, with mouse tile math based on `x = 32 + tile_x * 64` and
   `y = 16 + tile_y * 64`.

Changing only 640x480 to 800x600 will not make the game draw more map. Changing
only the 9x7 loops will overrun native-size surfaces. The smallest viable patch
changes both, but only for the main gameplay buffers and viewport code.

For a first experiment, use 800x600:

- Pixel size: 800 by 600.
- Tile viewport: 12 by 9.
- Max screen coords: 799 by 599.

This size is convenient because:

- `floor((800 - 32) / 64) = 12`
- `floor((600 - 16) / 64) = 9`

So it expands the native 9x7 view without immediately jumping to a large UI
rewrite.

## Important Functions

### Screen and surface setup

- `0x00404660` (`sub_404660`): constructs the main DirectDraw/render surface
  object at `unk_51D4C0`; hardcodes `640,480`.
- `0x00401A40` (`Render_LoadResourceBackbuffer`): initializes the default
  software render surface at `unk_51D9A0`; hardcodes `640,480`.
- `0x00461A20` (`Win_CreateMainWindow`): calls `CreateWindowExA` with
  width/height `640,480`.
- `0x0040AED0` and `0x00447DC0`-area functions allocate `dword_5202E0`, the
  main menu/gameplay software screen. This must grow too or expanded map draws
  can overrun the backing surface.

### DirectDraw mode

- `0x004046D0` (`Render_SetPixelFormat`) reads width/height from the render
  object at offsets `+0` and `+2`, then calls `0x00475080`.
- `0x00475080` calls `IDirectDraw2::SetDisplayMode` using those width/height
  fields.

This means the display mode follows the render object dimensions. Patch the
surface constructors rather than the `SetDisplayMode` call site.

### Map viewport object

- `0x00460410` initializes a map/DD viewport object with bounds `0,0,639,479`.
- `0x00460490` calls `sub_460B20(obj, 0, 640, 0, 480)`.
- `0x00460D80` re-applies `sub_460B20(obj, 0, 640, 0, 480)` when sprite/view
  metadata changes.
- `0x00460B20` converts the pixel viewport rectangle into internal scaled
  bounds.

The calls to `sub_460B20` are the cleanest place to make the visible pixel
viewport larger.

### Main adventure-map tile loops

- `0x00406FA0` is the main visible-map redraw/update loop. It repeatedly loops
  over `scroll_y + 7` and `scroll_x + 9`.
- `0x00407B90` is a mouse-drag scroll path. It clamps scroll X/Y using the 9x7
  visible dimensions.
- `0x0040FAD0`, `0x00418A90`, `0x00418C00`, and `0x00418CE0` are supporting
  center/repaint/visibility helpers that also encode 9x7.

These are the real "engine view" constants. They are more important than most
random `640` and `480` constants elsewhere in the executable.

## First 800x600 Patch Set

Do not overwrite the original executable. Create something like
`clash95_hdtest.exe` and patch that copy.

### A. Grow core render/window buffers

Patch little-endian 32-bit values:

| File offset | Function | Meaning | Old | New |
| --- | --- | --- | --- | --- |
| `0x003A64` | `0x00404660` | render object height | `480` | `600` |
| `0x003A69` | `0x00404660` | render object width | `640` | `800` |
| `0x000E4D` | `0x00401A40` | default surface height | `480` | `600` |
| `0x000E62` | `0x00401A40` | default surface width | `640` | `800` |
| `0x060EAD` | `0x00461A20` | window height | `480` | `600` |
| `0x060EB2` | `0x00461A20` | window width | `640` | `800` |
| `0x00A3BF` | `0x0040AED0` area | gameplay surface height | `480` | `600` |
| `0x00A3C4` | `0x0040AED0` area | gameplay surface width | `640` | `800` |
| `0x0471D7` | `0x00447DC0` area | menu/game surface height | `480` | `600` |
| `0x0471DC` | `0x00447DC0` area | menu/game surface width | `640` | `800` |

Expected bytes:

- `480`: `E0 01 00 00`
- `600`: `58 02 00 00`
- `640`: `80 02 00 00`
- `800`: `20 03 00 00`

### B. Grow viewport pixel bounds

Patch little-endian 32-bit values:

| File offset | Function | Meaning | Old | New |
| --- | --- | --- | --- | --- |
| `0x05F826` | `0x00460410` | max X | `639` | `799` |
| `0x05F82D` | `0x00460410` | max Y | `479` | `599` |
| `0x05F92D` | `0x00460490` | viewport bottom | `480` | `600` |
| `0x05F93B` | `0x00460490` | viewport right | `640` | `800` |
| `0x060212` | `0x00460D80` | viewport bottom | `480` | `600` |
| `0x06021E` | `0x00460D80` | viewport right | `640` | `800` |

Expected bytes:

- `639`: `7F 02 00 00`
- `799`: `1F 03 00 00`
- `479`: `DF 01 00 00`
- `599`: `57 02 00 00`

### C. Grow main visible tile loops from 9x7 to 12x9

Patch single-byte immediates in `0x00406FA0`:

Y loop limits, `+7` to `+9`:

- `0x0063E9`: `07` -> `09`
- `0x0066F7`: `07` -> `09`
- `0x006814`: `07` -> `09`
- `0x0068E1`: `07` -> `09`
- `0x0069A9`: `07` -> `09`
- `0x006A93`: `07` -> `09`
- `0x006B9F`: `07` -> `09`

X loop limits, `+9` to `+12`:

- `0x006423`: `09` -> `0C`
- `0x00674B`: `09` -> `0C`
- `0x00683A`: `09` -> `0C`
- `0x006907`: `09` -> `0C`
- `0x0069CF`: `09` -> `0C`
- `0x006AC1`: `09` -> `0C`
- `0x006BEF`: `09` -> `0C`

### D. Grow scroll clamp and center helpers

Minimum scroll-drag clamp in `0x00407B90`:

- `0x007080`: `09` -> `0C` (`scroll_x + 9` -> `scroll_x + 12`)
- `0x007087`: `F7` -> `F4` (`map_width - 9` -> `map_width - 12`)
- `0x0070B4`: `07` -> `09` (`scroll_y + 7` -> `scroll_y + 9`)
- `0x0070BB`: `F9` -> `F7` (`map_height - 7` -> `map_height - 9`)

Center-on-unit helper in `0x0040FAD0`:

- `0x00EF01`: `04` -> `06` (center X offset)
- `0x00EF18`: `03` -> `04` (center Y offset)
- `0x00EF4E`: `09` -> `0C`
- `0x00EF9D`: `F7` -> `F4`
- `0x00EF66`: `07` -> `09`
- `0x00EF6D`: `F9` -> `F7`

Single-tile repaint visibility in `0x00418A90`:

- `0x017EA6`: `09` -> `0C`
- `0x017EB3`: `07` -> `09`
- `0x017ECC`: `06` -> `08` (last visible row)
- `0x017EDB`: `06` -> `09` (last-row X cutoff, derived as `visible_x - 3`)
- `0x017EEC`: `06` -> `08`

Area/center helpers:

- `0x018009`: `09` -> `0C`
- `0x018016`: `07` -> `09`
- `0x018067`: `09` -> `0C`
- `0x018080`: `07` -> `09`
- `0x018087`: `F8` -> `F6`
- `0x0180C2`: `F6` -> `F3`
- `0x018112`: `09` -> `0C`
- `0x01812A`: `07` -> `09`
- `0x018131`: `F8` -> `F6`
- `0x018163`: `F6` -> `F3`

This group is the riskiest part of the small patch because some helper logic
encodes clipped bottom-row behavior, not just a rectangular viewport. Patch it
after verifying that A-C boots and draws without memory corruption.

## What Not To Patch Initially

Do not globally replace every `640`, `480`, `639`, or `479`.

Many constants belong to fixed 640x480 menus, videos, campaign screens, palette
conversion buffers, modal windows, or redraw rectangles. Leaving them alone is
what keeps the patch small. The first goal is expanded adventure-map view with
old UI content drawn in its old coordinates, not a fully re-laid-out UI.

Examples to leave alone at first:

- Full-screen menu fill rects like `0x27F,0x1DF`.
- AVI/campaign/misinfo temporary 640x480 surfaces.
- Mouse/menu hit boxes tied to fixed UI art.
- Castle/battle screen constants until those modes are targeted separately.

## Expected First-Test Behavior

Best case:

- Game opens in 800x600.
- Menus remain mostly top-left/native-layout.
- Main adventure map draws 12 by 9 tiles.
- Extra right/bottom area shows more map, while old UI elements stay in their
  original 640x480 positions.

Likely issues:

- Some dirty rectangles still update only 640x480.
- Some top/bottom menu hit tests still assume old coordinates.
- Bottom-row tile click behavior may be off until helper group D is tuned.
- Save/campaign/castle screens may show unfilled extra area.

## 2026-04-22 Menu/Input Split

The broad `draw` stage resized the shared/default and menu/game surfaces and
produced stripey menu graphics. The safer `gameplay` stage avoids those shared
surface changes and confirms the engine can create an 800x600 window and
DirectDraw mode, but menu/native UI still sits in the old 640x480 coordinate
space.

The mouse/cursor setup has three separate patch levers:

- `input-bounds`: `0x460410` initial raw clamp max X/Y.
- `viewport-init`: `0x460490` initial active viewport call.
- `viewport-switch`: `0x460D80` later active cursor/view changes.

`patch_clash95_hd.py --stage gameplay-menu640` keeps `input-bounds` and
`viewport-init` at 800x600, but leaves `viewport-switch` at 640x480. This is a
diagnostic build for the current symptom where the menu/native UI and mouse are
not aligned. If that restores menu input, the final small patch should make
`0x460D80` conditional: 640x480 for native menus and 800x600 only for gameplay
map cursor modes.

`patch_clash95_hd.py --stage gameplay-menu640-centered` now rewrites
`sub_401E30` in place so only the dedicated menu surface pointer
`dword_5202E0` is blitted at `(80,60)` inside the 800x600 display. Other
640x480 fullscreen blits keep their native `(0,0)` destination, which avoids
shifting the startup AVI/movie path and other fixed-size screens.

`patch_clash95_hd.py --stage gameplay-menu640-centered-hitboxes` keeps that
menu-only centered blit and also shifts the PlayGame start-menu descriptor x/y
fields by `+80,+60`. These 53-byte descriptors feed both `sub_419D80` drawing
and `sub_419DC0` hit testing, so this is the smallest diagnostic patch for the
"centered menu art but dead mouse" symptom. It intentionally leaves `0x460D80`
at the original 640x480 menu cursor switch.

The mouse probe showed DirectInput reaching the game: button bytes toggle, but
the X/Y state can arrive as large absolute-style values while `sub_460A50`
integrates them as relative deltas. That pins the cursor at the clamp maximum,
for example `610,452` in the centered menu. The
`gameplay-menu640-centered-mousefix` stage keeps the centered/hitbox patches and
changes the mouse DirectInput data format from absolute/axis-mask to relative
axes (`0x4E93F0` and X/Y/Z object descriptors at `0x4E9130`).

Changing the DirectInput format alone did not alter the values returned by the
old fullscreen wrapper/OS path. The `gameplay-menu640-centered-absinput` stage
patches `sub_460A50` directly: nonzero mouse X/Y samples are shifted by 6 and
assigned to the cursor position instead of being multiplied by mouse speed and
added as deltas. With the wrapper now set to windowed/application display mode,
that absolute-coordinate diagnostic can snap the cursor toward the top-left
corner, so it is no longer the recommended build.

The current stable menu/input stage is `gameplay-menu640-centered-hitboxes`
(alias `gameplay-menu640-centered-relinput`): it keeps the menu-only centered
blit and shifted menu descriptors, but restores the engine's native relative
mouse updater.

## 2026-04-22 Map 12x9 Stage

`gameplay-menu640-centered-map12-novswitch-relinput` is the next HD map build.
It keeps the centered 640x480 menu and relative mouse path, then enables the
12x9 map drawing/helper patch set without changing the later global
`sub_460D80` viewport switch:

- `main-loops`: the primary adventure-map redraw loops cover `scroll_x + 12`
  and `scroll_y + 9`.
- `helpers`: scroll clamp, center-on-unit, single-tile repaint, and area/center
  helper constants are moved from the old 9x7 assumptions to the 12x9 viewport.

The `gameplay-menu640-centered-map12-relinput` stage also changes
`viewport-switch` so later `sub_460D80` cursor/view resets use 800x600 instead
of falling back to 640x480. That broke mouse behavior during menu testing, so
it is now a diagnostic build only until the switch can be made conditional for
gameplay views.

This is the build to test by entering a map, scrolling, centering on a unit,
and clicking/selecting tiles near the new right and bottom edges.

Built/deployed test binaries:

- Stage: `gameplay-menu640-centered-map12-relinput`
- Output SHA-256:
  `613584D50525691D9CFE55BEC598487B8672ECE159855C192C9CBB664C16DE97`
- Diagnostic path:
  - `C:\Clash\clash95_hdmap12_full_vswitch_diag.exe`
- Stage: `gameplay-menu640-centered-map12-novswitch-relinput`
- Output SHA-256:
  `C246A71A87003B0BDCC7EB997DBE1A5A97E08CC3AA8349DE00A528321EBBD757`
- Deployed paths:
  - `C:\Clash\clash95_hdmap12_novswitch_relinput.exe`
  - `C:\Clash\clash95_hdmap12_relinput.exe`
  - `C:\Clash\clash95_hdmenu_centered.exe`
- Fallback without helper/viewport-switch patches:
  `C:\Clash\clash95_hdmenu_centered_relinput_nohelpers.exe`

Startup/menu checks passed:

- `test_clash_menu_click.ps1` saw an 800x600 client area and captured the
  centered menu from the map12 build.
- `run_cdb_menu_probe.ps1` with `clash95_hd_crash_probe.cdb` survived a
  20-second no-skip intro/movie run using the real `C:\Clash\DDRAW.dll`
  wrapper, with no second-chance crash logged.
- After manual testing showed mouse failure in the full viewport-switch build,
  `clash95_hdmenu_centered.exe` was redeployed as the no-switch map12 build.
  The follow-up harness run at `captures\clicktest-20260422-151033` again saw
  an 800x600 client and captured the centered menu.

## 2026-04-22 Automated Frame/Click Harness

`test_clash_menu_click.ps1` launches a patched exe from `C:\Clash`, kills stale
`clash95*`/`cdb` processes before each case, skips the startup AVI/story path,
dumps before/after PNGs, tries menu clicks, writes `results.json` and
`results.csv`, and kills the test process at the end. With `C:\Clash\dxcfg.ini`
set to windowed/application display mode, the wrapper now exposes an 800x600
client area, so the harness can capture the logical HD surface directly.

The startup sequence is not reliably skipped by mouse alone in automation.
The AVI callback checks `Input_IsAnyKeyPressed`, and the later wait checks
Esc/Space/Enter, so the harness now sends Space pulses plus neutral center
mouse clicks before taking the menu frame.

Current automated mouse clicks are useful for driving the OS cursor but are not
accepted by the DirectInput menu path: after synthetic `SendInput` or
`PostMessage` clicks, the in-game cursor remains on the pre-click position and
the menu frame is unchanged. For automated input validation, use CDB/memory
injection or a lower-level HID-style clicker; do not treat PowerShell
`SendInput` menu-click failures as proof that manual mouse input is broken.

Clean frame dumps from `captures\clicktest-20260422-125357` show:

- `display-absinput`, `isolate-inputbounds-absinput`,
  `isolate-viewportcall-absinput`, `isolate-main-loops-absinput`,
  `isolate-surface-absinput`, and `hdmenu-absinput` render the same shifted menu
  frame, aside from cursor position/hash noise.
- `display-centered-visual-absinput` and `hdcentered-visual-absinput` share a
  different frame with duplicated/misaligned menu button blits because only the
  640x480 blit moved; the descriptor table stayed in native menu coordinates.
- `gameplay-menu640-centered-absinput` pairs the 80,60 blit shift with the
  `menu-center-hitboxes` descriptor shift. The frame captured in
  `captures\clicktest-20260422-135410` shows the original 640x480 menu art
  centered inside the 800x600 surface while keeping the menu surface itself at
  640x480.
- Growing the menu surface to 800x600 (`menu-surface` on the main menu path)
  causes the stripey/corrupt menu frame seen in
  `captures\clicktest-20260422-131211`, so that experiment is retired.
- The old broad two-byte `center-blit` experiment affected startup AVI/movie
  blits and could crash in `PlayAviStretch`. The current centered-menu stages
  use the in-place `menu-only-center-blit` guard instead, and a no-skip CDB run
  survived the startup movie/menu sequence for 20 seconds without a
  second-chance AV.

## Recommended Workflow

1. Build a small patcher that validates original bytes before changing them.
2. Emit `clash95_hdtest.exe`; never patch `clash95.exe` in place.
3. Apply patch groups A and B, boot-test.
4. Apply group C, enter a map and verify drawing.
5. Apply group D gradually while testing scroll, center-on-unit, click/select,
   and partial tile redraw.
6. Only after 800x600 works, repeat the same logic for 1024x768:
   - viewport width: 15 tiles
   - viewport height: 11 tiles
   - max coords: 1023 by 767

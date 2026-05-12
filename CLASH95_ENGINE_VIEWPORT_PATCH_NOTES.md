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
- `0x017EDB`: `06` -> `0C` (last-row X cutoff, aligned with the 12-column
  HD bottom row)
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

Harness update on 2026-04-22: `test_clash_menu_click.ps1` now reacquires the
visible top-level window by process id when `MainWindowHandle` becomes null or
zero. A fresh `gameplay-menu640-centered-map12-novswitch-relinput` candidate at
`C:\Clash\clash95_hd_harnesscheck_20260422.exe` produced three full-client
800x600 captures in `captures\clicktest-20260422-163904` with no null-handle
errors. In that run, `centered-exit` changed 15.68% of sampled pixels and
passed, while `shifted-exit` and `native-exit` changed 0% and failed without
harness errors. Treat centered-menu click coordinates as the current automation
target and use geometry/CDB evidence for the remaining mouse fidelity work.

`tools/capture_geometry.py` adds exact full-frame diff and bounds analysis. Its
first report for `captures\clicktest-20260422-163904` warns that all three
frames are full-frame nonblack and that the only passing `centered-exit` case
has a unique before-frame hash. That can happen if the intro/menu state was not
identical across cases, so the next harness improvement is a menu-readiness or
frame-stability gate before result clicks.

The readiness gate is now in `test_clash_menu_click.ps1`. The validation run at
`captures\clicktest-20260422-182440` reached stable, menu-ready 800x600 frames
for centered, shifted, and native exit clicks. All three clicks were attempted,
but all three produced 0% post-click frame change with matching before/after
hashes. This removes the earlier intro/menu-readiness false-positive and points
back to the input path: synthetic `SendInput` is not enough proof of manual
DirectInput behavior, so the next evidence should come from CDB mouse-state
probes.

CDB mouse-state evidence from
`C:\Clash\hd-cdb-harnesscheck-mouse-state-20260422.log` shows input is reaching
`sub_460A50`: 416 `MOUSE` rows, nonzero button states, and changing `dx/dy`.
The bad pattern is coordinate integration. The run saw `dx` up to 2220, `dy`
up to 1509, displayed cursor positions up to `1303,923`, final max bounds
`610,452`, and 373 rows already beyond max before clamp. This means the game is
receiving movement and buttons, but the cursor is overdriven into the active
menu clamp. The next proof should combine the `MOUSE` breakpoint with
`MENUHIT` at `0x00419B80` in one run to show which menu descriptors are tested
when the cursor/button state changes.

Combined CDB evidence from
`C:\Clash\hd-cdb-harnesscheck-mouse-menu-sample-20260422.log`, summarized at
`captures\mousemenuprobe-20260422-sample-summary.json`, confirms that the menu
descriptor scan runs but receives a pinned logical cursor. The run parsed 246
`MOUSE` rows and 598 sampled `MENUHIT` rows. The HD candidate still produced
overlarge movement (`x` max 12165, `y` max 6801, `dx` max 28211, `dy` max
19077), then the menu hit-test state was clamped to `610,452` for every
sampled descriptor. The six repeated descriptor origins were `(239,196)`,
`(232,228)`, `(265,264)`, `(437,196)`, `(424,228)`, and `(468,264)`, with no
synthetic sweep-click button state observed. This points to bad mouse
coordinate integration before hit testing, not missing menu descriptors or
misplaced menu art.

## 2026-04-22 Python Mouse Mapping Evidence

`tools/mouse_path_probe.py` maps the automation side of the problem: requested
client point, requested screen point, actual `GetCursorPos`, actual
`ScreenToClient`, and click down/up phases. The 2026-04-22 standalone run at
`captures\mouseclickmap-20260422-absquarter-sendinput-v2.json` verified that
the Python forced-click path is exact for the abs-quarter candidate:
`max_abs_error=0`, `max_sample_abs_error=0`, `path_verified=true`, and
`click_path_verified=true`.

`run_cdb_python_mouse_map.ps1` runs that same path while CDB logs internal
`MOUSE` and `MENUHIT` rows. The run at
`captures\cdb-python-mouse-map-20260422.log`, summarized in
`captures\mousemenuprobe-20260422-cdb-python-map-summary.json`, changes the
mouse hypothesis:

- Held `SendInput` clicks are visible to the engine when held long enough:
  `button_rows=20`, `left_button_rows=20`, and `menuhit_button_rows=10`.
- The coordinate path is still wrong. Python actual screen `(1119,603)` and
  client `(239,196)` produced DirectInput sample `(280,151)` and game logical
  `(70,37)`.
- The DirectInput sample matches quartered screen coordinates, not client
  coordinates: `(1119,603) / 4 ~= (280,151)`.
- Therefore `gameplay-menu640-centered-map12-absquarter` is a useful
  diagnostic but not a fix. It effectively maps `screen / 16` into the game.

Next patch direction: find a reliable runtime client origin or use a Win32
client-coordinate path. The desired transform for this wrapper/device behavior
is roughly `client = (directinput_sample * 4) - client_origin_screen`, then
store that value in the engine's shifted raw cursor fields. Do not hard-code
the observed origin `(880,407)` except in an explicitly temporary diagnostic.

## 2026-04-22 DDraw Geometry And Screen-Origin Diagnostic

The Win32 geometry trace proved the local DirectDraw wrapper already knows the
client rectangle and screen origin. `clash95_win32_geometry_entry_probe.cdb`
logged `USER32!GetClientRect` and `USER32!ClientToScreen` entry callers in
`captures\win32-geometry-entry-probe-20260422.log`. The useful wrapper callers
were:

- `1803fdc4`: after `GetClientRect`;
- `1803fdd2` and `1803fdda`: after two `ClientToScreen` calls for origin and
  bottom-right;
- `1801c4e5` and `1801c4f3`: a second wrapper path for the same origin and
  bottom-right points.

`clash95_ddraw_geometry_callsite_probe.cdb` then broke at those wrapper return
sites and wrote `captures\ddraw-geometry-callsite-probe-20260422.log`. It
recorded:

- `DDRAW_RECT rect=(0,0,800,600) size=(800,600)`;
- `DDRAW_ORIGIN_A pt=(880,407)`;
- `DDRAW_BOTTOMRIGHT_A pt=(1680,1007) span=(800,600)`;
- the second path reported the same origin and bottom-right.

`captures\win32-geometry-ddraw-disasm-20260422.log` records the DDraw call-site
disassembly. The wrapper reads related globals at `18162a34`, `18162a44`, and
`18440e80`, but the current patch workspace should not assume those addresses
are portable across wrapper versions.

To prove the math, `patch_clash95_hd.py` now has diagnostic stage
`gameplay-menu640-centered-map12-screenorigin`. It patches `sub_460A50` to
write:

`raw = ((DirectInputSample * 4) - tracedClientOrigin) << 6`

with zero DirectInput samples skipped. The stage hard-codes `(880,407)` and is
not shippable. Its purpose is to prove that the current wrapper/device supplies
quartered screen coordinates.

Built candidates:

- `C:\Clash\clash95_hd_mouseorigin_20260422.exe`, SHA-256
  `D4894C339D584A2F542FC06169267F136129D40CFB18527E04A364180A1D4EC8`; proved
  the transform, but zero samples mapped to `(-880,-407)`.
- `C:\Clash\clash95_hd_mouseorigin_skip0_20260422.exe`, SHA-256
  `ABBBEF097E1A61E353E064AFFBC893D3576C774506B7A01404D90B5746E39D60`; skips
  zero samples and is the current best coordinate-proof candidate.

Validation summary from
`captures\mousemenuprobe-20260422-mouseorigin-skip0-summary.json`:

- `mouse_rows=18`, `menuhit_rows=9`;
- `button_rows=8`, `menuhit_button_rows=4`;
- `preclamp_over_bounds=0`, `menuhit_over_bounds=0`;
- Python client `(239,196)` mapped to CDB `MOUSE x=240 y=197`;
- Python client `(468,264)` mapped to CDB `MOUSE x=468 y=265`.

Conclusion: the root mouse bug is confirmed as missing screen-origin removal.
The next stable path is to replace the hard-coded origin with a dynamic source:
either hook/use the wrapper's existing HWND/client geometry, store client
coordinates from window messages, or implement the mouse transform in a local
DirectDraw/input wrapper where the client origin is naturally available.

## 2026-04-22 Dynamic-Origin Mouse Patch

The original executable already has the pieces needed for a small dynamic
mouse-origin patch:

- `CreateWindowExA` stores the game HWND at `0x005452DC` (`mov [005452dc],eax`
  at `0x00461ACE`).
- The executable imports `USER32!ClientToScreen` through IAT `0x004EA3E0`.
- `clash95_hwnd_origin_probe.cdb` confirmed that `0x005452DC` equals the HWND
  used by the local `DDRAW.dll` wrapper when the wrapper reports the `800x600`
  client origin.

`patch_clash95_hd.py --stage gameplay-menu640-centered-map12-dynorigin` now
replaces the hard-coded screen-origin diagnostic with a code cave at
`0x004E9810`. The cave builds `POINT{0,0}` on the stack, calls
`ClientToScreen([0x005452DC], &point)`, computes:

`raw = ((DirectInputSample * 4) - clientOrigin) << 6`

and stores it into the engine mouse raw fields only when the transformed value
is within the current active max bound. Zero samples and out-of-bounds startup
samples are skipped so transient DirectInput/wrapper noise does not pin the
cursor before the menu is ready.

Built candidates:

- `C:\Clash\clash95_hd_mousedynorigin_20260422.exe`, SHA-256
  `C4EE2D3E66AFCBD6067694201FA38E95B4EAE91B7359A3AF96D7302FB2A20B0F`;
  dynamic-origin proof without transformed-bound guarding.
- `C:\Clash\clash95_hd_mousedynorigin_boundguard_20260422.exe`, SHA-256
  `E1725A5FCB4E2BA8E7700914FE5F9312670831D3097E92A8CE41F4110D5FC7CF`;
  current best mouse candidate.

Validation:

- `captures\hwnd-origin-probe-createhwnd-20260422.log` confirmed
  `hWnd_create=wrapperHwnd=00800cf0` and origin `(880,407)` in the same run.
- `captures\mousemenuprobe-20260422-dynorigin-boundguard-summary.json`:
  `mouse_rows=40`, `menuhit_rows=21`, `x=0..468`, `y=0..285`,
  `button_rows=19`, `menuhit_button_rows=10`, `preclamp_over_bounds=0`, and
  `menuhit_over_bounds=0`.
- `captures\mouseclickmap-cdb-python-dynorigin-boundguard-20260422.json`
  recorded exact Python cursor placement with `path_verified=true` and
  `click_path_verified=true`.

Remaining caveat: `test_clash_menu_click.ps1` with held SendInput still did not
exit from the centered-exit point in a non-CDB frame run. Because CDB proves
the internal cursor/button path is now aligned, treat that as a click-target,
menu-flow, or harness-cadence question rather than evidence that the coordinate
transform is still broken.

## 2026-04-22 HD Map Patch-Stage Report

`tools/patch_stage_report.py` now provides a deterministic static check for
candidate executables. It imports the patch definitions from
`patch_clash95_hd.py`, parses the PE section table for RVA/VA reporting, and
reports whether each selected stage byte is still original, patched, or
unexpected.

Validation command:

`C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\patch_stage_report.py --exe C:\Clash\clash95_hd_mousedynorigin_boundguard_20260422.exe --stage gameplay-menu640-centered-map12-dynorigin --write-json captures\patch-stage-dynorigin-boundguard-20260422.json`

Result for the current best candidate:

- SHA-256:
  `E1725A5FCB4E2BA8E7700914FE5F9312670831D3097E92A8CE41F4110D5FC7CF`.
- Selected stage bytes: `92/92` patched, `0` original, `0` unexpected.
- Map loops: `main-loops` `14/14` patched, which means the selected redraw
  constants target `12x9` visible tiles instead of native `9x7`.
- Map helpers: `helpers` `25/25` patched for scroll clamp, center-on-unit,
  single-tile repaint, and area/center helper constants.
- Pixel viewport setup: `input-bounds` `2/2` and `viewport-init` `2/2` are
  patched for 800x600.
- `viewport-switch` remains unpatched by design in this stage. It is still the
  menu-safe route until runtime evidence proves a conditional gameplay-only
  switch is needed.

This proves the byte layer only. The next HD-map proof still needs runtime
evidence from an entered gameplay map: `sub_406FA0` redraw hits, scroll globals,
tile bounds, and a first adventure-map capture.

## 2026-04-22 Runtime Map Probe And Initial Scroll Gap

The runtime map probe entered gameplay for the current dynamic-origin candidate
and proved the 12x9 redraw path is active, but it also exposed a separate
initial-scroll clamp gap.

Evidence:

- Candidate:
  `C:\Clash\clash95_hd_mousedynorigin_boundguard_20260422.exe`,
  SHA-256 `E1725A5FCB4E2BA8E7700914FE5F9312670831D3097E92A8CE41F4110D5FC7CF`.
- Probe log:
  `captures\cdb-map-runtime-loadslot0-v2-20260422.log`.
- Summary:
  `captures\map-runtime-loadslot0-v2-summary-20260422.json`.
- Runtime state:
  `PLAYGAME gd=035d0030 map=(50,50) scroll=(39,42) player=0 selected=-1
  mission=1 turn=34`.
- Redraw evidence:
  64 `MAP_REDRAW` rows and 64 `MAP_REPAINT` rows were logged.
- Tile-bound evidence:
  the 12x9 viewport makes the first redraw end at `(51,51)`, while the native
  9x7 end would be `(48,49)`.
- Analyzer result:
  `edge_overrun_rows=64`, expected max scroll `(38,41)`, overrun `(1,1)`.
- Crash:
  CDB recorded a second-chance AV at `00403582`
  (`repne movs dword ptr es:[edi],dword ptr [esi]`) after the redraw/repaint
  rows.

The key lesson is that expanding redraw loops and movement clamps is not enough
for saved games or restored player turns. `PlayGame` restores per-player scroll
from saved player data at `0040B748` and `0040B764`; that value can be valid
for native 9x7 and invalid for 12x9. The next patch should first be proven as a
CDB-time clamp immediately after that restore:

- `scroll_x = min(scroll_x, max(0, map_width - 12))`
- `scroll_y = min(scroll_y, max(0, map_height - 9))`

Only after this debugger-time proof should the patcher add a permanent
code-cave or byte patch for initial scroll restoration.

## 2026-04-22 Clamp Proof And Remaining Copy Crash

The debugger-time scroll clamp was proven, but it did not eliminate the map
crash.

Clamp evidence:

- `captures\map-runtime-clamp-loadslot0-summary-20260422.json`
- `SCROLL_RESTORE before=(39,42) max=(38,41) map=(50,50)`
- `SCROLL_RESTORE_CLAMP after=(38,41)`
- First redraw after clamp:
  `scroll=(38,41)`, `end12=(50,50)`, native `end9=(47,48)`
- `edge_overrun_rows=0`

Crash evidence after clamp:

- `captures\map-runtime-clamp-crash-loadslot0-summary-20260422.json`
- `ExceptionAddress: 00403582 (clash95+0x00003582)`
- write address `0b3cc1d0`
- faulting instruction:
  `repne movs dword ptr es:[edi],dword ptr [esi]`
- surrounding helper:
  `Render_BlendSurfaceRect`

This means the initial scroll clamp is necessary but not sufficient. The
remaining crash appears after in-bounds 12x9 redraws and lands in a 64-byte
copy into a render surface. The write address is just past a 640x480-sized
region, which points to a remaining native-sized blit/scratch/clip extent or a
surface-object mismatch.

Diagnostic stage:

- `gameplay-menu640-centered-map12-dynorigin-sharedscratch`
- Adds `shared-surface` to the dynamic-origin stage.
- Leaves `menu-surface` native to avoid the known stripey main menu path.
- Built candidate:
  `C:\Clash\clash95_hd_mousedynorigin_sharedscratch_20260422.exe`
- SHA-256:
  `D2EC22AAE227A432FAA32EFFBA2A254B167F5775D274A1FA4B240F35D5FE7951`
- Static report:
  `captures\patch-stage-dynorigin-sharedscratch-20260422.json` with `94/94`
  selected bytes patched.

Sharedscratch runtime result:

- `captures\map-runtime-sharedscratch-clamp-crash-loadslot0-summary-20260422.json`
- `edge_overrun_rows=0`
- `ExceptionAddress: 00403582`
- write address `0b3bc1d0`

Conclusion: growing `unk_51D4C0`/the default scratch surface alone is not the
remaining fix. The next useful evidence is a copy-extent probe at `0040357A`
and `00403582` that logs destination pointer, source pointer, copy length, the
surface object in `[ebp+5A]`, the source pointer in `[ebp-5A]`, and the last
successful copy chunks before the AV.

### Copy-Extent Probe Results, 2026-04-22

Debugger overhead matters here. A CDB breakpoint at `00403582` still traps even
when the command body is gated by a pseudo-register, so copy breakpoints must be
disabled until the first `MAP_REDRAW` and enabled from that breakpoint with
`be`.

Evidence:

- `captures\map-copy-extent-sharedscratch-skipclick-loadslot0-summary-20260422.json`
  reached `PLAYGAME` and the CDB-time scroll clamp, but copy logging armed at
  scroll restore filled its 512-row budget before map redraw.
- `captures\map-redraw-copy-extent-sharedscratch-loadslot0-summary-20260422.json`
  reached `MAP_REDRAW seq=0`, `scroll=(38,41)`, `end12=(50,50)`,
  `edge_overrun_rows=0`, and captured 768 redraw-copy rows.
- The redraw-gated copy aggregate was a single render object/vtable
  (`objvt=0050ed94`) with exec rows in destination range
  `0b2449d0..0b24bfcc`; most sampled exec copies were 64 bytes.
- `captures\map-copy-sampler-enabled-sharedscratch-loadslot0-summary-20260422.json`
  used a disabled-until-redraw sampler, reached 4 redraws, 12 repaint rows, and
  sampled copy counts through `seq=45056` without a crash in the 20-second run.

Interpretation:

- The map edge overrun is no longer the observed blocker once the scroll is
  clamped to `(38,41)`.
- The first map redraw copies are lower in the heap than the earlier crash write
  near `0b3bc1d0`, so the fault likely occurs in a later copy phase or a
  different destination allocation/clip extent.
- Next useful probes should avoid hot software breakpoints until the relevant
  phase, then either sample longer, break only above a high destination
  threshold, or identify the `0050ed94` object allocation/extent in Ghidra/CDB.

### Stream Surface Probe And Menusurface Diagnostic, 2026-04-23

CDB static and runtime evidence identified the remaining native-sized map-copy
target.

Static evidence:

- `captures\cdb-static-stream-constructors-20260423.log`
- `00403EB0` and `00403EF0` construct `0050ed94` render streams.
- The constructors read `word ptr [surface]` as width/pitch, compute
  `base + row * pitch + x`, store pitch at `[stream+8]`, and store the cursor
  at `[stream+4]`.

Crash object evidence:

- `captures\map-crash-object-detail-sharedscratch-loadslot0-summary-20260423.json`
- Fault: `00403582`
- Destination: `0b26c1d0`
- Object/vtable: `00f89be0` / `0050ed94`
- Object cursor: `0b26c1d0`
- Object aux/pitch: `00000280` (`640`)

Stream-constructor evidence:

- `captures\map-stream-constructors-sharedscratch-loadslot0-summary-20260423.json`
- Primary stream group before the new diagnostic:
  `surf=028bc3c8`, `size=640x480`, `base=0b210030`,
  `cursor_max=0b250808`
- The same run reproduced the `00403582` write at `0b25c1d0`.

Diagnostic patch:

- New stage:
  `gameplay-menu640-centered-map12-dynorigin-menusurface`
- Adds `menu-surface` to the dynamic-origin sharedscratch map stage.
- Candidate:
  `C:\Clash\clash95_hd_mousedynorigin_menusurface_20260423.exe`
- SHA-256:
  `7063B2FD032974D975D82175B8ADC2DC08C3C1A72F97FC86FBB7D8C7A140578B`
- Static report:
  `captures\patch-stage-dynorigin-menusurface-20260423.json`
  (`96/96` selected bytes patched)

Runtime result:

- `captures\map-stream-constructors-menusurface-loadslot0-summary-20260423.json`
- Reached gameplay with 12 in-bounds redraws.
- `edge_overrun_rows=0`
- `exception_rows=0`
- Primary stream group after the diagnostic:
  `surf=025fc3c0`, `size=800x600`, `base=0b210030`,
  `cursor_max=0b260988`

Interpretation:

- The 12x9 map crash had two independent causes:
  initial saved scroll could exceed the new 12x9 max, and the active map target
  stream still pointed at a 640x480 menu/game surface.
- The CDB-time scroll clamp fixes the first cause.
- The `menu-surface` allocation patch fixes the observed 640x480 destination
  stream and removes the `00403582` AV in a 20-second CDB map probe.
- This made the known surface-size cause ready to combine with a permanent
  saved-scroll clamp. The PNG capture helper still can include
  debugger-console pixels instead of a clean DirectDraw/client frame.

### Permanent Saved-Scroll Clamp And Standalone Map Candidate, 2026-04-23

The PlayGame saved-scroll restore clamp is now implemented as a binary patch,
not a CDB-time edit.

Patch details:

- Stage:
  `gameplay-menu640-centered-map12-dynorigin-menusurface-scrollclamp`
- Candidate:
  `C:\Clash\clash95_hd_mousedynorigin_menusurface_scrollclamp_20260423.exe`
- SHA-256:
  `E7BFF85DF851785522206594C1FE904C6FA77EE8EDE6C4687803B0D243714DA0`
- Hook:
  file offset `0x00AB6A`, VA `0x0040B76A`, old `E8 E1 20 00 00`, new
  `E9 11 E1 0D 00`
- Cave:
  file offset `0x0E8C80`, VA `0x004E9880`

The cave clamps restored scroll after PlayGame writes the saved player values:

- `scroll_x = min(scroll_x, max(0, map_width - 12))`
- `scroll_y = min(scroll_y, max(0, map_height - 9))`

It then calls the original `0040D850` and returns to `0040B76F`.

Validation:

- `captures\patch-stage-dynorigin-menusurface-scrollclamp-20260423.json`
  reports `98/98` selected bytes patched and
  `saved_scroll_restore_clamp=true`.
- `captures\cdb-static-scrollclamp-candidate-20260423.log` confirms the hook,
  cave, original call, and return path.
- `captures\map-stream-constructors-menusurface-scrollclamp-loadslot0-summary-20260423.json`
  entered gameplay without any CDB-time scroll edit. It restored
  `scroll=(39,42)`, clamped to `(38,41)`, logged 12 in-bounds redraw rows,
  kept `edge_overrun_rows=0`, and had `exception_rows=0`.
- The primary map stream in that run was `800x600`
  (`surf=025ac408`, `base=0b220030`, `cursor_max=0b270988`), so the previously
  observed 640-wide `0050ed94` copy destination is no longer present in this
  probe.

This is the current best standalone 800x600/12x9 map candidate. The next proof
gap is capture quality and non-CDB smoke testing, because the current CDB PNG
path can still include debugger-console pixels.

Clean non-CDB capture update:

- `capture_clash_client_frame.ps1` now captures frames from a separate
  DPI-aware process and refuses captures whose client center is not the target
  Clash window.
- `run_clash_visual_smoke.ps1` keeps mouse driving DPI-unaware/logical, then
  calls that helper only for screenshots.
- The clean smoke at
  `captures\visual-smoke-20260423-113427\results.json` proves the combined
  scrollclamp/menusurface candidate is not yet shippable: it reaches the main
  menu outside CDB, but the menu is stripey/corrupt.
- Therefore `menu-surface` cannot remain a global immediate patch. It fixes the
  map stream by making the `0050ed94` target 800x600, but it breaks fixed
  640x480 menu rendering. The next binary patch should keep the
  `00447DD6 -> 00403D70` allocation at `640x480` for menu flow and grow or
  replace that surface only when entering gameplay/map rendering.

### Menu-Safe Map Surface Upgrade, 2026-04-23

The global `menu-surface` patch has been replaced by a gameplay-only surface
swap prototype.

Patch details:

- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp`
- Candidate:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_20260423.exe`
- SHA-256:
  `8DA12E7C0C0B06426B657DC199E573D346ED47D92E401296493A06945A82AC03`
- Hook:
  file offset `0x00AB6A`, VA `0x0040B76A`, old `E8 E1 20 00 00`, new
  `E9 11 E1 0D 00`
- Cave:
  file offset `0x0E8C80`, VA `0x004E9880`

The cave leaves the main-menu allocation at `00447DD6` native. After menu
dispatch, before the first gameplay redraw, it checks `dword_5202E0`; if the
surface is not already 800 pixels wide, it allocates a fresh `0xBC`-byte render
surface, calls `Render_CreateSurface(eax, edx=800, ebx=600)`, and stores the
result back to `dword_5202E0`. It then applies the saved-scroll clamp and calls
the original `0040D850`.

The stage also uses `menu-only-center-blit-640only`:

- Hook:
  file offset `0x001230`, VA `0x00401E30`, old function prologue/block replaced
  with a jump to `0x004E9920`
- Cave:
  file offset `0x0E8D20`, VA `0x004E9920`

That cave applies the menu blit offset `80,60` only when
`eax == dword_5202E0` and `word ptr [eax] == 640`. This matters because the HD
map stage intentionally swaps `dword_5202E0` to 800x600 after menu dispatch.

Validation:

- `captures\patch-stage-dynorigin-mapsurface-scrollclamp-20260423.json`
  reports `97/97` selected bytes patched.
- `captures\cdb-static-mapsurface-scrollclamp-640blit-caves-20260423.log`
  confirms both caves.
- `captures\visual-smoke-20260423-121409\results.json` reaches a centered,
  non-stripey main menu and then gameplay in a non-CDB run.
- `captures\map-stream-constructors-mapsurface-scrollclamp-640blit-loadslot0-summary-20260423.json`
  reaches gameplay with `edge_overrun_rows=0`, `exception_rows=0`, restored
  scroll clamped from `(39,42)` to `(38,41)`, and primary stream
  `800x600`.

Remaining defect:

- The non-CDB gameplay capture still has dirty/right-bottom artifacts:
  `captures\visual-smoke-20260423-121409\after-map-path.png`.
- Since stream constructors now prove an 800x600 destination and the crash rows
  are gone, investigate stale clear/present rectangles and old 640x480 UI/map
  layout draws next. Static disassembly in
  `captures\cdb-static-fullscreen-blit-fill-20260423.log` shows
  `sub_401E30` still contains a legacy `(0,0)-(639,479)` copy/present
  rectangle.

### Full Redraw Helper, 2026-04-23

The remaining map artifacts were not from `sub_418A90`; static disassembly of
the active candidate confirmed that the single-tile repaint helper already has
the 12x9 bounds.

The next missing draw path was `sub_418700`, the full redraw/scroll repaint
helper. Native code still drew 9 columns by 6 full rows, followed by a clipped
6-column bottom row. The active stage now includes `full-redraw-12x9`:

- `0x017B70`: `09` -> `0C` (`sub_418700` full redraw columns 9 -> 12)
- `0x017B81`: `06` -> `08` (`sub_418700` full redraw full rows 6 -> 8)
- `0x017DFF`: `06` -> `0C` (`sub_418700` clipped bottom row columns 6 -> 12)

Validation:

- `captures\patch-stage-dynorigin-mapsurface-scrollclamp-20260423.json`
  reports `100/100` selected bytes patched and `full-redraw-12x9` `3/3`.
- `captures\cdb-static-sub418700-fullredraw12-20260423.log` confirmed the
  earlier 12x8 plus 9-column bottom-row experiment. On 2026-04-24, bottom-row
  coverage evidence promoted that final compare to `cmp ecx,0Ch` so the HD
  bottom row draws all 12 columns.
- `captures\visual-smoke-20260423-135516\results.json` reaches gameplay and
  shows improved lower/right map coverage.
- `captures\map-stream-constructors-fullredraw12-loadslot0-summary-20260423.json`
  still reports an 800x600 primary stream, saved-scroll clamp, zero edge
  overruns, and zero exceptions.

Remaining defect:

- Far-right/top and lower-right regions still show old UI/minimap-like
  remnants. A wider `sub_418700` copy/present bounds patch to `799x591` was
  tested briefly and backed out after smoke stopped reaching gameplay. Before
  restoring that experiment, use a focused CDB probe to prove whether those
  pixels are clipped presents or overlay draws.

### Full Redraw Present Bounds, 2026-04-23

The focused full-redraw-only probe resolved the ambiguity. The 12x9 tile draw
was correct, but the full-redraw present rectangles still used native bounds.

Evidence:

- `captures\cdb-map-redraw-rect-fullonly-20260423.log` on the active
  100-patch candidate showed tile drawing to `xy=(736,464)` and bottom-row
  drawing to `xy=(544,528)` on an `800x600` `dword_5202E0` surface.
- The same log showed stale full-redraw present rectangles:
  - top `(32,16,607,225)`;
  - right `(429,225,607,252)`;
  - bottom `(32,252,607,463)`.

Added diagnostic group `full-redraw-present-bounds-800`:

- `0x017CDE`: `5F020000` -> `1F030000`
  (`sub_418700` top/right present edge `607 -> 799`)
- `0x017D6C`: `5F020000` -> `1F030000`
  (`sub_418700` right-edge compare `607 -> 799`)
- `0x017D82`: `5F020000` -> `1F030000`
  (`sub_418700` right strip present edge `607 -> 799`)
- `0x017D99`: `CF010000` -> `4F020000`
  (`sub_418700` bottom-edge compare `463 -> 591`)
- `0x017E5E`: `CF010000` -> `4F020000`
  (`sub_418700` bottom strip present edge `463 -> 591`)
- `0x017E68`: `5F020000` -> `1F030000`
  (`sub_418700` bottom strip right edge `607 -> 799`)

Validation:

- Built
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_20260423.exe`
  from the verified original, SHA-256
  `A4233F396DAFE2D4D5197C96C1EEBB44542271F6CA2461BE43514DCC2BE2F403`.
- `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-20260423.json`
  reports `106/106` selected bytes patched and
  `full-redraw-present-bounds-800` `6/6`.
- `captures\cdb-map-redraw-rect-fullonly-presentbounds-20260423.log`
  confirms runtime full-redraw presents widened to:
  - top `(32,16,799,225)`;
  - right `(429,225,799,252)`;
  - bottom `(32,252,799,591)`.
- `captures\map-redraw-rect-fullonly-presentbounds-frame-loadslot0-20260423.png`
  shows the map body filling the new right/bottom area. Remaining visible
  defects are old UI/minimap/sidebar overlays in the new top/right area.

Next target:

- Trace `dword_1845E8` overlay/sidebar blits around recovered `sub_46D20`
  and related `sub_148F8` calls. Reference disassembly shows several old
  sidebar coordinates around x `498..624` and y `10..354`; these are plausible
  sources for the duplicated top/right overlay after the map body is widened.

## Minimap Dirty-Rectangle Clip, 2026-04-23

The first `full-redraw-present-bounds-800` candidate widened the top/right
present rectangle enough to expose a second minimap copy in the HD top-right
area. CDB overlay probing showed the duplicate came from `sub_40D560`, the
minimap dirty-rectangle helper:

- `0040D340..0040D430` initializes minimap left/top/width/height globals at
  `00523344..0052334A`.
- `0040D560` copies dirty minimap chunks from the minimap backing surface at
  `0052334C`.
- With widened full-redraw presents, dirty chunks whose destination extended
  past the native 214-wide minimap caused source reads past the minimap backing
  surface and duplicated the minimap across the new right-side area.

Added diagnostic group `minimap-right-clip`:

- Hook: file offset `0x00C960`, VA `0x0040D560`,
  `56558b35e4025200 -> e91bc40d00909090`.
- Cave: file offset `0x0E8D80`, VA `0x004E9980`.
- Behavior:
  - compute `minimap_right = [00523344] + [00523348] - 1`;
  - skip the dirty chunk when left `ax` is already past `minimap_right`;
  - clamp right `bx` to `minimap_right` for partially overlapping chunks;
  - continue through the original helper at `0040D568` or original epilogue at
    `0040D6C7`.

Validation:

- Built
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapclip2_20260423.exe`
  from the verified original, SHA-256
  `03F1BE6C72B6BB7E4DC84068274F50A95F9A039DF1B0C44C3EA96CB55D263A3C`.
- `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapclip2-20260423.json`
  reports `108/108` selected bytes patched and `minimap-right-clip` `2/2`.
- `captures\cdb-map-overlay-presentbounds-minimapclip2-20260423.log` reached
  gameplay without an access violation.
- `captures\map-overlay-presentbounds-minimapclip2-frame-loadslot0-20260423.png`
  shows the duplicated minimap is gone. The remaining artifact is a black/stale
  top-right band and old vertical border texture, so the next investigation is
  a post-full-redraw overwrite or native-bounded UI/present path, not another
  minimap read-past.

## Minimap HD Right Anchor, 2026-04-23

After the duplicate-minimap clip, a focused top-band probe showed the remaining
black/stale pixels were already present in `dword_5202E0` before the top/right
present. The probe did not record a later write into the suspect band, so the
next practical layout experiment was to move the real minimap into the newly
exposed HD upper-right area instead of leaving it at the native 608-pixel
anchor.

`tools\topband_probe_summary.py` now summarizes that probe from
`captures\cdb-map-topband-minimapclip2-20260423.log` into
`captures\map-topband-minimapclip2-summary-20260424.json`:

- the probe reached gameplay and logged `FULLREDRAW_ENTER=8` with `av_rows=0`;
- the dominant top-band present source is `00418BDC` (`224` rows);
- `s672_16`, `s736_16`, `s672_80`, `s736_80`, `s672_144`, and `s736_144`
  are zero in `8/8` before and after samples;
- x `608` is nonzero in the same top rows, and later y `208` samples become
  nonzero across x `608`, `672`, and `736`.

This confirms the remaining top/right artifact in the interim `minimapclip2`
candidate is not a final present-copy problem. A follow-up image-region pass
then checked whole logical 64x64 regions instead of single pixels:

- Tool: `tools\topband_image_summary.py`
- Output: `captures\topband-image-summary-20260424.json`
- `captures\map-overlay-presentbounds-minimapclip2-frame-loadslot0-20260423.png`
  has `0.0%` nonblack pixels in x `672..799`, y `16..207`.
- `captures\map-overlay-presentbounds-minimapright-frame-loadslot0-20260423.png`
  has `98.958..100.0%` nonblack pixels across the same upper-right logical
  regions.
- `captures\map-viewportbounds-minimapright-dynvswitch-v2-frame-20260424.png`
  has `98.806..100.0%` nonblack pixels across those same regions.

Interpretation: the black upper-right band was an intermediate layout artifact
from clipping the old native-anchored minimap while leaving the HD upper-right
area exposed. Moving the minimap to the HD right anchor fills that region in
both the `minimapright` candidate and the current v2 conditional-switch
candidate. The single-pixel CDB top-band probe remains useful for surface
source proof, but it should not be treated as an open v2 map-body-fill bug
unless a fresh v2 frame shows the same region-level blanking.

Static CDB disassembly of `sub_40D330` showed the minimap left coordinate is
derived from a right anchor:

- `0040D390 ba60020000` loads right anchor `608`.
- `0040D3A8` subtracts the minimap width from that anchor.
- `0040D3AF` stores the resulting left coordinate at `00523344`.

Added diagnostic group `minimap-hd-right-anchor`:

- File offset `0x00C790`, VA `0x0040D390`.
- Old bytes `BA60020000`.
- New bytes `BA20030000`.
- Effect: compute minimap left as `800 - minimap_width`; with the observed
  214-wide minimap this places the left edge at `586` and the right edge at
  logical x `799`.

Validation:

- Built
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_20260423.exe`
  from the verified original, SHA-256
  `D326BD782F7B30FAE4F6622ACA5AF176D4D9B2B036CB67C13A5E4A47F086E11A`.
- `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-20260423.json`
  reports `109/109` selected bytes patched, with `minimap-right-clip` and
  `minimap-hd-right-anchor` both fully patched.
- `captures\cdb-map-overlay-presentbounds-minimapright-20260423.log` reached
  gameplay without an access violation and logged minimap dirty blits at
  destinations such as `(586,16)`, `(608,16)`, `(672,16)`, and `(736,16)`.
  This proves the minimap now uses the HD right anchor rather than the old
  native x `394` left coordinate.
- `captures\map-overlay-presentbounds-minimapright-frame-loadslot0-20260423.png`
  is a target-owned `1200x900` capture with the minimap visually aligned to the
  upper-right corner. The old minimap location now reveals terrain.

Next validation:

- Prove minimap hit testing/navigation still follows the moved globals by
  clicking several points inside the new `(586..799,16..229)` minimap rectangle
  and logging the resulting scroll/viewport state.

### Minimap Click Probe And Mouse Bounds, 2026-04-23

The moved minimap now has separate evidence for drawing and hit testing, but
not yet for navigation:

- `clash95_map_minimap_click_probe.cdb` logs minimap initialization,
  play-game entry, redraw state, mouse rows, minimap hit-test calls/successes,
  and AV rows.
- `tools\minimap_probe_summary.py` summarizes minimap bounds, old-anchor
  rejection, new-box acceptance, scroll changes, and mouse ranges.
- The second minimapright probe,
  `captures\cdb-map-minimapclick-minimapright-v2-20260423.log`, reached
  gameplay with no AV. Its summary is
  `captures\map-minimapclick-minimapright-summary-v2-20260423.json`.
- Runtime globals were `left=586`, `top=16`, `width=214`, `height=214`,
  `right=799`, and `bottom=229`.
- Old-anchor-only x rows were tested but not accepted
  (`old_only_test_rows=127`, `old_only_true_rows=0`), while rows inside the new
  HD minimap box were accepted (`new_box_true_rows=120`).

The blocker is input reachability, not the minimap globals:

- Logged internal mouse bounds remained `max=(610,452)`.
- Requested high client x positions such as `650`, `760`, and `700` collapsed
  to internal x around `448`.
- Scroll stayed at `(38,41)`, so minimap navigation did not change.

Static CDB disassembly of the viewport-switch path exposed old native
constants at `00460E11 push 1E0h` and `00460E1D mov ecx,280h`; `00460B20`
then writes mouse/view bounds into object fields. A diagnostic stage,
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch`,
now enables the full `viewport-switch` group with the moved minimap to test
whether those bound writes must be widened during gameplay. The candidate
`C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_vswitch_20260423.exe`
has SHA-256
`079CC3ADEA88B3C96276E0FA0F16DD886A9628C858806C131847BA814C778941`, and
`captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch-20260423.json`
verifies `111/111` selected bytes. The first runtime attempt was blocked by
`SetCursorPos` access denial in the mouse harness, so the next probe should log
bound writes first and only then rerun physical click navigation.

### Viewport Switch Bound Writes And Rerun, 2026-04-23

`clash95_viewport_bounds_probe.cdb` now logs:

- initial viewport args at `0046053F`;
- later switch args at `00460E32`;
- `sub_460B20` writes at `00460BA7`;
- mouse-bound rows at `00460A9D`.

Timed CDB-only runs show the key difference:

- Baseline moved-minimap candidate:
  `captures\cdb-viewport-bounds-minimapright-20260423.log`
  ends on a later `VIEWPORT_SWITCH_CALL right_arg=640 bottom_arg=480` and
  final `VIEWPORT_SET max=(610,452)` for metadata `005196a0`.
- Diagnostic full-switch candidate:
  `captures\cdb-viewport-bounds-minimapright-vswitch-20260423.log`
  ends on `VIEWPORT_SWITCH_CALL right_arg=800 bottom_arg=600` and final
  `VIEWPORT_SET max=(770,572)` for the same metadata.

`tools\viewport_bounds_summary.py` summarizes those runs and the compare file
`captures\viewport-bounds-compare-20260423.json` explicitly reports:

- baseline `final_set_is_native_640x480=true`;
- diagnostic `final_set_is_hd_800x600=true`.

This proves the later `sub_460D80` viewport switch is what collapses the
baseline back to native gameplay bounds.

With that bound proof in hand, the moved-minimap click probe was rerun against
the `...minimapright-vswitch` candidate. The new run reached gameplay and kept
the widened bounds during real SendInput clicks:

- `captures\cdb-map-minimapclick-minimapright-vswitch-rerun-20260423.log`
- `captures\map-minimapclick-minimapright-vswitch-rerun-summary-20260423.json`
- `captures\map-minimapclick-minimapright-vswitch-rerun-mouse-20260423.json`
- `captures\map-minimapclick-minimapright-vswitch-rerun-frame-20260423.png`

Important result:

- internal mouse rows now reach `x=648`, `x=700`, and `x=760`;
- `max=(770,572)` is preserved throughout the click run;
- old-anchor-only minimap rows are still rejected and new HD-box rows are
  accepted.

But scroll still does not change from `(38,41)`, so the remaining bug is no
longer mouse reachability. The next likely gameplay path is `sub_40DC10`,
which converts minimap cursor position back into `gameData+140008` /
`gameData+140012`. Static disassembly shows it still uses native visible-area
clamps:

- `0040DCB0 83EE09` (`map_width - 9`);
- `0040DCDA 83EA07` (`map_height - 7`).

Trace `sub_40DC10` during HD minimap clicks before promoting the diagnostic
stage.

### Minimap Action Probe And Clamp Fix, 2026-04-23

That trace is now in place.

Added:

- `clash95_minimap_action_probe.cdb`
- `tools\minimap_action_summary.py`

The focused action run against
`C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_vswitch_20260423.exe`
(`079CC3ADEA88B3C96276E0FA0F16DD886A9628C858806C131847BA814C778941`)
proved the moved minimap is not dead input:

- `sub_40DC10` is active for HD minimap clicks;
- a click around `mouse=(648,49)` writes `scroll=(13,6)`;
- a lower-right click around `mouse=(760,201)` accepts target `(41,44)` and
  ends at native-like final `scroll=(41,43)`.

Summary:

- `captures\map-minimapaction-minimapright-vswitch-summary-20260423.json`
  reports:
  - `action_path_reached=true`
  - `write_path_reached=true`
  - `accepted_target_values=[(13,6), (26,24), (41,44)]`
  - `final_scroll_values=[(13,6), (26,24), (41,43)]`

This is the missing proof that the remaining bug lived inside the minimap
action clamps, not in hit testing or cursor reach.

The three remaining clamp bytes were added to the existing 12x9 `helpers`
group:

- `0x00D0B0`: `83 EE 09` -> `83 EE 0C`
- `0x00D0DA`: `83 EA 07` -> `83 EA 09`
- `0x00D124`: `83 EA 07` -> `83 EA 09`

Rebuilt candidate:

- `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_vswitch_minimapclamp_20260423.exe`
- SHA-256:
  `438543C90A82373ED60DE50F4A451B89FABDE48E7DA759C407CFFD76BABACE29`

Static verification:

- `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch-minimapclamp-20260423.json`
  reports `114/114` selected bytes patched and `helpers 28/28`.

Second focused action result:

- `captures\map-minimapaction-minimapright-vswitch-minimapclamp-summary-20260423.json`
  reports:
  - accepted lower-right target `(41,44)` is now explicitly clamped to
    `x=38`, `y=41`;
  - final scroll values become `[(13,6), (26,24), (38,41)]`.

So the moved HD minimap now drives scroll values consistent with the 12x9
viewport.

Remaining design problem:

- this proof still relies on the full `viewport-switch` diagnostic stage,
  because the menu-safe stage collapses the later gameplay bounds back to
  native `640x480`;
- the next stable fix should make the later `sub_460D80` switch conditional or
  gameplay-only so gameplay keeps widened bounds without regressing menu
  safety.

### Conditional Viewport Switch V2, 2026-04-24

The stable-switch prototype now branches on the proven gameplay/map metadata
pointer instead of the current surface width. CDB showed the later switch uses
`edx == 005196A0` for the map metadata, while menu/native paths can still pass
other metadata such as `00545158`.

Patch cave behavior:

- `cmp edx, 005196A0`
- map/gameplay path: push bottom `600`, set right `800`
- other paths: push bottom `480`, set right `640`
- then run the original `sub_460B20` call and return

Important implementation footnote: the first candidate used `74 0A`, which
landed two bytes early inside `push 480` and produced bogus runtime args
`right_arg=3 bottom_arg=27`, invalid max bounds, and an access violation. The
working v2 cave uses `74 0C`.

Current v2 evidence:

- Candidate:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_dynvswitch_v2_20260424.exe`
- SHA-256:
  `FDFE9A346D709A44E612E1FF1ED9AA42C1B191D566EC1E013ADA86CF0802F1AD`
- Static report:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-v2-20260424.json`
  verifies `114/114` selected bytes.
- Viewport report:
  `captures\viewport-bounds-minimapright-dynvswitch-v2-20260424.json`
  reports final metadata `005196a0`, final max `(770,572)`,
  `final_set_is_hd_800x600=true`, and no AV rows.
- Minimap action report:
  `captures\map-minimapaction-minimapright-dynvswitch-v2-summary-20260424.json`
  reports accepted HD minimap targets and final scroll values
  `{(13,6), (26,24), (38,41)}` with `av=0`.

This is the first candidate that combines the moved HD minimap, widened
gameplay bounds, and menu-safe conditional switching. It has replaced the old
`novswitch` default in `patch_clash95_hd.py` because the old default is proven
to collapse gameplay bounds back to native values after the map-surface swap.

### Bottom-Right Clipped Row Fix, 2026-04-24

The current v2 gameplay capture exposed a black lower-right corner. The new
`tools\map_tile_coverage.py` analyzer treats the HD map as a 12x9 grid starting
at logical `(32,16)`, masks the moved minimap rectangle, and checks each
64x64 cell.

Evidence on the pre-fix v2 frame:

- Input: `captures\map-viewportbounds-minimapright-dynvswitch-v2-frame-20260424.png`
- Output: `captures\map-tile-coverage-v2-bottom12-20260424.json`
- Active bottom-row cells `r8c9`, `r8c10`, and `r8c11` were blank:
  - `r8c9`: `3.103%` nonblack
  - `r8c10`: `1.042%` nonblack
  - `r8c11`: `1.031%` nonblack

Root cause:

- The `full-redraw-12x9` group still preserved the native clipped-row shape by
  changing the bottom-row loop only from `6` columns to `9` columns.
- For the 800x600 map surface, the bottom row needs all 12 columns.

Patch change:

- File offset `0x017DFF`, VA `0x00418BFF`
- Old base byte: `06`
- Previous patch byte: `09`
- New patch byte: `0C`
- Meaning: `sub_418700` clipped bottom row columns `6 -> 12`

Fresh candidate:

- `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_dynvswitch_bottom12_20260424.exe`
- SHA-256:
  `A85E9E7FD0E16B26773B0479C987DC3648D38E4B07209FA849D39C1AD9DAFEAB`

Validation:

- `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-bottom12-20260424.json`
  reports `114/114` selected bytes patched.
- `captures\viewport-bounds-minimapright-dynvswitch-bottom12-20260424.json`
  reports no AV rows and final map metadata `005196a0` with HD max bounds
  `(770,572)`.

Remaining proof:

- Capture a fresh gameplay frame from the bottom12 candidate and run
  `tools\map_tile_coverage.py` against it. The expected visual result is that
  `r8c9`, `r8c10`, and `r8c11` are no longer blank.

### Bottom-Row Partial Repaint Alignment, 2026-04-24

The full-redraw path now draws all 12 columns in the clipped bottom row, but the
single-tile/partial repaint helper still carried the older 9-column bottom-row
cutoff. That mismatch can reintroduce stale lower-right cells after any partial
dirty-tile repaint.

Patch change:

- File offset `0x017EDB`, VA `0x00418ADB`
- Old base byte: `06`
- Previous patch byte: `09`
- New patch byte: `0C`
- Meaning: `sub_418A90` last-row X cutoff `6 -> 12`, matching the
  `sub_418700` clipped bottom-row redraw.

Remaining proof:

- Build a fresh current-stage candidate, verify `00418AD9 cmp ecx,0Ch` and
  `004189FD cmp ecx,0Ch`, then capture a real gameplay frame and rerun
  `tools\map_tile_coverage.py --require-gameplay`.

Follow-up visual smoke:

- `captures\visual-smoke-20260424-074630\results.json` completed without a
  crash and captured the centered 800x600 menu in a 1200x900 client.
- The run used `MoveMode=none` and `ClickMode=postmessage` because the Codex
  desktop runner denied `SetCursorPos`, absolute `SendInput`, and
  `GetCursorPos` with `[WinError 5]`.
- The menu and post-path frame hashes match, so this is menu/liveness evidence,
  not clean gameplay-entry evidence.
- A manual or otherwise interactive real-cursor smoke should still be run
  before calling the stage fully stable.

### Retired Route Notes Removed, 2026-05-12

The obsolete route evidence block from 2026-04-24/25 has been removed. Current validation notes resume below with the no-popup CDB surface dump path.

No-popup CDB surface dump follow-up:

- Added a host-side hidden-desktop harness:
  `run_cdb_surface_dump.ps1`.
- Added the route/dump probe:
  `clash95_surface_dump_probe.cdb`.
- Added the raw surface converter:
  `tools\cdb_surface_dump_to_png.py`.
- Intended proof path:
  route into gameplay under x86 CDB, read `dword_5202E0`, dump the 8-bit map
  surface with `.writemem`, reconstruct a grayscale-index PNG, then run
  `tools\map_tile_coverage.py` on that PNG.
- Runtime evidence:
  `captures\cdb-surface-dump-20260428-105423\RUN-SUMMARY.md` failed before
  gameplay with `App_RequestQuit=True` and
  `DirectDraw Error DDERR_UNSUPPORTED`.
- Interpretation:
  the no-popup harness works as a hidden diagnostic path, but raw system
  DirectDraw does not support the needed mode on a separate hidden desktop. A
  successful no-popup surface dump likely needs a local DirectDraw proxy/wrapper
  that owns the surface memory and does not depend on active-desktop display
  mode creation.

No-popup DirectDraw proxy evidence:

- `ddraw_surfdump_proxy/` now provides a minimal 32-bit local `ddraw.dll` for
  hidden CDB surface dumping only. It implements enough `IDirectDraw2`,
  `IDirectDrawSurface`, and `IDirectDrawPalette` behavior for the game to reach
  the map redraw path without using system DirectDraw on the hidden desktop.
- `captures\cdb-surface-dump-20260428-123224` proves the route:
  `SURFDUMP_PLAYGAME`, four `SURFDUMP_REDRAW` rows, and
  `SURFDUMP_READY redraw_seq=4 surface=0a1bed90 size=(800,600)
  base=0a460030 bytes=480000`.
- The reconstructed grayscale surface is
  `captures\cdb-surface-dump-20260428-123224\surface.png`; tile coverage reports
  `gameplay_frame_likely=True`, `active=108`, `measurable=99`, and `blank=13`.
- The remaining map-drawing focus is the right-side blank region reported by
  the coverage tool, not DirectDraw hidden-desktop initialization.
- CDB probe caveat: the full startup path is currently required. Skipping or
  fast-forwarding `UI_StartAnims` can leave state uninitialized and crash at
  `00487cf4` while touching address `0x38`.

No-popup host-read visibility evidence:

- `run_cdb_surface_dump.ps1` now defaults to host-side `ReadProcessMemory`
  after the CDB log emits `SURFDUMP_READY`. The generated CDB script prints
  `SURFDUMP_HOST_READY` and continues while the host reads the surface bytes,
  then the harness kills only the launched CDB/candidate processes. This avoids
  the older nested `.writemem` command-tail issue.
- `clash95_surface_dump_probe.cdb` now emits `SCROLL_VISDUMP` plus a CDB `db`
  memory dump for the same 12x9 viewport before the surface dump action.
- Successful run:
  `captures\cdb-surface-dump-20260429-111340`.
- Runtime evidence:
  `SURFDUMP_PLAYGAME`, `SURFDUMP_READY redraw_seq=4 surface=0a07ed90
  size=(800,600) base=0a320030 bytes=480000`, `SCROLL_VISDUMP
  player=0 screen0=(32,16) map0=(10,17) rows=9 cols=12`, and
  `SURFDUMP_HOST_READY`.
- Harness summary:
  `Passed=true`, `LaunchMode=hidden-desktop`, `StoppedAfterDump=true`,
  `DumpMethod=host-readprocessmemory`, `HostDumpedMemory=true`, and no timeout.
- Surface evidence:
  `surface.raw` is 480000 bytes and `surface.png` is 800x600.
- Image-only coverage still reports the same 13 blank cells:
  `r3c10`, `r3c11`, `r4c10`, `r4c11`, `r5c10`, `r5c11`, `r6c10`, `r6c11`,
  `r7c10`, `r7c11`, `r8c0`, `r8c10`, and `r8c11`.
- Visibility-aware coverage reports `observation_points=108`,
  `status_counts.visibility_zero=13`, and `unexplained_blank_cells=[]`.
- Interpretation:
  the no-popup route now classifies the dark right/bottom cells as game
  visibility/fog state in the same run that produced the grayscale surface
  dump. This is not evidence for another map-drawing patch.

No-popup visible-edge experiment:

- Added `-ForceVisibleEdges` to `run_cdb_surface_dump.ps1`. It is a
  debugger-only validation switch for the current load-slot-0 viewport at
  `scroll=(10,17)`, not a normal gameplay patch.
- First syntax attempts:
  `captures\cdb-surface-dump-20260429-115600` and
  `captures\cdb-surface-dump-20260429-120508` exposed CDB command-string and
  expression-parser issues in the generated breakpoint action.
- Useful partial run:
  `captures\cdb-surface-dump-20260429-124928`.
- Evidence:
  the CDB log reached gameplay, emitted `SURFDUMP_FORCE_VISIBLE_EDGES`, dumped
  the surface, and `SCROLL_VISDUMP` showed the target cells with nonzero direct
  visibility values. `tools\visibility_coverage.py` classified all 13 target
  cells as `blank_despite_visible`, not `visibility_zero`.
- Interpretation:
  the no-popup forced-visible action did write the direct visibility bytes by
  dump time, but the surface pixels were unchanged. Either the writes happened
  too late for the tile draw that produced the dumped surface, or the tile path
  depends on neighbor/path-specific visibility evidence beyond direct cell bits
  in this harness.
- Follow-up attempts:
  moving the injection earlier to the `PlayGame` breakpoint avoided the late
  write, but runs `captures\cdb-surface-dump-20260429-125308` and
  `captures\cdb-surface-dump-20260429-125735` stalled before menu routing on
  the hidden desktop. A default no-force retry
  `captures\cdb-surface-dump-20260429-130246` also stalled, so this is
  currently a hidden-desktop startup fragility, not proof that the PlayGame
  injection is wrong.
- Next step:
  make the hidden-desktop route less dependent on full `UI_StartAnims`, or add
  a CDB probe that forces the exact `sub_40F0C0` neighbor-visible condition
  before `sub_416850` draws the HD edge cells.

No-popup forced visible-edge proof:

- `clash95_surface_dump_probe.cdb` now carries disabled-at-start VEDGE
  breakpoints for the same branch evidence used by the earlier visibility proof:
  pre-call tile entry at `00416850`, `sub_40F0C0` call/return at
  `004169bc` / `004169c1`, clear/draw branches at `00417a98` / `004169e6`,
  and post-return pixel samples at `0041876b` / `004189fa`.
- `run_cdb_surface_dump.ps1 -ForceVisibleEdges` enables those breakpoints at
  `PlayGame`, injects the exact visibility bytes for the current load-slot-0
  viewport, and freezes the proof viewport at `scroll=(10,17)` during redraw.
- `-FastForwardStartAnims` was changed from the older unsafe AVI-call skip to a
  sleep-fast-forward path that lets startup/AVI resource initialization run.
- Successful run:
  `captures\cdb-surface-dump-20260429-133917`.
- Command:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -ForceVisibleEdges -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-surface-dump -RunSeconds 120`.
- Runtime evidence:
  hidden desktop, local DirectDraw proxy, `SURFDUMP_FORCE_VISIBLE_EDGES`,
  `SURFDUMP_FORCE_VIEWPORT`, `SURFDUMP_READY` on an `800x600` surface at
  `map0=(10,17)`, 54 `SURFDUMP_VEDGE_VISRET` rows, and 54
  `SURFDUMP_VEDGE_POST` rows.
- Coverage:
  `gameplay_frame_likely=True`, `active=108`, `measurable=99`, `blank=0`,
  `stale_or_solid=0`, `right_below_minimap=97.838%`, and `bottom=77.373%`.
- Conclusion:
  the two dark right/bottom corner cells are not an HD map drawing failure when
  visibility is present. Normal gameplay should keep authentic fog/visibility;
  `-ForceVisibleEdges` remains a debugger-only proof switch.

Forced visible-edge proof gate:

- Added `tools\forced_visible_summary.py` and wired it into
  `run_cdb_surface_dump.ps1 -ForceVisibleEdges`.
- The gate requires the exact proof shape, not just a nonblank image:
  `gameplay_frame_likely=True`, zero active blank cells, latest
  `SCROLL_VISDUMP map0=(10,17)`, force-visible and force-viewport markers, 54
  `SURFDUMP_VEDGE_VISRET` rows, 54 `SURFDUMP_VEDGE_POST` rows, all VEDGE
  visibility returns nonzero, and all VEDGE post samples nonblack.
- Positive proof:
  `captures\cdb-surface-dump-20260429-135242` passed the integrated gate.
- Negative proof:
  `captures\cdb-surface-dump-20260429-133504` fails the standalone gate because
  it drifted to `map0=(0,41)`, lacked `SURFDUMP_FORCE_VIEWPORT`, had wrong
  VEDGE counts, and retained active blank cells.

Normal no-popup visibility explanation gate:

- `run_cdb_surface_dump.ps1` now runs
  `tools\visibility_coverage.py --require-explained` whenever a normal
  non-`-ForceVisibleEdges` dump has active blank cells.
- The harness records `VisibilityExitCode`, `VisibilityRequireExplained`, and
  `VisibilityExplainedGate` in `summary.json`, mirrors the gate in
  `RUN-SUMMARY.md`, and fails the run if any active blank lacks same-run
  visibility, fog, or clip evidence.
- Positive proof:
  `captures\cdb-surface-dump-20260429-111340` still passes because all 13
  active blank cells are classified as `visibility_zero`; the direct
  `--require-explained` check exits `0`.
- Fresh normal proof:
  `captures\cdb-surface-dump-20260429-140916` reran the normal hidden-desktop
  path with `-UseDdrawProxy -NoSkipStartAnims -RequireGameplay`. It passed with
  `VisibilityRequireExplained=True`, `VisibilityExplainedGate.Passed=True`,
  `VisibilityExitCode=0`, 13 active blank cells, and zero unexplained blanks.
- Negative proof:
  using the same coverage with an empty CDB log exits `2` with 13
  `unexplained_blank` cells, so the gate will not silently accept image blanks
  without debugger evidence.

No-popup map evidence matrix:

- Added `tools\no_popup_map_evidence_matrix.py` to join the two current proof
  shapes into one gate.
- Explicit validation with
  `captures\cdb-surface-dump-20260429-140916` plus
  `captures\cdb-surface-dump-20260429-135242` passes.
- Auto-selection with `--require-pass` also picks those two runs and passes.
- `--write-markdown captures\no-popup-map-evidence-current.md` writes the
  current human-readable proof report with both screenshots embedded.
- Interpretation:
  the current patch has a compact no-popup evidence story: normal dark cells
  are explained by visibility/fog, and the same HD right/bottom region draws
  when debugger-visible.

Current HD map patch-stage gate:

- Added `tools\patch_stage_report.py --require-current-hd-map`.
- The gate verifies the selected executable has no original or unexpected bytes
  for the recommended HD stage and that the map summary proves:
  `visible_tiles=12x9`, 12x9 loops/helpers, 800x600 input and viewport init,
  dynamic map-surface viewport switching, widened full-redraw present bounds,
  right-side minimap clipping/anchoring, saved-scroll clamp, and post-menu map
  surface upgrade.
- Positive proof:
  `C:\ClashTests\cdb-surface-dump\clash95_hd_surfdump_20260429_140916.exe`
  passes with 118 patched, 0 original, 0 unexpected, and
  `current_hd_map_gate: PASS`.
- Negative proof:
  `C:\Clash\clash95.exe` is rejected with exit code `2` because all 118
  selected bytes are still original and the map summary remains 9x7.

CDB-only right-bottom UI policy, 2026-04-30:

- User direction: use CDB-only proof for current HD-map work.
- Use `run_cdb_surface_dump.ps1`, hidden-desktop CDB, host CDB probes, and
  CDB-only harnesses for new right-bottom UI and map-drawing proof.
- Added `clash95_right_bottom_ui_probe.cdb` as the current static/runtime probe
  target for action-panel/right-bottom UI work. It should be launched only by a
  CDB-only route harness.
- `tools\right_bottom_ui_bounds.py` is the current screenshot-side helper for
  measuring right-side panel, minimap, bottom strip, and bottom-right 12x9
  cells. Baseline output for
  `captures\map-minimapaction-minimapright-dynvswitch-v2-frame-20260424.png`
  is stored at `captures\right-bottom-ui-bounds-baseline-20260429.json`.
- Every completed task report should show a current UI screenshot artifact. For
  CDB-only runs, the reconstructed surface PNG from `run_cdb_surface_dump.ps1`
  counts as the screenshot artifact; for docs-only work, reuse the latest
  relevant UI capture and label it as reused.

dword_526990 callback probe, 2026-04-30:

- Added `clash95_d526990_extra.cdb` and `tools\d526990_summary.py`.
- Successful hidden-desktop run:
  `captures\cdb-surface-dump-20260430-115605`.
- The run reached gameplay and `SURFDUMP_READY`, dumped an 800x600
  `surface.png`, and preserved the existing visibility explanation gate.
- Runtime rows:
  3 full-redraw entries, 3 `004187A0` callback tests, 0 calls through
  `dword_526990`, 0 writes to `00526990`, and `dword_526994=00000000`.
- Interpretation:
  the optional `sub_418700` callback is not merely clipped or misplaced in the
  current loaded-save path; it is not installed. The next patch-discovery step
  is to find static xrefs/writers for `00526990` and `00526994` and probe that
  setup path before changing UI draw/present rectangles.

dword_526994 static owner probe, 2026-04-30:

- Static CDB byte-pattern search on the original executable found no direct
  writer for `00526990` beyond the `sub_418700` callback test/call at
  `004187A0` / `004187A9`.
- `00526994` has a clearer owner cluster:
  - `00423760` saves the old flag, sets `00526994=1`, calls `sub_418700`,
    restores the old value, then calls `sub_418700` again.
  - `00423B00` sets `00526994=1` and calls `sub_418700`.
  - `00423B40` clears `00526994=0` after `00418FE0` and calls `sub_418700`.
  - `00418AF1` reads `00526994` in the lower/right dirty-edge fallback path.
- Added `clash95_d526994_setup_extra.cdb`,
  `clash95_d526994_setup_min_extra.cdb`, and parser support in
  `tools\d526990_summary.py`.
- Runtime setup attempts in
  `captures\cdb-surface-dump-20260430-121113`,
  `captures\cdb-surface-dump-20260430-132217`, and
  `captures\cdb-surface-dump-20260430-133012` stalled before
  `SURFDUMP_MAIN_HIT`, with no owner markers and no game AV. Treat these as
  hidden-desktop startup/AVI-route failures before drawing conclusions about
  the owner cluster.

startup-stall and dword_526994 rerun, 2026-04-30:

- Added `clash95_startup_stall_d526994_extra.cdb` and
  `tools\startup_stall_summary.py`.
- `captures\cdb-surface-dump-20260430-142129` with full startup reached the
  logo `Video_Avi_playIn` path and stopped progressing after
  `STARTUP_VIDEO_AFTER_MODE_BEGIN`; no `SURFDUMP_MAIN_HIT` and no AV.
- `captures\cdb-surface-dump-20260430-145646` with
  `-FastForwardStartAnims` reached the menu route and gameplay, dumped a fresh
  800x600 surface, and still reported 3 `D526994_MIN_CALLBACK_TEST` rows with
  `callback=00000000` and `flag526994=00000000`.
- No `00423760`, `00423B00`, or `00423B40` owner entry fired in the successful
  load-slot route. The next recovery question is which caller/game state
  invokes that owner cluster.

dword_526994 owner route trigger, 2026-04-30:

- Static direct-call scan of the original executable found:
  - `00423760` called from `004087C8`.
  - `00423B00` called from `0040A5EE`.
  - `00423B40` called from `0040A51A`.
  - `00423B00` and `00423B40` are both reached through `sub_40A500`; the
    initial `PlayGame` setup reaches `sub_40A400` at `0040B7AE` and then
    `sub_40A500` at `0040B7B3`.
- Added `clash95_d526994_owner_route_extra.cdb` plus
  `tools\d526994_owner_route_summary.py`.
- Hidden-desktop CDB run
  `captures\cdb-surface-dump-20260430-224749` passed and generated a fresh
  800x600 surface. Parser result:
  `owner_count=1 route_count=8 ready=True av_count=0`.
- The successful route used a debugger-only state nudge immediately before the
  natural `0040B7B3` call: `dword_511B58=-1` and `dword_514194=0`. That
  forced `sub_40A500` to take the `0040A51A -> 00423B40` branch.
- Key row:
  `D526994_OWNER_423B40_ENTRY ret=0040a51f callback=00000000 flag526994=00000000 selected=-1 prior=0`.
- Patch implication:
  `00526994` is not enough by itself. The forced owner route proves the branch
  can execute, but it remains a clear-highlight path with `dword_526990` null.
  Recovering the missing right-bottom border frame and bottom tooltip should
  next target `sub_40A400`, `sub_419D80`, and `dword_511D40` descriptor setup
  and clipping/present bounds.

dword_511D40 descriptor trace, 2026-05-06:

- Added `clash95_descriptor_trace_extra.cdb` and
  `tools\descriptor_trace_summary.py`.
- Hidden-desktop CDB run
  `captures\cdb-surface-dump-20260506-092608` passed and generated the current
  800x600 screenshot artifact at
  `captures\cdb-surface-dump-20260506-092608\surface.png`.
- Runtime evidence:
  `sub_40A400` reached `sub_419D80(dword_511D40)`, and all six descriptors
  scanned and drew. The draw rows were `(416,400)`, `(480,400)`, `(544,400)`,
  `(416,432)`, `(480,432)`, and `(544,432)`.
- The run observed zero `DESC_SKIP_X640` rows. `render` and `map_surface` were
  both the same 800x600 surface during `DESC_40A400_ENTRY` and
  `DESC_419D80_ENTRY`.
- Patch implication:
  the `dword_511D40` descriptor list is not the missing HD lower-right border
  or tooltip. It draws the native action-button cluster and does not cover the
  HD bottom/right bands. Do not patch this list as the primary border-tooltip
  recovery path until a later probe proves a specific descriptor should move or
  widen.
- Next lead:
  trace the action/status/bottom-pane functions `004347A0`, `00434E20`,
  `00435280`, `00435500`, and `UI_DrawUnitInfoPane` at `00419F70`, ideally
  with CDB-forced selection/hover state, to classify whether the relevant UI is
  skipped by state, overwritten after draw, or anchored to native 640x480
  bounds.

hover/selection UI probe, 2026-05-06:

- Added `clash95_hover_selection_ui_extra.cdb` and
  `tools\hover_selection_ui_summary.py`.
- Probe targets:
  `004347A0`, `00434E20`, `00435280`, `00435500`, `00419F70`, `0041A7B2`,
  `00419ED0`, `00435A00`, `00435BC0`, filtered text calls, and filtered
  `004024E0` presents.
- The first passing hidden-desktop run,
  `captures\cdb-surface-dump-20260506-093846`, proved the extra probe can ride
  on the surface-dump harness, but its hover setter collided with the harness
  `00406FA0` redraw breakpoint.
- The hover setter now uses `0040AE11`, the caller just before `sub_406FA0`.
- Final parsed negative run:
  `captures\cdb-surface-dump-20260506-100922` reached `SURFDUMP_READY` and
  observed four forced hover states, but the synthetic mouse sequence moved the
  scroll from `(10,17)` to `(35,51)` before the dump, so `map_tile_coverage.py`
  rejected the screenshot as non-gameplay.
- Important state evidence:
  all forced hover rows reported `d532218=00000000`, `selected=0`,
  `action=0`, and `d532220=0`. None of the target UI entry, text, or filtered
  present breakpoints fired.
- Patch implication:
  do not patch anchors or present rectangles for these functions yet. In this
  route they are not running. Mouse-forced hover is also a poor proof method
  because it activates map scrolling before the UI state is entered.
- Next lead:
  trace the non-mouse state route into the action panel owner: `sub_435BC0`,
  `sub_435A00`, `sub_435AC0`, `UI_GetGridIndexFromMouse`, and writes to
  `dword_532218` / `dword_5322C8`.

passive action panel route probe, 2026-05-06:

- Added `clash95_action_panel_route_extra.cdb` and
  `tools\action_panel_route_summary.py`.
- The probe does not write mouse globals. It passively watches:
  `PlayGame -> 40A400/40A500`, `004338E0`, the `00433914` call to
  `sub_435BC0`, `sub_435BC0`, `sub_435B90`, `sub_435A00`, `sub_435AC0`,
  `UI_GetGridIndexFromMouse`, action/status draw functions, and write
  watchpoints for `dword_532218` / `dword_5322C8`.
- Static correction:
  CDB disassembly confirmed the relevant owner caller is `sub_4338E0` at
  `004338E0`; the direct call to `sub_435BC0` is at `00433914`.
- Final run:
  `captures\cdb-surface-dump-20260506-102113` passed on hidden-desktop CDB
  with the DirectDraw proxy and produced
  `captures\cdb-surface-dump-20260506-102113\surface.png`.
- Parser result:
  `ready=True av_count=0 owner_rows=0 panel_rows=0 draw_rows=0
  nonzero_owner_rows=0`.
- Runtime evidence:
  the normal load-slot route reached `PlayGame -> 40A400 -> 40A500` with
  `selected=-1`, `prior=-1`, `d532218=00000000`, and `d5322c8=0`, then reached
  `SURFDUMP_READY` on an 800x600 map surface. It did not enter
  `004338E0`, the `00433914` owner call, `sub_435BC0`, grid hit-testing, or
  action/status draw functions.
- Patch implication:
  do not patch the native action/status anchor or hitbox constants yet. The
  current proof says those routines are not executing in the loaded-game route.
  The next useful probe should use a non-mouse state nudge to enter the
  building/castle owner path without moving map scroll.

controlled action panel state-route probe, 2026-05-06:

- Added `clash95_action_panel_state_route_extra.cdb` and extended
  `tools\action_panel_route_summary.py` for `APSTATE_*` markers.
- Static safety point:
  `sub_435BC0` sets `dword_532210=0`, calls `sub_435B90`, and exits the loop
  when `dword_532210` changes. If the owner route becomes reachable, a
  debugger-only probe can latch that value after one poll to avoid hanging in
  the action-panel loop.
- Final run:
  `captures\cdb-surface-dump-20260506-111214` passed on hidden-desktop CDB
  with the DirectDraw proxy and produced
  `captures\cdb-surface-dump-20260506-111214\surface.png`.
- Parser result:
  `ready=True av_count=0 owner_rows=0 panel_rows=0 draw_rows=0
  nonzero_owner_rows=0`.
- Runtime evidence:
  `APSTATE_NUDGE_SKIPPED` fired with `d532150=00000000`,
  `d532218=00000000`, `mouse=(320,166)`, and `scroll=(10,17)`. No watched
  writes to `00532150`, `0053214C`, or `00532154` fired before
  `SURFDUMP_READY`.
- Patch implication:
  the current load-slot state does not install the owner global needed by
  `004338E0 -> 00433914 -> sub_435BC0`. Continue with static caller/writer
  recovery for `dword_532150` / `dword_53214C` / `dword_532154`; do not patch
  draw or presentation constants for the action/status panel until the natural
  owner setup path is known.

castle owner setup static/runtime probe, 2026-05-06:

- Static CDB scan of the original executable found references to
  `00532150` at `004329E4`, `00432AF8`, `00432C48`, `00433098`,
  `00433910`, `00433CE4`, `00433D00`, and `00433D1C`; references to
  `0053214C` at `00433C4C` and `00433D94`; and references to `00532154` at
  `00432FE8`, `0043394C`, `00433994`, `004339E4`, and `00433DF0`.
- Direct-call scanning found no `E8` calls to `00433C20`. A dword-pointer
  scan found `00433C20` referenced from `0042270A`; disassembly around
  `00422709` shows `mov ecx,00433C20`, `cmp esi,63h`, and a branch into the
  shared descriptor install path. This identifies the owner setup as castle
  screen command `0x63`, not as a normal map-load routine.
- Disassembly around `00433C20` identifies the owner setup writer:
  `00433C26` writes `dword_532150`, `00433C4B/00433C4C` installs
  `dword_53214C`, and `00433D5A` writes `dword_532154` after resource
  allocation. The later action path remains `004338E0 -> 00433914 ->
  sub_435BC0`.
- Added `clash95_castle_owner_setup_extra.cdb` as a passive CDB-only probe for
  `00422020`, `00422709`, `0042257E`, `00433C20`, write watches on
  `00532150` / `0053214C` / `00532154`, and the `004338E0` / `00433914` /
  `00435BC0` action-owner path.
- Added `tools\castle_owner_setup_summary.py` to parse those markers and write
  JSON/markdown run summaries.
- Runtime command:
  `run_cdb_surface_dump.ps1 -UseDdrawProxy -NoSkipStartAnims -RequireGameplay -ExtraProbeTemplate .\clash95_castle_owner_setup_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-castle-owner-setup -RunSeconds 150`.
- Runtime evidence:
  `captures\cdb-surface-dump-20260506-121909` passed on the hidden desktop,
  produced a fresh 800x600 `surface.png`, and the current HD map patch-stage
  gate passed for
  `C:\ClashTests\cdb-castle-owner-setup\clash95_hd_surfdump_20260506_121909.exe`.
- Parser result:
  `SURFDUMP_READY` at line 189, `setup_rows=0`, `owner_global_rows=0`,
  `action_rows=0`, and `av_rows=0`.
- Visibility/coverage result:
  `map_tile_coverage.py` still reports 13 active blank cells, and
  `visibility_coverage.py --require-explained` explains all 13 as
  `visibility_zero`.
- Interpretation:
  the current normal load-slot route reaches gameplay but does not enter the
  castle screen dispatcher, does not install command `0x63`, and does not write
  `dword_532150` / `dword_53214C` / `dword_532154`. The missing right-bottom
  owner/action UI remains a route/state issue. The next useful step is a
  CDB-only castle-screen entry probe that opens or safely calls the authentic
  `00422020` owner screen path for a known castle index, then checks whether the
  border frame and bottom tooltip draw on the 800x600 surface.

castle screen invoke and owner setup proof, 2026-05-06:

- Added `clash95_castle_screen_invoke_extra.cdb` as a controlled CDB-only probe.
  It route-injects from `PlayGame` into full castle screen routine `00422180`
  with `eax=0` for castle index 0, forces one command `0x63` hit-test result,
  forces the descriptor click test, and dumps the current surface when
  `00433C20` writes `dword_532154`.
- Corrected static naming:
  `00422180` is the full castle screen routine and `00422020` is the render
  hook installed by that routine. The command `0x63` setup path is still
  `00422709 -> 0042257E -> 00433C20`.
- Added `-SkipMapValidation` to `run_cdb_surface_dump.ps1` so non-map UI
  surface dumps can still produce `summary.json`, `RUN-SUMMARY.md`, and a PNG
  without forcing `map_tile_coverage.py` onto castle/menu surfaces.
- Runtime command:
  `run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -ExtraProbeTemplate .\clash95_castle_screen_invoke_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-castle-screen-invoke -RunSeconds 120`.
- Successful evidence:
  `captures\cdb-surface-dump-20260506-141239` passed on the hidden desktop with
  host-side `ReadProcessMemory`, no AV rows, and candidate SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Key CDB rows:
  `CASTLE_INVOKE_PLAYGAME`, `CASTLE_SCREEN_OWNER_SET_422207`,
  `CASTLE_RENDERHOOK_DRAW_422020`, two `CASTLE_CMD99_SETUP_422709` rows,
  `CASTLE_DESCRIPTOR_INSTALL_42257E callback=00433c20`,
  `CASTLE_FORCE_COMMAND99_CLICK`, `CASTLE_OWNER_SETUP_433C20`, and writes to
  `00532150`, `0053214C`, and `00532154`.
- Parser result:
  `tools\castle_owner_setup_summary.py --require-surface-ready --require-owner-setup`
  reports `ready_line=222`, `setup_rows=4`, `owner_global_rows=4`,
  `action_rows=0`, and `av_rows=0`.
- Visual result:
  `captures\cdb-surface-dump-20260506-141239\surface.png` is a 640x480
  grayscale castle screen dump with visible top resource frame, castle banner,
  and bottom tooltip frame. `tools\right_bottom_ui_bounds.py` measured custom
  `bottom-tooltip` nonblack coverage at `92.623%` and `right-banner` at
  `96.836%`.
- Interpretation:
  the owner setup path is authentic and reachable, but it is native castle
  screen state on a 640x480 surface. The missing HD gameplay right-bottom UI is
  still not proven to be a draw clipping bug. The next proof should attempt a
  safe post-owner route into `004338E0 -> 00433914 -> sub_435BC0` on an
  800x600 gameplay surface or show why that action route is castle-screen-only.

post-owner action panel proof, 2026-05-06:

- Added/refined `clash95_post_owner_action_extra.cdb` for a CDB-only,
  debugger-controlled route from the 800x600 gameplay redraw into owner setup
  and then the action-panel path.
- Probe shape that works:
  replace data watchpoints with software breakpoints, short-return from
  `00433C20` immediately after `dword_532154` is written, and enter the action
  route at `0043390F` so it still loads `dword_532150` and reaches
  `00433914 -> sub_435BC0` without stalling in the `004338E0` prelude.
- Successful command:
  `run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -ExtraProbeTemplate .\clash95_post_owner_action_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-post-owner-action -RunSeconds 120`.
- Successful evidence:
  `captures\cdb-surface-dump-20260506-175108` passed on the hidden desktop,
  dumped an 800x600 surface, and produced
  `captures\cdb-surface-dump-20260506-175108\surface.png`.
- Parser result:
  `tools\action_panel_route_summary.py --require-ready --require-owner`
  reports `ready=True`, `av_count=0`, `owner_rows=11`, `panel_rows=6`,
  `draw_rows=5`, and `nonzero_owner_rows=13`.
- Draw evidence:
  the route hit `APPOST_433914_CALL_435BC0`,
  `APPOST_OWNER_435BC0_ENTRY`, `APPOST_WRITE_532218`,
  `APPOST_PANEL_DRAW_4347A0`, `APPOST_GRID_DRAW_434E20`,
  `APPOST_STATUS_DRAW_435280`, and `APPOST_ACTION_BOX_435500`.
- Visual evidence:
  the bottom tooltip region is visible on the 800x600 gameplay surface

castle barracks UI probe, 2026-05-11:

- Added `clash95_castle_barracks_ui_extra.cdb` as a focused CDB-only probe for
  the post-owner castle action-panel path. It records owner setup, the
  `00433914 -> 00435BC0` entry, selected addon/list state, panel/grid/status
  draw rows, and the bottom action-box render target.
- Added `tools\castle_barracks_ui_summary.py` to parse `APBARRACKS_*` rows.
  The parser handles multiple CDB `.printf` records on a single physical log
  line, which occurs in the hidden-desktop CDB route.
- Runtime evidence:
  `captures\cdb-surface-dump-20260511-084202` passed on the hidden desktop,
  dumped an 800x600 surface, and produced
  `captures\cdb-surface-dump-20260511-084202\surface.png`.
- Parser result:
  `ready=True`, `panel=True`, `action_box=True`, `av_count=0`, and
  `last_selected_addon=0`.
- Important row:
  `APBARRACKS_PANEL_DRAW_4347A0` logged
  `list=(0,1,3,16,17,-1,-1,-1,-1,-1,-1,-1)`,
  `selected_index=0`, `selected_addon=0`, and
  `render=0a07ed90 map_surface=0a07ed90`.
- Remaining defect:
  `APBARRACKS_ACTION_BOX_435500` logged
  `render=0051d4c0 map_surface=0a07ed90 scratch=0051d4c0 scratch_sz=(800,600)`.
  The fresh screenshot and `right_bottom_ui_bounds.py` still show large black
  right/bottom components, so the next target is action-box render-target or
  copyback recovery around `00435500` and its restore/copyback sequence.
  (`83.256%` nonblack). The right-bottom panel remains mostly black
  (`21.43%` nonblack), and `APPOST_ACTION_BOX_435500` reports
  `render=0051d4c0` while the map surface is `0a57edb0`.
- Interpretation:
  the missing bottom tooltip was route/state related. The remaining
  right-bottom panel issue is probably render-target selection or copyback from
  the `0051D4C0` action-box target, not another global map tile-loop problem.

action-box redirect/copyback negative proof, 2026-05-06:

- Extended `clash95_post_owner_action_extra.cdb` with debugger-only
  `APREDIR_*` breakpoints around the `00435500` action-box render-target
  switch and the following `00435D93 -> 00405020` call.
- Redirect-only run:
  `captures\cdb-surface-dump-20260506-180501` redirected the `00435532`
  current-render write from `0051D4C0` to the live map surface for this CDB
  session. It passed with no AV rows, but the right-bottom panel remained
  `21.43%` nonblack and `r8c10` / `r8c11` stayed fully black.
- Copyback run:
  `captures\cdb-surface-dump-20260506-180755` also redirected the `00435D93`
  post-action `00405020` target to the live map surface. It passed with no AV
  rows, but produced the same raw and PNG hashes as the redirect-only run.
- Important samples:
  before/after action-box and copyback, the map samples at `(586,528)`,
  `(672,528)`, and `(736,528)` stayed `(c1,01,01)`, while scratch-like samples
  stayed `(00,66,93)`.
- Updated inference:
  `00435500` target selection and the immediate `00405020` copyback are not
  sufficient to recover the right-bottom blank cells. Next trace should focus
  on the actual tile draw/visibility decisions for blank cells in the
  post-owner action capture, especially `r6c10`, `r6c11`, `r7c10`, `r7c11`,
  `r8c0`, `r8c10`, and `r8c11`.

post-owner tile visibility proof, 2026-05-06:

- Added `clash95_post_owner_tile_visibility_extra.cdb` for the same safe
  post-owner action route plus focused visibility samples for the seven blank
  cells.
- Extended `tools\visibility_coverage.py` so it can consume `APVIS_CELL` rows
  and base `SURFDUMP_VEDGE_*` draw-time rows.
- Clean evidence:
  `captures\cdb-surface-dump-20260506-190037` passed with the hidden-desktop
  DirectDraw-proxy route, dumped an 800x600 post-owner surface, and produced a
  gameplay-like frame. `tools\action_panel_route_summary.py` reports
  `owner_rows=11`, `panel_rows=6`, `draw_rows=5`, and `av_count=0`.
- The seven blank cells are still:
  `r6c10`, `r6c11`, `r7c10`, `r7c11`, `r8c0`, `r8c10`, and `r8c11`.
- Each focused row reports zero visibility and fog sample `01`, for example:
  `byte=00`, `hit=00`, `sample=01`, `center_sample=01`.
- `tools\visibility_coverage.py --require-explained` classifies all seven
  cells as `visibility_zero` and reports zero unexplained blanks.
- A separate draw-time diagnostic
  `captures\cdb-surface-dump-20260506-185450` armed the base
  `SURFDUMP_VEDGE_*` rows. It proves the same cells enter the visibility-zero
  clear path and end with sample `01`, but the instrumentation caused an early
  base dump, so use it as draw-time proof rather than a visual baseline.
- Updated inference:
  the right/bottom black cells are explained by normal fog/unexplored
  visibility state in this save. Do not patch more draw loops or present
  bounds for these cells unless a future forced-visible or explored-save proof
  shows they stay blank despite nonzero visibility.

post-owner seven-cell forced-visible proof, 2026-05-06:

- Added a debugger-only `-PostOwnerForceVisibleSeven` path to
  `run_cdb_surface_dump.ps1`. It writes exactly the visibility bytes needed for
  `r6c10`, `r6c11`, `r7c10`, `r7c11`, `r8c0`, `r8c10`, and `r8c11` through the
  existing PlayGame CDB breakpoint before HD redraw. This is evidence only, not
  a gameplay patch.
- Added `tools\post_owner_forced_visible_summary.py` to gate the focused
  proof.
- Successful evidence:
  `captures\cdb-surface-dump-20260506-200426` passed on the hidden desktop
  with `-UseDdrawProxy -FastForwardStartAnims -PostOwnerForceVisibleSeven` and
  the post-owner extra probe.
- Coverage:
  `map_tile_coverage.py` reports `gameplay_frame_likely=True` and no blank
  active cells.
- Focused APVIS rows:
  all seven target cells have nonzero hits after the forced bytes, including
  `r6c10 hit=80`, `r6c11 hit=80`, `r7c10 hit=01`, `r7c11 hit=01`,
  `r8c0 hit=02`, `r8c10 hit=02`, and `r8c11 hit=02`.
- Interpretation:
  the same HD 12x9 map path that left those cells black under normal save
  visibility draws them when visibility is present. The right/bottom dark
  cells are a fog/unexplored-state artifact of the current save evidence, not a
  remaining map-loop or present-bound defect.

post-owner forced-visible harness gate, 2026-05-06:

- Wired `tools\post_owner_forced_visible_summary.py` into
  `run_cdb_surface_dump.ps1` for `-PostOwnerForceVisibleSeven` runs. The
  harness now emits `post-owner-forced-visible-summary.json` /
  `post-owner-forced-visible-summary.txt`, reports the gate in
  `RUN-SUMMARY.md`, and throws if the focused proof fails.
- Fresh evidence:
  `captures\cdb-surface-dump-20260506-201114` passed with
  `Post-owner forced-visible gate: passed`.
- The focused gate reports `force=1`, `done=1`, `action=1`, `ready=1`,
  no blank active cells, no missing cells, and no zero-hit cells.

post-owner evidence matrix, 2026-05-08:

- Added `tools\post_owner_evidence_matrix.py`.
- The matrix pairs the latest passing normal post-owner visibility-zero run
  with the latest passing seven-cell forced-visible run and fails if either
  proof is missing or failed.
- Current passing output:
  `captures\post-owner-evidence-current.md`.
- Current pair:
  normal `captures\cdb-surface-dump-20260506-190037` and forced-visible
  `captures\cdb-surface-dump-20260506-201114`.

HD map smoke matrix, 2026-05-08:

- Added `tools\hd_map_smoke_matrix.py`.
- The matrix combines the current HD map patch-stage gate with the post-owner
  evidence matrix and does not launch CDB or the game.
- Current passing output:
  `captures\hd-map-smoke-current.md`.
- Current candidate:
  `C:\ClashTests\cdb-post-owner-forced-visible\clash95_hd_surfdump_20260506_201114.exe`,
  SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Fresh-base reproduction is documented in `README.md`. The important
  evidence artifact is the `tools\patch_stage_report.py --write-json` manifest:
  it records each selected patch's file offset, RVA, VA, expected old bytes,
  expected new bytes, actual bytes, status, group, and rationale note before
  the candidate is accepted by `tools\hd_map_smoke_matrix.py`.
- `prepare_hd_map_smoke_candidate.ps1` is the safe dry-run entrypoint for that
  reproduction path. It verifies the base SHA when accessible, prints the
  unique candidate path and commands, and refuses repository-local candidate
  output by default.
- `tools\patch_manifest_compare.py` compares two patch-stage report JSON files
  without reading executables. The current example comparison
  `captures\patch-manifest-compare-current-vs-partial12.md` highlights the
  historical 9-column to 12-column bottom-row map drawing changes at
  `0x017DFF` and `0x017EDB`, plus the dynamic viewport-switch cave byte change
  at `0x0E8DC0`.
- `captures\hd-map-evidence-current.md` is the compact current evidence index.
  It links the smoke matrix, post-owner evidence matrix, patch-manifest
  comparison, normal/forced run summaries, and the current screenshot
  artifacts.
- `tools\evidence_index_check.py` verifies that the current evidence index's
  local Markdown links and screenshot artifacts resolve. Current check output:
  `captures\hd-map-evidence-current-check.json`.

castle barracks selected-addon and copyback trace, 2026-05-11:

- Added `clash95_castle_barracks_select_extra.cdb` as a CDB-only route proof
  for the castle barracks/action-panel UI. It forces `dword_532220` to selected
  index `1`, then logs `004347A0`, `00434E20`, `00435280`, `00435500`,
  `00435532`, `0043553F`, `00435569`, `00435D93`, `00435D9E`, and `00435DA5`.
- Fresh hidden-desktop run:
  `captures\cdb-surface-dump-20260511-134947` passed with no visible desktop
  window, no AV rows, and an 800x600 `surface.png`.
- The parsed result reports `APBARRACKS_SELECT_FORCED=1`,
  `selected_index=1`, `selected_addon=1`, panel/grid/status/action-box markers
  present, and `SURFDUMP_READY`.
- Copyback evidence:
  `00435500` deliberately switches `dword_511230` to `0051D4C0`, draws the
  action-box rectangle, then restores the old render target. Later,
  `00435D93` loads `eax=0051D4C0`, `00435D98` loads
  `edx=dword_53221C`, `00435D9E` clears `esi`, and `00435DA0` calls
  `00405020`.
- Current samples at the copyback points remain split:
  `map_samples=(c1,01,01)` while `scratch_samples=(00,66,93)`. This keeps the
  strongest lead on copyback/routing from the scratch render area to the HD map
  surface, not on missing barracks panel draw execution.
- Next proof:
  use CDB only to perform a manual row-copy experiment at `00435DA5`, copying
  the action-box rectangle from the scratch/render source into
  `dword_5202E0`, then compare the new `surface.png` against
  `captures\cdb-surface-dump-20260511-134947`.

castle barracks centered presentation proof, 2026-05-11:

- Runtime proof:
  `captures\cdb-surface-dump-20260511-141143` first proved the desired visual
  operation under CDB by copying the native `640x480` castle/barracks layer to
  scratch, clearing the `800x600` map surface, and copying it back at
  `(80,60)`.
- Patcher group:
  `castle-ui-center-present`.
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter`.
- Hook:
  file offset `0x0351A5`, VA `00435DA5`, old bytes `B8 D8 4C 54 00`,
  new bytes `E9 C5 D3 0D 00`.
- Cave:
  file offset `0x11136F`, VA `0051316F`, old bytes `00 * 86`.
  The cave copies `dword_5202E0` top-left `640x480` to `0051D4C0`, clears the
  target, copies `0051D4C0` back into `dword_5202E0` at `(80,60)`, restores
  `eax=00544CD8`, and jumps back to `00435DAA` so the original
  `mov ebx,00435B90; call Render_Present` code runs unchanged.
- Failed cave attempts:
  file offset `0x0EA087` was in `.idata` and corrupted imports
  (`c0000139`). VA `0051216F` was an incorrect DGROUP mapping and AVed on
  zero bytes. The corrected DGROUP VA is `0051316F`.
- Passing validation:
  `captures\cdb-surface-dump-20260511-142304` passed with no visible desktop
  window, no AV rows, no debugger-side `APBARRACKS_CENTER_*` assist, an
  `800x600` dump, and centered screenshot
  `captures\cdb-surface-dump-20260511-142304\surface.png`.
- Known gap:
  this centers presentation only. The next patch/probe must align
  castle/barracks hitboxes and mouse tests by `(80,60)` or prove an equivalent
  input transform.

castle barracks centered hitbox transform, 2026-05-11:

- Added patch group `castle-ui-centered-input` and stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`.
- The patch deliberately leaves castle/barracks draw coordinates alone. The
  centered visual layer remains a post-draw presentation copy from
  `castle-ui-center-present`.
- The input fix is local to the castle/barracks interaction loop:
  - file `0x034F90`, VA `00435B90`, old `52 B8 C0 D4 51 00`, new
    `E9 8B D6 0D 00 90`, jumps owner-poll entry to cave `00513220`;
  - file `0x034FB3`, VA `00435BB3`, old `5A C3 8D 80 00`, new
    `E9 A8 D6 0D 00`, jumps owner-poll exit to cave `00513260`;
  - file `0x0351F5`, VA `00435DF5`, old `E8 C6 3F FE FF`, new
    `E9 CB D3 0D 00`, wraps the descriptor hit-test call to `00419DC0` through
    cave `005131C5`.
- The caves temporarily subtract `80 << byte_54512C` from `dword_544CFC` and
  `60 << byte_54512C` from `dword_544D00`, run the original owner-poll or
  descriptor hit-test code, then restore the globals. Underflow is acceptable
  because signed mouse comparisons fail outside the native hitboxes and the
  original globals are restored before return.
- Passing validation:
  `captures\cdb-surface-dump-20260511-143741` passed under hidden-desktop CDB,
  no visible active-desktop window, no AV rows, `SURFDUMP_READY`, and
  screenshot `captures\cdb-surface-dump-20260511-143741\surface.png`.
- Patch report:
  `captures\cdb-surface-dump-20260511-143741\patch-stage-report.json` reports
  every selected byte patched, including `castle-ui-centered-input` `6/6`.
- Next proof:
  add a focused CDB hitbox probe that forces centered screen coordinates over
  one barracks grid cell or action button and requires the expected
  hover/selection marker. The current run proves safety and preserved visuals,
  but not yet a real centered click path.

castle barracks grid hitbox proof, 2026-05-11:

- The first centered-hitbox patch missed a separate path:
  `00435A17` calls `UI_GetGridIndexFromMouse` (`00435580`) after the
  descriptor wrapper has already restored the mouse globals.
- Added two more `castle-ui-centered-input` patches:
  - file `0x034E17`, VA `00435A17`, old `E8 64 FB FF FF`, new
    `E8 6E D8 0D 00`, redirects the grid helper call;
  - file `0x11148A`, VA `0051328A`, old `00 * 80`, wraps `00435580` with the
    same temporary `-80,-60` logical mouse transform and restores `eax`.
- Added `clash95_castle_barracks_hitbox_extra.cdb` to force a displayed
  centered grid coordinate and log the transform chain. The proof coordinate
  is displayed `(530,133)`, expected native `(450,73)`, grid result `0`.
- Passing validation:
  `captures\cdb-surface-dump-20260511-145141` passed hidden-desktop CDB. The
  log contains:
  `APBARRACKS_HITBOX_FORCE_CENTERED centered=(530,133)`,
  `APBARRACKS_HITBOX_OWNER_NATIVE mouse=(450,73)`,
  `APBARRACKS_HITBOX_GRID_ENTRY mouse=(450,73)`, and
  `APBARRACKS_HITBOX_GRID_RESULT result=0 expected=0`.
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-145141\surface.png`.
- Patch report:
  `captures\cdb-surface-dump-20260511-145141\patch-stage-report.json` reports
  `128 patched, 0 original, 0 unexpected`; `castle-ui-centered-input` is
  `8/8` patched.
- Residual limitation:
  this is still debugger-driven input. It proves the centered coordinate maps
  into the native barracks grid hit-test correctly. A later manual/input smoke
  should prove real mouse clicks through the same path outside CDB forcing.

castle barracks raw click-gate proof, 2026-05-11:

- Follow-up run:
  `captures\cdb-surface-dump-20260511-150643`.
- The previous grid proof rewrote `eax=1` at `00435A0E`, which directly
  bypassed the raw `DD_IsFlipping(dword_544CD8)` route gate.
  `004608F0` shows that this gate reads bit `1` from the input object byte at
  `00544D04`.
- Added `clash95_castle_barracks_click_extra.cdb`. The probe still uses CDB to
  set displayed mouse `(530,133)` and the click-state flag, but it no longer
  rewrites `eax` at `00435A0E`.
- Important rows:
  `APBARRACKS_HITBOX_CLICK_STATE centered=(530,133) ... click_flag=00000001 button0=0x80`;
  `APBARRACKS_HITBOX_GRID_GATE raw_result=1 forced_result=none`;
  `APBARRACKS_HITBOX_GRID_ENTRY mouse=(450,73)`; and
  `APBARRACKS_HITBOX_GRID_RESULT result=0 expected=0 mouse=(450,73)`.
- Validation:
  `tools\castle_barracks_hitbox_summary.py --require-ready --require-raw-gate --forbid-forced-gate --require-grid-hit`
  passed with
  `raw_gate_ok=True`, `forced_gate_count=0`, and `grid_hit_ok=True`.
- Patch report:
  `captures\cdb-surface-dump-20260511-150643\patch-stage-report.json` reports
  `128 patched, 0 original, 0 unexpected`, with
  `castle-ui-center-present: 2/2` and `castle-ui-centered-input: 8/8`.
- This is still a synthetic CDB click-state proof, not manual DirectInput
  proof, but it removes the direct gate override from the previous hitbox
  validation.

castle barracks action descriptor proof, 2026-05-11:

- Follow-up run:
  `captures\cdb-surface-dump-20260511-160221`.
- Added `clash95_castle_barracks_action_click_extra.cdb` and
  `tools\castle_barracks_action_click_summary.py`.
- Target:
  displayed centered bottom-left action coordinate `(161,501)`, expected
  native `(81,441)`.
- Important rows:
  `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1 click_cb=00435620 state=0x01 mouse=(81,441)`;
  `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620 desc_xy=(41,425)`;
  `APBARRACKS_ACTION_CLICK_435620_ENTRY desc=0051519a mouse=(81,441)`;
  and `APBARRACKS_ACTION_CLICK_EXIT_SET action_state=1`.
- Validation:
  `tools\castle_barracks_action_click_summary.py --require-ready --require-descriptor-click --require-action-exit --forbid-failure-exit`
  passed with
  `descriptor_click_ok=True`, `action_exit_ok=True`,
  `failure_exits=0`, and `av_count=0`.
- Patch report:
  `captures\cdb-surface-dump-20260511-160221\patch-stage-report.json` reports
  `128 patched, 0 original, 0 unexpected`, with
  `castle-ui-center-present: 2/2` and `castle-ui-centered-input: 8/8`.
- Caveat:
  this proves centered descriptor identity and the stock action callback path,
  but it is still debugger-assisted. The passing probe rearms `dword_544D04`
  at `00419C47` because earlier runs showed the hidden-desktop/proxy route
  clears that click byte before descriptor `0051519a` is evaluated. Do not
  treat this as manual DirectInput proof.

castle barracks action descriptor pre-gate refinement, 2026-05-11:

- Follow-up run:
  `captures\cdb-surface-dump-20260511-161212`.
- Failed exploratory run:
  `captures\cdb-surface-dump-20260511-160850` timed out when a global
  `00419B80` descriptor-entry breakpoint was installed. Treat that address as
  hot and late-arm it only after routing into the target UI, if needed.
- The new passing probe moves the harness rearm from `00419C47` to `00419C28`.
  This is after `00419B80` has selected action descriptor `0051519a`, but
  before the stock `00460900` and `004608F0` input gates run.
- Important rows:
  `APBARRACKS_ACTION_WIDGET_REARM_PRE_GATES desc=0051519a ... click_flag=00000001`;
  `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1`;
  `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620`;
  and `APBARRACKS_ACTION_CLICK_EXIT_SET action_state=1`.
- Validation:
  `tools\castle_barracks_action_click_summary.py --require-ready --require-descriptor-click --require-action-exit --forbid-failure-exit`
  passed with
  `descriptor_click_ok=True`, `action_exit_ok=True`,
  `failure_exits=0`, and `av_count=0`.
- Current interpretation:
  the remaining synthetic input issue belongs to the hidden-desktop/proxy
  harness. The centered hitbox patch correctly maps `(161,501)` to native
  `(81,441)`, identifies descriptor `0051519a`, and reaches callback
  `00435620` when `dword_544D04` survives to the action descriptor.

castle barracks no-rearm CDB harness fix, 2026-05-11:

- Diagnostic run:
  `captures\cdb-surface-dump-20260511-162607`.
- Passing run:
  `captures\cdb-surface-dump-20260511-162846`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-162846\surface.png`.
- Template change:
  `clash95_surface_dump_probe.cdb` now keeps its generic `00419B80`
  post-gameplay button cleanup only while no extra UI probe is active
  (`@$t18 == 0`).
- Validation:
  `tools\castle_barracks_action_click_summary.py --require-ready --require-descriptor-click --require-action-exit --forbid-failure-exit`
  passed with `descriptor_click_ok=True`, `action_exit_ok=True`,
  `failure_exits=0`, and `av_count=0`.
- Important rows:
  `APBARRACKS_ACTION_WIDGET_PRE_GATES desc=0051519a ... click_flag=00000001 button0=0x80`;
  `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1`;
  `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620`;
  and `APBARRACKS_ACTION_CLICK_EXIT_SET action_state=1`.
- Current interpretation:
  the previous need for descriptor-local rearm was introduced by the CDB
  surface-dump harness itself. With the template cleanup guarded, the centered
  barracks action descriptor works through the stock gate/callback path under
  no-popup CDB. This is still synthetic click-state evidence, not manual
  DirectInput proof.

castle barracks second bottom action descriptor, 2026-05-11:

- Added `clash95_castle_barracks_second_action_extra.cdb`.
- Extended `tools\castle_barracks_action_click_summary.py` with
  `--expect-desc` and `--expect-callback`.
- Passing run:
  `captures\cdb-surface-dump-20260511-163846`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-163846\surface.png`.
- Target:
  displayed `(276,501)` -> native `(196,441)`.
- Descriptor:
  `005151cf`, native origin `(156,425)`, stock callback `004356c0`.
- Validation:
  `tools\castle_barracks_action_click_summary.py --expect-desc 0x005151cf --expect-callback 0x004356c0 --require-ready --require-descriptor-click --forbid-failure-exit`
  passed with no AV rows and no failure exit.
- Important rows:
  `APBARRACKS_ACTION_WIDGET_PRE_GATES desc=005151cf ... click_flag=00000001 button0=0x80`;
  `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=005151cf click_gate=1 click_cb=004356c0`;
  `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=005151cf callback=004356c0`;
  and `APBARRACKS_ACTION_CLICK_4356C0_CHECK_RET check_result=0`.
- Current interpretation:
  the centered UI patch correctly routes a second bottom barracks action
  descriptor through the stock gate and callback. The callback's internal
  availability check rejects the current selected addon (`selected_addon=0`),
  so the next success-branch proof should first select a compatible addon or
  target a callback that is valid for the default selected unit.

castlecenter-all catalog and selected action proof, 2026-05-11:

- Added stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`.
  It currently aliases the proven `castlecenter-hitbox` byte set while the
  runtime catalog identifies which additional castle-interior routes need
  their own surgical hooks.
- Added `clash95_castle_interior_catalog_extra.cdb` and
  `tools\castle_interior_catalog_summary.py`. The catalog run
  `captures\cdb-surface-dump-20260511-170708` safely invoked full castle
  screen routine `00422180`, forced descriptor hit-test results, suppressed
  callbacks, and dumped the surface with no AV rows.
- Catalog result:
  `ready=True surface_size=[640, 480] descriptors=7 commands=0x63,0x86,0x87,0x99,0x9C,0x9F,0xA6 av_count=0`.
  The commands map to callbacks `00433C20`, `0044FE70`, `0042B0A0`,
  `0043DCE0`, `0043D8E0`, `0043DEE0`, and `0043DAE0`.
- Important inference:
  the full castle overview path still owns a native `640x480` surface. This is
  the same split previously seen around `00422180` / `00422020`; the barracks
  centering hook at `00435DA5` does not automatically center this full
  overview route. The next true "all castle screens" patch target is the
  castle-screen allocation/present path around `00422305` and `00422020`.
- Added `tools\castle_ui_center_geometry.py` for conservative 800x600 centered
  UI validation.
- Fresh `castlecenter-all` barracks run:
  `captures\cdb-surface-dump-20260511-170759` passed hidden-desktop CDB, dumped
  an 800x600 `surface.png`, and passed the geometry gate:
  `centered_gate=PASS image=800x600 centered_nonblack=74.464% max_margin_nonblack=24.979%`.
- The same run used `clash95_castle_barracks_second_action_select1_extra.cdb`
  to select addon `1`, click displayed `(276,501)` -> native `(196,441)`, hit
  descriptor `005151cf`, and reach callback `004356c0`'s success branch.
  Parser gate:
  `ready=True descriptor_click_ok=True action_exit_ok=False success_4356c0_ok=True failure_exits=0 clickflag_writes=0 av_count=0`.

castle overview gate and selected-action harness cleanup, 2026-05-12:

- Added `tools\castle_overview_gate.py` as the compact full castle overview
  gate. It combines `tools\castle_interior_catalog_summary.py` and
  `tools\castle_ui_center_geometry.py`, requiring:
  ready catalog markers, no AV rows, all seven expected castle descriptor
  commands, CDB-reported `800x600` surface size, and centered 800x600 PNG
  geometry.
- The gate is intended for the full `00422180` / `00422020` castle overview
  route. It is not a replacement for the already passing barracks-specific
  action/hitbox probes.
- The current catalog evidence at
  `captures\cdb-surface-dump-20260511-170708` is expected to fail this gate
  because it still reports a `640x480` surface. This keeps the next patch
  target narrowed to the full castle overview allocation/present path around
  `00422305` and `00422020`.
- Updated `clash95_castle_barracks_second_action_select1_extra.cdb` to produce
  a controlled dump-ready stop at `004356C0` for the selected-index-1 proof
  before the callback can hit the May 12 `c0000096` path at `004024E6`.
- Extended `tools\castle_barracks_action_click_summary.py` with
  `controlled_4356c0_ok` and `--require-4356c0-controlled-stop`, so future
  reruns can distinguish a deliberate CDB harness stop from a timeout or crash.
- Fresh validation run:
  `captures\cdb-surface-dump-20260512-082120` passed hidden-desktop CDB and
  dumped an 800x600 surface before the privileged-instruction path.
- Candidate SHA-256:
  `AF53C76D4E4C6184E1038B228F23F8D77FA2E0FDB31B6CD6BFC9CB497590619E`.
- Parser gate:
  `ready=True descriptor_click_ok=True action_exit_ok=False success_4356c0_ok=False controlled_4356c0_ok=True failure_exits=0 clickflag_writes=0 av_count=0`.
- This run proves the selected-index-1 descriptor/callback route and CDB
  harness control. Use `captures\cdb-surface-dump-20260511-170759` for the
  older post-action centered-frame/success-branch visual reference, because
  the new controlled-stop run intentionally exits earlier.

castle barracks duplicate/blur fix, 2026-05-12:

- Problem:
  the older castle centering path could produce a duplicated or blurry unit
  list/stat panel. The initial theory was that centering happened before the
  stock present callback, but runtime evidence showed a second source too: the
  barracks loop calls `00435B90` directly at `00435DDE`, after the initial
  present setup.
- Patch:
  `castle-ui-center-present-wrapper` now has three records:
  `00435DAA: bb905b4300 -> bb6f315100`, `00435DDE: e8adfdffff ->
  e88cd30d00`, and cave `0051316F`. The cave calls stock `00435B90`, then runs
  the same copy/clear/copy centering primitive as the older pre-present hook.
- Cave caution:
  when adding `popad/pushad` around the centering core, recalculate relative
  calls. The correct helper targets from wrapper `0051316F` are `00435B90`,
  `004024E0`, `00401E60`, and `004024E0`. Landing at `004024E6` produces
  `c0000096` on an invalid/privileged instruction.
- Evidence:
  `captures\cdb-surface-dump-20260512-082418` passed hidden-desktop CDB,
  dumped an 800x600 surface, and produced screenshot
  `captures\cdb-surface-dump-20260512-082418\surface.png`.
- Geometry:
  `tools\castle_ui_center_geometry.py --require-centered` passed with
  `centered_nonblack=71.228%`, `max_margin_nonblack=0.0%`, and
  `native_origin_echo_absent=True`.
- Patch-stage:
  candidate SHA-256
  `4E42D4A3EA61E1DB31007600A8B6515B4803E14CCC07FD2CBF1C2BA838492498`;
  `129 patched, 0 original, 0 unexpected`; current HD map gate passed.
- Validation caveat:
  the selected-index-1 screenshot run intentionally stops at `004356C0` before
  executing the callback body, so parser validation should require
  `--require-4356c0-controlled-stop` for that run. The older May 11 run remains
  the success-branch proof, but its native-origin echo is now rejected by the
  stricter geometry gate.

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

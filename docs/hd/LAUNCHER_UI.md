# Compact HD Mod-style launcher

The launcher uses the Heroes III HD Mod launcher's compact desktop layout as
its visual reference: a gold-on-teal banner, an executable/action row, a tabbed
settings area, paired graphics/component panels, and an Exit footer. The
banner is original vector-drawn Clash branding; no Heroes logos, artwork or
font files are included. The reference is the author's launcher screenshot:
https://sites.google.com/site/heroes3hd/eng/graphics

The existing Tk/ttk implementation remains in `src/launcher/gui.py`. Windows
keeps its native widget theme; Linux uses ttk's built-in clam theme. The
initial client size is approximately 730x650 at 96 DPI. Layout dimensions and
the banner scale with Tk's DPI setting. The window remains resizable and
previously saved window geometry is honored.

## Main settings

The renderer and source size are dropdowns instead of a vertical list of
resolution radio buttons. Custom dimensions appear only when `custom` is
selected. The source size still changes the internal map viewport; scaling
still uses the existing verified integer wrapper option. The mode label
reflects the existing windowed DirectDraw wrapper configuration, not a newly
implemented graphics backend.

The profile badge, read-only component list, viewport dimensions and validation
summary update from the current profile and shared display plan. All Framed
resolutions remain experimental; the Classic 800x600 status remains unchanged.
The component list describes the selected recipe and is not a plugin manager.
Language is informational English text, not a nonfunctional language selector.
No fullscreen, filter, system-cursor, auto-update, donation or multiplayer
controls are added merely to resemble the reference.

`Create HD exe` calls the existing candidate builder/deployment backend without
starting the game. It checks the original and output directory, blocks while
a game/debugger is detected (or its process scan fails), and asks for
confirmation before experimental preparation. A missing wrapper does not
prevent preparation, but is reported and disables Play. Preparation failures
remain errors. The original executable is never overwritten.

`Play` retains the existing user-initiated launch sequence and confirmation
checks. Instantiating the launcher, switching tabs, selecting a resolution,
opening diagnostics and creating an HD executable do not launch the game.
Preparation and Play cannot reenter each other while an operation is active.

## Secondary tabs

Launcher settings contains game/candidate folder fields, Browse buttons,
explicit Apply folders, and selected-candidate cleanup. Applying paths goes
through existing candidate-path validation before persisting them. Explicit
folder updates preserve the saved Classic resolution, including from a Framed
session. Cleanup still requires confirmation and uses the existing backend.

Information holds the full profile warning and explanation of preparation,
local game requirements and evidence boundaries. Diagnostics holds all four
installation checks, the full display plan summary, and the activity log.
The footer gives one short installation status instead of placing long error
and validation reports above the graphics settings.

## Validation and screenshots

`python tools/test_launcher_ui.py` runs the interaction unit tests without
opening windows; actual widget tests are opt-in. The separate Launcher UI
workflow sets `CLASH_LAUNCHER_UI_TESTS=1`, runs every UI test without skips on
Linux and Windows, and tests every tab at 96, 144 and 192 DPI. Linux widget
execution and screenshots use a separate Xvfb display, not a user's desktop.
Windows tests do not take desktop screenshots.

The Linux job retains actual Tk screenshots and a manifest binding them to the
source commit and GUI source hash. Each image is verified against a second,
pixel-identical capture. The capture environment deliberately has no game or
wrapper installed. These are launcher UI images, not gameplay screenshots,
manual input evidence, or stable renderer promotion.

No binary patcher, source pins, resolution registry, wrapper configuration,
save data or core process-start function is changed by this restyling.

# Experimental multi-resolution launcher

The standalone Windows launcher now contains Classic, Framed, Complete HD and
Modal Widgets. Its `hd_multires_v1` successors cover every preset above native
800x600: 1024x768, 1280x720, 1280x960, 1366x768, 1920x1080, 2560x1440,
3440x1440 and 3840x2160. That makes thirty-two independent profile/resolution
combinations. The first batch was 1920x1080, 2560x1440 and 3840x2160; the
second added the other five presets. The 800x600 cells keep their own recipes.
Every new combination remains **experimental**. Classic 800x600 remains the
stable default.

Below the 1144-pixel wide-menu width, the Classic predecessor has no RX
extension section. Classic 1024x768 therefore adds its own `.hdcode` section
for the bounded map code instead of extending an existing tail.

## Using the launcher

Open `ClashHDLauncher.exe`, select the installed game, renderer and resolution,
then choose **Create HD exe**. **Play** starts the prepared copy. Preparation
does not start the game or overwrite the original executable. The standalone
launcher needs neither Python nor a repository checkout; it contains no game,
wrapper DLL, game assets or saves.

The supported original SHA-256 remains
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
Generated candidates are isolated under
`C:/ClashTests/launcher/multires/hd_multires_v1/<profile>/<resolution>/`.
The GUI remembers its selected profile and each profile's resolution separately.
The historical Classic setting and the Classic default for headless commands
are preserved. An explicit `--profile` overrides the remembered GUI profile.

The existing source CLI uses the same recipe registry:

```powershell
python -B src/launcher/run.py --profile completehd --resolution 3840x2160 --describe-plan
python -B src/launcher/run.py --profile completehd --resolution 3840x2160 --prepare
```

The new `hd_multires_v1` identity is separate from each frozen predecessor.
Explicit legacy stages still select their existing recipes. Other presets and
custom dimensions have not been qualified by this first batch.

## Implemented source behavior

- Framed-derived profiles install bounded full-map repaint and actual-world
  mouse admission, including owned army input where that profile provides it.
  Small maps no longer need to fill the full-tile viewport.
- Classic installs separate bounded map/partial-cell/mouse adapters while
  retaining Classic frame, native command descriptors and panel branches.
  It does not call a Framed builder under the Classic name.
- Tile size remains 64 pixels. Cells outside the actual world are excluded
  from targeting; camera clamping respects world bounds.
- Candidate preparation and launch verification reconstruct exact bytes,
  metadata and a canonical initial-image probe. A private source issuer rejects
  altered frozen producers and ignores replaceable public builder aliases.
- The package contains a fixed allowlist of exact source resources because
  those constructors authenticate their own source. A compiled inventory
  identity checks the extracted resources before exposing HD backends.
- The successor records checked predecessor source bindings as canonical
  relative paths. Historical recipes retain their metadata; temporary one-file
  extraction directories do not become part of the new candidate identity.

These are installed source/byte capabilities. They are not fresh native input,
screen composition, save/load or endurance acceptance.

## Verification and remaining acceptance

The public source/CPU tests use authored synthetic memory and callbacks. An
optional local lane constructs all thirty-two candidates from the exact user-owned
original without executing the game:

```powershell
python -B tools/test_hd_multires_candidate.py --original-backed C:/Clash/clash95.exe
python -B tools/test_hd_multires_installed_cpu.py --original-backed C:/Clash/clash95.exe
```

`tools/hd_multires_qualification.py` prepares immutable candidate bundles or
authenticates their executable, metadata, probe, original and current launcher
catalog. Its selected-cell report keeps the whole release target at 36 and
never promotes missing runtime lanes. The fifteen native acceptance lanes and
candidate-bound installed expanded battle remain unfinished.

The separate final Adjacent/Unit successor and original-backed CPU fixture
prove only the valid-index/type-minus-one provider-free route through real
Count and Unit returns. Normal sprite-bearing Unit routes, provider/RLE
ownership, complete battle installation, native lifetime and healthy full-game
continuity remain separate work. A source or emulator pass is not gameplay proof.

The installed-candidate CPU fixture loads actual reconstructed candidate bytes
at two image bases. It covers small and tall worlds, partial cells, camera
clamping, full/incremental paint and ordinary-map targeting in both presentation
modes. Its drawing/input callbacks remain models. The fresh portable-metadata
receipt is `reports/hd-multires-installed-cpu-20261027-portable.json`; the earlier
source closure's receipt is preserved separately.

`tools/hd_multires_hidden_session.py` authenticates an exact selected bundle
before creating an isolated hidden desktop and owned process job. It implements
initial loaded-byte and natural-menu/acquisition diagnostics. Its map-idle and
map-pan routes first replay the canonical initial image. They then reach the
adventure map through the legacy hidden soak's disclosed debugger-forced route:
- fast-forwarded intro sleeps;
- bypassed DirectInput acquisition;
- forced main-menu and load-slot clicks;
- the canonical soak extra, including native arrow-key pans;
- skipped map drag-scroll starts after map entry.

The unacquired hidden mouse leaves stale button bytes, so the original drag
handler (`0x407B90`) sees a held button and scrolls the map by a page from a
far-left pointer, which the HD clamp then pins. After map entry every drag
start therefore takes the handler's own not-held exit (`0x407BC6`). The first
sixteen skips are logged with their flags, button bytes, pointer and scroll
position. The report counts those logged lines as `drag_scroll_skips` and
discloses `drag_scroll=cdb_forced_skip`; later skips are not logged.

Every breakpoint site of that route, and the main-menu, load-list and PlayGame
ranges, are byte-identical to the original in all 36 candidates. The host binds
map entry and the soak-ready surface to the adopted process and the selected
canvas, samples process telemetry on a fixed one-second grid and the surface
every 60 seconds,
and replays the whole retained log through the shared soak row grammar. The
route's duration is its 64 Hz system-tick delta, which the host clock
corroborates within polling jitter.

All thirty-two successor cells passed this 120 s map-idle route on a hidden
desktop; the compact receipt is
[`reports/hd-multires-hidden-map-20261103.json`](../../reports/hd-multires-hidden-map-20261103.json).
The receipt measures each run's final frame through its own palette:
- All 24 Framed, Complete HD and Modal Widgets cells show frame art along
  all four edges (at least 91% of each edge strip) and in the bottom-right
  action-bar corner (at least 74%).
- All eight Classic cells show only partial top and left border art, with
  black right and bottom edges and a black action-bar corner, which are the
  known proxy and frame-gutter limits.

These are `hidden_cdb_host` observations with `input_or_callback_forced` set.
The memory-only proxy's software surface can omit separately composed HUD
layers, so its frames are not visible composition, input or endurance
acceptance. The old Classic 800x600 runner is separate. A local Classic 1080p
hidden attempt observed a genuine mouse Acquire denial; its failed report is
retained as a diagnostic, not acceptance.

The menu-idle route stays observation-only by default. Its menu-ready
observation is the main-menu hit test at `+0x19b80`, which fires every frame
while the menu waits. The former `+0x47d61` anchor is a dispatch poll that only
runs after a menu choice.

On a hidden desktop the game never reaches its menu: the mouse Acquire is
denied (`0x80070005`) and the keyboard Acquire never follows. The opt-in
`--hidden-menu-entry` therefore fast-forwards the intro sleeps and applies the
map route's acquisition bypass. Both steps are disclosed in the report, and it
writes no input, clicks or menu state.

An idle menu stops locking its surface, so its frames are read from the
source-built proxy's single buffer for the live surface of that exact canvas
(`frame_source=proxy_surface_buffer`). A Classic 1024x768 run passed 120 s at
the centered native menu with one sample per second.

The proxy log is replayed in order to find that buffer. The game destroys and
recreates its canvas surface during start-up, and the heap can return the
same address. The earlier parser treated every destroyed address as dead, so
about half of the hidden menu runs timed out at a menu they had reached.
Only each address's latest creation and the Locks after it now count. The
two failed farm runs' retained logs (Classic 1024x768, Complete HD
2560x1440) both resolve to their live buffer under the fixed parser.

The first ordered short ladder passed for Framed 1920x1080 on a hidden desktop
(`reports/hd-multires-soak-ladder-framed-1920x1080-20261103.json`). Its five
rungs were a 120 s menu idle with the hidden menu entry, 120 s and 600 s map
idle, then 600 s and 1800 s map pan:
- Every map rung measured exactly 64 system ticks and one telemetry sample
  per second. The pan rungs made 59 and 179 native arrow pans.
- Peak growth was 312 KiB working set, 340 KiB private bytes and 3 handles,
  against the legacy 64 MiB, 64 MiB and 128-handle limits.
- Every map rung logged the sixteen-line drag-skip cap. Live saves stayed
  unchanged and owned-process cleanup was verified.

The matrix-cell release evaluation replays `short_soak_ladder` and
`resolution_coverage` as passing. The other fourteen lanes have no evidence,
so the cell fails. These remain forced-route hidden-host observations.

The ladder ran with the session producer before its continuity extension.
The replay pins the producer's exact bytes, so that receipt documents the
earlier producer; every soak lane must be collected again with the current
one.

### Hidden save/load continuity extra

A 120 s map-idle run can add one continuity extra from
`tools/hd_multires_route_extras.py` (`--route-extra`). The extras module and
each template it lists are pinned producer sources, so new extras never
change the session module. The session composes the extra after the soak
extra and rejects any reused breakpoint site; a second `bp` on one address
would silently replace the first.

`forced-save` loads `load_slot` through the forced route. At the first
world-map loop entry (`0x40B0C1`, before the first poll) it keeps EAX and EDX,
calls the native `saveGame` (`0x4443E0`) for `save_slot` and restores both
registers on return; `saveGame` preserves the others. The run discloses
`save=cdb_forced_save_game` and snapshots the loaded and saved isolated
slots before launch. Afterwards it requires the loaded slot unchanged and
the saved slot rewritten, and keeps a copy of the save in the run directory.
Slot 0 is never a save target. The map loop and `saveGame` are
byte-identical to the original in all 36 candidates.

The save format copies two process-local object pointers verbatim: the
trailing dword of 500 725-byte records at game data `+0x23EE6` and of 100
467-byte records at `+0x7C6EA`. Loading recreates them, so two saves of one
state differ there whenever the heap moves. The user's own slot 0, written
by the original game, holds such pointers in the same fields. The
save/load comparison zeroes only those 2,400 bytes
(`route_extras.POINTER_FIELDS`, derived from the bounds and fields the code
uses) and keeps the raw hashes.

On Framed 1920x1080 a forced save of slot 0 into slot 7, then a reload of
slot 7 saved into slot 8, both passed. Each `saveGame` returned 1. The
reload read exactly the first save's bytes. The two saves differ in 22
bytes, all inside those pointer fields, and have the same normalized state.
Against the source slot 0, the first save differs only in pointer fields
and its empty 16-byte name.

### Hidden forced day of turns

`forced-turn` is a second extra, so the session module is unchanged. At the
world-map loop site `0x40B0C8` it saves `before_slot`. It then calls the native
`nextPlayer` (`0x40AA60`) every 128 ticks until the day word (`gd+0x222F6`) has
advanced by one and player 0 is current again, then saves `after_slot`. There
are at most five calls. Each forced call keeps every general register and the
flags and restores them when the call returns with its ESP. Its state uses the
only header padding free in all 36 candidates (`0x4003C0`-`0x4003FF`); the
older day diagnostic's `0x400300` lies inside the section table of 18 HD
candidates.

The unacquired hidden mouse leaves stale button bytes. The day banner
(`0x40A943`) and its release wait treat them as clicks and held buttons. The
wait tests left (`0x4609E0`) every iteration and right (`0x4609FC`) only
when left reads released. It ends only when both read released in one
iteration. The banner is observed for eight polls and the wait for eight
iterations. Only then may the banner result, or in the eighth iteration each
held button's result, be overridden once, disclosed as
`turn_input=cdb_bounded_stale_button_result_overrides`.

On Framed 1920x1080 the run saved slot 5. Calls 1-3 returned players 1-3. Call
4 logged the native day increment 1 to 2, the banner and its release wait,
then returned player 0 on day 2. The run saved slot 6, and the map redrew to
its 120 s route end. The cycle took about 660 ticks. No result override was
needed; the banner's eighth test read the stale bytes as a click, which is
not input. Every nextPlayer, banner and release-wait site is byte-identical
to the original in all 36 candidates.

`forced-campaign` continues the same calls through two or three consecutive
days before its after-save. On Framed 1920x1080 a three-day campaign returned
the day word 1 to 4 in 12 calls, each day back at player 0. Days 3 and 4 each
needed one disclosed right-release override in the eighth iteration, and both
saves returned 1. A forced save then reloaded the campaign's end slot. Its
resave had the same normalized state.

### Neutralized failed mouse reads

On a hidden desktop every mouse `GetDeviceState` fails (`8007000C`, not
acquired). The game still copies its 16-byte stack buffer into the mouse state
(`0x47C03C`-`0x47C062`), so stale stack bytes become motion and held buttons:
- phantom drag starts, which the drag-scroll skip handles;
- banner acknowledgments and endless release waits;
- a cursor that drifts anywhere on the HD canvas.

In a farm of continuity runs this hung two reloads and ended two campaigns
(Complete HD 2560x1440, Modal Widgets 3440x1440) with an access violation in
the unchecked native `GetPixel` (`0x403F50`). That read used native
coordinates (-956, -240) on a 640-wide surface.

A continuity extra can request `neutral_mouse: true`. A failed read's buffer
is then zeroed at the call's return (`0x47C02C`, byte-identical in all 36
candidates), reporting no motion and no buttons, as for an idle player.
Successful reads are untouched. The run discloses
`mouse_state=cdb_neutral_failed_mouse_reads` and logs its first four
neutralized reads; the replay requires them. The turn and campaign lanes use
it, so each day's banner now always needs its one disclosed acknowledgment
and the release wait returns on its first test. Requests without the key keep
their exact spec, so the save/load round trip is unchanged.

With it, a three-day Complete HD 2560x1440 campaign and its end-state reload
both passed, with no access violation. Whether a real cursor far outside a
centered native screen can reach the same unchecked read remains an open
question for a targeted diagnostic.
`tools/hd_multires_visible_session.py` can prepare a specific Classic 1080p
five-minute acquisition/menu plan. Execution requires a fresh approval bound to
the exact plan, sources, candidate, assets and scope. It injects no input.

Each cell still requires real map/controls, castle and building routes, battle
entry/command/return, save/load and turn continuity, final-wrapper composition,
five genuine manual-input categories and the ordered endurance schedule.
The existing schedule is 54 minutes of short rungs, then two hours map-idle
and two hours map-pan: **4h54 per cell, 156h48 for the thirty-two successor cells**, before setup,
failed attempts and other observations. Visible/manual sessions require
specific approval under the repository rules.

## Local packaging check

```powershell
powershell -NoProfile -File scripts/launcher/build_launcher_exe.ps1 -Python C:/path/to/python.exe -OutputDir C:/ClashTests/launcher/build -Execute
ClashHDLauncher.exe --package-selftest C:/ClashTests/package-selftest.json
```

The self-test opens neither the GUI nor game. It records four source preflights,
thirty-two plans, thirty-two temporary settings roundtrips, defaults and false
runtime/input acceptance flags. It never reads or changes the user's saved
launcher settings. The build
checks its inputs before and after compilation. Any packaged-source change
requires a new executable and clean-folder verification.

The standalone restart receipt
[`reports/hd-multires-standalone-restart-20261103.json`](../../reports/hd-multires-standalone-restart-20261103.json)
records one build of commit `fb8672ba` and its package self-test with thirty-two
plans and settings roundtrips. Each of the thirty-two cells was prepared by two
separate launcher processes (64 in total), started from two clean folders
without Python on PATH. Each process ran on its own hidden desktop with its own
one-file extraction directory.
Every cell's executable, metadata and probe were byte-identical across both
runs and equal to the bundle that `tools/hd_multires_qualification.py`
prepared and authenticated; the original executable was unchanged. The first
twelve cells keep the executables and probes of the earlier
[twelve-cell receipt](../../reports/hd-multires-standalone-restart-20261102.json);
only their metadata source hashes moved with the two batch-2 builders. This is
construction and restart determinism only: no game, GUI, input, rendering or
release acceptance.

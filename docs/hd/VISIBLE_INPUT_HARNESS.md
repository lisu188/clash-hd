# Visible input harness

`scripts/smoke/run_clash_visual_smoke.ps1` requires fresh explicit approval
through its existing `-AllowVisibleRuntime` boundary. Repository fixtures do
not execute the game, capture the desktop, change foreground windows or inject
input. No repaired runtime result is established by these source changes.
Raw captures default to `C:\ClashCaptures\visible-input`, with a unique
directory for each run. The harness refuses an output root inside this
repository.

## Resolution and automated input

Supply `-Resolution WxH` matching the actual patched candidate and `-Stage`
for its exact producer stage. Resolution syntax and bounds come from the
patcher. The stage is recorded metadata; this harness does not authenticate
the candidate's patch bytes or grant release eligibility.

The default `-InputMode pulse` forwards the logical resolution to
`tools/menu_pulse_click.py --resolution`. Feedback is normalized to the
requested logical surface, retaining original pixels when client and logical
dimensions match. A differently shaped client is rejected because a
letterboxed content rectangle cannot be inferred safely. The default main-menu
Load target follows native 640x480 centering; load-list and confirmation
coordinates retain their existing native input space. Explicit
`-PulseRouteSteps` and `-FollowupPoints` are interpreted literally in the
requested logical input space. The historical `legacy` mode remains limited to 800x600.

Before automated aiming, the tool measures monitor bounds, outer-window bounds
and client origin. It moves an offscreen client by its measured nonclient
offset without resizing it, and refuses a client larger than its monitor.
Every aim iteration and final click checks foreground state and ownership at
the actual target point. A cached window handle must still belong to the
selected process. A recreated or occluded window can fail that second
check even after cursor convergence. Such a run cannot report a completed click.

Pulse feedback, frame transitions and the generic gameplay-image heuristic are
diagnostics. They do not establish native callback success, complete rendering,
manual DirectInput or final release acceptance.

For framed and `completehd` stages, the generic gameplay-image quality check
returns `Status=incomplete` and `GameplayFrameLikely=false`. That path still
needs the shared candidate context and observed minimap state before it can
use the framed coverage contract. Input diagnostics and capture collection
remain available; they cannot reuse the older unframed grid as a quality pass.

## Human-operated observation

Use `-InputMode manual -RunSeconds 60` to allow a person to operate the game
while paired client screenshots are recorded. The mode launches the selected
candidate by default. Add `-ObserveProcessId <process id>` to observe an
already running instance; its actual executable path must exactly match `-Exe`.
The harness does not stop an attached process.

This branch calls `menu_pulse_click.py --observe-only`, which performs no
foreground activation, window placement, cursor movement, click or key
injection. The operator must make the game visible and accessible. The
observer checks the client corners and center before each capture, retains
original client-size PNGs, records file hashes and measured geometry, and
applies the advisory `capture_tear_check.py` analysis to each pair. The
configured interval is a minimum between completed pairs; capture and analysis
time can make observations less frequent.

`CaptureComplete` describes collection only. Results retain
`ManualInputAccepted=false`, `PromotionReady=false`, and pending operator
observations. Actual human observations and callback evidence must be supplied
separately to the release proof workflow. Screen pairs cannot prove who moved
the mouse, and a nonsuspect tear heuristic is not proof of a tear-free frame.

The harness stops only its selected candidate when it owns that process;
unrelated game instances and debuggers are outside its cleanup scope.

## Offline verification

Run `python -B tools/test_visible_input_harness.py`. These fixtures cover
resolution transforms, measured placement, point ownership, refusal after
window recreation, observation without input/focus, PowerShell parsing,
candidate-specific cleanup and the actual manual branch with mocked tools.

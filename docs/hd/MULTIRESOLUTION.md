# Multiresolution display contracts

## Shared plan

`src/display_plan.py` resolves Classic and Framed requests through their actual
existing patch recipes. It accepts canonical ASCII resolution names, applies
the launcher policy envelope, then checks the selected recipe even at 800x600.
A resolution preset is not a substitute for successful recipe selection.
No patch tables, emitted x86, source pins, game files, or promotion decisions
are modified by the planner.

Classic delegates to the frozen patcher and retains its full-grid rectangle:
800x600 has 12x9 full tiles at inclusive (32,16)..(799,591). Framed delegates
to `FramedViewport` and the source-authenticated framed scalar recipe:
800x600 has 11x8 full tiles and 12x9 ceiling coverage at (32,16)..(767,583).
Framed controls and frame bands come from that authority, not copied formulas.
The `scalar_patch_sha256` authenticates selected old/new byte records and their
order; a plan is not an executable build or a full injected-payload byte gate.

Default policy bounds are 800x600 through 3840x2160, with even dimensions.
Callers may provide stricter policy bounds. The original patcher's instruction
encoding and recipe constraints always apply. Non-tile-aligned dimensions
such as 1366x768 and 802x602 remain eligible when their actual recipes succeed.
Only the already verified integer wrapper scaling setting is selectable.

The JSON form records immutable geometry, profile, recipe revision, feature
options, and a deterministic scalar recipe digest. Candidate-build, runtime,
manual-input and promotion fields remain false. Profile and resolution labels
must be resolved separately from evidence; this module promotes nothing.

## Configuration identity

`DisplayPlan.build_identity(original_sha256, sources)` binds the original,
profile, render resolution, selected byte recipe, geometry, feature options,
and repository-relative source hashes. Source order and checkout location do
not influence the identity. Presentation scaling is deliberately excluded.
`deployment_identity(build_id, wrapper_sha256, config_sha256)` binds the
resulting build to the actual wrapper and generated configuration. A timestamp
is not an identity, and a build identity is not a runtime-validation result.
These helpers do not move or rewrite existing candidate directories.

## World bounds and camera

`world_view()` bounds world dimensions to the native 1..100 tile backing and
clamps a requested camera to the current full-tile limits before calculating
cell membership. It explicitly distinguishes inside-world cells from complete
or partial regions that require clearing. The input geometry helper rejects
frame pixels, supplied overlay rectangles, and outside-world tails.

A valid small-world plan does **not** permit the native full renderer to run.
`require_native_full_loop()` rejects a world smaller than the full viewport.
The installed framed emitter retains its existing small-world guard. A native
bounded small-world drawing path, first-redraw camera hook, and callback/input
integration remain separate work; none is installed by these pure helpers.

## Presentation and surface utilities

`PresentationTransform` maps a caller-supplied, observed content rectangle into
render pixels. The rectangle origin can be signed for a multi-monitor desktop.
The caller must use one consistent coordinate space and account for Windows
DPI virtualization before supplying positions; these utilities do not query
windows or change process awareness. Letterbox clicks are rejected, not clamped.
Integer fitting changes presentation size without changing internal resolution.
The observed-rectangle mapping also handles fractional sizes, but does not add
an unverified fractional scaling setting to a wrapper configuration.

Relative samples preserve signed fractional remainders. Only use this helper
at an adapter boundary where the device units are known, and reset remainders
when the presentation geometry changes. It is not wired into native DirectInput
and must not be applied twice by a wrapper and a game hook.

`SurfaceLayout` validates positive or negative pitch, backing extent and
inclusive copy rectangles without creating a native pointer. For negative
pitch its offsets are relative to the **lowest-address byte of the allocation**;
row zero is the last physical row. It must not be used directly as an offset
from a native row-zero pointer without that explicit conversion. It uses the
reported byte pitch rather than assuming tightly packed scan lines.

Reference: Microsoft `DDSURFACEDESC2.lPitch` specifies the byte distance between
adjacent scan-line starts:
https://learn.microsoft.com/en-us/windows/win32/api/ddraw/ns-ddraw-ddsurfacedesc2

## Validation boundary

```powershell
python tools/test_display_plan.py -v
```

Tests combine independent synthetic geometry/input/stride oracles with real
repository recipe integration. The workflow rejects skipped contract tests;
local execution without the full source checkout explicitly skips integration
cases rather than substituting mocked source bytes. No test launches the game,
loads a wrapper, starts CDB, manipulates a desktop, or constructs a retail
candidate. Tests requiring original assets in the existing framed suite retain
their separate coverage and approval boundaries.

Runtime qualification, per-screen coordinate adapters, live DPI handling,
surface-restoration hooks, and bounded small-world native drawing remain open.
Render resolution is intended to be selected for the next launch, not changed
inside an already running process.

## Launcher integration

GUI and CLI now resolve every selected profile, stage and resolution through
the shared planner. The old default-resolution bypass is removed. The Classic
800x600 patch recipe and binary output remain unchanged. Diagnostic stages
that do not include the full stable-map patch set explicitly report
`map_geometry_available=false`; their numeric planning fields do not establish
a working expanded map, and world planning is rejected for those stages.

The GUI displays next-launch terrain dimensions, full/ceiling tile counts and
the minimum world size required by the current native full renderer. Each
resolution is evaluated against the selected profile; unbuildable choices are
disabled with a reason. Custom sizes share the same validation as CLI requests.
Saved game/candidate directory settings are honored by planning and environment
checks. Changing resolution updates only the next-launch plan, not a running
game or the wrapper's live display mode.

List profile-scoped eligibility without installed game files or a process scan:

```powershell
python src/launcher/run.py --profile framed --list-resolutions
```

Inspect a requested custom resolution, also without game files or writes:

```powershell
python src/launcher/run.py --profile framed --resolution 1366x768 --describe-plan
```

Geometry inspection reports requested game/candidate paths as unvalidated
metadata. It does not resolve Windows deployment paths on a Linux host or
construct a candidate plan. Use `--dry-run` for host-specific path validation;
preparation and launch retain their existing path guards.

Inspect a supplied world size and a hypothetical presentation area:

```powershell
python src/launcher/run.py --profile framed --resolution 1280x720 --describe-plan --map-size 60 60 --client-size 2560 1600
```

This reports a 1280x720 internal surface and a 2560x1440 image rectangle at
client offset (0,80). `--client-size` is not a window-size request, and
`--map-size` is not extracted from a save. Both arguments require
`--describe-plan`, are clearly labeled inspection-only, and cannot accompany
a preparation or launch. A supplied small world returns an incompatible result
and nonzero exit status; no native guard is bypassed.

Prepare through the existing opt-in source-tree Framed path:

```powershell
python src/launcher/run.py --profile framed --resolution 1366x768 --prepare
```

Preparation still requires the verified local original. No game is started,
and no display-resolution, DPI or input API is invoked by inspection.

## Profile registry and candidate metadata

`src/launcher/resolutions.json` uses schema 2 with separate Classic/Framed
recipe revisions, feature configurations, defaults and evidence scopes. The
legacy top-level fields remain an exact Classic compatibility projection; the
reader rejects mismatches rather than silently selecting one copy. Schema 1
files are still readable. Their historical status applies only to Classic,
never to the derived experimental Framed profile.

The registry includes 1366x768, 2560x1440, 3440x1440 and 3840x2160 as
experimental presets alongside the existing choices. Classic 800x600 retains
its original three evidence references. No new runtime evidence or promoted
resolution is added. `resolution_info()` reports recipe eligibility separately
from status and leaves `runtime_evidence_verified=false`; it does not reopen
or reinterpret the referenced runtime captures.

Preparation manifests include the resolved display plan and deterministic
`build_id`. Classic binds its exact generated scalar byte records and original
executable identity; Framed binds the reviewed builder plus all existing
implementation source identities. Successful wrapper deployment adds a
`deployment_id` covering the build, actual copied wrapper and configuration
bytes. Framed launch verification rejects missing or mismatched display, build
or deployment identity along with the existing artifact/source checks.

Existing candidate directories and build report/probe bytes are preserved.
Prepare regenerates the deployment manifest for a previously prepared candidate;
identical executable/report/probe artifacts can still be reused. The identities
are manifest fields in this implementation, not a content-addressed directory
migration or a new concurrent-build locking protocol. Classic process-start
behavior and its byte gate remain unchanged.

Additional source-only integration tests:

```powershell
python tools/test_launcher_multiresolution.py -v
```

The multiresolution workflow requires both display-contract and new launcher
integration suites to execute without skips on Linux and Windows. Candidate
build/deploy tests use explicitly synthetic bytes and the existing mocked
Framed builder; they are not retail executable construction or gameplay proof.

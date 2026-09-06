# Experimental framed launcher profile

The source-tree launcher offers two renderer profiles. **Classic** remains the
default and uses the existing stages and resolution registry without changes.
**Framed + minimap correction** uses the reviewed four-sided-frame candidate
builder with `minimap_viewport=True`. It is experimental at every resolution,
including 800x600; selecting it does not promote any resolution or patch stage.

Open `python src/launcher/run.py` and select the renderer profile before Play.
The GUI relabels all resolution badges as Experimental for the framed profile
and requests confirmation before preparing and launching it. Profile choice is
session-only: a subsequent ordinary launcher invocation returns to Classic.
Use `python src/launcher/run.py --profile framed` to initially select Framed.
The source-profile choice does not silently change saved Classic defaults.

## Prepare without playing

From the repository root, inspect paths and source verification without creating
candidate files:

```powershell
python src/launcher/run.py --profile framed --resolution 1280x720 --dry-run
```

Create the candidate, its source-bound build report and debugger probe, then
copy the user-owned wrapper and generate its configuration without starting
any game process:

```powershell
python src/launcher/run.py --profile framed --resolution 1280x720 --prepare
```

`--prepare` also works for Classic. It never starts the game, even when
`--yes-launch` is present. It cannot be combined with `--launch` or `--dry-run`.
Preparation may succeed without a wrapper; its result then explicitly says
`runtime_deployed=false`. A missing wrapper still blocks Play and CLI launch.

Starting a visible game requires the existing explicit double flag:

```powershell
python src/launcher/run.py --profile framed --resolution 1280x720 --launch --yes-launch
```

The experimental profile cannot be combined with an unrelated `--stage`.
Resolution constraints remain owned by the patcher. Canonical spelling such
as `1280x720` is required. The framed profile is intentionally unavailable in
a packaged/frozen launcher because it requires authenticated source files;
Classic packaging remains unchanged.

## Isolation and provenance

Default framed output directory:

```text
C:\ClashTests\launcher\framed-minimap\1280x720\
```

Classic keeps its existing `C:\ClashTests\launcher\1280x720\` directory.
Cleaning the selected framed candidate does not remove the Classic candidate.

The framed directory contains the candidate executable, `framed-build.json`,
`framed-probe.cdb`, the user's copied `ddraw.dll`, generated `dxcfg.ini`, and
`candidate-manifest.json`. No binary, proprietary asset, or runtime capture is
added to the repository or fetched from the network. The original executable
is read and verified, never overwritten. The probe is saved, not executed.

Preparation verifies the existing 14 implementation source hashes plus the
reviewed builder hash before building. It validates builder metadata against
the requested stage, resolution, minimap option, source hashes, and output
SHA-256. It exclusively creates new artifacts and refuses to overwrite differing
ones. Repeated preparation reuses byte-identical files; the deterministic local
build report omits only the builder's variable generation timestamp. Deployment
retains its own timestamp in the candidate manifest.

Before a framed launch, the launcher rechecks the original, source identities,
profile manifest, and hashes of the executable, build report, probe, wrapper,
and configuration. Changed or missing artifacts block launch; prepare again
or clean only the selected experimental profile rather than overriding checks.
All process starts remain in the existing GUI/CLI/core launch paths. The new
profile module has no process-start operation.

## Evidence boundary

The builder recipe covers guarded ordinary maps and AI banners. Unsupported
modal and army screens retain native fallback. This integration does not prove
runtime rendering, transitions, manual input, or continuity at 1280x720.
Preparation records `game_runtime_executed=false`, `manual_input_proof=false`,
and `promotion_ready=false`. A Play action is not itself accepted test evidence.

Run source-only launcher regression tests with:

```powershell
python tools/test_launcher_framed.py
python tools/launcher_policy_guard.py --require-pass
```

The new tests use explicitly synthetic non-game bytes and mock the binary
builder/process starter. The source-preflight case checks the actual repository
pins. Existing renderer fixtures and asset-dependent skips remain separate.

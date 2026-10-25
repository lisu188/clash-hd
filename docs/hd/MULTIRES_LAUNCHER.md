# Experimental 1080p, 1440p and 4K launcher

The standalone Windows launcher now contains Classic, Framed, Complete HD and
Modal Widgets. Its first multi-resolution batch is 1920x1080, 2560x1440 and
3840x2160: twelve independent profile/resolution combinations. Every new
combination remains **experimental**. Classic 800x600 remains the stable default.

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

These are installed source/byte capabilities. They are not fresh native input,
screen composition, save/load or endurance acceptance.

## Verification and remaining acceptance

The public source/CPU tests use authored synthetic memory and callbacks. An
optional local lane constructs all twelve candidates from the exact user-owned
original without executing the game:

```powershell
python -B tools/test_hd_multires_candidate.py --original-backed C:/Clash/clash95.exe
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

Each cell still requires real map/controls, castle and building routes, battle
entry/command/return, save/load and turn continuity, final-wrapper composition,
five genuine manual-input categories and the ordered endurance schedule.
The existing schedule is 54 minutes of short rungs, then two hours map-idle
and two hours map-pan: **4h54 per cell, 58h48 for twelve cells**, before setup,
failed attempts and other observations. Visible/manual sessions require
specific approval under the repository rules.

## Local packaging check

```powershell
powershell -NoProfile -File scripts/launcher/build_launcher_exe.ps1 -Python C:/path/to/python.exe -OutputDir C:/ClashTests/launcher/build -Execute
ClashHDLauncher.exe --package-selftest C:/ClashTests/package-selftest.json
```

The self-test opens neither the GUI nor game. It records four source preflights,
twelve plans, defaults and false runtime/input acceptance flags. The build
checks its inputs before and after compilation. Any packaged-source change
requires a new executable and clean-folder verification.

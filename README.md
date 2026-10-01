# Clash95 HD

Independent, unofficial binary patcher and launcher for the 32-bit Windows game
`clash95.exe`. The project modifies a **user-supplied local copy** to support
larger render resolutions, expanded gameplay viewports, anchored UI, and related
input transforms.

This repository contains patcher source, launcher code, tests, scripts,
documentation, and minimal patch metadata. It does **not** distribute the
original or patched game executable, wrapper DLL binaries, saves, game assets,
manuals, runtime captures, debugger dumps, decompiler/disassembler exports,
CD/ISO content, or cracks.

## Start here

| Goal | Entry point |
| --- | --- |
| Use the launcher | [Launcher guide](docs/hd/LAUNCHER.md) |
| Set up a checkout and run source-only checks | [Development and verification](docs/hd/DEVELOPMENT.md) |
| Find engineering documentation | [Documentation index](docs/hd/README.md) |
| Review contributor boundaries | [AGENTS.md](AGENTS.md) |

## Inspect without game files

Use Python 3.12. These commands do not require the game and do not launch it:

```powershell
python -B src/launcher/run.py --list-resolutions
python -B src/launcher/run.py --profile completehd --resolution 1920x1080 --describe-plan
python -B patch_clash95_hd.py --help
python -B tools/check-public-boundary.py
```

## Patch your own copy

With your own lawfully obtained installation, open the launcher:

```powershell
python -B src/launcher/run.py
```

The game starts only after an explicit **Play** action or the CLI combination
`--launch --yes-launch`. Generated candidates belong outside the repository,
for example under `C:\ClashTests\`. The original executable must never be
overwritten.

The currently supported reference executable is identified by SHA-256:

```text
500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae
```

This hash is an identifier only; the executable is not supplied by this
repository.

## Public validation boundary

Public CI and source control are source-only. Runtime checks that require the
original game, proprietary assets, native captures, debuggers, or rendered game
screens must be performed locally against a user-owned copy. Their raw outputs
must stay outside the repository.

Minimal file offsets, expected-byte signatures, and patch bytes required for the
patcher to operate remain part of the source. Raw disassembly, decompiler output,
function-inventory exports, screenshots, and runtime dumps are not public
project inputs.

## Legal scope

This project is independent and unofficial. It is not affiliated with,
endorsed by, or sponsored by the original game's developers, publishers, or
rightsholders. "Clash" is used only to identify compatibility.

No license to the original game, executable, artwork, audio, manuals,
trademarks, or other third-party material is granted by this repository. See
[NOTICE](NOTICE.md).

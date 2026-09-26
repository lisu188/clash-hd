# Clash95 HD

Reverse-engineering and binary-patching project for the 32-bit Windows game
`clash95.exe`. It extends the original 640x480 renderer, expands the adventure
viewport, anchors the interface, and checks input and rendering through
source-bound evidence.

The repository contains source, patch scripts, a launcher, tests, probes and
small evidence manifests. It does not distribute game executables, wrapper
DLL binaries, saves, copied assets, CD/ISO contents, cracks or memory dumps.

<a id="documentation"></a>
<a id="project-layout"></a>

## Start here

| Goal | Entry point |
| --- | --- |
| Choose a Clash project | [Clash project overview](https://github.com/lisu188/clash-disassembly/blob/main/docs/CLASH_PROJECTS.md) |
| Use the launcher | [Launcher guide](docs/hd/LAUNCHER.md) |
| Set up a checkout and run checks | [Development and verification](docs/hd/DEVELOPMENT.md) |
| Find engineering documentation | [Documentation index](docs/hd/README.md) |
| Continue implementation or validation | [Current handoff](docs/hd/AGENT_HANDOFF.md) and [operating rules](AGENTS.md) |

Related repositories are [clash-disassembly](https://github.com/lisu188/clash-disassembly)
for recovered engine source and [clash-save-editor](https://github.com/lisu188/clash-save-editor)
for save inspection and editing. The separate
[clash-assets repository](https://github.com/lisu188/clash-assets) catalogs
original reference/runtime artifacts; it is not a build prerequisite for the
source-only documentation checks here.

## Current scope

Classic at 800x600 remains the default and the sole stable launcher entry.
Other Classic resolutions and all Framed, Complete HD and Modal widgets HD
resolutions remain experimental. The launcher reads the profile-specific
statuses from [resolutions.json](src/launcher/resolutions.json); a component
test or a successful build does not promote a profile.

The protected stable stage is:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch
```

Complete HD expands the adventure map/HUD while keeping native menu, castle and
battle layouts. Expanded tactical battle is a separate validation lane. The
[current handoff](docs/hd/AGENT_HANDOFF.md#evidence-snapshot-and-active-work)
records the latest integration work, failed ordinary-input observations,
pending release evidence and availability of historical raw artifacts.

<a id="launcher"></a>
<a id="patcher"></a>

## Inspect or launch

Use Python 3.12, matching CI. Run commands from the repository root; the
[setup guide](docs/hd/DEVELOPMENT.md) covers interpreter discovery and optional
image-test dependencies. These commands need no game files and open no windows:

```powershell
python -B src/launcher/run.py --list-resolutions
python -B src/launcher/run.py --profile completehd --resolution 1920x1080 --describe-plan
python -B patch_clash95_hd.py --help
```

With Python/Tkinter and your own game installed, open the launcher:

```powershell
python -B src/launcher/run.py
```

The game starts only after an explicit Play action, or the CLI combination
`--launch --yes-launch`. [The launcher guide](docs/hd/LAUNCHER.md) explains
preparation, profiles, local build paths and wrapper requirements.

<a id="known-good-input"></a>

The expected original `C:\Clash\clash95.exe` has SHA-256:

```text
500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae
```

Never overwrite it. Generated candidates belong outside the repository under
`C:\ClashTests\...`; every patch must verify the input SHA and old bytes.

<a id="repo-only-validation"></a>

## Verify changes

For documentation changes, run the focused fixtures:

```powershell
python -B tools/test_handoff_freshness_guard.py
python -B tools/test_docs_consistency_guard.py
```

[Development and verification](docs/hd/DEVELOPMENT.md) distinguishes these
checks from image fixtures, native CPU fixtures, runtime checks and the
evidence-writing aggregate refresh. Saved `captures/current` reports have their
own dates and source identities; the directory name is not a freshness claim.

<a id="runtime-evidence"></a>
<a id="safety-and-contribution-rules"></a>

Hidden software surfaces, final wrapper composition, ordinary/manual input,
endurance and stable promotion are separate claims. Keep failed or incomplete
evidence intact. Visible/manual runtime requires fresh explicit approval under
[AGENTS.md](AGENTS.md); repository checks do not launch the game.

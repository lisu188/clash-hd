# HD documentation index

Public documentation describes the patcher, launcher, source-only validation,
and the procedure for running optional local compatibility checks against a
user-supplied game copy. Runtime captures and reverse-engineering exports are
not part of the public repository.

## Entry points

| Document | Purpose |
| --- | --- |
| [Root README](../../README.md) | Public scope, launcher entry point and repository boundary |
| [AGENTS.md](../../AGENTS.md) | Contributor rules and local/runtime boundaries |
| [Working with this repo](WORKING_WITH_THIS_REPO.md) | Short operating guide |
| [Development and verification](DEVELOPMENT.md) | Python setup and source-only checks |
| [Launcher](LAUNCHER.md) | User workflow, profiles and local candidate preparation |
| [Resolution release matrix](RESOLUTION_RELEASE_MATRIX.md) | Resolution support and validation status |
| [Release runbook](FINISH_LINE_RUNBOOK.md) | Local candidate/release requirements |

## Engineering guides

Implementation guides under this directory document rendering, input,
resolution, launcher, and patching work. Some historical notes describe local
runtime observations that are no longer retained as public capture artifacts.
Treat such references as historical descriptions, not as downloadable evidence.

For new public claims, prefer reproducible source tests and concise patch
metadata. For runtime claims, record results locally without committing
screenshots, dumps, executable-derived fixture bundles, or proprietary files.

## Repository evidence policy

Public source control may contain the minimal offsets, old-byte signatures,
new-byte sequences, and structural facts necessary to apply and validate a
patch. It must not contain:

- original or patched executable files;
- game assets, saves, manuals, audio, video, or CD/ISO data;
- screenshots or raw captures of the retail game;
- debugger/memory dumps;
- Ghidra/IDA/decompiler exports or generated source reconstructions.

See [Development and verification](DEVELOPMENT.md) and [NOTICE](../../NOTICE.md).

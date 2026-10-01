# Public project handoff

This file intentionally contains only source-level project state.

## Public repository state

- The repository contains independently authored patcher/launcher source,
  source-only tests, documentation, and minimal patch metadata.
- Original or patched executables, retail assets, saves, screenshots, runtime
  captures, debugger dumps, decompiler output, and disassembler exports are not
  public project artifacts.
- Public CI must not download or reconstruct the original game from another
  repository.
- Runtime validation is performed locally against a user-supplied lawful copy
  and its raw evidence remains outside source control.

## Stable public entry points

- [README](../../README.md)
- [Development and verification](DEVELOPMENT.md)
- [Launcher](LAUNCHER.md)
- [Resolution release matrix](RESOLUTION_RELEASE_MATRIX.md)
- [Release runbook](FINISH_LINE_RUNBOOK.md)
- [Contributor rules](../../AGENTS.md)

## Engineering state

The source tree remains the authority for implemented patch stages and
resolution behavior. `src/launcher/resolutions.json` is the user-facing
resolution registry. The patcher must verify the expected input executable
identity and old bytes before applying changes.

Historical runtime experiments, screenshots, raw debugger sessions, and
workstation-specific evidence that formerly accompanied this project are not
part of the public repository. Do not recreate them in public source control.

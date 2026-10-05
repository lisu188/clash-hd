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

The four all-preset source constructors are
[`classic_all_presets_candidate.py`](../../src/patcher/classic_all_presets_candidate.py),
[`framed_all_presets_candidate.py`](../../src/patcher/framed_all_presets_candidate.py),
[`complete_hd_all_presets_candidate.py`](../../src/patcher/complete_hd_all_presets_candidate.py)
and [`modal_widgets_all_presets_candidate.py`](../../src/patcher/modal_widgets_all_presets_candidate.py).
Classic retains the actual scalar predecessor at 800x600 and 1024x768, and the
menu-widget predecessor at the seven wider presets. Framed retains its inset
four-border map/minimap and native modal fallback; it borrows no owned-modal
bytes from the other profiles.
The Modal Widgets successor carries the full owned slots, primary surface,
text and widget chain across the nine canonical presets. All use separate
validation identities and retain the frozen recipes. They do not install the
expanded-battle successor or change launcher defaults or stable status.

The matrix can authenticate these fixed source recipes separately from the
launcher-resolved recipes. Unadvertised presets, missing production verifiers
and missing expanded-battle evidence remain failures. The complete target is
all four profiles at all nine presets, with actual functional, composition,
human-input, continuity and endurance evidence on each final candidate. See
[the matrix contract](RESOLUTION_RELEASE_MATRIX.md) for the acceptance scope.

[`ordinary_map_read_replay.py`](../../tools/ordinary_map_read_replay.py) can
retain and replay every bounded ordinary-map read, including rereads and lease
checkpoints. Its context must come from the owning authenticated runtime host;
an artifact's own hashes and passing report flags cannot substitute. Successful
offline replay establishes recorded-byte consistency only. It keeps live lease,
native/manual input, full geometry, release and promotion claims false. Raw
records and failed-read diagnostics belong outside source control.
The hidden diagnostic can opt in with `--retain-raw-observations` only on an
independently reconstructed `--prepared-matrix-candidate` or
`--prepared-small-world-candidate` bundle. Legacy launcher hash receipts remain
outside this raw-retention path. See [Development](DEVELOPMENT.md) for its disk
allowance and evidence limits.

Use the public boundary and cloud checks before focused source fixtures:

```powershell
python -B tools/check-public-boundary.py
python -B tools/cloud_check.py --mode cloud
python -B tools/test_classic_all_presets_candidate.py
python -B tools/test_framed_all_presets_candidate.py
python -B tools/test_modal_widgets_all_presets_candidate.py
python -B tools/test_resolution_release_matrix.py
python -B tools/test_ordinary_map_read_replay.py
```

The optional original-backed constructor lane builds only in memory from a
user-supplied local executable. It supplies no runtime, loader, screenshot,
manual-input or promotion evidence. Keep every candidate bundle, runtime log
and capture outside the repository and preserve the disk reserve before use.

Historical runtime experiments, screenshots, raw debugger sessions, and
workstation-specific evidence that formerly accompanied this project are not
part of the public repository. Do not recreate them in public source control.

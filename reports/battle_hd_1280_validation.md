# Expanded tactical battle: 1280x720 validation

The new `-castlecenter-all-battlehd` suffix selects an expanded tactical battle
lane. It accepts only `1280x720`; the existing centered battle stages and the
800x600 stable default remain unchanged. This lane is not promoted.

## Layout and implementation

- Battlefield capacity: 17 columns by 7 rows of native 64-pixel tiles, in the
  half-open rectangle `(32,136)-(1120,584)`.
- Original right sidebar: `(1120,120)-(1280,600)`. Six command descriptors,
  stats, hover tests, animation destinations, banners and dialogs follow the
  displayed coordinates. Border strips repeat across the widened frame.
- The shared results message is scoped at its battle call site. Its original
  640-pixel width is retained; artwork, text, capture and restoration share a
  centered origin. Other users of that shared message keep native placement.
- Arena data, combat rules and saves remain native. Render only real cells;
  short maps leave cleared, noninteractive slots. Horizontal camera range is
  `0..max(0, arena_columns-17)` and vertical camera position remains zero.
- `src/patcher/battle_hd_layout.py` is the geometry contract. The separate
  core/HUD modules contain original-byte records and assembly with its exact
  generated encodings. Production patching requires only the Python standard
  library. Keystone and Unicorn are optional development verification tools.
- The `.btlhd` section is appended at original EOF `0x12CE00`, maps at
  VA `0x562000` / RVA `0x162000`, and reserves 64 KiB. The original SHA, file
  size, zero section-header slot, every old instruction, and nonoverlapping
  patch/code ranges are checked. This stage never accepts unknown-SHA input.
- Battle teardown clears both shared HD surfaces before the native map graphics
  reload. The first complete hidden lifecycle exposed old sidebar pixels in the
  map's right gutter; a fresh map baseline and the subsequent hidden rerun
  confirmed that clearing removes them without changing map geometry.

## Reproduce a candidate without launching

```powershell
$stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd'
python patch_clash95_hd.py --input C:\Clash\clash95.exe --output C:\ClashTests\battle-hd-1280x720\clash95_battlehd.exe --stage $stage --resolution 1280x720
python src/launcher/run.py --dry-run --stage $stage --resolution 1280x720
```

Use a unique candidate filename; the patcher refuses an existing output by
default. Launcher defaults and resolution statuses are not changed.

## Checks and evidence classes

Repo-only fixtures are `tools/test_battle_hd_patch.py`,
`tools/test_battle_hd_core.py`, `tools/test_battle_hd_hud.py`, and
`tools/test_battle_hd_summary.py`. Core/HUD tests accept explicit
`--toolchain-path`, `--source-exe`, and `--require-machine-tools` for additional
assembly reproduction and actual x86 emulator checks. They never execute the
game. Default fixtures do not require a game installation.

The independent `tools/battle_hd_summary.py` binds each log to a run manifest
and patch-stage report by SHA, stage, resolution and wrapper. Owner visits,
forced helper diagnostics, route/action proof, software rendering, visible
composition and lifecycle completion are distinct claims. A forced helper
result is not manual input or a completed battle route.

The tracked `clash95_battle_hd_validation_extra.cdb`,
`clash95_battle_hd_camera_fixture_extra.cdb`, and
`clash95_battle_hd_lifecycle_extra.cdb` probes separate full/dirty rendering,
camera fixtures, and the actual results/return control flow. They explicitly
label debugger changes to unit placement, arena dimensions, input state and
callback dispatch. They do not inject OS input or write save commands.

The hidden surface-dump harness now accepts `-Resolution`. Its main-menu
injection follows relocated descriptors; load-list injection remains native
because that stock helper directly compares native coordinates. Use
`-FastForwardStartAnims` to preserve resource initialization. The default blunt
startup skip reproduced the known `00487CF4` / address `0x38` AV in both the
unchanged 800x600 baseline and the 1280x720 baseline; these are harness failures,
not battle HD patch evidence.

Runtime results and remaining acceptance items are recorded in
`captures/current/battle-hd-validation-current.json` and its Markdown report.
The helper, camera and lifecycle reports use their own current filenames and
bind their exact runtime candidate independently. Older candidates remain
diagnostics and cannot satisfy the final candidate's identity checks.
Final colors/composition and actual user input require fresh approved visible
runtime. Results/exit and restored HD-map rendering/input require explicit
lifecycle evidence. Neither existing centered-mode evidence nor a nonblack
frame satisfies those new-lane requirements.

The native cursor setter queues `(576,360)` for battle dialogs. In the forced
hidden route, its immediate device poll sometimes replaces X with a cached
sample of `4`; both pre-poll and post-poll values are reported. This is an open
input observation for visible validation, not evidence that the displayed
cursor is correct and not justification to alter generic map input.

# Imported HD validation foundation

This task imports the existing local implementation from
`C:/Users/andrz/git/clash-hd` into the reviewed repository. The source checkout
has additional uncommitted work; its Git revision alone does not identify these
files. The [import manifest](../../reports/hd-foundation-import-manifest.json)
records the exact source SHA-256, prior destination SHA-256 and batch for every
selected file. The source checkout was read only.

This is a source integration checkpoint. It does not promote a patch stage,
change launcher resolution status, or transfer a runtime pass from a different
candidate. Historical screenshots and failures remain in their original local
evidence directories. No game executable, save, asset, wrapper or raw capture
is included in the import.

## Construction layers

| Batch | Imported behavior | Primary construction entry |
| --- | --- | --- |
| `b1` | Combined validation stage, resolution-aware top/left frame extension, stable-stage and byte-definition guards | `patch_clash95_hd.py --stage <stable-stage>-combinedui-validation --resolution <WxH>` |
| `b2` | Clipped partial cells, initial/full map painting, four-sided frame/footer, command-panel composition, map input boundaries and optional minimap viewport correction | `tools/build_framed_candidate.py` |
| `b3` | Owned native 640x480 castle canvas, physical canvas mirror, explicit restoration/cleanup and native-size selected-army portraits | `tools/build_framed_army_candidate.py` |

The combined stage selects 27 groups and 166 existing patch records in frozen
table order. It combines the stable stage with `hdlayout-framerestore`,
`rightbottomcompose` and `castlecenter-all-battlecenter-inputprobe`. The latter
includes actual grid and descriptor input wrappers. Alternative legacy
presenters, action-descriptor relocation experiments and historical text-bar
experiments are excluded.

The framed builder layers a separate recipe and authenticated PE extension over
the combined candidate. The modal builder reconstructs that framed image from
pinned sources before adding its native canvas. The army builder reconstructs
the modal image before installing its separately admitted own-army composition
and input paths. Request `--minimap-viewport` for the existing optional minimap
correction; the default predecessor bytes remain independently reproducible.

Menus, castle views and tactical battles retain native 640x480 layouts centered
inside the larger physical surface. The unfinished widened-battle modules from
the source checkout are deliberately excluded from this import.

## Byte and evidence compatibility

The protected stable stage and frozen `PATCHES` table remain unchanged. Its
table hash is
`6683ee66851d23a28d856a8576e6b58c9b1285e0766bb592b9cdb0847bc8c55c`.
The original 800x600 combined candidate remains
`0a75cf35f42efe1e44fba1ac4031eaae5323cdff51aa19d261c36c5bb84691c2`.
Old-byte checks, original executable SHA admission, section/relocation checks
and output-path restrictions remain enforced by the existing builders.

The 24 source dependencies named in `.gitattributes` use `-text` because their
raw bytes are authenticated by the construction chain. This preserves the
reviewed mixed/LF line endings through commits and checkouts instead of changing
source pins merely to accommodate normalization. Verify dependency hashes from
the staged Git blobs as well as the working tree before merging this import.

The manifest preserves the raw source identity even where an import adjustment
was needed. `tools/test_initial_map_candidate.py` lost one trailing empty CRLF;
its original and imported hashes are both recorded. Unpinned guards, fixtures
and harnesses may use Git's normal CRLF-to-LF clean filter. Those text conversions
do not apply to the authenticated builder dependencies. The matching
`scripts/cdb/run_cdb_surface_dump.ps1` source is included in batch `b2`: its
initially missing import caused a real harness-contract fixture failure, which
passed only after the matching harness was imported. The original failed test
output remains in its local test directory.

Every repaired candidate needs its own source, stage, resolution, loaded-byte,
probe and output bindings. A passing source fixture or earlier software-surface
audit is not a current visible composition, ordinary-input or promotion pass.
The source checkpoint still has incomplete barracks slot composition, modal
exit/free coverage, wider-resolution traces and ordinary army interaction.

## Offline validation

Run the imported `tools/test_*.py` modules listed in the manifest with `python
-B`. They exercise frozen bytes, profile geometry, generated x86 instructions,
callee clobbers, partial-cell clipping, frame/source-pixel oracles, PE
relocations, native-canvas ownership and army redraw/input behavior.

Some optional fixtures read the user's original executable, `GFX3.RES`, or
previously generated local candidates. These files remain outside the
repository; missing local prerequisites must be reported as skips. Emitted-x86
fixtures compile and execute small synthetic x86 helpers outside the repository,
without launching Clash95 or CDB. Runtime-harness contract fixtures additionally
need the matching harness integration and are reported separately if that work
has not landed yet.

# Separate outside-world pixel diagnostics

`tools/framed_world_clear_audit.py` checks a declared before/after pair against
the existing `FramedViewport.WorldView` geometry. This fills an offline pixel
oracle gap: current geometry and native worker fixtures already check outside
world cell bounds and clear calls, while normal gameplay evidence explicitly
requires its entire ceiling window to remain inside the world.

The diagnostic does not extend that normal capture lane. There is currently no
authenticated outside-world before/after capture recipe, and complete-v1 does
not admit small worlds to the native full loop. Every output retains
`diagnostic_only: true`, `observation_authenticity: unverified_declared_pair`,
`native_capture_recipe_available: false`, `runtime_acceptance: false` and
`release_eligible: false`, including when the separate pixel contract passes.
The helper is not registered as a whole-release evidence adapter.

The shared candidate reader reconstructs the exact complete executable,
manifest and canonical probe. The diagnostic binds the framed geometry and
clipping source hashes and locates the actual outside-world fill call in those
candidate bytes. Its clear color is **palette index 1**, as emitted by
`partial_tile_clip.py` and independently checked by the native partial-cell
fixtures. Literal zero bytes fail that contract. No binary recipe is changed.

Every outside-world full or partial cell must contain only index 1 afterward
and must have at least one measured non-clear-to-index-1 transition. Already
clear before/after cells cannot demonstrate a clear operation. Reports separate
remaining non-clear pixels, unchanged stale non-clear pixels and missing
transition witnesses. Right and bottom partial cells, their corner, and full
cells exposed by a world smaller than the viewport use the same framed cell
rectangles; no older unframed tile calculation is used.

For in-world cells, the diagnostic reads the supplied player's complete native
visibility bitmap: 100 columns of 13 bytes, with bit `y & 7` in byte
`13*x + (y >> 3)`. A cell containing only indexed values 0/1 fails when that
matching bit is visible. Zero-visibility blanks are reported separately. This
tests the supplied bitmap and pixels; their native origin, player selection,
pause alignment and chronological pairing remain unverified. It is not a
terrain artwork or detail oracle.

All four frame bands must remain byte-identical across the pair. This checks
write containment, not correct frame artwork. The declared raw surface must be
packed indexed terrain **before overlay composition**. The diagnostic accepts
no masks: minimap, army or command overlays must not conceal a clearing defect.
The surface phase itself is not authenticated by a caller's declaration.

The pair manifest uses schema `clash95_framed_world_clear_pair_v1` and these
exact fields:

- `candidate`: exact stage, resolution, candidate SHA, base SHA, recipe revision,
  canonical probe SHA and the actual candidate-manifest SHA.
- `geometry_sha256`: actual `src/patcher/framed_viewport.py` hash.
- `world` and `scroll`: two integer coordinates each, subject to the existing
  world dimensions and full-tile scroll clamps. Booleans are rejected.
- `surface_format`: `indexed8-packed-terrain-before-overlays`.
- `before`, `after`, `visibility`: distinct local artifact references, each
  containing only an absolute `path` and exact `sha256`. All three must be in
  the manifest directory. Before and after each contain exactly width×height
  bytes; visibility contains exactly 1,300 bytes.

The context key names are `stage`, `resolution`, `candidate_sha256`,
`base_sha256`, `recipe_revision`, `probe_sha256` and `manifest_sha256`.
Additional fields, caller-authored pass flags, wrong hashes, mixed candidates
and cross-resolution contexts fail. The pair manifest, candidate manifest and
original executable are hashed before parsing or reconstruction, then checked
again after the audit. A manifest changed while reconstruction runs cannot
silently become the recorded source of already parsed values. Only a new
output may be written:

```powershell
python tools/framed_world_clear_audit.py --pair-manifest C:\ClashCaptures\world-clear\pair.json --candidate-manifest C:\ClashTests\candidate\clash95_completehd.candidate.json --original C:\Clash\clash95.exe --output C:\ClashCaptures\world-clear\pixel-diagnostic.json
```

That command reads existing files and starts no game, debugger or capture.
Exit zero means the declared pixel contract passed; a failed contract exits 2.
Neither result is release evidence, manual proof, cleanup proof or approval to
run the unsupported native capture path. Keep raw material outside Git.

`python -B tools/test_framed_world_clear_audit.py` runs synthetic fixtures for
all six launcher presets plus 802×602, small worlds, partial tails and corners,
literal-zero rejection, stale pixels, per-cell witnesses, visibility, border
containment, identity mutations and immutable output. The bound-artifact tests
replace only proprietary candidate reconstruction with an explicit stand-in;
source hashes, clear-instruction parsing, geometry and raw comparisons run.

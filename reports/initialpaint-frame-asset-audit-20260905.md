# Initial-paint frame artwork audit

The saved 800x600 run `20260905-210832` and 1024x768 run `20260905-211004`
have exact native top/left artwork, including their extensions. **Neither
contains a complete bottom/right frame.** At 1024x768 the left border continues
through row 767; the suspected cutoff around row 600 is not present in this
capture. These findings are separate from the passing action-bar and bounded
surface gates.

The [machine-readable audit](../captures/current/initialpaint-frame-asset-audit-current.json)
binds both summaries, raw surfaces, PNGs, recorded palettes and candidate
identities. Exact in-memory reconstruction verifies each PNG from its raw
indices and palette. Both saved PNGs were also inspected directly; no image
was edited or new capture taken.

| Source-art comparison | 800x600 | 1024x768 |
| --- | ---: | ---: |
| Native top band, x=0..639, y=0..15 | 10240/10240 exact | 10240/10240 exact |
| Top extension, x=640..W-1 | 2560/2560 exact | 6144/6144 exact |
| Native left band, x=0..31, y=16..479 | 14848/14848 exact | 14848/14848 exact |
| Left extension, y=480..599 | 3840/3840 exact | 3840/3840 exact |
| Left extension, y=600..767 | Outside image | 5376/5376 exact |
| Native right-middle reference translated to x=W-32..W-1, y=230..463 | 0/7488 art pixels match | 0/7488 art pixels match |
| Native bottom-middle reference translated to y=H-16..H-1, x=32..607 | 2/9208 art pixels match | 0/9208 art pixels match |

The last two rows are diagnostic comparisons with original artwork, excluding
the minimap, action bar and corners. They do not choose a new HD layout or
extension recipe. Neither bottom comparison has a complete matching row; the
two isolated matches at 800x600 are not surviving-frame proof. The right-middle
regions contain only palette indices 0/1. Most other black map regions have
not been classified: visibility/fog and omitted proxy layers remain distinct.

The visible seam near the old 640-wide edge is **not proved to be retained
right-frame artwork**. At its native x=608..639 position, y=16..229 has only
39/6848 source matches at 1024x768 and no complete matching row; y=230..463
has 0/7488. A seam's appearance alone cannot identify its source.

## Native source and current implementation

Gameplay uses root `FRAME.S32` from `C:/Clash/DATA/GFX3.RES`, not the different
`GFX/BATTLE/FRAME.S32` in `minimum.res`.

- Resource SHA-256: `31489538e8b98d180b434151db8260d00edf5ce9dd98e9f80e1d4e0607e3f525`.
- Member offset/length: `1884879 / 89593`; SHA-256:
  `8501cbae69c35aa5a804823227bbd56fb21e84b4f1e5c0f15e4419f522c4053d`.
- Native loader at `0040B003` populates `005202BC`. Native `Render_DrawSprite`
  at `00406740` places sprite 0 at `(0,0)`, sprite 1 at `(314,0)`, sprite 2
  at `(0,237)`, sprite 3 at `(315,238)`, then sprite 5 at `(155,465)`.
- The [existing decoder](../tools/hd_layout_asset_composition.py) reads literal,
  transparent and shared runs in memory. No proprietary extraction file is
  created. Native ASM and decoder hashes are in the audit.
- The [frame-restore recipe](../src/patcher/patch_clash95_hd.py) repeats native
  `(0,360)..(31,479)` down the left extension and `(480,0)..(639,15)` across
  the top extension, clipping tails. The observed pixels match that recipe
  exactly. It does not supply a relocated bottom/right frame.

The native drawing routine writes this artwork to both the software backbuffer
and the primary target. Its incomplete software border is therefore a separate
composition issue from hidden-capture omissions of minimap, tooltip or HUD
layers. Final visible-wrapper composition still needs its own approved
evidence. Existing runtime gates, old failures, manual proof and promotion
status remain unchanged.

## Separate prospective four-border oracle

[frame_surface_audit.py](../tools/frame_surface_audit.py) authenticates the
same resource/member and exposes `load_native_frame(resource_bytes)` for
in-memory consumers. `NativeFrame.base_pixels` contains sprites 0..3 only;
`NativeFrame.footer` is the separate 324x15 sprite 5. The base has exactly
49,152 opaque pixels, covering the native 32-pixel side bands and 16-pixel
horizontal bands, with transparent terrain and no overlapping pieces.

The explicit prospective `native_four_border_tiles_v1` profile preserves all
32x16 corners, repeats native x=32..607 inside horizontal bands and y=16..463
inside vertical bands, and clips tails. It is native-identical at 640x480.
This differs from the current 160/120 extension recipe tested above; a texture
phase mismatch under the new profile does not contradict the current exact
top/left result. The oracle installs no patch or stage.

Sprite 5 is drawn once at `(155+(W-640)//2,H-15)`, preserving the native
asymmetry. Native tooltip text starts five pixels to its right and two below;
the existing `terrain-tooltip-bottom-center` scalars preserve those offsets.
The oracle separates structural border pixels from this fixed footer
footprint. An exact footer match is required for a whole-frame pass. A footer
mismatch is reported as unverified background or active tooltip text, without
guessing glyphs or treating the entire footer as an allowed mask. Four-border
pixel proof still does not establish runtime, visible input or promotion.

# Battle UI Patch Manifest

Generated: 2026-05-15
Updated: 2026-05-20

Three battle-specific validation patch groups have been added:
`battle-ui-center-present-wrapper`, `battle-grid-centered-input`, and
`battle-ui-centered-input`.

The validation stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
currently selects the same patch groups as `castlecenter-all` plus the narrow
initial battle-present wrapper.

The validation stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe`
adds the two centered input wrapper groups for CDB-only proof.

## Current Patch Groups

- `battle-ui-center-present-wrapper`: patches `0042F2F5` / file offset
  `0x02E6F5` to call cave `0051BA00`, then the cave preserves the native
  640x480 battle frame, clears the 800x600 target, copybacks at `(80,60)`,
  and calls stock `Render_Present`.
- `battle-grid-centered-input`: patches `0042E4ED` / file offset `0x02D8ED`
  from `E8 5E E6 FF FF` to a call into cave `0051BAA0`. The cave temporarily
  subtracts the centered battle visual offset `(80,60)` from the fixed-point
  mouse globals, calls stock tactical-grid helper `0042CB50`, restores the
  visual coordinates, and returns to the battle loop.
- `battle-ui-centered-input`: patches `0042E501` / file offset `0x02D901`
  from `E8 BA B8 FE FF` to a jump into cave `0051BAF0`. The cave preserves the
  descriptor-scan stack shape, temporarily subtracts `(80,60)`, calls stock
  descriptor helper `00419DC0`, restores the visual coordinates, and resumes at
  `0042E506`.

## Deferred Patch Groups

- `battle-ui-center-present`: the initial-present subset is implemented as
  `battle-ui-center-present-wrapper`; post-ready redraw/copyback sampling now
  passes in `captures\current\battle-ui-post-ready-redraw-current.md`, but no broader
  present wrapper is promoted without a separate exact callsite need.
- `battle-ui-ensure-800-surface`: blocked until battle surface ownership/size is proven.
- Promotion of `battle-ui-centered-input` and `battle-grid-centered-input`:
  blocked until natural/manual cadence is proven. The current validation proof
  in `captures\current\battle-ui-centered-input-current.md` shows both wrappers apply
  the correct pre/inner/post coordinate transform under CDB, but helper bodies
  are intentionally skipped after entry to keep this a wrapper-mechanics proof.
- `battle-modal-centered-input`: the current forced route is classified as
  `input_update_seen_no_modal`; a modal-specific patch stays blocked until a
  real modal/dialog target is proven or manual testing shows one needs a
  centered transform.
- `battle-present-bounds`: blocked until stale right/bottom battle present/copy
  bounds are proven. The current post-ready sample records 9 presents and
  6 copybacks on the centered 800x600 surface without an AV.

Every future battle patch must document file offset, VA/RVA, old bytes, new
bytes, stage, rationale, observed effect, and must pass old-byte verification.

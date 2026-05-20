# Battle UI Patch Manifest

Generated: 2026-05-15
Updated: 2026-05-20

One battle-specific validation patch group has been added:
`battle-ui-center-present-wrapper`.

The validation stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
currently selects the same patch groups as `castlecenter-all` plus the narrow
initial battle-present wrapper.

## Current Patch Groups

- `battle-ui-center-present-wrapper`: patches `0042F2F5` / file offset
  `0x02E6F5` to call cave `0051BA00`, then the cave preserves the native
  640x480 battle frame, clears the 800x600 target, copybacks at `(80,60)`,
  and calls stock `Render_Present`.

## Deferred Patch Groups

- `battle-ui-center-present`: the initial-present subset is implemented as
  `battle-ui-center-present-wrapper`; later redraw centering is still blocked
  until battle-loop redraw callsites are proven.
- `battle-ui-ensure-800-surface`: blocked until battle surface ownership/size is proven.
- `battle-ui-centered-input`: blocked until natural/manual callback cadence is
  proven; descriptor hits, callback entry, and an enabled callback result are
  currently harness-proven only.
- `battle-grid-centered-input`: route classified through `0042CB50`, but still
  blocked until the exact centered-offset transform is implemented and proven
  without breaking natural/manual cadence.
- `battle-modal-centered-input`: the current forced route is classified as
  `input_update_seen_no_modal`; a modal-specific patch stays blocked until a
  real modal/dialog target is proven or manual testing shows one needs a
  centered transform.
- `battle-present-bounds`: blocked until stale right/bottom battle present/copy bounds are proven.

Every future battle patch must document file offset, VA/RVA, old bytes, new
bytes, stage, rationale, observed effect, and must pass old-byte verification.

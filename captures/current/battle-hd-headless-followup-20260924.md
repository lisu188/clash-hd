# Expanded battle headless follow-up, September 24

This report records completed hidden runs `20260924-091943` and
`20260924-093005` of candidate
`99D92EC7C8F81DEBF60321DCC5C1B5872C96E3C485FA2BDD7D9332287B3C7E87`.
The stage is `-castlecenter-all-battlehd` at 1280×720. The matching
[JSON](battle-hd-headless-followup-20260924.json) contains all 42 verified
artifact SHA-256 and length references, the forced actions, and the observations.
The later corrected candidate has separate
[checkpoint evidence](../../reports/battle_hd_merge_checkpoint_20260926.md).

## Results

- Camera measurements passed 7/7: widths 17 and 20 clamped to their expected
  endpoints, selection recentering reached both endpoints, and an already
  visible selection retained its camera position. The debugger temporarily
  changed arena width and selection for direct helper calls, then restored the
  original 16×7 arena before rendering. This is not natural wide-arena or input
  evidence.
- Lifecycle measurements passed 11/14. Banner, modal, and results exact cursor
  return checks failed: requested `(576,360)` became `(4,324)`, `(601,1)`, and
  `(576,385)` respectively.
- A separate read-only observer correlated each cursor call by caller, thread,
  stack position, instruction order, and device-buffer identity. All three
  native `GetDeviceState` calls returned `8007000C`; each 16-byte target buffer
  remained unchanged. Those values do not establish valid input deltas.
- The banner used the inherited absolute-input branch under owner `004617A0`.
  Modal and results calls used the relative-input branch under battle owner
  `0042E8B0`. The banner branch defect motivated the subsequent overlay fix.
- Both harnesses completed their finite captures with successful owned-process
  cleanup and no logged access violation or timeout. Neither run is a soak.

## Surface review and limits

The camera software surface shows the restored 16×7 battlefield, all four
battle-frame edges and the right statistics panel. Its bottom-right command
area is black, so command artwork and final wrapper composition remain
unproven. The post-exit surface shows map terrain and minimap; the complete
outer map frame and all six bottom-right action cells are absent. Restored map
composition and input therefore remain pending. No obvious horizontal
shearing appears in these hidden software surfaces; this is not a visible
capture tear-check or stable-pair claim.

The observer alone is read-only. The inherited startup and lifecycle fixture
force acquisition results, route setup, callback invocation and dismissal;
those interventions are fully listed in the retained run manifest. The
prepared visible packet was unused. No visible session, manual input,
natural lifecycle, or stable-stage promotion is claimed. Headless operation
remains the default and the launcher remains 800×600.

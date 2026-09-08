# Battle HD source-binding integration

The isolated battle HD stage changes the canonical patcher's source identity. Existing framed, partial-tile, modal, army and camera builders now bind that reviewed producer and the resulting dependency hashes. The canonical patcher retains every upstream line byte-for-byte and adds 56 lines. Only SHA string literals changed in the 13 dependent source files; source checks, reconstruction code, and patch recipes remain intact.

The upstream patcher at merge commit `409fa4c08dd2ff4c4a85732b4d5a80102de84de5` had SHA-256 `09f383ce7479d4be4c94017e347d6857acbcd364542fd2b72bafe3e1f0924db1`. The reviewed current patcher has SHA-256 `05f31359f93a0eb0b319679ee524b21c05cd3e86e485b7ebb92afc8e6da29f31`. The [foundation import manifest](hd-foundation-import-manifest.json) retains the original snapshot identities and was not edited by this integration. The integration manifest distinguishes Windows checkout hashes from Git blob hashes, including the two leaf source files normalized to their upstream LF form.

Comparison against that upstream commit confirmed:

- The full legacy table, including notes, retains SHA-256 `6683ee66851d23a28d856a8576e6b58c9b1285e0766bb592b9cdb0847bc8c55c`.
- All 62 existing stage groups and 186 recipe records are unchanged.
- All 147 supported selections and 225 rejected combinations match across 800×600, 1024×768, 1280×720, 1280×960, 1920×1080 and 802×602.
- The only added stage is `DEFAULT_STAGE + "-castlecenter-all-battlehd"`.

Exact old/new producer hashes, dependency edges and comparison digests are recorded in [the integration manifest](battle_hd_source_binding_integration.json). Existing candidate bytes remain governed by their original recipes; new build metadata reflects the reviewed producer identities. This source integration does not reclassify prior runtime evidence or establish promotion.

A fresh source-only Git checkout with `core.autocrlf=true` reproduced all 14 producer hashes and passed the source preflight. Explicit `-text` attributes preserve both leaf producers as well as their pinned dependencies. Focused validation results are recorded in the integration manifest. No game, debugger, wrapper, or runtime harness was launched for this review.

# Framed minimap: six-resolution runtime matrix

Recorded 2026-09-06T03:48:21.546600+00:00.

**All six captures pass minimap geometry and exact pixels, all four frame bands, footer and six action-bar cells.** Runtime passes remain limited to 800x600, 1024x768 and 802x602. The other three outcomes stay failed.

The optional `--minimap-viewport` revision uses the existing framed validation stage with new exact candidate identities. Stable selection is unchanged; no promotion, actual panning or manual-input proof is implied.

| Resolution / run | Runtime | Initial trace | Inclusive outline | Exact 4C perimeter | Frame / footer / action bar |
| --- | --- | --- | --- | --- | --- |
| 800x600 / 053205 | PASS | PASS | `(580,56)..(604,75)` | [86/86](framed-minimap-v1-800x600-viewport-20260906.json) | [PASS / PASS / 6 of 6](framed-minimap-v1-800x600-pixels-20260906.json) |
| 1024x768 / 051740 | PASS | PASS | `(804,56)..(835,80)` | [110/110](framed-minimap-v1-1024x768-viewport-20260906.json) | [PASS / PASS / 6 of 6](framed-minimap-v1-1024x768-pixels-20260906.json) |
| 1280x720 / 052225 | FAIL: coverage exit 2 | PASS | `(1060,56)..(1099,79)` | [124/124](framed-minimap-v1-1280x720-viewport-20260906.json) | [PASS / PASS / 6 of 6](framed-minimap-v1-1280x720-pixels-20260906.json) |
| 1280x960 / 052536 | FAIL: coverage exit 2 | PASS | `(1060,56)..(1099,86)` | [138/138](framed-minimap-v1-1280x960-viewport-20260906.json) | [PASS / PASS / 6 of 6](framed-minimap-v1-1280x960-pixels-20260906.json) |
| 1920x1080 / 053005 | FAIL: strict trace | FAIL | `(1700,56)..(1759,90)` | [186/186](framed-minimap-v1-1920x1080-viewport-20260906.json) | [PASS / PASS / 6 of 6](framed-minimap-v1-1920x1080-pixels-20260906.json) |
| 802x602 / 052106 | PASS | PASS | `(582,56)..(607,75)` | [88/88](framed-minimap-v1-802x602-viewport-20260906.json) | [PASS / PASS / 6 of 6](framed-minimap-v1-802x602-pixels-20260906.json) |

Every measured state has world 100x100, scroll (10,17), scale 2 and a 214x214 backing. The 1024 example projects 960x736 actual terrain pixels to 30x23 minimap pixels, then adds the native inclusive border. All perimeter mismatches are zero.

## Preserved failures

- **1280x720 and 1280x960:** `low_overall_gameplay_coverage` caused `map_tile_coverage.py` exit 2 before final summaries. Their labeled diagnostic summaries and original coverage reports remain preserved. A prior-revision fog explanation is not transferred to these candidate bytes.
- **1920x1080:** the strict trace reports `line 556: incremental input/exit lacks a fresh matching guard and phase`. The original runtime summary remains failed. The diagnostic PNG comes from its existing raw surface; its geometry/pixel pass is separate.

## Candidate identities

| Resolution | Candidate SHA-256 |
| --- | --- |
| 800x600 | `c0867837388e93507bc190c0e722717cd904eacd1562db835860ae60ed704373` |
| 1024x768 | `69899e07f70dde2094264be694300e00c7a778f1391ac7797b74c59c56ee1ce0` |
| 1280x720 | `6329940475c49c0db92398ec29264044cea8a0476b48a40529a3c104f37da78f` |
| 1280x960 | `181b720d759e9c7af62eedcaca74e0dc08cdd5db28048e9b611e70775961c9f9` |
| 1920x1080 | `034e184ee3c48fbea6a31a2b55a6339451f7f32f11fa77ce97e0e457ebedc3c1` |
| 802x602 | `2a75641f1aa1b3132ae50b5e8ed768458e5e6d6985e9cfba702ced85ffec8161` |

The [1024 plan](framed-minimap-run-plan-20260906-031649.json) and [additional five-run plan](framed-minimap-run-plan-20260906-032002.json) bind candidate, canonical installed extra, both prepared main-probe hashes and producer sources. The [JSON matrix](framed-minimap-runtime-current.json) records hash-bound audits, original/diagnostic summaries, logs, probes, observer packets, raw surfaces and PNG metadata.

## Process observations

The [coordinator export](framed-minimap-process-receipts-20260906.json) preserves parsed original receipts, their source paths and raw-file SHA-256 values. The private original receipt directory was inaccessible to this matrix task; the durable export was read and hashed instead. Candidate paths, debugger command lines, parent relationships, PID sets and observation ordering agree within that bundle.

| Resolution | Recorded CDB / game PIDs | Later observation |
| --- | --- | --- |
| 800x600 | 42448 / 29372 | Both absent at `2026-09-06T03:33:53.5149849Z` |
| 1024x768 | 28632 / 17920 | Both absent at `2026-09-06T03:19:01.8047648Z` |
| 1280x720 | 13956 / 32612 | Both absent at `2026-09-06T03:24:27.6642978Z` |
| 1280x960 | 39100 / 37684 | Both absent at `2026-09-06T03:29:51.5041354Z` |
| 1920x1080 | 41400 / 39448 | Both absent at `2026-09-06T03:31:49.3134842Z` |
| 802x602 | No live pair recorded | Empty late query at `2026-09-06T03:21:45.1530930Z`; no exact-PID cleanup proof |

Actual scroll transitions/old-outline erasure, far-world captures, scale-4 runtime, modal/army screens, visible composition, manual input and endurance remain separate work. Source and synthetic x86 coverage do not replace those observations. See [implementation and limits](../../docs/hd/MINIMAP_VIEWPORT.md).

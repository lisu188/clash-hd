# Framed initial-map runtime observations

Recorded 2026-09-06. **1024x768 passes its bounded hidden runtime checks;
800x600 remains a runtime trace failure. Both screenshots exactly match all
four frame bands, the separate footer and all six action-bar cells.**

The [observation manifest](framed-map-runtime-current.json) binds the immutable
[run plan](framed-map-run-plan-20260906-023304.json), candidate/probe/source
hashes, raw logs, original summaries, pixel artifacts and cleanup observation.
The exact validation stage is:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation
```

| Run | Runtime result | Frame pixels | Action bar |
| --- | --- | --- | --- |
| 800x600, `20260906-043323` | FAIL: duplicate native exit at events 81/82 | 57,092 border + 4,860 footer pixels exact | 6/6 exact |
| 1024x768, `20260906-043513` | PASS: loaded contract, partial status, initial trace, surface and explained visibility | 75,012 border + 4,860 footer pixels exact | 6/6 exact |

The 800 candidate SHA is
`7fad16f167205fb34ecbc99a6a1ff6180c710807f99b19f25efb48a8b1c8d15b`;
the 1024 candidate SHA is
`3e9969a1e9285a9e65290072ea89cb2a3f224bd118ef267794fd1028ac5d7053`.
Both actual files match the planned SHA, build metadata and loaded contract.
All **25 source pins** match the plan. Installed extra probes materialize
Windows CRLF; their canonical UTF-8 LF hashes match the plan exactly. The
manifest retains both raw extra and final generated-probe hashes.

The 1024 trace contains 140 events, one initial convergence/presentation pair,
49 incremental inputs and 37 matched native no-op exit records. It closes at
the update boundary before the four-update memory capture. The 800 log contains
141 events, 49 inputs and 38 exit records. Events 81/82 both observe BP74,
EIP `00418AFA`, TID `2A28`, ESP `000EDC7C`, world `(60,47)` and caller
`004166FA`. The second exit has no fresh guard/invocation; the strict parser
fails at line 395. Its initial full pair and increasing event sequence do not
excuse the invalid later call trace. No record was deduplicated.

The separate 800 `diagnostic-summary.json` keeps `Passed=false`, references the
original failed summary hash, and exposes only the already captured raw pixels
as `surface-diagnostic.png`. The original summary is unchanged. The 1024
`surface.png` belongs to its passing original summary. Independent
[800 frame](framed-v1-800-frame-audit-20260906.json),
[1024 frame](framed-v1-1024-frame-audit-20260906.json) and
[six-cell action-bar](framed-v1-action-bar-audit-20260906.json) audits bind the
PNG, raw surface, palette and candidate identities. These are indexed software
pixels, not visible wrapper or input proof.

Both runs use the hidden desktop and memory proxy with presentation disabled,
slot 0, and source-bound debugger route mechanics. Neither reports an AV,
timeout or host dump error. Actual minimap backing is enabled 214x214 at
`(554,16)` / `(778,16)` respectively. Current visibility scope requires every
ceiling cell to be in the world.

At **2026-09-06T02:39:37.7159976Z**, explicit `Get-Process -Id` observations
returned `NoProcessFoundForGivenId` for the runtime coordinator's recorded
800 CDB/game PIDs **14244/39120** and 1024 PIDs **33104/31664**. A CIM query was
denied in this reviewer sandbox; the manifest reports the successful process
absence method rather than claiming a CIM observation.

Historical failed runs and earlier unframed initial-paint passes remain
unchanged. This report covers only these two runs. Broader resolutions,
far-world captures, modal/army owners, active tooltip behavior, manual input,
visible composition and endurance remain separate claims. Stable selection and
promotion are unchanged; `manual_input_proof=false`, `promotion_ready=false`.

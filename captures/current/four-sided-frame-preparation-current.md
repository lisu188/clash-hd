# Four-sided frame preparation

Recorded 2026-09-05T19:46:16.328104+00:00. **31 focused tests pass**, including **903 synthetic x86 executions** at three code addresses. The helper is **uninstalled** and the actual game captures are **not fixed**.

The new geometry, source-pixel oracle and emitted memory-surface helper preserve native corners, repeat base artwork without scaling, and draw footer sprite 5 once. Pixel checks cover native 640x480 plus 800x600, 1024x768, 1280x720, 1280x960, 1920x1080 and 802x602. Every terrain/control pixel remains untouched in the reference canvas.

Synthetic execution verifies actual helper instructions, native-call arguments, rejection before drawing, register/flag/stack preservation, exact render-pointer restoration and relocation. Native sprite calls are fixture recorders; they do not provide game/runtime pixel proof.

The [current source audit](initialpaint-frame-asset-audit-current.json) proves intact top/left artwork under the existing recipe and missing right/bottom composition. Both actual PNGs [fail the prospective four-band profile](four-sided-frame-prospective-audit-current.json). That new repeat profile does not reclassify the older top/left proof.

Read [the integration contract](../../docs/hd/FOUR_SIDED_FRAME.md) before installing anything: terrain/control/input bounds, owner and tooltip order, frame presentation, initial readiness and candidate-bound hidden verification remain necessary. The original executable and protected stable patcher are unchanged. No frame game/debugger run, image edit, visible/manual input or promotion occurred.

Exact sources, fixture hashes and per-resolution emitted-code metadata: [JSON](four-sided-frame-preparation-current.json).

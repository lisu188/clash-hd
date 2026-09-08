# Owned castle canvas: current runtime evidence

The complete native-artwork protocol now has **six captured 1024x768 routes**.
All six bounded runtime traces and capture bindings pass. Exact native-to-HD
mirror comparison passes for five; **barracks fails with 24,576 missing pixels**.

| Route | Runtime/capture | Native mirror | Visible software-capture observation |
| --- | --- | --- | --- |
| Castle overview | PASS | PASS | Coherent courtyard, back button and bottom strip |
| Hospital | PASS | PASS | Readable text and intact panel border |
| School | PASS | PASS | Readable text and intact panel border |
| Workshop | PASS | PASS | Readable text and intact panel border |
| Smiths | PASS | PASS | Readable text and intact panel border |
| Barracks | PASS | FAIL | Five bottom controls, but blank unit-slot interiors |

Every screenshot was shown and inspected for the bottom-right controls and
all four edges. These centered castle screens have clear outer margins; the
ordinary-map frame/footer and six-cell bar templates are not modal acceptance.
All 479,232 margin pixels are index zero. Button/input behavior is unproven.

A preceding hospital attempt remains **failed before capture** because its
initial map trace repeats an incremental input/status without a fresh guard.
Its complete hospital sequence passed, but the host correctly refused capture.
The later successful run does not erase this failure.

All seven owned debugger/game pairs stopped with retained-handle receipts.
The original and existing workdir files are unchanged. Barracks generated four
native cache files; they are preserved outside the repository. Earlier striped
captures, the invalid-PE run and first-protocol limitations remain recorded in
the [preserved checkpoint](framed-modal-canvas-runtime-20260906-first-protocol.json).

[Exact candidate/source/artifact bindings, comparisons and cleanup](framed-modal-canvas-runtime-current.json).

The user next prioritized a wider tactical battle UI with native-size sprites
and controls anchored to the edges. Peasants has an unexecuted prepared plan;
the additional 802x602 candidate is built only. Court/recruitment composition,
native modal exit/free, other resolutions and manual-input/promotion gates
remain outstanding. The protected stable stage is unchanged.

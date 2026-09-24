# Route wide Classic presets through the verified menu correction

The manifest-driven real-EXE sweep reproduced missing button labels in wide
Classic menu captures. A nonempty, stable framebuffer was insufficient to catch
this defect. The menu-only builder in PR #108 now has a source-launcher route:
Classic widths at least 1144 use `classic_menu_widgets_v1` and a separate
`classic-menu-validation/<resolution>` candidate directory. All seven affected
advertised Classic presets use this route. Native 800x600 and 1024x768 retain
the exact existing scalar path, filenames and bytes. An explicitly selected
legacy stage still uses that stage rather than silently adding the extension.

The new `classic.py` facade shares the source-bound Complete HD preparation,
deployment, reconstruction and pre-Play verification implementation. It does
not duplicate or relax path, old-byte, wrapper or sidecar checks. Classic's
minimap flag remains false. The display plan keeps its scalar geometry while
recording the distinct menu revision/build identity. The manifest preserves
all existing options and Classic800x600 as the default; its explicit
`wide_menu_recipe` metadata is validated before routing. The source-only wide
builder is refused in a frozen launcher without its source prerequisites;
native Classic800x600 remains available. No packaged-wide compatibility pass is
claimed by this source-tree change.

## Verified source/UI checkpoint

Exact tested source commit: `9ebb036901a74d4e34ab5f1aa91021d85701a9de`.
Isolated Ubuntu/Xvfb run: `35509463247`.
Artifact: `10604943125`, `classic-launcher-review`, ZIP SHA-256
`27faf666b7b4699fdb609e4a444ca5a853a2b7aec4c7d5ff137e624005796c04`.

All 105 launcher methods, including nine new routing/bundle regression methods
and the actual isolated Tk fixtures, passed without skips, errors or failures.
The frozen source preflight passed. The downloaded archive and every archived
source file were checked against its recorded hash and the locally reviewed
source. No game runs during these source/UI fixtures; candidate bytes in the
focused tests are clearly synthetic. The previous exact-output integration
attempts failed before applying source changes because of a mismatched LF/CRLF
identity and an incorrect redundant executor hash. Those failures remain
retained as runs 35508687568 and 35508944327. The corrected integration retained
exact input and output source hashes and a reversible one-line newline fix.
Its temporary write-enabled executor and workflow were removed before this PR.

This checkpoint establishes launcher routing and reconstruction, not corrected
real menu pixels or gameplay. Fresh real runs must bind the new manifest and
candidate identities and compare the complete native menu to the retained
original, not just test that an image is nonblack. Map input, modal screens,
save/load and full-window 4K display remain separate validation. Protected
scalar recipes, original assets and all historical runtime receipts are unchanged.

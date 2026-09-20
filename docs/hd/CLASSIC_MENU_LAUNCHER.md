# Wide Classic menu routing

The source-tree launcher selects the separate `classic_menu_widgets_v1` recipe
for Classic presets whose width is at least 1144. It admits only authenticated
native menu descriptor tuples to widened menu bounds; foreign or parked widget
descriptors retain the original limit. Native 800x600 and 1024x768 use the
unchanged Classic scalar path. Classic800x600 remains the default.

Candidate bundles for corrected wide menus live under
`C:/ClashTests/launcher/classic-menu-validation/<resolution>/`, separate from
historical scalar candidates and all other profiles. The facade shares the
existing source-only HD preparation and launch verification path. Before reuse
or Play it reconstructs the requested recipe, verifies exact executable/probe
and sidecar bytes, and checks the deployed wrapper/configuration identities.
Renaming or rehashing a modified candidate does not bypass reconstruction.

For example, from the complete source checkout:

```powershell
python src/launcher/run.py --profile classic --resolution 1920x1080 --describe-plan
python src/launcher/run.py --profile classic --resolution 1920x1080 --prepare
```

Inspection builds nothing. Preparation does not launch the game. Play still
requires the GUI action, or both `--launch --yes-launch` for the CLI. The wide
menu extension requires its complete source prerequisites; no packaged-wide
launcher compatibility is claimed. Explicit legacy stage selection remains
available for historical reproduction rather than rewriting its candidate.

The exact launcher validation checkpoint is recorded in
[`classic_launcher_menu_20260920.md`](../../reports/classic_launcher_menu_20260920.md).
Source/UI tests do not replace actual menu, input, map or save/load checks. All
new routing and menu corrections remain experimental; no historical capture is
relabelled and no stable promotion is implied.

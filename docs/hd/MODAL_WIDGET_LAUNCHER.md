# Experimental modal-widget launcher profile

The source-tree launcher exposes **Modal widgets HD (experimental)** in the
renderer selector and as `--profile modalwidgets` on the command line. It uses
the exact `owned_modal_widget_bounds_v1` builder and a separate output tree:
`C:/ClashTests/launcher/modalwidgets-validation/<resolution>/` by default.
Classic/800x600 remains the global default. The older Complete HD profile is
still available and keeps its own directory, recipe and saved metadata.

This profile inherits the Complete HD adventure frame, clipped edge tiles,
minimap correction, owned native modal canvas and army panel, then adds modal
primary composition, centered barracks quantity text and the two context-bound
widget comparisons. Native menu/castle/battle dimensions remain centered rather
than enlarged. The available fixture resolutions are 800x600, 1024x768,
1280x720, 1280x960, 1920x1080 and 802x602; custom dimensions are not admitted by
this exact recipe. Every profile entry remains experimental.

The thin profile adapter shares the existing isolated HD preparation/deployment
pipeline instead of copying its path, hashing and reuse checks. The pipeline
reconstructs the selected candidate before reuse and before Play. Stage,
revision, resolution, candidate/probe identity, all three candidate files,
wrapper/configuration hashes and deployment identity must match. Rehashing a
modified executable or sidecar does not bypass reconstruction. Source preflight
also checks the frozen primary-text source identities. Output collisions,
symlinks, hard links, unknown originals and mixed-profile paths remain errors.

The packaged launcher still exposes Classic only; these experimental recipes
require their complete source tree. Use a separate installed working copy of
the original game, not an immutable asset-reference checkout.

```powershell
python src/launcher/run.py --profile modalwidgets
python src/launcher/run.py --profile modalwidgets --describe-plan --resolution 1920x1080
python src/launcher/run.py --profile modalwidgets --prepare --resolution 1920x1080 --clash-dir C:/Clash
```

The first command opens the launcher, not the game. `--describe-plan` needs no
game files and performs no build; `--prepare` builds/deploys but does not launch.
Play remains an explicit GUI action. CLI game launch still requires both
`--launch --yes-launch`. Existing Classic user settings are not overwritten
merely by selecting the experimental profile.

Menu startup evidence is not barracks-rendering or gameplay evidence. This
profile does not claim accepted controls, map entry, modal exits, save/load,
endurance or stable promotion. Source/UI fixtures use synthetic candidate bytes;
the exact candidate's real runtime observations are documented separately.

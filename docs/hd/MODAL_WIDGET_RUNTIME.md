# Runtime selection for the modal-widget candidate

`tools/real_exe_smoke.py` now selects the exact `modalwidgets` recipe through
`--complete-hd --hd-recipe modalwidgets --hd-resolution 1024x768 --hd-only`.
The six canonical builder profiles are accepted. The existing default Complete
HD 1024x768 comparison remains unchanged, including its original filename and
historical `complete_hd_manifest` report field. A widget candidate is never
reported as the older Complete HD recipe.

The selector calls the actual recipe writer rather than renaming a previously
built EXE. It checks the selected stage/revision/resolution, candidate bytes,
probe hash and exact serialized sidecar, and rechecks all recorded sources
before staging and after actual execution. A new `hd_candidate_manifest` field
retains the real recipe and complete ancestry. `--hd-only` omits the already
observed original/GOG and original/proxy baselines, not identity validation.
It still requires `--complete-hd`, the authenticated proxy and `--execute`.
A dry run imports no builder, reads no game assets and creates no files.

The existing system-x86-debugger harness is unchanged. It compares loaded
executable sections to the prepared disk image before observing its entry
point. It uses the existing diagnostic proxy and retains its limitations.
An HD-only runtime attempt additionally fails if it obtains no primary samples
or any sampled primary has dimensions other than the requested HD resolution.
Exact pixels, palettes, source identities, exceptions and cleanup observations
remain in the external run directory. No input is injected, no save is loaded,
and no failed legacy runtime report is relabeled.

The new matrix exercises the actual widget EXE at 1024x768 and 1920x1080 with
the full pinned `clash-assets` runtime. It retains only reports, source and
captures, never original/patched EXEs, wrapper DLLs or full resource archives.
The task-branch execution trigger is temporary and will be removed before
merge; subsequent runtime requires explicit manual workflow dispatch. Ordinary
pull requests run only nonexecuting source tests.

This adds a way to execute the new stage, not a claim that the menu, map, modal
widgets, glyphs, input or lifecycle passed runtime validation. Actual results
must be recorded separately with their source commit and candidate SHA. The
launcher defaults, protected stable stage, older candidate bytes and prior
failed captures remain unchanged. Menu-only observations cannot prove that a
barracks rendering defect was repaired, because that screen is not exercised.

# Runtime selection for the modal-widget candidate

`tools/real_exe_smoke.py` selects the exact `modalwidgets` recipe through
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

## Native debugger context

The system-x86-debugger harness compares loaded executable sections to the
prepared disk image before observing its entry point. It uses the existing
diagnostic proxy and retains its limitations. The first widget 1024x768 attempt
exposed a final debugger-context failure; the original failed report remains
unchanged. The follow-up retains the original process and primary thread
handles, checks both are alive while the debuggee is stopped, resolves their
system IDs to debugger IDs, selects them, and verifies the resulting identities
and readable instruction pointer before snapshotting. It never changes target
registers or substitutes a different thread after a crash. The actual identity
selection is recorded as `REAL_CONTEXT`, rather than inferred from a pass flag.

An HD-only runtime attempt additionally fails if it obtains no primary samples
or any sampled primary has dimensions other than the requested HD resolution.
Exact pixels, palettes, source identities, exceptions and cleanup observations
remain in the external run directory. No input is injected, no save is loaded,
and no failed legacy runtime report is relabeled. The loaded-code comparison is
not execution of the candidate's complete generated CDB probe, and a startup
observation is not full-stage acceptance.

## Actual observations and future execution

The [September 20 checkpoint](../../reports/modal_widget_runtime_20260920.md)
records the exact real widget EXEs at 1024x768 and 1920x1080, the first failed
1024x768 diagnostic, and fresh bounded observations after context selection.
Both follow-up runs reached the menu and retained full requested-size primary
buffers. The 1080p GDI window capture is clipped outside its visible 1024x768
region and is not accepted as full-window rendering proof.

The workflow retains only reports, source and captures, never original/patched
EXEs, wrapper DLLs or full resource archives. The temporary task-branch trigger
was removed before merge. Runtime is now manual `workflow_dispatch` with
`execute=true` only; ordinary pull requests run only nonexecuting source tests.

This adds a way to execute the new stage, not acceptance of its map, barracks,
glyphs, input or lifecycle. The launcher defaults, protected stable stage,
older candidate bytes and prior failed captures remain unchanged. Menu-only
observations cannot prove that the modal x=1000 defect was repaired, because
that screen is not exercised.

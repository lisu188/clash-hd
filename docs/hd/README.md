# HD Documentation

Durable Clash95 HD architecture notes live here. These files explain the stable
stage, evidence boundaries, validation ladder, route inventories, and release
criteria for the HD mod.

Use the root `patch_clash95_hd.py` wrapper for user-facing patch commands. When
editing implementation details, update `src/patcher/patch_clash95_hd.py` and
record patch evidence in `CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md`.

Start endurance validation from `HD_SOAK_TEST_ROADMAP.md`. The soak harness is
opt-in, writes raw frames outside the repo, and keeps validation-only routes
non-promoting until the required input and long-run gates pass.

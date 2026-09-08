# Astra preparation: latest repo-only review

- Aggregate generated: **2026-09-05T10:26:47+02:00**.
- Result: **164/166 checks passing; 2 unfinished release checks failing**.
- Shared `.codex/config.toml` contains only `model = "gpt-6-astra"`; TOML parsing and Git ignore checks pass. Existing `ultra` reasoning effort is inherited, and global configuration is unchanged.
- Both documentation guards use the canonical handoff by default. Legacy overrides remain available; explicitly supplied missing documents fail, including relative project-summary paths. The handoff is read once for the three legacy roles.
- Both guards also pass after the final handoff update; scoped `git diff --check` passes.
- Both focused fixture suites pass, including defaults without local handoff notes, missing canonical/override documents, stale claims, and required evidence references. Existing phrase, approval, and evidence checks remain intact.

## Remaining aggregate failures

- `hd_soak_long_report_guard`: the short ladder is incomplete and neither required 2h route has passing proof.
- `hd_endurance_release_checklist`: endurance, manual-input, and validation-stage promotion requirements remain incomplete. Existing battle callback evidence remains proven; it is separate from promotion proof.

These are release evidence gaps, not requirements for completing Astra preparation. The aggregate command exited 0; its report is the authority for individual gate results.

## Scope and preservation

The current checkout includes separate unfinished HD completion changes. They were compared with the saved initial inventories and preserved. The original Astra inventory and the fresh review baseline have no missing files; this review changes only the documentation consistency guard, its fixture, the current handoff, and relevant generated reports. No game/debugger execution, patch changes, promotion, artifact cleanup, commit, or push occurred in this review. The aggregate's bounded dry-run and negative-approval checks stop before game/debugger execution.

- [Detailed review record](astra-preparation-review-current.json)
- [Aggregate summary](current-evidence-refresh-current.json)
- [Original preparation snapshot](astra-preparation-current.md), retained as dated history
- [Current agent handoff](../../docs/hd/AGENT_HANDOFF.md)
- [Official Codex configuration guidance](https://learn.chatgpt.com/docs/config-file/config-basic)

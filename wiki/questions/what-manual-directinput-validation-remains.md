---
title: What Manual DirectInput Validation Remains
type: question
status: open
created: 2026-05-12
updated: 2026-05-12
tags:
  - question
  - clash95
  - input
---

# What Manual DirectInput Validation Remains

## Question

Which HD input behaviors still need manual or real DirectInput validation beyond
scripted CDB and synthetic mouse evidence?

## Context

The project has strong CDB evidence for many routes, but the operating notes
distinguish `SendInput`/`PostMessage` or debugger-forced clicks from proof that
manual DirectInput mouse behavior works. [source page:
[[Clash95 Engine Viewport Patch Notes]]]

## What Is Known

- Dynamic-origin mouse work fixed the root screen-origin removal issue for the
  HD/windowed workflow. [source page: [[Clash95 Engine Viewport Patch Notes]]]
- The menu load route recommends held clicks and CDB proof rows because click
  cadence and startup state can otherwise mislead automation. [source page:
  [[Clash95 Menu Load Route Notes]]]
- Castle/barracks centered input has debugger evidence for targeted descriptor
  and action paths. [source page: [[Castle Barracks UI CDB Validation]]]

## Current Boundary

- Five remaining manual targets are still pending: stable menu load, stable HD map input, right-bottom validation input, castle barracks centered input, and castle overview centered input.
- No-popup evidence remains the default operating boundary. Do not launch
  Clash95, CDB, wrappers, PowerShell harnesses, or visible windows unless the
  user explicitly approves; visible helpers require `-AllowVisibleRuntime`.
- `rightbottomcompose` remains validation-only with
  `stable_stage_should_change=False`.
- `castlecenter-all` remains validation-only with
  `stable_stage_should_change=False`.
- The no-popup boundary guard is PASS with `required_guard_count=7`,
  `required_supporting_report_count=90`, and `required_report_count=97`.
- The manual DirectInput run plan is repo-only and non-promoting: it emits one
  future visible command template per remaining target, every command includes
  `-AllowVisibleRuntime`, and `proof_ready=False` remains blocked until an
  approved manual proof manifest validates.
- The right-bottom action-menu blocker triage is repo-only and non-promoting:
  controlled composition recovers the lower/right UI, but natural owner/action
  draw rows are still absent behind the owner-flag/load-route gate.
- The right-bottom visual artifact guard is repo-only and non-promoting: it
  keeps the current stripy/out-of-place natural right-bottom UI artifact
  blocked until natural owner/action rows or approved manual proof replace it.
- The load-slot transition run plan is repo-only and non-promoting: it emits
  hidden-desktop command templates for rows 3-5, but does not launch CDB or
  treat future transition entry proof as stable promotion by itself.
- The load-slot transition probe guard now requires the late select and accept
  breakpoints to compare against `__LOAD_SLOT__`; this fixed the old row-5
  hard-code so rows 3 and 4 can be probed honestly.
- The load-slot transition geometry guard pins rows 3-5 to the exact planned
  coordinates: slot 3 `(320,232)`, slot 4 `(320,254)`, and slot 5 `(320,276)`,
  with raw mouse globals shifted by `<< 6`.
- The load-slot transition probe preview is repo-only and non-promoting: it
  simulates the generated row-specific CDB text for rows 3-5 and verifies there
  are no unresolved placeholders, the raw mouse values match the geometry
  guard, and late select/accept conditions target the requested row.
- The load-slot transition readiness matrix is repo-only and non-promoting: it
  aggregates the entry-gap report, probe guard, run plan, geometry guard,
  generated-probe preview, and summary parser tests into one hidden next-run
  gate while still requiring future logs to prove entry, slot match, and
  `LOADSAVE`/`PlayGame`.
- The right-bottom slot fixture plan is explicitly non-promoting: it maps the
  route-compatible slot-5 save state into isolated row 0 only for future
  hidden-desktop evidence, preserving the natural slot-5 menu blocker.
- `scripts/smoke/prepare_right_bottom_slot_fixture.ps1` is guarded as a dry-run helper:
  the source guard requires `-Execute` before copying, permits `-SeedWorkDir`
  only as a non-save seed from `C:\Clash`, and rejects repository, source
  workdir, or live `C:\Clash\save` fixture output.
- The right-bottom slot fixture runtime plan is also non-promoting: it emits
  the future `-SeedWorkDir` dry-run, execute, and hidden-desktop CDB commands,
  then the strict result-parser command with load-success, slot-match,
  owner-bit2, and owner/action gates, but keeps the proof class
  `non_natural_isolated_fixture` until natural rows 3-5 reach load entry.
- The right-bottom slot fixture result parser is covered by repo-only tests:
  future logs must distinguish missing load, owner-flag-blocked, owner-loop
  without action, owner/action reached, and AV failure before any fixture
  result can be treated as evidence.

## Uncertainty

- Synthetic hidden-desktop input evidence does not fully prove manual
  DirectInput behavior across real mouse movement, route timing, wrappers, or
  all UI screens. [source page: [[Clash95 Engine Viewport Patch Notes]]]

## Candidate Answers

- Interpretation: manual checks should focus on the active HD map stage, menu
  load route, map edge scrolling, minimap/action UI interactions, and centered
  castle/barracks clicks.
- Interpretation: DirectInput validation should be recorded as a separate
  evidence class from no-popup geometry proof.

## Needed Sources Or Checks

- Define a small manual smoke checklist that records executable SHA, stage,
  wrapper state, input route, visual result, and whether DirectInput movement
  and held clicks behave as expected.
- Keep CDB evidence and manual evidence linked but separate in future source
  summaries and log entries.

## Related Pages

- [[Dynamic-Origin Mouse Input]]
- [[CDB-Only Validation]]
- [[HD Map Evidence Chain]]
- [[Castle UI Centering State]]

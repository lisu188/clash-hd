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

## Uncertainty

- Synthetic hidden-desktop input evidence does not fully prove manual
  DirectInput behavior across real mouse movement, route timing, wrappers, or
  all UI screens. [source page: [[Clash95 Engine Viewport Patch Notes]]]
- The remaining manual validation matrix is not yet enumerated in the wiki.

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


---
title: Which Castle Overview Path Needs Centering
type: question
status: open
created: 2026-05-12
updated: 2026-05-12
tags:
  - question
  - clash95
  - castle-ui
---

# Which Castle Overview Path Needs Centering

## Question

Which castle overview/interior dispatcher path should receive the next narrow
centering hook after the barracks/action-panel route?

## Context

Castle/barracks centered presentation and input are validated for targeted
paths, but the full castle overview/interior route still finishes on a native
640x480 surface. [source page: [[Castle Barracks UI CDB Validation]]]

## What Is Known

- The centered barracks presentation patch places the native UI at `(80,60)`.
  [source page: [[Castle Barracks UI CDB Validation]]]
- The centered input patch maps centered mouse coordinates back into native UI
  coordinates during relevant hit-test routines. [source page:
  [[Castle Barracks UI CDB Validation]]]
- The catalog run found seven reachable castle/interior command callbacks and
  reported a native 640x480 castle-screen surface. [source page:
  [[Castle Barracks UI CDB Validation]]]
- The report names the `00422180` / `00422305` / `00422020` castle
  surface/present path as needing its own narrow centering hook. [source page:
  [[Castle Barracks UI CDB Validation]]]

## Uncertainty

- The exact hook point and copyback/present strategy for the full castle
  overview path remain open. [source page:
  [[Castle Barracks UI CDB Validation]]]
- The current proof does not validate every full castle overview descriptor.
  [source page: [[Castle Barracks UI CDB Validation]]]

## Candidate Answers

- Interpretation: start with the full castle-screen routine and its present
  path, then pair visual centering with descriptor hit-test transforms only
  after the draw surface is understood.
- Interpretation: reuse the barracks `(80,60)` coordinate transform where the
  overview dispatcher uses the same native coordinate assumptions, but only
  after CDB proves the shared path.

## Needed Sources Or Checks

- Add a focused CDB probe around the castle overview present/surface path.
  [source page: [[Castle Barracks UI CDB Validation]]]
- Use the existing catalog and geometry parser outputs to define acceptance
  checks for an 800x600 centered overview surface. [source page:
  [[Castle Barracks UI CDB Validation]]]

## Related Pages

- [[Castle UI Centering State]]
- [[Centered UI Coordinate Transform]]
- [[DirectDraw Surface Target Split]]


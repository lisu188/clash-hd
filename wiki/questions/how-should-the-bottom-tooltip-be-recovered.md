---
title: How Should The Bottom Tooltip Be Recovered
type: question
status: open
created: 2026-05-12
updated: 2026-05-12
tags:
  - question
  - clash95
  - tooltip
---

# How Should The Bottom Tooltip Be Recovered

## Question

Should the HD patch recover a native-style bottom tooltip/status strip, relocate
tooltip text as an overlay, or leave the 12x9 map surface dominant and compose
UI differently?

## Context

The bottom-tooltip report treats tooltip/status recovery as a sibling problem
to border recovery and warns against silently folding it into map drawing.
[source page: [[Border And Bottom Tooltip Recovery Reports]]]

## What Is Known

- Possible bottom-tooltip owners include selected unit info, action/status
  panel, hover-only text, notification, and info-window paths. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]
- The report recommends proving whether text executes, where it draws, and
  whether the failure is redraw order, surface/present, anchor relocation, or
  hitbox pairing. [source page: [[Border And Bottom Tooltip Recovery Reports]]]
- The current no-popup surface route is useful for geometry but not final
  authentic-color evidence. [source page: [[Border And Bottom Tooltip Recovery Reports]]]

## Uncertainty

- The desired final HD design for bottom tooltip placement has not been chosen.
  [source page: [[Border And Bottom Tooltip Recovery Reports]]]
- It is not yet clear whether bottom/status routines are skipped by route/state
  conditions or are drawing to the wrong surface/region. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]

## Candidate Answers

- Interpretation: preserve a native-style bottom strip if CDB proves the stock
  owner can be recovered with narrow anchor or copyback changes.
- Interpretation: use an overlay if the stock strip conflicts with the 12x9 map
  design or if authentic frame recovery proves too invasive.

## Needed Sources Or Checks

- Run a bottom-tooltip CDB probe with filtered text and present rows for the
  candidate owner ranges. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]
- After ownership is known, choose between redraw-order, surface/present,
  anchor relocation, or paired hitbox changes. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]

## Related Pages

- [[Right-Bottom UI And Bottom Tooltip Recovery]]
- [[DirectDraw Surface Target Split]]
- [[No-Popup Surface Dump]]


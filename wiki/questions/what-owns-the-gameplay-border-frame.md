---
title: What Owns The Gameplay Border Frame
type: question
status: open
created: 2026-05-12
updated: 2026-05-12
tags:
  - question
  - clash95
  - ui-recovery
---

# What Owns The Gameplay Border Frame

## Question

Which function or owner path draws the ornate gameplay border frame, especially
the lower/right regions that are missing from the current 800x600 HD map view?

## Context

The current HD map evidence says the map cells themselves draw when visibility
permits, but the lower/right frame and bottom regions remain visually
unrecovered. [source page: [[Current HD Map Evidence]]; source page:
[[Border And Bottom Tooltip Recovery Reports]]]

## What Is Known

- The border-frame report identifies `sub_418700`, `dword_526990`,
  descriptor draw/hit-test helpers, action-panel functions, and panel/text
  functions as leads. [source page: [[Border And Bottom Tooltip Recovery Reports]]]
- The CDB validation report says `dword_511D40` is not currently the missing
  HD border/tooltip owner. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]
- The normal hidden-desktop load-slot route does not enter the right-bottom
  action/status owner path. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]

## Uncertainty

- It is not yet known whether the frame is never drawn, drawn before terrain
  and overwritten, drawn to a scratch surface, or drawn at native-only anchors.
  [source page: [[Border And Bottom Tooltip Recovery Reports]]]

## Candidate Answers

- Interpretation: `dword_526990` could be a late overlay/frame callback if it
  is non-null in the relevant route, but current reports say its ownership still
  needs proof. [source page: [[Border And Bottom Tooltip Recovery Reports]]]
- Interpretation: the border could be split across descriptor, action/status,
  and generic panel/text paths rather than one single owner.

## Needed Sources Or Checks

- Add or run a late-armed CDB probe that logs `sub_418700`, `dword_526990`, UI
  frame candidates, and pixel samples in frame bands. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]
- Compare samples before and after tile redraw, overlay callbacks, and final
  `SURFDUMP_READY`. [source page: [[Border And Bottom Tooltip Recovery Reports]]]

## Related Pages

- [[Right-Bottom UI And Bottom Tooltip Recovery]]
- [[DirectDraw Surface Target Split]]
- [[CDB-Only Validation]]


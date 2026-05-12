---
title: CDB-Only Validation
type: concept
aliases:
  - hidden-desktop CDB validation
status: active
created: 2026-05-12
updated: 2026-05-12
tags:
  - concept
  - clash95
  - validation
---

# CDB-Only Validation

## Definition

CDB-only validation is the current Clash95 evidence policy that favors scripted
x86 CDB runs, hidden-desktop launches, no-popup surface dumps, and repo-side
parsers over VirtualBox probing. [source page: [[Clash95 Engine Viewport Patch Notes]]]

## Why It Matters

Interpretation: the CDB-only route keeps runtime evidence repeatable and local,
while avoiding the older VirtualBox route that the project now treats as
historical context. [source page: [[Clash95 Engine Viewport Patch Notes]]]

## Key Claims

- The current no-popup workflow uses `run_cdb_surface_dump.ps1` and an x86 CDB
  harness to collect map and UI evidence. [source page: [[Current HD Map Evidence]]]
- The current HD map status depends on CDB surface-dump evidence paired with
  repo-only patch and evidence checks. [source page: [[Current HD Map Evidence]]]
- Menu-route validation still uses CDB proof rows to distinguish real gameplay
  entry from menu-like frames. [source page: [[Clash95 Menu Load Route Notes]]]
- Border/tooltip recovery plans require late-armed CDB probes rather than hot
  present/text breakpoints from process start. [source page:
  [[Border And Bottom Tooltip Recovery Reports]]]

## Examples

- `SURFDUMP_PLAYGAME`, `SURFDUMP_READY`, and visibility coverage rows are used
  to classify no-popup map evidence. [source page: [[Current HD Map Evidence]]]
- Castle/barracks validation uses extra CDB probes and parser gates to prove
  centered presentation and input behavior. [source page:
  [[Castle Barracks UI CDB Validation]]]

## Related Concepts

- [[No-Popup Surface Dump]]
- [[Visibility-Zero Versus Rendering Defect]]
- [[Dynamic-Origin Mouse Input]]
- [[DirectDraw Surface Target Split]]

## Open Questions

- [[What Manual DirectInput Validation Remains]]

## Sources

- [[Clash95 Engine Viewport Patch Notes]]
- [[Current HD Map Evidence]]
- [[Clash95 Menu Load Route Notes]]
- [[Border And Bottom Tooltip Recovery Reports]]
- [[Castle Barracks UI CDB Validation]]


# Local release-validation runbook

Release validation that requires the original game is **local-only**.

## Public prerequisites

Before any local runtime work:

1. Public-source boundary check passes:
   `python tools/check-public-boundary.py`.
2. Relevant source-only patch/launcher tests pass.
3. The candidate is produced outside the repository from a user-supplied,
   lawfully obtained executable.
4. The patcher verifies the expected executable hash and all old bytes before
   writing replacements.

## Local runtime validation

Use an isolated candidate directory outside the checkout. Keep the original
executable unchanged. Runtime checks may cover startup, menus, map rendering,
input, modal screens, battle rendering, save/load continuity, and endurance as
appropriate to the candidate.

Screenshots, captures, debugger logs, dumps, saves, and other retail-derived
evidence must remain outside public source control. Record only concise,
non-proprietary conclusions when updating public documentation.

## Promotion

A profile or resolution is promoted only when its source-level checks and the
required local runtime validation have both succeeded for the exact candidate.
A passing public CI job alone never establishes runtime acceptance.

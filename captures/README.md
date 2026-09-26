# Captures

The captures tree is split by role:

- `current/`: compact evidence summaries and JSON used by repo-only checks,
  reports and status pages. These include dated and superseded checkpoints;
  read each timestamp and source/candidate binding before calling it current.
- `archive/`: historical captures, screenshots, CDB surface dumps, and other
  evidence that remains useful but should not crowd the root.

Large raw dumps, proprietary game assets, executables, DLLs, saves, ISOs, and
credentials do not belong here or anywhere else in git.

The [current handoff](../docs/hd/AGENT_HANDOFF.md) owns the interpretation of
active versus historical results. Its September 26 availability record notes
that the former `C:/ClashCaptures` and `C:/ClashTests` trees were removed.
Retained manifests can describe the original observations but do not recreate
the missing pixels, logs, candidate bundles or producer snapshots. Check file
availability and hashes before claiming a replay or screenshot verification.

Preserve raw failures, incomplete runs and exact identities when adding a new
report. Do not relabel controlled native calls as ordinary/manual input or
hidden surfaces as final wrapper composition. Use the
[release evaluator](../docs/hd/COMPLETE_HD_EVIDENCE.md) for candidate-bound
eligibility and the [development guide](../docs/hd/DEVELOPMENT.md) for report
generation. Aggregate and individual guard CLIs may write here by default;
redirect diagnostic outputs to task scratch when a durable refresh is not the
intended change.

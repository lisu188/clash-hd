# Tools

This directory contains dependency-light Python helpers for parsing CDB logs,
building evidence summaries, checking patch manifests, guarding policy, and
running repo-only tests.

Keep tools separate by purpose. Do not merge unrelated validators just to reduce
file count; the compact structure comes from moving source families into the
right directories, not from hiding distinct checks inside larger scripts.

Run all tool tests and optionally write a durable current-evidence summary with:

```powershell
python tools\repo_test_sweep.py --write-json captures\current\repo-test-sweep-current.json --write-markdown captures\current\repo-test-sweep-current.md --require-pass
```

The equivalent manual loop is:

```powershell
Get-ChildItem tools\test_*.py | ForEach-Object { python $_.FullName }
```

Endurance-road helpers worth knowing:

- `tools/hd_soak_report.py`: validates one executed soak report, including
  canonical `C:\Clash`, `C:\ClashTests\hd-soak`, and `C:\ClashCaptures\hd-soak`
  roots.
- `tools/hd_soak_failure_triage.py`: classifies failed short-soak reports and
  refuses raw `passed=true` output when the soak report guard rejects the
  report contract.
- `tools/hd_soak_harness_guard.py`: source-inspects the opt-in soak harness and
  fails if the dry-run handoff can drift from `-RequirePass -Json`.
- `tools/hd_soak_dry_run_plan.py`: runs the current soak harness in dry-run
  JSON mode and persists the approval handoff plan without launching the game.
  Approval handoffs treat plans older than 12 hours as stale.
- `tools/hd_endurance_next_actions.py`: summarizes the next endurance action
  and surfaces the dry-run-plan verified execute command when available. It
  keeps focused soak validation separate from broader evidence refresh.
- `tools/hd_soak_approval_preflight.py`: emits the approval packet for the next
  visible-runtime soak and requires the current dry-run plan to match.
- `tools/current_evidence_refresh.py`: prefers the canonical first short-step
  soak report over the legacy compatibility report once that canonical report
  exists.
- `tools/hd_soak_long_report_guard.py`: fail-closed guard for future 2h+ representative-route soak evidence.
- `tools/hd_continuity_status.py`: fail-closed state-continuity guard for future save/load, turn, and campaign proofs.
- `tools/first_mission_visual_audit.py`: audits archived first-mission PNG
  frames for horizontal/vertical stripe signatures and large black UI patches.
- `tools/first_mission_minimap_surface_summary.py`: summarizes the focused
  first-mission CDB rows that sample minimap backing memory and final HD
  surface black-patch regions, with optional map coverage and visibility JSONs
  to separate visibility-zero map cells from render failures.
- `tools/hd_endurance_release_checklist.py`: aggregates the release-horizon gates.

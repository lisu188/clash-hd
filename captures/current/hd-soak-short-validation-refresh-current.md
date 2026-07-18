# HD Soak Short Validation Refresh

- Overall: PASS
- Generated: `2026-07-18T19:30:53.089250+00:00`
- Runtime policy: repo-only short-soak validation refresh; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Manifest: `captures\current\hd-soak-short-artifact-manifest-current.json`
- Status: `validated_reports`
- Reports found: `2/5`
- Guards written: `2`
- Triage written: `2`
- Failed runtime reports classified: `1`

## Steps

- `short2_menu_idle`: status=`validated_pass` report_exists=`True` guard=`True` triage=`True`
- `short2_map_idle`: status=`validated_failed` report_exists=`True` guard=`True` triage=`True`
- `short10_map_idle`: status=`no_report` report_exists=`False` guard=`False` triage=`False`
- `short10_map_pan`: status=`no_report` report_exists=`False` guard=`False` triage=`False`
- `short30_map_pan`: status=`no_report` report_exists=`False` guard=`False` triage=`False`

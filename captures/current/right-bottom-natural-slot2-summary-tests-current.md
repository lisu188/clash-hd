# Right-Bottom Natural Slot-2 Summary Tests

- Status: PASS
- Generated: `2026-07-17T15:36:31+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the natural slot-2 parser and static probe guard fail closed; this support-only check is not a real runtime result

## Tests

- `natural slot-2 summary accepts a complete synthetic proof while preserving evidence limits`
- `natural slot-2 summary rejects a wrong target record flag`
- `natural slot-2 summary requires verified load choice 5 from slot 2`
- `natural slot-2 summary rejects missing or misordered composition markers`
- `natural slot-2 summary rejects visible fallback or the wrong probe profile`
- `natural slot-2 static guard rejects forbidden mutations and control-flow forcing`
- `natural slot-2 summary rejects runtime forcing markers`
- `natural slot-2 summary CLI writes JSON/Markdown and honors --require-pass`
- `natural slot-2 summary CLI returns 2 for a failing log`

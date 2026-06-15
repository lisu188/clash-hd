# Battle UI Evidence Matrix Tests

- Status: PASS
- Generated: `2026-06-15T22:36:06+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for matrix CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the focused battle/right-bottom command lane stays below 100% until real visible click-to-callback evidence exists

## Tests

- `battle UI evidence matrix accepts the current battle/right-bottom command evidence shape`
- `battle UI evidence matrix fails closed for AV or missing reachability in each summary`
- `battle UI evidence matrix rejects feature regressions in command, grid, input, redraw, and modal proof`
- `battle UI evidence matrix rejects constructed-fixture render-begin guard regressions`
- `battle UI evidence matrix rejects missing constructed-fixture synthetic release proof`
- `battle UI evidence matrix rejects constructed-fixture pre-gate rearm regressions`
- `battle UI evidence matrix rejects native-click attempts in the visual-click fixture`
- `battle UI evidence matrix rejects missing visible command readiness`
- `battle UI evidence matrix rejects visible-input pass overclaims without real click consumption`
- `battle UI evidence matrix rejects real-click count mismatches`
- `battle UI evidence matrix CLI writes JSON/Markdown outputs and honors --require-pass`

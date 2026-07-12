# Right-Bottom Natural Route Guard Tests

- Status: PASS
- Generated: `2026-07-12T21:10:53+02:00`
- Runtime policy: repo-only fixture tests; launches only in-process parser code; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the natural right-bottom action-route guard fails closed unless the command-99 owner loop is reached, the exact 00433C20 owner-loop descriptor model is present, the 004338E0 descriptor is parked at (1000,426), owner flag bits are zero, owner/action renderer rows are absent, and no AV rows are present

## Tests

- `right_bottom_natural_route_guard passes when command 99 reaches the owner loop with owner_flag 0x00 and the exact 00433C20 descriptor model`
- `right_bottom_natural_route_guard fails when the action descriptor leaves its expected parked coordinate`
- `right_bottom_natural_route_guard fails when the static owner-loop descriptor model drifts`
- `right_bottom_natural_route_guard fails when owner flag bits allow the action route`
- `right_bottom_natural_route_guard fails when owner/action renderer rows fire`

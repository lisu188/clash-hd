# Castle Save Owner-Flag Scan Tests

- Status: PASS
- Generated: `2026-06-17T09:47:58+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the installed-save owner-flag scan stores only metadata, detects natural 004338E0 bit-2 route candidates, and fails closed when required save evidence is unavailable

## Tests

- `castle_save_owner_flag_scan reports current-style owner blocks without requiring bit 0x02`
- `castle_save_owner_flag_scan detects a natural action-eligible owner flag bit 0x02`
- `castle_save_owner_flag_scan CLI writes JSON/Markdown and fails closed under --require-action-eligible`
- `castle_save_owner_flag_scan fails closed when the saves root is missing`

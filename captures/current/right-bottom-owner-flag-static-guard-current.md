# Right-Bottom Owner-Flag Static Guard

- Overall: PASS
- Generated: `2026-07-18T10:17:56+02:00`
- Runtime policy: local original-executable byte inspection only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: the natural right-bottom action route must retain the command-99 owner-loop callback, owner-global writes, 004338E0 owner flag bit-2 early-return gate, and 00433C20 owner-loop bit gates before the current owner-flag blocker can be treated as understood evidence
- Executable: `C:\Clash\clash95.exe`
- Expected SHA-256: `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`
- Actual SHA-256: `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`
- Patterns: `9/9`
- Command 99 callback verified: `True`
- Owner globals verified: `True`
- 004338E0 bit-2 gate verified: `True`
- Owner-loop bit gates verified: `True`

## Patterns

- `command_99_callback_pointer`: `PASS` VA `0x00422709` file `0x021B09` - castle overview command 0x63 selects callback 00433C20
- `owner_global_532150_write`: `PASS` VA `0x00433C26` file `0x033026` - 00433C20 stores the owner pointer in dword_532150
- `owner_global_53214c_write`: `PASS` VA `0x00433C4B` file `0x03304B` - 00433C20 stores the selected owner index/state in dword_53214C
- `owner_global_532154_write`: `PASS` VA `0x00433D5A` file `0x03315A` - 00433C20 stores the owner UI surface pointer in dword_532154
- `action_4338e0_bit2_early_return`: `PASS` VA `0x004338E6` file `0x032CE6` - 004338E0 immediately returns unless owner flag bit 0x02 is set
- `action_433914_stock_owner_call`: `PASS` VA `0x00433914` file `0x032D14` - the validation wrapper targets only the post-gate owner/action draw call
- `owner_loop_bit2_gate`: `PASS` VA `0x00433CE3` file `0x0330E3` - 00433C20 checks owner flag bit 0x02 before the action descriptor lane
- `owner_loop_bit1_gate`: `PASS` VA `0x00433CFF` file `0x0330FF` - 00433C20 checks owner flag bit 0x01 before an adjacent owner descriptor lane
- `owner_loop_bit8_gate`: `PASS` VA `0x00433D1B` file `0x03311B` - 00433C20 checks owner flag bit 0x08 before an adjacent owner descriptor lane

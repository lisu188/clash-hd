# Right-Bottom addon_flags Save Fixture

- Overall: PASS
- Mode: `plan-only`
- Generated: `2026-07-03T09:04:31.388992+00:00`
- Runtime policy: repo-only fixture planner; reads at most one source save and writes only JSON/Markdown evidence unless --output-save is passed; never mutates C:\Clash\save and never launches Clash95, CDB, wrappers, PowerShell, or visible windows
- Promotion policy: non-promoting: the copied+patched save makes the right-bottom production panel drawable on a natural route, but promotion still requires approved real-input (manual DirectInput) proof per reports/final_hd_validation_matrix.md
- Source save: `C:\Clash\save\0.dat`

## Offset math (disassembly-verified)

- Building index: `0`
- Formula: `16 + 509674 + building_index*467 + 416`
- addon_flags file offset: `0x0007C89A` (`510106`)
- Record offset: `0x0007C6FA`
- Production flag bit: `0x02`
- Record stride: `467`, count: `100`
- Expected save size: `586414` (`0x0008F2AE`)

## Notes

- source save C:\Clash\save\0.dat not readable here; running plan-only (offset math is host-independent)

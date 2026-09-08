# Remaining framed modal routes: native contracts

Offline source inventory, 2026-09-06, extending the
[screen inventory](FRAMED_SCREEN_VALIDATION.md). This is not a runnable probe,
runtime report or input proof. The frozen modal producer/validator files were
not changed during this review.

## Binding and method

Read-only original `C:/Clash/clash95.exe` SHA-256:
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
Source `C:/Clash/clash95.asm` SHA-256:
`b298e8c85086f542ebc8b02c26904019aa8278d531cbf02a88d785170cbb4436`.
MSVC 14.44.35207 `dumpbin /disasm` independently confirmed instruction
boundaries and call targets against the original. Addresses are preferred-base
VAs; `RVA = VA - 00400000`. File offsets below use the actual PE mapping.

The [framed builder](../../tools/build_framed_candidate.py), SHA-256
`4178745fabb1e2270efcbdc72bf4999f97b0bca23bdad78db743a5db1b724d7a`,
reconstructed 800x600 with `minimap_viewport=false` entirely in memory:
`7fad16f167205fb34ecbc99a6a1ff6180c710807f99b19f25efb48a8b1c8d15b`.
Exact stage:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation
```

Future packets must reconstruct their own resolution/minimap option and check
loaded candidate bytes, including inherited modal hooks. This one comparison
does not validate another image. No executable, save or capture was written.

## Court: one converged initial presentation

Overview case `0042255B` selects ECX=`0044FE70`, command ESI=`86`. The existing
flipping gate and native resource prelude lead to `CALL ECX` at `0042262C`,
passing castle owner in EAX, return `0042262E`. This can extend the current
controlled overview dispatch without skipping Court initialization.

Entry saves six registers plus `4C` local bytes: **call/return ESP is entry
ESP−100** at the initial presentation. Court stores owner at `005443FC`, reads
three prisoner-action bytes at owner `+1C0+6*i`, and initializes descriptors.
The early `0044FEAD` branches choose descriptor states and rejoin the loop.
Five nation-presence branches select statistics/name drawing and converge;
they do not require five guessed capture stops.

Final draw order: `0044FC70` → `0044FD90` → descriptor draw `00419D80` with
list `00518DC8` → resource copy `00405020` → **present `0045045F`, return
`00450464`**. Call EAX must be `00544CD8`; owner `005443FC` must remain the
verified castle. `00450479` is the later input loop. These route/stop bytes
match the reconstructed candidate.

Smallest extension: Court route with case `0042255B`, command `86`, entry
`0044FE70`, present `0045045F`, frame depth 100 and the existing parent return
contract. Add loaded-byte checks and actual owner/resource observations
(`005443F8/005443F0` nonnull), with actual prisoner/nation state disclosed.
Stop before the input loop: its later `0044EB70` calls write prisoner actions.
Court draws to both memory map and primary. A map-only image may omit names
or controls; inspect actual layers before claiming complete visual composition.

## Recruitment/detail: initialize barracks, then its descriptor

The descriptor **starts at `00514FF5`** in list `00514FC0`. `00515015` is its
`+20` callback pointer, value `004338E0`, not its base. Its native label is
Production. Continue full barracks initialization through presentations
`00433E72`, `00433E86`, `00433E95` to `00433EB4`. Check `00532150` equals the
castle, loaded barracks resources, unchanged physical surface and installed
lower callback `00433BF0`. Do not reuse the old probe's short return at
`00433D5F` or jump to `0043390F`; both bypass native setup.

Full dispatch is barracks scan `00433EDC` → `00419DC0` → widget call
`00419C5D` → callback `004338E0`, EAX=`00514FF5`, return `00419C60`.
A direct descriptor-callback invocation from initialized barracks could be a
smaller **explicitly controlled** screenshot route, but is not a click.

`004338E0` calls descriptor animation `00419ED0` / `Render_Begin`, then checks
owner `+1A0 & 2`. Missing bit 2 returns at `004338F4/5` without recruitment.
Native resource setup and `Render_Pump` precede **call `00433914` → body
`00435BC0`**, return `00433919`. With outer callback-entry ESP S, that call is
S−4 and body entry is S−8. Observe bounded waits honestly; do not silently
skip the gate, animation or pump.

The body stores owner `00532218`, derives the actual artwork variant, resets
selection `00532220=0`, and builds list `00532224` using `004359B0` /
`Building_CanEquipAddon`. It also makes twelve RNG draws for UI state. Keep
native initialization; forcing index 1 does not prove a legal second entry.

Initial draw calls `004347A0` → `00435150` → `00435280` → `00435500`
(`00435D7F..00435D92`), then `00405020`, then **present `00435DAF`, return
`00435DB4`**. `00435DA5` is earlier EAX setup. Five saved registers and a later
EDI push give **body-entry ESP−24** at present/return. Capture before later
input-callback assignment and loop `00435DD2`; bind owner, selection/list,
resources and actual physical surface.

Current candidate `00433914` still calls the body directly. However,
`00435DA5` jumps to inherited bottom-strip copy `00513E80`, and `00435DAA`
loads callback wrapper `0051316F`. The present/return addresses are unchanged.
Authenticate both candidate hooks/recipes instead of requiring native MOVs.
Their composition may overlap the new frame; this route must expose that
behavior rather than inherit ordinary-map pixel claims.

## Battle initial: preserve the full attack ABI

Unit-versus-unit entry `Unit_Attack 0041AD20` takes attacker index in EAX,
defender index in EDX and the separately recorded option used by the controlled
route. Records are `gameData+23EE6+index*2D5` within the 500-record array.
Require distinct valid owners, occupied formations, signed world bounds and
adjacency. The older attack probe relocates the attacker and writes
`0051D01C`; these are constructed state, not natural movement. Any new route
must bind its isolated save and log every old/new mutation.

The actual call at `0041B145` supplies EAX/EDX as attacker/defender **pointers**,
EBX=0 for unit-versus-unit, ECX=`00412B60(attacker)` and a pushed
`00412B60(defender)` argument. That function returns boolean 0/1 for squad
type `21h/22h`. The old probe's ECX `result_ptr` label is inaccurate. Let native
attack setup produce these values. Building attack uses a separate nonzero
building-pointer contract and is not covered by this proposed lane.

Runner `0042E9E0` returns to `0041B14A`, saves three registers and `9C` local
bytes: initial-present frame **entry ESP−168**. Its `RET 4` consumes the one
caller-pushed argument. Reject an early attack return without runner entry.
The runner allocates state `00532048`, selects player `005202EC` / unit
`00511B58`, loads resources and installs owner `0042E8B0`.

Initial present is **`0042F2F5` → `0042F2FA`**, before turn/banner/input.
The candidate calls inherited centering wrapper `0051BA00`, not directly
`00460EA0`; authenticate its body and returned frame. Require live battle
state, valid selected slot/type, owner, resources, thread/stack and physical
surface. This is a separate attack protocol, not a castle Route row.

## Battle command: state change is not a completed frame

Tactical scan `0042E501` calls `00419DC0` with list `00514B78`. Click field
`00514B98` points to `0042D4E0`; hover/draw field `+1C` points to `004191F0`.
Widget call `00419C5D` passes descriptor EAX and returns to `00419C60`.
Require selected slot `[0,21]`, valid signed type, and nonzero type-table bytes
`0051257E+type*58` and `00512582+type*58` for enabled command admission.

Enabled entry `0042D520` calls `Render_Begin` at `0042D527`, returns at
`0042D52C`, toggles `0053205C`, changes descriptor state, and can call
`0042D290` to clear prior targeting. EBX/ECX/EDX are saved: frame depth 12.
**`0042D51C` has both disabled and enabled predecessors**: enabled state 2
with `00532060=0` also returns there. A hit alone is not a disabled result.
`0042D543` is still before remaining branch work, not a completed draw.

Extension requirements: retain initial battle proof; record exact descriptor
dispatch, enabled predicates, callback return and resulting state. Any bounded
input/wait override needs a separate explicit record. Then observe native
descriptor drawing and a subsequent completed composition/presentation with
matching owner before capture. That final boundary remains to be authenticated
for this candidate. Do not import the old early snapshots or broad wait
overrides as readiness. The historical July click-to-callback proof remains
resolved and separate.

## Post-battle writeback and the actual outcome-window branch

`HandleBattleResults 0042E5A0`, called at **`0042F46C`**, returning to
`0042F471`, clears/copies survivor formations into attacker, defender or
building records and logs results. It does not draw or present a screen.
`0042E6F0` is a temporary battle-grid-cell helper called from `00425A00`, not
an after-results boundary. Historical `BATTLE_DONE` marker labels cannot
establish different native semantics.

A narrower verified outcome branch exists: outcome EBP=1 or 2 plus the
matching player-control predicate can reach `0042F4DC` → `UI_ShowInfoWindow
00445360`, with localized retreat text and EDX=0. Within that complete native
message route, present **`0044540C` → `00445411`** precedes `Render_Begin`;
frame depth is 52 bytes. The message switches owner to `004617A0` and draws
primary content. These are proposed observation points for **that particular
outcome window**, not proof of a generic results screen or all outcome types.

A future outcome protocol must observe bounded native completion, the actual
result branch/writeback, specific message entry/text, complete draw and
returned presentation. Never force outcome flags or call writeback with
fabricated formations. Other victory/defeat window routes and capture-surface
contracts remain to be discovered; keep this matrix row as route discovery.

## Native byte fingerprints

Complete instruction spans below are review anchors, not standalone patch or
probe recipes. Future checks must bind surrounding flow and exact candidate.

| Site | VA / original file offset | Original hex | Current 800 candidate |
| --- | --- | --- | --- |
| Court entry | `0044FE70 / 04F270` | `53515256575583ec4cba01000000a3fc435400` | Same |
| Court call + return instruction | `0045045F / 04F85F` | `e83c0a0100890df4435400` | Same |
| Recruitment callback/gate | `004338E0 / 032CE0` | `52e8ea65feffa150215300f680a00100000275025ac3` | Same |
| Recruitment native owner/call | `0043390F / 032D0F` | `a150215300e8a7220000833d4c21530000` | Same |
| Recruitment entry | `00435BC0 / 034FC0` | `5351525655a3182253008a400225ff000000` | Same |
| Recruitment setup/present | `00435DA5 / 0351A5` | `b8d84c5400bb905b4300e8ecb00200` | `e9d6e00d00bb6f315100e8ecb00200` |
| Unit attack entry | `0041AD20 / 01A120` | `535156575581ec44030000` | Same |
| Runner call + return instruction | `0041B145 / 01A545` | `e89638010089c7` | Same |
| Runner entry | `0042E9E0 / 02DDE0` | `56575581ec9c000000` | Same |
| Initial battle present | `0042F2F5 / 02E6F5` | `e8a61b0300` | `e806c70e00` |
| Command entry | `0042D4E0 / 02C8E0` | `53515289c18b15581b5100` | Same |
| Result writeback call/test | `0042F46C / 02E86C` | `e82ff1ffff85ff` | Same |
| Conditional message call | `0042F4DC / 02E8DC` | `e87f5e0100` | Same |

Tower hit F9 still reaches overview default `004227FF`; no interior callback
is verified. `dw_14` at `00436300` remains unlinked in this source inventory.
Do not invent entry ABIs for either. The nine named castle views remain the
coverage inventory, with unimplemented routes and all unobserved outcomes
explicitly pending.

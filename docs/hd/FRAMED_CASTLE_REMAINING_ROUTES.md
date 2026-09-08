# Court and recruitment: native route contracts

Read-only source audit, 2026-09-06. These routes are pending diagnostics, not
implemented producer options or completed screenshot evidence. The seven
existing routes and their preserved results remain separate. No game, debugger,
input or capture was run for this audit.

Sources are the user-owned `C:/Clash/clash95.asm`, corresponding decompiled C,
and original executable SHA-256
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
The inspected modal-canvas candidate has SHA-256
`c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d`,
at 1024x768 with minimap-viewport support. The protected original and stable
stage are unchanged. See [canvas ownership](FRAMED_MODAL_CANVAS.md) and the
[broader route inventory](FRAMED_REMAINING_SCREEN_ROUTES.md).

## Court

The overview hit-map branch at `0042255B` selects callback `0044FE70` and
command `0x86`. It converges on the existing flip gate at `00422590` and
indirect callback at `0042262C`. Callback EAX is the selected castle pointer,
with the same bound root thread, owner and default render hook as the current
facility protocol. The source does not require a construction bit for court.

The entry saves six registers and subtracts `0x4C`, for 100 bytes of local
stack depth. Let H be the recorded map-handoff ESP. The existing overview
call chain puts court entry at H−64, with caller `0042262E`.

| Observation | VA → continuation | RVA / file offset | Actual bytes | ESP |
| --- | --- | --- | --- | --- |
| Overview branch | `0042255B` | `0002255B` / `0002195B` | `B9 70 FE 44 00 81 FE 86 00 00 00 74 1E` | H−60 |
| Court entry | `0044FE70` | `0004FE70` / `0004F270` | `53 51 52 56 57 55 83 EC 4C` | H−64 |
| Native PCX load | `0044FF21` → `0044FF24` | `0004FF21` / `0004F321` | `FF 56 30` | entry H−168, return H−164 |
| Full-surface blit | `0044FF84` → `0044FF87` | `0004FF84` / `0004F384` | `FF 52 24` | entry H−168, return H−164 |
| First present | `0045045F` → `00450464` | `0005045F` / `0004F85F` | `E8 3C 0A 01 00` | call/return H−164 |

The first-present continuation starts `89 0D F4 43 54 00 BB D8 4C 54 00`.
The load takes EAX=owned native E0, EDX=`stat.gfx`, EBX=the palette at
`005443F8`, ECX=0. `stat.s32` is loaded into `005443F0`. Both allocations
must be observed as valid; allocation failure is not an alternate successful
route. The selected castle is retained at `005443FC`.

Before loading, `0044EBA0` reads the three prisoner-state bytes at castle
`+1C0`, `+1C6`, `+1CC`. Values 1, 2 and 3 select different button states;
the branches converge on the same background load. Five player-presence and
statistics branches also converge before the single first-present call.
These are actual game-state observations, not fields to populate to obtain
a preferred screenshot. Court also reads current-player data and prisoner
identities; a valid selected-castle pointer alone is not a complete resource
or game-data admission check.

The initial blit is followed by primary-surface player artwork and text.
Later, the function changes `g_RenderDevice` back to E0 and draws graph
backgrounds, with partial native-to-primary copies. Immediately before first
present, calls `0045042F`→`0044FC70` and `00450434`→`0044FD90` draw prisoner
and queen content on primary; the descriptor redraw at `00450443` follows.
Consequently the early full-blit mirror is neither the final native canvas
nor the final primary composition. Adding a route record alone cannot prove
the complete court image.

## Recruitment through initialized barracks

Recruitment is not another direct overview callback. The native chain is:

1. Enter barracks `00433C20` through the existing overview route.
2. Complete its initialization and three initial presents at `00433E72`,
   `00433E86`, `00433E95`, each returning five bytes later.
3. Execute the callback initialization after `00433E9A` and reach the
   barracks loop at `00433EB4`.
4. Dispatch descriptor `00514FF5` through its callback `004338E0`.
5. Observe the native recruitment call `00433914`→`00435BC0`, returning to
   `00433919` only after the recruitment modal eventually closes.

The existing barracks screenshot stop at `00433E77` precedes steps 2 and 3.
It does not establish the initialized callback-loop state required here.

Barracks establishes castle pointer `00532150`, owner-resource style
`0053214C`, palette `00532154`, sprite set `00532144`, and the native auxiliary
surfaces at `005321F8` and `005321FC`. It initializes descriptor `00514FF5`
with x=155 when castle `+1A0 & 2` is set, or x=1000 when absent. The original
descriptor is x=155, y=426, state=1, resource-pointer address `00532144`,
sprite IDs 2/3, draw callback `00419770` at `+1C`, and action callback
`004338E0` at `+20` (`00515015`). Hover may add state bit 4.

Natural dispatch uses `00419C5D` (`FF 53 20`) → `00419C60` after native
hit-box and flip-gate checks, with EAX=the descriptor, not the castle.
`004338E0` first calls `00419ED0` to update that descriptor, then rechecks
`[00532150]+1A0 & 2`. Missing capability returns without entering recruitment.
A debugger-directed invocation must retain its explicit forced-route class
and distinct sentinel/stack contract; it is not native input proof.

| Observation | VA → continuation | RVA / file offset | Actual bytes |
| --- | --- | --- | --- |
| Descriptor callback | `004338E0` | `000338E0` / `00032CE0` | `52 E8 EA 65 FE FF A1 50 21 53 00 F6 80 A0 01 00 00 02 75 02 5A C3` |
| Recruitment call | `00433914` → `00433919` | `00033914` / `00032D14` | `E8 A7 22 00 00` |
| Recruitment entry | `00435BC0` | `00035BC0` / `00034FC0` | `53 51 52 56 55 A3 18 22 53 00` |
| Native PCX load | `00435C80` → `00435C83` | `00035C80` / `00035080` | `FF 56 30` |
| Full-surface blit | `00435D7C` → `00435D7F` | `00035D7C` / `0003517C` | `FF 52 24` |
| First present | `00435DAF` → `00435DB4` | `00035DAF` / `000351AF` | `E8 EC B0 02 00` |

Let C be `004338E0` entry ESP, and R the `00435BC0` entry ESP. Its caller
pushes EDX and executes CALL, so R=C−8 with return address `00433919`.
Recruitment initially saves only 20 bytes. Its background-load entry/return
are therefore **R−24 / R−20**. A later `PUSH EDI` at `00435CD9` adds four
bytes: blit entry/return are **R−28 / R−24**, and first-present call/return
are **R−24**. One uniform local-depth assumption would misclassify the load.
On the unmodified natural descriptor-dispatch path from the barracks loop,
C=H−144 and R=H−152; a forced direct callback has a different depth.

Recruitment retains castle `00532218`, style `00532214`, palette `0053221C`,
and sprites `0053220C`. Style selects `castle.chr` versus `castle.pog` for
`dw_13.gfx`, `dw_13.s32` and the resource group. Native `004359B0`, called at
`00435C3E`→`00435C43`, constructs the eligible type list using
`Building_CanEquipAddon` and the real type-resource table. Initial selection
index is zero. Before its first item is used, the first list item at
`00532224` must be a real eligible type in 0..39, not its initialized −1
sentinel. Observe this native result; do not invent an eligible selection.

## Current candidate and capture limits

The owned native640 canvas remains active across both routes under the
overview root. The common full-blit hook can mirror their background without
another allocation. It does not mirror all subsequent primary drawing.
Recruitment helpers `00434E20` and `00435280`, among others, explicitly select
primary for content after the initial blit.

The inspected candidate also retains older recruitment-specific edits:
`00435DA5` jumps to the action-strip copy at `00513E80`, `004352B3` to the
status-strip copy at `005132E0`, `00435DAA` selects callback wrapper
`0051BC20`, and `00435B90` retains its centered-input hook. The active canvas
wrapper bypasses its old centering copy while preserving native callback
work; it does not convert primary layers into physical-memory evidence.
These interactions require explicit validation, not an assumption that the
native640 allocation completes the route's HD composition.

The immediate implementation boundary is a source-bound route observer plus
an authentic capture of the relevant completed surface. Background route,
native/physical mirror relation, primary composition, visual correctness,
input, modal exit/destruction and promotion remain separate claims. No court
or recruitment pass, release readiness, or stable promotion is recorded here.

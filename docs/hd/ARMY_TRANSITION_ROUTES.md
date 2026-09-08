# Native army transition routes

Source audit, 2026-09-06. These are bounded diagnostic contracts, not new runtime,
ordinary mouse-dispatch, manual-input, or promotion evidence. Native instructions
were read with x86 `dumpbin /disasm:bytes`; save fields were read without changing
the save, units, visibility, executable, or candidate. The current implementation
is [framed_army_input.py](../../src/patcher/framed_army_input.py); its private
selected-army guard and coordinate hooks are already installed by the separately
bound army builder. No new patch is proposed here.

## Exact inputs

| Input | SHA-256 |
| --- | --- |
| `C:/Clash/clash95.exe` | `500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae` |
| `C:/Clash/save/0.dat` | `4f2182409d209985a527f07c4116b19e44332416698d6acb0a3d35ae68db8a89` |
| `C:/ClashTests/hd-completion/framed-army-v1-1024x768-build-20260906-085300/clash95_army_1024x768_v1.exe` | `9bc99ba5a33248066b90b95119dd4301692d5af429d93167c4b35d2e508c53b5` |
| `src/patcher/framed_army_input.py` | `c27a0feb17df909dcf9986bfde231d90a79e8c1ad8abbcf2884b52e767a70ee2` |
| `tools/build_framed_army_candidate.py` | `e24f1c2cee5d105121d200424e8729ac82202a68b472006f0dcfa93616551ba8` |

The candidate stage is the protected default name followed by
`-combinedui-partialtiles-initialpaint-framed-modalcanvas-army-validation`.
Bind the whole candidate and generated probe before using these observations.

## Real slot0 targets and geometry

A save unit begins at `147190 + 725*index`; runtime storage begins at
`gameData + 147174 + 725*index`. Signed words at offsets0/2 are world X/Y,
byte4 is owner, and the ten signed squad-type words are at `6+31*slot`.
The saved occupancy word at `16+0x87D56+200*X+2*Y` equals each listed unit ID.
All four listed armies are real player0 armies; no availability construction is
needed. Require the live occupancy, ownership, squad types and world/scroll
values again before calling a handler.

| Unit | World X,Y | Occupied types, then `-1` through slot9 | Logical tile center at scroll10,17 |
| --- | --- | --- | --- |
| 3, initial target | 16,19 | 16,16,1,1,1,1,1,1 | 448,176 |
| 1, second multi-squad target | 15,22 | 1,16,1,15 | 384,368 |
| 2, third target | 15,23 | 17,9 | 384,432 |
| 0, single-squad panel-close case | 14,22 | 5 | 320,368 |

The 1024x768 terrain is `(32,16)..(991,751)`. Tile centers are
`(64+64*(X-scrollX),48+64*(Y-scrollY))`. Native raw mouse globals are
`544CFC/544D00`, interpreted by signed shift with byte`54512C`; do not overwrite
global coordinates with translated portrait coordinates. The army backing is
`(32,686)..(418,751)`; hit cells start at `(38,686)`, each38x64, through X417/Y749.
Portrait artwork starts at `(38+38*slot,687)`, each32x64. A first-portrait test can
use logical `(54,719)`. Six action buttons start at `(800,688)` and remain a
separate input region.

## Bounded select/switch route

Native `408030` accepts a left-button predicate and changes selection only after
its occupancy and owner checks. With current selected3, it can select army1:
`4080EF` compares loaded ID1 against selected3, `408122` verifies player0,
`408126` assigns EAX1, and `40812B` writes EDX1 to `511B58`. Observe EAX1 and the
actual changed selection at `408131`, together with the preceding identity
checks; that epilogue is also reached by an early zero-input branch.
Same-unit and empty-tile paths return0 at `408136`; neither is deselection.

Use a disclosed call to `406980` after selection. Its `406987 -> 40698C` call to
`40A490`, followed by `40A4ED -> 40A4F2` calling `40A500`, selects these branches:

| Before -> selected target | Native panel call -> return | Required final selected/prior/lower |
| --- | --- | --- |
| No panel -> army3 | `40A5EE -> 40A5F3`, target`423B00` | 3/3/1 |
| Army3 -> army1 | `40A5E5 -> 40A5EA`, target`423B90` | 1/1/1 |
| Army1 -> army2 | same switch branch | 2/2/1 |
| Army2 -> single army0 | `40A51A -> 40A51F`, target`423B40` | 0/-1/0 |
| Single army0 -> army3 | open branch | 3/3/1 |

`511B58` is selected, `514194` is prior/displayed index, and `526994` is lower
owner. Require owner`5199D8=40AD40`, post callback`526990=0`, the same native TID,
and the expected displayed-unit pointer `526FA0` after an actual multi-army draw.
The pointer need not be zero when the panel closes; native close does not clear
that storage.

`423B00` sets lower1/prior=selected and clears the40 selection-flag bytes at
`526F78`. Calls `423B2D -> 423B32` (draw`423420`) and `423B37 -> 423B3C`
(redraw`418700`) must be observed. `423B90` sets prior at`423B95`, calls draw at
`423B9F -> 423BA4`, then **tail-jumps** to `418700` at`423BA9`. Its redraw returns
to the original caller `40A5EA`; there is no local switch-return instruction.
This switch preserves the40 portrait selection-flag bytes, unlike the normal
map dispatcher described below.

Let E be a panel function's entry ESP, with its genuine return at `[E]`.
Open/close save8 bytes: draw/redraw entry is E-12 and its return E-8. Switch has
no prologue: draw entry E-4, return E, and tail-redraw entry E. Require paired
callers and exact return ESP, not an unqualified breakpoint hit or generic EAX.
When setting current EIP to an entry via CDB, observe a verified instruction
after the first native instruction (e.g. switch`423B95` after its MOV); a
breakpoint exactly at newly assigned current EIP can be skipped by `gc`.

This is a native selection routine, **not the ordinary main-map dispatch**.
The ordinary loop calls `423860` at`40B10C`; when that returns0, it calls
`4084A0` at`40B233`. The latter has additional movement, information, audio and
release handling. Its selection write is `40984F`, preceded by saved old index
at`40983D`, and it clears flags by `409854 -> 409859` calling`423B70`. It is not
equivalent to calling`408030`; retain this limitation in a direct-route report.

## Native Map mode deselection

The descriptor`511D40` is labelled **Map mode**. Its callback `[descriptor+20]`
is`409D80`, and `[descriptor+31]` is the sound string pointer`4ECC9A`. In the
current candidate its geometry is `(800,688)`; callback/data fields are native.
Invoke the callback with EAX=`511D40`, explicitly disclosed as direct callback
control, while selected/prior identify the current own army and lower=1.

At`409D81` after native PUSH EDX, verify TID, EAX descriptor and ESP=E-4.
After its three saved registers, body ESP=E-12. It reads the descriptor sound,
loads ECX=-1 and calls sound`4425E0` at`409D94 -> 409D99`; verify ECX remains
the native sentinel. It saves selected into`511B5C` at`409DA3`, then actually
writes selected=-1 at`409DA8`. Observe this write before accepting deselection.
The call`409DAE -> 409DB3` to`40A500` must reach`423B40` through`40A51A`.

`423B40` calls`418FE0` at`423B42 -> 423B47`, then stores lower0 at`423B53` and
prior=-1 at`423B59`, and redraws at`423B5F -> 423B64`. `418FE0` only fills the
64-byte highlight table`5269D8` with FF; it does not clear selected itself.
The callback also updates command state through`40A360`, assigns cursor
descriptor`526A34=5196A0`, redraws at`409DC3 -> 409DC8`, restores registers and
returns at`409DCB`. Its final caller ESP is E+4. Accept final selected/prior=-1,
lower0 and native redraw evidence; no zeroed stale unit pointer is required.
An empty-map or right-click deselection contract has not been established.

## Separate left-portrait route

Call native`423860` only with a valid current own multi-squad panel. Its native
body is64 bytes below entry ESP. The installed coordinate trampoline reaches
`4238CA` with ESI=slot0..9 and EDI0. Bind actual slot/type and untouched logical
mouse coordinates. Observe cursor call`4238D4 -> 4238D9`; right-button query
`4238DE -> 4238E3` must return0 to exclude the separate Unit_Info route.
Left query`423932 -> 423937` must return1 and native occupied-type check at
`423948..423950` must pass. Only then does `423952` execute
`80 34 B5 78 6F 52 00 01`, XORing the byte at`526F78+4*slot` with1.
Record exact before/after flag and unchanged other slots at`42395A`.

Actual draw is`42395F -> 423964`, redraw is`42396B -> 423970`. The native release
wait is`423975 -> 42397A`, target`4609D0`: it calls left at`4609DB -> 4609E0`
and right at`4609F7 -> 4609FC`, looping through DirectInput if held. A bounded
diagnostic can stop before the wait, or explicitly disclose a controlled release
state before allowing it; never force a returned predicate into input proof.
The subsequent guarded map query`423984 -> 423989` must return0 for the portrait
pixel, with no `423991`/`423A59` movement route entered. The normal true return
is`423A99`; final caller ESP is entry+4. EAX1 alone is insufficient: hover also
sets EDI1 at`42397A`, which is returned as EAX.

## Small native byte bindings

All coordinates and callback instructions above are source-derived. These
original span hashes make the read-only audit reproducible; candidate changes
at the two input hooks and framed descriptor geometry must be authenticated by
whole candidate reconstruction rather than accepted as native unchanged bytes.

| VA / file offset / bytes | Original SHA-256 | Current candidate |
| --- | --- | --- |
| `409D80 / 9180 / 100` | `e6203b6863c8eedf88f14ef95a3159def6f329feecc83208a10f7f9f38e69b78` | unchanged |
| `40A490 / 9890 / 519` | `d57562d206050eea507ec0c34748be4790f8ceac986e6c8d1dffb6604bb4767b` | unchanged |
| `423B00 / 22F00 / 176` | `6fe0a2399c46517e54966a8776133249006a3645725ba04adae2bb31e479e104` | unchanged |
| `423860 / 22C60 / 593` | `55d007f9abafde52ccbd9cfbcfee64957d819dd7cae1b61bd39d6728a63223be` | two bound input hooks |
| `4609D0 / 5FDD0 / 52` | `c25d1a900626531d37090a0ac74732db1c6dd4dc7a58b4ae73d0fc43d9ce411e` | unchanged |
| `418FE0 / 183E0 / 25` | `70498c7997e9084fe26f28f959da48fae8ff139233dbe8d909977ffa9de47eef` | unchanged |

The planned six-step select3/switch1/switch2/single0/reselect3/Map-mode sequence
must retain individual failures and capture evidence for each completed state.
Portrait interaction is a separate additional route. Actual draw-helper status,
pixel completeness, frame/action-bar audits, retained process cleanup and manual
input remain separate acceptance claims. No transition run was executed by this
source audit.

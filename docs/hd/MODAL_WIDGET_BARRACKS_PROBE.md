# Widget-stage barracks probe preparation

`tools/modal_widgets_barracks_probe.py` prepares an observation packet for the
actual `-completehd-modalwidgets-validation` candidate. It authenticates the
external executable, manifest and sibling loaded-image probe through the
[canonical widget context](MODAL_WIDGET_CANDIDATE.md) exactly once. The packet
uses schema `clash95_modal_widgets_barracks_probe_packet_v1` and protocol
`widgets_barracks_owned_canvas_v1`; historical primary/text packets and logs
remain separate.

Preparation checks the complete 36-file candidate recipe, the additional
authentication dependency, and pinned observation helpers before and after
reconstruction. It retains real ancestor identities for text, primary, slots
and complete-HD. Primary observer CALL/return sites are checked against the
actual widget executable, as are every inherited native route byte span. The
compiled command binds the actual MWIDGETS and PTILE startup contracts and
inventories explicit and implicit breakpoint IDs after all startup substitutions.
Duplicate IDs/sites, unresolved tokens and lines exceeding CDB's bound fail.
The root patcher wrapper supplying resolution geometry is also pinned and
reread; its code cannot change commands while leaving recorded sources unchanged.

Only the controlled barracks route with `existing_flags` is exposed. Castle
availability is unchanged. Native case dispatch and the flipping-gate result
are forced diagnostics and remain explicitly recorded. The producer reuses
pinned pure route helpers; it does not rewrite historical stages or logs, change
their module globals, launch a debugger or inject operating-system input.

## Use and interpretation

Prepare a fresh external candidate using the command in the candidate guide,
then pass that exact bundle to the producer:

```powershell
python -B tools/modal_widgets_barracks_probe.py --original C:/Clash/clash95.exe --candidate C:/ClashTests/modalwidgets-validation/widget-1024x768.exe --candidate-manifest C:/ClashTests/modalwidgets-validation/widget-1024x768.candidate.json --resolution 1024x768
```

The JSON output includes the full loaded-image probe, command template, compiled
diagnostic command, preparation/source hashes, genuine ancestor identities and
four native checkpoint definitions. `regenerate_packet` repeats authentication and
compares the entire typed packet before any future consumer may trust it.
`checkpoint_script` formats their stop scripts and does not authenticate its
input. The compiled probe is ASCII/LF preparation text; its hash does not bind
the Windows CRLF transport that a runtime host still needs to implement.

**The command is not yet ready for runtime capture.** The packet deliberately
sets `runtime_ready`, `compiled_probe_complete_for_runtime`, `runtime_accepted`,
`primary_composition_proven`, `manual_input_proof` and `promotion_ready` to false.
A successful preparation process must not be treated as a capture or acceptance
report. Remaining integrations are explicit:

- A widget-stage trace consumer retaining every malformed, duplicate and failed
  observation, with authentic map, canvas, slot and primary call identities.
- Cached primary Lock, quantity-text and real widget-owner observations.
- A host binding exact command transport, process identity, raw memory queries,
  three samples at each checkpoint, bounded deadlines, final summary and cleanup.
- Original-artwork and native-font pixel comparisons, followed by ordinary
  input, modal exit and healthy map return on the same candidate.

The historical primary 1/1/1/3 capture contract is not the required new 3/3/3/3
contract. Neither the primary pixel audit nor the text-only checkpoint ledger
implicitly accepts this widget stage.

## Repository checks

```powershell
python -B tools/test_modal_widgets_barracks_probe.py
python -B tools/test_modal_widgets_context.py
python -B tools/test_run_framed_offline_tests.py
```

The pure producer fixtures use explicitly synthetic address space and mock only
candidate admission and VA mapping; native bytes, relocation identities, command
assembly and rejection paths still run. They cover all six fixture geometries
including 802x602, all four castle indices, exact startup/packet identities,
source drift and command collisions. An opt-in `CLASH_WIDGET_BARRACKS_MANIFEST`
fixture authenticates an existing external widget bundle once. It requires the
user-owned original executable, reconstructs the candidate and prepares a
packet without launching the game. Both suites are included in the aggregate
framed registry; an absent opt-in bundle is a reported skip, never runtime proof.

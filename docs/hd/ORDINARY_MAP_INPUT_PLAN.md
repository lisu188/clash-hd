# Measured ordinary-map input plan

`tools/ordinary_map_input_plan.py` is a pure planner for selecting a measured
friendly army and attempting one cardinal step. It reads no process memory,
injects no input and launches nothing. **It is not integrated with the runtime
harness.** A plan is not evidence that a click, native route or move executed.

On 2026-09-26, all **25** fixtures in
`tools/test_ordinary_map_input_plan.py` passed on Windows using Python 3.12.
Independent source review checked the origin exclusions, both endpoint
neighborhoods, retained occupant records and previous-selection contract. Its
native-function reference correction is applied. The focused CI workflow runs
the same fixtures on Linux and Windows; no runtime evidence accompanies these
source/state checks.

```text
python -B tools/test_ordinary_map_input_plan.py -v
```

The fixtures use synthetic records and standard-library code plus the local
viewport geometry modules. They need no original executable, save, game assets,
debugger, capture, machine emulator or installed test dependency.

## Caller and schema contract

The caller must authenticate the candidate bytes and layout, retain the exact
process identity, and obtain a coherent read while that process is paused.
Setting `paused: true` or copying a SHA into JSON does not authenticate anything.
Every observation needs a monotonically increasing sequence from the same
owned session. Keep source hashes, native addresses, raw-read hashes, timestamps,
action identifiers and other provenance in an enclosing receipt, not as extra
fields inside these strict records.

All records require exactly the listed keys. Missing or unknown fields fail.
Integers reject booleans; boolean fields require actual booleans. Bounds and
relationships are enforced by `candidate_contract()` and `inspect()` in the
planner. Coordinates use native world X/Y order; arrays retain the fixed
100-cell stride even in a smaller world.

| Record | Exact keys |
| --- | --- |
| Candidate, schema `clash95_ordinary_map_input_candidate_v1` | `schema`, `sha256`, `stage`, `profile`, `resolution`, `layout` |
| Observation, schema `clash95_ordinary_map_observation_v1` | `schema`, `sequence`, `paused`, `identity`, `context`, `world`, `player`, `minimap`, `port`, `stacks`, `tiles`, `unit_profiles` |
| `identity` | `pid`, `creation_filetime`, `candidate_sha256`, `image_base` |
| `context` | `game_data`, `render_hook`, `map_active`, `native_modal`, `post_callback`, `lower_owner`, `map_surface`, `map_pixels`, `map_vtable`, `map_extent`, `primary_extent`, `current_player`, `turn_owner`, `viewed_player`, `selected_stack`, `previous_stack`, `panel_stack`, `active_stack`, `join_mode`, `slot_flags` |
| `world` | `width`, `height`, `scroll_x`, `scroll_y` |
| `player` | `index`, `human`, `minimap_visible` |
| `minimap` | `left`, `top`, `width`, `height` |
| `port` | `x`, `y` |
| Each `stacks` item | `index`, `x`, `y`, `owner`, `hidden`, `queue_count`, `slots` |
| Each of ten `slots` items | `type`, `ap` |
| Each `tiles` item | `x`, `y`, `occupant`, `visible`, `terrain_id`, `terrain_profile`, `overlay_id`, `road_id`, `trap_mask` |
| Each `unit_profiles` item | `type`, `costs` |

Candidate layout is `framed_native_tiles_v1`, profile is `completehd` or
`modalwidgets`, stage ends in `-validation`, and SHA is lowercase 64-digit hex.
Resolution is canonical `WIDTHxHEIGHT` accepted by `FramedViewport` and
`FramedArmyViewport`. Geometry acceptance alone does not establish that a
matching candidate exists or was validated at that resolution.

Surface extents are `[width, height]`, not packed DWORDs. Selection indices are
signed (`-1` means none). Tile occupancy and overlay IDs retain unsigned
`65535` sentinels. Slot types are signed words; native occupied slots stop at
the first `-1`. `costs` contains eight measured unsigned terrain-cost bytes.
`slot_flags` contains ten measured zeros for whole-army selection. Records may
cover only measured candidate armies and relevant tiles; failure to find a
pair does not prove that none exists elsewhere in the world.

## Native read map

These are native image addresses at preferred base `0x400000`; image globals
and code pointers require relocation by the authenticated loaded-image delta.
`GD` denotes the measured pointer at `0x5202E4`; offsets below are decimal.
Do not rebase `GD` or other already-measured runtime pointers a second time.
The pending strict runtime observation adapter must supply these measurements;
the planner's `NATIVE` dictionary performs no reads.

| Measurements | Native source |
| --- | --- |
| Render/map/modal/post/lower owners | `0x5199D8`, `0x527C24`, `0x52698C`, `0x526990`, `0x526994` |
| Current player; join mode | `0x5202EC`; `0x5202E8` |
| Selected; previous; panel; active stack | `0x511B58`; `0x511B5C`; `0x514194`; `0x526FA0` |
| Ten selection flags | Ten DWORDs at `0x526F78` |
| Map surface and header | Pointer at `0x5202E0`; dimensions WORDs at `+0/+2`, pixels pointer `+4`, vtable pointer `+0xB8` |
| Primary extent | Width/height WORDs at `0x51D4C0/+2` |
| World size/scroll; turn/view player | `GD+140000/140004/140008/140012`; `GD+147139/147143` |
| Player human/minimap flags | DWORDs at `GD+140024+1423*player+27/+23` |
| Visibility | Byte at player record `+57+13*x+(y>>3)`, tested with `1<<(y&7)` |
| Measured minimap rectangle | Four WORDs at `0x523344/+2/+4/+6` |
| Army record | `GD+147174+725*index`: signed XY WORDs `+0/+2`, owner byte `+4`, signed queue count DWORD `+316`, hidden byte `+720` |
| Ten unit slots | Army `+6+31*slot`: signed type WORD `+0`, AP byte `+8` |
| Occupancy; map tile; trap | WORD at `GD+556374+200*x+2*y`; tile at `GD+1400*x+14*y` with terrain/overlay/road WORDs `+0/+2/+4`; byte at `GD+576374+100*x+y` |
| Port footprint origin | Signed DWORDs at `GD+586374/+586378` |
| Terrain profile; unit costs | DWORD at `0x52456C+4*terrain_id`; eight bytes at `0x512568+88*unit_type+30` |

Read-only source references in the separate `clash-disassembly` repository:

- `src/world/00408030_0040A040_world_001.cpp`: `0x408030` and `0x4084A0`
  selection/dispatch, including special-site and port routes.
- `src/world/0040D6D0_0040F4D0_world_004.cpp`: `0x40DD60` minimap hit test
  and `0x40F060` visibility bit addressing.
- `src/units/00412C00_00414350_units_003.cpp`: `0x413920` merged movement
  costs and `0x414150` tile admission; native metadata stride/cost bytes are
  corroborated by `clash95.asm` at `0x413920`.
- `src/units/00414390_00416750_units_004.cpp`: `0x4147A0` pathfinding.
- `src/buildings/00422B50_004254E0_buildings_005.cpp`: `0x424370` bridge
  terrain IDs 603 through 610 have separate cost semantics.
- `src/persistence/00443BB0_00445CE0_persistence_002.cpp`: `0x444150`
  hidden-enemy adjacency; calls before/after movement are in
  `src/units/0040F510_00411560_units_001.cpp`.
- `src/recovered_structs.h`: `UnitStackRecord`, `UnitSlotRecord`,
  `MapTileRecord`, `PlayerRuntimeState` and `UnitTypeMetadataRecord` layouts.

These references explain the bounded calculation, not original-parity or
runtime acceptance. The separate repository is not a fixture/CI dependency.

## Planning and validation

`plan_input(snapshot, candidate, aim_tolerance=4)` requires an ordinary-map
owner, no modal/post/join context, matching human/current/turn/view player,
and coherent selection/panel ownership. It chooses a different friendly,
visible, unhidden, occupied and idle stack. Tile centers come from the actual
candidate geometry and measured scroll. The entire aim tolerance square must
fit inside the frame and avoid the measured visible minimap, all action-bar
cells and prospective army portrait backing.

Both endpoints exclude traps, religious overlays and the port footprint.
The destination must be visible, empty, cardinal, without a road overlay or
bridge terrain, and have positive measured costs for every occupied unit type.
The cost is their maximum; every occupied slot must have sufficient current AP.
Both in-world 3x3 endpoint neighborhoods must be measured, with all occupying
army records retained and consistent. Hidden enemy and unknown occupants fail.
This is a conservative subset of native cost semantics, not a reachability
oracle. A single destination click may execute the step immediately.

The returned `clash95_ordinary_map_input_plan_v1` has exact keys `schema`,
`candidate`, `basis`, `basis_sha256`, `aim_tolerance`, `selection`, `movement`,
`reachability_proven`, `runtime_executed`, `proof_scope`. The basis retains only
relevant measured records. `checked_plan()` reconstructs the result and rejects
altered points, costs, records or claims. Both proof booleans remain false.
`selection` has `stack_index`, `tile`, `point`; `movement` has `stack_index`,
`origin`, `destination`, `point`, `measured_cardinal_cost`, `ap_before`,
`ap_after`, `one_click_may_execute`. Tile and point coordinates are `[x, y]`;
the AP arrays cover occupied slots only.

- `revalidate_before_click(plan, fresh, 'select'|'move')` requires a newer
  observation with unchanged identity, owner, player, camera, stack, safety
  tiles, neighboring occupants and unit profiles. Move additionally requires
  the exact planned whole army to own selection and its panel.
- `verify_selection(plan, before, after)` requires that exact army's selection
  transition, unchanged world records, and either native previous-index
  behavior (`0x408030` preserves it; `0x4084A0` stores the old selection).
- `verify_movement(plan, before, after)` requires the planned destination,
  source vacated, destination occupied by that same army, exact occupied-slot
  AP charges, empty queue and unchanged relevant context.

These validators establish relationships between supplied observations. They
do not authenticate those observations or prove the input callback, native
return, rendered result, process cleanup or lifecycle.

## Pending harness integration

`real_exe_smoke.py` already has bounded `Session.read()`, owned process/thread
selection and `pause_owned()`. Its periodic `snapshot()` immediately resumes;
a bounded action request/acknowledgment protocol must hold a coherent paused
observation for validation and bind resumption to the same action.

In `resolution_playability.py`, replace the sparse `STATE_HELPER` with a strict
observation reader and separate panel `0x514194` from previous `0x511B5C`.
Replace `run()`'s blind timed dismiss and fixed selection/movement coordinates
with observed ordinary-map readiness, planning and per-action validation.
An unrecognized modal must fail closed, not receive a guessed dismiss click.

`runner_menu_input.py` currently measures only live cursor feedback.
`menu_pulse_click.py`'s `click_while_pulsing()` emits more motion after aiming,
including four pulses before button-down. Bind the fresh pre-click observation,
actual click-boundary cursor, plan hash, owner identity and exact post-action
observation in one receipt. An earlier converged aim or nearby timed snapshot
cannot stand in for this binding. Use one planned click; do not assume a second
confirmation click is necessary.

Replace `selected_unit()`/`native_input_passed` acceptance based on any selected
index or aim receipts with the exact transition results and separately observed
native input route. Keep map pixel audits bound to their own paused samples.
Existing hidden selection/movement capture scripts supply useful retained-handle
and repeated-read patterns; their diagnostic routes do not supply ordinary-input
proof. The present foreground runner adapter also does not establish an input
transport on a hidden desktop. Runtime/capture approvals, manual proof and stable
promotion remain separate under `AGENTS.md`.

#!/usr/bin/env python3
"""Compare three externally captured army records; execute no game or input.

The exact original and inspected save authenticate the layout and starting
army. They do not authenticate supplied snapshots. A separate source-bound
protocol must bind every record hash, address and observed context to its run.
Passing here means the requested state deltas match, never runtime acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct


ORIGINAL_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
SAVE_SHA256 = "4f2182409d209985a527f07c4116b19e44332416698d6acb0a3d35ae68db8a89"
SAVE_SIZE = 586414
SAVE_LABEL_SIZE = 16
UNIT_INDEX = 3
UNIT_TABLE_OFFSET = 147174
UNIT_SIZE = 725
UNIT_OFFSET = UNIT_TABLE_OFFSET + UNIT_INDEX * UNIT_SIZE
SLOT_BASE = 6
SLOT_SIZE = 31
SLOT_COUNT = 10
PATH_COUNT_OFFSET = 316
PATH_NODES_OFFSET = 320
PATH_CAPACITY = 100
INITIAL_XY = (16, 19)
EXPECTED_TYPES = (16, 16, 1, 1, 1, 1, 1, 1, -1, -1)
PHASES = ("baseline", "preview", "settled")

# Read-only corroboration inspected 2026-09-06. These are evidence references,
# not dependencies on another checkout at execution time.
LAYOUT_SOURCES = {
    "clash-disassembly/src/recovered_structs.h:135":
        "3bc818bd2494b03a0a6dc293e1b383e578be96bfb6304f021c8885be43fc3f97",
    "clash-disassembly/src/recovered_types.h:97":
        "a845ca8f3a07582f78a890f6030143f5920ff2233014cdc0ddd2cf3613b08640",
    "clash-disassembly/tools/dump_save_dat.py:52":
        "4e5f5cd5b9d33f4e5f9e76694c492b942fe2200036300159ba7c94e402d84079",
    "clash-disassembly/clash95.asm":
        "b298e8c85086f542ebc8b02c26904019aa8278d531cbf02a88d785170cbb4436",
}
# Contiguous objdump-decoded instruction spans, not guessed instruction starts.
# Original file offsets are fixed by the authenticated PE identity.
NATIVE_LAYOUT_SPANS = (
    (0x410360, 63328, "89c88d04c50000000001c8c1e00401c88b15e402520089c18d0485000000008db2e63e020001c801c68d863c0100008b18",
     "Compute gameData+147174+index*725 and read queue at army+316"),
    (0x410013, 62483, "83c02531dbba010000008a58e90fbf0883f9ff741431c98a480839cb7e0289cb4283c01f83fa0a7ce489d85a595bc3",
     "Ten contiguous slots, signed type -1 terminator, unsigned AP at slot+8, stride31"),
    (0x410130, 62768, "53515689c683c00631c90fbf1883fbff741c31db8a580839d37d0289da8a580883c01f28d3418858e983f90a7cdc89f0e8eb4d04005e595bc3",
     "Occupied-slot AP subtraction; no exact movement cost inferred"),
    (0x4103B1, 63409, "8d04bd0000000001e88b400431db8944246c0fbf0631c9898424800000000fbf4602",
     "Four-byte waypoint load and signed army XY words at+0/+2"),
    (0x410AEE, 65262, "66890789c866895f02",
     "Native settled XY writes at army+0/+2"),
)
LIMITS = [
    "Caller-supplied snapshot bytes and context are not authenticated capture evidence. Bind their hashes and unit addresses through a separate exact-source protocol.",
    "A matching queue is structural preview state, not proof that a native admission predicate or click executed.",
    "Exact settled XY is mandatory; an empty queue or charged AP alone can occur before movement animation finishes.",
    "AP may stay equal or decrease. No pathfinding, terrain, obstacle, visibility, movement-cost or animation-timing oracle runs here.",
    "Only named invariant fields and complete empty slots are required unchanged. All other changed bytes are reported without a claim of semantic correctness.",
    "No runtime, manual input, pixels, cleanup, stable-stage promotion or complete world-state preservation is proved.",
]


@dataclass(frozen=True)
class MovementSnapshot:
    """Values that an external protocol must bind to one paused observation."""

    record: bytes
    selected_index: int
    prior_index: int
    current_player: int
    squad_flags: tuple[int, ...]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_unit(record: bytes) -> dict:
    """Decode a complete record, rejecting malformed signed path counts first."""
    if type(record) is not bytes or len(record) != UNIT_SIZE:
        raise ValueError("immutable complete 725-byte army record required")
    count = struct.unpack_from("<i", record, PATH_COUNT_OFFSET)[0]
    if not 0 <= count <= PATH_CAPACITY:
        raise ValueError("signed waypoint count outside native capacity0..100")
    slots = []
    for index in range(SLOT_COUNT):
        offset = SLOT_BASE + SLOT_SIZE * index
        slots.append(dict(index=index, offset=offset,
                          unit_type=struct.unpack_from("<h", record, offset)[0],
                          owner=record[offset+2], ap=record[offset+8],
                          health=record[offset+9], fatigue=record[offset+10],
                          morale=record[offset+11]))
    return dict(xy=list(struct.unpack_from("<hh", record)), owner=record[4],
                facing=record[5], hidden=record[720], slots=slots,
                occupied_count=sum(s["unit_type"] != -1 for s in slots),
                path_count=count, path=[dict(xy=list(struct.unpack_from("<BB", record, 320+4*i)),
                    cumulative_cost=struct.unpack_from("<H", record, 322+4*i)[0]) for i in range(count)])


def immutable_ranges() -> list[dict]:
    """Half-open byte ranges for this bounded no-combat/no-turn comparison."""
    ranges = [dict(start=4, end=5, purpose="army owner")]
    for i in range(SLOT_COUNT):
        offset = SLOT_BASE + SLOT_SIZE*i
        if i < 8:
            ranges.extend((dict(start=offset, end=offset+3, purpose=f"slot{i} type and owner"),
                           dict(start=offset+9, end=offset+12, purpose=f"slot{i} health fatigue morale")))
        else:
            ranges.append(dict(start=offset, end=offset+SLOT_SIZE, purpose=f"slot{i} entire empty record"))
    return ranges


def _differences(before: bytes, after: bytes) -> list[dict]:
    """Account for every changed byte, including inactive queue and opaque data."""
    groups = []
    for offset, (old, new) in enumerate(zip(before, after)):
        if old == new:
            continue
        if not groups or groups[-1][1] != offset:
            groups.append([offset, offset+1])
        else:
            groups[-1][1] += 1
    return [dict(offset=a, size=b-a, before_hex=before[a:b].hex(), after_hex=after[a:b].hex())
            for a, b in groups]


def compare_movement_state(original: bytes, save: bytes, *, baseline: MovementSnapshot,
                           preview: MovementSnapshot, settled: MovementSnapshot,
                           destination: tuple[int, int]) -> dict:
    """Check state deltas only. Never upgrades external evidence/approval flags.

    Destination must be explicit and inside the authenticated save's world.
    The queue's first stored node is destination-first in the native path format.
    Record bytes, including unused queue bytes, are never normalized or repaired.
    """
    result = dict(schema="clash95_framed_army_movement_state_v1", passed=False,
                  state_deltas_passed=False, original_authenticated=False,
                  save_authenticated=False, captured_records_bound=False,
                  native_route_proved=False, runtime_accepted=False,
                  manual_input_proof=False, pixels_verified=False,
                  cleanup_verified=False, promotion_ready=False,
                  unit_index=UNIT_INDEX, game_data_record_offset=UNIT_OFFSET,
                  source_layout=dict(LAYOUT_SOURCES), immutable_ranges=immutable_ranges(),
                  source={}, snapshots={}, byte_deltas={}, ap_deltas=[], failures=[], limits=list(LIMITS))
    failures = result["failures"]
    def require(ok, message):
        if not ok:
            failures.append(message)
    try:
        if type(original) is not bytes or sha(original) != ORIGINAL_SHA256:
            raise ValueError("exact authenticated original executable required")
        for va, offset, expected, _ in NATIVE_LAYOUT_SPANS:
            if original[offset:offset+len(expected)//2] != bytes.fromhex(expected):
                raise ValueError(f"native layout bytes differ at{va:08x}")
        result["original_authenticated"] = True
        if type(save) is not bytes or len(save) != SAVE_SIZE or sha(save) != SAVE_SHA256:
            raise ValueError("exact inspected slot0 save required")
        result["save_authenticated"] = True
        result["source"] = dict(original_sha256=sha(original), save_sha256=sha(save),
            native_spans=[dict(va=va, file_offset=offset, size=len(h)//2,
                              sha256=sha(bytes.fromhex(h)), purpose=why)
                          for va, offset, h, why in NATIVE_LAYOUT_SPANS])
        world = struct.unpack_from("<ii", save, SAVE_LABEL_SIZE+140000)
        if world != (100, 100):
            raise ValueError("inspected save world geometry differs")
        if (type(destination) is not tuple or len(destination) != 2 or
                any(type(v) is not int for v in destination) or
                not all(0 <= v < size for v, size in zip(destination, world)) or
                destination == INITIAL_XY):
            raise ValueError("explicit different in-world destination required")
        result.update(world=list(world), destination=list(destination))
        source_record = save[SAVE_LABEL_SIZE+UNIT_OFFSET:SAVE_LABEL_SIZE+UNIT_OFFSET+UNIT_SIZE]
        expected = decode_unit(source_record)
        if (tuple(expected["xy"]) != INITIAL_XY or expected["owner"] != 0 or
                tuple(s["unit_type"] for s in expected["slots"]) != EXPECTED_TYPES or expected["path_count"] != 0):
            raise ValueError("inspected army3 layout or eight-squad save contract differs")
        result["source"]["unit_record_sha256"] = sha(source_record)
        records = dict(zip(PHASES, (baseline, preview, settled)))
        decoded = {}
        for phase, snapshot in records.items():
            if type(snapshot) is not MovementSnapshot:
                raise ValueError(phase+": immutable MovementSnapshot required")
            if (any(type(v) is not int for v in (snapshot.selected_index, snapshot.prior_index, snapshot.current_player)) or
                    type(snapshot.squad_flags) is not tuple or len(snapshot.squad_flags) != 10 or
                    any(type(v) is not int for v in snapshot.squad_flags)):
                raise ValueError(phase+": exact integer selection/player and immutable ten-flag context required")
            require((snapshot.selected_index, snapshot.prior_index, snapshot.current_player) == (3, 3, 0),
                    phase+": selected army/prior/player identity differs")
            require(snapshot.squad_flags == (0,)*10, phase+": whole-army zero-flag context differs")
            unit = decode_unit(snapshot.record)
            decoded[phase] = unit
            result["snapshots"][phase] = dict(record_sha256=sha(snapshot.record), record_size=UNIT_SIZE,
                selected_index=snapshot.selected_index, prior_index=snapshot.prior_index,
                current_player=snapshot.current_player, squad_flags=list(snapshot.squad_flags), state=unit)
            require(tuple(s["unit_type"] for s in unit["slots"]) == EXPECTED_TYPES,
                    phase+": ordered eight occupied/two empty squad slots differ")
            require(all(0 <= v < size for v, size in zip(unit["xy"], world)), phase+": army XY outside world")
            require(unit["hidden"] == expected["hidden"] == 0, phase+": army hidden state differs")
            for span in result["immutable_ranges"]:
                a, b = span["start"], span["end"]
                require(snapshot.record[a:b] == source_record[a:b], phase+": changed "+span["purpose"])
            for index, node in enumerate(unit["path"]):
                require(all(0 <= v < size for v, size in zip(node["xy"], world)),
                        f"{phase}: waypoint{index} outside world")
        first, planned, final = (decoded[p] for p in PHASES)
        require(tuple(first["xy"]) == INITIAL_XY and first["path_count"] == 0,
                "baseline: initial XY/empty queue differs")
        require(planned["xy"] == first["xy"], "preview: coordinates changed before confirmation")
        require(planned["path_count"] > 0, "preview: accepted nonempty queue required")
        if planned["path"]:
            require(tuple(planned["path"][0]["xy"]) == destination, "preview: stored destination differs")
        require(tuple(final["xy"]) == destination, "settled: exact destination not reached")
        require(final["path_count"] == 0, "settled: queue still active")
        for i in range(8):
            initial_ap, before, after = (decoded[p]["slots"][i]["ap"] for p in PHASES)
            require(initial_ap == expected["slots"][i]["ap"], f"baseline: slot{i} AP differs from save")
            require(before == initial_ap, f"preview: slot{i} AP changed before confirmation")
            require(after <= initial_ap, f"settled: slot{i} AP increased")
            result["ap_deltas"].append(dict(slot=i, baseline=initial_ap, preview=before,
                                           settled=after, delta=after-initial_ap))
        for before, after in (("save", "baseline"), ("baseline", "preview"), ("preview", "settled")):
            a = source_record if before == "save" else records[before].record
            changes = _differences(a, records[after].record)
            result["byte_deltas"][before+"_to_"+after] = dict(
                changed_bytes=sum(c["size"] for c in changes), ranges=changes)
    except (ValueError, TypeError, struct.error) as error:
        failures.append(str(error))
    result["passed"] = result["state_deltas_passed"] = not failures
    return result

#!/usr/bin/env python3
"""Disclosed continuity extras for the hidden successor map route.

An extra adds debugger-forced native calls to the forced map route of
tools/hd_multires_hidden_session.py and names the isolated save files it reads
and writes. The session pins this module and every template in SOURCES,
composes the extra after the soak extra, rejects any breakpoint-site collision,
snapshots the named files before launch, retains copies after the run and
replays the extra's markers here. Extras never write input, clicks or menu
state. Each forced call is disclosed in forced_mechanisms, so their runs are
hidden_cdb_host continuity observations, never input proof.

forced-save: after the forced route loads ``load_slot``, the first world-map
loop entry (0x40B0C1, before its first poll) calls the native saveGame
(0x4443E0) once for ``save_slot`` with the loaded game's name buffer, then
restores the two registers it set. Saving slot 0 into slot 7, then reloading
slot 7 and saving it into slot 8, is the save/load round trip.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

FORCED_SAVE = "forced-save"
FORCED_SAVE_TEMPLATE = "probes/cdb/continuity/hd_multires_forced_save_extra.cdb"
SOURCES = (FORCED_SAVE_TEMPLATE,)
MAX_TEMPLATE_BYTES = 64 * 1024
MAX_SAVE_BYTES = 16 * 1024 * 1024
# The forced load list's rows (hidden_soak_probe_composition.LOAD_SLOT_RANGE).
SLOT_RANGE = (0, 9)
ROUTE, DURATION = "map-idle", 120
MECHANISMS = {"save": "cdb_forced_save_game"}
# The forced map route and soak extra never break here.
SITES = ("0040B0C1",)
_PLACEHOLDER = re.compile(r"__[A-Z0-9_]+__")
_BREAKPOINT = re.compile(r"^bp\s+(?:/\d+\s+)?([0-9A-Fa-f]{8})\s", re.M)
SAVE_CALL = re.compile(r"HDCONT_SAVE_CALL slot=(\d+) load_slot=(\d+) gd=([0-9a-fA-F`]+) player=(\d+) "
                       r"scroll=\((-?\d+),(-?\d+)\) tick=(\d+)")
SAVE_RETURNED = re.compile(r"HDCONT_SAVE_RETURNED slot=(\d+) eax=([0-9a-fA-F]+) tick=(\d+)")
LOADSAVE = re.compile(r"HDSESSION_LOADSAVE selected_arg=(-?\d+) selected_global=(-?\d+) accept=(-?\d+) "
                      r"choice=(-?\d+) gd=([0-9a-fA-F`]+)")
# saveGame writes a 16-byte name, then the whole 0x8F29E-byte game-data block.
SAVE_HEADER_BYTES, GAME_DATA_BYTES = 16, 0x8F29E
SAVE_BYTES = SAVE_HEADER_BYTES + GAME_DATA_BYTES
# Two record arrays end in a process-local object pointer that the save copies
# verbatim and loading re-creates: (game-data offset, record bytes, records,
# pointer offset in the record). The 500 records at +0x23EE6 are indexed
# against 0x1F4 next to loadGame (0x4441FF, 0x444368); the 100 records at
# +0x7C6EA start where those end, stop at the +0x87D56 table and are bounded
# by 100. Code reads both fields as object handles (0x456130 tests +0x1CF for
# null). Only these 2,400 bytes may differ between two saves of one state.
POINTER_FIELDS = ((0x23EE6, 0x2D5, 500, 0x2D1), (0x7C6EA, 0x1D3, 100, 0x1CF))


def state_digest(save: bytes) -> str:
    """SHA-256 of one save with every process-local pointer field zeroed."""
    if len(save) != SAVE_BYTES:
        raise ValueError("A forced save must be exactly the 16-byte name and the whole game-data block.")
    state = bytearray(save)
    for base, stride, count, field in POINTER_FIELDS:
        for index in range(count):
            offset = SAVE_HEADER_BYTES + base + index * stride + field
            state[offset:offset + 4] = bytes(4)
    return hashlib.sha256(bytes(state)).hexdigest()


def breakpoint_sites(text: str) -> list[str]:
    """Upper-case absolute addresses of every breakpoint line, in order."""
    return [site.upper() for site in _BREAKPOINT.findall(text.replace("\r\n", "\n"))]


def _slot(value: Any, label: str, low: int) -> int:
    if type(value) is not int or not low <= value <= SLOT_RANGE[1]:
        raise ValueError(f"{label} must be an integer slot in {low}..{SLOT_RANGE[1]}.")
    return value


def prepare(request: Any, *, route: str, duration: int) -> dict:
    """Validate one extra request and return the spec the session records."""
    if type(request) is not dict or set(request) != {"name", "load_slot", "save_slot"} \
            or request["name"] != FORCED_SAVE:
        raise ValueError("A route extra must be exactly {name: forced-save, load_slot, save_slot}.")
    if (route, duration) != (ROUTE, DURATION):
        raise ValueError("Continuity extras run only on the 120 s map-idle route.")
    load_slot = _slot(request["load_slot"], "load_slot", SLOT_RANGE[0])
    # Slot 0 is every map route's own load source, so it is never a save target.
    save_slot = _slot(request["save_slot"], "save_slot", 1)
    if save_slot == load_slot:
        raise ValueError("A forced save must not overwrite the slot it loaded.")
    return dict(request=dict(request), name=FORCED_SAVE, load_slot=load_slot, save_slot=save_slot,
                template=FORCED_SAVE_TEMPLATE, mechanisms=dict(MECHANISMS), sites=list(SITES),
                pre_files=[f"save/{load_slot}.dat"], post_files=[f"save/{save_slot}.dat"])


def compose(spec: dict, template: bytes) -> str:
    """The extra's substituted CDB lines, CRLF-joined, without a trailing newline."""
    if len(template) > MAX_TEMPLATE_BYTES:
        raise ValueError("Route extra template exceeds its bound.")
    try:
        text = template.decode("ascii").replace("\r\n", "\n")
    except UnicodeDecodeError as error:
        raise ValueError("Route extra template must be ASCII.") from error
    for key, value in (("__LOAD_SLOT__", spec["load_slot"]), ("__SAVE_SLOT__", spec["save_slot"])):
        if key not in text:
            raise ValueError(f"Route extra template lacks {key}.")
        text = text.replace(key, str(value))
    lines = text.rstrip("\n").split("\n")
    if _PLACEHOLDER.search(text) or any(not line.strip() for line in lines):
        raise ValueError("Route extra template has an unsubstituted placeholder or a blank line.")
    if any(line.strip() in ("g", "gc", "q") for line in lines) or any("\t" in line for line in lines):
        raise ValueError("Route extra template must not resume, quit or contain tabs.")
    if sorted(breakpoint_sites(text)) != sorted(spec["sites"]):
        raise ValueError("Route extra breakpoints differ from its declared sites.")
    return "\r\n".join(lines)


def observe(spec: dict, log: str) -> tuple[dict, list[str]]:
    """Replay the extra's printed markers; echoed commands cannot match them."""
    lines = [line.strip() for line in log.replace("\r\n", "\n").split("\n")]
    calls = [(index, match) for index, line in enumerate(lines) if (match := SAVE_CALL.fullmatch(line))]
    returns = [(index, match) for index, line in enumerate(lines) if (match := SAVE_RETURNED.fullmatch(line))]
    loads = [(index, match) for index, line in enumerate(lines) if (match := LOADSAVE.fullmatch(line))]
    failures = []
    fields = dict(loads=[dict(selected_arg=int(m[1]), selected_global=int(m[2]), accept=int(m[3]),
                              choice=int(m[4]), gd=int(m[5].replace("`", ""), 16)) for _, m in loads],
                  save_call=None, save_returned=None)
    if len(calls) != 1 or len(returns) != 1:
        failures.append("forced save requires exactly one call and one return marker")
    else:
        (call_at, call), (return_at, returned) = calls[0], returns[0]
        fields["save_call"] = dict(slot=int(call[1]), load_slot=int(call[2]), gd=int(call[3].replace("`", ""), 16),
                                   player=int(call[4]), scroll=[int(call[5]), int(call[6])], tick=int(call[7]))
        fields["save_returned"] = dict(slot=int(returned[1]), eax=int(returned[2], 16), tick=int(returned[3]))
        if (fields["save_call"]["slot"], fields["save_call"]["load_slot"]) != (spec["save_slot"], spec["load_slot"]) \
                or fields["save_call"]["gd"] == 0:
            failures.append("forced save call names another slot or has no game data")
        if fields["save_returned"]["slot"] != spec["save_slot"] or fields["save_returned"]["eax"] != 1:
            failures.append("native saveGame did not report success for the forced slot")
        if not call_at < return_at:
            failures.append("forced save returned before its call")
        if not loads or any(index > call_at for index, _ in loads):
            failures.append("the forced save must follow the route's native load")
    if not loads or any(row["selected_arg"] != spec["load_slot"] or row["selected_global"] != spec["load_slot"]
                        for row in fields["loads"]):
        failures.append("the forced route did not load exactly the requested slot")
    return fields, failures

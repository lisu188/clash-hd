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

forced-turn: at the world-map loop site 0x40B0C8 it saves ``before_slot``, then
calls the native nextPlayer (0x40AA60) every 128 ticks until the day word has
advanced by one and player 0 is current again, then saves ``after_slot``. Each
forced call keeps and restores every general register and the flags. The
unacquired hidden mouse leaves stale button state, so the day banner and its
release wait are observed for eight polls before at most one disclosed result
override per banner or button.

forced-campaign: the same forced calls continue through ``days`` consecutive day
transitions, each with its own banner and release wait, before ``after_slot`` is
saved.

neutral_mouse: on a hidden desktop every mouse GetDeviceState fails (not
acquired), yet the game copies its 16-byte stack buffer into the mouse state
regardless (0x47C03C-0x47C062), so stale stack bytes become motion and held
buttons. With ``neutral_mouse: true`` a failed read's buffer is zeroed at the
call's return (0x47C02C): no motion and no buttons, as for an idle player.
Successful reads are untouched. The first four neutralized reads are logged.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

FORCED_SAVE = "forced-save"
FORCED_SAVE_TEMPLATE = "probes/cdb/continuity/hd_multires_forced_save_extra.cdb"
FORCED_TURN = "forced-turn"
FORCED_TURN_TEMPLATE = "probes/cdb/continuity/hd_multires_forced_turn_extra.cdb"
FORCED_CAMPAIGN = "forced-campaign"
FORCED_CAMPAIGN_TEMPLATE = "probes/cdb/continuity/hd_multires_forced_campaign_extra.cdb"
SOURCES = (FORCED_SAVE_TEMPLATE, FORCED_TURN_TEMPLATE, FORCED_CAMPAIGN_TEMPLATE)
# Repeated day transitions, bounded to what fits the 120 s route.
CAMPAIGN_DAYS = (2, 3)
MAX_TEMPLATE_BYTES = 64 * 1024
MAX_SAVE_BYTES = 16 * 1024 * 1024
# The forced load list's rows (hidden_soak_probe_composition.LOAD_SLOT_RANGE).
SLOT_RANGE = (0, 9)
ROUTE, DURATION = "map-idle", 120
MECHANISMS = {"save": "cdb_forced_save_game"}
# The forced map route and soak extra never break here.
SITES = ("0040B0C1",)
TURN_MECHANISMS = {"turn": "cdb_forced_next_player", "save": "cdb_forced_save_game",
                   "turn_input": "cdb_bounded_stale_button_result_overrides"}
# Loop iteration, day increment, banner test and exit, release wait entry, its
# left and right tests and its return; all byte-identical in every candidate.
TURN_SITES = ("0040B0C8", "0040AB44", "0040A943", "0040A9FA", "004609D0", "004609E0", "004609FC", "0040AA06")
NEUTRAL_MOUSE_SITE = "0047C02C"
NEUTRAL_MOUSE_MECHANISM = {"mouse_state": "cdb_neutral_failed_mouse_reads"}
# Header-padding scratch 004003F8 counts logged neutral reads; free in every extra.
NEUTRAL_MOUSE_LINES = (
    "ed 004003f8 0",
    r'bp 0047C02C ".if ((@eax & 0x80000000) != 0) { ed @esp+0x50 0; ed @esp+0x54 0; ed @esp+0x58 0; '
    r'ed @esp+0x5c 0; .if (poi(004003f8) < 0n4) { ed 004003f8 (poi(004003f8)+1); '
    r'.printf \"HDNEUTRAL_MOUSE_READ hresult=%08x\\n\", @eax } }; gc"',
)
NEUTRAL_MOUSE_READ = re.compile(r"HDNEUTRAL_MOUSE_READ hresult=([0-9a-fA-F]{8})")
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


def _prepare_turn(request: dict, *, route: str, duration: int) -> dict:
    if set(request) != {"name", "load_slot", "before_slot", "after_slot"}:
        raise ValueError("A forced-turn extra must be exactly {name, load_slot, before_slot, after_slot}.")
    if (route, duration) != (ROUTE, DURATION):
        raise ValueError("Continuity extras run only on the 120 s map-idle route.")
    load_slot = _slot(request["load_slot"], "load_slot", SLOT_RANGE[0])
    before_slot = _slot(request["before_slot"], "before_slot", 1)
    after_slot = _slot(request["after_slot"], "after_slot", 1)
    if len({load_slot, before_slot, after_slot}) != 3:
        raise ValueError("A forced turn needs distinct load, before and after slots.")
    return dict(request=dict(request), name=FORCED_TURN, load_slot=load_slot, before_slot=before_slot,
                after_slot=after_slot, template=FORCED_TURN_TEMPLATE, mechanisms=dict(TURN_MECHANISMS),
                sites=list(TURN_SITES), pre_files=[f"save/{load_slot}.dat"],
                post_files=[f"save/{before_slot}.dat", f"save/{after_slot}.dat"])


def _prepare_campaign(request: dict, *, route: str, duration: int) -> dict:
    if set(request) != {"name", "load_slot", "before_slot", "after_slot", "days"}:
        raise ValueError("A forced-campaign extra must be exactly {name, load_slot, before_slot, after_slot, days}.")
    if type(request["days"]) is not int or request["days"] not in CAMPAIGN_DAYS:
        raise ValueError(f"A forced campaign runs {CAMPAIGN_DAYS[0]} or {CAMPAIGN_DAYS[1]} days.")
    turn = _prepare_turn({key: request[key] for key in ("name", "load_slot", "before_slot", "after_slot")},
                         route=route, duration=duration)
    return dict(turn, request=dict(request), name=FORCED_CAMPAIGN, days=request["days"],
                template=FORCED_CAMPAIGN_TEMPLATE)


def prepare(request: Any, *, route: str, duration: int) -> dict:
    """Validate one extra request and return the spec the session records."""
    if type(request) is dict and "neutral_mouse" in request:
        if request["neutral_mouse"] is not True:
            raise ValueError("neutral_mouse is either absent or exactly true.")
        spec = _prepare({key: value for key, value in request.items() if key != "neutral_mouse"},
                        route=route, duration=duration)
        return dict(spec, request=dict(request), neutral_mouse=True, sites=spec["sites"] + [NEUTRAL_MOUSE_SITE],
                    mechanisms=dict(spec["mechanisms"], **NEUTRAL_MOUSE_MECHANISM))
    return _prepare(request, route=route, duration=duration)


def _prepare(request: Any, *, route: str, duration: int) -> dict:
    if type(request) is dict and request.get("name") == FORCED_TURN:
        return _prepare_turn(request, route=route, duration=duration)
    if type(request) is dict and request.get("name") == FORCED_CAMPAIGN:
        return _prepare_campaign(request, route=route, duration=duration)
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
    slots = (("__SAVE_SLOT__", spec["save_slot"]),) if spec["name"] == FORCED_SAVE else (
        ("__BEFORE_SLOT__", spec["before_slot"]), ("__AFTER_SLOT__", spec["after_slot"]),
        *((("__DAYS__", spec["days"]),) if spec["name"] == FORCED_CAMPAIGN else ()))
    for key, value in (("__LOAD_SLOT__", spec["load_slot"]), *slots):
        if key not in text:
            raise ValueError(f"Route extra template lacks {key}.")
        text = text.replace(key, str(value))
    lines = text.rstrip("\n").split("\n") + (list(NEUTRAL_MOUSE_LINES) if spec.get("neutral_mouse") else [])
    text = "\n".join(lines)
    if _PLACEHOLDER.search(text) or any(not line.strip() for line in lines):
        raise ValueError("Route extra template has an unsubstituted placeholder or a blank line.")
    if any(line.strip() in ("g", "gc", "q") for line in lines) or any("\t" in line for line in lines):
        raise ValueError("Route extra template must not resume, quit or contain tabs.")
    if sorted(breakpoint_sites(text)) != sorted(spec["sites"]):
        raise ValueError("Route extra breakpoints differ from its declared sites.")
    return "\r\n".join(lines)


def observe(spec: dict, log: str) -> tuple[dict, list[str]]:
    """Replay the extra's printed markers; echoed commands cannot match them."""
    fields, failures = _observe(spec, log)
    if spec.get("neutral_mouse"):
        lines = [line.strip() for line in log.replace("\r\n", "\n").split("\n")]
        reads = [match for line in lines if (match := NEUTRAL_MOUSE_READ.fullmatch(line))]
        fields = dict(fields, neutral_mouse_reads=len(reads))
        if not reads or any(int(match[1], 16) < 0x80000000 for match in reads):
            failures = failures + ["neutral_mouse requires logged neutralized failed mouse reads"]
    return fields, failures


def _observe(spec: dict, log: str) -> tuple[dict, list[str]]:
    if spec["name"] == FORCED_TURN:
        return _observe_turn(spec, log)
    if spec["name"] == FORCED_CAMPAIGN:
        return _observe_campaign(spec, log)
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


TURN_ROWS = {
    "start": re.compile(r"HDTURN_START player=(\d+) day=(\d+) gd=([0-9a-fA-F`]+) tick=(\d+) "
                        r"active=\((\d+),(\d+),(\d+),(\d+),(\d+)\)"),
    "save_call": re.compile(r"HDTURN_SAVE_CALL slot=(\d+) player=(\d+) day=(\d+)"),
    "save_returned": re.compile(r"HDTURN_SAVE_RETURNED slot=(\d+) eax=([0-9a-fA-F]+)"),
    "next_call": re.compile(r"HDTURN_NEXT_CALL advance=(\d+) player=(\d+) day=(\d+) tick=(\d+)"),
    "next_return": re.compile(r"HDTURN_NEXT_RETURN advance=(\d+) player=(\d+) day=(\d+) tick=(\d+)"),
    "day_increment": re.compile(r"HDTURN_DAY_INCREMENT advance=(\d+) player=(\d+) day=(\d+)"),
    "full_day": re.compile(r"HDTURN_FULL_DAY_RETURNED initial_day=(\d+) final_day=(\d+) player=(\d+) advances=(\d+)"),
    "done": re.compile(r"HDTURN_DONE player=(\d+) day=(\d+) advances=(\d+)"),
    "banner_exit": re.compile(r"HDTURN_BANNER_EXIT player=(\d+) day=(\d+) polls=(\d+)"),
    "release_entry": re.compile(r"HDTURN_RELEASE_WAIT_ENTRY wait=(\d+) player=(\d+) day=(\d+)"),
    "release_return": re.compile(r"HDTURN_RELEASE_RETURN player=(\d+) day=(\d+) left=(\d+) right=(\d+)"),
    "banner_override": re.compile(r"HDTURN_FORCED_BANNER_ACK poll=8 value=1"),
    "release_override": re.compile(r"HDTURN_FORCED_RELEASE button=(left|right) poll=8 value=0"),
    "fail": re.compile(r"HDTURN_FAIL (\S+)"),
}


def _observe_turn(spec: dict, log: str) -> tuple[dict, list[str]]:
    """Replay one forced day of turns: its saves, every call and return, the day and every override."""
    lines = [line.strip() for line in log.replace("\r\n", "\n").split("\n")]
    rows = {name: [(index, match) for index, line in enumerate(lines) if (match := pattern.fullmatch(line))]
            for name, pattern in TURN_ROWS.items()}
    ints = lambda match: [int(value) for value in match.groups()]
    failures = [f"turn probe failed: {match[1]}" for _, match in rows["fail"]]
    fields = dict(start=None, saves=[], calls=[ints(m) for _, m in rows["next_call"]],
                  returns=[ints(m) for _, m in rows["next_return"]],
                  day_increments=[ints(m) for _, m in rows["day_increment"]], full_day=None, done=None,
                  banner_exits=len(rows["banner_exit"]), release_waits=len(rows["release_entry"]),
                  release_returns=len(rows["release_return"]),
                  overrides=dict(banner=len(rows["banner_override"]),
                                 left=sum(m[1] == "left" for _, m in rows["release_override"]),
                                 right=sum(m[1] == "right" for _, m in rows["release_override"])))
    if len(rows["start"]) != 1:
        failures.append("forced turn requires exactly one start marker")
    else:
        player, day, gd, tick, *active = (int(value, 16) if index == 2 else int(value)
                                          for index, value in enumerate(rows["start"][0][1].groups()))
        fields["start"] = dict(player=player, day=day, gd=gd, tick=tick, active=active)
        if player != 0 or gd == 0 or not active[0]:
            failures.append("forced turn must start on the loaded game's active player 0")
    calls, returns = rows["save_call"], rows["save_returned"]
    fields["saves"] = [dict(slot=int(c[1]), player=int(c[2]), day=int(c[3]), eax=int(r[2], 16))
                       for (_, c), (_, r) in zip(calls, returns)]
    if [(save["slot"], save["eax"]) for save in fields["saves"]] != [(spec["before_slot"], 1), (spec["after_slot"], 1)] \
            or len(calls) != 2 or len(returns) != 2 or any(int(r[1]) != int(c[1]) for (_, c), (_, r) in zip(calls, returns)):
        failures.append("forced turn requires a successful before save and after save of its own slots")
    advances = len(fields["calls"])
    if not 1 <= advances <= 5 or [row[0] for row in fields["calls"]] != list(range(1, advances + 1)) \
            or [row[0] for row in fields["returns"]] != list(range(1, advances + 1)):
        failures.append("every forced nextPlayer call needs its own numbered return")
    if len(rows["full_day"]) != 1 or len(rows["done"]) != 1:
        failures.append("forced turn requires one full-day return and one completion")
    else:
        initial, final, player, count = ints(rows["full_day"][0][1])
        fields["full_day"] = dict(initial_day=initial, final_day=final, player=player, advances=count)
        fields["done"] = dict(zip(("player", "day", "advances"), ints(rows["done"][0][1])))
        if final != (initial + 1) & 0xFFFF or player != 0 or count != advances:
            failures.append("the forced calls did not return through exactly one new day to player 0")
    if len(fields["day_increments"]) != 1:
        failures.append("the native day increment must be observed exactly once")
    order = [index for name in ("start", "save_call", "next_call", "full_day", "done") for index, _ in rows[name][:1]]
    if order != sorted(order) or (calls and rows["full_day"] and not calls[-1][0] > rows["full_day"][0][0]):
        failures.append("forced turn markers are out of order")
    if fields["release_returns"] != fields["release_waits"]:
        failures.append("every release wait must return to the day banner caller")
    return fields, failures


CAMPAIGN_ROWS = {
    "start": re.compile(r"HDCAMP_START days=(\d+) player=(\d+) day=(\d+) gd=([0-9a-fA-F`]+) tick=(\d+) "
                        r"active=\((\d+),(\d+),(\d+),(\d+),(\d+)\)"),
    **{name: re.compile(pattern.pattern.replace("HDTURN_", "HDCAMP_")) for name, pattern in TURN_ROWS.items()
       if name not in ("start", "done")},
    "day_returned": re.compile(r"HDCAMP_DAY_RETURNED days=(\d+) day=(\d+) player=(\d+) advances=(\d+)"),
    "done": re.compile(r"HDCAMP_DONE player=(\d+) day=(\d+) advances=(\d+) days=(\d+)"),
}


def _observe_campaign(spec: dict, log: str) -> tuple[dict, list[str]]:
    """Replay a forced campaign: its saves, every call and return, each day transition and every override."""
    lines = [line.strip() for line in log.replace("\r\n", "\n").split("\n")]
    rows = {name: [(index, match) for index, line in enumerate(lines) if (match := pattern.fullmatch(line))]
            for name, pattern in CAMPAIGN_ROWS.items()}
    ints = lambda match: [int(value) for value in match.groups()]
    days = spec["days"]
    failures = [f"campaign probe failed: {match[1]}" for _, match in rows["fail"]]
    fields = dict(start=None, saves=[], calls=[ints(m) for _, m in rows["next_call"]],
                  returns=[ints(m) for _, m in rows["next_return"]],
                  day_increments=[ints(m) for _, m in rows["day_increment"]],
                  days_returned=[ints(m) for _, m in rows["day_returned"]], full_day=None, done=None,
                  banner_exits=len(rows["banner_exit"]), release_waits=len(rows["release_entry"]),
                  release_returns=len(rows["release_return"]),
                  overrides=dict(banner=len(rows["banner_override"]),
                                 left=sum(m[1] == "left" for _, m in rows["release_override"]),
                                 right=sum(m[1] == "right" for _, m in rows["release_override"])))
    if len(rows["start"]) != 1:
        failures.append("forced campaign requires exactly one start marker")
    else:
        count, player, day, gd, tick, *active = (int(value, 16) if index == 3 else int(value)
                                                 for index, value in enumerate(rows["start"][0][1].groups()))
        fields["start"] = dict(days=count, player=player, day=day, gd=gd, tick=tick, active=active)
        if count != days or player != 0 or gd == 0 or not active[0]:
            failures.append("forced campaign must start its requested days on the loaded game's active player 0")
    calls, returns = rows["save_call"], rows["save_returned"]
    fields["saves"] = [dict(slot=int(c[1]), player=int(c[2]), day=int(c[3]), eax=int(r[2], 16))
                       for (_, c), (_, r) in zip(calls, returns)]
    if [(save["slot"], save["eax"]) for save in fields["saves"]] != [(spec["before_slot"], 1), (spec["after_slot"], 1)] \
            or len(calls) != 2 or len(returns) != 2 or any(int(r[1]) != int(c[1]) for (_, c), (_, r) in zip(calls, returns)):
        failures.append("forced campaign requires a successful before save and after save of its own slots")
    advances = len(fields["calls"])
    if not days <= advances <= 5 * days or [row[0] for row in fields["calls"]] != list(range(1, advances + 1)) \
            or [row[0] for row in fields["returns"]] != list(range(1, advances + 1)):
        failures.append("every forced nextPlayer call needs its own numbered return")
    if len(rows["full_day"]) != 1 or len(rows["done"]) != 1:
        failures.append("forced campaign requires one final return and one completion")
    else:
        initial, final, player, count = ints(rows["full_day"][0][1])
        fields["full_day"] = dict(initial_day=initial, final_day=final, player=player, advances=count)
        fields["done"] = dict(zip(("player", "day", "advances", "days"), ints(rows["done"][0][1])))
        if final != (initial + days) & 0xFFFF or player != 0 or count != advances or fields["done"]["days"] != days:
            failures.append("the forced calls did not return through exactly the requested new days to player 0")
    if len(fields["day_increments"]) != days or [row[0] for row in fields["days_returned"]] != list(range(1, days + 1)):
        failures.append("every requested day needs one native increment and one return to player 0")
    order = [index for name in ("start", "save_call", "next_call", "full_day", "done") for index, _ in rows[name][:1]]
    if order != sorted(order) or (calls and rows["full_day"] and not calls[-1][0] > rows["full_day"][0][0]):
        failures.append("forced campaign markers are out of order")
    if fields["release_returns"] != fields["release_waits"]:
        failures.append("every release wait must return to the day banner caller")
    return fields, failures

#!/usr/bin/env python3
"""Offline, fail-closed summary for the bounded day diagnostic, not release proof.

No game/debugger/process APIs are used. A generic surface Passed=true is never
a day-transition pass. Cleanup is a separately supplied, identity-bound record
of actual observations, not inferred from a timeout, exit code, or absent file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "continuity_day_diagnostic_summary_v1"
CLEANUP_SCHEMA = "continuity_day_cleanup_v1"
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
STABLE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch"
PATCH_COUNTS = {STABLE: 118, STABLE + "-combinedui-validation": 166}
IDENTITY_SITES = {
    "DAYDIAG_NEXT_CALL": 0x406FA1, "DAYDIAG_NEXT_RETURN": 0x406FA1,
    "DAYDIAG_BANNER_ENTRY": 0x40A820, "DAYDIAG_BANNER_EXIT": 0x40A9FA,
    "DAYDIAG_RELEASE_WAIT_ENTRY": 0x4609D0, "DAYDIAG_RELEASE_RETURN": 0x40AA06,
    "DAYDIAG_INPUT_POLL_ENTRY": 0x47BFD1,
}
DEVICE_SITES = {"keyboard": (0x47BFF9, 0x47BFFC), "mouse": (0x47C029, 0x47C02C)}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def same_sha(left: Any, right: Any) -> bool:
    return is_sha(left) and is_sha(right) and left.lower() == right.lower()


def same_path(left: Any, right: Any) -> bool:
    return (isinstance(left, str) and isinstance(right, str) and bool(left.strip())
            and ntpath.normcase(ntpath.normpath(left)) == ntpath.normcase(ntpath.normpath(right)))


def number(value: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+", value):
        raise ValueError("invalid decimal marker field")
    return int(value)


def pointer(value: Any) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"(?:0x)?[0-9a-fA-F`]+", value):
        raise ValueError("invalid hexadecimal marker field")
    return int(value.replace("`", ""), 16)


def fields(body: str) -> dict[str, str]:
    pairs = re.findall(r"(\w+)=((?:\([^)]*\))|\S+)", body)
    if " ".join(f"{key}={value}" for key, value in pairs) != body or len(dict(pairs)) != len(pairs):
        raise ValueError("malformed or duplicate marker fields")
    return dict(pairs)


def tick_delta(later: int, earlier: int) -> int:
    if not 0 <= later <= 0xFFFFFFFF or not 0 <= earlier <= 0xFFFFFFFF:
        raise ValueError("tick outside 32-bit source range")
    return (later - earlier) & 0xFFFFFFFF


def tick_value(value: str) -> int:
    # CDB's %d can render the same 32-bit tick with a negative signed spelling.
    result = number(value)
    if not -(1 << 31) <= result <= 0xFFFFFFFF:
        raise ValueError("tick outside signed/unsigned 32-bit spelling")
    return result & 0xFFFFFFFF


def diagnostic_versions(text: str) -> list[int]:
    return [int(value) for value in re.findall(r"(?m)^(?:\.echo )?=== Clash95 bounded day-transition diagnostic v(\d+) ===\r?$", text)]


def analyze_markers(log_text: str) -> dict[str, Any]:
    errors: list[str] = []
    events: list[dict[str, Any]] = []
    contract = False
    players = None
    start = None
    active_call = None
    calls = []
    last_return = None
    increment = None
    full_day = None
    post_day = None
    ready = None
    surface_completed = False
    ack_count = 0
    bounded_wait = None
    input_returns = []
    input_return_observations = []
    input_identity_observations = []
    pending_device = None
    pending_by_thread = {}
    contract_failure = False
    runtime_failure = False
    versions = diagnostic_versions(log_text)
    version = versions[0] if len(versions) == 1 else None
    if len(versions) > 1 or version not in (None, 1, 2, 3, 4, 5, 6, 7):
        errors.append("duplicate or unsupported diagnostic version disclosure")
    forced_release = {"left": 0, "right": 0}
    release_waits = []
    input_phases = []

    def require(condition: bool, reason: str):
        if not condition:
            raise ValueError(reason)

    def pending_input() -> bool:
        return pending_device is not None or bool(pending_by_thread)

    def identity_fields(f: dict[str, str], name: str) -> dict[str, int]:
        identity = {key: pointer(f[key]) for key in ("tid", "eip", "esp")}
        site = IDENTITY_SITES.get(name)
        if name in ("DAYDIAG_GETDEVICESTATE_CALL", "DAYDIAG_GETDEVICESTATE_RETURN"):
            site = DEVICE_SITES[f["device"]][name.endswith("RETURN")]
        require(identity["eip"] == site, "trace identity has wrong native EIP")
        require(0 < identity["tid"] <= 0xFFFFFFFF and 0 < identity["esp"] <= 0xFFFFFFFF
                and identity["esp"] % 4 == 0, "trace identity has invalid OS TID/ESP")
        return identity

    def require_owner(identity: dict[str, int]):
        require(active_call is not None and identity["tid"] == active_call["identity"]["tid"],
                "native phase boundary has wrong owner thread")

    for line_number, original in enumerate(log_text.splitlines(), 1):
        line = original.strip()
        if re.search(r"(?:^AV_SURFDUMP\b|^SURFDUMP_(?:APP_REQUEST_QUIT|INVALID)\b|Syntax error|Couldn't resolve|Couldn't insert|Memory access error)", line):
            runtime_failure = True
            errors.append(f"line {line_number}: runtime/debugger failure marker")
        if line.startswith("DAYDIAG_CONTRACT_FAIL "):
            contract_failure = True
            errors.append(f"line {line_number}: {line}")
            continue
        if line.startswith("DAYDIAG_FAIL "):
            errors.append(f"line {line_number}: {line}")
            continue
        if not line.startswith(("DAYDIAG_", "SURFDUMP_READY ", "SURFDUMP_HOST_READY", "SURFDUMP_DONE")):
            continue
        name, _, body = line.partition(" ")
        events.append({"line": line_number, "marker": name})
        try:
            f = fields(body)
            if name == "DAYDIAG_GETDEVICESTATE_RETURN":
                observation = {"line": line_number, "device": f["device"], "hresult": pointer(f["hresult"])}
                if version == 7:
                    # Retain even malformed/unpaired identities and failed HRESULTs.
                    observation["raw_identity"] = {key: f.get(key) for key in ("tid", "eip", "esp")}
                input_return_observations.append(observation)
            identity = None
            if name in IDENTITY_SITES or name in ("DAYDIAG_GETDEVICESTATE_CALL", "DAYDIAG_GETDEVICESTATE_RETURN"):
                if version == 7:
                    identity_observation = {"line": line_number, "marker": name,
                        "advance": active_call["advance"] if active_call else None,
                        "raw_identity": {key: f.get(key) for key in ("tid", "eip", "esp")}}
                    if "device" in f:
                        identity_observation["device"] = f["device"]
                    input_identity_observations.append(identity_observation)
                    identity = identity_fields(f, name)
                    identity_observation["identity"] = identity
                    events[-1]["identity"] = identity
                    if name == "DAYDIAG_GETDEVICESTATE_RETURN":
                        input_return_observations[-1]["identity"] = identity
                else:
                    require(not {"tid", "eip"}.intersection(f), "thread identity requires declared diagnostic v7")
            if (version in (6, 7) and active_call is not None and active_call["release"] is not None
                    and active_call["release"]["returned"] and not active_call["trace"].get("ended")):
                require(name == "DAYDIAG_INPUT_TRACE_END", "release return must immediately end the input trace")
            if name == "DAYDIAG_CONTRACT_PASS":
                require(not contract and start is None, "duplicate/late contract")
                require(f == {"resolution": "800x600", "candidate_sha_source": "matching_outer_byte_report", "byte_gate_required": "1"}, "unexpected native contract disclosure")
                contract = True
            elif name == "DAYDIAG_PLAYERS":
                require(contract and players is None and start is None, "players before contract or duplicate/late")
                active = tuple(map(number, f["active"].strip("()").split(",")))
                controllers = tuple(map(number, f["controller"].strip("()").split(",")))
                require(len(active) == len(controllers) == 5 and active[0] != 0, "expected five slots with active player0")
                players = {"active": active, "controller": controllers}
            elif name == "DAYDIAG_START":
                require(contract and players is not None and start is None, "start must follow one contract/players record")
                start = {key: number(f[key]) for key in ("mode", "player", "day", "tick", "forced_nextplayer")}
                start["tick"] = tick_value(f["tick"])
                start["gd"] = pointer(f["gd"])
                require(start["mode"] in (0, 1) and start["player"] == 0 and 0 <= start["day"] <= 65535 and start["gd"] > 0 and start["forced_nextplayer"] == 1, "invalid initial native-call disclosure/state")
            elif name == "DAYDIAG_NEXT_CALL":
                require(start is not None and active_call is None and full_day is None and bounded_wait is None, "overlapping/late call or call without start")
                call = {key: number(f[key]) for key in ("advance", "player", "day", "tick")}
                call["tick"] = tick_value(f["tick"])
                call["saved_esp"] = pointer(f["saved_esp"])
                if version == 7:
                    require(identity["esp"] == call["saved_esp"], "native call identity differs from saved ESP")
                    call["identity"] = identity
                previous = last_return or start
                require(call["advance"] == len(calls) + 1 <= 5 and call["player"] == previous["player"] and call["day"] == previous["day"], "advance/player/day does not follow previous return")
                require(128 <= tick_delta(call["tick"], previous["tick"]) <= 180 * 64 and call["saved_esp"] > 0 and f["mechanism"] == "forced_native_call", "invalid call cadence/stack/mechanism")
                phase = {"advance": call["advance"], "phase": "native_call", "poll_count": 0, "limited": False}
                if version == 7:
                    phase["polls_by_thread"] = {}
                input_phases.append(phase)
                call.update(join=None, banner_open=False, banner_tests=[], input_returns=[], release=None,
                            release_required=False, trace=phase)
                calls.append(call)
                active_call = call
            elif name in ("DAYDIAG_NATIVE_DAY_INCREMENT", "DAYDIAG_AFTER_DAY_BRANCH"):
                require(active_call is not None and start is not None, "native day marker without outstanding call")
                require(number(f["advance"]) == active_call["advance"], "native marker advance mismatch")
                row = {key: number(f[key]) for key in ("advance", "player", "day")}
                if name == "DAYDIAG_NATIVE_DAY_INCREMENT":
                    require(increment is None and active_call["join"] is None and row["player"] == 0 and row["day"] == (start["day"] + 1) & 65535 and pointer(f["gd"]) == start["gd"] and active_call["player"] > 0, "invalid/duplicate day increment")
                    increment = row
                else:
                    expected_day = increment["day"] if increment is not None else start["day"]
                    require(active_call["join"] is None and row["day"] == expected_day and 0 <= row["player"] < 5, "invalid/duplicate branch join")
                    if increment is not None:
                        require(row["player"] == 0 and row["advance"] == increment["advance"], "join does not match increment")
                    active_call["join"] = row
            elif name == "DAYDIAG_BANNER_ENTRY":
                if version == 7:
                    require_owner(identity)
                require(active_call is not None and active_call["join"] is not None and not active_call["banner_open"], "banner without joined call or nested banner")
                require(number(f["advance"]) == active_call["advance"] and pointer(f["ret"]) > 0, "banner call identity mismatch")
                require(all(number(f[k]) == active_call["join"][k] for k in ("player", "day")), "banner entry state mismatch")
                active_call["banner_open"] = True
            elif name == "DAYDIAG_BANNER_TEST":
                require(active_call is not None and active_call["banner_open"], "banner test without entry")
                row = {key: number(f[key]) for key in ("poll", "observed_eax", "player", "day")}
                row.update({key: pointer(f[key]) for key in ("button_flags", "lbtn", "rbtn")})
                require(row["poll"] == len(active_call["banner_tests"]) + 1 <= 8, "banner poll order/count")
                require(all(row[k] == active_call["join"][k] for k in ("player", "day")) and row["observed_eax"] == (row["button_flags"] & 1), "banner test state/result mismatch")
                active_call["banner_tests"].append(row)
            elif name == "DAYDIAG_FORCED_BANNER_ACK":
                require(start is not None and active_call is not None and active_call["banner_open"] and start["mode"] == 1 and ack_count == 0, "undisclosed/repeated forced acknowledgment")
                require(len(active_call["banner_tests"]) == 8 and active_call["banner_tests"][-1]["observed_eax"] == 0, "ack without eight zero-result observations")
                require(f == {"banner_tests": "8", "observed_eax": "0", "mechanism": "override_banner_button_result", "value": "1", "manual_input_proof": "0"}, "invalid ack disclosure")
                ack_count += 1
            elif name == "DAYDIAG_OBSERVED_BANNER_INPUT_WAIT":
                require(active_call is not None and active_call["banner_open"] and bounded_wait is None and f == {"acknowledgment_not_attempted": "1"}, "invalid bounded wait marker")
                tests = active_call["banner_tests"]
                require(len(tests) == 8 and all(t["observed_eax"] == 0 and t["button_flags"] & 1 == 0 and t["lbtn"] & 128 == 0 and t["rbtn"] & 128 == 0 for t in tests), "bounded wait lacks eight zero button observations")
                bounded_wait = {"advance": active_call["advance"], "input_returns": list(active_call["input_returns"])}
            elif name == "DAYDIAG_BANNER_EXIT":
                if version == 7:
                    require_owner(identity)
                require(active_call is not None and active_call["banner_open"] and bounded_wait is None, "exit without banner or after bounded stop")
                # Only the banner ACK consumes mode 1 at 0x00400304. Release
                # overrides use separate flags at 0x0040034c and retain mode 1.
                require(number(f["mode"]) == (2 if ack_count else start["mode"]), "banner exit mode mismatch")
                require(all(number(f[k]) == active_call["join"][k] for k in ("player", "day")), "banner exit state mismatch")
                require(not pending_input(), "banner exit interrupts a traced input call")
                active_call["banner_open"] = False
                active_call["release_required"] = version in (4, 5, 6, 7)
                phase = {"advance": active_call["advance"], "phase": "release_wait", "poll_count": 0, "limited": False}
                if version == 7:
                    phase["polls_by_thread"] = {}
                input_phases.append(phase)
                active_call["trace"] = phase
            elif name == "DAYDIAG_RELEASE_WAIT_ENTRY":
                require(version in (4, 5, 6, 7) and active_call is not None and active_call["release_required"]
                        and active_call["join"] is not None and not active_call["banner_open"]
                        and active_call["release"] is None and bounded_wait is None, "release entry lacks declared banner-exit phase or is repeated")
                if version == 7:
                    require_owner(identity)
                require(set(f) == {"ret", "object", "player", "day", "esp"} | ({"tid", "eip"} if version == 7 else set()), "unexpected release entry fields")
                require(pointer(f["ret"]) == 0x40AA06 and pointer(f["object"]) == 0x544CD8 and pointer(f["esp"]) > 0,
                        "release entry native target/object/stack mismatch")
                require(all(number(f[k]) == active_call["join"][k] for k in ("player", "day")), "release entry state mismatch")
                release = {"advance": active_call["advance"], "player": number(f["player"]), "day": number(f["day"]),
                           "esp": pointer(f["esp"]), "left_tests": [], "right_tests": [], "left_effective": None,
                           "right_effective": None, "returned": False, "next": "left"}
                active_call["release"] = release
                release_waits.append(release)
            elif name in ("DAYDIAG_RELEASE_LEFT_TEST", "DAYDIAG_RELEASE_RIGHT_TEST"):
                require(active_call is not None and active_call["release"] is not None and bounded_wait is None,
                        "release test without entry or after bounded stop")
                release = active_call["release"]
                require(not release["returned"] and set(f) == {"poll", "observed_eax", "button_flags", "lbtn", "rbtn", "player", "day"},
                        "late release test or unexpected fields")
                button = "left" if name.endswith("LEFT_TEST") else "right"
                row = {key: number(f[key]) for key in ("poll", "observed_eax", "player", "day")}
                row.update({key: pointer(f[key]) for key in ("button_flags", "lbtn", "rbtn")})
                require(all(row[k] == release[k] for k in ("player", "day"))
                        and row["observed_eax"] == int(bool(row["button_flags"] & (1 if button == "left" else 2)))
                        and 0 <= row["button_flags"] <= 0xFFFFFFFF and 0 <= row["lbtn"] <= 255 and 0 <= row["rbtn"] <= 255,
                        "release test native result/state mismatch")
                if button == "left":
                    require(release["next"] == "left" and row["poll"] == len(release["left_tests"]) + 1 <= 8,
                            "release left poll order/count/phase mismatch")
                    release["left_effective"] = row["observed_eax"]
                    release["right_effective"] = None
                    release["next"] = "left" if row["observed_eax"] else "right"
                else:
                    require(release["next"] == "right" and release["left_effective"] == 0
                            and row["poll"] == release["left_tests"][-1]["poll"]
                            and (not release["right_tests"] or release["right_tests"][-1]["poll"] < row["poll"]),
                            "right release test lacks zero left result in the same iteration")
                    release["right_effective"] = row["observed_eax"]
                    release["next"] = "left" if row["observed_eax"] else "return"
                release[button + "_tests"].append(row)
            elif name == "DAYDIAG_FORCED_RELEASE":
                require(version in (5, 6, 7) and start is not None and start["mode"] == 1 and active_call is not None
                        and active_call["release"] is not None and bounded_wait is None,
                        "controlled release is undeclared or outside the release phase")
                require(set(f) == {"button", "tests", "observed_eax", "mechanism", "value", "manual_input_proof"}
                        and f["button"] in forced_release, "malformed controlled release disclosure")
                button, release = f["button"], active_call["release"]
                tests = release[button + "_tests"]
                require(not release["returned"] and forced_release[button] == 0 and tests
                        and events[-2]["marker"] == "DAYDIAG_RELEASE_" + button.upper() + "_TEST",
                        "repeated controlled release or missing immediately preceding button observation")
                require(tests[-1]["poll"] == 8 and number(f["tests"]) == len(tests)
                        and number(f["observed_eax"]) == tests[-1]["observed_eax"] == 1
                        and f["mechanism"] == "override_release_button_result" and f["value"] == "0" and f["manual_input_proof"] == "0",
                        "controlled release observation/count/value mismatch")
                forced_release[button] += 1
                release[button + "_effective"] = 0
                release["next"] = "right" if button == "left" else "return"
            elif name == "DAYDIAG_OBSERVED_RELEASE_INPUT_WAIT":
                require(active_call is not None and active_call["release"] is not None and bounded_wait is None,
                        "bounded release wait without entry or repeated")
                require(set(f) == {"button", "tests", "release_not_attempted"} and f["button"] in ("left", "right")
                        and f["tests"] == "8" and f["release_not_attempted"] == "1", "invalid bounded release disclosure")
                release, button = active_call["release"], f["button"]
                tests = release[button + "_tests"]
                require(not release["returned"] and tests and tests[-1]["poll"] == 8 and tests[-1]["observed_eax"] == 1
                        and release[button + "_effective"] == 1 and forced_release[button] == 0,
                        "bounded release wait lacks an unmodified held-button observation at iteration eight")
                bounded_wait = {"kind": "release", "button": button, "advance": active_call["advance"],
                                "observed_button_tests": len(tests), "input_returns": list(active_call["input_returns"])}
            elif name == "DAYDIAG_RELEASE_RETURN":
                if version == 7:
                    require_owner(identity)
                require(active_call is not None and active_call["release"] is not None and bounded_wait is None,
                        "release return without entry or after bounded stop")
                release = active_call["release"]
                require(set(f) == {"player", "day", "esp"} | ({"tid", "eip"} if version == 7 else set())
                        and not release["returned"] and release["next"] == "return"
                        and release["left_effective"] == release["right_effective"] == 0,
                        "release return lacks both zero query results or is repeated")
                require(all(number(f[k]) == release[k] for k in ("player", "day"))
                        and pointer(f["esp"]) == release["esp"] + 4, "release return state/ESP mismatch")
                release["returned"] = True
                release["return_esp"] = pointer(f["esp"])
            elif name == "DAYDIAG_INPUT_TRACE_END":
                require(version in (6, 7) and active_call is not None and active_call["release"] is not None
                        and active_call["release"]["returned"] and active_call["trace"]["phase"] == "release_wait"
                        and not active_call["trace"].get("ended") and not pending_input()
                        and f == {"phase": "release_wait"}, "invalid, premature, or duplicate input trace end")
                active_call["trace"]["ended"] = True
            elif name == "DAYDIAG_INPUT_POLL_ENTRY":
                require(active_call is not None and pointer(f["ret"]) > 0 and pointer(f["object"]) > 0, "input poll outside forced call")
                phase = active_call["trace"]
                require(not phase.get("ended"), "input observation after declared trace end")
                require(not phase["limited"] and phase["poll_count"] < 16
                        and (identity["tid"] not in pending_by_thread if version == 7 else pending_device is None),
                        "input polling exceeded phase cap or overlaps an unfinished device call")
                if version == 7:
                    # The probe's cap is global; call/return pairing is per OS
                    # thread and native poll stack. Foreign observations remain
                    # diagnostics and cannot stand in for owner input evidence.
                    phase["polls_by_thread"][identity["tid"]] = {
                        "line": line_number, "identity": identity, "devices": [],
                        "enabled": {device: number(f[device + "_enabled"]) != 0 for device in DEVICE_SITES},
                        "owner_thread": identity["tid"] == active_call["identity"]["tid"],
                    }
                phase["poll_count"] += 1
            elif name == "DAYDIAG_INPUT_TRACE_LIMIT":
                require(active_call is not None and f == {"polls": "16"}, "input trace limit outside call or malformed")
                phase = active_call["trace"]
                require(not phase.get("ended"), "input observation after declared trace end")
                require(phase["poll_count"] == 16 and not phase["limited"] and not pending_input(),
                        "input trace limit lacks sixteen complete polls or is repeated")
                phase["limited"] = True
            elif name == "DAYDIAG_GETDEVICESTATE_CALL":
                require(active_call is not None
                        and (identity["tid"] not in pending_by_thread if version == 7 else pending_device is None),
                        "overlapping input call or input outside advance")
                require(not active_call["trace"].get("ended"), "input observation after declared trace end")
                require(active_call["trace"]["poll_count"] > 0 and not active_call["trace"]["limited"], "device call outside active input trace phase")
                require(f["device"] in ("mouse", "keyboard") and pointer(f["target"]) > 0 and number(f["bytes"]) == {"mouse": 16, "keyboard": 256}[f["device"]], "invalid input device contract")
                if version == 7:
                    poll = active_call["trace"]["polls_by_thread"].get(identity["tid"])
                    require(poll is not None and identity["esp"] == poll["identity"]["esp"] - 0x74,
                            "input call lacks same-thread native poll stack")
                    require(poll["enabled"][f["device"]] and f["device"] not in poll["devices"],
                            "input device disabled or called twice in one native poll")
                    require(not (f["device"] == "keyboard" and "mouse" in poll["devices"]),
                            "keyboard call follows mouse in one native poll")
                    poll["devices"].append(f["device"])
                    pending_by_thread[identity["tid"]] = {"device": f["device"], "identity": identity,
                        "call_line": line_number, "poll_line": poll["line"], "owner_thread": poll["owner_thread"]}
                else:
                    pending_device = f["device"]
            elif name == "DAYDIAG_GETDEVICESTATE_RETURN":
                require(active_call is None or not active_call["trace"].get("ended"), "input observation after declared trace end")
                if version == 7:
                    pending = pending_by_thread.get(identity["tid"])
                    require(active_call is not None and pending is not None and pending["device"] == f["device"],
                            "input return lacks matching same-thread call")
                    require(identity["esp"] == pending["identity"]["esp"] + 0x0C,
                            "input return ESP does not match native stdcall cleanup")
                    row = {**pending, "return_identity": identity, "return_line": line_number,
                           "hresult": pointer(f["hresult"])}
                    del pending_by_thread[identity["tid"]]
                else:
                    require(active_call is not None and pending_device == f["device"], "input return lacks matching call")
                    row = {"device": pending_device, "hresult": pointer(f["hresult"])}
                    pending_device = None
                input_returns.append(row)
                if version != 7 or row["owner_thread"]:
                    active_call["input_returns"].append(row)
            elif name == "DAYDIAG_NEXT_RETURN":
                if version == 7:
                    require_owner(identity)
                require(active_call is not None and active_call["join"] is not None and not active_call["banner_open"] and not pending_input() and bounded_wait is None, "return lacks join/banner exit/input return")
                require(not active_call["release_required"] or active_call["release"] is not None and active_call["release"]["returned"],
                        "native return lacks completed release-entry/query/return phase")
                row = {key: number(f[key]) for key in ("advance", "player", "day", "tick")}
                row["tick"] = tick_value(f["tick"])
                row["esp"] = pointer(f["esp"])
                require(all(row[k] == active_call["join"][k] for k in ("advance", "player", "day")) and row["esp"] == active_call["saved_esp"], "return identity/ESP mismatch")
                require(tick_delta(row["tick"], active_call["tick"]) <= 180 * 64, "invalid return tick")
                last_return = row
                active_call = None
            elif name == "DAYDIAG_FULL_DAY_RETURNED":
                require(start is not None and increment is not None and last_return is not None and active_call is None and full_day is None, "full-day claim without native increment/return")
                require(number(f["initial_day"]) == start["day"] and number(f["final_day"]) == last_return["day"] == (start["day"] + 1) & 65535 and number(f["player"]) == last_return["player"] == 0, "full-day state mismatch")
                require(last_return["advance"] == increment["advance"] and number(f["mode"]) == (2 if ack_count else start["mode"]), "full-day advance/mode mismatch")
                full_day = {"initial_day": start["day"], "final_day": last_return["day"], "player": 0}
            elif name == "DAYDIAG_POST_DAY_REDRAW":
                require(full_day is not None and post_day is None and ready is None, "redraw before full return or duplicate")
                require(number(f["player"]) == 0 and number(f["day"]) == full_day["final_day"] and f["dump_released"] == "1", "post-day redraw state mismatch")
                post_day = full_day.copy()
            elif name == "SURFDUMP_READY":
                require(post_day is not None and ready is None, "surface ready before post-day redraw or duplicate")
                width, height = map(number, f["size"].strip("()").split(","))
                ready = {"RedrawSeq": number(f["redraw_seq"]), "Surface": f["surface"], "Width": width, "Height": height, "Base": f["base"], "Bytes": number(f["bytes"])}
                require((width, height, ready["Bytes"]) == (800, 600, 480000) and ready["RedrawSeq"] >= 4 and pointer(ready["Surface"]) > 0 and pointer(ready["Base"]) > 0, "invalid ready surface")
            elif name in ("SURFDUMP_HOST_READY", "SURFDUMP_DONE"):
                require(ready is not None and not body and not surface_completed, "surface completion before ready or duplicate")
                surface_completed = True
            else:
                raise ValueError("unknown diagnostic marker")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"line {line_number}: {name}: {exc}")

    if pending_device is not None:
        errors.append(f"unreturned traced {pending_device} GetDeviceState call at end of log")
    for thread, pending in pending_by_thread.items():
        errors.append(f"unreturned traced {pending['device']} GetDeviceState call for OS thread {thread:x} at end of log")
    if (version in (6, 7) and active_call is not None and active_call["release"] is not None
            and active_call["release"]["returned"] and not active_call["trace"].get("ended")):
        errors.append("release return lacks required input trace end")
    if contract_failure:
        observed = "contract_failed"
    elif runtime_failure:
        observed = "runtime_or_debugger_failure"
    elif bounded_wait:
        observed = ("bounded_release_input_wait" if bounded_wait.get("kind") == "release" else
                    "bounded_banner_input_wait" if bounded_wait["input_returns"] and not pending_input() else "banner_wait_input_calls_unverified")
    elif full_day is not None and post_day is not None and ready is not None:
        observed = ("full_day_returned_with_controlled_input_queries" if any(forced_release.values()) else
                    "full_day_returned_with_forced_ack" if ack_count else "full_day_returned")
        if not surface_completed:
            errors.append("surface completion marker missing after ready")
    elif increment is not None:
        observed = ("native_day_increment_without_complete_return" if last_return is None or last_return["advance"] != increment["advance"]
                    else "native_day_return_without_post_day_proof")
    else:
        observed = "incomplete"
    return {"errors": errors, "events": events, "observed_classification": observed,
            "diagnostic_version": version, "native_day_increment_observed": increment is not None, "native_day_increment": increment,
            "native_day_return_observed": increment is not None and last_return is not None and last_return["advance"] == increment["advance"],
            "contract_passed": contract, "start": start, "players": players,
            "call_count": len(calls), "full_day": full_day, "surface": ready,
            "surface_completed": surface_completed,
            "forced_ack_count": ack_count, "input_returns": input_returns,
            "input_return_observations": input_return_observations,
            "input_identity_observations": input_identity_observations,
            "forced_release_counts": forced_release, "release_waits": release_waits,
            "bounded_wait": bounded_wait, "input_trace_phases": input_phases,
            "input_failure_hresult": [r for r in input_return_observations if r["hresult"] & 0x80000000],
            "pending_input_call": pending_device, "pending_input_calls_by_thread": pending_by_thread}


def evaluate(summary: dict, log_data: bytes, generated_probe_data: bytes, byte_report: dict,
             cleanup: dict | None, *, expected_stage: str, expected_candidate_sha256: str,
             expected_generated_probe_sha256: str, expected_mode: int = 0,
             raw_data: bytes | None = None) -> dict:
    markers = analyze_markers(log_data.decode("utf-8-sig", errors="replace"))
    failures = list(markers["errors"])

    def check(condition, reason):
        if not condition:
            failures.append(reason)

    log_sha, probe_sha = sha(log_data), sha(generated_probe_data)
    log_text = log_data.decode("utf-8-sig", errors="replace")
    command_lines = re.findall(r"(?m)^CommandLine: (.+)\r?$", log_text)
    check(len(command_lines) == 1 and same_path(command_lines[0].strip().strip('"'), summary.get("CandidatePath")), "logged candidate command does not match outer summary")
    probe_loads = re.findall(r"(?m)^\d+:\d+> \$\$><(.+)\r?$", log_text)
    check(len(probe_loads) == 1 and same_path(probe_loads[0].strip(), summary.get("GeneratedProbe")), "logged generated-probe path does not match outer summary")
    check(expected_stage in PATCH_COUNTS, "unsupported diagnostic stage")
    check(same_sha(expected_candidate_sha256, summary.get("CandidateSha256")), "outer candidate SHA mismatch/missing")
    check(summary.get("Stage") == expected_stage and summary.get("Resolution") == "800x600", "outer stage/resolution mismatch")
    check(same_sha(probe_sha, expected_generated_probe_sha256), "generated-probe SHA mismatch")
    check(diagnostic_versions(generated_probe_data.decode("utf-8-sig", errors="replace")) == diagnostic_versions(log_text),
          "logged diagnostic version differs from the generated probe")
    modes = re.findall(rb"(?m)^ed 00400304 ([01])\r?$", generated_probe_data)
    check(modes == [str(expected_mode).encode()] and expected_mode in (0, 1), "generated probe mode initialization mismatch")
    if markers["start"] is not None:
        check(markers["start"]["mode"] == expected_mode, "observed start mode mismatch")
    check(summary.get("HiddenDesktop") is True and summary.get("AllowVisibleDesktop") is False and summary.get("LaunchMode") == "hidden-desktop", "hidden launch evidence missing/mismatched")
    check(summary.get("UseDdrawProxy") is True and str(summary.get("ProxyPresentSetting")) == "0" and is_sha(summary.get("DdrawProxySha256")), "non-presenting proxy identity missing")
    check(summary.get("LoadSlot") == 0 and type(summary.get("LoadSlot")) is int, "expected load-slot0")
    check(summary.get("ForceVisibleEdges") is False and summary.get("PostOwnerForceVisibleSeven") is False and summary.get("SkipMapValidation") is False, "unsupported forced visibility/skipped map gates")
    check(summary.get("Av") is False and summary.get("AppRequestQuit") is False and summary.get("HostDumpError") is None, "outer runtime failure or missing runtime result")
    check(byte_report.get("stage") == expected_stage and byte_report.get("resolution") == "800x600" and same_sha(byte_report.get("exe_sha256"), expected_candidate_sha256), "byte report stage/resolution/candidate mismatch")
    check(same_sha(byte_report.get("expected_base_sha256"), ORIGINAL_SHA), "byte report original SHA mismatch")
    patch_count = PATCH_COUNTS.get(expected_stage)
    rows = byte_report.get("patches", [])
    counts = byte_report.get("status_counts", {})
    check(byte_report.get("patch_count") == patch_count and len(rows) == patch_count and counts.get("patched") == patch_count and all(v == 0 for k, v in counts.items() if k != "patched"), "byte report count/status mismatch")
    check(all(r.get("status") == "patched" and r.get("actual") == r.get("new") and r.get("actual") != r.get("old") for r in rows), "byte report contains unmatched patch bytes")
    offsets = [r.get("offset") for r in rows]
    check(all(type(offset) is int and offset >= 0 for offset in offsets) and len(set(offsets)) == len(offsets), "byte report patch offsets missing/duplicated")
    gate = byte_report.get("current_hd_map_gate", {})
    check(gate.get("passed") is True and gate.get("failures") == [], "HD-map byte gate missing/failing")

    cleanup = cleanup or {}
    check(cleanup.get("schema") == CLEANUP_SCHEMA, "explicit cleanup observation missing/schema mismatch")
    for key, expected in (("stage", expected_stage), ("resolution", "800x600")):
        check(cleanup.get(key) == expected, f"cleanup {key} mismatch")
    for key, expected in (("candidate_sha256", expected_candidate_sha256), ("generated_probe_sha256", probe_sha), ("log_sha256", log_sha)):
        check(same_sha(cleanup.get(key), expected), f"cleanup {key} mismatch")
    check(same_path(cleanup.get("candidate_path"), summary.get("CandidatePath")) and same_path(cleanup.get("run_dir"), summary.get("RunDir")), "cleanup run/candidate path mismatch")
    check(cleanup.get("game_stopped") is True and cleanup.get("cdb_stopped") is True and cleanup.get("errors") == [], "cleanup incomplete or failed")
    check(all(type(cleanup.get(k)) is int and cleanup[k] > 0 for k in ("game_pid", "cdb_pid")) and cleanup.get("game_pid") != cleanup.get("cdb_pid"), "cleanup process identities missing/invalid")
    logged_game_pids = {int(pid, 16) for pid in re.findall(r"(?m)^\(([0-9a-fA-F]+)\.[0-9a-fA-F]+\):", log_text)}
    check(logged_game_pids == {cleanup.get("game_pid")}, "cleanup game PID does not match debugger event identity")
    try:
        check(datetime.fromisoformat(cleanup["observed_at"].replace("Z", "+00:00")).tzinfo is not None, "cleanup timestamp has no timezone")
    except (KeyError, TypeError, ValueError, AttributeError):
        check(False, "cleanup timestamp missing/invalid")

    observed = markers["observed_classification"]
    if observed == "incomplete" and summary.get("TimedOut") is True:
        observed = "unknown_timeout"
    day_markers = observed in ("full_day_returned", "full_day_returned_with_forced_ack", "full_day_returned_with_controlled_input_queries")
    if day_markers:
        check(summary.get("Passed") is True and summary.get("Error") is None and summary.get("TimedOut") is False, "outer surface run did not pass")
        check(summary.get("SurfaceGeometryMatched") is True, "outer surface dimensions unverified")
        outer_surface = summary.get("Surface") or {}
        for key, value in markers["surface"].items():
            if key in ("Base", "Surface"):
                try:
                    check(pointer(outer_surface.get(key)) == pointer(value), f"outer surface {key} mismatch")
                except ValueError:
                    check(False, f"outer surface {key} missing")
            else:
                check(type(outer_surface.get(key)) is int and outer_surface.get(key) == value, f"outer surface {key} mismatch")
        check(raw_data is not None and len(raw_data) == summary.get("RawBytes") == 480000, "actual raw surface missing/size mismatch")
        check(raw_data is not None and same_sha(cleanup.get("surface_sha256"), sha(raw_data)), "raw surface digest missing/mismatched in cleanup receipt")
        check(isinstance(summary.get("RawPath"), str) and same_path(ntpath.dirname(summary["RawPath"]), summary.get("RunDir")), "raw surface path is outside the recorded run")
        check(summary.get("HostDumpedMemory") is True and summary.get("DumpMethod") == "host-readprocessmemory", "host surface read evidence missing")
    else:
        failures.append(f"no complete bounded day proof: {observed}")
    return {"schema": SCHEMA, "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": not failures and day_markers, "day_transition_passed": not failures and day_markers,
            "observed_classification": observed, "failures": failures,
            "environment": "hidden_cdb_host", "entry_mechanism": "cdb_breakpoint_forced_loader_entry",
            "turn_mechanism": "forced_native_nextplayer", "requested_mode": expected_mode,
            "forced_banner_ack_count": markers["forced_ack_count"],
            "forced_release_counts": markers["forced_release_counts"],
            "controlled_input_query_overrides": bool(markers["forced_ack_count"] or any(markers["forced_release_counts"].values())),
            "native_day_increment_observed": markers["native_day_increment_observed"],
            "native_day_return_observed": markers["native_day_return_observed"],
            "input_responsiveness": "not_applicable_hidden", "manual_input_proof": False,
            "promotion_evidence": False, "stage": expected_stage, "resolution": "800x600",
            "candidate_sha256": expected_candidate_sha256, "generated_probe_sha256": probe_sha,
            "log_sha256": log_sha, "surface_sha256": sha(raw_data) if raw_data is not None else None,
            "cleanup": cleanup, "markers": markers,
            "limits": "Bounded forced native calls with any controlled input-query overrides counted explicitly; no ordinary/manual end-turn, sustained continuity, extended-register preservation, visible composition or promotion proof."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--byte-report", required=True, type=Path)
    parser.add_argument("--cleanup", type=Path)
    parser.add_argument("--expected-stage", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--expected-generated-probe-sha256", required=True)
    parser.add_argument("--expected-mode", type=int, choices=(0, 1), default=0)
    parser.add_argument("--json-out", type=Path, help="Optional explicit output; default is stdout only.")
    args = parser.parse_args()
    try:
        summary = json.loads(args.summary.read_text(encoding="utf-8-sig"))
        probe = Path(summary["GeneratedProbe"])
        log = Path(summary["Log"])
        raw = Path(summary["RawPath"]) if summary.get("RawPath") else None
        result = evaluate(summary, log.read_bytes(), probe.read_bytes(),
                          json.loads(args.byte_report.read_text(encoding="utf-8-sig")),
                          json.loads(args.cleanup.read_text(encoding="utf-8-sig")) if args.cleanup else None,
                          expected_stage=args.expected_stage,
                          expected_candidate_sha256=args.expected_candidate_sha256,
                          expected_generated_probe_sha256=args.expected_generated_probe_sha256,
                          expected_mode=args.expected_mode, raw_data=raw.read_bytes() if raw and raw.exists() else None)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"schema": SCHEMA, "passed": False, "day_transition_passed": False,
                  "observed_classification": "unreadable_evidence", "failures": [str(exc)]}
    output = json.dumps(result, indent=2) + "\n"
    if args.json_out:
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Offline initial-map-paint trace verifier; no runtime or artifact mutation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from partial_tile_trace_probe import validate_event_integrity


STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
         "presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-validation")
FRAMED_STAGE = STAGE.removesuffix("-validation") + "-framed-validation"
FULL_STATUS_TO_READY_STACK_BYTES = 88
# framed_full_paint adds a preserving outer frame (60 bytes) around418700.
# initial_map_paint exposes this as initial_contract.stack.full_status_plus_to_ready.
FRAMED_FULL_STATUS_TO_READY_STACK_BYTES = 148
CLOSE_EIP = 0x406FA0
H = r"[0-9a-fA-F]{1,8}"
I = r"-?[0-9]{1,10}"
IDENTITY = rf"tid=(?P<tid>{H}) esp=(?P<esp>{H})"
WORLD = rf"world=\((?P<wx>{I}),(?P<wy>{I})\)"
INPUT = (rf"{IDENTITY} {WORLD} caller=(?P<caller>{H}) gd=(?P<gd>{H}) "
         rf"map=\((?P<mw>{I}),(?P<mh>{I})\) scroll=\((?P<sx>{I}),(?P<sy>{I})\) vtable=(?P<vtable>{H})")
PATTERNS = {
    "PTILE_INITIAL_ADMISSION": re.compile(rf"PTILE_INITIAL_ADMISSION status=(?P<status>{I}) {IDENTITY}"),
    "PTILE_INITIAL_RETURN": re.compile(rf"PTILE_INITIAL_RETURN {IDENTITY} result=(?P<result>{H})"),
    "PTILE_MAP_READY": re.compile(rf"PTILE_MAP_READY owner=(?P<owner>{H}) size=\((?P<width>[0-9]{{1,4}}),(?P<height>[0-9]{{1,4}})\)"),
    "PTILE_STATUS": re.compile(rf"PTILE_STATUS hook=(?P<hook>full_converge|full_present|incremental) status=(?P<status>{I}) {IDENTITY} owner=(?P<owner>{H}) tile=(?P<tile>{H}) post=(?P<post>{H}) lower=(?P<lower>{H}) player=(?P<player>{I})"),
    "PTILE_INCREMENTAL_INPUT": re.compile("PTILE_INCREMENTAL_INPUT " + INPUT),
    "PTILE_NATIVE_NOOP_EXIT": re.compile("PTILE_NATIVE_NOOP_EXIT " + INPUT),
    "PTILE_COMPOSITION_GUARD": re.compile(rf"PTILE_COMPOSITION_GUARD {IDENTITY} status=(?P<status>{I}) {WORLD} cell=\((?P<col>{I}),(?P<row>{I})\) present=(?P<present>{I}) caller=(?P<caller>{H})"),
}
HEX_FIELDS = {"tid", "esp", "caller", "gd", "vtable", "owner", "tile", "post", "lower", "result"}
LIMITS = [
    "Initial-paint native sequence and logged auxiliary call integrity only; generic partial-tile status and loaded-byte gates remain separately required.",
    "No screenshot, final visible composition, manual input, endurance or promotion proof is established.",
    "Native paint-return EAX is recorded without interpreting it as success.",
    "Trace closure checks native site, thread, ordering and an aligned observed stack; no closure-to-initial stack delta is claimed.",
    "The four-update stop and host pause are harness source contracts, not an update count encoded in the close marker.",
]


def evaluate_trace(log: str, probe: str, *, resolution: str, candidate_sha256: str, stage: str) -> dict:
    integrity = validate_event_integrity(log, probe, reset_bp=76)
    failures = list(integrity["errors"])
    events = integrity["events"]
    initial = {}
    pending_full, pending_incremental = {}, {}
    full_pairs = []

    def fail(line: int, message: str) -> None:
        failures.append(f"line {line}: {message}")

    dimensions = re.fullmatch(r"([1-9][0-9]{1,3})x([1-9][0-9]{1,3})", resolution)
    width, height = map(int, dimensions.groups()) if dimensions else (0, 0)
    if not 96 <= width <= 8192 or not 80 <= height <= 8192:
        failures.append("resolution must be canonical WxH within supported geometry bounds")
    framed = stage == FRAMED_STAGE
    if stage not in (STAGE, FRAMED_STAGE):
        failures.append("stage must be an exact supported combinedui-partialtiles-initialpaint validation stage")
    if framed and not (640 <= width <= 8192 and 480 <= height <= 8192 and width % 2 == height % 2 == 0):
        failures.append("framed resolution requires even 640..8192 by 480..8192 physical dimensions")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", candidate_sha256):
        failures.append("candidate SHA-256 must be exactly 64 hexadecimal digits")
    contract = f"PTILE_CONTRACT_PASS stage={stage} resolution={resolution} candidate_sha256={candidate_sha256.lower()}"
    scope = "PTILE_SCOPE guarded_map_only manual_input_proof=false promotion_ready=false"
    for text, name in ((contract, "loaded contract"), (scope, "non-promoting scope")):
        rows = [row for row in integrity["raw_records"] if row["marker"] == text.split()[0]]
        if len(rows) != 1 or rows[0]["text"] != text or not events or rows[0]["line"] >= events[0]["line"]:
            failures.append(f"missing, repeated, mismatched or late {name}")
        if probe.splitlines().count(".echo " + text) != 1:
            failures.append(f"supplied probe lacks its exact {name}")
    terrain_width, terrain_height = width - (64 if framed else 32), height - (32 if framed else 16)
    floor_cols, floor_rows = terrain_width // 64, terrain_height // 64
    ceil_cols, ceil_rows = (terrain_width + 63) // 64, (terrain_height + 63) // 64
    full_status_stack_bytes = (FRAMED_FULL_STATUS_TO_READY_STACK_BYTES if framed
                               else FULL_STATUS_TO_READY_STACK_BYTES)

    for event in events:
        line, bp = event["line"], event["bp"]
        if event["esp"] % 4:
            fail(line, "unaligned event stack")
        if bp == 76:
            if initial:
                fail(line, "initial admission repeated")
            initial.setdefault("admission", event)
        if bp == 73:
            if "admission" not in initial or "ready" in initial or event["seq"] != 2:
                fail(line, "map readiness must follow the single initial admission")
            initial.setdefault("ready", event)
        if bp not in (76, 73) and "ready" not in initial:
            fail(line, "native observation precedes initial map readiness")
        if bp in (73, 77) and "admission" in initial:
            if (event["tid"], event["esp"]) != (initial["admission"]["tid"], initial["admission"]["esp"]):
                fail(line, "initial admission/readiness/return thread or stack differs")

        for record in event["records"]:
            marker = record["marker"]
            match = PATTERNS.get(marker)
            match = match.fullmatch(record["text"]) if match else None
            if not match:
                fail(record["line"], "malformed or unsupported native semantic record")
                continue
            values = {key: value if key == "hook" else int(value, 16 if key in HEX_FIELDS else 10)
                      for key, value in match.groupdict().items()}
            if any(not -0x80000000 <= value <= 0x7FFFFFFF for key, value in values.items()
                   if key not in HEX_FIELDS and key != "hook"):
                fail(record["line"], "native signed value outside x86 range")
            if marker == "PTILE_INITIAL_ADMISSION":
                if values["status"] != 1:
                    fail(line, "initial admission did not return exact status 1")
                continue
            if marker == "PTILE_MAP_READY":
                if (values["owner"], values["width"], values["height"]) != (0x40AD40, width, height):
                    fail(line, "map readiness owner or dimensions mismatch")
                continue
            if marker == "PTILE_INITIAL_RETURN":
                if "return" in initial or "pair" not in initial:
                    fail(line, "native paint return lacks one complete initial pair or is repeated")
                if any(key[0] == event["tid"] for key in (*pending_full, *pending_incremental)):
                    fail(line, "native paint returned with an unfinished invocation")
                initial.setdefault("return", event)
                initial["return_eax"] = values["result"]
                continue

            delta = 120 if marker == "PTILE_COMPOSITION_GUARD" else 28 if marker == "PTILE_NATIVE_NOOP_EXIT" else 36
            native_sp = values["esp"] + delta
            if native_sp > 0xFFFFFFFF:
                fail(line, "normalized native stack overflows x86")
            key = values["tid"], native_sp
            for active_key, call in pending_incremental.items():
                guard = call["guard"]
                outside = not (0 <= guard["col"] < ceil_cols and 0 <= guard["row"] < ceil_rows)
                if outside and active_key[0] == key[0] and active_key != key:
                    fail(line, "offscreen no-op interrupted by another invocation")
            if marker == "PTILE_COMPOSITION_GUARD":
                if values["status"] != 1 or values["present"] != 1 or values["caller"] == 0:
                    fail(line, "composition guard did not approve the actual incremental call")
                if key in pending_incremental:
                    fail(line, "repeated incremental guard for the same invocation")
                else:
                    pending_incremental[key] = {"phase": "guard", "guard": values}
                continue
            if marker in ("PTILE_INCREMENTAL_INPUT", "PTILE_NATIVE_NOOP_EXIT"):
                call = pending_incremental.get(key)
                expected_phase = "guard" if marker == "PTILE_INCREMENTAL_INPUT" else "exit"
                if not call or call["phase"] != expected_phase:
                    fail(line, "incremental input/exit lacks a fresh matching guard and phase")
                    continue
                if marker == "PTILE_NATIVE_NOOP_EXIT":
                    if any(values[field] != call["input"][field] for field in ("caller", "wx", "wy", "gd", "mw", "mh", "sx", "sy", "vtable")):
                        fail(line, "native no-op exit changed its input/context")
                    del pending_incremental[key]
                    continue
                guard = call["guard"]
                if any(values[field] != guard[field] for field in ("caller", "wx", "wy")):
                    fail(line, "incremental input differs from its guarded call")
                if not (values["gd"] and values["vtable"] and 1 <= values["mw"] <= 100 and 1 <= values["mh"] <= 100
                        and 0 <= values["sx"] <= max(0, values["mw"] - floor_cols)
                        and 0 <= values["sy"] <= max(0, values["mh"] - floor_rows)):
                    fail(line, "invalid incremental map/scroll context")
                if (guard["col"], guard["row"]) != (values["wx"] - values["sx"], values["wy"] - values["sy"]):
                    fail(line, "guarded cell differs from world/scroll coordinates")
                call.update(phase="input", input=values)
                continue
            context = tuple(values[field] for field in ("owner", "tile", "post", "lower", "player"))
            if not (values["owner"] == 0x40AD40 and values["tile"] in (0, 0x425120, 0x429EC0)
                    and values["post"] == values["lower"] == values["player"] == 0):
                fail(line, "unsupported ordinary-map composition context")
            if values["hook"] == "incremental":
                call = pending_incremental.get(key)
                if not call or call["phase"] != "input":
                    fail(line, "incremental status lacks a fresh guard/input pair")
                    continue
                guard, data = call["guard"], call["input"]
                visible = 0 <= guard["col"] < ceil_cols and 0 <= guard["row"] < ceil_rows
                in_world = 0 <= data["wx"] < data["mw"] and 0 <= data["wy"] < data["mh"]
                if values["status"] == 0:
                    if visible or not in_world or values["tile"] or data["vtable"] != 0x50EE24:
                        fail(line, "zero status is not a native offscreen no-op")
                    call["phase"] = "exit"
                else:
                    if not visible or values["status"] not in (1, 2) or (values["status"] == 1) != in_world:
                        fail(line, "incremental draw/clear status contradicts actual bounds")
                    del pending_incremental[key]
                continue
            if values["status"] != 1:
                fail(line, "full paint status must be exactly 1")
            if "return" not in initial:
                admission = initial.get("admission", {})
                if values["tile"] != 0:
                    fail(line, "initial full paint changed the admission's zero tile callback")
                if event["tid"] != admission.get("tid") or event["esp"] + full_status_stack_bytes != admission.get("esp"):
                    fail(line, "initial full paint does not match admission thread/normalized stack")
                if "pair" in initial:
                    fail(line, "additional full paint before the single initial native return")
            if values["hook"] == "full_converge":
                if key in pending_full:
                    fail(line, "duplicate convergence before matching presentation")
                else:
                    pending_full[key] = (context, event)
            else:
                pending = pending_full.pop(key, None)
                if not pending or pending[0] != context:
                    fail(line, "presentation lacks matching thread/stack/context convergence")
                else:
                    pair = {"converge_line": pending[1]["line"], "present_line": event["line"], "tid": event["tid"], "esp": event["esp"]}
                    full_pairs.append(pair)
                    if "return" not in initial:
                        initial.setdefault("pair", pair)

    if pending_incremental or pending_full:
        failures.append("trace ends with an unfinished native call or full-paint pair")
    if any(name not in initial for name in ("admission", "ready", "pair", "return")):
        failures.append("initial admission/readiness/full-paint/return chain is incomplete")
    boundaries = integrity["boundary_records"]
    if len(boundaries) != 1:
        failures.append("one explicit trace closure is required")
    else:
        close = boundaries[0]
        if (close["eip"] != CLOSE_EIP or close["tid"] != initial.get("admission", {}).get("tid")
                or not close["esp"] or close["esp"] % 4):
            fail(close["line"], "closure native site/thread/aligned stack mismatch")
        if "return" not in initial or close["line"] <= initial["return"]["line"]:
            fail(close["line"], "trace closes before native initial paint returns")
        if any("SURFDUMP_HOST_READY" in text and number < close["line"] for number, text in enumerate(log.splitlines(), 1)):
            fail(close["line"], "host-ready marker preceded trace closure")
    return {"passed": not failures, "status": "initial_paint_observed" if not failures else "initial_paint_trace_failed",
            "stage": stage, "resolution": resolution, "candidate_sha256": candidate_sha256.lower(),
            "trace_contract": {"profile": "native_four_border_tiles_v1" if framed else "legacy_expanded_map",
                               "terrain_inclusive": [32, 16, terrain_width + 31, terrain_height + 15],
                               "full_tiles": [floor_cols, floor_rows], "ceil_tiles": [ceil_cols, ceil_rows],
                               "full_status_to_ready_stack_bytes": full_status_stack_bytes},
            "initial_sequence": initial, "full_pairs": full_pairs, "event_integrity": integrity,
            "manual_input_proof": False, "promotion_ready": False, "limits": LIMITS, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    try:
        log_bytes, probe_bytes = args.log.read_bytes(), args.probe.read_bytes()
        report = evaluate_trace(log_bytes.decode("utf-8-sig"), probe_bytes.decode("ascii"),
                                resolution=args.resolution, candidate_sha256=args.candidate_sha256, stage=args.stage)
        report["sources"] = {"log": {"path": str(args.log), "sha256": hashlib.sha256(log_bytes).hexdigest()},
                             "probe": {"path": str(args.probe), "sha256": hashlib.sha256(probe_bytes).hexdigest()}}
    except (OSError, UnicodeError, ValueError) as exc:
        report = {"passed": False, "status": "initial_paint_trace_unreadable", "failures": [str(exc)],
                  "manual_input_proof": False, "promotion_ready": False, "limits": LIMITS}
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Guard the natural right-bottom action-route explanation.

This is a repo-only parser for the hidden-desktop castle command-99 owner-loop
probe. It records why the right-bottom owner/action renderer is absent in the
current save: the action descriptor exists, but the owner flag keeps it parked
off-screen, so the natural route cannot enter the action draw cluster.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RUN = Path("captures/archive/cdb-surface-dump-20260712-150434")
DEFAULT_JSON = Path("captures/current/right-bottom-natural-route-guard-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-natural-route-guard-current.md")
EXPECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch-rightbottomaction-nativecenter"
)
EXPECTED_PROBE = "probes/cdb/castle/clash95_castle_cmd99_owner_action_descriptor_extra.cdb"
EXPECTED_ACTION_CALLBACK = "004338e0"
EXPECTED_OWNER_LOOP_DESCRIPTORS = {
    "d0": {"x": 39, "y": 426, "callback": "004338c0"},
    "d1": {"x": 1000, "y": 426, "callback": EXPECTED_ACTION_CALLBACK},
    "d2": {"x": 1000, "y": 426, "callback": "00433a40"},
}

MARKERS = (
    "NOWNER_FORCE_MAP_CASTLE_CLICK",
    "NOWNER_BUILDING_TILE",
    "NOWNER_CASTLE_OVERVIEW_ENTRY",
    "NOWNER_CASTLE_CMD99_GATE",
    "NOWNER_CASTLE_CALLBACK",
    "NOWNER_433C20_ENTRY",
    "NOWNER_OWNER_FLAG_TEST",
    "NOWNER_WRITE_532154",
    "NOWNER_OWNER_SCREEN_DESC_DRAW",
    "NOWNER_FORCE_OWNER_DESC_CLICK",
    "NOWNER_HITTEST_ENTRY",
    "NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY",
    "NOWNER_4338E0_ENTRY",
    "NOWNER_4338E0_OWNER_FLAG_BLOCKED",
    "NOWNER_ACTION_CALL_WRAPPER",
    "NOWNER_OWNER_435BC0_ENTRY",
    "NOWNER_WRAPPER_COPYBACK_DONE",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
    "AV_SURFDUMP",
)

ACTION_ROUTE_MARKERS = (
    "NOWNER_4338E0_ENTRY",
    "NOWNER_ACTION_CALL_WRAPPER",
    "NOWNER_OWNER_435BC0_ENTRY",
    "NOWNER_WRAPPER_COPYBACK_DONE",
)

OWNER_ENTRY_RE = re.compile(r"NOWNER_433C20_ENTRY\b.*?\bowner_flag=(0x[0-9a-fA-F]+)")
FLAG_TEST_RE = re.compile(
    r"NOWNER_OWNER_FLAG_TEST\b.*?\bowner_flag=(0x[0-9a-fA-F]+)\b.*?"
    r"\bbit2=(?P<bit2>\d+)\b.*?\bbit1=(?P<bit1>\d+)\b.*?\bbit8=(?P<bit8>\d+)"
)
DESC_DRAW_RE = re.compile(
    r"NOWNER_OWNER_SCREEN_DESC_DRAW\b.*?"
    r"d0=\((?P<d0x>-?\d+),(?P<d0y>-?\d+) cb=(?P<d0cb>[0-9a-fA-F]+)\)\s+"
    r"d1=\((?P<d1x>-?\d+),(?P<d1y>-?\d+) cb=(?P<d1cb>[0-9a-fA-F]+)\)\s+"
    r"d2=\((?P<d2x>-?\d+),(?P<d2y>-?\d+) cb=(?P<d2cb>[0-9a-fA-F]+)\)"
)
DESC_RESULT_RE = re.compile(
    r"NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY\b.*?\bresult=(?P<result>-?\d+)\b.*?"
    r"\bowner=(?P<owner>[0-9a-fA-F]+)\b.*?\bowner_flag=(?P<owner_flag>0x[0-9a-fA-F]+)\b.*?"
    r"\bsize=\((?P<width>\d+),(?P<height>\d+)\)"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def marker_counts(text: str) -> dict[str, int]:
    return {marker: text.count(marker) for marker in MARKERS}


def probe_template_matches(value: object, expected_rel: str) -> bool:
    normalized = str(value or "").replace("\\", "/").lower()
    expected = expected_rel.replace("\\", "/").lower()
    basename = expected.rsplit("/", 1)[-1]
    return expected in normalized or normalized.endswith("/" + basename) or normalized.endswith(basename)


def _hex_lower(value: str | None) -> str | None:
    return value.lower() if value else None


def _int_group(match: re.Match[str], name: str) -> int:
    return int(match.group(name))


def parse_log(log_path: Path) -> dict[str, Any]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    counts = marker_counts(text)

    owner_entry = OWNER_ENTRY_RE.search(text)
    flag_test = FLAG_TEST_RE.search(text)
    desc_draw = DESC_DRAW_RE.search(text)
    desc_result = DESC_RESULT_RE.search(text)

    descriptors: dict[str, dict[str, Any]] = {}
    if desc_draw:
        for name in ("d0", "d1", "d2"):
            descriptors[name] = {
                "x": _int_group(desc_draw, f"{name}x"),
                "y": _int_group(desc_draw, f"{name}y"),
                "callback": _hex_lower(desc_draw.group(f"{name}cb")),
            }

    action_descriptor = next(
        (
            {"slot": slot, **row}
            for slot, row in descriptors.items()
            if row.get("callback") == EXPECTED_ACTION_CALLBACK
        ),
        None,
    )
    action_route_count = sum(counts[marker] for marker in ACTION_ROUTE_MARKERS)
    desc_result_info: dict[str, Any] = {}
    if desc_result:
        desc_result_info = {
            "result": _int_group(desc_result, "result"),
            "owner": _hex_lower(desc_result.group("owner")),
            "owner_flag": _hex_lower(desc_result.group("owner_flag")),
            "surface": [_int_group(desc_result, "width"), _int_group(desc_result, "height")],
        }

    return {
        "log": str(log_path),
        "marker_counts": counts,
        "owner_entry_flag": _hex_lower(owner_entry.group(1)) if owner_entry else None,
        "flag_test": {
            "owner_flag": _hex_lower(flag_test.group(1)) if flag_test else None,
            "bit2": _int_group(flag_test, "bit2") if flag_test else None,
            "bit1": _int_group(flag_test, "bit1") if flag_test else None,
            "bit8": _int_group(flag_test, "bit8") if flag_test else None,
        },
        "descriptors": descriptors,
        "action_descriptor": action_descriptor,
        "descriptor_result": desc_result_info,
        "action_route_count": action_route_count,
    }


def build_report(run: Path) -> dict[str, Any]:
    summary_path = run / "summary.json"
    log_path = run / "cdb-surface-dump.log"
    failures: list[str] = []
    summary: dict[str, Any] = {}
    parsed: dict[str, Any] = {}

    if not summary_path.exists():
        failures.append(f"missing summary: {summary_path}")
    else:
        summary = load_json(summary_path)
    if not log_path.exists():
        failures.append(f"missing log: {log_path}")
    else:
        parsed = parse_log(log_path)

    counts = parsed.get("marker_counts") or {}
    action_descriptor = parsed.get("action_descriptor") or {}
    desc_result = parsed.get("descriptor_result") or {}
    flag_test = parsed.get("flag_test") or {}

    if summary:
        if summary.get("Passed") is not True:
            failures.append("natural route run did not pass")
        if summary.get("HiddenDesktop") is not True:
            failures.append("natural route run was not hidden-desktop")
        if summary.get("UseDdrawProxy") is not True:
            failures.append("natural route run did not use the DirectDraw proxy")
        if summary.get("Stage") != EXPECTED_STAGE:
            failures.append(f"natural route stage mismatch: {summary.get('Stage')}")
        if not probe_template_matches(summary.get("ExtraProbeTemplate"), EXPECTED_PROBE):
            failures.append("natural route run used an unexpected extra probe")

    for marker in (
        "NOWNER_CASTLE_CMD99_GATE",
        "NOWNER_CASTLE_CALLBACK",
        "NOWNER_433C20_ENTRY",
        "NOWNER_OWNER_FLAG_TEST",
        "NOWNER_OWNER_SCREEN_DESC_DRAW",
        "NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY",
        "SURFDUMP_READY",
        "SURFDUMP_HOST_READY",
    ):
        if int(counts.get(marker) or 0) <= 0:
            failures.append(f"missing natural-route marker: {marker}")

    if int(counts.get("AV_SURFDUMP") or 0):
        failures.append("natural route log contains AV rows")
    if int(parsed.get("action_route_count") or 0) != 0:
        failures.append("natural route unexpectedly entered the owner/action renderer")
    if parsed.get("owner_entry_flag") != "0x00":
        failures.append(f"owner entry flag was {parsed.get('owner_entry_flag')}, expected 0x00")
    if flag_test.get("owner_flag") != "0x00":
        failures.append(f"owner flag-test value was {flag_test.get('owner_flag')}, expected 0x00")
    if any(int(flag_test.get(bit) or 0) for bit in ("bit2", "bit1", "bit8")):
        failures.append(f"owner flag bits were {flag_test}, expected all zero")
    for slot, expected in EXPECTED_OWNER_LOOP_DESCRIPTORS.items():
        actual = (parsed.get("descriptors") or {}).get(slot)
        if actual != expected:
            failures.append(f"owner-loop descriptor {slot} was {actual}, expected {expected}")
    if action_descriptor.get("callback") != EXPECTED_ACTION_CALLBACK:
        failures.append("owner-loop action descriptor callback 004338E0 was not found")
    if action_descriptor.get("x") != EXPECTED_OWNER_LOOP_DESCRIPTORS["d1"]["x"]:
        failures.append(
            f"action descriptor x was {action_descriptor.get('x')}, "
            f"expected {EXPECTED_OWNER_LOOP_DESCRIPTORS['d1']['x']}"
        )
    if action_descriptor.get("y") != EXPECTED_OWNER_LOOP_DESCRIPTORS["d1"]["y"]:
        failures.append(
            f"action descriptor y was {action_descriptor.get('y')}, "
            f"expected {EXPECTED_OWNER_LOOP_DESCRIPTORS['d1']['y']}"
        )
    if desc_result.get("result") != 0:
        failures.append(f"owner descriptor result was {desc_result.get('result')}, expected 0")
    if desc_result.get("owner_flag") != "0x00":
        failures.append(f"owner descriptor result flag was {desc_result.get('owner_flag')}, expected 0x00")

    state_gated = not failures
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": "repo-only; reads existing hidden-desktop CDB artifacts and does not launch Clash95, CDB, wrappers, or visible windows",
        "guard_policy": (
            "natural right-bottom action routing must be classified as save-state gated only when "
            "command 99 reaches the owner loop, the exact 00433C20 owner-loop descriptor model is "
            "present, the 004338E0 action descriptor is parked at (1000,426), owner flag bits are "
            "zero, no owner/action renderer rows fire, and the run has no AV rows"
        ),
        "run": str(run),
        "summary_json": str(summary_path),
        "log": str(log_path),
        "screenshot": summary.get("PngPath"),
        "stage": summary.get("Stage"),
        "candidate_sha256": summary.get("CandidateSha256"),
        "state_gated_by_owner_flag": state_gated,
        "expected_action_callback": EXPECTED_ACTION_CALLBACK,
        "expected_owner_loop_descriptors": EXPECTED_OWNER_LOOP_DESCRIPTORS,
        "parsed": parsed,
        "summary": {
            "hidden_desktop": summary.get("HiddenDesktop"),
            "stage": summary.get("Stage"),
            "candidate_sha256": summary.get("CandidateSha256"),
            "owner_entry_flag": parsed.get("owner_entry_flag"),
            "owner_flag_test": flag_test,
            "action_descriptor": action_descriptor,
            "descriptor_result": desc_result,
            "action_route_count": parsed.get("action_route_count"),
            "state_gated_by_owner_flag": state_gated,
            "av_count": counts.get("AV_SURFDUMP"),
        },
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    action_desc = summary.get("action_descriptor") or {}
    desc_result = summary.get("descriptor_result") or {}
    lines = [
        "# Right-Bottom Natural Route Guard",
        "",
        f"- Status: {'PASS' if report['passed'] else 'FAIL'}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Run: `{report['run']}`",
        f"- Stage: `{report.get('stage')}`",
        f"- Candidate SHA-256: `{report.get('candidate_sha256')}`",
        f"- State gated by owner flag: `{report['state_gated_by_owner_flag']}`",
        f"- Expected owner-loop descriptors: `{report.get('expected_owner_loop_descriptors')}`",
        f"- Owner entry flag: `{summary.get('owner_entry_flag')}`",
        f"- Owner flag test: `{summary.get('owner_flag_test')}`",
        f"- Action descriptor: slot `{action_desc.get('slot')}`, x/y `({action_desc.get('x')},{action_desc.get('y')})`, callback `{action_desc.get('callback')}`",
        f"- Descriptor result: `{desc_result}`",
        f"- Owner/action renderer rows: `{summary.get('action_route_count')}`",
        f"- AV rows: `{summary.get('av_count')}`",
    ]
    if report.get("screenshot"):
        lines.extend(["", f"![surface dump]({report['screenshot']})"])
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.run)
    print(f"overall: {'PASS' if report['passed'] else 'FAIL'}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"state-gated-by-owner-flag: {report['state_gated_by_owner_flag']}")
    print(f"action-route-count: {report['summary'].get('action_route_count')}")
    print(f"action-descriptor: {report['summary'].get('action_descriptor')}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, report)
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

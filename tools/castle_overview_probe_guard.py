#!/usr/bin/env python3
"""Guard the focused full castle overview hitbox probe.

This is a repo-only inspection guard. It verifies that the focused CDB probe
still covers the proven descriptor-loop callsites, that the known crashing
overview descriptor-input wrapper marker has not returned, and that the current
focused hitbox log still proves the displayed-coordinate wrapper/gate without
an AV.
It does not launch Clash95, CDB, wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import castle_overview_hitbox_summary


DEFAULT_PROBE = Path("probes/cdb/castle/clash95_castle_overview_hitbox_extra.cdb")
DEFAULT_SUMMARY_PARSER = Path("tools/castle_overview_hitbox_summary.py")
DEFAULT_PATCHER = Path("patch_clash95_hd.py")
DEFAULT_FOCUSED_RUN = Path("captures/cdb-surface-dump-20260514-130015")
DEFAULT_JSON = Path("captures/current/castle-overview-probe-guard-current.json")
DEFAULT_MD = Path("captures/current/castle-overview-probe-guard-current.md")
RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
GUARD_POLICY = (
    "focused overview hitbox proof must keep the descriptor-loop breakpoints, "
    "forbid the old crashing overview descriptor-input wrapper marker, and "
    "continue to prove the displayed-coordinate wrapper and click gate with no AV"
)

REQUIRED_BREAKPOINTS = {
    "00422544": "raw hit-test result after the overview descriptor hitmap lookup",
    "0042257E": "descriptor command/callback install row",
    "00422590": "stock click gate result row",
    "0042262C": "descriptor callback-call sentinel",
}

REQUIRED_PROBE_MARKERS = {
    "CASTLEOV_HITBOX_DISPLAYED_HITTEST_BEGIN": "displayed coordinates are installed before hit-test",
    "CASTLEOV_HITBOX_DISPLAYED_RESULT": "displayed-coordinate raw hit result is logged",
    "CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK": "displayed coordinates reached the target through the binary input wrapper",
    "CASTLEOV_HITBOX_DESCRIPTOR_INSTALL": "descriptor command/callback is logged",
    "CASTLEOV_HITBOX_CLICK_GATE": "stock click gate result is logged",
    "CASTLEOV_HITBOX_CLICK_GATE_OK": "target click gate success is logged",
    "CASTLEOV_HITBOX_CALLBACK_SUPPRESSED": "target callback is suppressed after proof",
    "CASTLEOV_HITBOX_CALLBACK_CALL": "unexpected callback entry remains observable",
    "CASTLEOV_HITBOX_SURFDUMP_READY": "surface dump ready row is emitted",
}

FORBIDDEN_MARKERS = (
    "CASTLECAT_OVERVIEW_DESC_INPUT_WRAPPER_ENTRY",
    "OVERVIEW_DESC_INPUT_WRAPPER_ENTRY",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def breakpoint_present(text: str, address: str) -> bool:
    return bool(re.search(rf"\bbp(?:\s+/1)?\s+{re.escape(address)}\b", text, re.IGNORECASE))


def check_probe_script(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    if not path.exists():
        return {
            "passed": False,
            "path": str(path),
            "failures": [f"missing probe script: {path}"],
        }

    text = read_text(path)
    breakpoints = {
        address: {
            "present": breakpoint_present(text, address),
            "purpose": purpose,
        }
        for address, purpose in REQUIRED_BREAKPOINTS.items()
    }
    for address, record in breakpoints.items():
        if not record["present"]:
            failures.append(f"missing breakpoint {address}: {record['purpose']}")

    markers = {
        marker: {
            "present": marker in text,
            "purpose": purpose,
        }
        for marker, purpose in REQUIRED_PROBE_MARKERS.items()
    }
    for marker, record in markers.items():
        if not record["present"]:
            failures.append(f"missing probe marker {marker}: {record['purpose']}")

    forbidden_hits = [marker for marker in FORBIDDEN_MARKERS if marker in text]
    for marker in forbidden_hits:
        failures.append(f"forbidden old crashing marker is present in probe script: {marker}")

    return {
        "passed": not failures,
        "path": str(path),
        "breakpoints": breakpoints,
        "markers": markers,
        "forbidden_hits": forbidden_hits,
        "failures": failures,
    }


def check_summary_parser(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    if not path.exists():
        return {
            "passed": False,
            "path": str(path),
            "failures": [f"missing summary parser: {path}"],
        }

    text = read_text(path)
    markers = {marker: marker in text for marker in REQUIRED_PROBE_MARKERS}
    for marker, present in markers.items():
        if not present:
            failures.append(f"summary parser does not recognize marker: {marker}")

    forbidden_hits = [marker for marker in FORBIDDEN_MARKERS if marker in text]
    for marker in forbidden_hits:
        failures.append(f"forbidden old crashing marker is present in summary parser: {marker}")

    return {
        "passed": not failures,
        "path": str(path),
        "markers": markers,
        "forbidden_hits": forbidden_hits,
        "failures": failures,
    }


def check_forbidden_markers(paths: list[Path]) -> dict[str, Any]:
    failures: list[str] = []
    hits: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        text = read_text(path)
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                hits.append({"path": str(path), "marker": marker})
                failures.append(f"forbidden old crashing marker {marker} is present in {path}")

    return {
        "passed": not failures,
        "paths": [str(path) for path in paths],
        "forbidden_markers": list(FORBIDDEN_MARKERS),
        "hits": hits,
        "failures": failures,
    }


def check_focused_log(run: Path) -> dict[str, Any]:
    log = run / "cdb-surface-dump.log"
    failures: list[str] = []
    if not log.exists():
        return {
            "passed": False,
            "run": str(run),
            "log": str(log),
            "failures": [f"missing focused hitbox log: {log}"],
        }

    summary = castle_overview_hitbox_summary.parse_log(log)
    ready = bool(
        summary["marker_counts"]["CASTLEOV_HITBOX_SURFDUMP_READY"]
        or summary["marker_counts"]["SURFDUMP_READY"]
    )
    if not ready:
        failures.append("focused hitbox surface-ready marker was not observed")
    if summary["last_ready"].get("size") != [800, 600]:
        failures.append(f"focused hitbox ready surface was {summary['last_ready'].get('size')}")
    if summary.get("last_overview_post_draw", {}).get("main_size") != [800, 600]:
        failures.append(
            "focused hitbox overview post-draw main surface was "
            f"{summary.get('last_overview_post_draw', {}).get('main_size')}"
        )
    if summary.get("last_overview_post_draw", {}).get("overview_size") != [640, 480]:
        failures.append(
            "focused hitbox native overview surface was "
            f"{summary.get('last_overview_post_draw', {}).get('overview_size')}"
        )
    for key, label in (
        ("displayed_hit_ok", "displayed-coordinate target hit"),
        ("descriptor_ok", "descriptor command/callback install"),
        ("click_gate_ok", "stock click gate"),
        ("callback_suppressed", "callback suppression after proof"),
    ):
        if not summary.get(key):
            failures.append(f"focused hitbox log does not prove {label}")
    displayed_wrapper_ok = bool(summary["marker_counts"]["CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK"])
    if not displayed_wrapper_ok:
        failures.append("focused hitbox log does not prove displayed-coordinate binary wrapper success")
    if summary.get("callback_called"):
        failures.append("focused hitbox callback was entered")
    if summary.get("av_count"):
        failures.append("focused hitbox AV rows were observed")

    return {
        "passed": not failures,
        "run": str(run),
        "log": str(log),
        "ready": ready,
        "ready_size": summary["last_ready"].get("size"),
        "overview_post_draw": summary.get("last_overview_post_draw"),
        "displayed_result": summary.get("displayed_result"),
        "last_descriptor": summary.get("last_descriptor"),
        "last_click_gate": summary.get("last_click_gate"),
        "displayed_hit_ok": summary.get("displayed_hit_ok"),
        "displayed_wrapper_ok": displayed_wrapper_ok,
        "descriptor_ok": summary.get("descriptor_ok"),
        "click_gate_ok": summary.get("click_gate_ok"),
        "callback_suppressed": summary.get("callback_suppressed"),
        "callback_called": summary.get("callback_called"),
        "av_count": summary.get("av_count"),
        "failures": failures,
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    probe = check_probe_script(args.probe_script)
    parser = check_summary_parser(args.summary_parser)
    forbidden = check_forbidden_markers([args.probe_script, args.summary_parser, args.patcher])
    focused = check_focused_log(args.focused_run)
    checks = {
        "probe_script": probe,
        "summary_parser": parser,
        "forbidden_marker_absence": forbidden,
        "focused_hitbox_log": focused,
    }
    failures: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            failures.extend(f"{name}: {failure}" for failure in check.get("failures", []))

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "required_breakpoints": REQUIRED_BREAKPOINTS,
        "required_probe_markers": REQUIRED_PROBE_MARKERS,
        "forbidden_markers": list(FORBIDDEN_MARKERS),
        "checks": checks,
        "failures": failures,
    }


def write_json(path: Path, guard: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    checks = guard["checks"]
    probe = checks["probe_script"]
    focused = checks["focused_hitbox_log"]
    lines = [
        "# Castle Overview Probe Guard",
        "",
        f"- Overall: {status_text(bool(guard.get('passed')))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        "",
        "## Probe Script",
        "",
        f"- Status: {status_text(bool(probe.get('passed')))}",
        f"- Script: `{probe.get('path')}`",
        "",
        "### Required Breakpoints",
        "",
    ]
    for address, record in (probe.get("breakpoints") or {}).items():
        lines.append(
            f"- `{address}`: {status_text(bool(record.get('present')))} - {record.get('purpose')}"
        )

    lines.extend(["", "### Required Markers", ""])
    for marker, record in (probe.get("markers") or {}).items():
        lines.append(
            f"- `{marker}`: {status_text(bool(record.get('present')))} - {record.get('purpose')}"
        )

    lines.extend(
        [
            "",
            "## Focused Hitbox Log",
            "",
            f"- Status: {status_text(bool(focused.get('passed')))}",
            f"- Run: `{focused.get('run')}`",
            f"- Log: `{focused.get('log')}`",
            f"- Ready size: `{focused.get('ready_size')}`",
            f"- Overview post-draw: `{focused.get('overview_post_draw')}`",
            f"- Displayed result: `{focused.get('displayed_result')}`",
            f"- Descriptor: `{focused.get('last_descriptor')}`",
            f"- Click gate: `{focused.get('last_click_gate')}`",
            f"- Displayed hit ok: `{focused.get('displayed_hit_ok')}`",
            f"- Displayed wrapper ok: `{focused.get('displayed_wrapper_ok')}`",
            f"- Click gate ok: `{focused.get('click_gate_ok')}`",
            f"- Callback suppressed: `{focused.get('callback_suppressed')}`",
            f"- Callback called: `{focused.get('callback_called')}`",
            f"- Access violations: `{focused.get('av_count')}`",
            "",
            "## Forbidden Markers",
            "",
        ]
    )
    forbidden = checks["forbidden_marker_absence"]
    lines.append(f"- Status: {status_text(bool(forbidden.get('passed')))}")
    lines.append(f"- Markers: {', '.join(f'`{marker}`' for marker in guard['forbidden_markers'])}")
    if forbidden.get("hits"):
        for hit in forbidden["hits"]:
            lines.append(f"- Hit: `{hit['marker']}` in `{hit['path']}`")

    if guard.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard.get('passed')))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
        if name == "probe_script":
            present = [
                address
                for address, record in (check.get("breakpoints") or {}).items()
                if record.get("present")
            ]
            print(f"  breakpoints_present: {present}")
        if name == "focused_hitbox_log":
            print(f"  ready_size: {check.get('ready_size')}")
            print(f"  displayed_hit_ok: {check.get('displayed_hit_ok')}")
            print(f"  displayed_wrapper_ok: {check.get('displayed_wrapper_ok')}")
            print(f"  click_gate_ok: {check.get('click_gate_ok')}")
            print(f"  av_count: {check.get('av_count')}")
        if check.get("failures"):
            for failure in check["failures"]:
                print(f"  - {failure}")
    if guard.get("failures"):
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-script", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--summary-parser", type=Path, default=DEFAULT_SUMMARY_PARSER)
    parser.add_argument("--patcher", type=Path, default=DEFAULT_PATCHER)
    parser.add_argument("--focused-run", type=Path, default=DEFAULT_FOCUSED_RUN)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
    if args.write_json:
        write_json(args.write_json, guard)
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    print_guard(guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

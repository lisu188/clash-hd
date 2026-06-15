#!/usr/bin/env python3
"""Inventory right-bottom owner-flag/action-route evidence from archived logs.

This repo-only helper scans existing CDB surface-dump logs. It does not launch
Clash95, CDB, wrappers, PowerShell, or visible windows. The goal is to keep the
current right-bottom conclusion machine-checkable: controlled forced routes can
enter the owner/action renderer, while the current natural command-99 route is
blocked by owner state and parks the 004338E0 action descriptor off-screen.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CAPTURES_ROOT = Path("captures")
DEFAULT_JSON = Path("captures/current/right-bottom-owner-flag-inventory-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-owner-flag-inventory-current.md")
RUNTIME_POLICY = (
    "repo-only; scans existing CDB logs and does not launch Clash95, CDB, "
    "wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "right-bottom owner/action evidence must keep at least one controlled "
    "forced owner route, at least one current natural owner-flag-gated route, "
    "and no non-fixture archived natural route that already reaches the "
    "owner/action renderer without an explicit forced owner flag"
)
EXPECTED_ACTION_CALLBACK = "004338e0"
NON_NATURAL_FIXTURE_PROOF_CLASS = "non_natural_isolated_fixture"

MARKERS = (
    "RBUI_DESC_SWITCH",
    "RBUI_PANEL_DRAW",
    "RBUI_ACTION_BOX",
    "NOWNER_OWNER_FLAG_TEST",
    "NOWNER_OWNER_SCREEN_DESC_DRAW",
    "NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY",
    "NOWNER_4338E0_ENTRY",
    "NOWNER_ACTION_CALL_WRAPPER",
    "NOWNER_OWNER_435BC0_ENTRY",
    "NOWNER_WRAPPER_COPYBACK_DONE",
    "NOWNER_CASTLE_HITMAP_SAMPLE",
    "NOWNER_CASTLE_CMD99_TARGET",
    "NOWNER_CASTLE_HIT",
    "NOWNER_4338E0_SURFDUMP_READY",
    "AV_SURFDUMP",
)

FIXTURE_MARKERS = (
    "NOWNER_CASTLE_HITMAP_SAMPLE",
)

FORCED_FLAG_RE = re.compile(
    r"(?P<prefix>[A-Z0-9]+)_OWNER_FLAG_FORCED\b.*?\bowner_flag_new=(?P<flag>0x[0-9A-Fa-f]+)"
)
ACTION_CALL_RE = re.compile(r"(?P<prefix>[A-Z0-9]+)_ACTION_CALL\b")
OWNER_RENDER_RE = re.compile(
    r"(?P<prefix>[A-Z0-9]+)_(?:OWNER_435BC0_ENTRY|PANEL_DRAW_4347A0|ACTION_BOX_435500)\b"
)
FLAG_TEST_RE = re.compile(
    r"NOWNER_OWNER_FLAG_TEST\b.*?\bowner_flag=(?P<flag>0x[0-9A-Fa-f]+)\b.*?"
    r"\bbit2=(?P<bit2>\d+)\b.*?\bbit1=(?P<bit1>\d+)\b.*?\bbit8=(?P<bit8>\d+)"
)
DESC_DRAW_RE = re.compile(
    r"NOWNER_OWNER_SCREEN_DESC_DRAW\b.*?"
    r"d0=\((?P<d0x>-?\d+),(?P<d0y>-?\d+) cb=(?P<d0cb>[0-9A-Fa-f]+)\)\s+"
    r"d1=\((?P<d1x>-?\d+),(?P<d1y>-?\d+) cb=(?P<d1cb>[0-9A-Fa-f]+)\)\s+"
    r"d2=\((?P<d2x>-?\d+),(?P<d2y>-?\d+) cb=(?P<d2cb>[0-9A-Fa-f]+)\)"
)
DESC_RESULT_RE = re.compile(
    r"NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY\b.*?\bresult=(?P<result>-?\d+)\b.*?"
    r"\bowner=(?P<owner>[0-9A-Fa-f]+)\b.*?\bowner_flag=(?P<flag>0x[0-9A-Fa-f]+)\b.*?"
    r"\bsize=\((?P<width>\d+),(?P<height>\d+)\)"
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def marker_counts(text: str) -> dict[str, int]:
    return {marker: text.count(marker) for marker in MARKERS}


def lower_hex(value: str | None) -> str | None:
    return value.lower() if value is not None else None


def int_group(match: re.Match[str], name: str) -> int:
    return int(match.group(name))


def parse_descriptors(text: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    match = DESC_DRAW_RE.search(text)
    descriptors: dict[str, dict[str, Any]] = {}
    if not match:
        return descriptors, None
    for slot in ("d0", "d1", "d2"):
        descriptors[slot] = {
            "x": int_group(match, f"{slot}x"),
            "y": int_group(match, f"{slot}y"),
            "callback": lower_hex(match.group(f"{slot}cb")),
        }
    action_descriptor = next(
        (
            {"slot": slot, **descriptor}
            for slot, descriptor in descriptors.items()
            if descriptor.get("callback") == EXPECTED_ACTION_CALLBACK
        ),
        None,
    )
    return descriptors, action_descriptor


def parse_desc_result(text: str) -> dict[str, Any]:
    match = DESC_RESULT_RE.search(text)
    if not match:
        return {}
    return {
        "result": int_group(match, "result"),
        "owner": lower_hex(match.group("owner")),
        "owner_flag": lower_hex(match.group("flag")),
        "surface": [int_group(match, "width"), int_group(match, "height")],
    }


def fixture_summary_for(run: Path) -> dict[str, Any]:
    return load_json(run / "right-bottom-slot-fixture-result-summary.json")


def is_non_natural_fixture(
    text: str,
    summary: dict[str, Any],
    fixture_summary: dict[str, Any],
    counts: dict[str, int],
) -> bool:
    if fixture_summary.get("proof_class") == NON_NATURAL_FIXTURE_PROOF_CLASS:
        return True
    extra_probe = str(summary.get("ExtraProbeTemplate") or "").lower()
    candidate_dir = str(summary.get("CandidateDir") or "").lower()
    candidate_path = str(summary.get("CandidatePath") or "").lower()
    if "slot5_fixture" in extra_probe or "slot5-as-slot0-fixture" in extra_probe:
        return True
    if "right-bottom-slot5-as-slot0-fixture" in candidate_dir:
        return True
    if "right-bottom-slot5-as-slot0-fixture" in candidate_path:
        return True
    lowered = text.lower()
    if "slot5-as-slot0 fixture" in lowered:
        return True
    return any(int(counts.get(marker) or 0) > 0 for marker in FIXTURE_MARKERS)


def parse_log(log_path: Path, captures_root: Path) -> dict[str, Any]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    run = log_path.parent
    summary = load_json(run / "summary.json")
    counts = marker_counts(text)
    fixture_summary = fixture_summary_for(run)
    non_natural_fixture = is_non_natural_fixture(text, summary, fixture_summary, counts)
    forced_flags = [
        {"prefix": match.group("prefix"), "flag": lower_hex(match.group("flag"))}
        for match in FORCED_FLAG_RE.finditer(text)
    ]
    action_prefixes = sorted({match.group("prefix") for match in ACTION_CALL_RE.finditer(text)})
    owner_render_prefixes = sorted({match.group("prefix") for match in OWNER_RENDER_RE.finditer(text)})

    flag_test_match = FLAG_TEST_RE.search(text)
    flag_test = {
        "owner_flag": lower_hex(flag_test_match.group("flag")) if flag_test_match else None,
        "bit2": int_group(flag_test_match, "bit2") if flag_test_match else None,
        "bit1": int_group(flag_test_match, "bit1") if flag_test_match else None,
        "bit8": int_group(flag_test_match, "bit8") if flag_test_match else None,
    }
    descriptors, action_descriptor = parse_descriptors(text)
    desc_result = parse_desc_result(text)
    natural_action_route_count = sum(
        counts[marker]
        for marker in (
            "NOWNER_4338E0_ENTRY",
            "NOWNER_ACTION_CALL_WRAPPER",
            "NOWNER_OWNER_435BC0_ENTRY",
            "NOWNER_WRAPPER_COPYBACK_DONE",
        )
    )

    has_zero_bits = (
        flag_test.get("owner_flag") == "0x00"
        and all(int(flag_test.get(bit) or 0) == 0 for bit in ("bit2", "bit1", "bit8"))
    )
    descriptor_result_value = desc_result.get("result")
    natural_state_gated = (
        counts["NOWNER_OWNER_FLAG_TEST"] > 0
        and has_zero_bits
        and bool(action_descriptor)
        and int((action_descriptor or {}).get("x") or 0) >= 800
        and descriptor_result_value is not None
        and int(descriptor_result_value) == 0
        and desc_result.get("owner_flag") == "0x00"
        and natural_action_route_count == 0
        and counts["AV_SURFDUMP"] == 0
    )
    forced_owner_action_route = bool(forced_flags) and (
        bool(action_prefixes) or bool(owner_render_prefixes)
    )
    non_natural_fixture_route = non_natural_fixture and natural_action_route_count > 0
    natural_ui_descriptor_only = (
        counts["RBUI_DESC_SWITCH"] > 0
        and counts["RBUI_PANEL_DRAW"] == 0
        and counts["RBUI_ACTION_BOX"] == 0
    )

    classifications: list[str] = []
    if non_natural_fixture:
        classifications.append("non_natural_isolated_fixture")
    if natural_state_gated:
        classifications.append("natural_state_gated")
    if natural_action_route_count and not non_natural_fixture:
        classifications.append("natural_action_route")
    if forced_owner_action_route:
        classifications.append("forced_owner_action_route")
    if natural_ui_descriptor_only:
        classifications.append("natural_ui_descriptor_only")
    if not classifications and (
        forced_flags
        or action_prefixes
        or owner_render_prefixes
        or counts["NOWNER_OWNER_FLAG_TEST"]
        or counts["RBUI_DESC_SWITCH"]
    ):
        classifications.append("right_bottom_related")

    try:
        run_label = run.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except (OSError, ValueError):
        try:
            run_label = run.relative_to(captures_root.parent).as_posix()
        except ValueError:
            run_label = str(run)

    return {
        "run": str(run),
        "run_label": run_label,
        "log": str(log_path),
        "classifications": classifications,
        "proof_class": (
            NON_NATURAL_FIXTURE_PROOF_CLASS
            if non_natural_fixture
            else fixture_summary.get("proof_class")
        ),
        "fixture_status": fixture_summary.get("status"),
        "is_non_natural_fixture": non_natural_fixture,
        "hidden_desktop": summary.get("HiddenDesktop"),
        "stage": summary.get("Stage"),
        "candidate_sha256": summary.get("CandidateSha256"),
        "surface": [
            (summary.get("Surface") or {}).get("Width"),
            (summary.get("Surface") or {}).get("Height"),
        ],
        "marker_counts": counts,
        "forced_flags": forced_flags,
        "action_prefixes": action_prefixes,
        "owner_render_prefixes": owner_render_prefixes,
        "natural_flag_test": flag_test,
        "natural_descriptors": descriptors,
        "natural_action_descriptor": action_descriptor,
        "natural_descriptor_result": desc_result,
        "natural_action_route_count": natural_action_route_count,
        "non_natural_fixture_action_route_count": (
            natural_action_route_count if non_natural_fixture_route else 0
        ),
        "av_count": counts["AV_SURFDUMP"],
    }


def scan_logs(captures_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for log_path in sorted(captures_root.rglob("cdb-surface-dump.log")):
        row = parse_log(log_path, captures_root)
        if row["classifications"]:
            rows.append(row)
    return rows


def build_report(captures_root: Path) -> dict[str, Any]:
    all_logs = sorted(captures_root.rglob("cdb-surface-dump.log"))
    rows = scan_logs(captures_root)
    classification_counts: Counter[str] = Counter(
        classification
        for row in rows
        for classification in row["classifications"]
    )
    natural_state_rows = [
        row for row in rows if "natural_state_gated" in row["classifications"]
    ]
    forced_route_rows = [
        row for row in rows if "forced_owner_action_route" in row["classifications"]
    ]
    natural_action_rows = [
        row for row in rows if "natural_action_route" in row["classifications"]
    ]
    fixture_rows = [
        row for row in rows if "non_natural_isolated_fixture" in row["classifications"]
    ]
    failures: list[str] = []
    if not all_logs:
        failures.append(f"no CDB surface-dump logs found under {captures_root}")
    if not natural_state_rows:
        failures.append("no natural owner-flag-gated right-bottom route was found")
    if not forced_route_rows:
        failures.append("no controlled forced owner/action route was found")
    if natural_action_rows:
        failures.append(
            "a non-fixture archived natural route reaches owner/action rows; current blocker docs need review"
        )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "captures_root": str(captures_root),
        "scanned_log_count": len(all_logs),
        "relevant_run_count": len(rows),
        "classification_counts": dict(sorted(classification_counts.items())),
        "natural_state_gated_count": len(natural_state_rows),
        "forced_owner_action_route_count": len(forced_route_rows),
        "natural_action_route_count": len(natural_action_rows),
        "non_natural_isolated_fixture_count": len(fixture_rows),
        "non_natural_isolated_fixture_action_route_count": sum(
            int(row.get("non_natural_fixture_action_route_count") or 0)
            for row in fixture_rows
        ),
        "natural_ui_descriptor_only_count": classification_counts.get(
            "natural_ui_descriptor_only",
            0,
        ),
        "representative_runs": {
            "natural_state_gated": natural_state_rows[0] if natural_state_rows else None,
            "forced_owner_action_route": forced_route_rows[0] if forced_route_rows else None,
            "natural_ui_descriptor_only": next(
                (
                    row
                    for row in rows
                    if "natural_ui_descriptor_only" in row["classifications"]
                ),
                None,
            ),
            "non_natural_isolated_fixture": fixture_rows[0] if fixture_rows else None,
        },
        "rows": rows,
        "failures": failures,
    }


def status_text(value: bool) -> str:
    return "PASS" if value else "FAIL"


def write_markdown(path: Path, report: dict[str, Any], max_rows: int) -> None:
    lines = [
        "# Right-Bottom Owner-Flag Inventory",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Scanned CDB logs: `{report['scanned_log_count']}`",
        f"- Relevant runs: `{report['relevant_run_count']}`",
        f"- Classification counts: `{report['classification_counts']}`",
        f"- Natural state-gated routes: `{report['natural_state_gated_count']}`",
        f"- Controlled forced owner/action routes: `{report['forced_owner_action_route_count']}`",
        f"- Natural owner/action routes: `{report['natural_action_route_count']}`",
        f"- Non-natural isolated fixture routes: `{report['non_natural_isolated_fixture_count']}`",
        f"- Non-natural fixture owner/action rows: `{report['non_natural_isolated_fixture_action_route_count']}`",
        "",
        "## Representative Runs",
        "",
    ]
    for label, row in (report.get("representative_runs") or {}).items():
        if not row:
            lines.append(f"- `{label}`: none")
            continue
        lines.append(
            "- `{label}`: `{run}` stage `{stage}` classifications `{classes}`".format(
                label=label,
                run=row.get("run_label"),
                stage=row.get("stage"),
                classes=row.get("classifications"),
            )
        )
        action_desc = row.get("natural_action_descriptor")
        if action_desc:
            lines.append(f"  Action descriptor: `{action_desc}`")
        flag_test = row.get("natural_flag_test")
        if flag_test and flag_test.get("owner_flag"):
            lines.append(f"  Owner flag test: `{flag_test}`")
        proof_class = row.get("proof_class")
        if proof_class:
            lines.append(f"  Proof class: `{proof_class}`")

    rows = report.get("rows") or []
    lines.extend(["", f"## First {min(max_rows, len(rows))} Relevant Runs", ""])
    for row in rows[:max_rows]:
        lines.append(
            "- `{run}`: `{classes}`, forced `{forced}`, actions `{actions}`, owner-render `{owner}`".format(
                run=row.get("run_label"),
                classes=row.get("classifications"),
                forced=row.get("forced_flags"),
                actions=row.get("action_prefixes"),
                owner=row.get("owner_render_prefixes"),
            )
        )

    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_report(report: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"scanned-logs: {report['scanned_log_count']}")
    print(f"relevant-runs: {report['relevant_run_count']}")
    print(f"classification-counts: {report['classification_counts']}")
    print(f"natural-state-gated: {report['natural_state_gated_count']}")
    print(f"forced-owner-action-routes: {report['forced_owner_action_route_count']}")
    print(f"natural-owner-action-routes: {report['natural_action_route_count']}")
    print(f"non-natural-isolated-fixtures: {report['non_natural_isolated_fixture_count']}")
    print(
        "non-natural-fixture-owner-action-rows: "
        f"{report['non_natural_isolated_fixture_action_route_count']}"
    )
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures-root", type=Path, default=DEFAULT_CAPTURES_ROOT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--max-markdown-rows", type=int, default=30)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.captures_root)
    print_report(report)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, report, args.max_markdown_rows)
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

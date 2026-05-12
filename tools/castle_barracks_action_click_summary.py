#!/usr/bin/env python3
"""Summarize Clash95 centered castle/barracks action descriptor CDB probes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "APBARRACKS_CLICKFLAG_WATCH_ARMED",
    "APBARRACKS_CLICKFLAG_WRITE",
    "APBARRACKS_CLICKFLAG_CLEAR_PRE",
    "APBARRACKS_CLICKFLAG_CLEAR_POST",
    "APBARRACKS_ACTION_FORCE_CENTERED",
    "APBARRACKS_SELECT_FORCED",
    "APBARRACKS_ACTION_DESCRIPTOR_ENTRY",
    "APBARRACKS_ACTION_WIDGET_CLICK_GATE",
    "APBARRACKS_ACTION_WIDGET_PRE_GATES",
    "APBARRACKS_ACTION_WIDGET_REARM_ENTRY",
    "APBARRACKS_ACTION_WIDGET_REARM_PRE_GATES",
    "APBARRACKS_ACTION_WIDGET_REARM_CLICK",
    "APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET",
    "APBARRACKS_ACTION_WIDGET_HOVER_ARM",
    "APBARRACKS_ACTION_DESCRIPTOR_CALLBACK",
    "APBARRACKS_ACTION_DESCRIPTOR_RESULT",
    "APBARRACKS_ACTION_DESCRIPTOR_FAIL_EXIT",
    "APBARRACKS_ACTION_CLICK_435620_ENTRY",
    "APBARRACKS_ACTION_CLICK_435620_BEFORE_SET",
    "APBARRACKS_ACTION_CLICK_EXIT_SET",
    "APBARRACKS_ACTION_CLICK_4356C0_ENTRY",
    "APBARRACKS_ACTION_CLICK_4356C0_CHECK_RET",
    "APBARRACKS_ACTION_CLICK_4356C0_SUCCESS_BRANCH",
    "APBARRACKS_ACTION_CLICK_4356C0_CONTROLLED_STOP",
    "APBARRACKS_ACTION_CLICK_4356C0_EARLY_RETURN",
    "APBARRACKS_ACTION_CLICK_4356C0_RETURN",
    "APBARRACKS_ACTION_BOX_435500",
    "APBARRACKS_SURFDUMP_READY",
    "SURFDUMP_READY",
)

KV_RE = re.compile(
    r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)="
    r"(?P<value>\([^)]*\)|[^\s]+)"
)


def parse_value(value: str) -> Any:
    value = value.strip().rstrip(",")
    if value.startswith("(") and value.endswith(")"):
        parts = [part.strip() for part in value[1:-1].split(",") if part.strip()]
        return [parse_value(part) for part in parts]
    try:
        return int(value, 0)
    except ValueError:
        if re.fullmatch(r"[0-9A-Fa-f]{6,8}", value):
            return int(value, 16)
        return value


def parse_log(
    path: Path,
    expected_desc: int = 0x0051519A,
    expected_callback: int = 0x00435620,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker_counts = {marker: 0 for marker in MARKERS}
    rows: list[dict[str, Any]] = []
    av_rows: list[dict[str, Any]] = []
    marker_re = re.compile("|".join(re.escape(marker) for marker in MARKERS))

    for index, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        if "access violation" in lowered or "code c0000005" in lowered:
            av_rows.append({"line": index, "text": line.strip()})

        matches = list(marker_re.finditer(line))
        for match_index, match in enumerate(matches):
            marker = match.group(0)
            end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(line)
            fragment = line[match.start() : end].strip()
            marker_counts[marker] += 1
            values = {m.group("key"): parse_value(m.group("value")) for m in KV_RE.finditer(fragment)}
            rows.append(
                {
                    "line": index,
                    "marker": marker,
                    "values": values,
                    "text": fragment,
                }
            )

    callback_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_DESCRIPTOR_CALLBACK"
    ]
    click_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_CLICK_435620_ENTRY"
    ]
    exit_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_CLICK_EXIT_SET"
    ]
    click_4356c0_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_CLICK_4356C0_ENTRY"
    ]
    select_forced_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_SELECT_FORCED"
    ]
    check_4356c0_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_CLICK_4356C0_CHECK_RET"
    ]
    success_4356c0_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_CLICK_4356C0_SUCCESS_BRANCH"
    ]
    controlled_4356c0_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_CLICK_4356C0_CONTROLLED_STOP"
    ]
    early_4356c0_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_CLICK_4356C0_EARLY_RETURN"
    ]
    fail_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_DESCRIPTOR_FAIL_EXIT"
    ]
    pre_gate_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_ACTION_WIDGET_PRE_GATES"
    ]
    clickflag_write_rows = [
        row for row in rows if row["marker"] in {
            "APBARRACKS_CLICKFLAG_WRITE",
            "APBARRACKS_CLICKFLAG_CLEAR_PRE",
            "APBARRACKS_CLICKFLAG_CLEAR_POST",
        }
    ]
    clickflag_watch_armed_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_CLICKFLAG_WATCH_ARMED"
    ]

    descriptor_click_ok = any(
        row["values"].get("desc") == expected_desc
        and row["values"].get("callback") == expected_callback
        for row in callback_rows
    )
    action_exit_ok = any(
        row["values"].get("action_state") == 1
        for row in exit_rows
    )
    pre_gate_click_ok = any(
        row["values"].get("desc") == expected_desc
        and row["values"].get("click_flag") == 1
        and row["values"].get("button0") == 0x80
        for row in pre_gate_rows
    )

    classification: list[str] = []
    if marker_counts["APBARRACKS_ACTION_FORCE_CENTERED"]:
        classification.append("centered action coordinate was installed")
    else:
        classification.append("centered action coordinate was not observed")
    if select_forced_rows:
        classification.append("selected barracks addon was forced before action-panel draw")
    if descriptor_click_ok:
        classification.append(
            f"descriptor {expected_desc:08x} callback resolved to {expected_callback:08x}"
        )
    else:
        classification.append(
            f"descriptor callback did not prove {expected_callback:08x} dispatch"
        )
    if click_rows:
        classification.append("00435620 action click dispatch was entered")
    else:
        classification.append("00435620 action click dispatch was not entered")
    if click_4356c0_rows:
        classification.append("004356c0 action callback was entered")
    if success_4356c0_rows:
        classification.append("004356c0 action callback reached the success branch")
    elif controlled_4356c0_rows:
        classification.append("004356c0 action callback stopped at the controlled dump point")
    elif early_4356c0_rows:
        classification.append("004356c0 action callback returned through the availability-failed branch")
    if action_exit_ok:
        classification.append("action click set dword_532210 to exit the barracks loop")
    else:
        classification.append("action click did not prove dword_532210 exit state")
    if clickflag_watch_armed_rows:
        classification.append("dword_544D04 trace was armed after centered click injection")
    if pre_gate_click_ok:
        classification.append(
            f"action descriptor {expected_desc:08x} saw click_flag=1 before stock gates"
        )
    if clickflag_write_rows:
        first_write = clickflag_write_rows[0]["values"]
        classification.append(
            "dword_544D04 changed after arming at eip={eip} new={new}".format(
                eip=first_write.get("eip", "unknown"),
                new=first_write.get("new", "unknown"),
            )
        )
    if fail_rows:
        classification.append("descriptor probe used failure exit")
    if marker_counts["APBARRACKS_SURFDUMP_READY"] or marker_counts["SURFDUMP_READY"]:
        classification.append("surface dump reached ready state")
    else:
        classification.append("surface dump did not reach ready state")

    return {
        "log": str(path),
        "expected_desc": expected_desc,
        "expected_callback": expected_callback,
        "marker_counts": marker_counts,
        "row_count": len(rows),
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "descriptor_click_ok": descriptor_click_ok,
        "action_exit_ok": action_exit_ok,
        "success_4356c0_ok": bool(success_4356c0_rows),
        "controlled_4356c0_ok": bool(controlled_4356c0_rows),
        "pre_gate_click_ok": pre_gate_click_ok,
        "failure_exit_count": len(fail_rows),
        "clickflag_watch_armed_count": len(clickflag_watch_armed_rows),
        "clickflag_write_count": len(clickflag_write_rows),
        "first_clickflag_write": clickflag_write_rows[0]["values"] if clickflag_write_rows else None,
        "last_callback": callback_rows[-1]["values"] if callback_rows else None,
        "last_select_forced": select_forced_rows[-1]["values"] if select_forced_rows else None,
        "last_click": click_rows[-1]["values"] if click_rows else None,
        "last_click_4356c0": click_4356c0_rows[-1]["values"] if click_4356c0_rows else None,
        "last_check_4356c0": check_4356c0_rows[-1]["values"] if check_4356c0_rows else None,
        "last_success_4356c0": success_4356c0_rows[-1]["values"] if success_4356c0_rows else None,
        "last_controlled_4356c0": controlled_4356c0_rows[-1]["values"] if controlled_4356c0_rows else None,
        "last_early_4356c0": early_4356c0_rows[-1]["values"] if early_4356c0_rows else None,
        "last_exit": exit_rows[-1]["values"] if exit_rows else None,
        "classification": classification,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], path: Path, screenshot: str | None) -> None:
    lines = [
        "# Castle Barracks Centered Action Click Probe",
        "",
        f"- Log: `{summary['log']}`",
        f"- Expected descriptor: `{summary['expected_desc']:08x}`",
        f"- Expected callback: `{summary['expected_callback']:08x}`",
        f"- Rows parsed: {summary['row_count']}",
        f"- Access violations: {summary['av_count']}",
        f"- Descriptor click ok: {summary['descriptor_click_ok']}",
        f"- Action exit ok: {summary['action_exit_ok']}",
        f"- 004356c0 success branch ok: {summary['success_4356c0_ok']}",
        f"- 004356c0 controlled stop ok: {summary['controlled_4356c0_ok']}",
        f"- Pre-gate click ok: {summary['pre_gate_click_ok']}",
        f"- Failure exits: {summary['failure_exit_count']}",
        f"- Click flag trace armed: {summary['clickflag_watch_armed_count']}",
        f"- Click flag writes: {summary['clickflag_write_count']}",
        "",
        "## Classification",
        "",
    ]
    lines += [f"- {item}" for item in summary["classification"]]
    if screenshot:
        lines += ["", "## Screenshot", "", f"![castle barracks action click]({screenshot})"]
    lines += ["", "## Key Rows", ""]
    for row in summary["rows"][-16:]:
        lines.append(f"- line {row['line']}: `{row['text']}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--expect-desc", default="0x0051519a")
    parser.add_argument("--expect-callback", default="0x00435620")
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--screenshot")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-descriptor-click", action="store_true")
    parser.add_argument("--require-action-exit", action="store_true")
    parser.add_argument("--require-4356c0-success", action="store_true")
    parser.add_argument("--require-4356c0-controlled-stop", action="store_true")
    parser.add_argument("--require-clickflag-write", action="store_true")
    parser.add_argument("--forbid-failure-exit", action="store_true")
    args = parser.parse_args()

    expected_desc = int(args.expect_desc, 0)
    expected_callback = int(args.expect_callback, 0)
    summary = parse_log(args.log, expected_desc, expected_callback)
    if args.screenshot:
        summary["screenshot"] = args.screenshot
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md, args.screenshot)

    print(
        "ready={ready} descriptor_click_ok={descriptor} action_exit_ok={exit_ok} "
        "success_4356c0_ok={success_4356c0} controlled_4356c0_ok={controlled_4356c0} "
        "failure_exits={failures} clickflag_writes={clickflag_writes} av_count={av}".format(
            ready=bool(
                summary["marker_counts"]["APBARRACKS_SURFDUMP_READY"]
                or summary["marker_counts"]["SURFDUMP_READY"]
            ),
            descriptor=summary["descriptor_click_ok"],
            exit_ok=summary["action_exit_ok"],
            success_4356c0=summary["success_4356c0_ok"],
            controlled_4356c0=summary["controlled_4356c0_ok"],
            failures=summary["failure_exit_count"],
            clickflag_writes=summary["clickflag_write_count"],
            av=summary["av_count"],
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")

    if args.require_ready and not (
        summary["marker_counts"]["APBARRACKS_SURFDUMP_READY"]
        or summary["marker_counts"]["SURFDUMP_READY"]
    ):
        print("required surface-ready marker was not observed", file=sys.stderr)
        return 2
    if args.require_descriptor_click and not summary["descriptor_click_ok"]:
        print("required action descriptor click was not observed", file=sys.stderr)
        return 2
    if args.require_action_exit and not summary["action_exit_ok"]:
        print("required action exit state was not observed", file=sys.stderr)
        return 2
    if args.require_4356c0_success and not summary["success_4356c0_ok"]:
        print("required 004356c0 success branch was not observed", file=sys.stderr)
        return 2
    if args.require_4356c0_controlled_stop and not summary["controlled_4356c0_ok"]:
        print("required 004356c0 controlled stop was not observed", file=sys.stderr)
        return 2
    if args.require_clickflag_write and not summary["clickflag_write_count"]:
        print("required click-flag write was not observed", file=sys.stderr)
        return 2
    if args.forbid_failure_exit and summary["failure_exit_count"]:
        print("failure-exit marker was observed", file=sys.stderr)
        return 2
    if summary["av_count"]:
        print("access violation rows were observed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

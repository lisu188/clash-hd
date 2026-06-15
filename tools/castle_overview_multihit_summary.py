#!/usr/bin/env python3
"""Summarize Clash95 full castle overview multi-hitbox CDB probes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "CASTLEOV_MULTI_TARGET_SET",
    "CASTLEOV_MULTI_OVERVIEW_POST_DRAW",
    "CASTLEOV_MULTI_HITTEST_BEGIN",
    "CASTLEOV_MULTI_HITTEST_RESULT",
    "CASTLEOV_MULTI_HITTEST_MISS",
    "CASTLEOV_MULTI_DESCRIPTOR_INSTALL",
    "CASTLEOV_MULTI_CLICK_GATE",
    "CASTLEOV_MULTI_TARGET_OK",
    "CASTLEOV_MULTI_TARGET_DONE",
    "CASTLEOV_MULTI_CALLBACK_CALL",
    "CASTLEOV_MULTI_SURFDUMP_READY",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
)

EXPECTED_TARGETS = {
    0: {"raw": 0xF8, "command": 0x86, "callback": 0x0044FE70, "gate": 1},
    1: {"raw": 0xFE, "command": 0x63, "callback": 0x00433C20, "gate": 1},
    2: {"raw": 0xFF, "command": 0x87, "callback": 0x0042B0A0, "gate": 1},
}

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


def parse_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker_counts = {marker: 0 for marker in MARKERS}
    marker_re = re.compile("|".join(re.escape(marker) for marker in MARKERS))
    rows: list[dict[str, Any]] = []
    av_rows: list[dict[str, Any]] = []

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
            rows.append(
                {
                    "line": index,
                    "marker": marker,
                    "values": {m.group("key"): parse_value(m.group("value")) for m in KV_RE.finditer(fragment)},
                    "text": fragment,
                }
            )

    for row in rows:
        row["index"] = row["values"].get("index")

    expected_by_index: dict[int, dict[str, Any]] = {}
    for row in rows:
        if row["marker"] != "CASTLEOV_MULTI_TARGET_SET":
            continue
        values = row["values"]
        index = values.get("index")
        if not isinstance(index, int):
            continue
        expected_by_index[index] = {
            "raw": values.get("raw"),
            "command": values.get("command"),
            "callback": values.get("callback"),
            "gate": values.get("expected_gate", values.get("gate")),
        }
    if not expected_by_index:
        expected_by_index = {
            index: expected.copy()
            for index, expected in EXPECTED_TARGETS.items()
        }

    by_index: dict[int, dict[str, Any]] = {
        index: {"expected": expected.copy(), "ok": False}
        for index, expected in sorted(expected_by_index.items())
    }
    for row in rows:
        values = row["values"]
        index = row.get("index")
        if not isinstance(index, int) or index not in by_index:
            continue
        target = by_index[index]
        marker = row["marker"]
        if marker == "CASTLEOV_MULTI_TARGET_SET":
            target["target_set"] = values
        elif marker == "CASTLEOV_MULTI_HITTEST_RESULT":
            target["hittest_result"] = values
        elif marker == "CASTLEOV_MULTI_DESCRIPTOR_INSTALL":
            target["descriptor"] = values
        elif marker == "CASTLEOV_MULTI_CLICK_GATE":
            target["click_gate"] = values
        elif marker in {"CASTLEOV_MULTI_TARGET_OK", "CASTLEOV_MULTI_TARGET_DONE"}:
            target["completion"] = values

    for target in by_index.values():
        expected = target["expected"]
        result = target.get("hittest_result") or {}
        descriptor = target.get("descriptor") or {}
        gate = target.get("click_gate") or {}
        target["raw_ok"] = result.get("raw_hit") == expected["raw"]
        target["descriptor_ok"] = (
            descriptor.get("command") == expected["command"]
            and descriptor.get("callback") == expected["callback"]
        )
        target["gate_ok"] = (
            gate.get("command") == expected["command"]
            and gate.get("callback") == expected["callback"]
            and gate.get("gate") == expected["gate"]
        )
        completion = target.get("completion") or {}
        if completion and any(key in completion for key in ("raw", "command", "callback", "gate")):
            target["completion_ok"] = (
                completion.get("raw") == expected["raw"]
                and completion.get("command") == expected["command"]
                and completion.get("callback") == expected["callback"]
                and completion.get("gate") == expected["gate"]
            )
        else:
            target["completion_ok"] = bool(completion)
        target["ok"] = (
            target["raw_ok"]
            and target["descriptor_ok"]
            and target["gate_ok"]
            and target["completion_ok"]
        )

    ready_rows = [
        row
        for row in rows
        if row["marker"] in {"CASTLEOV_MULTI_SURFDUMP_READY", "SURFDUMP_READY"}
    ]
    last_ready = ready_rows[-1]["values"] if ready_rows else {}
    all_targets_ok = all(target["ok"] for target in by_index.values())

    classification = []
    for index, target in by_index.items():
        expected = target["expected"]
        classification.append(
            "target {index} raw 0x{raw:02X} command 0x{command:02X} gate {gate}: {status}".format(
                index=index,
                raw=expected["raw"],
                command=expected["command"],
                gate=expected["gate"],
                status="ok" if target["ok"] else "not proven",
            )
        )
    if ready_rows:
        classification.append("surface dump reached ready state")
    if av_rows:
        classification.append("AV observed")

    return {
        "log": str(path),
        "expected_targets": EXPECTED_TARGETS,
        "targets": by_index,
        "all_targets_ok": all_targets_ok,
        "marker_counts": marker_counts,
        "row_count": len(rows),
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "last_ready": last_ready,
        "callback_called": bool(marker_counts["CASTLEOV_MULTI_CALLBACK_CALL"]),
        "classification": classification,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], path: Path, screenshot: str | None) -> None:
    lines = [
        "# Castle Overview Multi-Hitbox Probe",
        "",
        f"- Log: `{summary['log']}`",
        f"- All targets ok: {summary['all_targets_ok']}",
        f"- Access violations: {summary['av_count']}",
        f"- Callback called: {summary['callback_called']}",
        f"- Ready surface size: `{summary['last_ready'].get('size')}`",
        "",
        "## Targets",
        "",
    ]
    for index, target in summary["targets"].items():
        expected = target["expected"]
        lines.append(
            f"- index {index}: raw `0x{expected['raw']:02X}`, command `0x{expected['command']:02X}`, "
            f"callback `0x{expected['callback']:08X}`, expected gate `{expected['gate']}`, "
            f"completion_ok={target.get('completion_ok')}, ok={target['ok']}"
        )
    lines += ["", "## Classification", ""]
    lines += [f"- {item}" for item in summary["classification"]]
    if screenshot:
        lines += ["", "## Screenshot", "", f"![castle overview multi-hitbox]({screenshot})"]
    lines += ["", "## Key Rows", ""]
    for row in summary["rows"][-24:]:
        lines.append(f"- line {row['line']}: `{row['text']}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--screenshot")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-800x600", action="store_true")
    parser.add_argument("--require-all-targets", action="store_true")
    parser.add_argument("--forbid-callback", action="store_true")
    args = parser.parse_args()

    summary = parse_log(args.log)
    if args.screenshot:
        summary["screenshot"] = args.screenshot
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md, args.screenshot)

    print(
        "ready={ready} surface_size={surface_size} all_targets_ok={all_targets_ok} "
        "callback_called={callback_called} av_count={av}".format(
            ready=bool(
                summary["marker_counts"]["CASTLEOV_MULTI_SURFDUMP_READY"]
                or summary["marker_counts"]["SURFDUMP_READY"]
            ),
            surface_size=summary["last_ready"].get("size"),
            all_targets_ok=summary["all_targets_ok"],
            callback_called=summary["callback_called"],
            av=summary["av_count"],
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")

    if args.require_ready and not (
        summary["marker_counts"]["CASTLEOV_MULTI_SURFDUMP_READY"]
        or summary["marker_counts"]["SURFDUMP_READY"]
    ):
        print("required surface-ready marker was not observed", file=sys.stderr)
        return 2
    if args.require_800x600 and summary["last_ready"].get("size") != [800, 600]:
        print("required 800x600 ready surface was not observed", file=sys.stderr)
        return 2
    if args.require_all_targets and not summary["all_targets_ok"]:
        print("not all overview hit targets were proven", file=sys.stderr)
        return 2
    if args.forbid_callback and summary["callback_called"]:
        print("descriptor callback was entered", file=sys.stderr)
        return 2
    if summary["av_count"]:
        print("access violation rows were observed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

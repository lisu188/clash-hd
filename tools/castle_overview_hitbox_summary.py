#!/usr/bin/env python3
"""Summarize Clash95 full castle overview centered hitbox CDB probes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "CASTLEOV_HITBOX_NATIVE_TRANSFORM_SET",
    "CASTLEOV_HITBOX_DISPLAYED_HITTEST_BEGIN",
    "CASTLEOV_HITBOX_CALLBACK_SUPPRESSED",
    "CASTLEOV_HITBOX_SURFDUMP_READY",
    "CASTLEOV_HITBOX_CLICK_GATE_OK",
    "CASTLEOV_HITBOX_INVOKE_PLAYGAME",
    "CASTLEOV_HITBOX_SCREEN_ENTRY",
    "CASTLEOV_HITBOX_OVERVIEW_POST_DRAW",
    "CASTLEOV_HITBOX_DISPLAYED_SET",
    "CASTLEOV_HITBOX_DISPLAYED_RESULT",
    "CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK",
    "CASTLEOV_HITBOX_NATIVE_RESULT",
    "CASTLEOV_HITBOX_NATIVE_MISS",
    "CASTLEOV_HITBOX_DESCRIPTOR_INSTALL",
    "CASTLEOV_HITBOX_CLICK_STATE",
    "CASTLEOV_HITBOX_CLICK_GATE",
    "CASTLEOV_HITBOX_CALLBACK_CALL",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
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
    expected_command: int = 0x86,
    expected_callback: int = 0x0044FE70,
    expected_hit: int = 0xF8,
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

    displayed_results = [
        row for row in rows if row["marker"] == "CASTLEOV_HITBOX_DISPLAYED_RESULT"
    ]
    native_results = [
        row for row in rows if row["marker"] == "CASTLEOV_HITBOX_NATIVE_RESULT"
    ]
    descriptors = [
        row for row in rows if row["marker"] == "CASTLEOV_HITBOX_DESCRIPTOR_INSTALL"
    ]
    click_gates = [
        row for row in rows if row["marker"] == "CASTLEOV_HITBOX_CLICK_GATE"
    ]
    click_gate_ok_rows = [
        row for row in rows if row["marker"] == "CASTLEOV_HITBOX_CLICK_GATE_OK"
    ]
    callback_rows = [
        row for row in rows if row["marker"] == "CASTLEOV_HITBOX_CALLBACK_CALL"
    ]
    ready_rows = [
        row
        for row in rows
        if row["marker"] in {"CASTLEOV_HITBOX_SURFDUMP_READY", "SURFDUMP_READY"}
    ]
    overview_post_rows = [
        row for row in rows if row["marker"] == "CASTLEOV_HITBOX_OVERVIEW_POST_DRAW"
    ]

    descriptor_ok = any(
        row["values"].get("command") == expected_command
        and row["values"].get("callback") == expected_callback
        for row in descriptors
    )
    native_hit_ok = any(
        row["values"].get("raw_hit") == expected_hit for row in native_results
    )
    displayed_hit_ok = any(
        row["values"].get("raw_hit") == expected_hit for row in displayed_results
    )
    click_gate_ok = any(
        row["values"].get("command") == expected_command
        and row["values"].get("callback") == expected_callback
        and row["values"].get("gate") == 1
        for row in click_gates + click_gate_ok_rows
    )
    callback_suppressed = bool(marker_counts["CASTLEOV_HITBOX_CALLBACK_SUPPRESSED"])
    callback_called = bool(callback_rows)
    last_ready = ready_rows[-1]["values"] if ready_rows else {}
    last_post = overview_post_rows[-1]["values"] if overview_post_rows else {}

    classification: list[str] = []
    if marker_counts["CASTLEOV_HITBOX_DISPLAYED_SET"]:
        classification.append("displayed coordinate 371,107 was installed")
    else:
        classification.append("displayed coordinate was not installed")
    if displayed_results:
        displayed_hit = displayed_results[-1]["values"].get("raw_hit")
        if displayed_hit == expected_hit:
            classification.append("displayed coordinate hit the target overview command")
        else:
            classification.append(
                f"displayed coordinate hit raw id {displayed_hit}, not {expected_hit}"
            )
    else:
        classification.append("displayed-coordinate result was not observed")
    if marker_counts["CASTLEOV_HITBOX_NATIVE_TRANSFORM_SET"]:
        classification.append("debugger-side native transform 371,107 -> 291,47 was installed")
    else:
        classification.append("debugger-side native transform was not installed")
    if native_hit_ok:
        classification.append("native coordinate returned target raw hit 0xF8")
    else:
        classification.append("native coordinate did not prove target raw hit 0xF8")
    if marker_counts["CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK"]:
        classification.append("displayed coordinate reached the target through the binary input wrapper")
    if descriptor_ok:
        classification.append(
            f"descriptor command 0x{expected_command:02X} callback 0x{expected_callback:08X} was installed"
        )
    else:
        classification.append(
            f"descriptor command 0x{expected_command:02X} callback 0x{expected_callback:08X} was not installed"
        )
    if click_gate_ok:
        classification.append("stock click gate returned 1 for the target descriptor")
    else:
        classification.append("stock click gate did not prove the target descriptor")
    if callback_suppressed:
        classification.append("target callback was suppressed after gate proof")
    if callback_called:
        classification.append("descriptor callback was entered")
    if ready_rows:
        classification.append("surface dump reached ready state")
    else:
        classification.append("surface dump did not reach ready state")
    if av_rows:
        classification.append("AV observed")

    return {
        "log": str(path),
        "expected_command": expected_command,
        "expected_callback": expected_callback,
        "expected_hit": expected_hit,
        "marker_counts": marker_counts,
        "row_count": len(rows),
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "displayed_result": displayed_results[-1]["values"] if displayed_results else None,
        "native_result": native_results[-1]["values"] if native_results else None,
        "descriptor_ok": descriptor_ok,
        "displayed_hit_ok": displayed_hit_ok,
        "native_hit_ok": native_hit_ok,
        "click_gate_ok": click_gate_ok,
        "callback_suppressed": callback_suppressed,
        "callback_called": callback_called,
        "last_descriptor": descriptors[-1]["values"] if descriptors else None,
        "last_click_gate": click_gates[-1]["values"] if click_gates else None,
        "last_ready": last_ready,
        "last_overview_post_draw": last_post,
        "classification": classification,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], path: Path, screenshot: str | None) -> None:
    lines = [
        "# Castle Overview Centered Hitbox Probe",
        "",
        f"- Log: `{summary['log']}`",
        f"- Expected command: `0x{summary['expected_command']:02X}`",
        f"- Expected callback: `0x{summary['expected_callback']:08X}`",
        f"- Expected raw hit: `{summary['expected_hit']}`",
        f"- Rows parsed: {summary['row_count']}",
        f"- Access violations: {summary['av_count']}",
        f"- Displayed result: `{summary['displayed_result']}`",
        f"- Native result: `{summary['native_result']}`",
        f"- Descriptor ok: {summary['descriptor_ok']}",
        f"- Displayed hit ok: {summary['displayed_hit_ok']}",
        f"- Native hit ok: {summary['native_hit_ok']}",
        f"- Click gate ok: {summary['click_gate_ok']}",
        f"- Callback suppressed: {summary['callback_suppressed']}",
        f"- Callback called: {summary['callback_called']}",
        f"- Ready surface size: `{summary['last_ready'].get('size')}`",
        "",
        "## Classification",
        "",
    ]
    lines += [f"- {item}" for item in summary["classification"]]
    if screenshot:
        lines += ["", "## Screenshot", "", f"![castle overview centered hitbox]({screenshot})"]
    lines += ["", "## Key Rows", ""]
    for row in summary["rows"][-18:]:
        lines.append(f"- line {row['line']}: `{row['text']}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--expect-command", default="0x86")
    parser.add_argument("--expect-callback", default="0x0044fe70")
    parser.add_argument("--expect-hit", default="0xf8")
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--screenshot")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-800x600", action="store_true")
    parser.add_argument("--require-displayed-hit", action="store_true")
    parser.add_argument("--require-native-hit", action="store_true")
    parser.add_argument("--require-descriptor", action="store_true")
    parser.add_argument("--require-click-gate", action="store_true")
    parser.add_argument("--require-callback-suppressed", action="store_true")
    parser.add_argument("--forbid-callback", action="store_true")
    args = parser.parse_args()

    summary = parse_log(
        args.log,
        expected_command=int(args.expect_command, 0),
        expected_callback=int(args.expect_callback, 0),
        expected_hit=int(args.expect_hit, 0),
    )
    if args.screenshot:
        summary["screenshot"] = args.screenshot
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md, args.screenshot)

    print(
        "ready={ready} surface_size={surface_size} displayed_hit_ok={displayed_hit} "
        "native_hit_ok={native_hit} "
        "descriptor_ok={descriptor} click_gate_ok={gate} callback_suppressed={suppressed} "
        "callback_called={callback_called} av_count={av}".format(
            ready=bool(
                summary["marker_counts"]["CASTLEOV_HITBOX_SURFDUMP_READY"]
                or summary["marker_counts"]["SURFDUMP_READY"]
            ),
            surface_size=summary["last_ready"].get("size"),
            displayed_hit=summary["displayed_hit_ok"],
            native_hit=summary["native_hit_ok"],
            descriptor=summary["descriptor_ok"],
            gate=summary["click_gate_ok"],
            suppressed=summary["callback_suppressed"],
            callback_called=summary["callback_called"],
            av=summary["av_count"],
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")

    if args.require_ready and not (
        summary["marker_counts"]["CASTLEOV_HITBOX_SURFDUMP_READY"]
        or summary["marker_counts"]["SURFDUMP_READY"]
    ):
        print("required surface-ready marker was not observed", file=sys.stderr)
        return 2
    if args.require_800x600 and summary["last_ready"].get("size") != [800, 600]:
        print("required 800x600 ready surface was not observed", file=sys.stderr)
        return 2
    if args.require_displayed_hit and not summary["displayed_hit_ok"]:
        print("required displayed-coordinate hit proof was not observed", file=sys.stderr)
        return 2
    if args.require_native_hit and not summary["native_hit_ok"]:
        print("required native hit proof was not observed", file=sys.stderr)
        return 2
    if args.require_descriptor and not summary["descriptor_ok"]:
        print("required descriptor was not observed", file=sys.stderr)
        return 2
    if args.require_click_gate and not summary["click_gate_ok"]:
        print("required click gate proof was not observed", file=sys.stderr)
        return 2
    if args.require_callback_suppressed and not summary["callback_suppressed"]:
        print("required callback suppression marker was not observed", file=sys.stderr)
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

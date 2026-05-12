#!/usr/bin/env python3
"""Gate a full castle overview CDB surface-dump run.

This combines the castle descriptor catalog, the surface size reported by CDB,
and the 800x600 centered-UI geometry check into one compact pass/fail report.
It is intended for the full castle overview path around 00422180/00422020,
not for the already proven barracks-only centered action probes.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import castle_barracks_action_click_summary
import castle_interior_catalog_summary
import castle_ui_center_geometry


DEFAULT_COMMANDS = (0x63, 0x86, 0x87, 0x99, 0x9C, 0x9F, 0xA6)


def command_label(command: int) -> str:
    return f"0x{command:02X}"


def safe_repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def build_gate(
    run_dir: Path,
    expected_commands: tuple[int, ...],
    threshold: int,
    max_echo_percent: float,
    barracks_run: Path | None = None,
) -> dict[str, Any]:
    log_path = run_dir / "cdb-surface-dump.log"
    png_path = run_dir / "surface.png"
    failures: list[str] = []

    if log_path.exists():
        catalog = castle_interior_catalog_summary.parse_log(log_path)
    else:
        catalog = {
            "log": str(log_path),
            "marker_counts": {},
            "av_count": 0,
            "commands": [],
            "commands_hex": [],
            "last_surface": {},
            "classification": ["catalog log was not found"],
        }
        failures.append(f"missing catalog log: {log_path}")

    geometry = None
    if png_path.exists():
        geometry = castle_ui_center_geometry.analyze(
            png_path,
            threshold=threshold,
            max_echo_percent=max_echo_percent,
        )
    else:
        failures.append(f"missing surface PNG: {png_path}")

    marker_counts = catalog.get("marker_counts", {})
    ready = bool(
        marker_counts.get("CASTLECAT_SURFDUMP_READY")
        or marker_counts.get("SURFDUMP_READY")
    )
    if not ready:
        failures.append("castle catalog surface-ready marker was not observed")

    if catalog.get("av_count"):
        failures.append("access violation rows were observed")

    overview_post_draw = catalog.get("last_overview_post_draw", {})
    if not marker_counts.get("CASTLECAT_OVERVIEW_POST_DRAW"):
        failures.append("overview post-draw marker was not observed")
    if overview_post_draw.get("main_size") != [800, 600]:
        failures.append(
            "expected overview post-draw main surface size [800, 600], got "
            f"{overview_post_draw.get('main_size')}"
        )

    observed_commands = set(catalog.get("commands") or [])
    missing_commands = [
        command for command in expected_commands if command not in observed_commands
    ]
    if missing_commands:
        failures.append(
            "missing expected castle descriptor commands: "
            + ", ".join(command_label(command) for command in missing_commands)
        )

    surface_size = catalog.get("last_surface", {}).get("size")
    if surface_size != [800, 600]:
        failures.append(f"expected catalog surface size [800, 600], got {surface_size}")

    centered_gate = bool(geometry and geometry.get("gate", {}).get("passed"))
    if not centered_gate:
        failures.append("centered 800x600 geometry gate failed")

    barracks_baseline = None
    if barracks_run is not None:
        barracks_baseline = build_barracks_baseline(
            barracks_run,
            threshold=threshold,
            max_echo_percent=max_echo_percent,
        )
        if not barracks_baseline["passed"]:
            failures.append(
                "barracks baseline regression: "
                + "; ".join(barracks_baseline["failures"])
            )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "run_dir": str(run_dir),
        "log": str(log_path),
        "screenshot": str(png_path) if png_path.exists() else None,
        "passed": not failures,
        "failures": failures,
        "expected_commands": [command_label(command) for command in expected_commands],
        "catalog": {
            "ready": ready,
            "av_count": catalog.get("av_count", 0),
            "commands": catalog.get("commands_hex", []),
            "descriptors": catalog.get("descriptors", []),
            "last_surface": catalog.get("last_surface", {}),
            "last_overview_post_draw": overview_post_draw,
            "classification": catalog.get("classification", []),
        },
        "geometry": geometry,
        "barracks_baseline": barracks_baseline,
    }


def build_barracks_baseline(
    run_dir: Path,
    threshold: int,
    max_echo_percent: float,
) -> dict[str, Any]:
    log_path = run_dir / "cdb-surface-dump.log"
    png_path = run_dir / "surface.png"
    failures: list[str] = []

    action = None
    if log_path.exists():
        action = castle_barracks_action_click_summary.parse_log(
            log_path,
            expected_desc=0x005151CF,
            expected_callback=0x004356C0,
        )
    else:
        failures.append(f"missing barracks action log: {log_path}")

    geometry = None
    if png_path.exists():
        geometry = castle_ui_center_geometry.analyze(
            png_path,
            threshold=threshold,
            max_echo_percent=max_echo_percent,
        )
    else:
        failures.append(f"missing barracks surface PNG: {png_path}")

    ready = bool(
        action
        and (
            action["marker_counts"].get("APBARRACKS_SURFDUMP_READY")
            or action["marker_counts"].get("SURFDUMP_READY")
        )
    )
    if action:
        if not ready:
            failures.append("barracks surface-ready marker was not observed")
        if action.get("av_count"):
            failures.append("barracks AV rows were observed")
        if not action.get("descriptor_click_ok"):
            failures.append("barracks selected-action descriptor did not resolve")
        if not action.get("controlled_4356c0_ok"):
            failures.append("barracks controlled 004356c0 stop was not observed")

    if not (geometry and geometry.get("gate", {}).get("passed")):
        failures.append("barracks centered geometry gate failed")

    return {
        "run_dir": str(run_dir),
        "passed": not failures,
        "failures": failures,
        "action": {
            "ready": ready,
            "descriptor_click_ok": bool(action and action.get("descriptor_click_ok")),
            "controlled_4356c0_ok": bool(action and action.get("controlled_4356c0_ok")),
            "av_count": action.get("av_count", 0) if action else None,
        },
        "geometry": geometry,
    }


def write_markdown(path: Path, gate: dict[str, Any]) -> None:
    catalog = gate["catalog"]
    geometry = gate.get("geometry") or {}
    geometry_gate = geometry.get("gate", {})
    barracks_baseline = gate.get("barracks_baseline")
    screenshot = gate.get("screenshot")
    lines = [
        "# Castle Overview Gate",
        "",
        f"- Overall: {'PASS' if gate['passed'] else 'FAIL'}",
        f"- Generated: `{gate['generated_at']}`",
        f"- Run: `{safe_repo_relative(Path(gate['run_dir']))}`",
        f"- Surface ready: {catalog['ready']}",
        f"- Surface size: `{catalog['last_surface'].get('size')}`",
        f"- Catalog commands: {', '.join(catalog['commands']) or 'none'}",
        f"- Expected commands: {', '.join(gate['expected_commands'])}",
        f"- Access violations: {catalog['av_count']}",
        f"- Overview post-draw surface: `{catalog['last_overview_post_draw'].get('main_size')}`",
        f"- Centered geometry: {'PASS' if geometry_gate.get('passed') else 'FAIL'}",
        "",
        "## Geometry",
        "",
        f"- Image: `{geometry.get('image', {}).get('width')}x{geometry.get('image', {}).get('height')}`",
        f"- Centered nonblack: `{geometry_gate.get('centered_nonblack_percent')}`",
        f"- Max margin nonblack: `{geometry_gate.get('max_margin_nonblack_percent')}`",
        "",
    ]
    if gate["failures"]:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in gate["failures"])
        lines.append("")
    if catalog["classification"]:
        lines.extend(["## Classification", ""])
        lines.extend(f"- {item}" for item in catalog["classification"])
        lines.append("")
    if barracks_baseline:
        barracks_geometry_gate = (barracks_baseline.get("geometry") or {}).get("gate", {})
        lines.extend(
            [
                "## Barracks Baseline",
                "",
                f"- Run: `{safe_repo_relative(Path(barracks_baseline['run_dir']))}`",
                f"- Overall: {'PASS' if barracks_baseline['passed'] else 'FAIL'}",
                f"- Descriptor click: {barracks_baseline['action']['descriptor_click_ok']}",
                f"- Controlled 004356c0 stop: {barracks_baseline['action']['controlled_4356c0_ok']}",
                f"- Centered geometry: {'PASS' if barracks_geometry_gate.get('passed') else 'FAIL'}",
                "",
            ]
        )
    if screenshot:
        lines.extend(["## Screenshot", "", f"![castle overview surface]({Path(screenshot).resolve()})", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_command(value: str) -> int:
    return int(value, 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--expect-command", type=parse_command, action="append")
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--max-echo-percent", type=float, default=25.0)
    parser.add_argument("--barracks-run", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expected_commands = tuple(args.expect_command or DEFAULT_COMMANDS)
    gate = build_gate(
        run_dir=args.run_dir,
        expected_commands=expected_commands,
        threshold=args.threshold,
        max_echo_percent=args.max_echo_percent,
        barracks_run=args.barracks_run,
    )

    print(f"overall: {'PASS' if gate['passed'] else 'FAIL'}")
    print(f"run: {gate['run_dir']}")
    print(f"catalog-ready: {gate['catalog']['ready']}")
    print(f"surface-size: {gate['catalog']['last_surface'].get('size')}")
    print(f"overview-post-draw-size: {gate['catalog']['last_overview_post_draw'].get('main_size')}")
    print(f"commands: {','.join(gate['catalog']['commands']) or 'none'}")
    geometry_gate = (gate.get("geometry") or {}).get("gate", {})
    print(f"centered-geometry: {'PASS' if geometry_gate.get('passed') else 'FAIL'}")
    if gate["failures"]:
        print("failures:")
        for failure in gate["failures"]:
            print(f"  - {failure}")

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, gate)
    if args.require_pass and not gate["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

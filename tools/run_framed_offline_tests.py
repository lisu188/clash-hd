#!/usr/bin/env python3
"""Run source-bound framed-renderer fixtures without claiming game validation."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tempfile
import time
import unittest
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = "tools/build_framed_candidate.py"
SUITES = (
    "test_action_bar_surface_audit",
    "test_build_framed_candidate",
    "test_build_partial_tile_candidate",
    "test_four_sided_frame",
    "test_four_sided_frame_x86",
    "test_frame_surface_audit",
    "test_framed_full_paint",
    "test_framed_input",
    "test_framed_minimap",
    "test_framed_minimap_integration",
    "test_framed_partial_tile",
    "test_framed_presentation",
    "test_framed_recipe",
    "test_framed_viewport",
    "test_initial_map_candidate",
    "test_initial_map_paint",
    "test_initial_map_paint_trace",
    "test_map_tile_coverage",
    "test_partial_tile_clip",
    "test_partial_tile_hooks",
    "test_partial_tile_trace_probe",
    "test_pe_extension",
    "test_render_cdb_surface_probe",
    "test_framed_modal_canvas",
    "test_pe_modal_extension",
    "test_build_framed_modal_candidate",
    "test_framed_army_composition",
    "test_framed_army_draw",
    "test_framed_army_input",
    "test_framed_army_viewport",
    "test_pe_army_extension",
    "test_build_framed_army_candidate",
    "test_framed_modal_slots",
    "test_pe_modal_slots_extension",
    "test_build_framed_modal_slots_candidate",
    "test_complete_hd_main_probe",
    "test_framed_gameplay_evidence",
    "test_modal_slots_barracks_capture",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or "\\" in name:
        raise ValueError("source path must be a relative POSIX path")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != name or path.suffix != ".py":
        raise ValueError(f"invalid source path: {name}")
    resolved = (root / name).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"source escapes repository: {name}")
    return resolved


def source_preflight(root: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    try:
        raw = source_path(root, BUILDER).read_bytes()
        names = ("PINNED_SOURCES", "MINIMAP_SOURCE", "MINIMAP_SOURCE_SHA256")
        values = {}
        for node in ast.parse(raw).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in names:
                        if target.id in values:
                            raise ValueError(f"duplicate pin declaration: {target.id}")
                        values[target.id] = ast.literal_eval(node.value)
        pins = values["PINNED_SOURCES"]
        if not isinstance(pins, dict) or not pins:
            raise ValueError("PINNED_SOURCES must be a nonempty literal mapping")
        pins = dict(pins)
        minimap = values["MINIMAP_SOURCE"]
        if minimap in pins and pins[minimap] != values["MINIMAP_SOURCE_SHA256"]:
            raise ValueError("conflicting minimap source pins")
        pins[minimap] = values["MINIMAP_SOURCE_SHA256"]
        for name, expected in sorted(pins.items()):
            if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
                raise ValueError(f"invalid SHA-256 pin: {name}")
            try:
                actual = digest(source_path(root, name).read_bytes())
                checks[name] = {"expected_sha256": expected, "actual_sha256": actual, "passed": actual == expected}
            except (OSError, ValueError) as exc:
                checks[name] = {"expected_sha256": expected, "passed": False, "error": str(exc)}
        return {"passed": all(row["passed"] for row in checks.values()),
                "builder_sha256": digest(raw), "checks": checks}
    except (OSError, ValueError, SyntaxError, KeyError, TypeError) as exc:
        return {"passed": False, "checks": checks, "error": str(exc)}


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.successful_tests: list[str] = []

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self.successful_tests.append(test.id())


def run_worker(name: str, result_path: Path) -> int:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tools"))
    suite = unittest.defaultTestLoader.loadTestsFromName(name)
    discovered = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    status = "passed" if result.wasSuccessful() and discovered else "failed"
    if status == "passed" and not result.successful_tests:
        status = "incomplete" if result.expectedFailures else "skipped"
    record = {
        "suite": name, "status": status, "discovered": discovered,
        "tests_run": result.testsRun, "successful": result.successful_tests,
        "skipped": [{"test": test.id(), "reason": reason} for test, reason in result.skipped],
        "expected_failures": [test.id() for test, _ in result.expectedFailures],
        "unexpected_successes": [test.id() for test in result.unexpectedSuccesses],
        "failures": [{"test": test.id(), "traceback": text} for test, text in result.failures],
        "errors": [{"test": test.id(), "traceback": text} for test, text in result.errors],
    }
    result_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return int(status == "failed")


def validate_record(record: Any, name: str) -> None:
    if not isinstance(record, dict) or record.get("suite") != name:
        raise ValueError("worker result does not match the requested suite")
    for key in ("discovered", "tests_run"):
        if type(record.get(key)) is not int or record[key] < 0:
            raise ValueError(f"invalid worker count: {key}")
    for key in ("successful", "skipped", "expected_failures", "unexpected_successes", "failures", "errors"):
        if not isinstance(record.get(key), list):
            raise ValueError(f"invalid worker outcome list: {key}")
    if not len(record["successful"]) <= record["tests_run"] <= record["discovered"]:
        raise ValueError("inconsistent worker counts")
    failed = not record["discovered"] or any(record[key] for key in ("failures", "errors", "unexpected_successes"))
    expected = "failed" if failed else "passed"
    if expected == "passed" and not record["successful"]:
        expected = "incomplete" if record["expected_failures"] else "skipped"
    if record.get("status") != expected:
        raise ValueError("worker status contradicts its outcomes")


def run_suite(root: Path, name: str, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    record: dict[str, Any] = {"suite": name, "status": "failed"}
    with tempfile.TemporaryDirectory(prefix="clash-hd-offline-") as temporary:
        result_path = Path(temporary) / "result.json"
        log_path = Path(temporary) / "output.log"
        try:
            with log_path.open("wb") as log:
                process = subprocess.run(
                    [sys.executable, "-B", str(root / "tools" / Path(__file__).name),
                     "--worker", name, "--worker-result", str(result_path)],
                    cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
                )
            loaded = json.loads(result_path.read_text(encoding="utf-8"))
            validate_record(loaded, name)
            record = loaded
            record["returncode"] = process.returncode
            if process.returncode != 0:
                record["status"] = "failed"
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            record["error"] = str(exc)
            record["timed_out"] = isinstance(exc, subprocess.TimeoutExpired)
        if record["status"] == "failed" and log_path.exists():
            with log_path.open("rb") as log:
                log.seek(max(0, log_path.stat().st_size - 12000))
                record["output_tail"] = log.read().decode("utf-8", errors="replace")
    record["seconds"] = round(time.monotonic() - started, 3)
    return record


def summarize(preflight: dict[str, Any], records: list[dict[str, Any]], selected: tuple[str, ...]) -> dict[str, Any]:
    successful = sum(len(row.get("successful", [])) for row in records)
    passed = (preflight["passed"] and len(records) == len(selected) and successful > 0
              and all(row.get("status") in ("passed", "skipped", "incomplete") for row in records))
    complete = passed and all(
        row.get("status") == "passed" and not row.get("skipped") and not row.get("expected_failures")
        and len(row.get("successful", [])) == row.get("discovered") for row in records)
    return {
        "schema": 1, "evidence_class": "repo_only_framed_fixtures",
        "offline_passed": bool(passed), "selected_coverage_complete": bool(complete),
        "full_suite_selected": selected == SUITES,
        "successful_tests": successful,
        "skipped_records": sum(len(row.get("skipped", [])) for row in records),
        "expected_failure_records": sum(len(row.get("expected_failures", [])) for row in records),
        "python": platform.python_version(), "platform": platform.platform(),
        "source_preflight": preflight, "selected_suites": list(selected), "suites": records,
        "game_runtime_executed": False, "manual_input_proof": False, "promotion_ready": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", action="append", choices=SUITES)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--worker", choices=SUITES, help=argparse.SUPPRESS)
    parser.add_argument("--worker-result", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be a finite positive number")
    if args.worker:
        if args.worker_result is None:
            parser.error("worker-result is required for a worker")
        return run_worker(args.worker, args.worker_result)
    if args.worker_result is not None:
        parser.error("worker-result requires worker")
    if args.report_json is not None and args.report_json.suffix.lower() != ".json":
        parser.error("report-json must name a JSON file")
    selected = tuple(dict.fromkeys(args.suite)) if args.suite else SUITES
    preflight = source_preflight(ROOT)
    records = []
    if preflight["passed"]:
        for name in selected:
            row = run_suite(ROOT, name, args.timeout)
            records.append(row)
            print(f"{name}: {row['status']} ({len(row.get('successful', []))} successful, "
                  f"{len(row.get('skipped', []))} skip records)", file=sys.stderr, flush=True)
    report = summarize(preflight, records, selected)
    text = json.dumps(report, indent=2) + "\n"
    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.report_json.parent,
                                         prefix=".framed-report-", suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(text)
        try:
            os.replace(temporary, args.report_json)
        finally:
            temporary.unlink(missing_ok=True)
    print(text, end="")
    return int(not report["offline_passed"] or (args.require_complete and not report["selected_coverage_complete"]))


if __name__ == "__main__":
    raise SystemExit(main())

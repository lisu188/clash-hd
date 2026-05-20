#!/usr/bin/env python3
"""Run the repo-only Clash95 battle UI evidence matrix.

This matrix combines the current focused battle UI summaries. It checks
existing hidden-desktop CDB/proxy artifacts only; it does not launch Clash95,
CDB, wrappers, PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter"
)
EXPECTED_BASE_SHA256 = "500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE"
EXPECTED_BATTLE_SHA256 = "F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF"

DEFAULT_FORCE_ENTRY_JSON = Path("captures/battle-ui-force-entry-current.json")
DEFAULT_COMMAND_HIT_JSON = Path("captures/battle-ui-command-hit-current.json")
DEFAULT_COMMAND_CALLBACK_JSON = Path("captures/battle-ui-command-callback-current.json")
DEFAULT_ENABLED_CALLBACK_JSON = Path("captures/battle-ui-command-enabled-callback-current.json")
DEFAULT_GRID_HIT_JSON = Path("captures/battle-ui-grid-hit-current.json")
DEFAULT_MODAL_CLASSIFIED_JSON = Path("captures/battle-ui-modal-classified-current.json")
DEFAULT_PATCH_STAGE_JSON = Path("captures/patch-stage-battlecenter-current.json")
DEFAULT_STABLE_SMOKE_JSON = Path("captures/hd-map-smoke-current.json")
DEFAULT_MATRIX_JSON = Path("captures/battle-ui-evidence-current.json")
DEFAULT_MATRIX_MD = Path("captures/battle-ui-evidence-current.md")

SUMMARY_NAMES = (
    "force_entry",
    "command_hit",
    "command_callback",
    "enabled_callback",
    "grid_hit",
    "modal_classified",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def maybe_load_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.exists():
        return None, [f"missing JSON: {path}"]
    try:
        return load_json(path), []
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON {path}: {exc}"]


def under_clash_tests(path_text: str | None) -> bool:
    if not path_text:
        return False
    return path_text.replace("/", "\\").lower().startswith("c:\\clashtests\\")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def markdown_image_ref(screenshot: str, markdown_path: Path) -> str:
    screenshot_path = Path(screenshot)
    try:
        return screenshot_path.resolve().relative_to(markdown_path.parent.resolve()).as_posix()
    except (OSError, ValueError):
        return screenshot


def row_values(summary: dict[str, Any], key: str) -> dict[str, Any]:
    row = summary.get(key) or {}
    return row.get("values") or {}


def common_summary_failures(name: str, summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if summary.get("battle_ready") is not True:
        failures.append(f"{name}: battle_ready is not true")
    if summary.get("surface_size") != [800, 600]:
        failures.append(f"{name}: surface_size is {summary.get('surface_size')}")
    if summary.get("visual_mode") != "centered-native-640x480":
        failures.append(f"{name}: visual_mode is {summary.get('visual_mode')}")
    if summary.get("centered_wrapper_seen") is not True:
        failures.append(f"{name}: centered wrapper was not observed")
    if int(summary.get("av_count") or 0):
        failures.append(f"{name}: AV rows were observed: {summary.get('av_count')}")
    if summary.get("hidden_desktop") is not True:
        failures.append(f"{name}: hidden_desktop is not true")
    if not under_clash_tests(summary.get("candidate")):
        failures.append(f"{name}: candidate is not under C:\\ClashTests: {summary.get('candidate')}")
    return failures


def feature_failures(name: str, summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if name == "force_entry":
        if summary.get("centered_offset") != [80, 60]:
            failures.append(f"{name}: centered offset is {summary.get('centered_offset')}")
    elif name == "command_hit":
        if summary.get("command_hit_ok") is not True:
            failures.append("command_hit: visual command hit is not proven")
        if summary.get("command_native_hit_ok") is not True:
            failures.append("command_hit: native command hit is not proven")
    elif name == "command_callback":
        if summary.get("command_callback_ok") is not True:
            failures.append("command_callback: callback entry is not proven")
        if summary.get("command_callback_result_ok") is not True:
            failures.append("command_callback: callback result is not proven")
        branch = row_values(summary, "last_command_callback_result").get("branch")
        if branch != "precondition-disabled":
            failures.append(f"command_callback: branch is {branch}, expected precondition-disabled")
    elif name == "enabled_callback":
        if summary.get("command_callback_ok") is not True:
            failures.append("enabled_callback: callback entry is not proven")
        if summary.get("command_callback_result_ok") is not True:
            failures.append("enabled_callback: callback result is not proven")
        if summary.get("command_render_begin_skip_seen") is not True:
            failures.append("enabled_callback: render-begin skip row is not proven")
        branch = row_values(summary, "last_command_callback_result").get("branch")
        if branch != "state2":
            failures.append(f"enabled_callback: branch is {branch}, expected state2")
    elif name == "grid_hit":
        if summary.get("grid_hit_ok") is not True:
            failures.append("grid_hit: grid hit is not proven")
        visual_cell = row_values(summary, "last_grid_result").get("cell")
        native_cell = row_values(summary, "last_grid_hit").get("cell")
        if visual_cell != [1, 1]:
            failures.append(f"grid_hit: visual result cell is {visual_cell}, expected [1, 1]")
        if native_cell != [0, 0]:
            failures.append(f"grid_hit: native hit cell is {native_cell}, expected [0, 0]")
    elif name == "modal_classified":
        if summary.get("modal_classified") is not True:
            failures.append("modal_classified: modal path was not classified")
        status = row_values(summary, "last_modal_classified").get("status")
        if status not in (None, "input_update_seen_no_modal"):
            failures.append(f"modal_classified: status is {status}")
    return failures


def patch_stage_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    if payload.get("stage") != EXPECTED_STAGE:
        failures.append(f"patch stage is {payload.get('stage')}, expected {EXPECTED_STAGE}")
    if str(payload.get("expected_base_sha256") or "").upper() != EXPECTED_BASE_SHA256:
        failures.append("patch-stage base SHA mismatch")
    status_counts = payload.get("status_counts") or {}
    if int(status_counts.get("original", 0) or 0):
        failures.append(f"patch-stage has original bytes: {status_counts.get('original')}")
    if int(status_counts.get("unexpected", 0) or 0):
        failures.append(f"patch-stage has unexpected bytes: {status_counts.get('unexpected')}")
    group = (payload.get("groups") or {}).get("battle-ui-center-present-wrapper") or {}
    if group.get("patched") != 2 or group.get("total") != 2:
        failures.append(f"battle present wrapper group is {group}, expected 2/2")
    if str(payload.get("exe_sha256") or "").upper() != EXPECTED_BATTLE_SHA256:
        failures.append("battle candidate SHA mismatch in patch-stage report")
    return {
        "passed": not failures,
        "path": str(path),
        "stage": payload.get("stage"),
        "candidate": payload.get("exe"),
        "candidate_sha256": payload.get("exe_sha256"),
        "status_counts": status_counts,
        "battle_group": group,
        "failures": failures,
    }


def stable_smoke_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    passed = bool(payload.get("passed") or payload.get("overall") == "PASS")
    if not passed:
        failures.append("stable HD-map smoke did not pass")
    return {
        "passed": not failures,
        "path": str(path),
        "candidate_sha256": payload.get("candidate_sha256")
        or (payload.get("patch_stage") or {}).get("sha256"),
        "failures": failures,
    }


def build_matrix(args: argparse.Namespace) -> dict[str, Any]:
    paths = {
        "force_entry": args.force_entry_json,
        "command_hit": args.command_hit_json,
        "command_callback": args.command_callback_json,
        "enabled_callback": args.enabled_callback_json,
        "grid_hit": args.grid_hit_json,
        "modal_classified": args.modal_classified_json,
    }
    summaries: dict[str, Any] = {}
    checks: dict[str, Any] = {}
    failures: list[str] = []

    for name in SUMMARY_NAMES:
        payload, load_failures = maybe_load_json(paths[name])
        if payload is None:
            checks[name] = {"passed": False, "path": str(paths[name]), "failures": load_failures}
            failures.extend(load_failures)
            continue
        check_failures = common_summary_failures(name, payload)
        check_failures.extend(feature_failures(name, payload))
        summaries[name] = payload
        checks[name] = {
            "passed": not check_failures,
            "path": str(paths[name]),
            "candidate_sha256": payload.get("candidate_sha256"),
            "screenshot": payload.get("screenshot"),
            "failures": check_failures,
        }
        failures.extend(check_failures)

    patch_stage = patch_stage_gate(args.patch_stage_json)
    stable_smoke = stable_smoke_gate(args.stable_smoke_json)
    checks["patch_stage"] = patch_stage
    checks["stable_smoke"] = stable_smoke
    failures.extend(f"patch_stage: {failure}" for failure in patch_stage["failures"])
    failures.extend(f"stable_smoke: {failure}" for failure in stable_smoke["failures"])

    candidate_values = {
        str(value).upper()
        for value in [patch_stage.get("candidate_sha256")]
        + [summary.get("candidate_sha256") for summary in summaries.values()]
        if value
    }
    if candidate_values != {EXPECTED_BATTLE_SHA256}:
        failures.append(f"battle candidate SHA values are {sorted(candidate_values)}")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows",
        "stage": EXPECTED_STAGE,
        "candidate_sha256": EXPECTED_BATTLE_SHA256 if not failures or EXPECTED_BATTLE_SHA256 in candidate_values else None,
        "promotion_status": "validation_stage_only",
        "stable_stage_should_change": False,
        "checks": checks,
        "key_evidence": {
            "centered_visual": summaries.get("force_entry", {}).get("visual_mode"),
            "command_hit_ok": summaries.get("command_hit", {}).get("command_hit_ok"),
            "command_native_hit_ok": summaries.get("command_hit", {}).get("command_native_hit_ok"),
            "command_callback_branch": row_values(summaries.get("command_callback", {}), "last_command_callback_result").get("branch"),
            "enabled_callback_branch": row_values(summaries.get("enabled_callback", {}), "last_command_callback_result").get("branch"),
            "grid_visual_cell": row_values(summaries.get("grid_hit", {}), "last_grid_result").get("cell"),
            "grid_native_cell": row_values(summaries.get("grid_hit", {}), "last_grid_hit").get("cell"),
            "modal_classified": summaries.get("modal_classified", {}).get("modal_classified"),
        },
        "failures": failures,
    }


def write_markdown(path: Path, matrix: dict[str, Any]) -> None:
    lines = [
        "# Battle UI Evidence Matrix",
        "",
        f"- Overall: {status_text(bool(matrix['passed']))}",
        f"- Generated: `{matrix['generated_at']}`",
        f"- Runtime policy: {matrix['runtime_policy']}",
        f"- Stage: `{matrix['stage']}`",
        f"- Candidate SHA-256: `{matrix.get('candidate_sha256')}`",
        f"- Promotion status: `{matrix['promotion_status']}`",
        f"- Stable stage should change: `{matrix['stable_stage_should_change']}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in matrix["checks"].items():
        lines.append(f"- {name}: {status_text(bool(check.get('passed')))}")
    lines.extend(["", "## Key Evidence", ""])
    for key, value in matrix["key_evidence"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Failures", ""])
    if matrix["failures"]:
        lines.extend(f"- {failure}" for failure in matrix["failures"])
    else:
        lines.append("- None")
    screenshots = [
        check.get("screenshot")
        for name, check in matrix["checks"].items()
        if name in SUMMARY_NAMES and check.get("screenshot")
    ]
    if screenshots:
        lines.extend(["", "## Screenshots", ""])
        for screenshot in screenshots:
            lines.append(f"![battle UI evidence]({markdown_image_ref(screenshot, path)})")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-entry-json", type=Path, default=DEFAULT_FORCE_ENTRY_JSON)
    parser.add_argument("--command-hit-json", type=Path, default=DEFAULT_COMMAND_HIT_JSON)
    parser.add_argument("--command-callback-json", type=Path, default=DEFAULT_COMMAND_CALLBACK_JSON)
    parser.add_argument("--enabled-callback-json", type=Path, default=DEFAULT_ENABLED_CALLBACK_JSON)
    parser.add_argument("--grid-hit-json", type=Path, default=DEFAULT_GRID_HIT_JSON)
    parser.add_argument("--modal-classified-json", type=Path, default=DEFAULT_MODAL_CLASSIFIED_JSON)
    parser.add_argument("--patch-stage-json", type=Path, default=DEFAULT_PATCH_STAGE_JSON)
    parser.add_argument("--stable-smoke-json", type=Path, default=DEFAULT_STABLE_SMOKE_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_MATRIX_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MATRIX_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matrix = build_matrix(args)
    print(f"overall: {status_text(bool(matrix['passed']))}")
    print(f"runtime-policy: {matrix['runtime_policy']}")
    print(f"promotion-status: {matrix['promotion_status']}")
    print(f"candidate-sha256: {matrix.get('candidate_sha256')}")
    print(f"failures: {len(matrix['failures'])}")
    for failure in matrix["failures"]:
        print(f"  - {failure}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, matrix)
    if args.require_pass and not matrix["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

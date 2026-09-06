#!/usr/bin/env python3
"""Evaluate new HD-layout evidence without modifying a stage or launching runtime.

The historical hd_layout_promotion_decision.py remains a separate diagnostic.
This additive evaluator rechecks raw evidence and can recommend component
eligibility; it neither promotes bytes nor declares the whole HD mod complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

import hd_layout_summary
import manual_directinput_checklist as manual
import patch_stage_report
import capture_tear_check
import hd_layout_visible_summary as visible
import hd_layout_asset_composition as asset_composition
import hd_layout_command_input_summary as command_parser


ROOT = Path(__file__).resolve().parents[1]
STABLE_STAGE = manual.CURRENT_STABLE_STAGE
REQUIRED_LAYOUT_GROUPS = {
    "terrain-tooltip-bottom-center", "selected-unit-command-panel-right-bottom",
    "frame-restore-bands",
}
RESOLUTION = "800x600"
RUNTIME_POLICY = "repo-only artifact and candidate-byte inspection; no runtime or promotion"


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def utc_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be text")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must include its timezone")
    return result.astimezone(timezone.utc)


def same_sha(first: Any, second: Any) -> bool:
    return (isinstance(first, str) and isinstance(second, str)
            and bool(manual.SHA256_RE.fullmatch(first))
            and first.upper() == second.upper())


def isolated_candidate(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    path = PureWindowsPath(value)
    return (path.is_absolute() and ".." not in path.parts
            and path.suffix.lower() == ".exe"
            and manual._is_same_or_under(value, manual.EXPECTED_CANDIDATE_ROOT))


def validate_candidate_origin(data: bytes, patches: list[Any], expected_original_sha: str) -> list[str]:
    """Undo selected bytes in memory and require the known original hash.

    This detects unrelated modifications outside the reported patch offsets;
    it never writes the reconstructed input or the candidate.
    """
    original = bytearray(data)
    for patch in patches:
        if len(patch.old) != len(patch.new):
            return ["candidate reconstruction requires equal-length patch definitions"]
        if data[patch.offset:patch.offset + len(patch.new)] != patch.new:
            return [f"candidate bytes differ at patch offset {patch.offset:#x}"]
        original[patch.offset:patch.offset + len(patch.old)] = patch.old
    if not same_sha(hashlib.sha256(original).hexdigest(), expected_original_sha):
        return ["candidate cannot reconstruct the exact known original SHA; unrelated bytes differ"]
    return []


def validate_byte_report(report: dict[str, Any], *, candidate_sha: str,
                         stage: str, resolution: str) -> list[str]:
    """Validate the complete byte report, not just its map-gate flag."""
    failures: list[str] = []
    if report.get("stage") != stage or report.get("resolution") != resolution:
        failures.append("byte report stage/resolution does not match command evidence")
    if not same_sha(report.get("exe_sha256"), candidate_sha):
        failures.append("byte report candidate SHA does not match command evidence")
    patcher = patch_stage_report.load_patcher()
    selected = patcher.STAGE_GROUPS.get(stage)
    if (stage == STABLE_STAGE or not stage.startswith(STABLE_STAGE + "-")
            or selected is None or not REQUIRED_LAYOUT_GROUPS.issubset(selected)):
        failures.append("stage is not a registered validation stage with all required layout/frame groups")
        return failures
    if patcher.DEFAULT_STAGE != STABLE_STAGE:
        failures.append("patcher default no longer matches the protected stable stage")
    if resolution != RESOLUTION:
        failures.append("HD-layout geometry/composition acceptance supports only 800x600")
        return failures
    expected = patcher.select_patches(stage)
    records = report.get("patches")
    if not isinstance(records, list) or len(records) != len(expected):
        failures.append("byte report does not contain every selected patch record")
        return failures
    for index, (record, patch) in enumerate(zip(records, expected)):
        if not isinstance(record, dict) or any((
            record.get("group") != patch.group,
            record.get("offset") != patch.offset,
            record.get("old") != patch_stage_report.spaced_hex(patch.old),
            record.get("new") != patch_stage_report.spaced_hex(patch.new),
            record.get("actual") != patch_stage_report.spaced_hex(patch.new),
            record.get("status") != "patched",
        )):
            failures.append(f"byte record {index} does not match the authoritative patch definition")
    if report.get("patch_count") != len(expected):
        failures.append("byte report patch count does not match the selected stage")
    if report.get("status_counts") != {"patched": len(expected)}:
        failures.append("byte report includes missing, original, or unexpected bytes")
    expected_base = patcher.EXPECTED_SHA256
    if not same_sha(report.get("expected_base_sha256"), expected_base):
        failures.append("byte report expected original SHA does not match patcher")
    if report.get("groups") != patch_stage_report.summarize_groups(records):
        failures.append("byte report group totals do not match its records")
    gate = patch_stage_report.current_hd_map_gate(report)
    if gate.get("passed") is not True or report.get("current_hd_map_gate") != gate:
        failures.append("complete HD map byte gate is not passing or was misreported")
    return failures


def validate_hidden(summary: dict[str, Any], run: dict[str, Any],
                    *, candidate_sha: str, stage: str) -> list[str]:
    failures: list[str] = []
    if run.get("Passed") is not True or run.get("Error"):
        failures.append("hidden geometry run did not pass")
    if (run.get("HiddenDesktop") is not True or run.get("AllowVisibleDesktop") is not False
            or run.get("LaunchMode") != "hidden-desktop"):
        failures.append("geometry run is not bound to the hidden-desktop evidence class")
    if run.get("Stage") != stage or not same_sha(run.get("CandidateSha256"), candidate_sha):
        failures.append("hidden geometry run candidate/stage does not match command evidence")
    if not isolated_candidate(run.get("CandidatePath")):
        failures.append("hidden geometry run does not identify an isolated candidate path")
    if not same_sha(run.get("InputSha256"), patch_stage_report.load_patcher().EXPECTED_SHA256):
        failures.append("hidden geometry run input SHA does not match the known original")
    if (run.get("Surface", {}).get("Width"), run.get("Surface", {}).get("Height")) != (800, 600):
        failures.append("hidden geometry run resolution does not match 800x600")
    if not isinstance(summary.get("log"), str) or not isinstance(run.get("Log"), str):
        return failures + ["hidden geometry source log is missing"]
    log = resolve_path(summary["log"])
    if log != resolve_path(run["Log"]):
        failures.append("hidden geometry summary and run refer to different logs")
    if not isinstance(run.get("RunDir"), str) or not log.is_relative_to(resolve_path(run.get("RunDir", ""))):
        failures.append("hidden geometry log is outside its recorded run directory")
    fresh = hd_layout_summary.summarize(log)
    for key in ("passed", "target_size", "redraw_clip_proved", "checks", "marker_counts"):
        if summary.get(key) != fresh.get(key):
            failures.append(f"hidden geometry {key} does not match its raw log")
    if fresh.get("passed") is not True or fresh.get("redraw_clip_proved") is not True:
        failures.append("raw hidden geometry does not prove every anchor and redraw clip")
    return failures


def validate_manual_proof(proof: dict[str, Any]) -> list[str]:
    failures = manual.validate_manual_proof_data(proof)
    items = proof.get("checked_items")
    if not isinstance(items, list):
        return failures
    ids = [item.get("id") for item in items if isinstance(item, dict)]
    if len(ids) != len(manual.REQUIRED_IDS) or set(ids) != set(manual.REQUIRED_IDS):
        failures.append("manual proof must contain exactly the five unique required targets")
    if isolated_candidate(proof.get("candidate_path")):
        primary = resolve_path(proof["candidate_path"])
        if (not isolated_candidate(str(primary)) or not primary.is_file()
                or not same_sha(sha256(primary), proof.get("executable_sha256"))
                or not any(same_sha(item.get("executable_sha256"), proof.get("executable_sha256"))
                           for item in items if isinstance(item, dict))):
            failures.append("manual proof primary candidate is not bound to its actual file and checked targets")
    # The existing assembler carries these per-target fields. Require actual
    # referenced files so a generic checklist or a bare pass flag is insufficient.
    for item in items:
        if not isinstance(item, dict):
            continue
        target = item.get("id", "unknown")
        if not isolated_candidate(item.get("candidate_path")):
            failures.append(f"manual target {target} lacks an isolated candidate path")
        if not manual.SHA256_RE.fullmatch(str(item.get("executable_sha256", ""))):
            failures.append(f"manual target {target} lacks a candidate SHA")
        elif isolated_candidate(item.get("candidate_path")):
            candidate = resolve_path(item["candidate_path"])
            if not isolated_candidate(str(candidate)):
                failures.append(f"manual target {target} resolved candidate is outside the isolated root")
            elif not candidate.is_file() or not same_sha(sha256(candidate), item["executable_sha256"]):
                failures.append(f"manual target {target} actual candidate SHA does not match")
            else:
                patcher = patch_stage_report.load_patcher()
                stage = item.get("stage")
                if stage not in patcher.STAGE_GROUPS:
                    failures.append(f"manual target {target} stage is not registered")
                else:
                    report = patch_stage_report.build_report(candidate, stage, RESOLUTION)
                    if report.get("status_counts") != {"patched": report.get("patch_count")}:
                        failures.append(f"manual target {target} candidate does not carry its declared stage bytes")
                    failures.extend(f"manual target {target}: {error}" for error in validate_candidate_origin(
                        candidate.read_bytes(), patcher.select_patches(stage), patcher.EXPECTED_SHA256))
        artifacts = item.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            failures.append(f"manual target {target} lacks raw observation artifacts")
        else:
            for artifact in artifacts:
                if not isinstance(artifact, str) or not resolve_path(artifact).is_file():
                    failures.append(f"manual target {target} raw artifact is missing: {artifact}")
    return failures


def validate_hygiene(hygiene: dict[str, Any], finished_at: str) -> list[str]:
    failures: list[str] = []
    if (hygiene.get("passed") is not True or type(hygiene.get("matching_process_count")) is not int
            or hygiene.get("matching_process_count") != 0 or hygiene.get("matching_processes") != []
            or type(hygiene.get("inspection_returncode")) is not int or hygiene.get("inspection_returncode") != 0
            or hygiene.get("inspection_error") or hygiene.get("failures")):
        failures.append("post-run process hygiene is not passing")
    if ("cdb.exe" not in hygiene.get("target_exact_names", [])
            or "clash95" not in hygiene.get("target_prefixes", [])):
        failures.append("process hygiene did not inspect the required process names")
    if utc_time(hygiene.get("generated_at")) < utc_time(finished_at):
        failures.append("process hygiene predates completion of the command-input run")
    return failures


def checked_reference(value: Any, label: str) -> Path:
    if not isinstance(value, dict) or not isinstance(value.get("path"), str):
        raise ValueError(f"{label} requires a path and SHA-256 reference")
    path = resolve_path(value["path"])
    if not path.is_file() or not same_sha(value.get("sha256"), sha256(path)):
        raise ValueError(f"{label} is missing or its raw SHA-256 does not match")
    return path


class RecipeImage:
    """Map numeric recipe coordinates onto authentic pixels; write no image."""

    width = 1200
    height = 900

    def __init__(self, source: Any) -> None:
        self.source = source

    def rgb_at(self, x: int, y: int) -> Any:
        return self.source.rgb_at(x * self.source.width // self.width,
                                  y * self.source.height // self.height)


def authentic_screen_frame(path: Path, sidecar: dict[str, Any], hwnd: str | None) -> bool:
    image = visible.read_png(path)
    size = (image.width, image.height)
    return (isinstance(hwnd, str) and hwnd.startswith("0x") and hwnd.lower() not in ("0x0", "0x00000000")
            and size in ((800, 600), (1200, 900))
            and size == (sidecar.get("Width"), sidecar.get("Height"))
            and same_sha(sha256(path), sidecar.get("Hash"))
            and sidecar.get("CaptureMode") == "screen"
            and sidecar.get("CenterWindowMatchesTarget") is True
            and visible._same_handle(hwnd, sidecar.get("TargetHwnd"),
                                     sidecar.get("CenterWindowHwnd"), sidecar.get("CenterRootHwnd")))


def composition_sources(command: dict) -> tuple[bytes, list[dict], dict, int]:
    """Recheck the immutable resource approved for this actual owned session."""
    receipt_path = checked_reference(command.get("session_receipt"), "command session receipt")
    receipt = read_object(receipt_path)
    plan_path = checked_reference(receipt.get("plan"), "command execution plan")
    if not same_sha(sha256(plan_path), command["identity"].get("execution_plan_sha256")):
        raise ValueError("composition asset plan differs from the approved execution plan")
    inventory = read_object(plan_path).get("assets", {})
    work = resolve_path(inventory.get("work_dir", ""))
    if work != resolve_path(command["identity"]["candidate_path"]).parent:
        raise ValueError("composition asset workspace differs from the executed candidate")
    records = inventory.get("files")
    if not isinstance(records, list):
        raise ValueError("composition source asset inventory is missing")
    records = [item for item in records if isinstance(item, dict)
               and str(item.get("relative_path", "")).lower() == "data/minimum.res"]
    if len(records) != 1:
        raise ValueError("composition requires exactly one approved DATA/minimum.res")
    resource = checked_reference(records[0], "approved minimum.res")
    if (resource != (work / "DATA/minimum.res").resolve()
            or type(records[0].get("size_bytes")) is not int
            or records[0]["size_bytes"] != resource.stat().st_size):
        raise ValueError("composition resource path or length differs from the approved asset")
    if any((work / "GFX" / name).exists() for name in ("map_butt.s32", "mouse.s32", "map.pal")):
        raise ValueError("loose layout asset overrides require a separately validated source profile")
    assets = asset_composition.decode_assets(resource.read_bytes())
    raw = checked_reference(command.get("raw_log"), "command raw log").read_bytes()
    rows, _, malformed = command_parser.parse_events(raw.decode("utf-8-sig"))
    if malformed:
        raise ValueError("composition input observations contain malformed native rows")
    boundary = receipt.get("click_observation_start_line")
    if type(boundary) is not int or boundary < 1:
        raise ValueError("composition requires the measured post-capture click boundary")
    return raw, rows, assets, boundary


def capture_state(sidecar: dict, phase: str, raw: bytes, rows: list[dict]) -> tuple[dict, int, int]:
    """Bind the actual capture interval to passive native state, including cursor."""
    references = []
    for key in ("InputObservationBefore", "InputObservationAfter"):
        ref = sidecar.get(key)
        if (not isinstance(ref, dict) or type(ref.get("line")) is not int
                or type(ref.get("prefix_bytes")) is not int
                or not 0 < ref["prefix_bytes"] <= len(raw)):
            raise ValueError("capture lacks a native input observation prefix reference")
        prefix = raw[:ref["prefix_bytes"]]
        if not prefix.endswith(b"\n") or not same_sha(hashlib.sha256(prefix).hexdigest(), ref.get("prefix_sha256")):
            raise ValueError("capture native input prefix SHA or complete-line boundary differs")
        line_count = len(prefix.decode("utf-8-sig").splitlines())
        descriptors = [row for row in rows if row["marker"] == "DESCRIPTOR" and row["line"] <= line_count]
        if not descriptors or descriptors[-1]["line"] != ref["line"]:
            raise ValueError("capture reference is not the latest native descriptor in its raw prefix")
        references.append(ref)
    before, after = references
    if after["line"] <= before["line"] or after["prefix_bytes"] <= before["prefix_bytes"]:
        raise ValueError("capture lacks a fresh native observation after its pixels were captured")
    interval = [row["values"] for row in rows if row["marker"] == "DESCRIPTOR"
                and before["line"] <= row["line"] <= after["line"]]
    state = interval[0]
    if any(value != state for value in interval):
        raise ValueError("native selection, state, or cursor changed across the capture interval")
    expected_state, meta, sprite = (2, 0x5196C8, 3) if phase == "map" else (6, 0x5196A0, 2)
    if ((state["desc"], state["x"], state["y"], state["width"], state["height"], state["callback"])
            != (0x511D40, 608, 528, 800, 600, 0x409D80)
            or state["state"] != expected_state or state["state3"] not in (1, 2)
            or state["selected_unit"] < 0
            or (state["cursor_meta"], state["cursor_sprite"]) != (meta, sprite)
            or (state["cursor_x"], state["cursor_y"]) != (state["mouse_x"], state["mouse_y"])):
        raise ValueError("capture does not observe the source-defined selected/hover cursor state")
    x, y = state["mouse_x"], state["mouse_y"]
    if not ((240 <= x <= 480 and 200 <= y <= 400) if phase == "map"
            else (608 <= x < 671 and 528 <= y < 559)):
        raise ValueError("capture native cursor is outside its required phase region")
    return state, before["line"], after["line"]


def validate_composition(composition: dict[str, Any], command: dict[str, Any],
                         started_at: str, finished_at: str) -> list[str]:
    """Check same-run native state and source asset pixels at 800x600 anchors."""
    failures: list[str] = []
    identity = command["identity"]
    if type(composition.get("schema_version")) is not int or composition.get("schema_version") != 1:
        failures.append("composition schema_version must be 1")
    if composition.get("evidence_class") != "approved_visible_automated_layout_composition":
        failures.append("composition evidence class is not approved visible layout composition")
    if composition.get("identity") != identity:
        failures.append("composition identity differs from the command-input run")
    for key, source_key in (("command_manifest", "source_manifest"), ("approval", "approval")):
        reference = composition.get(key)
        path = checked_reference(reference, f"composition {key}")
        expected = command.get(source_key, {})
        if (path != resolve_path(expected.get("path", ""))
                or not same_sha(reference.get("sha256"), expected.get("sha256"))):
            failures.append(f"composition {key} is not bound to the command-input source")
    if failures:
        return failures
    frames = composition.get("frames")
    if not isinstance(frames, dict) or set(frames) != {"map", "panel_hover"}:
        return failures + ["composition requires map and panel_hover capture pairs"]
    raw_log, observation_rows, assets, click_boundary = composition_sources(command)
    images: dict[str, Any] = {}
    seen_paths: set[Path] = set()
    seen_capture_ids: set[str] = set()
    window: str | None = identity.get("hwnd")
    previous_time: datetime | None = None
    previous_line = 0
    selected_identity: tuple[int, int, int] | None = None
    last_state: dict = {}
    for name in ("map", "panel_hover"):
        pair = frames[name]
        if not isinstance(pair, list) or len(pair) != 2:
            failures.append(f"composition {name} requires two separate consecutive captures")
            continue
        paths: list[Path] = []
        for item in pair:
            path = checked_reference(item, f"composition {name} frame")
            sidecar_path = checked_reference(item.get("sidecar"), f"composition {name} sidecar")
            sidecar = read_object(sidecar_path)
            if path in seen_paths:
                failures.append("composition reuses one capture path as independent evidence")
            seen_paths.add(path)
            capture_id = sidecar.get("CaptureId")
            if not isinstance(capture_id, str) or not capture_id or capture_id in seen_capture_ids:
                failures.append("composition capture IDs must be present and distinct")
            else:
                seen_capture_ids.add(capture_id)
            if (sidecar.get("RunId") != identity.get("run_id")
                    or not same_sha(sidecar.get("CandidateSha256"), identity.get("candidate_sha256"))
                    or sidecar.get("Stage") != identity.get("stage")
                    or sidecar.get("ClientSize") != [800, 600]):
                failures.append(f"composition {name} raw capture identity does not match the input run")
            timestamp = utc_time(sidecar.get("CapturedAt"))
            if not utc_time(started_at) <= timestamp <= utc_time(finished_at):
                failures.append(f"composition {name} capture is outside the command-input run")
            if previous_time is not None and timestamp <= previous_time:
                failures.append("composition captures are not independently ordered in time")
            previous_time = timestamp
            if failures:
                return failures
            if not authentic_screen_frame(path, sidecar, window):
                failures.append(f"composition {name} screen capture authenticity failed")
            state, before_line, after_line = capture_state(sidecar, name, raw_log, observation_rows)
            if before_line < previous_line:
                failures.append("composition capture observation intervals are not ordered")
            previous_line = after_line
            selected = (state["tid"], state["selected_unit"], state["state3"])
            if selected_identity is not None and selected != selected_identity:
                failures.append("composition changes the selected unit, UI thread, or descriptor-3 state")
            selected_identity = selected
            last_state = state
            failures.extend(asset_composition.check_frame(visible.read_png(path), assets, state, name))
            paths.append(path)
        if len(paths) == 2 and paths[0] != paths[1]:
            tear = capture_tear_check.build_report(paths, None)
            if tear.get("clean") is not True or tear.get("verdict") != "clean_stable_pair":
                failures.append(f"composition {name} lacks a non-suspect stable capture pair")
            images[name] = RecipeImage(visible.read_png(paths[0]))
    if len(images) == 2:
        tooltip, old_tooltip = visible._tooltip_check(images["map"])
        for name, check in (("tooltip anchor", tooltip), ("legacy tooltip absence", old_tooltip)):
            if check.get("passed") is not True:
                failures.append(f"same-run visible {name} failed the established image recipe")
    matched = command.get("matched_sequence")
    click_state = matched[0].get("values", {}) if isinstance(matched, list) and matched else {}
    # Natural movement within the same hovered icon is proved by the click's
    # own native hitbox chain; selection/cursor identity must remain unchanged.
    same_hover = (bool(last_state)
        and all(click_state.get(key) == value for key, value in last_state.items()
                if key not in {"mouse_x", "mouse_y", "cursor_x", "cursor_y"})
        and (click_state.get("cursor_x"), click_state.get("cursor_y"))
            == (click_state.get("mouse_x"), click_state.get("mouse_y")))
    if (click_boundary < previous_line or not isinstance(matched, list) or not matched
            or matched[0].get("line", 0) <= click_boundary or not same_hover):
        failures.append("native click is not after all captures in the same selected hover state")
    return failures


def build_decision(args: argparse.Namespace) -> dict[str, Any]:
    failures: list[str] = []
    checks: dict[str, dict[str, Any]] = {}
    sources: dict[str, dict[str, str]] = {}

    def load(name: str, value: Path) -> dict[str, Any]:
        path = resolve_path(value)
        data = read_object(path)
        sources[name] = {"path": str(path), "sha256": sha256(path)}
        return data

    def check(name: str, action: Any) -> Any:
        try:
            value, errors = action()
        except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError) as exc:
            value, errors = None, [f"{type(exc).__name__}: {exc}"]
        checks[name] = {"passed": not errors, "failures": errors}
        failures.extend(f"{name}: {error}" for error in errors)
        return value

    def command_check() -> tuple[dict[str, Any], list[str]]:
        import hd_layout_command_input_summary as command_parser
        supplied = load("command_input", args.command_input_json)
        manifest_path = checked_reference(supplied.get("source_manifest"), "command source manifest")
        regenerated = command_parser.build_report(manifest_path)
        errors: list[str] = []
        for key in ("schema_version", "passed", "status", "identity", "source_manifest", "raw_log", "probe",
                    "approval", "session_receipt", "command_click_alignment", "panel_click_callback_proof",
                    "manual_directinput_proof", "promotion_ready", "proof_class",
                    "native_click_gate_observed", "matched_sequence"):
            if supplied.get(key) != regenerated.get(key):
                errors.append(f"command-input {key} differs from independently reparsed evidence")
        if (regenerated.get("passed") is not True or regenerated.get("status") != "observed"
                or regenerated.get("command_click_alignment") is not True
                or regenerated.get("panel_click_callback_proof") is not True
                or regenerated.get("native_click_gate_observed") is not True):
            errors.append("raw command evidence does not prove aligned relocated-panel input and callback")
            errors.extend(str(error) for error in regenerated.get("failures", []))
        if regenerated.get("manual_directinput_proof") is not False or regenerated.get("promotion_ready") is not False:
            errors.append("command parser incorrectly claims manual release proof or promotion")
        return regenerated, errors

    command = check("command_input", command_check)
    identity = command.get("identity", {}) if isinstance(command, dict) else {}
    if not isinstance(identity, dict):
        identity = {}
    identity_ok = (isinstance(identity, dict) and isolated_candidate(identity.get("candidate_path"))
                   and identity.get("resolution") == [800, 600]
                   and bool(manual.SHA256_RE.fullmatch(str(identity.get("candidate_sha256", "")))))
    if not identity_ok:
        failures.append("candidate_identity: isolated candidate SHA/path and supported resolution are required")
    checks["candidate_identity"] = {"passed": identity_ok}
    stage = identity.get("stage", "")
    candidate_sha = identity.get("candidate_sha256", "")

    def byte_check() -> tuple[dict[str, Any], list[str]]:
        if not identity_ok:
            raise ValueError("a valid command-input candidate identity is required")
        candidate = resolve_path(identity["candidate_path"])
        if not isolated_candidate(str(candidate)):
            raise ValueError("resolved candidate path is outside the isolated candidate root")
        if not same_sha(sha256(candidate), candidate_sha):
            raise ValueError("actual candidate file SHA differs from command-input evidence")
        patcher = patch_stage_report.load_patcher()
        if stage not in patcher.STAGE_GROUPS:
            raise ValueError("unregistered candidate stage")
        supplied = load("patch", args.patch_json)
        fresh = patch_stage_report.build_report(candidate, stage, RESOLUTION)
        errors = validate_byte_report(fresh, candidate_sha=candidate_sha, stage=stage, resolution=RESOLUTION)
        errors.extend(validate_candidate_origin(candidate.read_bytes(), patcher.select_patches(stage), patcher.EXPECTED_SHA256))
        for key in ("stage", "resolution", "exe_sha256", "expected_base_sha256", "image_base_hex", "sections",
                    "patch_count", "status_counts", "groups", "map", "patches", "current_hd_map_gate"):
            if supplied.get(key) != fresh.get(key):
                errors.append(f"supplied byte report {key} differs from actual candidate bytes")
        return fresh, errors

    check("candidate_bytes", byte_check)

    def hidden_check() -> tuple[dict[str, Any], list[str]]:
        summary = load("hidden_geometry", args.hidden_json)
        run = load("hidden_run", args.hidden_run_json)
        return summary, validate_hidden(summary, run, candidate_sha=candidate_sha, stage=stage)

    check("hidden_geometry", hidden_check)

    def composition_check() -> tuple[dict[str, Any], list[str]]:
        composition = load("visible_composition", args.composition_json)
        if not identity_ok or not isinstance(command, dict):
            raise ValueError("command-input run identity is missing")
        return composition, validate_composition(composition, command, identity["started_at"], identity["finished_at"])

    check("same_run_visible_composition", composition_check)

    def manual_check() -> tuple[dict[str, Any], list[str]]:
        proof = load("manual_proof", args.manual_proof)
        return proof, validate_manual_proof(proof)

    proof = check("five_target_manual_proof", manual_check)

    def hygiene_check() -> tuple[dict[str, Any], list[str]]:
        hygiene = load("process_hygiene", args.process_hygiene_json)
        return hygiene, validate_hygiene(hygiene, identity["finished_at"])

    check("post_run_process_hygiene", hygiene_check)
    stable_ok = args.current_stable_stage == STABLE_STAGE
    checks["protected_stable_stage"] = {"passed": stable_ok}
    if not stable_ok:
        failures.append("protected_stable_stage: current stable stage was changed")
    ready = not failures
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runtime_policy": RUNTIME_POLICY,
        "passed": ready,
        "decision": "eligible_for_hd_layout_component_review" if ready else "defer_hd_layout_completion",
        "component_promotion_ready": ready,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "full_game_complete": False,
        "current_stable_stage": args.current_stable_stage,
        "validation_stage": stage or None,
        "candidate_sha256": candidate_sha or None,
        "resolution": RESOLUTION,
        "command_click_alignment": bool(command and command.get("command_click_alignment") is True
                                          and checks["command_input"]["passed"]),
        "panel_click_callback_proof": bool(command and command.get("panel_click_callback_proof") is True
                                           and checks["command_input"]["passed"]),
        "manual_input_proof_valid": checks["five_target_manual_proof"]["passed"],
        "manual_checked_item_count": len(proof.get("checked_items", [])) if proof else 0,
        "sources": sources,
        "checks": checks,
        "failures": failures,
        "scope_notes": [
            "Eligibility is a component review recommendation; no patch bytes or stage defaults are changed.",
            "Source asset pixels cover native 800x600 or exact 3:2 replication, active descriptors 0/3, hover and software cursor; filtered DPI captures require separate validation. Hidden geometry covers all six anchors.",
            "The five legacy manual targets remain separate from relocated-panel command callback evidence.",
            "Capture-pair heuristics support interpretation but cannot authenticate the human origin of approval or observations.",
            "Combined-stage interaction, other presets, endurance, continuity, and an explicit promotion decision remain independent requirements.",
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    defaults = {
        "command-input-json": "hd-layout-command-input-current.json",
        "composition-json": "hd-layout-composition-proof-current.json",
        "patch-json": "patch-stage-hdlayout-current.json",
        "hidden-json": "hd-layout-summary-current.json",
        "manual-proof": "manual-directinput-proof-current.json",
        "process-hygiene-json": "process-hygiene-guard-current.json",
    }
    for option, filename in defaults.items():
        parser.add_argument("--" + option, type=Path, default=Path("captures/current") / filename)
    parser.add_argument("--hidden-run-json", type=Path,
                        default=Path("captures/archive/cdb-surface-dump-20260713-072428/summary.json"))
    parser.add_argument("--current-stable-stage", default=STABLE_STAGE)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def write_markdown(path: Path, decision: dict[str, Any]) -> None:
    lines = ["# HD-layout completion decision", "", f"Decision: `{decision['decision']}`",
             f"Component eligibility: `{decision['component_promotion_ready']}`",
             "Stable stage changed: `False`", "", "## Evidence checks", ""]
    lines.extend(f"- {name}: {'PASS' if result['passed'] else 'FAIL'}" for name, result in decision["checks"].items())
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {failure}" for failure in decision["failures"])
    lines.extend(["", "## Scope", ""])
    lines.extend(f"- {note}" for note in decision["scope_notes"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    decision = build_decision(args)
    print(json.dumps(decision, indent=2))
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, decision)
    return 2 if args.require_pass and not decision["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

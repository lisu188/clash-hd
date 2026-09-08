#!/usr/bin/env python3
"""Read and bind complete-HD acceptance evidence; never run game/runtime tools.

The release manifest is an index, not proof. Its immutable references identify
the original, candidate, deterministic builder output, probe, and separately
produced lane reports. Old component reports are not upgraded or rewritten.
Evidence eligibility and an explicit promotion decision are separate results;
neither result edits a stable stage, launcher manifest, or release checklist.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = Path(r"C:\ClashTests")
STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)
STAGE = STABLE_STAGE + "-completehd-validation"
RECIPE_REVISION = "complete_hd_v1"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
SHA_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
RELEASE_SCHEMA = "complete_hd_release_manifest_v1"
LANE_SCHEMA = "complete_hd_lane_evidence_v1"
RUNTIME_POLICY = "read-only candidate rebuild and recorded-evidence validation; no runtime, input, capture, or promotion writes"
MANUAL_IDS = (
    "stable_menu_load", "stable_hd_map_input", "right_bottom_validation_input",
    "castle_barracks_centered_input", "castle_overview_centered_input",
)
SHORT_STEPS = (
    ("short2", "menu-idle", 120), ("short2", "map-idle", 120),
    ("short10", "map-idle", 600), ("short10", "map-pan", 600),
    ("short30", "map-pan", 1800),
)
# These requirements are executable policy. The release index cannot remove
# requirements, choose its own checker, or substitute a different proof class.
LANES = {
    "geometry": (("hidden_cdb_geometry",), (
        "loaded_candidate_contract", "frame_and_footer", "partial_tiles", "minimap_viewport",
        "army_panel", "modal_canvas", "centered_native_screens", "map_return")),
    "visible_composition": (("approved_visible_composition",), (
        "authentic_frames", "capture_tear_check", "map_frame_and_hud", "tooltip_and_panel",
        "castle_and_barracks", "battle", "no_visible_corruption")),
    **{name: (("manual_directinput",), ("displayed_target_alignment", "native_input_consumed", "expected_behavior"))
       for name in MANUAL_IDS},
    "panel_command": (("observed_relocated_panel_native_callback",), (
        "command_click_alignment", "native_click_gate_observed", "panel_click_callback_proof",
        "observation_only_probe", "matching_descriptor_and_callback")),
    "battle_entry_return": (("approved_visible_battle_route",), (
        "battle_entry", "command_click_alignment", "native_click_consumed", "matching_callback",
        "battle_return", "post_return_map_health", "no_forced_click_or_callback")),
    "save_load_roundtrip": (("approved_hidden_cdb_continuity", "manual_directinput"), (
        "roundtrip_completed", "state_hashes_match", "isolated_saves", "live_saves_unchanged")),
    "turn_advancement": (("approved_hidden_cdb_continuity", "manual_directinput"), (
        "player_cycle_completed", "day_advanced", "call_return_observed", "post_day_map_health")),
    "campaign_routes": (("approved_hidden_cdb_continuity", "manual_directinput"), (
        "repeated_screen_transitions", "route_completed", "state_consistent", "post_return_map_health")),
    "short_soak_ladder": (("approved_hidden_cdb_host_soak", "approved_visible_soak"), (
        "ordered_ladder_completed", "process_liveness", "render_integrity", "process_growth", "clean_stop")),
    "long_map_idle": (("approved_hidden_cdb_host_soak", "approved_visible_soak"), (
        "route_completed", "process_liveness", "render_integrity", "process_growth", "clean_stop")),
    "long_map_pan": (("approved_hidden_cdb_host_soak", "approved_visible_soak"), (
        "route_completed", "process_liveness", "render_integrity", "process_growth", "frame_progression", "clean_stop")),
    "resolution_coverage": (("repo_resolution_coverage",), (
        "patcher_constraints", "candidate_byte_gate", "advertised_resolution_matches",
        "other_resolutions_not_promoted")),
}
VISIBLE_LANES = {"visible_composition", *MANUAL_IDS, "panel_command", "battle_entry_return"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_digest(value: Any) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii"))


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not re.search("placeholder|replace_|TODO", value, re.I)


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be text")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must have a timezone")
    return result


def read_reference(reference: Any, base: Path, *, json_object: bool = False) -> tuple[Path, Any]:
    ref = _object(reference, "artifact reference")
    if not _text(ref.get("path")) or not isinstance(ref.get("sha256"), str) or not SHA_RE.fullmatch(ref["sha256"]):
        raise ValueError("artifact reference requires a real path and 64-hex sha256")
    path = Path(ref["path"])
    path = (path if path.is_absolute() else base / path).resolve()
    data = path.read_bytes()
    if digest(data) != ref["sha256"].lower():
        raise ValueError(f"artifact SHA-256 mismatch: {path}")
    if json_object:
        return path, _object(json.loads(data.decode("utf-8-sig")), str(path))
    return path, data


def build_candidate(original: bytes, resolution: str):
    """Lazy trusted recipe import; it only builds bytes in memory."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module("src.patcher.complete_hd_candidate").build_candidate(original, resolution)


def candidate_context(spec: dict[str, Any], base: Path, *, builder: Callable = build_candidate,
                      repo_root: Path = ROOT) -> dict[str, Any]:
    """Verify actual bytes and exact deterministic recipe metadata, not a claimed SHA."""
    base_path, original = read_reference(spec.get("base_executable"), base)
    candidate_path, actual = read_reference(spec.get("executable"), base)
    metadata_path, metadata = read_reference(spec.get("metadata"), base, json_object=True)
    probe_path, probe_bytes = read_reference(spec.get("probe"), base)
    if (candidate_path == base_path or candidate_path.is_relative_to(repo_root.resolve())
            or not candidate_path.is_relative_to(CANDIDATE_ROOT.resolve())):
        raise ValueError("candidate must be an isolated external copy, never the original or repository")
    if candidate_path.suffix.lower() != ".exe":
        raise ValueError("candidate must identify an executable")
    if digest(original) != BASE_SHA256:
        raise ValueError("base executable is not the known original SHA-256")
    resolution = metadata.get("resolution")
    if not isinstance(resolution, str) or not re.fullmatch(r"[1-9][0-9]*x[1-9][0-9]*", resolution):
        raise ValueError("candidate resolution must be WxH")
    if type(metadata.get("schema")) is not int or metadata["schema"] != 1 or metadata.get("stage") != STAGE or metadata.get("recipe_revision") != RECIPE_REVISION:
        raise ValueError("candidate is not the complete-HD validation recipe")
    from complete_hd_runtime_context import verify_context
    verified = verify_context(metadata, original, resolution=resolution,
                              candidate=actual, probe=probe_bytes.decode("utf-8"), builder=builder)
    if not isinstance(verified["candidate"], bytes) or not isinstance(verified["probe"], str):
        raise ValueError("complete-HD builder returned invalid candidate or probe types")
    if metadata.get("base_sha256", "").lower() != digest(original) or metadata.get("candidate_sha256", "").lower() != digest(actual):
        raise ValueError("builder metadata does not identify the actual base and candidate")
    if metadata.get("probe_sha256", "").lower() != digest(probe_bytes):
        raise ValueError("builder metadata does not identify the actual probe")
    source_hashes = _object(metadata.get("source_hashes"), "candidate source_hashes")
    if not source_hashes or not isinstance(metadata.get("patch_records"), list) or not metadata["patch_records"]:
        raise ValueError("candidate metadata lacks source pins or patch records")
    for relative, expected_sha in source_hashes.items():
        source = (repo_root / relative).resolve()
        if not source.is_relative_to(repo_root.resolve()):
            raise ValueError("candidate source reference escapes the repository")
        if not isinstance(expected_sha, str) or digest(source.read_bytes()) != expected_sha.lower():
            raise ValueError(f"candidate source has changed: {relative}")
    return {
        "identity": {"stage": STAGE, "resolution": resolution, "candidate_sha256": digest(actual),
                     "base_sha256": digest(original), "recipe_revision": RECIPE_REVISION,
                     "metadata_sha256": digest(metadata_path.read_bytes()), "probe_sha256": digest(probe_bytes)},
        "candidate_path": str(candidate_path), "metadata_path": str(metadata_path), "probe_path": str(probe_path),
        "source_hashes": source_hashes, "byte_rebuild_passed": True,
    }


def candidate_manifest_context(path: Path, *, base_executable: Path = Path("C:/Clash/clash95.exe"),
                               builder: Callable = build_candidate, repo_root: Path = ROOT) -> dict[str, Any]:
    """Shared release-mode context for a bundle written by the complete builder.

    This reads and rebuilds the actual executable and probe alongside the
    .candidate.json file. Loading JSON identity fields alone is never binding.
    """
    path = path.resolve()
    if not path.name.endswith(".candidate.json"):
        raise ValueError("candidate manifest must be a complete builder .candidate.json bundle")
    stem = path.name[:-len(".candidate.json")]
    paths = {"base_executable": base_executable.resolve(), "metadata": path,
             "executable": path.with_name(stem + ".exe"), "probe": path.with_name(stem + ".cdb")}
    refs = {name: {"path": str(value), "sha256": digest(value.read_bytes())} for name, value in paths.items()}
    return candidate_context(refs, path.parent, builder=builder, repo_root=repo_root)


def _resolution_verifier(report: dict[str, Any], report_path: Path, context: dict[str, Any],
                         repo_root: Path) -> dict[str, Any]:
    """Re-evaluate launcher status and actual builder context from their inputs.

    Runtime resolution acceptance belongs to the other fixed lanes. This lane
    proves only constraints, byte identity and the unpromoted launcher policy.
    """
    source, manifest = read_reference(report.get("resolution_manifest"), report_path.parent, json_object=True)
    if source != (repo_root / "src/launcher/resolutions.json").resolve():
        raise ValueError("resolution verifier requires the actual launcher resolution manifest")
    from src.launcher import presets

    # An indexed profile is not advertised if the actual launcher rejects it.
    # In particular, adding an unsupported `complete` profile cannot certify
    # this still-incomplete release lane.
    presets.validate_manifest(manifest)
    resolution = context["identity"]["resolution"]
    entries = _object(manifest.get("resolutions"), "launcher resolutions")
    profiles = _object(manifest.get("profiles"), "launcher renderer profiles")
    candidate_profiles = [row for row in profiles.values() if isinstance(row, dict)
                          and row.get("stage") == context["identity"]["stage"]
                          and row.get("recipe_revision") == context["identity"]["recipe_revision"]]
    candidate_profile = candidate_profiles[0] if len(candidate_profiles) == 1 else {}
    candidate_resolutions = candidate_profile.get("resolutions", {})
    profile_policy = all(
        isinstance(profile, dict) and isinstance(profile.get("resolutions"), dict)
        and all(isinstance(row, dict) and row.get("status") == (
            "stable" if name == "classic" and key == "800x600" else "experimental")
                for key, row in profile["resolutions"].items())
        for name, profile in profiles.items())
    specs = {
        "patcher_constraints": context.get("byte_rebuild_passed") is True,
        "candidate_byte_gate": context.get("byte_rebuild_passed") is True,
        "advertised_resolution_matches": (
            manifest.get("schema") == 2 and manifest.get("default_renderer") == "classic"
            and resolution in entries and candidate_profile.get("default") == "800x600"
            and candidate_profile.get("features") == {"minimap_viewport": True}
            and isinstance(candidate_resolutions, dict) and resolution in candidate_resolutions
            and isinstance(candidate_resolutions[resolution], dict)
            and candidate_resolutions[resolution].get("status") == "experimental"),
        "other_resolutions_not_promoted": (
            profile_policy and manifest.get("stable_stage") == STABLE_STAGE and manifest.get("default") == "800x600"
            and isinstance(profiles.get("classic"), dict) and profiles["classic"].get("stage") == STABLE_STAGE
            and profiles["classic"].get("resolutions") == entries
            and isinstance(entries.get("800x600"), dict) and entries["800x600"].get("status") == "stable"
            and all(isinstance(row, dict) and row.get("status") == "experimental"
                    for name, row in entries.items() if name != "800x600")),
    }
    failures = [name for name, passed in specs.items() if not passed]
    return {"passed": not failures, "failures": failures,
            "checks": {name: {"passed": passed, "failures": [] if passed else [name]}
                       for name, passed in specs.items()}}


# Only repository code chooses a verifier. Never import a module/function or
# execute a command supplied by an evidence report. Missing adapters are an
# explicit incomplete requirement, not permission to trust claimed booleans.
# Add a lane here only with source-artifact replay and negative fixtures.
LANE_VERIFIERS: dict[str, tuple[str, Callable]] = {
    "resolution_coverage": ("tools/complete_hd_evidence.py", _resolution_verifier),
}


def verify_lane_semantics(lane: str, report: dict[str, Any], report_path: Path,
                          context: dict[str, Any], repo_root: Path) -> list[str]:
    verifier = LANE_VERIFIERS.get(lane)
    if verifier is None:
        return [f"integrated source-artifact verifier is not implemented for {lane}; claimed passes cannot establish evidence"]
    relative, evaluate = verifier
    producer_path, _ = read_reference(report.get("producer"), report_path.parent)
    if producer_path != (repo_root / relative).resolve():
        return [f"lane requires the fixed repository verifier {relative}"]
    actual = _object(evaluate(report, report_path, context, repo_root), "recomputed lane result")
    failures = list(actual.get("failures", []))
    _check(actual.get("passed") is True and actual.get("failures") == [], failures,
           "source-artifact verifier did not affirmatively pass")
    for name in LANES[lane][1]:
        measured = _object(actual.get("checks"), "recomputed checks").get(name)
        _check(isinstance(measured, dict) and measured.get("passed") is True and measured.get("failures") == [],
               failures, f"source-artifact check is missing or failed: {name}")
        _check(report.get("checks", {}).get(name) == measured, failures,
               f"claimed check differs from source-artifact replay: {name}")
    return failures


def _check(condition: bool, failures: list[str], message: str) -> None:
    if not condition:
        failures.append(message)


def verify_reference_graph(value: Any, base: Path, seen: set[tuple[Path, str]] | None = None) -> None:
    """Recheck pinned input bytes at completion, including nested proof/approval refs."""
    seen = set() if seen is None else seen
    if isinstance(value, list):
        for item in value:
            verify_reference_graph(item, base, seen)
    elif isinstance(value, dict):
        if "path" in value and "sha256" in value:
            path, data = read_reference(value, base)
            key = (path, value["sha256"].lower())
            if key not in seen:
                seen.add(key)
                if path.suffix.lower() == ".json":
                    verify_reference_graph(json.loads(data.decode("utf-8-sig")), path.parent, seen)
        else:
            for item in value.values():
                verify_reference_graph(item, base, seen)


def _approval(report: dict[str, Any], report_path: Path, identity: dict[str, Any]) -> list[str]:
    """Validate a recorded approval for the historical measured run, not a new run."""
    _, approval = read_reference(report.get("approval"), report_path.parent, json_object=True)
    failures: list[str] = []
    _check(approval.get("approved") is True and _text(approval.get("approval_record")), failures,
           "a real explicit approval record is required")
    _check(approval.get("identity") == identity and approval.get("run_id") == report.get("run_id"), failures,
           "approval does not match the measured candidate/run")
    _check(approval.get("runtime_profile") == report.get("runtime_profile"), failures,
           "approval runtime profile differs from the measured run")
    started, ended = _time(report.get("started_at")), _time(report.get("finished_at"))
    approved, expires = _time(approval.get("approved_at")), _time(approval.get("expires_at"))
    _check(approved <= started <= ended <= expires, failures, "run falls outside its recorded approval interval")
    return failures


def _soak_rows(report: dict[str, Any], lane: str, identity: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    rows = report.get("steps") if lane == "short_soak_ladder" else [report]
    expected = SHORT_STEPS if lane == "short_soak_ladder" else (("long2h", "map-idle" if lane == "long_map_idle" else "map-pan", 7200),)
    if not isinstance(rows, list) or len(rows) != len(expected):
        return ["soak evidence does not contain the complete fixed step list"]
    previous_end: datetime | None = None
    for row, (tier, route, seconds) in zip(rows, expected):
        if not isinstance(row, dict):
            failures.append("soak step must be an object")
            continue
        _check(row.get("identity") == identity, failures, "soak step candidate identity mismatch")
        _check(row.get("tier") == tier and row.get("route") == route, failures, "soak step order/tier/route mismatch")
        _check(type(row.get("duration_sec")) in (int, float) and row["duration_sec"] >= seconds,
               failures, "soak duration is below the required interval")
        _check(row.get("passed") is True and row.get("clean_stop") is True, failures, "soak step did not pass with clean termination")
        begin, end = _time(row.get("started_at")), _time(row.get("finished_at"))
        _check((end - begin).total_seconds() >= seconds, failures, "soak measured wall interval is too short")
        _check(previous_end is None or previous_end <= begin, failures, "soak ladder is not sequential")
        previous_end = end
    if report.get("evidence_class") == "approved_hidden_cdb_host_soak":
        _check(report.get("runtime_profile", {}).get("environment") == "hidden_cdb_host", failures,
               "hidden soak environment is missing or differs")
        _check(report.get("input_responsiveness") == "not_applicable_hidden", failures,
               "hidden endurance must not claim manual/visible input proof")
    else:
        _check(report.get("input_responsiveness") == "passed", failures, "visible soak lacks input responsiveness proof")
    return failures


def evaluate_lane(lane: str, ref: Any, context: dict[str, Any], base: Path, *, repo_root: Path = ROOT) -> dict[str, Any]:
    failures: list[str] = []
    report: dict[str, Any] = {}
    report_path: Path | None = None
    try:
        report_path, report = read_reference(ref, base, json_object=True)
        identity = context["identity"]
        classes, checks = LANES[lane]
        _check(report.get("schema") == LANE_SCHEMA and report.get("lane") == lane, failures,
               "report is not a complete-HD report for the required lane")
        _check(report.get("identity") == identity, failures, "report candidate/stage/resolution/recipe identity mismatch")
        _check(report.get("passed") is True and report.get("failures") == [], failures, "lane report is not an affirmative pass")
        _check(report.get("evidence_class") in classes, failures, "evidence class cannot establish this lane")
        _check(report.get("stable_stage_should_change") is False, failures, "evidence producer must preserve the stable boundary")
        actual_checks = _object(report.get("checks"), "lane checks")
        for check in checks:
            value = actual_checks.get(check)
            _check(isinstance(value, dict) and value.get("passed") is True and value.get("failures") == [],
                   failures, f"required substantive check is missing or failed: {check}")
        producer_path, _ = read_reference(report.get("producer"), report_path.parent)
        _check(producer_path.is_relative_to((repo_root / "tools").resolve()), failures,
               "lane producer must identify pinned repository validation code")
        inputs = report.get("source_artifacts")
        if not isinstance(inputs, list) or not inputs:
            failures.append("lane report requires immutable original evidence artifacts")
        else:
            input_paths: set[Path] = set()
            for source in inputs:
                path, _ = read_reference(source, report_path.parent)
                _check(path != report_path and path != producer_path and path not in input_paths, failures,
                       "source artifacts must be distinct original inputs, not the report or producer")
                input_paths.add(path)
        if lane != "resolution_coverage":
            _check(_text(report.get("run_id")), failures, "runtime run identity is missing")
            started, finished = _time(report.get("started_at")), _time(report.get("finished_at"))
            generated = _time(report.get("generated_at"))
            _check(started <= finished <= generated <= datetime.now(timezone.utc), failures, "runtime/report timestamps are inconsistent")
            _check(report.get("no_crash") is True and report.get("process_cleanup_verified") is True, failures,
                   "runtime has no accepted crash/owned-process cleanup evidence")
            profile = _object(report.get("runtime_profile"), "runtime profile")
            _check(_text(profile.get("environment")) and _text(profile.get("input_method")), failures,
                   "runtime profile must disclose environment and input method")
            for key in ("wrapper", "wrapper_config"):
                read_reference(profile.get(key), report_path.parent)
            if lane in VISIBLE_LANES or report.get("evidence_class") in ("manual_directinput", "approved_visible_soak"):
                _check(profile.get("environment") == "host_visible", failures, "host visible evidence is required")
                failures.extend(_approval(report, report_path, identity))
            if lane in MANUAL_IDS or lane == "panel_command":
                _check(profile.get("input_method") == "manual_directinput", failures, "real manual input is required")
                _check(report.get("input_injected") is False and report.get("input_or_callback_forced") is False,
                       failures, "injected or debugger-forced input cannot satisfy manual acceptance")
                for name in ("observed_result", "pass_fail_notes"):
                    _check(_text(report.get(name)), failures, f"manual observation lacks real {name}")
            if lane in ("short_soak_ladder", "long_map_idle", "long_map_pan"):
                failures.extend(_soak_rows(report, lane, identity))
            if lane in ("save_load_roundtrip", "turn_advancement", "campaign_routes"):
                _check(report.get("live_save_mutated") is False and report.get("safe_test_save") is True,
                       failures, "continuity requires isolated test saves and unchanged live saves")
                for name in ("before_state_sha256", "after_state_sha256"):
                    _check(isinstance(report.get(name), str) and bool(SHA_RE.fullmatch(report[name])), failures,
                           f"continuity state hash is missing: {name}")
                if lane == "save_load_roundtrip":
                    _check(report.get("before_state_sha256") == report.get("after_state_sha256"), failures,
                           "save/load state hashes differ")
                else:
                    _check(report.get("before_state_sha256") != report.get("after_state_sha256"), failures,
                           "advancement/continuity state did not change")
        else:
            _check(report.get("release_resolutions") == [identity["resolution"]], failures,
                   "coverage must list exactly the candidate resolution; additional presets need separate complete acceptance")
        failures.extend(verify_lane_semantics(lane, report, report_path, context, repo_root))
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        failures.append(str(exc))
    return {"passed": not failures, "lane": lane, "report_path": str(report_path) if report_path else None,
            "report_sha256": ref.get("sha256") if isinstance(ref, dict) else None,
            "evidence_class": report.get("evidence_class"), "runtime_profile": report.get("runtime_profile"),
            "started_at": report.get("started_at"), "finished_at": report.get("finished_at"), "failures": failures}


def evaluate_release_manifest(path: Path, *, candidate_manifest: Path | None = None,
                              builder: Callable = build_candidate, repo_root: Path = ROOT) -> dict[str, Any]:
    """Evaluate the fixed complete-HD set without writing files or launching tools."""
    failures: list[str] = []
    context: dict[str, Any] = {}
    lanes: dict[str, Any] = {}
    manifest: dict[str, Any] = {}
    manifest_sha = None
    try:
        path = path.resolve()
        raw = path.read_bytes()
        manifest_sha = digest(raw)
        manifest = _object(json.loads(raw.decode("utf-8-sig")), "release manifest")
        if manifest.get("schema") != RELEASE_SCHEMA:
            raise ValueError("unsupported complete-HD release manifest schema")
        context = candidate_context(_object(manifest.get("candidate"), "candidate"), path.parent,
                                    builder=builder, repo_root=repo_root)
        if candidate_manifest is not None and candidate_manifest.resolve() != Path(context["metadata_path"]):
            raise ValueError("--candidate-manifest differs from the release index's actual candidate metadata")
        if context["identity"]["resolution"] != "1920x1080":
            raise ValueError("this full-HD acceptance profile requires 1920x1080")
        refs = _object(manifest.get("lanes"), "release lanes")
        _check(set(refs) == set(LANES), failures, "release manifest must contain exactly every fixed acceptance lane")
        for name in LANES:
            lanes[name] = evaluate_lane(name, refs.get(name), context, path.parent, repo_root=repo_root)
            failures.extend(f"{name}: {failure}" for failure in lanes[name]["failures"])
        # All visible results must represent the same wrapper/configuration.
        profiles = {object_digest({key: value for key, value in lanes[name]["runtime_profile"].items() if key != "input_method"})
                    for name in VISIBLE_LANES if lanes[name]["passed"]}
        _check(len(profiles) <= 1, failures, "visible/input lanes use incompatible runtime profiles")
        for name in ("long_map_idle", "long_map_pan"):
            if lanes[name]["passed"] and lanes["short_soak_ladder"]["passed"]:
                _check(_time(lanes["short_soak_ladder"]["finished_at"]) <= _time(lanes[name]["started_at"]),
                       failures, f"{name}: long route began before the short ladder completed")
                _check(lanes[name]["runtime_profile"] == lanes["short_soak_ladder"]["runtime_profile"],
                       failures, f"{name}: endurance profile differs from the prerequisite ladder")
        if lanes["long_map_idle"]["passed"] and lanes["long_map_pan"]["passed"]:
            _check(_time(lanes["long_map_idle"]["finished_at"]) <= _time(lanes["long_map_pan"]["started_at"]),
                   failures, "long endurance routes must run sequentially after the short ladder")
        verify_reference_graph(manifest, path.parent)
        _check(digest(path.read_bytes()) == manifest_sha, failures, "release manifest changed during evaluation")
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError) as exc:
        failures.append(str(exc))
    evidence_ready = not failures and len(lanes) == len(LANES)
    acceptance_digest = object_digest({"identity": context.get("identity"), "lanes": manifest.get("lanes")})
    promotion_failures: list[str] = []
    promotion_approved = False
    if manifest.get("promotion_decision") is not None:
        try:
            _, decision = read_reference(manifest["promotion_decision"], path.parent, json_object=True)
            _check(evidence_ready, promotion_failures, "promotion cannot substitute for missing complete evidence")
            _check(decision.get("schema") == "complete_hd_promotion_decision_v1", promotion_failures, "unsupported promotion decision schema")
            _check(decision.get("decision") == "approve_complete_hd_promotion" and decision.get("approved") is True,
                   promotion_failures, "decision does not explicitly approve complete-HD promotion")
            _check(_text(decision.get("approval_record")), promotion_failures, "real promotion approval record is missing")
            _check(decision.get("identity") == context.get("identity") and decision.get("acceptance_sha256") == acceptance_digest,
                   promotion_failures, "promotion decision is not bound to this exact acceptance set")
            _check(decision.get("current_stable_stage") == STABLE_STAGE, promotion_failures, "promotion decision protected baseline differs")
            approval_time = _time(decision.get("approved_at"))
            _check(approval_time <= datetime.now(timezone.utc), promotion_failures, "promotion approval timestamp is in the future")
            for lane_ref in (manifest.get("lanes") or {}).values():
                _, lane_report = read_reference(lane_ref, path.parent, json_object=True)
                _check(_time(lane_report.get("generated_at")) <= approval_time, promotion_failures,
                       "promotion approval predates the reviewed acceptance report")
            promotion_approved = not promotion_failures
        except (OSError, ValueError, TypeError, KeyError) as exc:
            promotion_failures.append(str(exc))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "runtime_policy": RUNTIME_POLICY,
        "evaluation_scope": "complete_hd_1920x1080_candidate_eligibility",
        "release_manifest": str(path), "release_manifest_sha256": manifest_sha,
        "candidate_context": context, "acceptance_sha256": acceptance_digest,
        "whole_hd_acceptance_evaluated": bool(context), "required_lanes": list(LANES), "lanes": lanes,
        "unimplemented_lane_verifiers": [name for name in LANES if name not in LANE_VERIFIERS],
        "passed": evidence_ready and not promotion_failures, "evidence_ready": evidence_ready,
        "eligible_for_stable_promotion": evidence_ready, "promotion_approved": promotion_approved,
        "promotion_ready": evidence_ready and promotion_approved,
        "stable_stage_should_change": False, "checklist_updated": None, "full_game_complete": False,
        "failures": failures, "promotion_failures": promotion_failures,
    }

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
import math
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
MAX_JSON_CONTAINER_DEPTH = 64
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


def parse_evidence_json(data: bytes, label: str) -> Any:
    """Require unique keys, finite numbers and bounded evidence containers."""
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label}: duplicate JSON key: {key}")
            result[key] = value
        return result

    def finite_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            raise ValueError(f"{label}: non-finite JSON number")
        return value

    def invalid_constant(token: str) -> None:
        raise ValueError(f"{label}: invalid JSON numeric constant: {token}")

    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object,
                           parse_float=finite_float, parse_constant=invalid_constant)
    except RecursionError as exc:
        raise ValueError(f"{label}: JSON nesting exceeds parser capacity") from exc
    # One iterator per container avoids recursion and a list of every sibling.
    # Referenced documents have their own depth bound and iterative graph walk.
    pending = [(iter((value,)), 0)]
    while pending:
        values, depth = pending[-1]
        try:
            item = next(values)
        except StopIteration:
            pending.pop()
            continue
        if isinstance(item, (dict, list)):
            if depth >= MAX_JSON_CONTAINER_DEPTH:
                raise ValueError(f"{label}: JSON container nesting exceeds {MAX_JSON_CONTAINER_DEPTH}")
            pending.append((iter(item.values() if isinstance(item, dict) else item), depth + 1))
    return value


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
        return path, _object(parse_evidence_json(data, str(path)), str(path))
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
    # A supported experimental profile can satisfy this metadata lane, while
    # an unknown profile or a promoted status cannot replace its contract.
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


def _panel_verifier(report: dict[str, Any], report_path: Path, context: dict[str, Any],
                    repo_root: Path) -> dict[str, Any]:
    """Reparse original native observations; caller-provided pass flags are not proof."""
    import hd_layout_command_input_summary as command
    manifest_path, manifest = read_reference(report.get("command_manifest"), report_path.parent, json_object=True)
    observed = command.build_report(manifest_path, candidate_manifest=Path(context["metadata_path"]))
    failures = list(observed.get("failures", []))
    identity = observed.get("identity", {})
    _check(observed.get("candidate_context", {}).get("identity") == context["identity"], failures,
           "replayed command observations belong to another complete candidate")
    wrapper = identity.get("wrapper", {})
    expected_profile = {"environment": identity.get("environment"), "input_method": identity.get("input_method"),
                        "wrapper": {key: wrapper.get(key) for key in ("path", "sha256")},
                        "wrapper_config": wrapper.get("config")}
    for key, expected in (("run_id", identity.get("run_id")), ("started_at", identity.get("started_at")),
                          ("finished_at", identity.get("finished_at")), ("runtime_profile", expected_profile),
                          ("approval", manifest.get("approval"))):
        _check(report.get(key) == expected, failures, f"command lane envelope differs from original observation {key}")
    source_paths = {read_reference(ref, report_path.parent)[0] for ref in report.get("source_artifacts", [])}
    _check(manifest_path in source_paths, failures, "command lane must retain its original observation manifest")
    _check(observed.get("passed") is True and observed.get("manual_directinput_proof") is False,
           failures, "native callback report must pass while preserving the separate manual-proof boundary")
    values = {
        "command_click_alignment": observed.get("command_click_alignment") is True,
        "native_click_gate_observed": observed.get("native_click_gate_observed") is True,
        "panel_click_callback_proof": observed.get("panel_click_callback_proof") is True,
        "observation_only_probe": observed.get("passed") is True,
        "matching_descriptor_and_callback": observed.get("passed") is True and observed.get("matched_sequence") is not None,
    }
    return {"passed": not failures and all(values.values()), "failures": failures,
            "checks": {name: {"passed": passed, "failures": [] if passed else [name]} for name, passed in values.items()}}


# Only repository code chooses a verifier. Never import a module/function or
# execute a command supplied by an evidence report. Missing adapters are an
# explicit incomplete requirement, not permission to trust claimed booleans.
# Add a lane here only with source-artifact replay and negative fixtures.
LANE_VERIFIERS: dict[str, tuple[str, Callable]] = {
    "resolution_coverage": ("tools/complete_hd_evidence.py", _resolution_verifier),
    "panel_command": ("tools/hd_layout_command_input_summary.py", _panel_verifier),
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


# The existing hidden runner is a stable-stage diagnostic producer. These are
# missing producer capabilities, not fields which an evidence author can fill
# with a green boolean. In particular, replay below never registers a release
# lane or treats a CDB-forced route/pan as native manual input.
HIDDEN_SOAK_PRODUCER_GAPS = (
    "hidden soak producer only builds the protected stable stage; it lacks a source-bound complete candidate and loaded candidate contracts",
    "hidden soak producer retains only edge raw frames; immutable raw references for every sampled frame are required",
    "hidden soak producer lacks PID, executable path and creation-time-bound termination receipts for its game, debugger and descendants",
    "hidden soak producer lacks an authenticated run start/finish envelope binding candidate, generated probe, wrapper and raw observations",
    "hidden soak producer has no menu-idle route; the short ladder needs a separate authentic menu-idle producer",
)


def _same_raw_json(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int aliases or NaN equality."""
    try:
        options = {"sort_keys": True, "separators": (",", ":"), "allow_nan": False}
        return json.dumps(left, **options) == json.dumps(right, **options)
    except (TypeError, ValueError, RecursionError):
        return False


def _hidden_soak_log(log: str, failures: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Replay the anchored records emitted by clash95_hidden_soak_route_extra.cdb."""
    patterns = (
        ("ready", r"(SOAK_SURFDUMP_READY|SURFDUMP_READY) redraw_seq=(\d{1,10}) surface=([0-9a-fA-F]{1,16}|[0-9a-fA-F]{1,8}`[0-9a-fA-F]{1,8}) size=\((\d{1,5}),(\d{1,5})\) base=([0-9a-fA-F]{1,16}|[0-9a-fA-F]{1,8}`[0-9a-fA-F]{1,8}) bytes=(\d{1,10})",
         "source redraw_seq surface width height base bytes"),
        ("start", r"SOAK_ROUTE_START route_ticks=(\d{1,10}) pan=(0|1) player=(-?\d{1,10}) tick=(-?\d{1,10}) gd=([0-9a-fA-F]{1,16}|[0-9a-fA-F]{1,8}`[0-9a-fA-F]{1,8}) scroll=\((-?\d{1,10}),(-?\d{1,10})\)",
         "route_ticks pan player tick game_data scroll_x scroll_y"),
        ("end", r"SOAK_ROUTE_END route_ticks=(\d{1,10}) pan=(0|1) hits=(\d{1,10}) tickdelta=(\d{1,10}) player=(-?\d{1,10}) scroll=\((-?\d{1,10}),(-?\d{1,10})\)",
         "route_ticks pan hits tick_delta player scroll_x scroll_y"),
        ("heartbeat", r"SOAK_HEARTBEAT hits=(\d{1,10}) tickdelta=(\d{1,10}) player=(-?\d{1,10}) scroll=\((-?\d{1,10}),(-?\d{1,10})\)",
         "hits tick_delta player scroll_x scroll_y"),
        ("plan", r"SOAK_PAN_PLAN base=\((-?\d{1,10}),(-?\d{1,10})\) delta=\((-?\d{1,10}),(-?\d{1,10})\) max=\((-?\d{1,10}),(-?\d{1,10})\) safe=1",
         "base_x base_y delta_x delta_y max_x max_y"),
        ("unsafe", r"SOAK_PAN_UNSAFE base=\((-?\d{1,10}),(-?\d{1,10})\) max=\((-?\d{1,10}),(-?\d{1,10})\) reason=([a-z0-9_-]{1,64})",
         "base_x base_y max_x max_y reason"),
        ("pan", r"SOAK_PAN_SET phase=(\d) x=(-?\d{1,10}) y=(-?\d{1,10}) hits=(\d{1,10}) tickdelta=(\d{1,10}) delta=\((-?\d{1,10}),(-?\d{1,10})\)",
         "phase x y hits tick_delta delta_x delta_y"),
    )
    rows: dict[str, list[dict[str, Any]]] = {kind: [] for kind, _, _ in patterns}
    marker_names = r"(?:SOAK_SURFDUMP_READY|SURFDUMP_READY|SOAK_ROUTE_START|SOAK_ROUTE_END|SOAK_HEARTBEAT|SOAK_PAN_PLAN|SOAK_PAN_UNSAFE|SOAK_PAN_SET)\b"
    for number, text in enumerate(log.splitlines(), 1):
        line = text.strip()
        for kind, pattern, fields in patterns:
            match = re.fullmatch(pattern, line)
            if match:
                try:
                    row = {name: value if name in {"source", "surface", "base", "game_data", "reason"} else int(value)
                           for name, value in zip(fields.split(), match.groups())}
                except (ValueError, OverflowError):
                    failures.append(f"malformed numeric hidden soak record at line {number}")
                    break
                row["_line"] = number
                rows[kind].append(row)
                break
        else:
            if re.match(marker_names, line):
                failures.append(f"malformed anchored hidden soak record at line {number}")
        if line in {"AV_SURFDUMP", "SURFDUMP_INVALID"} or line.startswith("SURFDUMP_APP_REQUEST_QUIT"):
            failures.append(f"raw hidden soak log records runtime failure: {line}")
    if rows["unsafe"]:
        failures.append("raw hidden soak log records SOAK_PAN_UNSAFE")
    return rows


def _hidden_sample_times(rows: list[Any], kind: str, interval: int, duration: int,
                         failures: list[str]) -> float | None:
    times = []
    for row in rows:
        try:
            times.append(_time(_object(row, f"{kind} sample").get("Timestamp")))
        except (TypeError, ValueError):
            failures.append(f"{kind} sample has a missing or invalid timezone timestamp")
    if len(times) < 2:
        failures.append(f"at least two timestamped {kind} samples are required")
        return None
    gaps = [(right - left).total_seconds() for left, right in zip(times, times[1:])]
    _check(all(gap > 0 for gap in gaps), failures, f"{kind} sample timestamps are not strictly increasing")
    if interval > 0:
        _check(all(gap <= interval + 2 for gap in gaps), failures, f"{kind} samples have unexplained gaps beyond the declared interval")
    span = (times[-1] - times[0]).total_seconds()
    # Preserve the existing producer's endpoint allowance. Native route ticks
    # are checked independently; this span is not authenticated wall-clock proof.
    _check(span >= max(0, duration - interval - 2), failures, f"{kind} sample span is shorter than the requested soak coverage")
    return span


def audit_hidden_soak_raw(samples: Any, log: Any, raw_frames: Any, identity: Any, *,
                          minimum_duration_sec: int = 7200) -> dict[str, Any]:
    """Validate existing hidden-soak raw diagnostics without accepting a lane.

    ``raw_frames`` maps the existing frame ``Name`` to its full indexed-8 bytes.
    The caller must separately authenticate artifact references and candidate
    bytes. This pure helper performs no file reads, runtime or approval writes.
    It replays measured bytes/records instead of trusting assembled reports;
    even consistent diagnostics leave ``passed`` and release verification false.
    """
    failures: list[str] = []
    for value, label in ((samples, "samples"), (raw_frames, "raw_frames"), (identity, "identity")):
        _check(isinstance(value, dict), failures, f"hidden soak {label} must be an object")
    samples = samples if isinstance(samples, dict) else {}
    raw_frames = raw_frames if isinstance(raw_frames, dict) else {}
    identity = identity if isinstance(identity, dict) else {}
    _check(isinstance(log, str) and bool(log.strip()), failures, "raw hidden soak CDB log is missing")
    log = log if isinstance(log, str) else ""
    _check(_same_raw_json(samples, samples) and _same_raw_json(identity, identity), failures,
           "raw hidden soak metadata must contain finite JSON values")
    _check(samples.get("schema") == "hidden_cdb_host_soak_samples_v1", failures, "unsupported raw hidden soak samples schema")
    _check(samples.get("executed") is True, failures, "hidden soak execution was not recorded")
    _check(samples.get("environment") == "hidden_cdb_host" and samples.get("launch_mode") == "hidden-desktop"
           and samples.get("frame_read_method") == "host_readprocessmemory", failures,
           "hidden soak capture method or environment differs from the raw producer")
    _check(samples.get("input_responsiveness") == "not_applicable_hidden", failures,
           "hidden diagnostics cannot establish visible or manual input responsiveness")
    for field in ("input_max_abs_error", "input_max_sample_abs_error", "route_results"):
        value = samples.get(field)
        _check(value is None or _same_raw_json(value, []) or _same_raw_json(value, ""), failures,
               f"hidden diagnostics contain forbidden input evidence: {field}")
    for field in ("runner_failures", "capture_errors"):
        _check(_same_raw_json(samples.get(field), []), failures, f"hidden soak {field} must be an empty array")
    for field in ("av_observed", "surface_invalid_observed", "app_request_quit_observed",
                  "cdb_exit_before_duration", "game_exit_before_duration", "process_exited_unexpectedly"):
        _check(samples.get(field) is False, failures, f"hidden soak reports a failure or lacks a boolean observation: {field}")
    for field, source in (("stage", "stage"), ("candidate_sha256", "candidate_sha256"), ("input_sha256", "base_sha256")):
        expected = identity.get(source)
        valid = _text(expected) if source == "stage" else isinstance(expected, str) and bool(SHA_RE.fullmatch(expected))
        _check(valid and _same_raw_json(samples.get(field), expected), failures, f"hidden soak differs from supplied candidate identity: {source}")
    match = re.fullmatch(r"([1-9][0-9]{0,4})x([1-9][0-9]{0,4})", identity.get("resolution", "")) if isinstance(identity.get("resolution"), str) else None
    width, height = (int(value) for value in match.groups()) if match else (0, 0)
    _check(bool(match) and width <= 65535 and height <= 65535, failures, "supplied candidate resolution must be positive 16-bit WxH")
    duration = samples.get("duration_sec")
    interval = samples.get("frame_interval_sec")
    maximum_duration = 0x7fffffff // 64  # The existing probe prints signed 32-bit route ticks.
    minimum_valid = type(minimum_duration_sec) is int and 0 < minimum_duration_sec <= maximum_duration
    duration_valid = type(duration) is int and 0 < duration <= maximum_duration
    interval_valid = type(interval) is int and duration_valid and 0 < interval and 2 * interval <= duration
    _check(minimum_valid, failures, "minimum soak duration must be a positive policy integer within the probe range")
    _check(duration_valid and minimum_valid and duration >= minimum_duration_sec, failures,
           "raw hidden soak duration is below the requested policy duration or outside the probe range")
    _check(interval_valid, failures,
           "raw hidden soak sampling interval must be positive and at most half the duration")
    duration = duration if duration_valid else 0
    interval = interval if interval_valid else 0
    route = samples.get("route")
    _check(route in ("map-idle", "map-pan"), failures, "hidden raw producer does not implement this soak route")
    expected_pan = int(route == "map-pan")
    _check(type(samples.get("duration_ticks")) is int and samples["duration_ticks"] == duration * 64, failures,
           "raw hidden soak duration ticks differ from the requested 64 Hz duration")
    rows = _hidden_soak_log(log, failures)
    ready_rows = [row for row in rows["ready"] if row["source"] == "SOAK_SURFDUMP_READY"]
    for kind, values in (("ready", ready_rows), ("start", rows["start"]), ("end", rows["end"])):
        _check(len(values) == 1, failures, f"raw hidden soak requires exactly one {kind} marker")
    ready = ready_rows[0] if len(ready_rows) == 1 else {}
    start = rows["start"][0] if len(rows["start"]) == 1 else {}
    end = rows["end"][0] if len(rows["end"]) == 1 else {}
    for field, actual in (("ready_marker", ready), ("route_start_marker", start), ("route_end_marker", end)):
        _check(bool(actual) and _same_raw_json(samples.get(field), {key: value for key, value in actual.items() if key != "_line"}),
               failures, f"{field} differs from raw anchored CDB records")
    _check(type(samples.get("heartbeat_count")) is int and samples["heartbeat_count"] == len(rows["heartbeat"])
           and bool(rows["heartbeat"]), failures, "raw heartbeat inventory is absent or differs from the samples")
    _check(type(samples.get("pan_event_count")) is int and samples["pan_event_count"] == len(rows["pan"]), failures,
           "raw pan event count differs from the samples")
    _check(_same_raw_json(samples.get("pan_events"), [{key: value for key, value in row.items() if key != "_line"} for row in rows["pan"]]),
           failures, "pan_events differ from raw anchored CDB records")
    if ready:
        _check(ready["width"] == width and ready["height"] == height and ready["bytes"] == width * height, failures,
               "raw surface dimensions or byte count differ from the supplied candidate")
        _check(ready["redraw_seq"] > 0, failures, "raw surface ready marker lacks redraw liveness")
        for field in ("surface", "base"):
            _check(0 < int(ready[field].replace("`", ""), 16) <= 0xffffffff, failures, f"raw {field} pointer is not a nonzero x86 address")
        _check(_same_raw_json(samples.get("surface"), {"Base": ready["base"], "Width": width, "Height": height,
                                                        "Bytes": width * height, "Source": ready["source"]}), failures,
               "surface metadata differs from raw CDB surface records")
    if start and ready and end:
        # The actual probe emits START immediately before SOAK_SURFDUMP_READY.
        _check(start["_line"] < ready["_line"] < end["_line"], failures, "raw start, ready and end markers are not ordered")
        _check(start["route_ticks"] == end["route_ticks"] == duration * 64
               and start["pan"] == end["pan"] == expected_pan, failures, "raw route markers differ from the requested route or duration")
        _check(end["tick_delta"] >= duration * 64 and end["hits"] > 0 and end["player"] == start["player"], failures,
               "raw route end lacks full duration, liveness or same-turn continuity")
        _check(0 <= start["player"] < 8 and 0 < int(start["game_data"].replace("`", ""), 16) <= 0xffffffff, failures,
               "raw route start lacks a valid player or nonzero x86 game-data address")
        previous = (-1, -1)
        for row in rows["heartbeat"]:
            _check(start["_line"] < row["_line"] < end["_line"] and row["player"] == start["player"]
                   and previous[0] < row["tick_delta"] <= end["tick_delta"] and previous[1] < row["hits"] <= end["hits"]
                   and row["hits"] > 0 and row["hits"] % 2048 == 0, failures, "raw heartbeat records violate the probe order or liveness contract")
            previous = (row["tick_delta"], row["hits"])
        if not expected_pan:
            _check(not rows["plan"] and not rows["pan"], failures, "map-idle raw log contains forced pan records")
            _check((start["scroll_x"], start["scroll_y"]) == (end["scroll_x"], end["scroll_y"]), failures,
                   "map-idle raw scroll position changed")
        else:
            _check(len(rows["plan"]) == 1 and bool(rows["pan"]), failures, "map-pan raw log lacks one safe plan and pan events")
            if len(rows["plan"]) == 1:
                plan = rows["plan"][0]
                _check(ready["_line"] < plan["_line"] < end["_line"] and plan["base_x"] == start["scroll_x"]
                       and plan["base_y"] == start["scroll_y"], failures, "raw pan plan order or base differs from route start")
                delta = tuple(1 if plan[f"base_{axis}"] < plan[f"max_{axis}"] else -1 if plan[f"base_{axis}"] > 0 else 0 for axis in ("x", "y"))
                _check(any(delta) and all(0 <= plan[f"base_{axis}"] <= plan[f"max_{axis}"] for axis in ("x", "y"))
                       and delta == (plan["delta_x"], plan["delta_y"]), failures, "raw pan plan is not the probe's bounded inward direction")
                previous = (0, -1)
                pan_interval = samples.get("pan_interval_sec")
                _check(type(pan_interval) is int and 0 < pan_interval < duration, failures, "raw pan interval must be a positive integer below the duration")
                pan_ticks = pan_interval * 64 if type(pan_interval) is int and pan_interval > 0 else duration * 64
                for index, row in enumerate(rows["pan"]):
                    phase = index % 4
                    target = (plan["base_x"] + (plan["delta_x"] if phase in (1, 2) else 0),
                              plan["base_y"] + (plan["delta_y"] if phase in (2, 3) else 0))
                    _check(plan["_line"] < row["_line"] < end["_line"] and row["phase"] == phase
                           and (row["delta_x"], row["delta_y"]) == delta and (row["x"], row["y"]) == target
                           and row["tick_delta"] - previous[0] >= pan_ticks and max(0, previous[1]) < row["hits"] <= end["hits"]
                           and row["tick_delta"] < end["tick_delta"], failures, "raw pan records violate the bounded phase, interval or liveness contract")
                    previous = (row["tick_delta"], row["hits"])
        scroll = (start["scroll_x"], start["scroll_y"])
        previous = (-1, -1)
        for row in sorted(rows["heartbeat"] + rows["pan"], key=lambda row: row["_line"]):
            _check(row["tick_delta"] >= previous[0] and row["hits"] >= previous[1], failures,
                   "raw heartbeat and pan streams disagree on clock or redraw order")
            previous = (row["tick_delta"], row["hits"])
            if "phase" in row:
                scroll = (row["x"], row["y"])
            else:
                _check((row["scroll_x"], row["scroll_y"]) == scroll, failures, "raw heartbeat scroll differs from the preceding pan phase")
        _check((end["scroll_x"], end["scroll_y"]) == scroll, failures, "raw end scroll differs from the replayed route")
    frames = samples.get("frame_samples")
    processes = samples.get("process_samples")
    _check(isinstance(frames, list) and isinstance(processes, list), failures, "raw frame and process inventories must be arrays")
    frames = frames if isinstance(frames, list) else []
    processes = processes if isinstance(processes, list) else []
    frame_span = _hidden_sample_times(frames, "frame", interval, duration, failures)
    process_span = _hidden_sample_times(processes, "process", interval, duration, failures)
    seen: set[str] = set()
    measured_frames = []
    for row in frames:
        if not isinstance(row, dict):
            failures.append("raw frame sample must be an object")
            continue
        name = row.get("Name")
        if not isinstance(name, str) or not re.fullmatch(r"frame-[0-9]{4,}", name) or name in seen:
            failures.append("raw frame names are missing, malformed or duplicated")
            continue
        seen.add(name)
        data = raw_frames.get(name)
        if not isinstance(data, bytes) or len(data) != width * height or not data:
            failures.append(f"full raw indexed-8 bytes are missing or truncated for {name}")
            continue
        measured = {"name": name, "sha256": digest(data), "nonblack_percent": round(100 * (len(data) - data.count(0)) / len(data), 3),
                    "unique_colors": len(set(data))}
        measured_frames.append(measured)
        _check(type(row.get("Width")) is int and row["Width"] == width and type(row.get("Height")) is int and row["Height"] == height,
               failures, f"raw frame dimensions differ for {name}")
        _check(row.get("CaptureMode") == "hidden-cdb-host-readprocessmemory", failures, f"raw frame capture method differs for {name}")
        _check(row.get("Hash") == measured["sha256"], failures, f"raw frame SHA-256 differs for {name}")
        _check(type(row.get("NonblackPercent")) in (int, float) and row["NonblackPercent"] == measured["nonblack_percent"]
               and type(row.get("UniqueSampleColors")) is int and row["UniqueSampleColors"] == measured["unique_colors"], failures,
               f"raw frame histogram metrics differ for {name}")
        _check(measured["nonblack_percent"] >= 10 and measured["unique_colors"] >= 8, failures, f"raw frame fails the diagnostic rendering thresholds for {name}")
    _check(set(raw_frames) == seen, failures, "raw frame byte inventory differs from the samples")
    if expected_pan:
        _check(len({row["sha256"] for row in measured_frames}) >= 2, failures, "map-pan raw frames have no measured progression")
    metrics: dict[str, list[int]] = {"WorkingSet64": [], "PrivateMemorySize64": [], "HandleCount": []}
    for row in processes:
        if not isinstance(row, dict):
            failures.append("raw process sample must be an object")
            continue
        _check(row.get("HasExited") is False and row.get("ExitCode") is None and row.get("Error") in (None, ""), failures,
               "raw process telemetry records exit, error or missing liveness")
        for field in metrics:
            value = row.get(field)
            maximum_value = 0x7fffffff if field == "HandleCount" else 0x7fffffffffffffff
            if type(value) is not int or not 0 <= value <= maximum_value:
                failures.append(f"raw process {field} must be a nonnegative measured integer within its native range")
            else:
                metrics[field].append(value)
    growth = {field: max(values) - values[0] for field, values in metrics.items() if values}
    for field, maximum in (("WorkingSet64", 64 * 1024 * 1024), ("PrivateMemorySize64", 64 * 1024 * 1024), ("HandleCount", 128)):
        _check(len(metrics[field]) == len(processes) and len(processes) >= 2 and growth.get(field, maximum + 1) <= maximum,
               failures, f"raw process {field} growth is missing or exceeds the fixed diagnostic limit")
    failures = list(dict.fromkeys(failures))
    return {"passed": False, "raw_validation_passed": not failures, "release_evidence_verified": False,
            "candidate_authenticated": False, "clean_stop_verified": False, "input_evidence_verified": False,
            "raw_failures": failures, "producer_gaps": list(HIDDEN_SOAK_PRODUCER_GAPS),
            "failures": failures + list(HIDDEN_SOAK_PRODUCER_GAPS),
            "observations": {"native_route_ticks": end.get("tick_delta"), "frame_span_sec": frame_span,
                             "process_span_sec": process_span, "frame_metrics": measured_frames, "process_growth": growth}}


def verify_reference_graph(value: Any, base: Path, seen: set[tuple[Path, str]] | None = None) -> None:
    """Recheck pinned input bytes at completion, including nested proof/approval refs."""
    seen = set() if seen is None else seen
    pending = [(iter((value,)), base)]
    while pending:
        values, parent = pending[-1]
        try:
            item = next(values)
        except StopIteration:
            pending.pop()
            continue
        if isinstance(item, list):
            pending.append((iter(item), parent))
        elif isinstance(item, dict):
            if "path" in item and "sha256" in item:
                path, data = read_reference(item, parent)
                key = (path, item["sha256"].lower())
                if key not in seen:
                    seen.add(key)
                    if path.suffix.lower() == ".json":
                        parsed = parse_evidence_json(data, str(path))
                        pending.append((iter((parsed,)), path.parent))
            else:
                pending.append((iter(item.values()), parent))


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
                if lane != "panel_command":
                    failures.extend(_approval(report, report_path, identity))
                # Panel replay validates its original source-bound approval
                # receipt rather than requiring a second invented approval.
            if lane in MANUAL_IDS:
                _check(profile.get("input_method") == "manual_directinput", failures, "real manual input is required")
                _check(report.get("input_injected") is False and report.get("input_or_callback_forced") is False,
                       failures, "injected or debugger-forced input cannot satisfy manual acceptance")
                for name in ("observed_result", "pass_fail_notes"):
                    _check(_text(report.get(name)), failures, f"manual observation lacks real {name}")
            if lane == "panel_command":
                _check(profile.get("input_method") in ("manual_directinput", "win32_sendinput_relative"), failures,
                       "panel callback requires disclosed human or relative pulse input")
                _check(report.get("input_or_callback_forced") is False, failures,
                       "debugger-forced input or callback cannot establish native panel acceptance")
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
        manifest = _object(parse_evidence_json(raw, "release manifest"), "release manifest")
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

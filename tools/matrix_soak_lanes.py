#!/usr/bin/env python3
"""Hidden-host soak lane replay for the matrix-cell release context.

A soak lane report pins, for each fixed schedule row, one
hd_multires_hidden_session report and its retained CDB log. This replay
rereads both, binds them to the freshly authenticated matrix cell, replays the
log through the shared soak row grammar, rehashes every retained frame and
recomputes the lane's required checks from the recorded telemetry. Claimed
booleans are never trusted.

A pass is hidden_cdb_host evidence: map entry, pans and intro sleeps are
debugger-forced and disclosed. It is not manual input, visible composition,
other lanes or promotion. Evidence is bound to the exact candidate and to the
pinned session producer; a change to either invalidates it.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any, Callable

import complete_hd_evidence as evidence
import hidden_soak_log_observations as soak_log


LANES = ("short_soak_ladder", "long_map_idle", "long_map_pan")
SCHEDULE = {"short_soak_ladder": evidence.SHORT_STEPS,
            "long_map_idle": (("long2h", "map-idle", 7200),),
            "long_map_pan": (("long2h", "map-pan", 7200),)}
EVIDENCE_CLASS = "approved_hidden_cdb_host_soak"
PRODUCER = "tools/hd_multires_hidden_session.py"
SESSION_SCHEMA = "hd_multires_hidden_session_v1"
LANE_KEYS = frozenset({"schema", "lane", "identity", "evidence_class", "producer", "steps", "checks",
                       "passed", "failures", "stable_stage_should_change"})
STEP_KEYS = frozenset({"tier", "route", "duration_sec", "session_report", "cdb_log"})
SESSION_IDENTITY_KEYS = frozenset({"base_sha256", "candidate_sha256", "cell_id", "launcher_manifest_sha256",
                                   "probe_sha256", "profile", "recipe_revision", "resolution",
                                   "source_closure_sha256", "stage"})
MAX_SESSION_BYTES = 16 * 1024 * 1024
MAX_LOG_BYTES = 128 * 1024 * 1024
TICKS_PER_SECOND = 64
PAN_INTERVAL_SEC = 10
# The legacy hidden soak's host telemetry limits (tools/hd_soak_report.py).
GROWTH_LIMITS = {"working_set": 64 * 1024 * 1024, "private_bytes": 64 * 1024 * 1024, "handles": 128}
MAX_SAMPLE_GAP_SEC = 5
# Host-clock corroboration tolerance; the route's own duration is its tick delta.
HOST_JITTER_SEC = 2
MAP_MECHANISMS = {"map_entry": "cdb_forced_menu_load_route", "start_animations": "cdb_fast_forward_sleeps",
                  "acquisition": "cdb_forced_bypass"}
# A hidden desktop denies DirectInput, so its natural menu needs both disclosed
# steps; neither injects input, clicks or menu state.
MENU_MECHANISMS = ({}, {"start_animations": "cdb_fast_forward_sleeps", "acquisition": "cdb_forced_bypass"})
FAILURE_TOKENS = frozenset({"HDSESSION_AV", "HDSESSION_INITIAL_REJECT", "HDSESSION_BASE_REJECT",
                            "HDSESSION_APP_REQUEST_QUIT", "HDSESSION_PLAYGAME_NO_GAME_DATA"})
MENU_READY = re.compile(r"HDSESSION_MENU_READY pid=[0-9a-fA-F]+ surface=[0-9a-fA-F`]+ width=\d+ height=\d+ "
                        r"pixels=[0-9a-fA-F`]+")
_FRAME_NAME = re.compile(r"(?:map|menu)-frame-\d{4}\.indexed8")

Reader = Callable[..., tuple[Path, bytes]]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _int(value: Any) -> bool:
    return type(value) is int


def _number(value: Any) -> bool:
    return type(value) in (int, float)


def _telemetry(samples: Any, seconds: int, notes: list[str]) -> tuple[bool, bool]:
    """Return (liveness, growth) from per-second host samples."""
    if type(samples) is not list or len(samples) < seconds - MAX_SAMPLE_GAP_SEC:
        notes.append("telemetry does not cover the route at one sample per second")
        return False, False
    keys = ("working_set", "private_bytes", "handles")
    if any(type(row) is not dict or not _number(row.get("elapsed_sec")) or
           any(not _int(row.get(key)) or row[key] <= 0 for key in keys) for row in samples):
        notes.append("telemetry samples must carry positive process counters")
        return False, False
    elapsed = [row["elapsed_sec"] for row in samples]
    live = (all(later > earlier and later - earlier <= MAX_SAMPLE_GAP_SEC for earlier, later in zip(elapsed, elapsed[1:]))
            and elapsed[0] <= MAX_SAMPLE_GAP_SEC and elapsed[-1] >= seconds - HOST_JITTER_SEC)
    if not live:
        notes.append("telemetry has a gap, does not start with the route or stops before its end")
    growth = all(max(row[key] for row in samples) - samples[0][key] <= limit for key, limit in GROWTH_LIMITS.items())
    if not growth:
        notes.append("process working set, private bytes or handles grew beyond the legacy soak limits")
    return live, growth


def _frames(session: dict, run: Path, read: Reader, width_height: set, notes: list[str]) -> tuple[bool, set]:
    """Rehash every retained frame; return (render integrity, distinct frame hashes)."""
    frames, digests = session.get("frames"), set()
    if type(frames) is not list or len(frames) < 2:
        notes.append("route must retain at least its first and final frames")
        return False, digests
    for frame in frames:
        if (type(frame) is not dict or not _FRAME_NAME.fullmatch(str(frame.get("path")))
                or (frame.get("width"), frame.get("height")) not in width_height
                or frame.get("bytes") != frame["width"] * frame["height"]
                or frame.get("coherent_snapshot_verified") is not False):
            notes.append("frame record is not a retained full-canvas software-surface frame")
            return False, digests
        _, data = read({"path": str(run / frame["path"]), "sha256": frame.get("sha256", "")}, run,
                       "retained frame", maximum=frame["bytes"])
        if len(data) != frame["bytes"] or data.count(data[:1]) == len(data):
            notes.append("retained frame is truncated or a single flat colour")
            return False, digests
        digests.add(_sha(data))
    return True, digests


def _step(row: Any, expected: tuple, base: Path, identity: dict, read: Reader, producer_sha: str,
          marker: str, repo_root: Path) -> dict:
    tier, route, seconds = expected
    label = f"{tier} {route}"
    notes: list[str] = []
    result = dict(tier=tier, route=route, completed=False, liveness=False, render=False, growth=False,
                  clean=False, progression=False, started_at=None, finished_at=None, notes=notes)
    if type(row) is not dict or set(row) != STEP_KEYS:
        notes.append(f"{label}: step requires only tier, route, duration and pinned session and log")
        return result
    if (row["tier"], row["route"], row["duration_sec"]) != expected or not _int(row["duration_sec"]):
        notes.append(f"{label}: step differs from the fixed schedule row")
        return result
    session_path, session_raw = read(row["session_report"], base, f"{label} session report",
                                     maximum=MAX_SESSION_BYTES)
    log_path, log_raw = read(row["cdb_log"], base, f"{label} CDB log", maximum=MAX_LOG_BYTES)
    session = evidence.parse_evidence_json(session_raw, f"{label} session report")
    if type(session) is not dict:
        raise ValueError(f"{label} session report must be an object")
    run = Path(str(session.get("run_directory", "")))
    try:
        run_resolved = run.resolve()
    except OSError:
        run_resolved = None
    if (run_resolved is None or session_path != run_resolved / "session-report.json"
            or log_path != run_resolved / "cdb.log" or run_resolved.is_relative_to(repo_root.resolve())):
        notes.append(f"{label}: session report and log must be the retained files of one external run directory")
        return result
    session_identity = session.get("identity")
    if (type(session_identity) is not dict or set(session_identity) != SESSION_IDENTITY_KEYS
            or any(not evidence._same_raw_json(session_identity[key], identity.get(key))
                   for key in SESSION_IDENTITY_KEYS)):
        notes.append(f"{label}: session belongs to another candidate, cell, stage or catalog")
        return result
    retained = session.get("retained_log")
    hashes = session.get("producer_source_hashes")
    completed = (
        session.get("schema") == SESSION_SCHEMA and session.get("executed") is True
        and session.get("route") == route and session.get("duration_sec") == seconds
        and session.get("environment") == "hidden_cdb_host"
        and session.get("input_responsiveness") == "not_applicable_hidden"
        and session.get("input_injected") is False and session.get("manual_input_proof") is False
        and session.get("initial_image_bytes_verified") is True
        and session.get("diagnostic_passed") is True and session.get("failures") == []
        and session.get("smoke_only") is False and session.get("acquire_only") is False
        and evidence._same_raw_json(retained, {"path": "cdb.log", "sha256": _sha(log_raw), "bytes": len(log_raw)})
        and type(hashes) is dict and hashes.get(PRODUCER) == producer_sha)
    if not completed:
        notes.append(f"{label}: session is not a passing hidden run of the pinned producer with its retained log")
    lines = [line.strip() for line in log_raw.decode("latin-1").split("\n")]
    if FAILURE_TOKENS.intersection(lines) or lines.count(marker) != 1:
        notes.append(f"{label}: log records a runtime failure or lacks the single canonical image marker")
        completed = False
    width, height = (int(value) for value in identity["resolution"].split("x"))
    if route == "menu-idle":
        completed = completed and (
            session.get("natural_menu_idle_verified") is True and session.get("forced_mechanisms") in MENU_MECHANISMS
            and session.get("input_or_callback_forced") is False
            and _number(session.get("measured_menu_host_seconds"))
            and session["measured_menu_host_seconds"] >= seconds
            and sum(bool(MENU_READY.fullmatch(line)) for line in lines) == 1)
        sizes, pan_events = {(640, 480), (width, height)}, 0
    else:
        mechanisms = dict(MAP_MECHANISMS, **({"pan": "cdb_forced_native_arrow_key"} if route == "map-pan" else {}))
        rows = soak_log.parse_soak_log(log_raw)
        order = soak_log._global_order_failures(rows)
        ticks = seconds * TICKS_PER_SECOND
        end = rows["RouteEnds"][0] if len(rows["RouteEnds"]) == 1 else None
        surface = session.get("map_surface")
        pan_events = len(rows["PanEvents"])
        pan_ok = (len(rows["PanPlans"]) == 1 and pan_events >= seconds // PAN_INTERVAL_SEC - 2
                  if route == "map-pan" else not rows["PanPlans"] and not pan_events)
        completed = completed and not rows["failures"] and not order and pan_ok and (
            session.get("map_route_completed") is True and session.get("input_or_callback_forced") is True
            and session.get("forced_mechanisms") == mechanisms and session.get("load_slot") == 0
            and end is not None and end["RouteTicks"] == ticks and end["TickDelta"] >= ticks
            and end["Pan"] == int(route == "map-pan") and end["Hits"] > 0
            and type(surface) is dict and (surface.get("width"), surface.get("height")) == (width, height)
            and _number(session.get("measured_map_host_seconds"))
            and session["measured_map_host_seconds"] >= seconds - HOST_JITTER_SEC)
        if rows["failures"] or order or not pan_ok:
            notes.append(f"{label}: retained soak rows fail the shared grammar, ordering or pan schedule")
        sizes = {(width, height)}
    live, growth = _telemetry(session.get("samples"), seconds, notes)
    render, digests = _frames(session, run_resolved, read, sizes, notes)
    cleanup = session.get("cleanup")
    clean = (type(cleanup) is dict and cleanup.get("cleanup_verified") is True
             and session.get("live_saves_unchanged") is True and session.get("launch_artifacts_unchanged") is True
             and session.get("failures") == [])
    started, finished = evidence._time(session.get("started_at")), evidence._time(session.get("finished_at"))
    if (finished - started).total_seconds() < seconds:
        notes.append(f"{label}: session wall interval is shorter than the route")
        completed = False
    result.update(completed=completed, liveness=live, render=render, growth=growth, clean=clean,
                  progression=route == "map-pan" and pan_events >= seconds // PAN_INTERVAL_SEC - 2 and len(digests) > 1,
                  started_at=started, finished_at=finished)
    return result


def replay(lane: str, report: dict, report_path: Path, identity: dict, read: Reader,
           producer_raw: bytes, marker: str, repo_root: Path) -> tuple[dict, list[str]]:
    """Recompute a soak lane's required checks from its pinned retained runs."""
    schedule = SCHEDULE[lane]
    steps = report.get("steps")
    if type(steps) is not list or len(steps) != len(schedule):
        rows = []
        failures = [f"{lane} requires exactly its {len(schedule)} fixed schedule rows"]
    else:
        rows = [_step(row, expected, report_path.parent, identity, read, _sha(producer_raw), marker, repo_root)
                for row, expected in zip(steps, schedule)]
        failures = [note for row in rows for note in row["notes"]]
    sequential = len(rows) == len(schedule) and all(
        earlier["finished_at"] is not None and later["started_at"] is not None
        and earlier["finished_at"] <= later["started_at"] for earlier, later in zip(rows, rows[1:]))
    every = lambda key: bool(rows) and len(rows) == len(schedule) and all(row[key] for row in rows)
    values = {"ordered_ladder_completed": every("completed") and sequential, "route_completed": every("completed"),
              "process_liveness": every("liveness"), "render_integrity": every("render"),
              "process_growth": every("growth"), "frame_progression": every("progression"),
              "clean_stop": every("clean")}
    # The fixed policy, not this replay, chooses which checks a lane requires and their order.
    checks = {name: {"passed": values[name], "failures": [] if values[name] else [name]}
              for name in evidence.LANES[lane][1]}
    return checks, failures

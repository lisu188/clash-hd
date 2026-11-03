#!/usr/bin/env python3
"""Hidden-host continuity lane replay for the matrix-cell release context.

save_load_roundtrip pins two hd_multires_hidden_session runs of the fixed
forced-save extra (tools/hd_multires_route_extras.py), each with its CDB log
and the save it retained. Slot 0 is saved into slot 7, then slot 7 is
reloaded and saved into slot 8, in one isolated asset root. The replay rereads
every file and binds both runs to the freshly authenticated cell and the
pinned session producer. It replays each log's markers and requires the
reload to read exactly the first save's bytes. Resaving must reproduce the
first save except the process-local pointer fields the save format copies
verbatim (route_extras.POINTER_FIELDS); raw hashes stay recorded. Claimed
booleans are never trusted.

A pass is hidden_cdb_host continuity evidence: map entry and both saves are
debugger-forced and disclosed. It is not manual input, a played turn or day,
other lanes or promotion. Evidence is bound to the exact candidate and the
pinned session producer; a change to either invalidates it.
"""
from __future__ import annotations

from pathlib import Path, PureWindowsPath
from typing import Any

import complete_hd_evidence as evidence
import hd_multires_route_extras as route_extras
import matrix_soak_lanes as soak

LANES = ("save_load_roundtrip",)
EVIDENCE_CLASS = "approved_hidden_cdb_continuity"
PRODUCER = soak.PRODUCER
SCHEDULE = {"save_load_roundtrip": (
    ("save", {"name": route_extras.FORCED_SAVE, "load_slot": 0, "save_slot": 7}),
    ("reload_save", {"name": route_extras.FORCED_SAVE, "load_slot": 7, "save_slot": 8}))}
LANE_KEYS = soak.LANE_KEYS
STEP_KEYS = frozenset({"role", "session_report", "cdb_log", "save"})
STEP_BOUNDS = {"session_report": soak.MAX_SESSION_BYTES, "cdb_log": soak.MAX_LOG_BYTES,
               "save": route_extras.MAX_SAVE_BYTES}
# The session stages isolated game state only under this root.
EXTERNAL = PureWindowsPath("C:/ClashTests")


def _files(files: Any, loaded: str, saved: str, save_raw: bytes) -> dict | None:
    """The unchanged loaded-slot hash and the rewritten save's hash, or None."""
    if type(files) is not dict or set(files) != {"before", "after", "retained"} \
            or any(type(files[key]) is not dict for key in files):
        return None
    before, after, kept = files["before"], files["after"], files["retained"]
    if set(before) != {loaded, saved} or set(after) != {loaded, saved} or set(kept) != {saved}:
        return None
    digest = soak._sha(save_raw)
    old, new = before[saved], after[saved]
    rewritten = type(new) is dict and new.get("sha256") == digest and (old is None or (
        type(old) is dict and soak._int(old.get("mtime_ns")) and soak._int(new.get("mtime_ns"))
        and new["mtime_ns"] > old["mtime_ns"]))
    source = before[loaded]
    if not rewritten or type(source) is not dict or not evidence._same_raw_json(source, after[loaded]) \
            or not evidence._same_raw_json(kept[saved], {"path": f"route-extra/{PureWindowsPath(saved).name}",
                                                         "sha256": digest, "bytes": len(save_raw)}):
        return None
    return dict(loaded=source.get("sha256"), saved=digest)


def _step(row: Any, expected: tuple, base: Path, identity: dict, read: soak.Reader, producer_sha: str,
          marker: str, repo_root: Path) -> dict:
    role, request = expected
    notes: list[str] = []
    result = dict(role=role, completed=False, clean=False, live_saves=False, asset_root=None, loaded=None,
                  saved=None, state=None, started_at=None, finished_at=None, notes=notes)
    if type(row) is not dict or set(row) != STEP_KEYS or row["role"] != role:
        notes.append(f"{role}: step requires only its fixed role and pinned session, log and save")
        return result
    spec = route_extras.prepare(request, route=route_extras.ROUTE, duration=route_extras.DURATION)
    loaded, saved = spec["pre_files"][0], spec["post_files"][0]
    session_path, session_raw = read(row["session_report"], base, f"{role} session report",
                                     maximum=STEP_BOUNDS["session_report"])
    log_path, log_raw = read(row["cdb_log"], base, f"{role} CDB log", maximum=STEP_BOUNDS["cdb_log"])
    save_path, save_raw = read(row["save"], base, f"{role} retained save", maximum=STEP_BOUNDS["save"])
    session = evidence.parse_evidence_json(session_raw, f"{role} session report")
    if type(session) is not dict:
        raise ValueError(f"{role} session report must be an object")
    run = Path(str(session.get("run_directory", "")))
    try:
        run_resolved = run.resolve()
    except OSError:
        run_resolved = None
    if (run_resolved is None or session_path != run_resolved / "session-report.json"
            or log_path != run_resolved / "cdb.log"
            or save_path != run_resolved / "route-extra" / PureWindowsPath(saved).name
            or run_resolved.is_relative_to(repo_root.resolve())):
        notes.append(f"{role}: session report, log and save must be the retained files of one external run directory")
        return result
    session_identity = session.get("identity")
    if (type(session_identity) is not dict or set(session_identity) != soak.SESSION_IDENTITY_KEYS
            or any(not evidence._same_raw_json(session_identity[key], identity.get(key))
                   for key in soak.SESSION_IDENTITY_KEYS)):
        notes.append(f"{role}: session belongs to another candidate, cell, stage or catalog")
        return result
    retained, hashes = session.get("retained_log"), session.get("producer_source_hashes")
    completed = (
        session.get("schema") == soak.SESSION_SCHEMA and session.get("executed") is True
        and session.get("route") == route_extras.ROUTE and session.get("duration_sec") == route_extras.DURATION
        and session.get("environment") == "hidden_cdb_host"
        and session.get("input_responsiveness") == "not_applicable_hidden"
        and session.get("input_injected") is False and session.get("manual_input_proof") is False
        and session.get("initial_image_bytes_verified") is True
        and session.get("diagnostic_passed") is True and session.get("failures") == []
        and session.get("smoke_only") is False and session.get("acquire_only") is False
        and session.get("map_route_completed") is True and session.get("input_or_callback_forced") is True
        and evidence._same_raw_json(session.get("forced_mechanisms"), {**soak.MAP_MECHANISMS, **spec["mechanisms"]})
        and session.get("load_slot") == spec["load_slot"]
        and evidence._same_raw_json(session.get("route_extra"), spec)
        and evidence._same_raw_json(retained, {"path": "cdb.log", "sha256": soak._sha(log_raw), "bytes": len(log_raw)})
        and type(hashes) is dict and hashes.get(PRODUCER) == producer_sha)
    if not completed:
        notes.append(f"{role}: session is not a passing forced-save run of the pinned producer with its retained log")
    lines = [line.strip() for line in log_raw.decode("latin-1").split("\n")]
    if soak.FAILURE_TOKENS.intersection(lines) or lines.count(marker) != 1:
        notes.append(f"{role}: log records a runtime failure or lacks the single canonical image marker")
        completed = False
    observed, marker_failures = route_extras.observe(spec, log_raw.decode("latin-1"))
    if marker_failures or not evidence._same_raw_json(session.get("route_extra_observations"), observed):
        notes.append(f"{role}: replayed save markers fail or differ from the recorded observations")
        completed = False
    state = _files(session.get("route_extra_files"), loaded, saved, save_raw)
    if state is None:
        notes.append(f"{role}: retained files do not prove an unchanged loaded slot and a rewritten save")
        completed = False
    try:
        game_state = route_extras.state_digest(save_raw)
    except ValueError as error:
        notes.append(f"{role}: {error}")
        game_state, completed = None, False
    cleanup, asset_root = session.get("cleanup"), session.get("asset_root")
    clean = (type(cleanup) is dict and cleanup.get("cleanup_verified") is True
             and session.get("launch_artifacts_unchanged") is True and session.get("failures") == [])
    started, finished = evidence._time(session.get("started_at")), evidence._time(session.get("finished_at"))
    result.update(completed=completed, clean=clean, live_saves=session.get("live_saves_unchanged") is True,
                  asset_root=asset_root if type(asset_root) is str else None,
                  loaded=state and state["loaded"], saved=state and state["saved"], state=game_state,
                  started_at=started, finished_at=finished)
    return result


def _isolated(root: str | None, repo_root: Path) -> bool:
    if root is None:
        return False
    path = PureWindowsPath(root)
    return path.is_relative_to(EXTERNAL) and path != EXTERNAL and not path.is_relative_to(PureWindowsPath(repo_root))


def replay(lane: str, report: dict, report_path: Path, identity: dict, read: soak.Reader,
           producer_raw: bytes, marker: str, repo_root: Path) -> tuple[dict, list[str]]:
    """Recompute a continuity lane's required checks from its pinned retained runs."""
    schedule = SCHEDULE[lane]
    steps = report.get("steps")
    if type(steps) is not list or len(steps) != len(schedule):
        rows, failures = [], [f"{lane} requires exactly its {len(schedule)} fixed runs"]
    else:
        rows = [_step(row, expected, report_path.parent, identity, read, soak._sha(producer_raw), marker, repo_root)
                for row, expected in zip(steps, schedule)]
        failures = [note for row in rows for note in row["notes"]]
    full = len(rows) == len(schedule)
    roots = {row["asset_root"] for row in rows}
    one_root = full and len(roots) == 1 and None not in roots
    sequential = full and all(earlier["finished_at"] is not None and later["started_at"] is not None
                              and earlier["finished_at"] <= later["started_at"] for earlier, later in zip(rows, rows[1:]))
    first, second = (rows[0], rows[1]) if full else (None, None)
    values = {
        "roundtrip_completed": full and sequential and one_root and all(row["completed"] and row["clean"] for row in rows),
        # The reload reads exactly the first save's bytes, and resaving reproduces its game state.
        "state_hashes_match": full and first["saved"] is not None and first["saved"] == second["loaded"]
                              and first["state"] is not None and first["state"] == second["state"],
        "isolated_saves": one_root and _isolated(next(iter(roots)), repo_root),
        "live_saves_unchanged": full and all(row["live_saves"] for row in rows),
    }
    # The fixed policy, not this replay, chooses which checks a lane requires and their order.
    checks = {name: {"passed": values[name], "failures": [] if values[name] else [name]}
              for name in evidence.LANES[lane][1]}
    return checks, failures

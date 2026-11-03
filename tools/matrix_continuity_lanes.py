#!/usr/bin/env python3
"""Hidden-host continuity lane replay for the matrix-cell release context.

Each lane pins hd_multires_hidden_session runs of a fixed continuity extra
(tools/hd_multires_route_extras.py), each with its CDB log and every save it
retained, in one isolated asset root. The replay rereads every file and binds
each run to the freshly authenticated cell and the pinned session producer. It
replays the extra's markers and requires the loaded slot unchanged and every
written slot rewritten. Claimed booleans are never trusted.

save_load_roundtrip: slot 0 is saved into slot 7, then slot 7 is reloaded and
saved into slot 8. The reload must read exactly the first save's bytes, and
resaving must reproduce the first save except the process-local pointer fields
the save format copies verbatim (route_extras.POINTER_FIELDS); raw hashes stay
recorded.

turn_advancement: one forced-turn run saves slot 5, calls the native
nextPlayer until the day word has advanced by one and player 0 is current
again, then saves slot 6. Every active player must take its turn in order,
every call must return, exactly one native day increment must occur, the two
saves' states must differ, and the map must keep redrawing to its route end
with a non-flat frame after the day returned.

campaign_routes: one forced-campaign run saves slot 3, drives three consecutive
day transitions and saves slot 4; a forced-save run then reloads slot 4 and
saves it into slot 2. Each day must return through its banner and release
wait to player 0, the reload must read exactly the campaign's end save and
reproduce its state, and the map must keep redrawing after the last day.

A pass is hidden_cdb_host continuity evidence: map entry, saves and turn
calls are debugger-forced and disclosed. It is not manual input, a played
turn decision, other lanes or promotion. Evidence is bound to the exact
candidate and the pinned session producer; a change to either invalidates it.
"""
from __future__ import annotations

from pathlib import Path, PureWindowsPath
import re
from typing import Any

import complete_hd_evidence as evidence
import hd_multires_route_extras as route_extras
import matrix_soak_lanes as soak

LANES = ("save_load_roundtrip", "turn_advancement", "campaign_routes")
EVIDENCE_CLASS = "approved_hidden_cdb_continuity"
PRODUCER = soak.PRODUCER
SCHEDULE = {
    "save_load_roundtrip": (
        ("save", {"name": route_extras.FORCED_SAVE, "load_slot": 0, "save_slot": 7}),
        ("reload_save", {"name": route_extras.FORCED_SAVE, "load_slot": 7, "save_slot": 8})),
    "turn_advancement": (
        ("turn", {"name": route_extras.FORCED_TURN, "load_slot": 0, "before_slot": 5, "after_slot": 6}),),
    "campaign_routes": (
        ("campaign", {"name": route_extras.FORCED_CAMPAIGN, "load_slot": 0, "before_slot": 3, "after_slot": 4,
                      "days": 3}),
        ("reload_end", {"name": route_extras.FORCED_SAVE, "load_slot": 4, "save_slot": 2})),
}
LANE_KEYS = soak.LANE_KEYS
# Each written slot is pinned under its own step key, in the extra's post_files order, per schedule row.
SAVE_KEYS = {"save_load_roundtrip": (("save",), ("save",)), "turn_advancement": (("before_save", "after_save"),),
             "campaign_routes": (("before_save", "after_save"), ("save",))}
STEP_BOUNDS = {"session_report": soak.MAX_SESSION_BYTES, "cdb_log": soak.MAX_LOG_BYTES,
               **{key: route_extras.MAX_SAVE_BYTES for rows in SAVE_KEYS.values() for keys in rows for key in keys}}
# The session stages isolated game state only under this root.
EXTERNAL = PureWindowsPath("C:/ClashTests")
ROUTE_START = re.compile(r"SOAK_ROUTE_START route_ticks=\d+ pan=\d+ player=\d+ tick=(\d+) .*")


def _files(files: Any, loaded: str, saves: dict[str, bytes]) -> dict | None:
    """The unchanged loaded-slot hash and each rewritten save's hash, or None."""
    if type(files) is not dict or set(files) != {"before", "after", "retained"} \
            or any(type(files[key]) is not dict for key in files):
        return None
    before, after, kept = files["before"], files["after"], files["retained"]
    if set(before) != {loaded, *saves} or set(after) != {loaded, *saves} or set(kept) != set(saves):
        return None
    for name, raw in saves.items():
        digest, old, new = soak._sha(raw), before[name], after[name]
        rewritten = type(new) is dict and new.get("sha256") == digest and (old is None or (
            type(old) is dict and soak._int(old.get("mtime_ns")) and soak._int(new.get("mtime_ns"))
            and new["mtime_ns"] > old["mtime_ns"]))
        if not rewritten or not evidence._same_raw_json(kept[name], {
                "path": f"route-extra/{PureWindowsPath(name).name}", "sha256": digest, "bytes": len(raw)}):
            return None
    source = before[loaded]
    if type(source) is not dict or not evidence._same_raw_json(source, after[loaded]):
        return None
    return dict(loaded=source.get("sha256"), saved={name: soak._sha(raw) for name, raw in saves.items()})


def _post_day(session: dict, observed: dict, lines: list[str], run: Path, read: soak.Reader,
              identity: dict, notes: list[str]) -> bool:
    """After the day returned, the map kept redrawing to its route end with a non-flat frame."""
    width, height = (int(value) for value in identity["resolution"].split("x"))
    starts = [match for line in lines if (match := ROUTE_START.fullmatch(line))]
    done = [index for index, line in enumerate(lines) if line.startswith(("HDTURN_DONE ", "HDCAMP_DONE "))]
    ends = [index for index, line in enumerate(lines) if line.startswith("SOAK_ROUTE_END ")]
    render, _ = soak._frames(session, run, read, {(width, height)}, notes)
    if len(starts) != 1 or len(done) != 1 or len(ends) != 1 or not observed.get("returns") or not render:
        return False
    day_returned = (observed["returns"][-1][3] - int(starts[0][1])) / soak.TICKS_PER_SECOND
    final = session["frames"][-1]
    return done[0] < ends[0] and soak._number(final.get("elapsed_sec")) and final["elapsed_sec"] > day_returned


def _step(lane: str, index: int, row: Any, expected: tuple, base: Path, identity: dict, read: soak.Reader,
          producer_sha: str, marker: str, repo_root: Path) -> dict:
    role, request = expected
    notes: list[str] = []
    result = dict(role=role, completed=False, clean=False, live_saves=False, asset_root=None, loaded=None,
                  saved={}, states={}, observed={}, post_day=False, started_at=None, finished_at=None, notes=notes)
    keys = SAVE_KEYS[lane][index]
    if type(row) is not dict or set(row) != {"role", "session_report", "cdb_log", *keys} or row["role"] != role:
        notes.append(f"{role}: step requires only its fixed role and pinned session, log and saves")
        return result
    spec = route_extras.prepare(request, route=route_extras.ROUTE, duration=route_extras.DURATION)
    loaded = spec["pre_files"][0]
    session_path, session_raw = read(row["session_report"], base, f"{role} session report",
                                     maximum=STEP_BOUNDS["session_report"])
    log_path, log_raw = read(row["cdb_log"], base, f"{role} CDB log", maximum=STEP_BOUNDS["cdb_log"])
    pinned = {name: read(row[key], base, f"{role} retained {PureWindowsPath(name).name}", maximum=STEP_BOUNDS[key])
              for key, name in zip(keys, spec["post_files"])}
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
            or any(path != run_resolved / "route-extra" / PureWindowsPath(name).name for name, (path, _) in pinned.items())
            or run_resolved.is_relative_to(repo_root.resolve())):
        notes.append(f"{role}: session report, log and saves must be the retained files of one external run directory")
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
        notes.append(f"{role}: session is not a passing {spec['name']} run of the pinned producer with its retained log")
    lines = [line.strip() for line in log_raw.decode("latin-1").split("\n")]
    if soak.FAILURE_TOKENS.intersection(lines) or lines.count(marker) != 1:
        notes.append(f"{role}: log records a runtime failure or lacks the single canonical image marker")
        completed = False
    observed, marker_failures = route_extras.observe(spec, log_raw.decode("latin-1"))
    if marker_failures or not evidence._same_raw_json(session.get("route_extra_observations"), observed):
        notes.append(f"{role}: replayed {spec['name']} markers fail or differ from the recorded observations")
        completed = False
    state = _files(session.get("route_extra_files"), loaded, {name: raw for name, (_, raw) in pinned.items()})
    if state is None:
        notes.append(f"{role}: retained files do not prove an unchanged loaded slot and rewritten saves")
        completed = False
    states = {}
    for name, (_, raw) in pinned.items():
        try:
            states[name] = route_extras.state_digest(raw)
        except ValueError as error:
            notes.append(f"{role}: {error}")
            completed = False
    cleanup, asset_root = session.get("cleanup"), session.get("asset_root")
    clean = (type(cleanup) is dict and cleanup.get("cleanup_verified") is True
             and session.get("launch_artifacts_unchanged") is True and session.get("failures") == [])
    started, finished = evidence._time(session.get("started_at")), evidence._time(session.get("finished_at"))
    post_day = spec["name"] in (route_extras.FORCED_TURN, route_extras.FORCED_CAMPAIGN) and _post_day(
        session, observed, lines, run_resolved, read, identity, notes)
    result.update(completed=completed, clean=clean, live_saves=session.get("live_saves_unchanged") is True,
                  asset_root=asset_root if type(asset_root) is str else None,
                  loaded=state and state["loaded"], saved=state["saved"] if state else {}, states=states,
                  observed=observed, post_day=post_day, started_at=started, finished_at=finished)
    return result


def _isolated(root: str | None, repo_root: Path) -> bool:
    if root is None:
        return False
    path = PureWindowsPath(root)
    return path.is_relative_to(EXTERNAL) and path != EXTERNAL and not path.is_relative_to(PureWindowsPath(repo_root))


def _turn_values(row: dict, repo_root: Path) -> dict:
    observed = row["observed"]
    base = (row["completed"] and row["clean"] and row["live_saves"] and _isolated(row["asset_root"], repo_root)
            and bool(observed.get("start")) and observed.get("full_day") is not None)
    if not base:
        return dict.fromkeys(("player_cycle_completed", "day_advanced", "call_return_observed", "post_day_map_health"),
                             False)
    active, full_day, returns = observed["start"]["active"], observed["full_day"], observed["returns"]
    # Every active player after 0 takes its turn in order, then the new day returns to player 0.
    cycle = [player for player in range(1, len(active)) if active[player]] + [0]
    states = list(row["states"].values())
    return {
        "player_cycle_completed": [returned[1] for returned in returns] == cycle,
        "day_advanced": (full_day["final_day"] == (full_day["initial_day"] + 1) & 0xFFFF
                         and len(observed["day_increments"]) == 1
                         and observed["day_increments"][0][0] == full_day["advances"]
                         and len(states) == 2 and states[0] != states[1]),
        "call_return_observed": (len(observed["calls"]) == len(returns) == full_day["advances"]
                                 and observed["release_returns"] == observed["release_waits"]),
        "post_day_map_health": row["post_day"],
    }


def _campaign_values(rows: list[dict], repo_root: Path) -> dict:
    campaign, reload = rows
    observed, days = campaign["observed"], SCHEDULE["campaign_routes"][0][1]["days"]
    roots = {row["asset_root"] for row in rows}
    healthy = all(row["completed"] and row["clean"] and row["live_saves"] for row in rows) \
        and len(roots) == 1 and _isolated(next(iter(roots)), repo_root)
    sequential = (campaign["finished_at"] is not None and reload["started_at"] is not None
                  and campaign["finished_at"] <= reload["started_at"])
    full_day = observed.get("full_day")
    end, before = campaign["saved"].get("save/4.dat"), campaign["states"].get("save/3.dat")
    return {
        # Each requested day is its own banner, release wait and return to the map at player 0.
        "repeated_screen_transitions": healthy and len(observed.get("days_returned", [])) == days >= 2
                                       and observed["banner_exits"] == days
                                       and observed["release_waits"] == observed["release_returns"] == days,
        "route_completed": healthy and sequential and full_day is not None,
        # The end state differs from the start, and reloading and resaving it reproduces it.
        "state_consistent": (healthy and full_day is not None
                             and full_day["final_day"] == (full_day["initial_day"] + days) & 0xFFFF
                             and end is not None and end == reload["loaded"]
                             and campaign["states"].get("save/4.dat") not in (None, before)
                             and campaign["states"]["save/4.dat"] == reload["states"].get("save/2.dat")),
        "post_return_map_health": healthy and campaign["post_day"],
    }


def replay(lane: str, report: dict, report_path: Path, identity: dict, read: soak.Reader,
           producer_raw: bytes, marker: str, repo_root: Path) -> tuple[dict, list[str]]:
    """Recompute a continuity lane's required checks from its pinned retained runs."""
    schedule = SCHEDULE[lane]
    steps = report.get("steps")
    if type(steps) is not list or len(steps) != len(schedule):
        rows, failures = [], [f"{lane} requires exactly its {len(schedule)} fixed runs"]
    else:
        rows = [_step(lane, index, row, expected, report_path.parent, identity, read, soak._sha(producer_raw),
                      marker, repo_root) for index, (row, expected) in enumerate(zip(steps, schedule))]
        failures = [note for row in rows for note in row["notes"]]
    full = len(rows) == len(schedule)
    if lane == "turn_advancement":
        values = _turn_values(rows[0], repo_root) if full else dict.fromkeys(evidence.LANES[lane][1], False)
    elif lane == "campaign_routes":
        values = _campaign_values(rows, repo_root) if full else dict.fromkeys(evidence.LANES[lane][1], False)
    else:
        roots = {row["asset_root"] for row in rows}
        one_root = full and len(roots) == 1 and None not in roots
        sequential = full and all(earlier["finished_at"] is not None and later["started_at"] is not None
                                  and earlier["finished_at"] <= later["started_at"]
                                  for earlier, later in zip(rows, rows[1:]))
        first, second = (rows[0], rows[1]) if full else (None, None)
        saved = first["saved"].get("save/7.dat") if full else None
        values = {
            "roundtrip_completed": full and sequential and one_root and all(row["completed"] and row["clean"]
                                                                            for row in rows),
            # The reload reads exactly the first save's bytes, and resaving reproduces its game state.
            "state_hashes_match": (full and saved is not None and saved == second["loaded"]
                                   and first["states"].get("save/7.dat") is not None
                                   and first["states"]["save/7.dat"] == second["states"].get("save/8.dat")),
            "isolated_saves": one_root and _isolated(next(iter(roots)), repo_root),
            "live_saves_unchanged": full and all(row["live_saves"] for row in rows),
        }
    # The fixed policy, not this replay, chooses which checks a lane requires and their order.
    checks = {name: {"passed": values[name], "failures": [] if values[name] else [name]}
              for name in evidence.LANES[lane][1]}
    return checks, failures

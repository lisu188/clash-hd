"""Synthetic source-artifact fixtures for the matrix-cell hidden save/load round trip replay.

Each fixture is a complete retained run directory: session report, CDB log and
the save the run retained. No game, debugger or capture runs.
"""
from __future__ import annotations

import copy
from datetime import timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import hd_multires_route_extras as extras
import matrix_continuity_lanes as continuity
import matrix_release_evidence as release
from test_matrix_soak_lanes import IDENTITY, MARKER, PRODUCER, START, sha, write

LANE = "save_load_roundtrip"
SOURCE = b"slot zero" + bytes(range(64))
STATE = bytes((index * 7) % 251 for index in range(extras.SAVE_BYTES))
# The first record's process-local pointer field, as a file offset.
POINTER = extras.SAVE_HEADER_BYTES + extras.POINTER_FIELDS[0][0] + extras.POINTER_FIELDS[0][3]
ASSETS = "C:/ClashTests/hd-continuity-assets-synthetic"


def flipped(data: bytes, offset: int) -> bytes:
    return data[:offset] + bytes([data[offset] ^ 1]) + data[offset + 1:]


class Run:
    """One retained forced-save run directory, editable before it is written."""

    def __init__(self, root: Path, role: str, request: dict, started, *, loaded: bytes, saved: bytes):
        self.spec = extras.prepare(request, route="map-idle", duration=120)
        load, save = self.spec["load_slot"], self.spec["save_slot"]
        self.role, self.directory, self.saved = role, root / f"session-{role}", saved
        self.log_lines = [MARKER, "HDSESSION_TARGET pid=abc base=00400000",
                          *[f"HDSESSION_LOADSAVE selected_arg={load} selected_global={load} accept=1 choice=5 "
                            "gd=0a000000"] * 2,
                          f"HDCONT_SAVE_CALL slot={save} load_slot={load} gd=0a000000 player=0 scroll=(10,17) tick=100",
                          f"HDCONT_SAVE_RETURNED slot={save} eax=1 tick=101",
                          "SOAK_ROUTE_START route_ticks=7680 pan=0 player=0 tick=102 gd=0a000000 scroll=(10,17)"]
        source, target = self.spec["pre_files"][0], self.spec["post_files"][0]
        state = lambda data, mtime: {"sha256": sha(data), "bytes": len(data), "mtime_ns": mtime}
        self.session = {
            "schema": continuity.soak.SESSION_SCHEMA, "executed": True, "route": "map-idle", "duration_sec": 120,
            "identity": {key: IDENTITY[key] for key in continuity.soak.SESSION_IDENTITY_KEYS},
            "environment": "hidden_cdb_host", "input_responsiveness": "not_applicable_hidden",
            "input_injected": False, "manual_input_proof": False, "initial_image_bytes_verified": True,
            "diagnostic_passed": True, "failures": [], "smoke_only": False, "acquire_only": False,
            "map_route_completed": True, "input_or_callback_forced": True,
            "forced_mechanisms": dict(continuity.soak.MAP_MECHANISMS, **extras.MECHANISMS),
            "load_slot": load, "route_extra": copy.deepcopy(self.spec), "asset_root": ASSETS,
            "producer_source_hashes": {continuity.PRODUCER: sha(PRODUCER)},
            "run_directory": str(self.directory),
            "route_extra_files": {
                "before": {source: state(loaded, 5), target: state(b"old", 6)},
                "after": {source: state(loaded, 5), target: state(saved, 9)},
                "retained": {target: {"path": f"route-extra/{save}.dat", "sha256": sha(saved), "bytes": len(saved)}}},
            "cleanup": {"cleanup_verified": True}, "live_saves_unchanged": True, "launch_artifacts_unchanged": True,
            "started_at": started.isoformat(), "finished_at": (started + timedelta(seconds=150)).isoformat(),
        }

    def save(self) -> dict:
        log = ("\r\n".join(self.log_lines) + "\r\n").encode("ascii")
        session = copy.deepcopy(self.session)
        session.setdefault("retained_log", {"path": "cdb.log", "sha256": sha(log), "bytes": len(log)})
        session.setdefault("route_extra_observations", extras.observe(self.spec, log.decode("latin-1"))[0])
        return {"role": self.role,
                "session_report": write(self.directory / "session-report.json", json.dumps(session).encode()),
                "cdb_log": write(self.directory / "cdb.log", log),
                "save": write(self.directory / "route-extra" / f"{self.spec['save_slot']}.dat", self.saved)}


class RoundTripReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clash-continuity-lanes-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cases = 0

    def lane(self, *, resaved=STATE):
        self.cases += 1
        root = self.root / f"case-{self.cases}"
        (first, request_a), (second, request_b) = continuity.SCHEDULE[LANE]
        runs = [Run(root, first, request_a, START, loaded=SOURCE, saved=STATE),
                Run(root, second, request_b, START + timedelta(seconds=300), loaded=STATE, saved=resaved)]
        return root, runs

    def replay(self, root, runs, *, producer=PRODUCER, mutate=None):
        report = {"steps": [run.save() for run in runs]}
        if mutate:
            mutate(report)
        return continuity.replay(LANE, report, root / "lane.json", IDENTITY, release._reference_bytes, producer,
                                 MARKER, Path(__file__).resolve().parents[1])

    def failed(self, root, runs, **kwargs):
        checks, failures = self.replay(root, runs, **kwargs)
        return {key for key, value in checks.items() if not value["passed"]}, failures

    def test_round_trip_passes_only_from_its_retained_runs_in_policy_order(self):
        checks, failures = self.replay(*self.lane())
        self.assertEqual(list(checks), list(continuity.evidence.LANES[LANE][1]))
        self.assertFalse(failures)
        self.assertTrue(all(value == {"passed": True, "failures": []} for value in checks.values()), checks)
        self.assertEqual(continuity.STEP_BOUNDS["save"], extras.MAX_SAVE_BYTES)

    def test_each_gate_fails_closed_on_its_own_artifact(self):
        everything = set(continuity.evidence.LANES[LANE][1])
        cases = {
            # Resaving the reloaded game must reproduce its state outside the pointer fields.
            "state drift": (dict(resaved=flipped(STATE, 100)), None, {"state_hashes_match"}, None),
            "truncated save": (dict(resaved=STATE + b"!"), None, {"roundtrip_completed", "state_hashes_match"},
                               "16-byte name"),
            "other reload source": (None, lambda runs: runs[1].session["route_extra_files"]["before"]
                                    ["save/7.dat"].__setitem__("sha256", "9" * 64), {"roundtrip_completed",
                                    "state_hashes_match"}, "unchanged loaded slot"),
            "tampered retained save": (None, lambda runs: setattr(runs[0], "saved", STATE + b"x"),
                                       {"roundtrip_completed", "state_hashes_match"}, "rewritten save"),
            "save not rewritten": (None, lambda runs: runs[1].session["route_extra_files"]["after"]["save/8.dat"]
                                   .__setitem__("mtime_ns", 6), {"roundtrip_completed", "state_hashes_match"},
                                   "rewritten save"),
            "native save failed": (None, lambda runs: runs[0].log_lines.__setitem__(5, "HDCONT_SAVE_RETURNED slot=7 eax=0 tick=101"),
                                   {"roundtrip_completed"}, "save markers"),
            "another candidate": (None, lambda runs: runs[1].session["identity"].__setitem__("candidate_sha256", "9" * 64),
                                  everything, "another candidate"),
            "producer": (None, lambda runs: runs[0].session["producer_source_hashes"].__setitem__(continuity.PRODUCER, "8" * 64),
                         {"roundtrip_completed"}, "pinned producer"),
            "soak run": (None, lambda runs: runs[0].session.__setitem__("route_extra", None), {"roundtrip_completed"},
                         "forced-save run"),
            "undisclosed save": (None, lambda runs: runs[0].session.__setitem__("forced_mechanisms",
                                 dict(continuity.soak.MAP_MECHANISMS)), {"roundtrip_completed"}, "forced-save run"),
            "two roots": (None, lambda runs: runs[1].session.__setitem__("asset_root", ASSETS + "-2"),
                          {"roundtrip_completed", "isolated_saves"}, None),
            "live game root": (None, lambda runs: [run.session.__setitem__("asset_root", "C:/Clash") for run in runs],
                               {"isolated_saves"}, None),
            "live saves": (None, lambda runs: runs[1].session.__setitem__("live_saves_unchanged", False),
                           {"live_saves_unchanged"}, None),
            "reload first": (None, lambda runs: runs[1].session.__setitem__("started_at", runs[0].session["started_at"]),
                             {"roundtrip_completed"}, None),
            "cleanup": (None, lambda runs: runs[1].session["cleanup"].__setitem__("cleanup_verified", False),
                        {"roundtrip_completed"}, None),
            "failure token": (None, lambda runs: runs[1].log_lines.append("HDSESSION_AV"), {"roundtrip_completed"},
                              "runtime failure"),
        }
        for label, (options, mutate, expected, note) in cases.items():
            with self.subTest(case=label):
                root, runs = self.lane(**(options or {}))
                if mutate:
                    mutate(runs)
                failed, failures = self.failed(root, runs)
                self.assertEqual(failed, expected, failures)
                if note:
                    self.assertTrue(any(note in item for item in failures), failures)

    def test_process_pointer_residue_alone_is_not_state_drift(self):
        root, runs = self.lane(resaved=flipped(flipped(STATE, POINTER + 2), POINTER))
        checks, failures = self.replay(root, runs)
        self.assertFalse(failures)
        self.assertTrue(all(value["passed"] for value in checks.values()), checks)
        # One byte past the field is game state again.
        root, runs = self.lane(resaved=flipped(STATE, POINTER + 4))
        self.assertEqual(self.failed(root, runs)[0], {"state_hashes_match"})

    def test_schedule_roles_and_external_location_are_fixed(self):
        for mutate in (lambda report: report["steps"].reverse(),
                       lambda report: report["steps"].pop(),
                       lambda report: report["steps"][0].__setitem__("extra", True),
                       lambda report: report["steps"][1].pop("save")):
            with self.subTest(mutate=mutate):
                root, runs = self.lane()
                failed, failures = self.failed(root, runs, mutate=mutate)
                self.assertIn("roundtrip_completed", failed)
                self.assertTrue(failures)
        root, runs = self.lane()
        failed, _ = self.failed(root, runs, producer=b"another producer\n")
        self.assertIn("roundtrip_completed", failed)
        repo_root = Path(__file__).resolve().parents[1]
        checks, failures = continuity.replay(LANE, {"steps": [run.save() for run in runs]}, root / "lane.json",
                                             IDENTITY, release._reference_bytes, PRODUCER, MARKER, root)
        self.assertTrue(any("external run directory" in item for item in failures), failures)
        self.assertFalse(checks["roundtrip_completed"]["passed"])
        self.assertTrue(repo_root.is_dir())

    def test_release_dispatch_pins_every_step_file_with_its_bound(self):
        root, runs = self.lane()
        producer = (release.matrix.ROOT / continuity.PRODUCER).resolve()
        for run in runs:
            run.session["producer_source_hashes"] = {continuity.PRODUCER: sha(producer.read_bytes())}
        steps = [run.save() for run in runs]
        checks, _ = continuity.replay(LANE, {"steps": steps}, root / "lane.json", IDENTITY, release._reference_bytes,
                                      producer.read_bytes(), MARKER, release.matrix.ROOT)
        report = {"schema": release.LANE_SCHEMA, "lane": LANE, "identity": IDENTITY,
                  "evidence_class": continuity.EVIDENCE_CLASS,
                  "producer": {"path": str(producer), "sha256": sha(producer.read_bytes())},
                  "steps": steps, "checks": checks, "passed": True, "failures": [], "stable_stage_should_change": False}
        metadata = write(root / "candidate.json", json.dumps({"probe_contract": {"acceptance_marker": MARKER}}).encode())
        context = {"identity": IDENTITY, "artifact_refs": {"metadata": metadata}}
        refs, failures = [], []
        measured = release._hidden_lane(LANE, continuity, report, root / "lane.json", context, refs, failures)
        self.assertFalse(failures)
        self.assertTrue(all(value["passed"] for value in measured.values()))
        bounds = [4 * 1024 * 1024] + [continuity.STEP_BOUNDS[key] for key in ("session_report", "cdb_log", "save")] * 2
        self.assertEqual([entry[2] for entry in refs], bounds)
        for change, message in (({"evidence_class": "approved_hidden_cdb_host_soak"}, "approved_hidden_cdb_continuity"),
                                ({"passed": False}, "affirmative report")):
            with self.subTest(change=sorted(change)):
                failures = []
                release._hidden_lane(LANE, continuity, dict(report, **change), root / "lane.json", context, [], failures)
                self.assertTrue(any(message in item for item in failures), failures)


if __name__ == "__main__":
    unittest.main()

"""Synthetic source-artifact fixtures for the matrix-cell hidden soak lane replay.

Each fixture is a complete retained run directory: session report, CDB log,
frames and telemetry at a tiny canvas. No game, debugger or capture runs.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import hd_multires_route_extras as route_extras
import matrix_release_evidence as release
import matrix_soak_lanes as soak

WIDTH, HEIGHT = 16, 8
MARKER = "HDMULTI_LOADED_BYTES_OK profile=framed resolution=16x8 stage=synthetic"
IDENTITY = {"base_sha256": "1" * 64, "candidate_sha256": "2" * 64, "cell_id": "framed/16x8",
            "launcher_manifest_sha256": "3" * 64, "probe_sha256": "4" * 64, "profile": "framed",
            "recipe_revision": "hd_multires_v1", "resolution": "16x8", "source_closure_sha256": "5" * 64,
            "stage": "synthetic", "features": {"minimap_viewport": True}, "metadata_sha256": "6" * 64}
PRODUCER = b"synthetic producer source\n"
START = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": str(path), "sha256": sha(data)}


def map_log(route: str, seconds: int) -> list[str]:
    ticks, pan = seconds * 64, int(route == "map-pan")
    lines = [MARKER, "HDSESSION_TARGET pid=abc base=00400000",
             f"SOAK_ROUTE_START route_ticks={ticks} pan={pan} player=0 tick=100 gd=0a000000 scroll=(10,17)",
             f"SOAK_SURFDUMP_READY redraw_seq=0 surface=00520000 size=({WIDTH},{HEIGHT}) base=20000000 bytes={WIDTH * HEIGHT}"]
    x, y, hits = 10, 17, 0
    if pan:
        lines.append("SOAK_PAN_PLAN base=(10,17) delta=(1,1) max=(88,91) safe=1")
    lines.append(f"SOAK_HEARTBEAT hits=2048 tickdelta=60 player=0 scroll=({x},{y})")
    hits = 2048
    if pan:
        for index in range(seconds // 10 - 1):
            hits += 50
            x, y = ((10, 17), (11, 17), (11, 18), (10, 18))[index % 4]
            lines.append(f"SOAK_PAN_SET phase={index % 4} x={x} y={y} hits={hits} tickdelta={640 * (index + 1)} delta=(1,1)")
    lines.append(f"SOAK_ROUTE_END route_ticks={ticks} pan={pan} hits={hits + 10} tickdelta={ticks + 1} player=0 scroll=({x},{y})")
    return lines


class Run:
    """One retained hidden session run directory, editable before it is written."""

    def __init__(self, root: Path, tier: str, route: str, seconds: int, started: datetime,
                 extra: dict | None = None):
        self.root, self.tier, self.route, self.seconds = root, tier, route, seconds
        self.spec = None if extra is None else route_extras.prepare(extra, route=route, duration=seconds)
        self.directory = root / f"session-{tier}-{route}"
        self.log_lines = (map_log(route, seconds) if route != "menu-idle" else
                          [MARKER, "HDSESSION_TARGET pid=abc base=00400000",
                           f"HDSESSION_MENU_READY pid=abc surface=0051d4c0 width={WIDTH} height={HEIGHT} pixels=20000000"])
        if self.spec:
            # A neutralized failed mouse read, then one re-armed step printed on a fresh line.
            self.log_lines.insert(4, "HDNEUTRAL_MOUSE_READ hresult=8007000c")
            self.log_lines[-1:-1] = ["", "HDPAN_REARM reason=rate_limit step=3 count=1 total=1 value=2"]
        frames = [bytes((index + shift) % 251 for index in range(WIDTH * HEIGHT)) for shift in (0, 7)]
        prefix = "menu" if route == "menu-idle" else "map"
        self.frame_bytes = {f"{prefix}-frame-{index:04d}.indexed8": data for index, data in enumerate(frames)}
        mechanisms = (dict(soak.MENU_MECHANISMS[1]) if route == "menu-idle" else
                      dict(soak.MAP_MECHANISMS, **({"pan": "cdb_forced_native_arrow_key"} if route == "map-pan" else {}),
                           **(self.spec["mechanisms"] if self.spec else {})))
        self.session = {
            "schema": soak.SESSION_SCHEMA, "executed": True, "route": route, "duration_sec": seconds,
            "identity": {key: IDENTITY[key] for key in soak.SESSION_IDENTITY_KEYS},
            "environment": "hidden_cdb_host", "input_responsiveness": "not_applicable_hidden",
            "input_injected": False, "manual_input_proof": False, "initial_image_bytes_verified": True,
            "diagnostic_passed": True, "failures": [], "smoke_only": False, "acquire_only": False,
            "forced_mechanisms": mechanisms, "input_or_callback_forced": route != "menu-idle",
            "producer_source_hashes": {soak.PRODUCER: sha(PRODUCER)},
            "run_directory": str(self.directory),
            "samples": [{"elapsed_sec": float(second), "working_set": 40_000_000 + second,
                         "private_bytes": 20_000_000, "handles": 592} for second in range(seconds + 1)],
            "frames": [{"path": name, "sha256": sha(data), "bytes": len(data), "elapsed_sec": 0.0,
                        "width": WIDTH, "height": HEIGHT, "coherent_snapshot_verified": False}
                       for name, data in self.frame_bytes.items()],
            "cleanup": {"cleanup_verified": True}, "live_saves_unchanged": True, "launch_artifacts_unchanged": True,
            "started_at": started.isoformat(), "finished_at": (started + timedelta(seconds=seconds + 30)).isoformat(),
        }
        if route == "menu-idle":
            self.session.update(natural_menu_idle_verified=True, measured_menu_host_seconds=float(seconds))
        else:
            self.session.update(map_route_completed=True, load_slot=0, measured_map_host_seconds=float(seconds),
                                map_surface={"width": WIDTH, "height": HEIGHT})
        if self.spec:
            slot = {"sha256": "7" * 64, "bytes": 586414, "mtime_ns": 1}
            self.session.update(route_extra=self.spec, route_extra_files={
                "before": {"save/0.dat": dict(slot)}, "after": {"save/0.dat": dict(slot)}, "retained": {}})

    def save(self) -> dict:
        log = ("\r\n".join(self.log_lines) + "\r\n").encode("ascii")
        session = copy.deepcopy(self.session)
        session.setdefault("retained_log", {"path": "cdb.log", "sha256": sha(log), "bytes": len(log)})
        if self.spec:
            # The session records the extra's replay of its own final log.
            session.setdefault("route_extra_observations", route_extras.observe(self.spec, log.decode("latin-1"))[0])
        for name, data in self.frame_bytes.items():
            write(self.directory / name, data)
        return {"tier": self.tier, "route": self.route, "duration_sec": self.seconds,
                "session_report": write(self.directory / "session-report.json", json.dumps(session).encode()),
                "cdb_log": write(self.directory / "cdb.log", log)}


class SoakReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clash-soak-lanes-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cases = 0

    def lane(self, name, pan_extra="default"):
        """Map-pan rows carry pan_extra; by default the two-hour pan lane's carry the disclosed one."""
        if pan_extra == "default":
            pan_extra = soak.PAN_EXTRA if name == "long_map_pan" else None
        self.cases += 1
        root, started, runs = self.root / f"case-{self.cases}", START, []
        for tier, route, seconds in soak.SCHEDULE[name]:
            runs.append(Run(root, tier, route, seconds, started, pan_extra if route == "map-pan" else None))
            started += timedelta(seconds=seconds + 60)
        return root, runs

    def replay(self, name, root, runs, *, producer=PRODUCER, mutate=None):
        steps = [run.save() for run in runs]
        report = {"steps": steps}
        if mutate:
            mutate(report)
        return soak.replay(name, report, root / "lane.json", IDENTITY, release._reference_bytes, producer, MARKER,
                           Path(__file__).resolve().parents[1])

    def assert_passes(self, name, root, runs, **kwargs):
        checks, failures = self.replay(name, root, runs, **kwargs)
        self.assertEqual(list(checks), list(soak.evidence.LANES[name][1]))
        self.assertFalse(failures)
        self.assertTrue(all(value == {"passed": True, "failures": []} for value in checks.values()), checks)
        return checks

    def failed(self, name, root, runs, **kwargs):
        checks, failures = self.replay(name, root, runs, **kwargs)
        return {key for key, value in checks.items() if not value["passed"]}, failures

    def test_complete_ladder_and_long_routes_replay_from_retained_artifacts(self):
        for name in soak.LANES:
            with self.subTest(lane=name):
                self.assert_passes(name, *self.lane(name))

    def test_each_gate_fails_closed_on_its_own_artifact(self):
        cases = {
            # A session of another candidate counts for nothing in this cell.
            "identity": (lambda runs: runs[1].session["identity"].__setitem__("candidate_sha256", "9" * 64),
                         set(soak.evidence.LANES["short_soak_ladder"][1]), "another candidate"),
            "producer": (lambda runs: runs[1].session["producer_source_hashes"].__setitem__(soak.PRODUCER, "8" * 64),
                         {"ordered_ladder_completed"}, "pinned producer"),
            "retained log": (lambda runs: runs[1].session.__setitem__("retained_log", {"path": "cdb.log", "sha256": "7" * 64, "bytes": 1}),
                             {"ordered_ladder_completed"}, "retained log"),
            "tick shortfall": (lambda runs: runs[1].log_lines.__setitem__(-1, runs[1].log_lines[-1].replace("tickdelta=7681", "tickdelta=7000")),
                               {"ordered_ladder_completed"}, None),
            "failure token": (lambda runs: runs[2].log_lines.append("HDSESSION_AV"), {"ordered_ladder_completed"}, "runtime failure"),
            "two markers": (lambda runs: runs[0].log_lines.append(MARKER), {"ordered_ladder_completed"}, "canonical image marker"),
            "forced menu input": (lambda runs: runs[0].session.__setitem__("input_or_callback_forced", True),
                                  {"ordered_ladder_completed"}, None),
            "telemetry gap": (lambda runs: runs[2].session["samples"].__delitem__(slice(100, 106)), {"process_liveness"}, "gap"),
            "sparse telemetry": (lambda runs: runs[2].session["samples"].__delitem__(slice(100, None)),
                                 {"process_liveness", "process_growth"}, "too sparse"),
            "memory growth": (lambda runs: runs[2].session["samples"][-1].__setitem__("private_bytes", 200_000_000),
                              {"process_growth"}, "legacy soak limits"),
            "flat frame": (lambda runs: runs[3].frame_bytes.__setitem__("map-frame-0001.indexed8", bytes(WIDTH * HEIGHT)),
                           {"render_integrity"}, None),
            "cleanup": (lambda runs: runs[4].session["cleanup"].__setitem__("cleanup_verified", False), {"clean_stop"}, None),
            "overlap": (lambda runs: runs[2].session.__setitem__("started_at", runs[0].session["started_at"]),
                        {"ordered_ladder_completed"}, None),
            "few pans": (lambda runs: runs[3].log_lines.__delitem__(slice(6, 40)), {"ordered_ladder_completed"}, "pan schedule"),
        }
        for label, (mutate, expected, note) in cases.items():
            with self.subTest(case=label):
                root, runs = self.lane("short_soak_ladder")
                mutate(runs)
                if label == "flat frame":
                    flat = runs[3].frame_bytes["map-frame-0001.indexed8"]
                    runs[3].session["frames"][1]["sha256"] = sha(flat)
                failed, failures = self.failed("short_soak_ladder", root, runs)
                self.assertEqual(failed, expected, failures)
                if note:
                    self.assertTrue(any(note in item for item in failures), failures)

    def test_blank_frames_stationary_pans_and_failure_flags_fail_closed(self):
        # One lit pixel on a black surface is not a rendered screen.
        root, runs = self.lane("long_map_idle")
        blank = bytes(WIDTH * HEIGHT - 1) + b"\x01"
        for run in runs:
            run.frame_bytes = {name: blank for name in run.frame_bytes}
            for frame in run.session["frames"]:
                frame["sha256"] = sha(blank)
        failed, failures = self.failed("long_map_idle", root, runs)
        self.assertEqual(failed, {"render_integrity"})
        self.assertTrue(any("palette variety" in item for item in failures), failures)
        # A map that stopped moving fails, however its frames change.
        root, runs = self.lane("long_map_pan")
        lines = runs[0].log_lines
        for index, line in enumerate(lines):
            if line.startswith(("SOAK_PAN_SET ", "SOAK_ROUTE_END ")):
                lines[index] = re.sub(r"x=\d+ y=\d+", "x=10 y=17", re.sub(r"scroll=\(\d+,\d+\)", "scroll=(10,17)", line))
        failed, failures = self.failed("long_map_pan", root, runs)
        self.assertEqual(failed, {"route_completed", "frame_progression"})
        self.assertTrue(any("pan schedule" in item for item in failures), failures)
        # Explicit runtime failure rows fail beside an otherwise positive session summary.
        for row in ("SURFDUMP_INVALID", "AV_SURFDUMP",
                    "SURFDUMP_APP_REQUEST_QUIT text_ptr=00401000 caption_ptr=00402000",
                    "SOAK_PAN_UNSAFE base=(10,17) max=(0,0) reason=no_inward_axis"):
            with self.subTest(row=row):
                root, runs = self.lane("long_map_idle")
                runs[0].log_lines.insert(-1, row)
                failed, failures = self.failed("long_map_idle", root, runs)
                self.assertEqual(failed, {"route_completed"})
                self.assertTrue(any("runtime failure" in item for item in failures), failures)

    def test_schedule_shape_and_external_location_are_fixed(self):
        root, runs = self.lane("long_map_idle")
        for mutate in (lambda report: report["steps"].append(dict(report["steps"][0])),
                       lambda report: report["steps"][0].__setitem__("duration_sec", 600),
                       lambda report: report["steps"][0].__setitem__("route", "map-pan"),
                       lambda report: report["steps"][0].__setitem__("extra", True)):
            with self.subTest(mutate=mutate):
                failed, failures = self.failed("long_map_idle", root, runs, mutate=mutate)
                self.assertIn("route_completed", failed)
                self.assertTrue(failures)
        repo_root, repo_runs = self.lane("long_map_idle")
        checks, failures = soak.replay("long_map_idle", {"steps": [run.save() for run in repo_runs]},
                                       repo_root / "lane.json", IDENTITY, release._reference_bytes, PRODUCER, MARKER,
                                       repo_root)
        self.assertTrue(any("external run directory" in item for item in failures), failures)
        self.assertFalse(checks["route_completed"]["passed"])

    def test_pan_lane_needs_progressing_frames_and_another_producer_fails(self):
        root, runs = self.lane("long_map_pan")
        runs[0].frame_bytes["map-frame-0001.indexed8"] = runs[0].frame_bytes["map-frame-0000.indexed8"]
        runs[0].session["frames"][1]["sha256"] = runs[0].session["frames"][0]["sha256"]
        failed, _ = self.failed("long_map_pan", root, runs)
        self.assertEqual(failed, {"frame_progression"})
        root, runs = self.lane("long_map_pan")
        failed, failures = self.failed("long_map_pan", root, runs, producer=b"another producer\n")
        self.assertIn("route_completed", failed)

    def test_pan_rows_carry_exactly_the_disclosed_retry_extra_or_none(self):
        self.assertEqual(soak.PAN_EXTRAS, ({"name": "pan-retry", "neutral_mouse": True},
                                           {"name": "pan-press", "neutral_mouse": True},
                                           {"name": "pan-steady", "neutral_mouse": True}))
        self.assertEqual(soak.PAN_EXTRA, soak.PAN_EXTRAS[2])
        # The one-call press alone, the earlier pan-retry and pan-press remain valid pan rows,
        # and so is a ladder rung with the extra.
        self.assert_passes("long_map_pan", *self.lane("long_map_pan", pan_extra=None))
        self.assert_passes("long_map_pan", *self.lane("long_map_pan", pan_extra=soak.PAN_EXTRAS[0]))
        self.assert_passes("long_map_pan", *self.lane("long_map_pan", pan_extra=soak.PAN_EXTRAS[1]))
        self.assert_passes("short_soak_ladder", *self.lane("short_soak_ladder", pan_extra=soak.PAN_EXTRA))
        turn = {"name": "forced-turn", "load_slot": 0, "before_slot": 5, "after_slot": 6}
        cases = {
            "undisclosed press": lambda run: run.session["forced_mechanisms"].pop("pan_press"),
            "request without neutral mouse": lambda run: run.session["route_extra"].__setitem__(
                "request", {"name": "pan-press"}),
            "unknown pan extra": lambda run: run.session["route_extra"].__setitem__("name", "pan-hold"),
            "other extra's mechanisms": lambda run: run.session["forced_mechanisms"].update(
                pan_retry="cdb_soak_pan_step_rearmed_when_handler_declines"),
            "continuity extra": lambda run: run.session.__setitem__("route_extra", turn),
            "observations differ": lambda run: run.session.__setitem__(
                "route_extra_observations", {"rearms": [], "limits": [], "neutral_mouse_reads": 1}),
            "exhausted step": lambda run: run.log_lines.insert(-1, "HDPAN_REARM_LIMIT step=7"),
            "no neutral read": lambda run: run.log_lines.remove("HDNEUTRAL_MOUSE_READ hresult=8007000c"),
            "slot changed": lambda run: run.session["route_extra_files"]["after"]["save/0.dat"].__setitem__(
                "sha256", "9" * 64),
            "save retained": lambda run: run.session["route_extra_files"].__setitem__("retained", {"save/1.dat": {}}),
        }
        for label, mutate in cases.items():
            with self.subTest(case=label):
                root, runs = self.lane("long_map_pan")
                mutate(runs[0])
                failed, failures = self.failed("long_map_pan", root, runs)
                self.assertIn("route_completed", failed, failures)
        # Idle and menu rows carry no extra at all.
        root, runs = self.lane("long_map_idle")
        runs[0].session["route_extra"] = route_extras.prepare(soak.PAN_EXTRA, route="map-pan", duration=7200)
        failed, failures = self.failed("long_map_idle", root, runs)
        self.assertIn("route_completed", failed, failures)

    def test_a_slot_anchored_pan_row_keeps_every_logged_interval_periodic(self):
        press, steady = soak.PAN_EXTRAS[1], soak.PAN_EXTRAS[2]
        row = re.compile(r"(SOAK_PAN_SET phase=\d x=\d+ y=\d+ hits=\d+ tickdelta=)(\d+)( delta=\(1,1\))")

        def shifted(extra, ticks):
            """A two-hour pan lane whose hundredth and later steps are logged ``ticks`` later."""
            root, runs = self.lane("long_map_pan", pan_extra=extra)
            lines = runs[0].log_lines
            for index, line in enumerate(lines):
                match = row.fullmatch(line)
                if match and int(match[2]) >= 640 * 100:
                    lines[index] = f"{match[1]}{int(match[2]) + ticks}{match[3]}"
            return root, runs

        # A slot logs exactly its interval; a kept tick may widen one by the two-second allowance.
        self.assert_passes("long_map_pan", *shifted(steady, 0))
        self.assert_passes("long_map_pan", *shifted(steady, 128))
        for ticks in (129, 640, -1):
            with self.subTest(ticks=ticks):
                failed, failures = self.failed("long_map_pan", *shifted(steady, ticks))
                self.assertEqual(failed, {"route_completed", "frame_progression"}, failures)
                self.assertTrue(any("pan schedule" in item for item in failures), failures)
        # Rows of the earlier extras keep their earlier grading.
        self.assert_passes("long_map_pan", *shifted(press, 129))
        self.assert_passes("long_map_pan", *shifted(None, 129))
        # The coverage is the legacy grader's own, over the same parsed rows.
        rows = soak.soak_log.parse_soak_log(("\r\n".join(shifted(steady, 129)[1][0].log_lines) + "\r\n").encode("ascii"))
        self.assertTrue(any("periodic interval" in item for item in soak.pan_coverage_failures(rows, 7200)))
        rows["RouteEnds"] = []
        self.assertEqual(soak.pan_coverage_failures(rows, 7200), ["pan coverage requires one route end"])

    def release_lane(self, name, **changes):
        """A complete lane report pinned to the repository's actual hidden session producer."""
        root, runs = self.lane(name)
        producer = (release.matrix.ROOT / soak.PRODUCER).resolve()
        for run in runs:
            run.session["producer_source_hashes"] = {soak.PRODUCER: sha(producer.read_bytes())}
        steps = [run.save() for run in runs]
        checks, _ = soak.replay(name, {"steps": steps}, root / "lane.json", IDENTITY, release._reference_bytes,
                                producer.read_bytes(), MARKER, release.matrix.ROOT)
        report = {"schema": release.LANE_SCHEMA, "lane": name, "identity": IDENTITY,
                  "evidence_class": soak.EVIDENCE_CLASS, "producer": {"path": str(producer), "sha256": sha(producer.read_bytes())},
                  "steps": steps, "checks": checks, "passed": True, "failures": [], "stable_stage_should_change": False}
        report.update(changes)
        metadata = write(root / "candidate.json", json.dumps({"probe_contract": {"acceptance_marker": MARKER}}).encode())
        return report, root / "lane.json", {"identity": IDENTITY, "artifact_refs": {"metadata": metadata}}

    def test_release_dispatch_replays_only_the_fixed_hidden_soak_envelope(self):
        report, path, context = self.release_lane("long_map_idle")
        refs, failures = [], []
        measured = release._hidden_lane("long_map_idle", release.soak_lanes, report, path, context, refs, failures)
        self.assertFalse(failures)
        self.assertTrue(all(value["passed"] for value in measured.values()))
        # The producer and both pinned step files are rechecked at the end, each with its own bound.
        self.assertEqual([entry[2] for entry in refs], [4 * 1024 * 1024, soak.MAX_SESSION_BYTES, soak.MAX_LOG_BYTES])
        flipped = copy.deepcopy(report["checks"])
        flipped["clean_stop"] = {"passed": False, "failures": ["clean_stop"]}
        other = {"path": str((release.matrix.ROOT / "tools/matrix_soak_lanes.py").resolve()),
                 "sha256": sha((release.matrix.ROOT / "tools/matrix_soak_lanes.py").read_bytes())}
        for change, message in (({"evidence_class": "invented_green_runtime"}, "approved_hidden_cdb_host_soak"),
                                ({"passed": False}, "affirmative report"),
                                ({"stable_stage_should_change": True}, "protected stable stage"),
                                ({"checks": flipped}, "differ from source-artifact replay"),
                                ({"release_resolutions": ["1920x1080"]}, "fixed hidden-soak envelope"),
                                ({"producer": other}, "fixed hidden session producer")):
            with self.subTest(change=sorted(change)):
                report, path, context = self.release_lane("long_map_idle", **change)
                failures = []
                release._hidden_lane("long_map_idle", release.soak_lanes, report, path, context, [], failures)
                self.assertTrue(any(message in item for item in failures), failures)
        report, path, context = self.release_lane("long_map_idle")
        context["identity"] = dict(IDENTITY, recipe_revision="complete_hd_v1")
        with self.assertRaisesRegex(ValueError, "only hd_multires_v1"):
            release._hidden_lane("long_map_idle", release.soak_lanes, report, path, context, [], [])
        report, path, context = self.release_lane("long_map_idle")
        context["artifact_refs"]["metadata"] = write(path.parent / "other.json", b'{"probe_contract": {}}')
        with self.assertRaises(KeyError):
            release._hidden_lane("long_map_idle", release.soak_lanes, report, path, context, [], [])

    def test_tampered_frame_or_report_bytes_raise_before_any_check(self):
        root, runs = self.lane("long_map_idle")
        steps = [run.save() for run in runs]
        (runs[0].directory / "map-frame-0000.indexed8").write_bytes(bytes(WIDTH * HEIGHT))
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            soak.replay("long_map_idle", {"steps": steps}, root / "lane.json", IDENTITY, release._reference_bytes,
                        PRODUCER, MARKER, Path(__file__).resolve().parents[1])
        steps[0]["session_report"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            soak.replay("long_map_idle", {"steps": steps}, root / "lane.json", IDENTITY, release._reference_bytes,
                        PRODUCER, MARKER, Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)

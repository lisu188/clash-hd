"""Tiny synthetic retained-log fixtures; never run the harness or game."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import hidden_soak_log_observations as observations
from hidden_soak_retained_files import RetainedFileError, read_retained_file


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/cdb/run_hidden_soak.ps1"
PROBE = ROOT / "probes/cdb/soak/clash95_hidden_soak_route_extra.cdb"
POWERSHELL = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")


def canonical_log_inventory(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Construct and freeze a *pre-mutation synthetic fixture* log inventory.

    Caller must retain these bytes before testing mutations. This is never a
    production reader or grade-time repair. Existing coordinates/plans are
    required, not inferred to replace missing proof. Only fixture line numbers
    and log pins are assigned here; original counters and coordinates remain
    unchanged. Heartbeats interpolate between the existing redraw anchors.
    """
    result = copy.deepcopy(payload)
    start, ready, end = (result[name] for name in ("route_start_marker", "ready_marker", "route_end_marker"))
    plans, events = result.get("pan_plans", []), result["pan_events"]
    if result["route"] not in ("map-idle", "map-pan") or ready["source"] != "SOAK_SURFDUMP_READY":
        raise ValueError("canonical synthetic hidden route/readiness required")
    if result["route"] == "map-pan" and (len(plans) != 1 or not events):
        raise ValueError("preexisting synthetic plan/events are required")
    if result["route"] == "map-idle" and (plans or events):
        raise ValueError("idle fixture cannot contain pan receipts")
    lines = ["SOAK_PAN_PLAN and a SOAK_PAN_SET row for every write."]

    def append(line: str) -> int:
        lines.append(line)
        return len(lines)

    start["line_number"] = append(
        f"SOAK_ROUTE_START route_ticks={start['route_ticks']} pan={start['pan']} player={start['player']} "
        f"tick={start['tick']} gd={start['game_data']} scroll=({start['scroll_x']},{start['scroll_y']})")
    ready["line_number"] = append(
        f"SOAK_SURFDUMP_READY redraw_seq={ready['redraw_seq']} surface={ready['surface']} "
        f"size=({ready['width']},{ready['height']}) base={ready['base']} bytes={ready['bytes']}")
    if plans:
        plan = plans[0]
        plan["line_number"] = append(
            f"SOAK_PAN_PLAN base=({plan['base_x']},{plan['base_y']}) delta=({plan['delta_x']},{plan['delta_y']}) "
            f"max=({plan['max_x']},{plan['max_y']}) safe={plan['safe']}")
    count = result["heartbeat_count"]
    if type(count) is not int or not 0 < count <= min(end["hits"], end["tick_delta"] + 1):
        raise ValueError("fixture heartbeat count needs enough genuine redraw anchors")
    anchors = [(0, 0)] + [(event["hits"], event["tick_delta"]) for event in events] + [(end["hits"], end["tick_delta"])]
    for (old_hits, old_tick), (hits, tick) in zip(anchors, anchors[1:]):
        if min(hits, tick) < 0 or hits <= 0 or hits < old_hits or tick < old_tick or (hits == old_hits and tick != old_tick):
            raise ValueError("fixture redraw anchors must already be globally ordered")
    heartbeats = []
    anchor_index, last_tick = 1, -1
    for index in range(1, count + 1):
        hits = index * end["hits"] // count
        while anchors[anchor_index][0] < hits:
            anchor_index += 1
        old_hits, old_tick = anchors[anchor_index - 1]
        next_hits, next_tick = anchors[anchor_index]
        tick = next_tick if hits == next_hits else old_tick + (hits - old_hits) * (next_tick - old_tick) // (next_hits - old_hits)
        if tick <= last_tick:
            raise ValueError("fixture anchors cannot retain the requested strictly ordered heartbeat count")
        heartbeats.append({"hits": hits, "tick_delta": tick})
        last_tick = tick
    ordered = [(row["tick_delta"], row["hits"], 0, row) for row in heartbeats]
    ordered += [(row["tick_delta"], row["hits"], 1, row) for row in events]
    x, y = start["scroll_x"], start["scroll_y"]
    for _, _, kind, row in sorted(ordered, key=lambda item: item[:3]):
        if kind == 0:
            append(f"SOAK_HEARTBEAT hits={row['hits']} tickdelta={row['tick_delta']} player={start['player']} scroll=({x},{y})")
        else:
            row["line_number"] = append(
                f"SOAK_PAN_SET phase={row['phase']} x={row['x']} y={row['y']} hits={row['hits']} "
                f"tickdelta={row['tick_delta']} delta=({row['delta_x']},{row['delta_y']})")
            x, y = row["x"], row["y"]
    if (end["scroll_x"], end["scroll_y"]) != (x, y):
        raise ValueError("fixture terminal coordinates must already match its events")
    end["line_number"] = append(
        f"SOAK_ROUTE_END route_ticks={end['route_ticks']} pan={end['pan']} hits={end['hits']} "
        f"tickdelta={end['tick_delta']} player={end['player']} scroll=({x},{y})")
    raw = ("\n".join(lines) + "\n").encode("ascii")
    result.update(cdb_log_sha256=hashlib.sha256(raw).hexdigest(), cdb_log_size=len(raw))
    for field, value in (("pan_plans", plans), ("pan_event_count", len(events)), ("ready_observed", True),
                         ("soak_route_start_observed", True), ("soak_route_end_observed", True), ("av_observed", False),
                         ("surface_invalid_observed", False), ("app_request_quit_observed", False)):
        result.setdefault(field, value)
    return result, {result["cdb_log"]: raw}


def _baseline(route: str = "map-pan") -> tuple[dict[str, Any], bytes]:
    payload = {
        "route": route, "output_directory": r"C:\ClashCaptures\hd-soak\hidden\fixture",
        "cdb_log": r"C:\ClashCaptures\hd-soak\hidden\fixture\hidden-soak-cdb.log",
        "ready_marker": {"source": "SOAK_SURFDUMP_READY", "redraw_seq": 4, "surface": "00a00000",
                         "base": "00b40000", "width": 800, "height": 600, "bytes": 480000},
        "route_start_marker": {"route_ticks": 1920, "pan": int(route == "map-pan"), "player": 0,
                               "tick": 1000, "game_data": "00c00000", "scroll_x": 4, "scroll_y": 6},
        "route_end_marker": {"route_ticks": 1920, "pan": int(route == "map-pan"), "tick_delta": 1920, "hits": 8192,
                             "player": 0, "scroll_x": 5 if route == "map-pan" else 4, "scroll_y": 6},
        "pan_plans": [{"source": "SOAK_PAN_PLAN", "safe": 1, "base_x": 4, "base_y": 6,
                       "delta_x": 1, "delta_y": 1, "max_x": 20, "max_y": 20}] if route == "map-pan" else [],
        "pan_events": [{"phase": index, "x": 4 + index, "y": 6, "tick_delta": (index + 1) * 640, "hits": (index + 1) * 2048,
                        "delta_x": 1, "delta_y": 1} for index in range(2)] if route == "map-pan" else [],
        "heartbeat_count": 4 if route == "map-pan" else 1,
    }
    result, inventory = canonical_log_inventory(payload)
    return result, inventory[result["cdb_log"]]


class LogObservationTests(unittest.TestCase):
    def check(self, payload: dict[str, Any], raw: bytes):
        fixed = {payload["cdb_log"]: raw}
        with mock.patch.object(observations, "_reader", side_effect=lambda path, maximum: fixed[path]) as reader:
            result = observations.validate_retained_log(payload)
        reader.assert_called_once_with(payload["cdb_log"], observations.MAX_LOG_BYTES)
        return result

    def test_passing_idle_and_pan_and_unchanged_inputs(self):
        for route in ("map-idle", "map-pan"):
            payload, raw = _baseline(route)
            before = copy.deepcopy(payload)
            summary, failures = self.check(payload, raw)
            self.assertEqual(failures, [])
            self.assertEqual(payload, before)
            self.assertEqual(summary["sha256"], payload["cdb_log_sha256"])
            self.assertFalse(summary["native_producer_verified"])
            self.assertFalse(summary["running_time_verified"])
            self.assertLess(len(raw), 1024)

    def test_fixture_sealing_preserves_existing_values_and_counts(self):
        payload, _ = _baseline()
        payload["pan_events"][0]["hits"] = 500
        payload["pan_events"][1]["hits"] = 1000
        original = copy.deepcopy(payload)
        sealed, inventory = canonical_log_inventory(payload)
        for field in ("ready_marker", "route_start_marker", "route_end_marker", "pan_plans", "pan_events"):
            before = original[field] if type(original[field]) is list else [original[field]]
            after = sealed[field] if type(sealed[field]) is list else [sealed[field]]
            for old, new in zip(before, after):
                self.assertEqual({key: value for key, value in old.items() if key != "line_number"},
                                 {key: value for key, value in new.items() if key != "line_number"})
        self.assertEqual(sealed["heartbeat_count"], original["heartbeat_count"])
        self.assertEqual(payload, original)
        self.assertEqual(self.check(sealed, inventory[sealed["cdb_log"]])[1], [])
        invalid = dict(payload, heartbeat_count=8193)
        with self.assertRaises(ValueError):
            canonical_log_inventory(invalid)

    def test_actual_echo_prose_never_observations(self):
        prose = "\n".join(line[6:] for line in PROBE.read_text(encoding="ascii").splitlines() if line.startswith(".echo "))
        parsed = observations.parse_soak_log(prose.encode("ascii"))
        self.assertEqual(parsed["failures"], [])
        self.assertTrue(all(not value for key, value in parsed.items() if key != "failures"))
        self.assertFalse(observations.parse_soak_log(b".echo SOAK_ROUTE_END route_ticks=10\n")["RouteEnds"])

    def test_malformed_structured_rows_and_ranges_fail_without_observation(self):
        _, raw = _baseline()
        good = raw.decode("ascii").splitlines()
        rows = [line for line in good if "=" in line]
        rows.extend(("SOAK_ROUTE_END", "SOAK_PAN_PLAN base=(4,6) delta=(1,1) max=(20,20) safe=0",
                     "SOAK_ROUTE_START route_ticks=1 pan=2 player=0 tick=0 gd=0 scroll=(0,0)",
                     "SURFDUMP_APP_REQUEST_QUIT text_ptr=xyz caption_ptr=0"))
        for row in rows:
            invalid = row + " malformed" if row in good else row
            parsed = observations.parse_soak_log((invalid + "\n").encode("ascii"))
            self.assertTrue(parsed["failures"], invalid)
            self.assertTrue(all(not value for key, value in parsed.items() if key != "failures"), invalid)
        self.assertTrue(observations.parse_soak_log(raw.replace(b"route_ticks=1920", f"route_ticks={1 << 63}".encode()))["failures"])
        self.assertTrue(observations.parse_soak_log(raw.replace(b"player=0", b"player=2147483648"))["failures"])
        self.assertTrue(observations.parse_soak_log(b"SOAK_ROUTE_END route_ticks=" + b"9" * 5000)["failures"])
        padded = observations.parse_soak_log(raw.replace(b"route_ticks=1920", b"route_ticks=" + b"0" * 5000 + b"1920"))
        self.assertFalse(padded["failures"])
        self.assertEqual(padded["RouteStarts"][0]["RouteTicks"], 1920)

    def test_failure_rows_and_startup_mentions_are_distinct(self):
        raw = (b"prose AV_SURFDUMP SURFDUMP_INVALID SURFDUMP_APP_REQUEST_QUIT\n"
               b"AV_SURFDUMP\nSURFDUMP_INVALID\nSURFDUMP_APP_REQUEST_QUIT text_ptr=00ab`0010 caption_ptr=00000000\n"
               b"SOAK_PAN_UNSAFE base=(0,0) max=(0,0) reason=no_inward_direction\n")
        parsed = observations.parse_soak_log(raw)
        self.assertTrue(all(parsed[key] for key in ("AvObserved", "SurfaceInvalidObserved", "AppRequestQuitObserved")))
        self.assertEqual(parsed["PanUnsafeRows"][0]["LineNumber"], 5)
        self.assertFalse(parsed["failures"])

    def test_crlf_bom_backtick_and_negative_fields_preserve_positions(self):
        row = b"\n  SOAK_ROUTE_START route_ticks=1 pan=0 player=-1 tick=-2 gd=00000000`00c00000 scroll=(-3,-4)  \n"
        expected = observations.parse_soak_log(row)
        for raw in (row.replace(b"\n", b"\r\n"), b"\xef\xbb\xbf" + row, row.decode().encode("utf-16")):
            self.assertEqual(observations.parse_soak_log(raw), expected)
        self.assertEqual(expected["RouteStarts"][0]["LineNumber"], 2)
        self.assertEqual(expected["RouteStarts"][0]["Tick"], -2)
        self.assertTrue(observations.parse_soak_log(b"\xff\xfe\x00")["failures"])
        self.assertTrue(observations.parse_soak_log(b"bad\0log")["failures"])

    def test_all_report_observations_counts_and_flags_bind_original_bytes(self):
        payload, raw = _baseline()
        mutations = [
            ("ready_marker", "base", "00b50000"), ("route_start_marker", "tick", 1001),
            ("route_end_marker", "hits", 9999), ("pan_plans", "max_x", 21),
            ("pan_events", "x", 9), ("ready_marker", "redraw_seq", True),
        ]
        for top, field, value in mutations:
            invalid = copy.deepcopy(payload)
            target = invalid[top][0] if isinstance(invalid[top], list) else invalid[top]
            target[field] = value
            self.assertTrue(self.check(invalid, raw)[1], (top, field))
        for field in ("heartbeat_count", "pan_event_count", "cdb_log_size", "cdb_log_sha256", "pan_plans", "pan_events",
                      "av_observed", "surface_invalid_observed", "app_request_quit_observed", "ready_observed",
                      "soak_route_start_observed", "soak_route_end_observed"):
            invalid = copy.deepcopy(payload)
            invalid.pop(field)
            self.assertTrue(self.check(invalid, raw)[1], field)
        for value in (True, "2", 3):
            invalid = dict(payload, heartbeat_count=value)
            self.assertTrue(self.check(invalid, raw)[1], value)
        invalid = dict(payload, cdb_log_sha256="0" * 64)
        self.assertTrue(self.check(invalid, raw)[1])
        self.assertTrue(self.check(payload, raw + b"unrelated append\n")[1])

    def test_missing_default_file_and_unsafe_paths_fail_closed(self):
        payload, _ = _baseline()
        payload["cdb_log"] = r"C:\ClashCaptures\hd-soak\hidden\does-not-exist-fixture-9c04\hidden-soak-cdb.log"
        payload["output_directory"] = r"C:\ClashCaptures\hd-soak\hidden\does-not-exist-fixture-9c04"
        summary, failures = observations.validate_retained_log(payload)
        self.assertTrue(failures)
        self.assertIsNone(summary["sha256"])
        for path in ("relative.log", r"C:\ClashCaptures\hd-soak\hidden\other\log", r"C:\ClashCaptures\hd-soak\hidden\fixture\..\log"):
            invalid = dict(payload, cdb_log=path)
            with mock.patch.object(observations, "_reader") as reader:
                self.assertTrue(observations.validate_retained_log(invalid)[1])
                reader.assert_not_called()

    def test_original_read_and_close_errors_remain_diagnostic(self):
        payload, _ = _baseline()
        errors = (OSError("read-original"), OSError("close-original"))
        with mock.patch.object(observations, "_reader", side_effect=RetainedFileError("read failed", errors)):
            _, failures = observations.validate_retained_log(payload)
        self.assertTrue(any("read-original" in failure and "close-original" in failure for failure in failures))

    def test_original_log_global_order_and_failure_evidence_are_regraded(self):
        payload, raw = _baseline()
        variants = [
            raw.replace(b"SOAK_HEARTBEAT hits=4096", b"SOAK_HEARTBEAT hits=1"),
            raw.replace(b"tickdelta=1280 player=0", b"tickdelta=1 player=0"),
            raw.replace(b"player=0 scroll=(4,6)", b"player=1 scroll=(4,6)", 1),
            raw.replace(b"SOAK_HEARTBEAT hits=4096 tickdelta=1280 player=0 scroll=(4,6)",
                        b"SOAK_HEARTBEAT hits=4096 tickdelta=1280 player=0 scroll=(5,6)"),
            raw + b"SOAK_HEARTBEAT hits=8192 tickdelta=3000 player=0 scroll=(5,6)\n",
            raw + b"AV_SURFDUMP\n", raw + b"SURFDUMP_INVALID\n",
            raw + b"SURFDUMP_APP_REQUEST_QUIT text_ptr=00a00000 caption_ptr=00a00010\n",
            raw + b"SOAK_PAN_UNSAFE base=(0,0) max=(0,0) reason=no_inward_direction\n",
            raw + raw.splitlines()[1] + b"\n",  # A second genuine start row.
        ]
        for variant in variants:
            supplied = dict(payload, cdb_log_sha256=hashlib.sha256(variant).hexdigest(), cdb_log_size=len(variant))
            _, failures = self.check(supplied, variant)
            self.assertTrue(failures, variant)
            self.assertTrue(any("retained" in failure for failure in failures), failures)
        # Identical heartbeat/pan redraw pairs in the original fixture pass.
        self.assertFalse(self.check(payload, raw)[1])

    def test_tiny_actual_file_reader_with_fixed_fixture_mapping(self):
        payload, raw = _baseline("map-idle")
        with tempfile.TemporaryDirectory(prefix="clash-log-fixture-") as directory:
            path = Path(directory) / "original.log"
            path.write_bytes(raw)
            def read_fixture(requested, maximum):
                self.assertEqual(requested, payload["cdb_log"])
                return read_retained_file(str(path), maximum)
            with mock.patch.object(observations, "_reader", side_effect=read_fixture):
                self.assertFalse(observations.validate_retained_log(payload)[1])
        self.assertLess(len(raw), 1024)

    @unittest.skipUnless(sys.platform == "win32" and POWERSHELL.exists(), "source-extracted PowerShell parity needs Windows")
    def test_actual_powershell_source_parser_parity_all_valid_rows(self):
        helper = r'''param([string]$Runner,[string]$Log)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Runner,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'AST parse failure'}
$f=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Parse-SoakLog'},$true)
Invoke-Expression $f.Extent.Text
Parse-SoakLog -LogText ([IO.File]::ReadAllText($Log)) | ConvertTo-Json -Depth 8
'''
        _, raw = _baseline()
        extra = (b"SURFDUMP_READY redraw_seq=5 surface=00a00000 size=(800,600) base=00b40000 bytes=480000\n"
                 b"SOAK_PAN_UNSAFE base=(-1,0) max=(0,0) reason=base_out_of_bounds\n"
                 b"av_surfdump\nsurfdump_invalid\nsurfdump_app_request_quit text_ptr=00a0`0000 caption_ptr=00a00010\n")
        # Each retained fixture file stays below one KiB. The source AST is
        # read, but no full harness, native adapter, build or launch is run.
        for data in (raw, extra):
            with tempfile.TemporaryDirectory(prefix="clash-log-ps-parity-") as directory:
                script, log = Path(directory) / "parse.ps1", Path(directory) / "original.log"
                script.write_text(helper, encoding="ascii")
                log.write_bytes(data)
                completed = subprocess.run([str(POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                                            "-Runner", str(RUNNER), "-Log", str(log)], capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                actual = observations.parse_soak_log(data)
                self.assertFalse(actual.pop("failures"))
                self.assertEqual(actual, json.loads(completed.stdout))
                self.assertLess(max(len(data), len(helper)), 1024)


def run_tests() -> None:
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(LogObservationTests))
    if not result.wasSuccessful() or result.skipped:
        raise RuntimeError("retained-log observation tests did not pass completely")


if __name__ == "__main__":
    run_tests()

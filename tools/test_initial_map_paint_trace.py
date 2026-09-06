#!/usr/bin/env python3
"""Synthetic offline initial paint/event/call fixtures; no game or debugger."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import initial_map_paint_trace as trace
from partial_tile_trace_probe import instrument_probe


SHA = "a" * 64
TID, INITIAL_SP = 0xABC, 0x100000
FULL_SP = INITIAL_SP - 88
SITES = {bp: 0x700000 + (bp - 70) * 0x100 for bp in range(70, 78)}


def status(hook: str, esp: int, value: int = 1, *, tid: int = TID) -> str:
    return (f"PTILE_STATUS hook={hook} status={value} tid={tid:x} esp={esp:08x} "
            "owner=0040ad40 tile=00000000 post=00000000 lower=00000000 player=0")


def event(bp: int, esp: int, *records: str, tid: int = TID) -> dict:
    return dict(bp=bp, tid=tid, eip=SITES[bp], esp=esp, records=list(records))


def initial_events(resolution: str = "800x600", result: str = "deadbeef", *, framed: bool = False) -> list[dict]:
    width, height = resolution.split("x")
    full_sp = INITIAL_SP - (148 if framed else 88)
    return [
        event(76, INITIAL_SP, f"PTILE_INITIAL_ADMISSION status=1 tid={TID:x} esp={INITIAL_SP:08x}"),
        event(73, INITIAL_SP, f"PTILE_MAP_READY owner=0040ad40 size=({width},{height})"),
        event(70, full_sp, status("full_converge", full_sp)),
        event(71, full_sp, status("full_present", full_sp)),
        event(77, INITIAL_SP, f"PTILE_INITIAL_RETURN tid={TID:x} esp={INITIAL_SP:08x} result={result}"),
    ]


def auxiliary(*, noop: bool = False, clear: bool = False, world: tuple[int, int] | None = None,
              scroll: tuple[int, int] = (0, 0)) -> list[dict]:
    native_sp = 0x200000
    x, y, width, height = (20, 20, 50, 50) if noop else (10, 0, 10, 50) if clear else (0, 0, 50, 50)
    if world is not None:
        x, y = world
    sx, sy = scroll
    guard_sp, input_sp, exit_sp = native_sp - 120, native_sp - 36, native_sp - 28
    tail = f"world=({x},{y}) caller=0040ad80 gd=00600000 map=({width},{height}) scroll=({sx},{sy}) vtable=0050ee24"
    rows = [event(75, guard_sp, f"PTILE_COMPOSITION_GUARD tid={TID:x} esp={guard_sp:08x} status=1 world=({x},{y}) cell=({x-sx},{y-sy}) present=1 caller=0040ad80"),
            event(72, input_sp, f"PTILE_INCREMENTAL_INPUT tid={TID:x} esp={input_sp:08x} {tail}",
                  status("incremental", input_sp, 0 if noop else 2 if clear else 1))]
    if noop:
        rows.append(event(74, exit_sp, f"PTILE_NATIVE_NOOP_EXIT tid={TID:x} esp={exit_sp:08x} {tail}"))
    return rows


def fixture(events: list[dict] | None = None, *, resolution: str = "800x600", close: str | None = None,
            stage: str = trace.STAGE) -> tuple[str, str]:
    events = initial_events(resolution, framed=stage == trace.FRAMED_STAGE) if events is None else events
    contract = f"PTILE_CONTRACT_PASS stage={stage} resolution={resolution} candidate_sha256={SHA}"
    scope = "PTILE_SCOPE guarded_map_only manual_input_proof=false promotion_ready=false"
    # Synthetic declarations are never executed; real instrumenter and event
    # validator verify their call-site and counter grammar.
    members = {70: "PTILE_STATUS hook=full_converge", 71: "PTILE_STATUS hook=full_present",
               72: "PTILE_INCREMENTAL_INPUT PTILE_STATUS hook=incremental", 73: "PTILE_MAP_READY",
               74: "PTILE_NATIVE_NOOP_EXIT", 75: "PTILE_COMPOSITION_GUARD",
               76: "PTILE_INITIAL_ADMISSION", 77: "PTILE_INITIAL_RETURN"}
    probe = ".echo " + contract + "\n.echo " + scope + "\n" + "\n".join(
        f'bp{bp} {SITES[bp]:08x} ".echo {members[bp]}; gc"' for bp in range(70, 78)) + "\n"
    probe = instrument_probe(probe, reset_bp=76)
    lines = [contract, scope]
    for seq, row in enumerate(events, 1):
        lines.append(f"PTILE_EVENT seq={seq} bp={row['bp']} tid={row['tid']:x} eip={row['eip']:08x} esp={row['esp']:08x}")
        lines.extend(row["records"])
    if close is None:
        close = f"PTILE_TRACE_CLOSED tid={TID:x} eip=00406fa0 esp=00100100"
    if close:
        lines.extend([close, "SURFDUMP_HOST_READY fixture=synthetic"])
    return "\n".join(lines) + "\n", probe


def evaluate(log: str, probe: str, **kwargs) -> dict:
    return trace.evaluate_trace(log, probe, resolution=kwargs.get("resolution", "800x600"),
                                candidate_sha256=kwargs.get("candidate_sha256", SHA), stage=kwargs.get("stage", trace.STAGE))


class InitialPaintTraceTests(unittest.TestCase):
    def assert_rejected(self, log: str, probe: str, **kwargs) -> dict:
        report = evaluate(log, probe, **kwargs)
        self.assertFalse(report["passed"], report)
        self.assertTrue(report["failures"])
        return report

    def test_multiple_resolutions_and_uninterpreted_return_eax(self):
        for resolution in ("800x600", "1024x768", "1920x1080"):
            for eax in ("0", "1", "deadbeef", "ffffffff"):
                with self.subTest(resolution=resolution, eax=eax):
                    log, probe = fixture(initial_events(resolution, eax), resolution=resolution)
                    report = evaluate(log, probe, resolution=resolution)
                    self.assertTrue(report["passed"], report["failures"])
                    self.assertEqual(report["initial_sequence"]["return_eax"], int(eax, 16))
                    self.assertFalse(report["promotion_ready"])
                    self.assertFalse(report["manual_input_proof"])

    def test_auxiliary_calls_and_later_full_pairs_are_separate(self):
        events = initial_events()
        events[2:2] = auxiliary()  # An actual complete nested/native call is allowed.
        events += auxiliary(noop=True) + auxiliary(clear=True)
        events += [event(70, 0x300000, status("full_converge", 0x300000)), event(71, 0x300000, status("full_present", 0x300000))]
        report = evaluate(*fixture(events))
        self.assertTrue(report["passed"], report["failures"])
        self.assertEqual(len(report["full_pairs"]), 2)
        self.assertNotEqual(report["initial_sequence"]["pair"]["esp"], report["full_pairs"][-1]["esp"])

    def test_initial_sequence_missing_repeated_or_reordered(self):
        for index in range(5):
            with self.subTest(missing=index):
                events = initial_events(); del events[index]
                self.assert_rejected(*fixture(events))
            with self.subTest(repeated=index):
                events = initial_events(); events.insert(index, copy.deepcopy(events[index]))
                self.assert_rejected(*fixture(events))
        for left, right in ((0, 1), (1, 2), (2, 3), (3, 4)):
            events = initial_events(); events[left], events[right] = events[right], events[left]
            self.assert_rejected(*fixture(events))

    def test_initial_thread_stack_status_and_context_must_match(self):
        for index in (1, 2, 3, 4):
            for field, delta in (("esp", 4), ("tid", 1)):
                events = initial_events(); target = events[index]
                old = target[field]; target[field] += delta
                target["records"] = [text.replace(f"{field}={old:08x}" if field == "esp" else f"tid={old:x}",
                                                 f"{field}={target[field]:08x}" if field == "esp" else f"tid={target[field]:x}") for text in target["records"]]
                self.assert_rejected(*fixture(events))
        for old, new in (("status=1", "status=0"), ("owner=0040ad40", "owner=004617a0"),
                         ("post=00000000", "post=00000001"), ("player=0", "player=1"),
                         ("tile=00000000", "tile=00425120")):
            events = initial_events(); events[3]["records"][0] = events[3]["records"][0].replace(old, new)
            self.assert_rejected(*fixture(events))

    def test_contract_scope_stage_resolution_and_candidate_identity(self):
        log, probe = fixture()
        for old, new in ((SHA, "b" * 64), ("size=(800,600)", "size=(1024,768)"),
                         ("manual_input_proof=false", "manual_input_proof=true")):
            self.assert_rejected(log.replace(old, new), probe)
        self.assert_rejected(log, probe.replace(SHA, "b" * 64))
        self.assert_rejected(log, probe, stage=trace.STAGE.replace("-initialpaint", ""))
        self.assert_rejected(log, probe, candidate_sha256="a" * 63)
        for resolution in ("0800x600", "800X600", "0x600", "800x0", "9000x600"):
            self.assert_rejected(log, probe, resolution=resolution)
        self.assert_rejected(log.splitlines()[0] + "\n" + log, probe)
        self.assert_rejected(log, probe + probe.splitlines()[0] + "\n")

    def test_initial_zero_callback_is_stricter_than_later_redraw_policy(self):
        for callback in ("00425120", "00429ec0"):
            with self.subTest(callback=callback):
                events = initial_events()
                for row in events[2:4]:
                    row["records"][0] = row["records"][0].replace("tile=00000000", "tile=" + callback)
                self.assert_rejected(*fixture(events))
                later = [event(70, 0x300000, status("full_converge", 0x300000)),
                         event(71, 0x300000, status("full_present", 0x300000))]
                for row in later:
                    row["records"][0] = row["records"][0].replace("tile=00000000", "tile=" + callback)
                report = evaluate(*fixture(initial_events() + later))
                self.assertTrue(report["passed"], report["failures"])

    def test_close_required_exact_and_after_return(self):
        self.assert_rejected(*fixture(close=""))
        log, probe = fixture()
        close = next(line for line in log.splitlines() if line.startswith("PTILE_TRACE_CLOSED"))
        for old, new in (("tid=abc", "tid=abd"), ("eip=00406fa0", "eip=00406fa1"),
                         ("esp=00100100", "esp=00000000"), ("esp=00100100", "esp=00100101")):
            self.assert_rejected(log.replace(close, close.replace(old, new)), probe)
        self.assert_rejected(log + close + "\n", probe)
        self.assert_rejected(log.replace(close + "\n", "").replace("PTILE_EVENT seq=5", close + "\nPTILE_EVENT seq=5"), probe)
        self.assert_rejected(log.replace(close, "SURFDUMP_HOST_READY early\n" + close), probe)

    def test_output_replay_case_changes_and_unfinished_records_fail(self):
        log, probe = fixture()
        for old, new in (("seq=4", "seq=3"), ("PTILE_STATUS", "ptile_status"),
                         ("hook=full_present", "hook=FULL_PRESENT"), ("status=1", "status=1 extra=1"),
                         ("result=deadbeef", "result=xyz"), ("status=1", "status=2147483648")):
            self.assert_rejected(log.replace(old, new, 1), probe)
        events = initial_events(); events[-1]["records"] = []
        self.assert_rejected(*fixture(events))
        for tail in ("PTILE_REJECT unexpected", "PTILE_UNKNOWN value=1", "ptile_status replay",
                     "PTILE_EVENT seq=6 bp=77 tid=abc eip=00700700 esp=00100000"):
            self.assert_rejected(log + tail + "\n", probe)
        self.assert_rejected(log.replace("PTILE_INITIAL_RETURN", "PTILE_UNKNOWN"), probe)

    def test_auxiliary_zeros_never_become_draw_or_unfinished_call_proof(self):
        for mode in ("orphan_input", "duplicate_guard", "duplicate_status", "missing_exit", "changed_exit",
                     "zero_visible", "false_clear", "unfinished_full", "unfinished_guard"):
            with self.subTest(mode=mode):
                tail = auxiliary(noop=True)
                if mode == "orphan_input": del tail[0]
                elif mode == "duplicate_guard": tail.insert(1, copy.deepcopy(tail[0]))
                elif mode == "duplicate_status": tail.append(copy.deepcopy(tail[1]))
                elif mode == "missing_exit": tail.pop()
                elif mode == "changed_exit": tail[-1]["records"][0] = tail[-1]["records"][0].replace("world=(20,20)", "world=(21,20)")
                elif mode == "zero_visible":
                    tail = auxiliary(); tail[1]["records"][1] = tail[1]["records"][1].replace("status=1", "status=0")
                elif mode == "false_clear":
                    tail = auxiliary(); tail[1]["records"][1] = tail[1]["records"][1].replace("status=1", "status=2")
                elif mode == "unfinished_full": tail = [event(70, 0x300000, status("full_converge", 0x300000))]
                elif mode == "unfinished_guard": tail = tail[:1]
                self.assert_rejected(*fixture(initial_events() + tail))

    def test_native_pair_before_return_cannot_be_supplied_later(self):
        events = initial_events()
        events[3], events[4] = events[4], events[3]
        self.assert_rejected(*fixture(events))

    def test_framed_contract_native_hd_custom_geometry_and_return_values(self):
        # Independent literal oracle for physical borders, not imported emitter
        # values that would make a shared wrong formula self-confirming.
        cases = (("640x480", [9, 7], [9, 7]), ("800x600", [11, 8], [12, 9]),
                 ("1024x768", [15, 11], [15, 12]), ("1280x720", [19, 10], [19, 11]),
                 ("1280x960", [19, 14], [19, 15]), ("1920x1080", [29, 16], [29, 17]),
                 ("802x602", [11, 8], [12, 9]))
        for resolution, floor, ceil in cases:
            for result in ("0", "1", "deadbeef"):
                with self.subTest(resolution=resolution, result=result):
                    events = initial_events(resolution, result, framed=True) + auxiliary()
                    report = evaluate(*fixture(events, resolution=resolution, stage=trace.FRAMED_STAGE),
                                      resolution=resolution, stage=trace.FRAMED_STAGE)
                    self.assertTrue(report["passed"], report["failures"])
                    contract = report["trace_contract"]
                    width, height = map(int, resolution.split("x"))
                    self.assertEqual(contract, {"profile": "native_four_border_tiles_v1",
                        "terrain_inclusive": [32, 16, width - 33, height - 17],
                        "full_tiles": floor, "ceil_tiles": ceil, "full_status_to_ready_stack_bytes": 148})
                    self.assertEqual(report["initial_sequence"]["return_eax"], int(result, 16))
                    self.assertFalse(report["manual_input_proof"])
                    self.assertFalse(report["promotion_ready"])
        legacy = evaluate(*fixture())
        self.assertTrue(legacy["passed"])
        self.assertEqual(legacy["trace_contract"]["full_status_to_ready_stack_bytes"], 88)
        self.assertEqual(legacy["trace_contract"]["terrain_inclusive"], [32, 16, 799, 599])

    def test_stage_controls_stack_contract_without_legacy_fallback(self):
        for stage, events in ((trace.FRAMED_STAGE, initial_events()),
                              (trace.STAGE, initial_events(framed=True))):
            report = self.assert_rejected(*fixture(events, stage=stage), stage=stage)
            self.assertTrue(any("normalized stack" in error for error in report["failures"]))
        framed_log, framed_probe = fixture(stage=trace.FRAMED_STAGE)
        old_log, old_probe = fixture()
        self.assert_rejected(old_log, old_probe, stage=trace.FRAMED_STAGE)
        self.assert_rejected(framed_log, framed_probe, stage=trace.STAGE)
        self.assert_rejected(framed_log, old_probe, stage=trace.FRAMED_STAGE)
        for stage in (trace.FRAMED_STAGE.upper(), trace.FRAMED_STAGE + "-extra",
                      trace.FRAMED_STAGE.replace("-framed-validation", "-framed"),
                      trace.STAGE.replace("-initialpaint-validation", "-validation")):
            self.assert_rejected(*fixture(stage=stage), stage=stage)

    def test_framed_auxiliary_boundaries_reject_old_visible_cells(self):
        # Each point was a visible legacy tile but is outside the framed grid.
        for resolution, world in (("800x600", (0, 9)), ("1024x768", (15, 0)),
                                  ("802x602", (12, 0)), ("802x602", (0, 9))):
            with self.subTest(resolution=resolution, world=world):
                valid = auxiliary(noop=True, world=world)
                report = evaluate(*fixture(initial_events(resolution, framed=True) + valid,
                                           resolution=resolution, stage=trace.FRAMED_STAGE),
                                  resolution=resolution, stage=trace.FRAMED_STAGE)
                self.assertTrue(report["passed"], report["failures"])
                self.assert_rejected(*fixture(initial_events(resolution) + valid, resolution=resolution),
                                     resolution=resolution)
                wrong_draw = auxiliary(world=world)
                report = self.assert_rejected(*fixture(initial_events(resolution, framed=True) + wrong_draw,
                                                       resolution=resolution, stage=trace.FRAMED_STAGE),
                                              resolution=resolution, stage=trace.FRAMED_STAGE)
                self.assertTrue(any("actual bounds" in error for error in report["failures"]))
                legacy = evaluate(*fixture(initial_events(resolution) + wrong_draw, resolution=resolution),
                                  resolution=resolution)
                self.assertTrue(legacy["passed"], legacy["failures"])

    def test_framed_scroll_limit_uses_smaller_full_grid_and_remains_bounded(self):
        # In a50x50 world framed800 has floor11x8, hence max scroll39x42.
        # The older12x9 floor admits only38x41.
        valid = auxiliary(world=(39, 42), scroll=(39, 42))
        framed = evaluate(*fixture(initial_events(framed=True) + valid, stage=trace.FRAMED_STAGE),
                          stage=trace.FRAMED_STAGE)
        self.assertTrue(framed["passed"], framed["failures"])
        self.assert_rejected(*fixture(initial_events() + valid))
        for scroll in ((40, 42), (39, 43), (-1, 0), (0, -1)):
            report = self.assert_rejected(*fixture(initial_events(framed=True) +
                                                   auxiliary(world=scroll, scroll=scroll), stage=trace.FRAMED_STAGE),
                                          stage=trace.FRAMED_STAGE)
            self.assertTrue(any("map/scroll context" in error for error in report["failures"]))

    def test_framed_keeps_numbered_auxiliary_closure_and_native_exit_integrity(self):
        events = initial_events(framed=True) + auxiliary(noop=True, world=(0, 9))
        good_log, probe = fixture(events, stage=trace.FRAMED_STAGE)
        mutations = (("seq=4", "seq=3"), ("PTILE_STATUS", "ptile_status"),
                     ("player=0", "player=1"), ("tile=00000000", "tile=00425120"),
                     ("result=deadbeef", "result=xyz"),
                     ("hook=full_present status=1", "hook=full_present status=0"),
                     ("PTILE_NATIVE_NOOP_EXIT", "PTILE_UNDECLARED_EXIT"),
                     ("PTILE_TRACE_CLOSED tid=abc", "PTILE_TRACE_CLOSED tid=abd"))
        for old, new in mutations:
            with self.subTest(old=old):
                self.assert_rejected(good_log.replace(old, new, 1), probe, stage=trace.FRAMED_STAGE)
        for remove in (2, 3, 4, 5, 7):
            incomplete = copy.deepcopy(events)
            del incomplete[remove]
            self.assert_rejected(*fixture(incomplete, stage=trace.FRAMED_STAGE), stage=trace.FRAMED_STAGE)
        wrong_exit = copy.deepcopy(events)
        wrong_exit[-1]["records"][0] = wrong_exit[-1]["records"][0].replace("world=(0,9)", "world=(0,8)")
        self.assert_rejected(*fixture(wrong_exit, stage=trace.FRAMED_STAGE), stage=trace.FRAMED_STAGE)
        self.assert_rejected(*fixture(events, close="", stage=trace.FRAMED_STAGE), stage=trace.FRAMED_STAGE)
        self.assert_rejected(good_log + "PTILE_STATUS unexpected_after_close\n", probe, stage=trace.FRAMED_STAGE)

    def test_framed_rejects_noncanonical_physical_geometry_without_changing_legacy(self):
        for resolution in ("100x100", "638x480", "800x478", "801x600", "800x601"):
            with self.subTest(resolution=resolution):
                self.assert_rejected(*fixture(resolution=resolution, stage=trace.FRAMED_STAGE),
                                     resolution=resolution, stage=trace.FRAMED_STAGE)
                report = evaluate(*fixture(resolution=resolution), resolution=resolution)
                self.assertTrue(report["passed"], "legacy geometry behavior changed: " + str(report["failures"]))

    def test_cli_is_read_only_and_fails_missing_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log, probe = fixture()
            (root / "log.txt").write_text(log, encoding="utf-8")
            (root / "extra.cdb").write_text(probe, encoding="ascii")
            command = [sys.executable, "-B", str(Path(trace.__file__)), "--log", str(root / "log.txt"),
                       "--probe", str(root / "extra.cdb"), "--resolution", "800x600", "--candidate-sha256", SHA, "--stage", trace.STAGE]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["passed"])
            self.assertEqual(set(path.name for path in root.iterdir()), {"log.txt", "extra.cdb"})
            log, probe = fixture(stage=trace.FRAMED_STAGE)
            (root / "log.txt").write_text(log, encoding="utf-8")
            (root / "extra.cdb").write_text(probe, encoding="ascii")
            command[-1] = trace.FRAMED_STAGE
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["trace_contract"]["full_status_to_ready_stack_bytes"], 148)
            self.assertEqual(set(path.name for path in root.iterdir()), {"log.txt", "extra.cdb"})
            (root / "extra.cdb").unlink()
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["passed"])


if __name__ == "__main__":
    unittest.main()

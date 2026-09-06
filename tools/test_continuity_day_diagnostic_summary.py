#!/usr/bin/env python3
"""Synthetic offline diagnostic evidence fixtures; never runs game or CDB."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import continuity_day_diagnostic_summary as tool

STAGE = tool.STABLE + "-combinedui-validation"
CANDIDATE_SHA = "0a75cf35f42efe1e44fba1ac4031eaae5323cdff51aa19d261c36c5bb84691c2"
RUN = r"C:\ClashCaptures\fixture\daydiag"
CANDIDATE = r"C:\ClashTests\fixture\candidate\fixture.exe"
PROBE = RUN + r"\generated.cdb"


def marker_lines(mode=0, *, wait=False):
    lines = [f"CommandLine: {CANDIDATE}", f"0:000> $$><{PROBE}",
             "(64.65): Break instruction exception - code 80000003 (first chance)",
             "DAYDIAG_CONTRACT_PASS resolution=800x600 candidate_sha_source=matching_outer_byte_report byte_gate_required=1",
             "DAYDIAG_PLAYERS active=(1,1,1,1,1) controller=(1,0,0,0,1)",
             f"DAYDIAG_START mode={mode} player=0 day=20 gd=10000000 tick=100 forced_nextplayer=1"]
    tick = 100
    for advance in range(1, 6):
        previous, player = advance - 1, advance % 5
        day = 21 if player == 0 else 20
        tick += 128
        lines.append(f"DAYDIAG_NEXT_CALL advance={advance} player={previous} day=20 tick={tick} saved_esp=000edbb0 mechanism=forced_native_call")
        if player == 0:
            lines.append(f"DAYDIAG_NATIVE_DAY_INCREMENT advance={advance} player=0 day=21 gd=10000000")
        lines.append(f"DAYDIAG_AFTER_DAY_BRANCH advance={advance} player={player} day={day}")
        if advance == 1 and (mode == 1 or wait):
            lines.append("DAYDIAG_BANNER_ENTRY advance=1 player=1 day=20 ret=0040ac1f")
            for poll in range(1, 9):
                lines.extend([
                    "DAYDIAG_INPUT_POLL_ENTRY ret=004608ab object=00545198 mouse_enabled=1 keyboard_enabled=1 joystick_enabled=0",
                    "DAYDIAG_GETDEVICESTATE_CALL device=mouse target=70000123 bytes=16",
                    "DAYDIAG_GETDEVICESTATE_RETURN device=mouse hresult=00000000",
                    f"DAYDIAG_BANNER_TEST poll={poll} observed_eax=0 button_flags=0 lbtn=00 rbtn=00 player=1 day=20",
                ])
            if wait:
                lines.append("DAYDIAG_OBSERVED_BANNER_INPUT_WAIT acknowledgment_not_attempted=1")
                return lines
            lines.append("DAYDIAG_FORCED_BANNER_ACK banner_tests=8 observed_eax=0 mechanism=override_banner_button_result value=1 manual_input_proof=0")
            lines.append("DAYDIAG_BANNER_EXIT player=1 day=20 mode=2")
        tick += 10
        lines.append(f"DAYDIAG_NEXT_RETURN advance={advance} player={player} day={day} tick={tick} esp=000edbb0")
    lines.extend([
        f"DAYDIAG_FULL_DAY_RETURNED initial_day=20 final_day=21 player=0 mode={2 if mode else 0}",
        "DAYDIAG_POST_DAY_REDRAW player=0 day=21 dump_released=1",
        "SURFDUMP_READY redraw_seq=17 surface=10001000 size=(800,600) base=10002000 bytes=480000",
        "SURFDUMP_HOST_READY",
    ])
    return lines


def release_lines(*, player=1, day=20, controlled=False, bounded=False, right_tests=1):
    """Synthetic shared-left-iteration trace, with actual per-button counts."""
    rows = [f"DAYDIAG_RELEASE_WAIT_ENTRY ret=0040aa06 object=00544cd8 player={player} day={day} esp=000edb60"]
    for poll in range(1, 9):
        # For the all-right-loop case, left is already released each iteration.
        left = 0 if right_tests == 8 else 1
        flags = 2 if left == 0 else 3
        rows.append(f"DAYDIAG_RELEASE_LEFT_TEST poll={poll} observed_eax={left} button_flags={flags:x} lbtn=80 rbtn=80 player={player} day={day}")
        if controlled and poll == 8 and left:
            rows.append("DAYDIAG_FORCED_RELEASE button=left tests=8 observed_eax=1 mechanism=override_release_button_result value=0 manual_input_proof=0")
        if right_tests == 8 or controlled and poll == 8:
            rows.append(f"DAYDIAG_RELEASE_RIGHT_TEST poll={poll} observed_eax=1 button_flags={flags:x} lbtn=80 rbtn=80 player={player} day={day}")
        if poll < 8:
            rows.extend(["DAYDIAG_INPUT_POLL_ENTRY ret=00460a61 object=00545198 mouse_enabled=1 keyboard_enabled=1 joystick_enabled=0",
                         "DAYDIAG_GETDEVICESTATE_CALL device=mouse target=70000123 bytes=16",
                         "DAYDIAG_GETDEVICESTATE_RETURN device=mouse hresult=8007000c"])
    if bounded:
        rows.append(f"DAYDIAG_OBSERVED_RELEASE_INPUT_WAIT button={'right' if right_tests == 8 else 'left'} tests=8 release_not_attempted=1")
    elif controlled:
        rows.append(f"DAYDIAG_FORCED_RELEASE button=right tests={right_tests} observed_eax=1 mechanism=override_release_button_result value=0 manual_input_proof=0")
        rows.append(f"DAYDIAG_RELEASE_RETURN player={player} day={day} esp=000edb64")
    return rows


class SummaryTests(unittest.TestCase):
    def evidence(self, mode=0, *, wait=False):
        lines = marker_lines(mode, wait=wait)
        probe = f".echo synthetic fixture only\ned 00400304 {mode}\n".encode()
        summary = {
            "Passed": not wait, "Error": "surface dump was not completed" if wait else None,
            "CandidateSha256": CANDIDATE_SHA, "CandidatePath": CANDIDATE, "RunDir": RUN,
            "GeneratedProbe": PROBE, "Log": RUN + r"\raw.log", "Stage": STAGE, "Resolution": "800x600",
            "HiddenDesktop": True, "AllowVisibleDesktop": False, "LaunchMode": "hidden-desktop",
            "UseDdrawProxy": True, "ProxyPresentSetting": "0", "DdrawProxySha256": "d" * 64,
            "LoadSlot": 0, "ForceVisibleEdges": False, "PostOwnerForceVisibleSeven": False,
            "SkipMapValidation": False, "Av": False, "AppRequestQuit": False, "HostDumpError": None,
            "TimedOut": False, "SurfaceGeometryMatched": not wait, "HostDumpedMemory": not wait,
            "DumpMethod": "host-readprocessmemory", "RawBytes": 0 if wait else 480000,
            "RawPath": RUN + r"\surface.raw",
            "Surface": {"RedrawSeq": 17, "Surface": "10001000", "Width": 800, "Height": 600,
                        "Base": "10002000", "Bytes": 480000},
        }
        # Shape matches the real patch-stage producer. These deliberately
        # synthetic rows are fixture data, never published runtime evidence.
        report = {"stage": STAGE, "resolution": "800x600", "exe_sha256": CANDIDATE_SHA,
                  "expected_base_sha256": tool.ORIGINAL_SHA, "patch_count": 166,
                  "status_counts": {"patched": 166}, "current_hd_map_gate": {"passed": True, "failures": []},
                  "patches": [{"offset": i * 2, "status": "patched", "old": "00", "new": "01", "actual": "01"} for i in range(166)]}
        cleanup = {"schema": tool.CLEANUP_SCHEMA, "observed_at": "2026-09-05T12:00:00+02:00",
                   "stage": STAGE, "resolution": "800x600", "candidate_sha256": CANDIDATE_SHA,
                   "candidate_path": CANDIDATE, "run_dir": RUN, "generated_probe_sha256": tool.sha(probe),
                   "game_pid": 100, "cdb_pid": 101, "game_stopped": True, "cdb_stopped": True, "errors": []}
        return {"summary": summary, "lines": lines, "probe": probe, "report": report, "cleanup": cleanup,
                "raw": None if wait else bytes([1]) * 480000, "mode": mode}

    def grade(self, evidence, *, bind_log=True, **overrides):
        log = ("\n".join(evidence["lines"]) + "\n").encode()
        cleanup = copy.deepcopy(evidence["cleanup"])
        if cleanup is not None and bind_log:
            cleanup["log_sha256"] = tool.sha(log)
        if cleanup is not None and evidence["raw"] is not None:
            cleanup.setdefault("surface_sha256", tool.sha(evidence["raw"]))
        kwargs = {"expected_stage": STAGE, "expected_candidate_sha256": CANDIDATE_SHA,
                  "expected_generated_probe_sha256": tool.sha(evidence["probe"]),
                  "expected_mode": evidence["mode"], "raw_data": evidence["raw"]}
        kwargs.update(overrides)
        return tool.evaluate(evidence["summary"], log, evidence["probe"], evidence["report"], cleanup, **kwargs)

    def modern_evidence(self, *, right_tests=1, mode=1, banner_ack=True, controlled_release=True, version=5):
        data = self.evidence(1)
        data["mode"] = mode
        data["lines"].insert(3, f"=== Clash95 bounded day-transition diagnostic v{version} ===")
        data["probe"] = f".echo === Clash95 bounded day-transition diagnostic v{version} ===\ned 00400304 {mode}\n".encode()
        data["cleanup"]["generated_probe_sha256"] = tool.sha(data["probe"])
        if not banner_ack:
            begin = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_BANNER_ENTRY"))
            end = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_BANNER_EXIT"))
            data["lines"][begin:end + 1] = [
                "DAYDIAG_BANNER_ENTRY advance=1 player=1 day=20 ret=0040ac1f",
                "DAYDIAG_BANNER_TEST poll=1 observed_eax=1 button_flags=1 lbtn=80 rbtn=00 player=1 day=20",
                f"DAYDIAG_BANNER_EXIT player=1 day=20 mode={mode}",
            ]
        data["lines"] = [row.replace("START mode=1", f"START mode={mode}").replace(
            "FULL_DAY_RETURNED initial_day=20 final_day=21 player=0 mode=2",
            f"FULL_DAY_RETURNED initial_day=20 final_day=21 player=0 mode={2 if banner_ack else mode}")
            for row in data["lines"]]
        position = next(i for i, line in enumerate(data["lines"]) if line.startswith("DAYDIAG_BANNER_EXIT")) + 1
        release = release_lines(controlled=True, right_tests=right_tests) if controlled_release else [
            "DAYDIAG_RELEASE_WAIT_ENTRY ret=0040aa06 object=00544cd8 player=1 day=20 esp=000edb60",
            "DAYDIAG_RELEASE_LEFT_TEST poll=1 observed_eax=0 button_flags=0 lbtn=00 rbtn=00 player=1 day=20",
            "DAYDIAG_RELEASE_RIGHT_TEST poll=1 observed_eax=0 button_flags=0 lbtn=00 rbtn=00 player=1 day=20",
            "DAYDIAG_RELEASE_RETURN player=1 day=20 esp=000edb64",
        ]
        if version in (6, 7):
            release.append("DAYDIAG_INPUT_TRACE_END phase=release_wait")
        data["lines"][position:position] = release
        if version == 7:
            # Independent synthetic identities at the source-authenticated native
            # observation sites. The poll prologue/three pushed COM arguments
            # make call ESP=poll ESP-0x74, return ESP=call ESP+12.
            sites = {"DAYDIAG_NEXT_CALL": ("00406fa1", "000edbb0"),
                     "DAYDIAG_NEXT_RETURN": ("00406fa1", None),
                     "DAYDIAG_BANNER_ENTRY": ("0040a820", "000edb70"),
                     "DAYDIAG_BANNER_EXIT": ("0040a9fa", "000edb44"),
                     "DAYDIAG_RELEASE_WAIT_ENTRY": ("004609d0", None),
                     "DAYDIAG_RELEASE_RETURN": ("0040aa06", None),
                     "DAYDIAG_INPUT_POLL_ENTRY": ("0047bfd1", "000eda80"),
                     "DAYDIAG_GETDEVICESTATE_CALL": ("0047c029", "000eda0c"),
                     "DAYDIAG_GETDEVICESTATE_RETURN": ("0047c02c", "000eda18")}
            for index, row in enumerate(data["lines"]):
                site = sites.get(row.split(" ", 1)[0])
                if site:
                    eip, esp = site
                    data["lines"][index] += f" tid=44 eip={eip}" + (f" esp={esp}" if esp else "")
        return data

    def test_v7_exact_input_identity_and_owner_provenance(self):
        data = self.modern_evidence(version=7)
        result = self.grade(data)
        self.assertTrue(result["passed"], result["failures"])
        markers = result["markers"]
        self.assertEqual(len(markers["input_returns"]), 15)
        self.assertTrue(all(row["owner_thread"] for row in markers["input_returns"]))
        self.assertTrue(all(row["identity"]["tid"] == row["return_identity"]["tid"] == 0x44
                            and row["return_identity"]["esp"] == row["identity"]["esp"] + 12
                            for row in markers["input_returns"]))
        self.assertEqual(len(markers["input_failure_hresult"]), 7)
        self.assertTrue(markers["input_identity_observations"])
        self.assertFalse(result["manual_input_proof"])
        self.assertFalse(result["promotion_evidence"])

    def test_v7_interleaved_threads_pair_separately_without_becoming_owner_proof(self):
        data = self.modern_evidence(version=7)
        rows = data["lines"]
        poll = next(i for i, row in enumerate(rows) if row.startswith("DAYDIAG_INPUT_POLL_ENTRY"))
        foreign = [row.replace("tid=44", "tid=88").replace("000eda", "000eca")
                   for row in rows[poll:poll + 3]]
        # Owner call is pending while a different OS thread completes its call.
        rows[poll + 2:poll + 2] = foreign
        result = self.grade(data)
        self.assertTrue(result["passed"], result["failures"])
        pairs = result["markers"]["input_returns"]
        self.assertEqual(sum(not row["owner_thread"] for row in pairs), 1)
        self.assertEqual(pairs[0]["identity"]["tid"], 0x88)
        self.assertEqual(pairs[1]["identity"]["tid"], 0x44)
        self.assertEqual(result["markers"]["input_trace_phases"][0]["poll_count"], 9)
        # A foreign return cannot close the owner's outstanding call.
        broken = copy.deepcopy(data)
        owner_return = next(i for i, row in enumerate(broken["lines"])
                            if row.startswith("DAYDIAG_GETDEVICESTATE_RETURN") and "tid=44" in row)
        broken["lines"][owner_return] = broken["lines"][owner_return].replace("tid=44", "tid=88")
        self.assertFalse(self.grade(broken)["passed"])

    def test_v7_missing_wrong_and_duplicate_identities_fail_without_dropping_returns(self):
        data = self.modern_evidence(version=7)
        for mutation in ("missing_tid", "zero_tid", "wide_tid", "wrong_eip", "unaligned_esp", "call_stack",
                         "return_stack", "return_thread", "duplicate_call", "duplicate_return", "second_pair",
                         "call_without_thread_poll", "disabled_device", "undeclared_version"):
            changed = copy.deepcopy(data)
            rows = changed["lines"]
            call = next(i for i, row in enumerate(rows) if row.startswith("DAYDIAG_GETDEVICESTATE_CALL"))
            ret = call + 1
            if mutation == "missing_tid":
                rows[ret] = rows[ret].replace(" tid=44", "")
            elif mutation in ("zero_tid", "wide_tid", "return_thread"):
                rows[ret] = rows[ret].replace("tid=44", "tid=" + {"zero_tid": "0", "wide_tid": "100000000", "return_thread": "88"}[mutation])
            elif mutation == "wrong_eip":
                rows[ret] = rows[ret].replace("eip=0047c02c", "eip=0047c02d")
            elif mutation in ("unaligned_esp", "return_stack"):
                rows[ret] = rows[ret].replace("esp=000eda18", "esp=" + ("000eda19" if mutation == "unaligned_esp" else "000eda1c"))
            elif mutation == "call_stack":
                rows[call] = rows[call].replace("esp=000eda0c", "esp=000eda10")
            elif mutation == "call_without_thread_poll":
                rows[call] = rows[call].replace("tid=44", "tid=88")
            elif mutation == "disabled_device":
                rows[call - 1] = rows[call - 1].replace("mouse_enabled=1", "mouse_enabled=0")
            elif mutation == "duplicate_call":
                rows.insert(call + 1, rows[call])
            elif mutation == "duplicate_return":
                rows.insert(ret + 1, rows[ret])
            elif mutation == "second_pair":
                rows[ret + 1:ret + 1] = rows[call:ret + 1]
            else:
                rows[:] = [row.replace("diagnostic v7", "diagnostic v6") for row in rows]
            result = self.grade(changed)
            self.assertFalse(result["passed"], mutation)
            self.assertGreaterEqual(len(result["markers"]["input_return_observations"]), 15, mutation)
        # Repeated failed returns stay repeated raw failures, including identity.
        rows = copy.deepcopy(data["lines"])
        ret = next(i for i, row in enumerate(rows) if "hresult=8007000c" in row)
        rows.insert(ret + 1, rows[ret])
        result = tool.analyze_markers("\n".join(rows))
        self.assertTrue(result["errors"])
        self.assertEqual(len(result["input_failure_hresult"]), 8)
        self.assertEqual(result["input_failure_hresult"][0]["identity"], result["input_failure_hresult"][1]["identity"])

    def test_v7_phase_owner_and_native_stack_identity_cannot_be_rebound(self):
        for marker in ("DAYDIAG_NEXT_CALL", "DAYDIAG_NEXT_RETURN", "DAYDIAG_BANNER_ENTRY", "DAYDIAG_BANNER_EXIT",
                       "DAYDIAG_RELEASE_WAIT_ENTRY", "DAYDIAG_RELEASE_RETURN"):
            for mutation in ("tid", "eip", "esp"):
                data = self.modern_evidence(version=7)
                row = next(i for i, value in enumerate(data["lines"]) if value.startswith(marker + " "))
                old = data["lines"][row]
                if mutation == "tid":
                    data["lines"][row] = old.replace("tid=44", "tid=88")
                elif mutation == "eip":
                    fields = tool.fields(old.partition(" ")[2])
                    data["lines"][row] = old.replace("eip=" + fields["eip"], "eip=00400000")
                else:
                    # All boundary stacks must at least be native aligned; exact
                    # saved and release return stacks have additional checks.
                    fields = tool.fields(old.partition(" ")[2])
                    data["lines"][row] = old.replace(" esp=" + fields["esp"], " esp=00000001")
                self.assertFalse(self.grade(data)["passed"], (marker, mutation))

    def test_v7_keyboard_then_mouse_are_distinct_native_stdcall_pairs(self):
        data = self.modern_evidence(version=7)
        call = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_GETDEVICESTATE_CALL"))
        keyboard = [
            "DAYDIAG_GETDEVICESTATE_CALL device=keyboard target=70000456 bytes=256 tid=44 eip=0047bff9 esp=000eda0c",
            "DAYDIAG_GETDEVICESTATE_RETURN device=keyboard hresult=8007000c lbtn=00 rbtn=00 tid=44 eip=0047bffc esp=000eda18",
        ]
        data["lines"][call:call] = keyboard
        result = self.grade(data)
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual([row["device"] for row in result["markers"]["input_returns"][:2]], ["keyboard", "mouse"])
        self.assertEqual(len(result["markers"]["input_failure_hresult"]), 8)
        for mutation in ("mouse_site", "wrong_bytes", "reverse_order"):
            changed = copy.deepcopy(data)
            if mutation == "mouse_site":
                changed["lines"][call] = keyboard[0].replace("0047bff9", "0047c029")
            elif mutation == "wrong_bytes":
                changed["lines"][call] = keyboard[0].replace("bytes=256", "bytes=16")
            else:
                changed["lines"][call:call + 4] = changed["lines"][call + 2:call + 4] + keyboard
            self.assertFalse(self.grade(changed)["passed"], mutation)

    def test_v7_foreign_input_cannot_supply_owner_banner_wait_observations(self):
        data = self.modern_evidence(version=7)
        stop = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_FORCED_BANNER_ACK"))
        rows = data["lines"][:stop] + ["DAYDIAG_OBSERVED_BANNER_INPUT_WAIT acknowledgment_not_attempted=1"]
        owner = tool.analyze_markers("\n".join(rows))
        self.assertEqual(owner["observed_classification"], "bounded_banner_input_wait")
        rows = [row.replace("tid=44", "tid=88") if row.startswith(("DAYDIAG_INPUT_POLL_ENTRY", "DAYDIAG_GETDEVICESTATE_"))
                else row for row in rows]
        foreign = tool.analyze_markers("\n".join(rows))
        self.assertEqual(foreign["errors"], [])
        self.assertEqual(foreign["observed_classification"], "banner_wait_input_calls_unverified")
        self.assertEqual(len(foreign["input_returns"]), 8)
        self.assertFalse(any(row["owner_thread"] for row in foreign["input_returns"]))
        self.assertEqual(foreign["bounded_wait"]["input_returns"], [])

    def test_v7_phase_cap_stays_global_and_release_closure_stays_strict(self):
        data = self.modern_evidence(version=7)
        rows = data["lines"]
        begin = next(i for i, row in enumerate(rows) if row.startswith("DAYDIAG_INPUT_POLL_ENTRY"))
        poll = rows[begin:begin + 3]
        # The producer counts polls globally, even when two threads alternate.
        complete = rows[:begin] + [row.replace("tid=44", f"tid={0x44 if index % 2 else 0x88:x}")
                                  for index in range(16) for row in poll] + ["DAYDIAG_INPUT_TRACE_LIMIT polls=16"]
        self.assertEqual(tool.analyze_markers("\n".join(complete))["errors"], [])
        self.assertTrue(tool.analyze_markers("\n".join(complete + poll))["errors"])
        end = next(i for i, row in enumerate(rows) if row.startswith("DAYDIAG_INPUT_TRACE_END"))
        for suffix in (poll, ["DAYDIAG_INPUT_TRACE_LIMIT polls=16"], [rows[end]]):
            changed = copy.deepcopy(data)
            changed["lines"][end + 1:end + 1] = suffix
            self.assertFalse(self.grade(changed)["passed"], suffix)
        for missing in (end, end - 1):
            changed = copy.deepcopy(data)
            changed["lines"].pop(missing)
            self.assertFalse(self.grade(changed)["passed"])

    def test_actual_v6_duplicate_return_stays_failed_when_available(self):
        path = (Path(r"C:\ClashCaptures\hd-completion\continuity-daydiag-combined-v6-control")
                / "cdb-surface-dump-20260905-135344" / "cdb-surface-dump.log")
        if not path.is_file():
            self.skipTest("archived local v6 capture is not available in this clone")
        result = tool.analyze_markers(path.read_text(encoding="utf-8-sig", errors="replace"))
        self.assertEqual(result["diagnostic_version"], 6)
        self.assertEqual(result["observed_classification"], "full_day_returned_with_controlled_input_queries")
        self.assertEqual(result["errors"], ["line 265: DAYDIAG_GETDEVICESTATE_RETURN: input return lacks matching call"])
        self.assertEqual(len(result["input_return_observations"]), 21)
        self.assertEqual(len(result["input_failure_hresult"]), 21)

    def test_only_banner_ack_consumes_mode_for_all_override_branches(self):
        for version in (5, 6, 7):
            for mode, ack, release in ((0, False, False), (1, False, False),
                                       (1, True, False), (1, False, True), (1, True, True)):
                data = self.modern_evidence(mode=mode, banner_ack=ack, controlled_release=release, version=version)
                result = self.grade(data)
                self.assertTrue(result["passed"], (version, mode, ack, release, result["failures"]))
                self.assertEqual(result["forced_banner_ack_count"], int(ack))
                self.assertEqual(result["forced_release_counts"], {"left": int(release), "right": int(release)})
                self.assertFalse(result["manual_input_proof"])
                self.assertFalse(result["promotion_evidence"])
                expected_mode = 2 if ack else mode
                for marker in ("DAYDIAG_BANNER_EXIT", "DAYDIAG_FULL_DAY_RETURNED"):
                    for wrong_mode in {0, 1, 2, 3} - {expected_mode}:
                        changed = copy.deepcopy(data)
                        changed["lines"] = [row.replace(f"mode={expected_mode}", f"mode={wrong_mode}")
                                            if row.startswith(marker) else row for row in changed["lines"]]
                        self.assertFalse(self.grade(changed)["passed"], (version, mode, ack, release, marker, wrong_mode))

    def test_later_banner_keeps_mode_one_after_release_only_override(self):
        data = self.modern_evidence(banner_ack=False)
        position = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_NEXT_RETURN advance=2"))
        rows = ["DAYDIAG_BANNER_ENTRY advance=2 player=2 day=20 ret=0040ac1f",
                "DAYDIAG_BANNER_TEST poll=1 observed_eax=1 button_flags=1 lbtn=80 rbtn=00 player=2 day=20",
                "DAYDIAG_BANNER_EXIT player=2 day=20 mode=1",
                "DAYDIAG_RELEASE_WAIT_ENTRY ret=0040aa06 object=00544cd8 player=2 day=20 esp=000edb60",
                "DAYDIAG_RELEASE_LEFT_TEST poll=1 observed_eax=0 button_flags=0 lbtn=00 rbtn=00 player=2 day=20",
                "DAYDIAG_RELEASE_RIGHT_TEST poll=1 observed_eax=0 button_flags=0 lbtn=00 rbtn=00 player=2 day=20",
                "DAYDIAG_RELEASE_RETURN player=2 day=20 esp=000edb64"]
        data["lines"][position:position] = rows
        self.assertTrue(self.grade(data)["passed"])
        data["lines"] = [row.replace("player=2 day=20 mode=1", "player=2 day=20 mode=2") for row in data["lines"]]
        self.assertFalse(self.grade(data)["passed"])

    def test_v6_release_trace_end_is_required_and_closes_only_that_phase(self):
        data = self.modern_evidence(banner_ack=False, version=6)
        result = self.grade(data)
        self.assertTrue(result["passed"], result["failures"])
        self.assertTrue(result["markers"]["input_trace_phases"][1]["ended"])
        end = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_INPUT_TRACE_END"))
        for mutation in ("missing", "duplicate", "premature", "wrong_phase", "undeclared_v5", "truncated"):
            changed = copy.deepcopy(data)
            rows = changed["lines"]
            if mutation == "missing":
                rows.pop(end)
            elif mutation == "duplicate":
                rows.insert(end + 1, rows[end])
            elif mutation == "premature":
                rows[end - 1], rows[end] = rows[end], rows[end - 1]
            elif mutation == "wrong_phase":
                rows[end] = "DAYDIAG_INPUT_TRACE_END phase=native_call"
            elif mutation == "undeclared_v5":
                rows[:] = [row.replace("diagnostic v6", "diagnostic v5") for row in rows]
            else:
                rows[:] = rows[:end]
            self.assertFalse(self.grade(changed)["passed"], mutation)
        for marker in ("DAYDIAG_INPUT_POLL_ENTRY ret=00460a61 object=00545198 mouse_enabled=1 keyboard_enabled=1 joystick_enabled=0",
                       "DAYDIAG_GETDEVICESTATE_CALL device=mouse target=70000123 bytes=16",
                       "DAYDIAG_GETDEVICESTATE_RETURN device=mouse hresult=8007000c",
                       "DAYDIAG_INPUT_TRACE_LIMIT polls=16"):
            changed = copy.deepcopy(data)
            changed["lines"].insert(end + 1, marker)
            result = self.grade(changed)
            self.assertFalse(result["passed"], marker)
            self.assertTrue(any("after declared trace end" in reason for reason in result["failures"]), result)
            if "GETDEVICESTATE_RETURN" in marker:
                self.assertEqual(len(result["markers"]["input_failure_hresult"]), 8)
        # A new native call declares a fresh phase, which can trace input again.
        next_return = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_NEXT_RETURN advance=2"))
        data["lines"][next_return:next_return] = [
            "DAYDIAG_INPUT_POLL_ENTRY ret=00460a61 object=00545198 mouse_enabled=1 keyboard_enabled=1 joystick_enabled=0",
            "DAYDIAG_GETDEVICESTATE_CALL device=mouse target=70000123 bytes=16",
            "DAYDIAG_GETDEVICESTATE_RETURN device=mouse hresult=8007000c"]
        self.assertTrue(self.grade(data)["passed"])

    def test_v5_overlapping_input_failure_survives_correct_release_only_mode(self):
        data = self.modern_evidence(banner_ack=False)
        position = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_NEXT_RETURN"))
        poll = "DAYDIAG_INPUT_POLL_ENTRY ret=00460a61 object=00545198 mouse_enabled=1 keyboard_enabled=1 joystick_enabled=0"
        call = "DAYDIAG_GETDEVICESTATE_CALL device=mouse target=70000123 bytes=16"
        data["lines"][position:position] = [poll, poll, call, call,
            "DAYDIAG_GETDEVICESTATE_RETURN device=mouse hresult=8007000c"]
        result = self.grade(data)
        self.assertFalse(result["passed"])
        self.assertEqual(result["observed_classification"], "full_day_returned_with_controlled_input_queries")
        self.assertEqual(len(result["failures"]), 1, result["failures"])
        self.assertIn("overlapping input call", result["failures"][0])

    def test_controlled_release_is_disclosed_and_never_manual_or_promotion(self):
        for right_tests in (1, 8):
            result = self.grade(self.modern_evidence(right_tests=right_tests))
            self.assertTrue(result["passed"], result["failures"])
            self.assertEqual(result["observed_classification"], "full_day_returned_with_controlled_input_queries")
            self.assertEqual(result["forced_release_counts"], {"left": 1 if right_tests == 1 else 0, "right": 1})
            self.assertTrue(result["controlled_input_query_overrides"])
            self.assertTrue(result["native_day_increment_observed"])
            self.assertTrue(result["native_day_return_observed"])
            self.assertFalse(result["manual_input_proof"])
            self.assertFalse(result["promotion_evidence"])
            self.assertEqual(len(result["markers"]["input_failure_hresult"]), 7)

    def test_release_override_phase_counts_prior_value_and_exact_stack_fail_closed(self):
        for mutation in ("undeclared_mode", "undeclared_version", "repeat_left", "repeat_right", "missing_entry", "missing_exit",
                         "missing_left", "missing_right", "old_eax", "wrong_right_count", "wrong_left_count", "premature",
                         "wrong_mechanism", "wrong_value", "manual_claim", "wrong_return_esp", "wrong_entry_target",
                         "wrong_result_flags", "missing_release_return", "right_before_effective_left_zero"):
            data = self.modern_evidence()
            rows = data["lines"]
            if mutation.startswith("repeat_"):
                button = mutation.split("_")[1]
                i = next(i for i, row in enumerate(rows) if row.startswith("DAYDIAG_FORCED_RELEASE button=" + button))
                rows.insert(i + 1, rows[i])
            elif mutation in ("missing_entry", "missing_exit", "missing_left", "missing_right", "missing_release_return"):
                prefix = {"missing_entry": "DAYDIAG_RELEASE_WAIT_ENTRY", "missing_exit": "DAYDIAG_BANNER_EXIT",
                          "missing_left": "DAYDIAG_RELEASE_LEFT_TEST", "missing_right": "DAYDIAG_RELEASE_RIGHT_TEST",
                          "missing_release_return": "DAYDIAG_RELEASE_RETURN"}[mutation]
                rows[:] = [row for row in rows if not row.startswith(prefix)]
            elif mutation == "right_before_effective_left_zero":
                rows[:] = [row for row in rows if not row.startswith("DAYDIAG_FORCED_RELEASE button=left")]
            else:
                old, new = {
                    "undeclared_mode": ("START mode=1", "START mode=0"),
                    "undeclared_version": ("diagnostic v5", "diagnostic v4"),
                    "old_eax": ("button=left tests=8 observed_eax=1", "button=left tests=8 observed_eax=0"),
                    "wrong_right_count": ("button=right tests=1", "button=right tests=8"),
                    "wrong_left_count": ("button=left tests=8", "button=left tests=1"),
                    "premature": ("RELEASE_LEFT_TEST poll=8", "RELEASE_LEFT_TEST poll=7"),
                    "wrong_mechanism": ("mechanism=override_release_button_result", "mechanism=unknown"),
                    "wrong_value": ("override_release_button_result value=0", "override_release_button_result value=1"),
                    "manual_claim": ("override_release_button_result value=0 manual_input_proof=0", "override_release_button_result value=0 manual_input_proof=1"),
                    "wrong_return_esp": ("RELEASE_RETURN player=1 day=20 esp=000edb64", "RELEASE_RETURN player=1 day=20 esp=000edb60"),
                    "wrong_entry_target": ("ret=0040aa06 object=00544cd8", "ret=0040aa07 object=00544cd8"),
                    "wrong_result_flags": ("RELEASE_LEFT_TEST poll=8 observed_eax=1 button_flags=3", "RELEASE_LEFT_TEST poll=8 observed_eax=1 button_flags=2"),
                }[mutation]
                rows[:] = [row.replace(old, new) for row in rows]
            result = self.grade(data)
            self.assertFalse(result["passed"], (mutation, result))
            self.assertTrue(result["failures"], mutation)

    def test_native_increment_and_bounded_release_wait_are_separate_from_completion(self):
        data = self.evidence()
        end = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_NEXT_RETURN advance=5"))
        prefix = data["lines"][:end]
        banner = ["DAYDIAG_BANNER_ENTRY advance=5 player=0 day=21 ret=0040ac1f",
                  "DAYDIAG_BANNER_TEST poll=1 observed_eax=1 button_flags=3 lbtn=d0 rbtn=f0 player=0 day=21",
                  "DAYDIAG_BANNER_EXIT player=0 day=21 mode=0"]
        v3 = tool.analyze_markers("\n".join(["=== Clash95 bounded day-transition diagnostic v3 ===", *prefix, *banner]))
        self.assertEqual(v3["observed_classification"], "native_day_increment_without_complete_return")
        self.assertTrue(v3["native_day_increment_observed"])
        self.assertFalse(v3["native_day_return_observed"])
        for button_count in (1, 8):
            v4 = tool.analyze_markers("\n".join(["=== Clash95 bounded day-transition diagnostic v4 ===", *prefix, *banner,
                                               *release_lines(player=0, day=21, bounded=True, right_tests=button_count)]))
            self.assertEqual(v4["errors"], [])
            self.assertEqual(v4["observed_classification"], "bounded_release_input_wait")
            self.assertTrue(v4["native_day_increment_observed"])
            self.assertFalse(v4["native_day_return_observed"])
            self.assertIsNone(v4["full_day"])

    def test_controlled_release_limit_is_global_across_native_calls(self):
        data = self.modern_evidence()
        position = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_NEXT_RETURN advance=2"))
        repeated = ["DAYDIAG_BANNER_ENTRY advance=2 player=2 day=20 ret=0040ac1f",
                    "DAYDIAG_BANNER_TEST poll=1 observed_eax=1 button_flags=3 lbtn=80 rbtn=80 player=2 day=20",
                    "DAYDIAG_BANNER_EXIT player=2 day=20 mode=2",
                    *release_lines(player=2, controlled=True)]
        data["lines"][position:position] = repeated
        result = self.grade(data)
        self.assertFalse(result["passed"])
        self.assertEqual(result["forced_release_counts"], {"left": 1, "right": 1})
        self.assertTrue(any("repeated controlled release" in failure for failure in result["failures"]))

    def test_release_can_return_naturally_only_after_both_zero_results(self):
        data = self.modern_evidence()
        a = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_RELEASE_WAIT_ENTRY"))
        b = next(i for i, row in enumerate(data["lines"]) if row.startswith("DAYDIAG_RELEASE_RETURN"))
        data["lines"][a + 1:b] = [
            "DAYDIAG_RELEASE_LEFT_TEST poll=1 observed_eax=0 button_flags=0 lbtn=00 rbtn=00 player=1 day=20",
            "DAYDIAG_RELEASE_RIGHT_TEST poll=1 observed_eax=0 button_flags=0 lbtn=00 rbtn=00 player=1 day=20"]
        result = self.grade(data)
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["forced_release_counts"], {"left": 0, "right": 0})
        data["lines"].pop(a + 2)
        self.assertFalse(self.grade(data)["passed"])

    def test_input_trace_limit_is_sixteen_complete_polls_per_phase(self):
        rows = marker_lines()
        rows = rows[:next(i for i, row in enumerate(rows) if row.startswith("DAYDIAG_NEXT_RETURN"))]
        poll = ["DAYDIAG_INPUT_POLL_ENTRY ret=00460a61 object=00545198 mouse_enabled=1 keyboard_enabled=1 joystick_enabled=0",
                "DAYDIAG_GETDEVICESTATE_CALL device=mouse target=70000123 bytes=16",
                "DAYDIAG_GETDEVICESTATE_RETURN device=mouse hresult=8007000c"]
        complete = rows + poll * 16 + ["DAYDIAG_INPUT_TRACE_LIMIT polls=16"]
        self.assertEqual(tool.analyze_markers("\n".join(complete))["errors"], [])
        for invalid in (complete + poll, rows + poll * 15 + ["DAYDIAG_INPUT_TRACE_LIMIT polls=16"],
                        complete + ["DAYDIAG_INPUT_TRACE_LIMIT polls=16"], rows + poll * 17):
            self.assertTrue(tool.analyze_markers("\n".join(invalid))["errors"])

    def test_actual_v3_v4_logs_remain_failed_classifications_when_available(self):
        base = Path(r"C:\ClashCaptures\hd-completion")
        for version, run, expected in ((3, "20260905-121022", "native_day_increment_without_complete_return"),
                                       (4, "20260905-123426", "bounded_release_input_wait")):
            path = base / f"continuity-daydiag-combined-v{version}-observe" / f"cdb-surface-dump-{run}" / "cdb-surface-dump.log"
            if not path.is_file():
                continue
            result = tool.analyze_markers(path.read_text(encoding="utf-8-sig", errors="replace"))
            self.assertEqual(result["diagnostic_version"], version)
            self.assertEqual(result["observed_classification"], expected, result)
            self.assertEqual(result["native_day_increment"]["day"], 2)
            self.assertFalse(result["native_day_return_observed"])
            self.assertIsNone(result["full_day"])
            self.assertTrue(result["input_failure_hresult"])

    def test_actual_v5_release_only_mode_keeps_overlap_failure_when_available(self):
        path = (Path(r"C:\ClashCaptures\hd-completion\continuity-daydiag-combined-v5-control")
                / "cdb-surface-dump-20260905-130340" / "cdb-surface-dump.log")
        if not path.is_file():
            self.skipTest("user-owned historical v5 log is unavailable")
        result = tool.analyze_markers(path.read_text(encoding="utf-8-sig", errors="replace"))
        self.assertEqual(result["diagnostic_version"], 5)
        self.assertEqual(result["start"]["mode"], 1)
        self.assertEqual(result["forced_ack_count"], 0)
        self.assertEqual(result["forced_release_counts"], {"left": 1, "right": 1})
        self.assertEqual(result["observed_classification"], "full_day_returned_with_controlled_input_queries")
        self.assertEqual(result["native_day_increment"]["day"], 2)
        self.assertTrue(result["native_day_return_observed"])
        self.assertTrue(result["surface_completed"])
        self.assertEqual(result["errors"], [
            "line 309: DAYDIAG_GETDEVICESTATE_CALL: overlapping input call or input outside advance"])
        self.assertEqual(len(result["input_failure_hresult"]), 22)

    def test_failure_records_are_not_deduplicated(self):
        data = self.evidence()
        parsed = tool.analyze_markers("\n".join(data["lines"]))
        parsed["errors"] = ["same actual failure", "same actual failure"]
        from unittest import mock
        with mock.patch.object(tool, "analyze_markers", return_value=parsed):
            result = self.grade(data)
        self.assertEqual(result["failures"].count("same actual failure"), 2)
        raw_errors = tool.analyze_markers("\n".join([
            "DAYDIAG_GETDEVICESTATE_RETURN device=mouse hresult=8007000c",
            "DAYDIAG_GETDEVICESTATE_RETURN device=mouse hresult=8007000c"]))
        self.assertEqual(len(raw_errors["errors"]), 2)
        self.assertEqual(len(raw_errors["input_failure_hresult"]), 2)
        self.assertEqual(raw_errors["input_returns"], [])

    def test_real_schema_sequence_passes_with_forcing_disclosed(self):
        for mode in (0, 1):
            result = self.grade(self.evidence(mode))
            self.assertTrue(result["passed"], result["failures"])
            self.assertEqual(result["forced_banner_ack_count"], mode)
            self.assertEqual(result["markers"]["call_count"], 5)
            self.assertFalse(result["manual_input_proof"])
            self.assertFalse(result["promotion_evidence"])

    def test_every_required_transition_marker_is_needed_despite_surface_pass(self):
        for marker in ("CONTRACT_PASS", "PLAYERS", "START", "NEXT_CALL", "NATIVE_DAY_INCREMENT",
                       "AFTER_DAY_BRANCH", "NEXT_RETURN", "FULL_DAY_RETURNED", "POST_DAY_REDRAW"):
            data = self.evidence()
            data["lines"] = [line for line in data["lines"] if not line.startswith("DAYDIAG_" + marker + " ")]
            result = self.grade(data)
            self.assertFalse(result["passed"], marker)
        for marker in ("SURFDUMP_READY ", "SURFDUMP_HOST_READY"):
            data = self.evidence()
            data["lines"] = [line for line in data["lines"] if not line.startswith(marker)]
            self.assertFalse(self.grade(data)["passed"], marker)

    def test_reordered_increment_join_and_premature_surface_fail(self):
        for first, second in (("DAYDIAG_NATIVE_DAY_INCREMENT", "DAYDIAG_AFTER_DAY_BRANCH advance=5"),
                              ("DAYDIAG_POST_DAY_REDRAW", "SURFDUMP_READY")):
            data = self.evidence()
            a = next(i for i, line in enumerate(data["lines"]) if line.startswith(first))
            b = next(i for i, line in enumerate(data["lines"]) if line.startswith(second))
            data["lines"][a], data["lines"][b] = data["lines"][b], data["lines"][a]
            self.assertFalse(self.grade(data)["passed"])

    def test_exact_stack_return_day_player_and_cadence_are_required(self):
        replacements = [(" esp=000edbb0", " esp=000edbac"), ("final_day=21", "final_day=22"),
                        ("advance=5 player=0 day=21", "advance=5 player=1 day=21"),
                        ("tick=228 saved_esp", "tick=227 saved_esp"),
                        ("advance=5 player=4", "advance=6 player=4")]
        for old, new in replacements:
            data = self.evidence()
            data["lines"] = [line.replace(old, new) for line in data["lines"]]
            self.assertFalse(self.grade(data)["passed"], (old, new))

    def test_forced_ack_wrong_mode_double_ack_or_missing_banner_exit_fail(self):
        for kind in ("mode", "duplicate", "exit"):
            data = self.evidence(1)
            if kind == "mode":
                data["lines"] = [line.replace("START mode=1", "START mode=0") for line in data["lines"]]
            elif kind == "duplicate":
                idx = next(i for i, line in enumerate(data["lines"]) if line.startswith("DAYDIAG_FORCED_BANNER_ACK"))
                data["lines"].insert(idx, data["lines"][idx])
            else:
                data["lines"] = [line for line in data["lines"] if not line.startswith("DAYDIAG_BANNER_EXIT")]
            self.assertFalse(self.grade(data)["passed"], kind)

    def test_bounded_wait_is_classified_but_never_passes_day_proof(self):
        data = self.evidence(wait=True)
        result = self.grade(data)
        self.assertEqual(result["observed_classification"], "bounded_banner_input_wait", result)
        self.assertFalse(result["passed"])
        data["lines"] = [line for line in data["lines"] if "GETDEVICESTATE" not in line]
        result = self.grade(data)
        self.assertEqual(result["observed_classification"], "banner_wait_input_calls_unverified")
        self.assertFalse(result["passed"])

    def test_unknown_timeout_and_actual_contract_failure_never_become_day_proof(self):
        data = self.evidence()
        data["lines"] = data["lines"][:3]
        data["summary"]["TimedOut"] = True
        self.assertEqual(self.grade(data)["observed_classification"], "unknown_timeout")
        data["lines"] += ["DAYDIAG_CONTRACT_FAIL route_entries", " ^ Syntax error in ' .echo DAYDIAG_CONTRACT_FAIL route_entries; q; '"]
        data["cleanup"] = None
        result = self.grade(data)
        self.assertEqual(result["observed_classification"], "contract_failed")
        self.assertFalse(result["passed"])
        self.assertIn("explicit cleanup observation missing/schema mismatch", result["failures"])

    def test_sha_stage_dimensions_raw_and_generated_probe_binding(self):
        cases = [("CandidateSha256", "a" * 64), ("Stage", tool.STABLE), ("Resolution", "1024x768"),
                 ("CandidatePath", r"C:\ClashTests\other.exe"), ("GeneratedProbe", r"C:\other.cdb"),
                 ("SurfaceGeometryMatched", False), ("RawBytes", 10)]
        for key, value in cases:
            data = self.evidence()
            data["summary"][key] = value
            self.assertFalse(self.grade(data)["passed"], key)
        self.assertFalse(self.grade(self.evidence(), expected_generated_probe_sha256="b" * 64)["passed"])
        self.assertFalse(self.grade(self.evidence(), raw_data=None)["passed"])
        data = self.evidence()
        data["summary"]["Surface"]["Base"] = "10002001"
        self.assertFalse(self.grade(data)["passed"])

    def test_cleanup_cannot_be_inferred_from_surface_pass_or_exit(self):
        for key, value in (("game_stopped", False), ("cdb_stopped", None), ("errors", ["stop failed"]),
                           ("game_pid", 0), ("cdb_pid", 100), ("candidate_sha256", "a" * 64),
                           ("game_pid", 102), ("surface_sha256", "a" * 64),
                           ("generated_probe_sha256", "a" * 64), ("observed_at", "2026-09-05T12:00:00")):
            data = self.evidence()
            data["cleanup"][key] = value
            self.assertFalse(self.grade(data)["passed"], key)
        data = self.evidence()
        data["cleanup"]["log_sha256"] = "a" * 64
        self.assertFalse(self.grade(data, bind_log=False)["passed"])

    def test_patch_gate_counts_actual_bytes_and_map_gate_cannot_be_bypassed(self):
        for kind in ("sha", "stage", "resolution", "count", "row", "gate"):
            data = self.evidence()
            if kind == "count":
                data["report"]["status_counts"]["unexpected"] = 1
            elif kind == "row":
                data["report"]["patches"][0]["actual"] = "02"
            elif kind == "gate":
                data["report"]["current_hd_map_gate"]["passed"] = False
            else:
                key = {"sha": "exe_sha256", "stage": "stage", "resolution": "resolution"}[kind]
                data["report"][key] = "wrong"
            self.assertFalse(self.grade(data)["passed"], kind)

    def test_runtime_failures_override_complete_markers(self):
        for marker in ("AV_SURFDUMP", "SURFDUMP_APP_REQUEST_QUIT", "SURFDUMP_INVALID", "Syntax error"):
            data = self.evidence()
            data["lines"].append(marker)
            self.assertFalse(self.grade(data)["passed"], marker)
        for key, value in (("Av", True), ("AppRequestQuit", True), ("HostDumpError", "read failed"),
                           ("ProxyPresentSetting", "1"), ("HiddenDesktop", False)):
            data = self.evidence()
            data["summary"][key] = value
            self.assertFalse(self.grade(data)["passed"], key)

    def test_cli_missing_files_emits_failed_json_without_runtime(self):
        with tempfile.TemporaryDirectory(prefix="clash-daydiag-fixture-") as temp:
            command = [sys.executable, "-B", str(Path(tool.__file__)), "--summary", str(Path(temp) / "missing.json"),
                       "--byte-report", str(Path(temp) / "missing-byte.json"), "--expected-stage", STAGE,
                       "--expected-candidate-sha256", CANDIDATE_SHA, "--expected-generated-probe-sha256", "a" * 64]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertFalse(json.loads(result.stdout)["passed"])
            self.assertEqual(list(Path(temp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()

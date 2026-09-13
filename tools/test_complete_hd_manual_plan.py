"""Offline human-plan fixtures; no runtime, input or actual approval."""
from __future__ import annotations

import copy
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import complete_hd_manual_plan as planner


class HumanPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="complete-human-plan-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capture = self.root / "captures"
        self.capture.mkdir()
        self.scope = patch.object(planner, "CAPTURE_ROOT", self.capture)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        candidate = self.root / "candidate.exe"
        metadata = self.root / "candidate.candidate.json"
        probe = self.root / "candidate.cdb"
        candidate.write_bytes(b"SYNTHETIC OFFLINE FIXTURE")
        metadata.write_text('{"fixture_only":true}\n')
        probe.write_text('$$ synthetic offline fixture\n')
        self.context = {
            "identity": {"stage": planner.evidence.STAGE, "resolution": "1920x1080",
                "candidate_sha256": planner.file_ref(candidate)["sha256"],
                "metadata_sha256": planner.file_ref(metadata)["sha256"],
                "probe_sha256": planner.file_ref(probe)["sha256"],
                "base_sha256": "a" * 64, "recipe_revision": planner.evidence.RECIPE_REVISION},
            "candidate_path": str(candidate), "metadata_path": str(metadata), "probe_path": str(probe),
            "byte_rebuild_passed": True, "source_hashes": {"fixture_only": "b" * 64},
        }
        self.metadata = metadata

    def loader(self, path):
        self.assertEqual(path, self.metadata.resolve())
        return copy.deepcopy(self.context)

    def build(self, **kwargs):
        return planner.build_plan(self.metadata, run_id="human-1080", output_root=self.capture,
                                  context_loader=self.loader, **kwargs)

    def test_exact_five_targets_geometry_and_human_only_capture(self):
        with patch.object(subprocess, "run", side_effect=AssertionError("planner must not execute")), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("planner must not launch")):
            plan = self.build()
            planner.validate_plan(plan, self.metadata, context_loader=self.loader)
        self.assertEqual([row["id"] for row in plan["targets"]], list(planner.evidence.MANUAL_IDS))
        self.assertEqual(plan["targets"][0]["geometry"]["display_canvas_inclusive"], [640, 300, 1279, 779])
        panel = plan["targets"][2]
        self.assertEqual(panel["geometry"]["action_cells_inclusive"][0], [1696, 1000, 1759, 1031])
        self.assertEqual(panel["geometry"]["first_command_native_hit_bounds_exclusive"], [1696, 1000, 1759, 1031])
        self.assertEqual(panel["native_observer"]["descriptor"], "0x00511d40")
        self.assertEqual(panel["native_observer"]["callback"], "0x00409d80")
        self.assertFalse(plan["runtime_ready"])
        self.assertFalse(plan["executed"])
        self.assertFalse(plan["manual_input_accepted"])
        self.assertFalse(plan["promotion_ready"])
        self.assertFalse(plan["input_policy"]["watching_injected_input_is_manual_proof"])
        self.assertFalse((self.capture / "human-1080").exists())
        for row in plan["targets"]:
            self.assertTrue(row["blocking_gaps"])
            template = row["capture_template"]
            args = template["arguments"]
            self.assertEqual(args[args.index("-InputMode") + 1], "manual")
            self.assertEqual(args[args.index("-ObserveProcessId") + 1], {"runtime_value": "owned_candidate_pid", "minimum": 1})
            self.assertNotIn("-MoveWindowX", args)
            self.assertNotIn("-PulseRouteSteps", args)
            self.assertNotIn("-FollowupPoints", args)
            self.assertFalse(template["injects_input"])
            self.assertFalse(row["evidence_accepted"])

    def test_unknown_world_and_castle_targets_stay_unknown(self):
        rows = self.build()["targets"]
        self.assertIsNone(rows[1]["geometry"]["minimap"]["backing_size"])
        self.assertIsNone(rows[1]["geometry"]["minimap"]["clickable_rectangle"])
        for row in (rows[0], rows[3], rows[4]):
            self.assertIsNone(row["geometry"]["clickable_rectangles"])
            self.assertFalse(row["native_observer"]["implemented"])
            self.assertIsNone(row["native_observer"]["callback"])

    def test_geometry_at_all_regression_resolutions(self):
        for resolution, canvas, action in (
            ("800x600", [80, 60, 719, 539], [576, 520, 639, 551]),
            ("1024x768", [192, 144, 831, 623], [800, 688, 863, 719]),
            ("802x602", [81, 61, 720, 540], [578, 522, 641, 553]),
        ):
            self.context["identity"]["resolution"] = resolution
            plan = self.build()
            self.assertEqual(plan["targets"][0]["geometry"]["display_canvas_inclusive"], canvas)
            self.assertEqual(plan["targets"][2]["geometry"]["action_cells_inclusive"][0], action)

    def test_mixed_candidate_stage_recipe_probe_and_manifest_fail(self):
        for key in ("stage", "recipe_revision", "candidate_sha256", "metadata_sha256", "probe_sha256"):
            original = self.context["identity"][key]
            self.context["identity"][key] = "changed"
            with self.assertRaises(ValueError):
                self.build()
            self.context["identity"][key] = original
        self.context["byte_rebuild_passed"] = False
        with self.assertRaises(ValueError):
            self.build()

    def test_tampered_geometry_callbacks_or_input_claims_fail_validation(self):
        changes = [
            lambda p: p["targets"][2]["geometry"]["action_cells_inclusive"][0].__setitem__(0, 608),
            lambda p: p["targets"][3]["geometry"].__setitem__("clickable_rectangles", [[0, 0, 100, 100]]),
            lambda p: p["targets"][3]["native_observer"].__setitem__("callback", "0x0044fe70"),
            lambda p: p["input_policy"].__setitem__("method", "win32_sendinput_relative"),
            lambda p: p.__setitem__("manual_input_accepted", True),
            lambda p: p["targets"].pop(),
        ]
        for change in changes:
            plan = self.build()
            change(plan)
            with self.assertRaises(ValueError):
                planner.validate_plan(plan, self.metadata, context_loader=self.loader)

    def test_paths_and_previous_artifacts_fail_closed(self):
        for name in ("..", "../escape", "with spaces"):
            with self.assertRaises(ValueError):
                planner.build_plan(self.metadata, run_id=name, output_root=self.capture, context_loader=self.loader)
        with self.assertRaises(ValueError):
            planner.build_plan(self.metadata, run_id="external", output_root=self.root, context_loader=self.loader)
        plan = self.build()
        output = self.capture / "plan.json"
        planner.write_plan(output, plan)
        before = output.read_bytes()
        with self.assertRaises(FileExistsError):
            planner.write_plan(output, plan)
        self.assertEqual(before, output.read_bytes())
        with self.assertRaises(ValueError):
            planner.write_plan(self.root / "outside.json", plan)
        (self.capture / "human-1080").mkdir()
        with self.assertRaises(ValueError):
            self.build()

    def test_generated_plan_does_not_satisfy_runtime_readiness(self):
        args = ["complete_hd_manual_plan.py", "--candidate-manifest", str(self.metadata),
                "--run-id", "human-1080", "--output-root", str(self.capture), "--require-runtime-ready"]
        with patch.object(sys, "argv", args), patch.object(planner, "build_plan", return_value=self.build()), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(planner.main(), 2)


if __name__ == "__main__":
    unittest.main()

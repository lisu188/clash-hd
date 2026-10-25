"""Private issuer replay checks; genuine-original construction is explicit opt-in."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import importlib
import inspect
import subprocess
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import hd_multires_candidate as candidate
from src.patcher import hd_multires_issuer as issuer

ORIGINAL = None


def poison_public_aliases():
    stack = ExitStack()
    rejected = AssertionError("a public mutable implementation was called")
    for name in ("_builder", "_source", "_source_hashes", "_build_candidate", "sha256"):
        stack.enter_context(patch.object(candidate, name, side_effect=rejected))
    stack.enter_context(patch.object(candidate, "BUILDERS", {"framed": "untrusted.module"}))
    stack.enter_context(patch.object(candidate.bounded, "integrate", side_effect=rejected))
    stack.enter_context(patch.object(candidate.classic_bounded, "integrate", side_effect=rejected))
    stack.enter_context(patch.object(candidate.pe, "inspect_pe", side_effect=rejected))
    for name in ("classic_all_presets_candidate", "framed_all_presets_candidate",
                 "complete_hd_all_presets_candidate", "modal_widgets_all_presets_candidate"):
        module = importlib.import_module("src.patcher." + name)
        stack.enter_context(patch.object(module, "build_candidate", side_effect=rejected))
        stack.enter_context(patch.object(module, "_sources", side_effect=rejected))
    stack.enter_context(patch.object(issuer, "FROZEN_SOURCE_PINS", {}))
    stack.enter_context(patch.object(issuer, "_snapshot", side_effect=rejected))
    stack.enter_context(patch.object(issuer, "_private_modules", side_effect=rejected))
    return stack


class IssuerSourceTests(unittest.TestCase):
    def test_public_issuer_alias_present_before_first_candidate_import_is_ignored(self):
        code = """
import sys, types
sys.path[:0] = [sys.argv[1], sys.argv[1] + '/tools']
fake = types.ModuleType('src.patcher.hd_multires_issuer')
def reject(): raise AssertionError('preexisting public issuer alias called')
fake.create_issuer = reject
sys.modules[fake.__name__] = fake
from src.patcher import hd_multires_candidate as candidate
for profile in candidate.PROFILES:
    assert candidate.source_hashes(profile)
print('private source factory independent of preexisting alias')
"""
        result = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT)],
                                capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("independent of preexisting alias", result.stdout)

    def test_public_signatures_offer_no_builder_source_or_verifier_override(self):
        self.assertEqual(tuple(inspect.signature(candidate.build_candidate).parameters),
                         ("original", "resolution", "profile"))
        self.assertEqual(tuple(inspect.signature(candidate.source_hashes).parameters), ("profile",))

    def test_all_profile_closures_pin_the_executed_private_source_context(self):
        for profile in candidate.PROFILES:
            with self.subTest(profile=profile):
                sources = candidate.source_hashes(profile)
                self.assertTrue(set(issuer.MODULE_ORDER) | {issuer.SOURCE} <= set(sources))
                self.assertTrue(all(not name.startswith("_clash95") for name in sources))
                self.assertEqual(sources, {name: issuer._sha((ROOT / name).read_bytes())
                                          for name in sources})

    def test_retained_entrypoints_ignore_public_alias_maps_helpers_and_factory_changes(self):
        baseline = {profile: candidate.source_hashes(profile) for profile in candidate.PROFILES}
        with poison_public_aliases():
            for profile, expected in baseline.items():
                with self.subTest(profile=profile):
                    self.assertEqual(candidate.source_hashes(profile), expected)
            with self.assertRaisesRegex(ValueError, "original executable"):
                candidate.build_candidate(b"not a game executable", "1920x1080", profile="framed")

    def test_frozen_source_tampering_is_rejected_before_execution(self):
        read = Path.read_bytes
        target = ROOT / "src/patcher/framed_camera.py"
        with patch.object(Path, "read_bytes", lambda path: read(path) + (b"\n# drift\n" if path == target else b"")):
            with self.assertRaisesRegex(ValueError, "frozen issuer source pin differs"):
                candidate.source_hashes("framed")

    def test_source_change_after_snapshot_cannot_return_a_successful_result(self):
        read = Path.read_bytes
        target = ROOT / issuer.SOURCE
        reads = 0

        def change(path):
            nonlocal reads
            raw = read(path)
            if path == target:
                reads += 1
                if reads > 1:
                    return raw + b"\n# changed during reconstruction\n"
            return raw

        with patch.object(Path, "read_bytes", change):
            with self.assertRaisesRegex(ValueError, "source changed during reconstruction"):
                candidate.source_hashes("framed")
        self.assertGreaterEqual(reads, 2)

    def test_private_namespace_is_retired_after_success_and_rejection(self):
        before = {name for name in sys.modules if name.startswith("_clash95_hd_issuer_")}
        candidate.source_hashes("modalwidgets")
        with self.assertRaises(ValueError):
            candidate.build_candidate(b"fake", "1920x1080", profile="framed")
        self.assertEqual({name for name in sys.modules if name.startswith("_clash95_hd_issuer_")}, before)


class OriginalIssuerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if ORIGINAL is None:
            raise unittest.SkipTest("genuine-original construction requires --original-backed")
        cls.original = ORIGINAL.read_bytes()
        if issuer._sha(cls.original) != candidate.ORIGINAL_SHA256:
            raise ValueError("the opt-in file is not the exact supported original")

    def test_original_bound_bytes_and_probe_ignore_poisoned_public_implementations(self):
        # Two structurally distinct parents exercise private viewport/class
        # identity and the complete owned-modal reconstruction, without a game.
        for profile in ("classic", "framed", "modalwidgets"):
            with self.subTest(profile=profile):
                baseline = candidate.build_candidate(self.original, "1920x1080", profile=profile)
                with poison_public_aliases():
                    actual = candidate.build_candidate(self.original, "1920x1080", profile=profile)
                self.assertEqual(actual[0], baseline[0])
                self.assertEqual(actual[2], baseline[2])
                self.assertEqual(actual[1]["source_hashes"], baseline[1]["source_hashes"])
                self.assertEqual(actual[1]["candidate_sha256"], baseline[1]["candidate_sha256"])
                self.assertFalse(actual[1]["runtime_executed"])
                self.assertFalse(actual[1]["promotion_ready"])
        self.assertEqual(ORIGINAL.read_bytes(), self.original)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", type=Path)
    args, remaining = parser.parse_known_args()
    ORIGINAL = args.original_backed
    unittest.main(argv=[sys.argv[0], *remaining])

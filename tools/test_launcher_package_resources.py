"""Portable standalone source-integrity checks; no compiler or game starts."""
from __future__ import annotations

import importlib
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/launcher"))
import package_resources as resources
import bootstrap


class BundleResourcesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="clash-hd-package-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        for name in resources.RESOURCE_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"VALUE = 123\n" if name.endswith(".py") else b"{}\n")
        self.raw = resources.inventory_bytes(self.root)
        self.digest = resources.sha256(self.raw)
        (self.root / resources.INVENTORY_NAME).write_bytes(self.raw)

    def test_complete_raw_resources_keep_exact_paths_bytes_and_source_identity(self):
        verified = resources.verify_resources(self.root, self.digest)
        self.assertEqual(set(verified), set(resources.RESOURCE_FILES))
        self.assertEqual((self.root / "src/patcher/framed_minimap.py").read_bytes(), b"VALUE = 123\n")
        with patch.object(sys, "meta_path", list(sys.meta_path)), patch.dict(sys.modules):
            for name in ("src", "src.patcher", "src.patcher.framed_minimap"):
                sys.modules.pop(name, None)
            resources.install_source_importer(self.root, verified)
            module = importlib.import_module("src.patcher.framed_minimap")
            self.assertEqual(module.VALUE, 123)
            self.assertEqual(Path(module.__file__), self.root / "src/patcher/framed_minimap.py")
            self.assertFalse((self.root / "src/patcher/__pycache__").exists())

    def test_mutated_missing_and_rehashed_inventory_resources_fail(self):
        target = self.root / "src/patcher/framed_minimap.py"
        target.write_bytes(b"VALUE = 999\n")
        with self.assertRaisesRegex(ValueError, "preflight failed"):
            resources.verify_resources(self.root, self.digest)
        # Updating both source and the external inventory cannot replace the
        # inventory identity embedded in the compiled launcher.
        (self.root / resources.INVENTORY_NAME).write_bytes(resources.inventory_bytes(self.root))
        with self.assertRaisesRegex(ValueError, "inventory differs"):
            resources.verify_resources(self.root, self.digest)
        (self.root / resources.INVENTORY_NAME).write_bytes(self.raw)
        target.unlink()
        with self.assertRaises(OSError):
            resources.verify_resources(self.root, self.digest)

    def test_inventory_cannot_expand_shrink_or_duplicate_the_fixed_allowlist(self):
        for operation in ("add", "remove", "duplicate"):
            modified = json.loads(self.raw)
            if operation == "add":
                modified["files"]["clash95.exe"] = "0" * 64
            elif operation == "remove":
                modified["files"].pop("src/display_plan.py")
            if operation == "duplicate":
                raw = b'{"schema":"a","schema":"b","files":{}}'
            else:
                raw = json.dumps(modified).encode()
            (self.root / resources.INVENTORY_NAME).write_bytes(raw)
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                resources.verify_resources(self.root, resources.sha256(raw))

    def test_unlisted_project_source_and_source_changed_after_preflight_cannot_import(self):
        verified = resources.verify_resources(self.root, self.digest)
        extra = self.root / "src/patcher/unlisted.py"
        extra.write_bytes(b"raise AssertionError('must not execute')\n")
        (self.root / "src/patcher/framed_minimap.py").write_bytes(b"VALUE = 999\n")
        with patch.object(sys, "meta_path", list(sys.meta_path)), patch.dict(sys.modules):
            for name in ("src", "src.patcher", "src.patcher.framed_minimap"):
                sys.modules.pop(name, None)
            resources.install_source_importer(self.root, verified)
            with self.assertRaisesRegex(ModuleNotFoundError, "outside.*allowlist"):
                importlib.import_module("src.patcher.unlisted")
            with self.assertRaisesRegex(ImportError, "changed before import"):
                importlib.import_module("src.patcher.framed_minimap")

    def test_frozen_preflight_requires_compiled_inventory_identity(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", str(self.root), create=True):
            with patch.dict(sys.modules, {"launcher_bundle_identity": None}):
                self.assertFalse(bootstrap.bundled_sources_verified())
                with self.assertRaises(ImportError):
                    bootstrap.ensure_repo_paths()

    def test_packaging_inventory_contains_only_public_source_and_two_data_files(self):
        self.assertEqual(len(resources.RESOURCE_FILES), len(set(resources.RESOURCE_FILES)))
        self.assertTrue(all(name.endswith(".py") for name in resources.SOURCE_FILES))
        self.assertEqual(resources.DATA_FILES, ("src/launcher/resolutions.json", "dxcfg_windowed.ini"))
        self.assertTrue(all(not name.startswith(("captures/", "reports/", "tests/", ".git/"))
                            for name in resources.RESOURCE_FILES))
        for unsafe in ("../source.py", "/source.py", "src//source.py", "src/./source.py"):
            with self.subTest(path=unsafe), self.assertRaises(ValueError):
                resources._plain_file(self.root, unsafe)


class ActualSourceClosureTests(unittest.TestCase):
    def test_all_four_constructor_source_closures_fit_the_fixed_package_allowlist(self):
        sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
        from src.patcher import hd_multires_candidate
        for profile in hd_multires_candidate.PROFILES:
            with self.subTest(profile=profile):
                hashes = hd_multires_candidate.source_hashes(profile)
                self.assertTrue(hashes)
                self.assertLessEqual(set(hashes), set(resources.SOURCE_FILES))
                for path, digest in hashes.items():
                    self.assertEqual(resources.sha256((ROOT / path).read_bytes()), digest)


class PackageSelftestTests(unittest.TestCase):
    def test_actual_twelve_plans_need_no_game_wrapper_gui_or_child_process(self):
        import run
        import core
        with tempfile.TemporaryDirectory(prefix="clash-hd-selftest-") as directory:
            report = Path(directory) / "selftest.json"
            with patch.object(core, "launch_game", side_effect=AssertionError("game launch forbidden")), \
                    patch.object(subprocess, "Popen", side_effect=AssertionError("child process forbidden")):
                self.assertEqual(run.main(["--package-selftest", str(report)]), 0)
            recorded = json.loads(report.read_text())
            self.assertTrue(recorded["passed"])
            self.assertEqual(len(recorded["cells"]), 12)
            self.assertEqual(len({row["cell_id"] for row in recorded["cells"]}), 12)
            self.assertFalse(recorded["standalone_executable"])
            self.assertFalse(recorded["game_runtime_executed"])
            self.assertFalse(recorded["input_executed"])
            self.assertFalse(recorded["runtime_acceptance"])
            self.assertEqual(list(Path(directory).iterdir()), [report])

    def test_selftest_cannot_be_combined_with_runtime_modes(self):
        import run
        for args in (("--launch", "--yes-launch"), ("--prepare",), ("--gui-selftest",), ("--dry-run",)):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                run.parse_args(["--package-selftest", "unused.json", *args])
            self.assertEqual(error.exception.code, 2)

    def test_selftest_preserves_existing_reports(self):
        import run
        with tempfile.TemporaryDirectory(prefix="clash-hd-selftest-") as directory:
            report = Path(directory) / "selftest.json"
            report.write_bytes(b"preserved previous result\n")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(run.main(["--package-selftest", str(report)]), 1)
            self.assertEqual(report.read_bytes(), b"preserved previous result\n")


if __name__ == "__main__":
    unittest.main()

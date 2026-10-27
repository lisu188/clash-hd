"""Per-profile settings migration and hidden launcher widget roundtrips.

No game, capture, foreground input or user settings are accessed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/launcher"))
import settings
import run


class ProfileSettingsTests(unittest.TestCase):
    def test_legacy_settings_keep_classic_and_fresh_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            fresh = settings.load_settings(path)
            self.assertEqual(fresh["last_profile"], "classic")
            self.assertEqual(settings.resolution_for_profile(fresh, "classic"), "800x600")
            path.write_text(json.dumps({"schema": 1, "last_resolution": "1024x768"}))
            old = settings.load_settings(path)
            self.assertEqual(old["last_profile"], "classic")
            self.assertEqual(settings.resolution_for_profile(old, "classic"), "1024x768")
            self.assertEqual(settings.resolution_for_profile(old, "modalwidgets"), "800x600")

    def test_all_four_selections_roundtrip_independently_without_default_aliasing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            data = settings.defaults()
            selected = dict(zip(settings.PROFILES, ("1024x768", "1920x1080", "2560x1440", "3840x2160")))
            for profile, resolution in selected.items():
                settings.remember_selection(data, profile, resolution)
                settings.save_settings(data, path)
                data = settings.load_settings(path)
                self.assertEqual(data["last_profile"], profile)
            for profile, resolution in selected.items():
                self.assertEqual(settings.resolution_for_profile(data, profile), resolution)
            self.assertEqual(data["last_resolution"], "1024x768")
            self.assertEqual(settings.defaults()["profile_resolutions"], dict.fromkeys(settings.PROFILES, "800x600"))

    def test_malformed_profile_map_and_unknown_profile_cannot_choose_a_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"schema": 1, "last_profile": "other",
                "profile_resolutions": {"framed": False, "modalwidgets": {}, "completehd": "", "other": "3840x2160"}}))
            data = settings.load_settings(path)
            self.assertEqual(data, settings.defaults())
            path.write_text(json.dumps({"schema": 1, "profile_resolutions": ["3840x2160"]}))
            self.assertEqual(settings.load_settings(path), settings.defaults())
            with self.assertRaises(ValueError):
                settings.remember_selection(data, "other", "1920x1080")

    def test_explicit_cli_profile_overrides_saved_gui_choice_and_headless_default_stays_classic(self):
        self.assertEqual(run.parse_args([]).profile, "classic")
        self.assertFalse(run.parse_args([]).profile_explicit)
        args = run.parse_args(["--profile", "framed"])
        self.assertTrue(args.profile_explicit)
        self.assertEqual(args.profile, "framed")
        with patch.dict(os.environ, {"LOCALAPPDATA": tempfile.gettempdir()}), patch.object(
                run.settings_mod, "load_settings", return_value={**settings.defaults(), "last_profile": "modalwidgets"}), patch(
                "gui.start_gui", return_value=0) as start:
            run._main(run.parse_args([]))
            start.assert_called_once_with(initial_profile=None)
            start.reset_mock()
            run._main(args)
            start.assert_called_once_with(initial_profile="framed")


class HiddenWidgetRoundtripTests(unittest.TestCase):
    def test_switch_and_reopen_restores_each_profile_without_starting_game(self):
        import tkinter as tk
        import gui
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"LOCALAPPDATA": directory}), patch.object(
                gui.LauncherApp, "refresh_environment"), patch.object(gui.core, "launch_game") as launch:
            try:
                root = tk.Tk()
            except tk.TclError as error:
                self.skipTest("Hidden Tk widget lane unavailable: " + str(error))
            root.withdraw()
            try:
                app = gui.LauncherApp(root)
                self.assertEqual(app.profile_var.get(), "classic")
                self.assertEqual(app.resolution_var.get(), "800x600")
                selected = dict(zip(settings.PROFILES, ("1024x768", "1920x1080", "2560x1440", "3840x2160")))
                for profile, resolution in selected.items():
                    app.profile_var.set(profile)
                    app.on_profile_change()
                    app.resolution_var.set(resolution)
                app._save_settings()
                reopened = gui.LauncherApp(root)
                self.assertEqual(reopened.profile_var.get(), "modalwidgets")
                self.assertEqual(reopened.resolution_var.get(), "3840x2160")
                for profile, resolution in selected.items():
                    reopened.profile_var.set(profile)
                    reopened.on_profile_change()
                    self.assertEqual(reopened.resolution_var.get(), resolution)
                explicit = gui.LauncherApp(root, initial_profile="framed")
                self.assertEqual(explicit.profile_var.get(), "framed")
                self.assertEqual(explicit.resolution_var.get(), "1920x1080")
                launch.assert_not_called()
            finally:
                root.destroy()


if __name__ == "__main__":
    unittest.main()

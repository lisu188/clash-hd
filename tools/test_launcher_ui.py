from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import os
import sys
import tempfile
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/launcher'))
import bootstrap
bootstrap.ensure_repo_paths()
import core
import framed
import gui
import presets
import settings


class LauncherInteractionTests(unittest.TestCase):
    def setUp(self):
        self.app = object.__new__(gui.LauncherApp)
        self.app._plan_valid = True
        self.app._busy = False
        self.app.environment = SimpleNamespace(ready_to_patch=True, wrapper_dll=SimpleNamespace(passed=True),
                                               running_processes=SimpleNamespace(passed=True))
        self.app.play_button = Mock()
        self.app.prepare_button = Mock()
        self.app.status_label = Mock()
        self.app.log = Mock()
        self.app.refresh_environment = Mock()
        self.app.refresh_display_plan = Mock()
        self.app.manifest = presets.load_manifest()
        self.backend = Mock()
        self.backend.deploy_runtime_files.return_value = {'wrapper': 'copied'}
        self.app._backend = Mock(return_value=self.backend)
        self.app._selected_plan = Mock(return_value=SimpleNamespace(renderer='framed', resolution='1280x720', stage=framed.STAGE))
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.confirm = self.stack.enter_context(patch.object(gui.messagebox, 'askokcancel', return_value=True))
        self.error = self.stack.enter_context(patch.object(gui.messagebox, 'showerror'))
        self.launch = self.stack.enter_context(patch.object(core, 'launch_game'))

    def test_create_hd_exe_uses_existing_backend_without_launching(self):
        self.app.on_prepare()
        self.backend.ensure_candidate.assert_called_once_with(self.app._selected_plan.return_value, progress=self.app.log)
        self.backend.deploy_runtime_files.assert_called_once()
        self.launch.assert_not_called()
        self.assertFalse(self.app._busy)
        self.assertIn('No game was launched', self.app.status_label.configure.call_args.kwargs['text'])

    def test_cancel_experimental_preparation_does_not_build(self):
        self.confirm.return_value = False
        self.app.on_prepare()
        self.backend.ensure_candidate.assert_not_called()
        self.backend.deploy_runtime_files.assert_not_called()
        self.launch.assert_not_called()
        self.assertFalse(self.app._busy)

    def test_preparation_requires_valid_original_and_output_checks(self):
        self.app.environment.ready_to_patch = False
        self.app.on_prepare()
        self.backend.ensure_candidate.assert_not_called()
        self.error.assert_called_once()
        self.launch.assert_not_called()

    def test_preparation_refuses_running_game_or_unknown_snapshot(self):
        self.app.environment.running_processes.passed = False
        self.app.on_prepare()
        self.backend.ensure_candidate.assert_not_called()
        self.error.assert_called_once()
        self.launch.assert_not_called()

    def test_missing_wrapper_is_reported_after_preparation_without_launch(self):
        self.backend.deploy_runtime_files.return_value = {'wrapper': 'missing'}
        self.app.on_prepare()
        self.assertIn('Add a DirectDraw wrapper', self.app.status_label.configure.call_args.kwargs['text'])
        self.launch.assert_not_called()

    def test_backend_failure_is_reported_and_busy_state_is_restored(self):
        self.backend.ensure_candidate.side_effect = core.LauncherError('source mismatch')
        self.app.on_prepare()
        self.error.assert_called_once_with('Clash HD Launcher', 'source mismatch')
        self.backend.deploy_runtime_files.assert_not_called()
        self.assertFalse(self.app._busy)
        self.launch.assert_not_called()

    def test_action_states_distinguish_missing_game_missing_wrapper_and_busy(self):
        self.app._set_action_state()
        self.app.play_button.configure.assert_called_with(state='normal')
        self.app.environment.wrapper_dll.passed = False
        self.app._set_action_state()
        self.app.play_button.configure.assert_called_with(state='disabled')
        self.app.prepare_button.configure.assert_called_with(state='normal')
        self.app.environment.ready_to_patch = False
        self.app._set_action_state()
        self.app.prepare_button.configure.assert_called_with(state='disabled')
        self.app.environment.ready_to_patch = True
        self.app.environment.wrapper_dll.passed = True
        self.app._busy = True
        self.app._set_action_state()
        self.app.play_button.configure.assert_called_with(state='disabled')
        self.app.prepare_button.configure.assert_called_with(state='disabled')

    def test_reentrant_prepare_and_play_do_not_start_another_operation(self):
        self.app._busy = True
        self.app._play_sequence = Mock()
        self.app.on_prepare()
        self.app.on_play()
        self.app._play_sequence.assert_not_called()
        self.backend.ensure_candidate.assert_not_called()
        self.launch.assert_not_called()

    def test_play_button_preserves_existing_sequence(self):
        self.app._play_sequence = Mock()
        self.app.on_play()
        self.app._play_sequence.assert_called_once()
        self.assertFalse(self.app._busy)
        self.launch.assert_not_called()

    def test_apply_folders_preserves_saved_classic_resolution(self):
        self.app.settings = dict(settings.DEFAULT_SETTINGS, last_resolution='1024x768')
        self.app.game_dir_var = SimpleNamespace(get=lambda: 'C:/Games/Clash')
        self.app.candidates_dir_var = SimpleNamespace(get=lambda: 'C:/ClashTests/launcher')
        self.app.scaling_var = SimpleNamespace(get=lambda: 'integer')
        self.app._current_resolution_key = Mock(return_value='1280x720')
        with patch.object(settings, 'save_settings') as save:
            self.app.on_apply_folders()
        self.assertEqual(save.call_args.args[0]['last_resolution'], '1024x768')
        self.assertEqual(self.app.settings['clash_dir'], 'C:/Games/Clash')
        self.backend.plan_candidate.assert_called_once()
        self.launch.assert_not_called()

    def test_apply_folders_rejection_does_not_persist_or_change_settings(self):
        self.app.settings = dict(settings.DEFAULT_SETTINGS)
        before = dict(self.app.settings)
        self.app.game_dir_var = SimpleNamespace(get=lambda: 'C:/Clash')
        self.app.candidates_dir_var = SimpleNamespace(get=lambda: 'C:/Clash/candidates')
        self.app.scaling_var = SimpleNamespace(get=lambda: 'integer')
        self.app._current_resolution_key = Mock(return_value='800x600')
        self.backend.plan_candidate.side_effect = core.LauncherError('Refusing candidates root inside the game directory')
        with patch.object(settings, 'save_settings') as save:
            self.app.on_apply_folders()
        save.assert_not_called()
        self.assertEqual(self.app.settings, before)
        self.error.assert_called_once()

    def test_empty_folder_and_cancelled_browse_are_no_ops(self):
        self.app.game_dir_var = SimpleNamespace(get=lambda: '')
        self.app.candidates_dir_var = SimpleNamespace(get=lambda: 'C:/ClashTests')
        with patch.object(settings, 'save_settings') as save:
            self.app.on_apply_folders()
        save.assert_not_called()
        self.backend.plan_candidate.assert_not_called()
        variable = Mock()
        self.app.root = Mock()
        with patch.object(gui.filedialog, 'askdirectory', return_value=''):
            self.app._browse_folder(variable)
        variable.set.assert_not_called()


@unittest.skipUnless(os.environ.get('CLASH_LAUNCHER_UI_TESTS') == '1', 'opt-in isolated Tk UI lane required')
class LauncherWidgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='clash-launcher-ui-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.env_patch = patch.dict(os.environ, {'LOCALAPPDATA': str(self.directory / 'settings')})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        settings.save_settings(dict(settings.DEFAULT_SETTINGS, clash_dir=str(self.directory / 'game-not-installed'),
                                    candidates_root=str(self.directory / 'candidates')))
        self.root = None
        self.create_app()
        self.addCleanup(lambda: self.root.destroy() if self.root is not None else None)

    def create_app(self, dpi=96):
        if self.root is not None:
            self.root.destroy()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.tk.call('tk', 'scaling', dpi / 72)
        self.app = gui.LauncherApp(self.root)
        self.root.deiconify()
        self.root.update()

    def assert_visible_bounds(self, widget):
        for child in widget.winfo_children():
            if child.winfo_ismapped():
                with self.subTest(widget=str(child), kind=child.winfo_class()):
                    self.assertGreaterEqual(child.winfo_x(), 0)
                    self.assertGreaterEqual(child.winfo_y(), 0)
                    self.assertLessEqual(child.winfo_x() + child.winfo_width(), widget.winfo_width() + 1)
                    self.assertLessEqual(child.winfo_y() + child.winfo_height(), widget.winfo_height() + 1)
                    if child.winfo_class() in ('TLabel', 'TButton', 'TEntry', 'TCombobox'):
                        self.assertGreaterEqual(child.winfo_height() + 1, child.winfo_reqheight())
                self.assert_visible_bounds(child)

    def test_compact_tabbed_layout_and_primary_actions(self):
        self.assertEqual(tuple(self.app.notebook.tab(tab, 'text') for tab in self.app.notebook.tabs()), gui.TAB_NAMES)
        self.assertEqual(self.app.prepare_button.cget('text'), 'Create HD exe')
        self.assertEqual(self.app.play_button.cget('text'), 'Play')
        self.assertEqual(self.app.executable_combo.get(), 'clash95.exe')
        self.assertEqual(self.app.notebook.select(), str(self.app.tabs['Main settings']))
        self.assertLessEqual(self.root.winfo_width(), 735)
        self.assertLessEqual(self.root.winfo_height(), 655)
        self.assertEqual(self.app.resolution_buttons, [])

    def test_missing_game_disables_create_and_play_without_claiming_readiness(self):
        self.assertIn('disabled', self.app.play_button.state())
        self.assertIn('disabled', self.app.prepare_button.state())
        self.assertIn('missing or unrecognized', self.app.status_label.cget('text'))
        self.assertFalse(self.app.environment.base_exe.passed)
        self.assertFalse((self.directory / 'candidates').exists())

    def test_dropdown_profile_changes_labels_geometry_and_components(self):
        self.app.renderer_combo.current(1)
        self.app.renderer_combo.event_generate('<<ComboboxSelected>>')
        self.app.resolution_var.set('1366x768')
        self.root.update()
        self.assertEqual(self.app.profile_var.get(), 'framed')
        self.assertIn('Experimental', self.app.profile_badge.cget('text'))
        self.assertIn('1302 x 736', self.app.viewport_label.cget('text'))
        self.assertIn('21 x 12', self.app.viewport_label.cget('text'))
        self.assertIn('Clipped edge tiles', self.app.component_list.get(0, 'end'))
        self.assertEqual(settings.load_settings()['last_resolution'], '800x600')
        self.assertFalse((self.directory / 'candidates').exists())

    def test_classic_800_status_is_not_transferred_to_framed(self):
        self.assertIn('Stable', self.app.profile_badge.cget('text'))
        self.app.profile_var.set('framed')
        self.app.on_profile_change()
        self.assertIn('Experimental', self.app.profile_badge.cget('text'))
        self.assertIn('Framed + minimap', self.app.renderer_choice.get())
        self.app.profile_var.set('classic')
        self.app.on_profile_change()
        self.assertIn('Stable', self.app.profile_badge.cget('text'))
        self.assertIn('Classic adventure-map layout', self.app.component_list.get(0, 'end'))

    def test_custom_resolution_fields_validate_and_hide_again(self):
        self.app.profile_var.set('framed')
        self.app.on_profile_change()
        self.app.resolution_var.set('custom')
        self.app.custom_width_var.set('802')
        self.app.custom_height_var.set('602')
        self.root.update()
        self.assertTrue(self.app.custom_row.winfo_ismapped())
        self.assertTrue(self.app._plan_valid)
        self.assertIn('738 x 570', self.app.viewport_label.cget('text'))
        self.assert_visible_bounds(self.app.tabs['Main settings'])
        self.app.custom_width_var.set('803')
        self.assertFalse(self.app._plan_valid)
        self.assertIn('disabled', self.app.play_button.state())
        self.assertIn('even', self.app.validation_label.cget('text'))
        self.app.resolution_var.set('1280x720')
        self.root.update()
        self.assertFalse(self.app.custom_row.winfo_ismapped())
        self.assertTrue(self.app._plan_valid)

    def test_all_tabs_fit_at_default_size(self):
        for name, tab in self.app.tabs.items():
            self.app.notebook.select(tab)
            self.root.update()
            with self.subTest(tab=name):
                self.assert_visible_bounds(self.app.shell)

    def test_minimum_size_and_high_dpi_keep_controls_inside_tabs(self):
        for dpi in (96, 144, 192):
            self.create_app(dpi)
            self.app.profile_var.set('framed')
            self.app.on_profile_change()
            self.app.resolution_var.set('custom')
            self.app.custom_width_var.set('1366')
            self.app.custom_height_var.set('768')
            width, height = self.root.minsize()
            self.root.geometry(f'{width}x{height}')
            for name, tab in self.app.tabs.items():
                self.app.notebook.select(tab)
                self.root.update()
                with self.subTest(dpi=dpi, tab=name):
                    self.assert_visible_bounds(self.app.shell)

    def test_diagnostics_button_opens_details_not_a_process(self):
        buttons = []
        def collect(parent):
            for child in parent.winfo_children():
                if child.winfo_class() == 'TButton':
                    buttons.append(child)
                collect(child)
        collect(self.app.tabs['Main settings'])
        button = next(b for b in buttons if b.cget('text') == 'View diagnostics')
        with patch.object(core, 'launch_game') as launch:
            button.invoke()
        self.assertEqual(self.app.notebook.select(), str(self.app.tabs['Diagnostics']))
        launch.assert_not_called()
        self.assertEqual(len(self.app.env_labels), 4)

    def test_banner_is_original_vector_ui_and_redraw_does_not_accumulate_items(self):
        self.app._draw_banner()
        first = len(self.app.banner.find_all())
        self.app._draw_banner()
        self.assertEqual(first, len(self.app.banner.find_all()))
        titles = [self.app.banner.itemcget(item, 'text') for item in self.app.banner.find_all()
                  if self.app.banner.type(item) == 'text']
        self.assertIn('CLASH HD', titles)
        self.assertNotIn('HEROES', ' '.join(titles))
        self.assertFalse(any(self.app.banner.type(item) == 'image' for item in self.app.banner.find_all()))

    def test_frozen_launcher_exposes_only_classic_renderer(self):
        self.root.destroy()
        self.root = None
        with patch.object(sys, 'frozen', True, create=True):
            self.create_app()
        self.assertEqual(tuple(self.app.renderer_combo.cget('values')), ('Classic',))


if __name__ == '__main__':
    unittest.main()

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
from itertools import combinations
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.display_plan import (DisplayPlan, DisplayPlanError, PresentationTransform, SurfaceLayout,
                              deployment_identity, parse_dimensions, resolve_display_plan)


def framed_fixture() -> DisplayPlan:
    return DisplayPlan("framed", "1280x720", "synthetic-validation", "fixture-v1", 1280, 720,
                       "integer", True, (320, 120), (32, 16, 1247, 703), (19, 10), (19, 11), (0, 48),
                       ((0, 0, 1279, 15), (0, 704, 1279, 719), (0, 16, 31, 703), (1248, 16, 1279, 703)),
                       ((1056, 640, 1119, 671), (1120, 640, 1183, 671), (1184, 640, 1247, 671),
                        (1056, 672, 1119, 703), (1120, 672, 1183, 703), (1184, 672, 1247, 703)),
                       1248, 1, "a" * 64)


class DisplayContractTests(unittest.TestCase):
    def test_policy_accepts_even_non_tile_aligned_resolutions(self):
        for key in ("800x600", "802x602", "1280x720", "1366x768", "3440x1440", "3840x2160"):
            self.assertEqual(parse_dimensions(key), tuple(map(int, key.split("x"))))

    def test_resolution_spelling_and_types_fail_before_recipe_import(self):
        invalid = (None, True, 1280, "1280X720", "1280x720\n", " 1280x720", "01280x0720", "１２８０x７２０", "1280x720/../x")
        with patch("src.display_plan.importlib.import_module", side_effect=AssertionError("unexpected import")):
            for value in invalid:
                with self.subTest(value=value), self.assertRaises(DisplayPlanError) as error:
                    resolve_display_plan(resolution=value)
                self.assertEqual(error.exception.code, "invalid_resolution")

    def test_bounds_evenness_and_presentation_are_not_silently_coerced(self):
        for key in ("798x600", "800x598", "3842x2160", "3840x2162", "1367x768", "1366x769"):
            with self.subTest(key=key), self.assertRaises(DisplayPlanError):
                parse_dimensions(key)
        for kwargs in ({"renderer": "unknown"}, {"minimap_viewport": 1}, {"minimap_viewport": True},
                       {"scaling_mode": "aspect"}, {"scaling_mode": "integer\n"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(DisplayPlanError):
                resolve_display_plan(**kwargs)

    def test_invalid_bounds_and_tighter_policy(self):
        for bounds in (None, (), ((True, 600), (3840, 2160)), ((900, 600), (800, 600)),
                       ((800, 600.0), (3840, 2160)), ((0, 0), (800, 600))):
            with self.subTest(bounds=bounds), self.assertRaises(DisplayPlanError):
                parse_dimensions("800x600", bounds)
        self.assertEqual(parse_dimensions("1280x720", ((800, 600), (1280, 720))), (1280, 720))
        with self.assertRaises(DisplayPlanError):
            parse_dimensions("1920x1080", ((800, 600), (1280, 720)))

    def test_missing_source_has_structured_failure(self):
        with patch("src.display_plan.importlib.import_module", side_effect=ImportError("fixture source missing")):
            with self.assertRaises(DisplayPlanError) as error:
                resolve_display_plan()
        self.assertEqual(error.exception.code, "missing_recipe")

    def test_plan_is_immutable_and_json_copies_nested_values(self):
        plan = framed_fixture()
        with self.assertRaises(FrozenInstanceError):
            plan.width = 800
        report = plan.to_dict()
        report["action_cells"][0][0] = 0
        self.assertEqual(plan.action_cells[0][0], 1056)
        self.assertEqual(json.loads(json.dumps(plan.to_dict())), plan.to_dict())
        for key in ("candidate_built", "game_runtime_executed", "manual_input_proof", "promotion_ready"):
            self.assertIs(plan.to_dict()[key], False)

    def test_build_id_binds_features_recipe_original_and_source_but_not_presentation(self):
        plan, sources = framed_fixture(), {"tools/builder.py": "b" * 64, "src/geometry.py": "c" * 64}
        digest = plan.build_identity("d" * 64, sources)
        self.assertEqual(digest, plan.build_identity("d" * 64, dict(reversed(tuple(sources.items())))))
        self.assertEqual(digest, replace(plan, scaling_mode="different-presentation-fixture").build_identity("d" * 64, sources))
        for changed in (replace(plan, minimap_viewport=False), replace(plan, recipe_revision="new"),
                        replace(plan, scalar_patch_sha256="e" * 64), replace(plan, stage="other-validation")):
            self.assertNotEqual(digest, changed.build_identity("d" * 64, sources))
        self.assertNotEqual(digest, plan.build_identity("e" * 64, sources))
        self.assertNotEqual(digest, plan.build_identity("d" * 64, sources | {"src/geometry.py": "f" * 64}))

    def test_invalid_source_identity_paths_and_hashes(self):
        for sources in ({}, {"/tmp/a.py": "a" * 64}, {"C:/a.py": "a" * 64}, {"src/../a.py": "a" * 64},
                        {"src//a.py": "a" * 64}, {"src\\a.py": "a" * 64}, {"src/a.py": "A" * 64},
                        {"src/a.py": "a" * 63}, {"src/a.py": True}):
            with self.subTest(sources=sources), self.assertRaises(DisplayPlanError):
                framed_fixture().build_identity("b" * 64, sources)

    def test_deployment_id_changes_for_wrapper_and_config_without_changing_build(self):
        expected = deployment_identity("a" * 64, "b" * 64, "c" * 64)
        self.assertEqual(expected, deployment_identity("a" * 64, "b" * 64, "c" * 64))
        for values in (("d" * 64, "b" * 64, "c" * 64), ("a" * 64, "d" * 64, "c" * 64), ("a" * 64, "b" * 64, "d" * 64)):
            self.assertNotEqual(expected, deployment_identity(*values))
        with self.assertRaises(DisplayPlanError):
            deployment_identity("not-a-hash", "b" * 64, "c" * 64)


class WorldPlanTests(unittest.TestCase):
    def test_cells_partition_complete_terrain_including_partial_bottom(self):
        plan = framed_fixture().world_view(100, 100)
        cells = plan.cells()
        self.assertEqual(len(cells), 209)
        self.assertTrue(all(cell.in_world for cell in cells))
        self.assertEqual(sum((c.rect[2]-c.rect[0]+1)*(c.rect[3]-c.rect[1]+1) for c in cells), 1216*688)
        self.assertEqual(cells[-1].rect, (1184, 656, 1247, 703))
        for first, second in combinations(cells, 2):
            a, b = first.rect, second.rect
            self.assertTrue(a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

    def test_saved_camera_is_clamped_before_planning_far_edge(self):
        world = framed_fixture().world_view(100, 100, 99, -20)
        self.assertEqual(world.scroll, (81, 0))
        self.assertEqual(world.max_scroll, (81, 90))
        self.assertTrue(world.to_dict()["scroll_was_clamped"])
        far = framed_fixture().world_view(100, 100, 10000, 10000)
        self.assertEqual(far.scroll, (81, 90))
        self.assertTrue(far.native_full_loop_safe)
        self.assertEqual(sum(not cell.in_world for cell in far.cells()), 19)
        self.assertIsNone(far.tile_at(1247, 703))
        self.assertEqual(far.tile_at(1247, 655), (99, 99))

    def test_small_world_plan_does_not_authorize_unsafe_native_loop(self):
        world = framed_fixture().world_view(3, 2, 100, 100)
        self.assertEqual(world.scroll, (0, 0))
        self.assertFalse(world.native_full_loop_safe)
        self.assertEqual(sum(cell.in_world for cell in world.cells()), 6)
        self.assertFalse(world.to_dict()["bounded_renderer_installed"])
        with self.assertRaises(DisplayPlanError) as error:
            world.require_native_full_loop()
        self.assertEqual(error.exception.code, "small_world_unsupported")
        self.assertEqual(world.tile_at(32, 16), (0, 0))
        self.assertIsNone(world.tile_at(224, 16))

    def test_equal_world_is_safe_and_clipped_tail_is_noninteractive(self):
        world = framed_fixture().world_view(19, 10)
        world.require_native_full_loop()
        self.assertEqual(world.max_scroll, (0, 0))
        self.assertEqual(world.tile_at(1247, 655), (18, 9))
        self.assertIsNone(world.tile_at(1247, 656))

    def test_overlays_and_frame_do_not_become_world_clicks(self):
        display = framed_fixture()
        world = display.world_view(100, 100)
        for x, y in ((31, 16), (32, 15), (1248, 16), (32, 704), (-1, -1)):
            self.assertIsNone(world.tile_at(x, y))
        for left, top, right, bottom in display.action_cells:
            self.assertIsNone(world.tile_at(left, top, excluded=display.action_cells))
            self.assertIsNone(world.tile_at(right, bottom, excluded=display.action_cells))
        minimap = (1034, 16, 1247, 229)
        self.assertIsNone(world.tile_at(1034, 16, excluded=(minimap,)))
        self.assertIsNotNone(world.tile_at(1033, 16, excluded=(minimap,)))

    def test_world_and_input_types_fail_closed(self):
        for args in ((0, 100), (101, 100), (100, 0), (100, True), (3.0, 2), (3, 2, True), (3, 2, 0, 1.0)):
            with self.subTest(args=args), self.assertRaises(DisplayPlanError):
                framed_fixture().world_view(*args)
        world = framed_fixture().world_view(100, 100)
        with self.assertRaises(DisplayPlanError):
            world.tile_at(True, 0)
        with self.assertRaises(DisplayPlanError):
            world.tile_at(32, 16, excluded=((10, 0, 1, 5),))


class PresentationTests(unittest.TestCase):
    def test_integer_fit_adds_letterbox_without_changing_render_size(self):
        transform = PresentationTransform.integer_fit(1280, 720, 2560, 1600)
        self.assertEqual((transform.left, transform.top, transform.width, transform.height), (0, 80, 2560, 1440))
        self.assertEqual((transform.render_width, transform.render_height), (1280, 720))
        self.assertEqual(transform.render_point(0, 80), (0, 0))
        self.assertEqual(transform.render_point(2559, 1519), (1279, 719))

    def test_letterbox_clicks_are_rejected_not_clamped(self):
        transform = PresentationTransform.integer_fit(1280, 720, 2560, 1600)
        for point in ((0, 79), (0, 1520), (-1, 80), (2560, 80)):
            self.assertIsNone(transform.render_point(*point))

    def test_negative_monitor_origin_and_odd_letterbox_remainder(self):
        transform = PresentationTransform.integer_fit(1280, 720, 2563, 1603, -2563, -300)
        self.assertEqual((transform.left, transform.top), (-2562, -219))
        self.assertEqual(transform.render_point(-2562, -219), (0, 0))
        self.assertEqual(transform.render_point(-3, 1220), (1279, 719))
        self.assertIsNone(transform.render_point(-2, 1220))

    def test_observed_fractional_size_is_mapped_with_integer_arithmetic(self):
        transform = PresentationTransform(1280, 720, 10, 20, 1707, 961)
        for x in range(1707):
            self.assertEqual(transform.render_point(x + 10, 20), (x * 1280 // 1707, 0))
        self.assertEqual(transform.render_point(1716, 980), (1279, 719))

    def test_small_client_and_invalid_geometry_are_rejected(self):
        for args in ((1280, 720, 1279, 720), (1280, 720, 1280, 719), (0, 720, 1280, 720), (True, 720, 1280, 720)):
            with self.subTest(args=args), self.assertRaises(DisplayPlanError):
                PresentationTransform.integer_fit(*args)
        for args in ((1280, 720, 0, 0, -1, 720), (1280, 720, 0.0, 0, 1280, 720)):
            with self.assertRaises(DisplayPlanError):
                PresentationTransform(*args)

    def test_relative_samples_retain_subpixel_motion_and_cancel_reversals(self):
        transform = PresentationTransform.integer_fit(1280, 720, 2560, 1440)
        first, residual = transform.relative_sample(1, -1)
        self.assertEqual(first, (0, 0))
        second, residual = transform.relative_sample(1, -1, residual)
        self.assertEqual((second, residual), ((1, -1), (0, 0)))
        _, residual = transform.relative_sample(1, 1)
        self.assertEqual(transform.relative_sample(-1, -1, residual), ((0, 0), (0, 0)))

    def test_relative_conservation_for_random_signed_stream(self):
        transform = PresentationTransform(1366, 768, 0, 0, 2049, 1152)
        rng = random.Random(42)
        residual, inputs, outputs = (0, 0), [0, 0], [0, 0]
        for _ in range(5000):
            sample = (rng.randrange(-9, 10), rng.randrange(-9, 10))
            output, residual = transform.relative_sample(*sample, residual)
            for axis in (0, 1):
                inputs[axis] += sample[axis]
                outputs[axis] += output[axis]
        self.assertEqual(inputs[0] * 1366, outputs[0] * 2049 + residual[0])
        self.assertEqual(inputs[1] * 768, outputs[1] * 1152 + residual[1])

    def test_input_remainder_and_coordinate_types(self):
        transform = PresentationTransform(1280, 720, 0, 0, 2560, 1440)
        for residual in ((2560, 0), (0, -1440), (True, 0), (), [0, 0]):
            with self.subTest(residual=residual), self.assertRaises(DisplayPlanError):
                transform.relative_sample(1, 1, residual)
        with self.assertRaises(DisplayPlanError):
            transform.render_point(1.0, 0)


class SurfaceTests(unittest.TestCase):
    def test_padded_1366_surface_rows_do_not_use_width_as_pitch(self):
        layout = SurfaceLayout(1366, 768, 1376)
        self.assertEqual(layout.required_bytes, 767 * 1376 + 1366)
        spans = layout.byte_spans((0, 0, 1365, 767), layout.required_bytes)
        self.assertEqual(spans[1], (1376, 1366))
        self.assertEqual(spans[-1][0] + spans[-1][1], layout.required_bytes)
        self.assertTrue(all(length == 1366 for _, length in spans))

    def test_negative_pitch_uses_explicit_bottom_up_storage(self):
        layout = SurfaceLayout(3, 2, -8, 2)
        self.assertEqual(layout.required_bytes, 14)
        self.assertEqual(layout.byte_spans((1, 0, 2, 1), 14), ((10, 4), (2, 4)))

    def test_surface_copy_spans_preserve_padding_and_guard_bytes(self):
        layout = SurfaceLayout(3, 2, 8, 2)
        buffer = bytearray(b"x" * 20)
        for start, count in layout.byte_spans((0, 0, 2, 1), len(buffer)):
            buffer[start:start + count] = bytes(count)
        self.assertEqual(buffer, bytes(6) + b"xx" + bytes(6) + b"xxxxxx")

    def test_overflow_truncation_outside_rectangles_and_types_fail(self):
        for args in ((0, 1, 1), (3, 2, 2), (3, 2, 0), (3, 2, 8, 5), (True, 1, 2), (2, 32767, 0x7FFFFFFF)):
            with self.subTest(args=args), self.assertRaises(DisplayPlanError):
                SurfaceLayout(*args)
        layout = SurfaceLayout(1366, 768, 1376)
        for rect, size in (((0, 0, 1366, 767), layout.required_bytes), ((0, 0, 1365, 768), layout.required_bytes),
                           ((0, 0, 1365, 767), layout.required_bytes - 1), ((-1, 0, 1, 1), layout.required_bytes),
                           ((True, 0, 1, 1), layout.required_bytes)):
            with self.subTest(rect=rect, size=size), self.assertRaises(DisplayPlanError):
                layout.byte_spans(rect, size)
        with self.assertRaises(DisplayPlanError):
            layout.row_offset(768)


@unittest.skipUnless((ROOT / "src/patcher/patch_clash95_hd.py").is_file(), "complete repository source is required for recipe integration")
class RecipeIntegrationTests(unittest.TestCase):
    def test_all_existing_and_custom_profiles_use_real_recipes(self):
        expected = {"800x600": ((11, 8), (12, 9), (32, 56)), "1024x768": ((15, 11), (15, 12), (0, 32)),
                    "1280x720": ((19, 10), (19, 11), (0, 48)), "1366x768": ((20, 11), (21, 12), (22, 32)),
                    "1920x1080": ((29, 16), (29, 17), (0, 24)), "2560x1440": ((39, 22), (39, 22), (0, 0)),
                    "3440x1440": ((52, 22), (53, 22), (48, 0)), "3840x2160": ((59, 33), (59, 34), (0, 16)),
                    "802x602": ((11, 8), (12, 9), (34, 58))}
        for resolution, geometry in expected.items():
            with self.subTest(resolution=resolution):
                plan = resolve_display_plan(renderer="framed", resolution=resolution)
                self.assertEqual((plan.full_tiles, plan.coverage_tiles, plan.partial_pixels), geometry)
                self.assertEqual(len(plan.action_cells), 6)
                self.assertEqual(len(plan.frame_bands), 4)
                self.assertTrue(plan.minimap_viewport)
                classic = resolve_display_plan(resolution=resolution)
                self.assertFalse(classic.minimap_viewport)
                self.assertGreater(classic.scalar_patch_count, 0)

    def test_classic_800_preserves_frozen_selection_and_geometry(self):
        import patch_clash95_hd as patcher
        before = [(p.group, p.offset, p.old, p.new) for p in patcher.select_patches_for(patcher.DEFAULT_STAGE, patcher.PROFILE_800)]
        classic = resolve_display_plan()
        framed = resolve_display_plan(renderer="framed")
        self.assertEqual(classic.full_tiles, (12, 9))
        self.assertEqual(classic.terrain, (32, 16, 799, 591))
        self.assertEqual(framed.full_tiles, (11, 8))
        self.assertEqual(framed.terrain, (32, 16, 767, 583))
        self.assertEqual(before, [(p.group, p.offset, p.old, p.new) for p in patcher.select_patches_for(patcher.DEFAULT_STAGE, patcher.PROFILE_800)])

    def test_default_resolution_does_not_bypass_recipe_validation(self):
        import patch_clash95_hd as patcher
        with patch.object(patcher, "select_patches_for", side_effect=patcher.ResolutionError("fixture rejection")) as select:
            with self.assertRaises(DisplayPlanError) as error:
                resolve_display_plan()
        select.assert_called_once()
        self.assertEqual(error.exception.code, "recipe_rejected")

    def test_unknown_or_cross_profile_stage_rejected(self):
        import patch_clash95_hd as patcher
        for kwargs in ({"stage": "unknown"}, {"renderer": "framed", "stage": patcher.DEFAULT_STAGE},
                       {"stage": resolve_display_plan(renderer="framed").stage}):
            with self.subTest(kwargs=kwargs), self.assertRaises(DisplayPlanError):
                resolve_display_plan(**kwargs)

    def test_patcher_encoding_constraints_still_apply_beyond_policy(self):
        with self.assertRaises(DisplayPlanError):
            resolve_display_plan(resolution="16384x2160", bounds=((800, 600), (32766, 32766)))

    def test_framed_scalar_digest_and_requested_options_are_deterministic(self):
        first = resolve_display_plan(renderer="framed", resolution="1366x768")
        second = resolve_display_plan(renderer="framed", resolution="1366x768")
        self.assertEqual(first, second)
        without = resolve_display_plan(renderer="framed", resolution="1366x768", minimap_viewport=False)
        self.assertEqual(first.scalar_patch_sha256, without.scalar_patch_sha256)
        self.assertNotEqual(first.build_identity("a" * 64, {"fixture.py": "b" * 64}),
                            without.build_identity("a" * 64, {"fixture.py": "b" * 64}))

    def test_planning_does_not_modify_source_pins_or_resolution_registry(self):
        files = [ROOT / name for name in ("src/patcher/patch_clash95_hd.py", "src/patcher/framed_recipe.py",
                                         "src/patcher/framed_viewport.py", "src/launcher/resolutions.json")]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
        for renderer in ("classic", "framed"):
            resolve_display_plan(renderer=renderer, resolution="1280x720")
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files})


if __name__ == "__main__":
    unittest.main()

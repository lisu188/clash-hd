#!/usr/bin/env python3
"""Small pure fixtures: no runtime, files, dependency installation or OS input."""
from copy import deepcopy
import unittest

import ordinary_map_input_plan as tool


def fixture(*, resolution='1024x768', origin=(10, 11), destination=(11, 11), scroll=(7, 8)):
    width, height = map(int, resolution.split('x'))
    candidate = dict(schema=tool.CANDIDATE_SCHEMA, sha256='a'*64,
                     stage='synthetic-completehd-validation', profile='completehd',
                     resolution=resolution, layout=tool.LAYOUT)
    slots = [dict(type=1, ap=26), dict(type=16, ap=22)]+[dict(type=-1, ap=255) for _ in range(8)]
    def tile(xy, occupant):
        return dict(x=xy[0], y=xy[1], occupant=occupant, visible=True,
                    terrain_id=13, terrain_profile=2, overlay_id=65535, road_id=65535, trap_mask=0)
    neighborhood = {(x+dx, y+dy) for x, y in (origin, destination)
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if 0 <= x+dx < 50 and 0 <= y+dy < 50}
    measured_tiles = [tile(origin, 13), tile(destination, 65535)]
    measured_tiles += [tile(xy, 0x8000) for xy in sorted(neighborhood-{origin, destination})]
    snapshot = dict(schema=tool.OBSERVATION_SCHEMA, sequence=1, paused=True,
        identity=dict(pid=4321, creation_filetime=134349000000000000, candidate_sha256='a'*64, image_base=0x400000),
        context=dict(game_data=0x2000000, render_hook=0x40AD40, map_active=1,
                     native_modal=0, post_callback=0, lower_owner=0,
                     map_surface=0x3000000, map_pixels=0x4000000, map_vtable=0x50EE24,
                     map_extent=[width, height], primary_extent=[width, height],
                     current_player=0, turn_owner=0, viewed_player=0,
                     selected_stack=-1, previous_stack=-1, panel_stack=-1,
                     active_stack=0, join_mode=0, slot_flags=[0]*10),
        world=dict(width=50, height=50, scroll_x=scroll[0], scroll_y=scroll[1]),
        player=dict(index=0, human=True, minimap_visible=True),
        minimap=dict(left=width-246, top=16, width=214, height=214),
        port=dict(x=-1, y=-1),
        stacks=[dict(index=13, x=origin[0], y=origin[1], owner=0, hidden=False, queue_count=0, slots=slots)],
        tiles=measured_tiles,
        unit_profiles=[dict(type=1, costs=[4, 6, 5, 7, 4, 0, 8, 0]),
                       dict(type=16, costs=[4, 6, 7, 7, 4, 0, 8, 0])])
    return candidate, snapshot


def selected(snapshot, sequence):
    result = deepcopy(snapshot)
    result['sequence'] = sequence
    stack = result['stacks'][0]
    if len(tool.occupied_slots(stack)) == 1:
        result['context'].update(selected_stack=stack['index'], panel_stack=-1, lower_owner=0)
    else:
        result['context'].update(selected_stack=stack['index'], panel_stack=stack['index'],
            lower_owner=1, active_stack=result['context']['game_data']+147174+725*stack['index'])
    return result


def moved(snapshot, sequence):
    result = selected(snapshot, sequence)
    result['stacks'][0].update(x=11, y=11)
    result['stacks'][0]['slots'][0]['ap'] = 19
    result['stacks'][0]['slots'][1]['ap'] = 15
    result['tiles'][0]['occupant'] = 65535
    result['tiles'][1]['occupant'] = 13
    return result


class PlannerTests(unittest.TestCase):
    def test_measured_friendly_pair_uses_scroll_and_slowest_occupied_slot(self):
        candidate, state = fixture()
        original = deepcopy(state)
        plan = tool.plan_input(state, candidate)
        self.assertEqual(plan['selection'], dict(stack_index=13, tile=[10, 11], point=[256, 240]))
        self.assertEqual(plan['movement']['destination'], [11, 11])
        self.assertEqual(plan['movement']['point'], [320, 240])
        self.assertEqual(plan['movement']['measured_cardinal_cost'], 7)
        self.assertEqual(plan['movement']['ap_before'], [26, 22])
        self.assertEqual(plan['movement']['ap_after'], [19, 15])
        self.assertIs(plan['movement']['one_click_may_execute'], True)
        self.assertFalse(plan['reachability_proven'])
        self.assertFalse(plan['runtime_executed'])
        self.assertEqual(state, original)
        self.assertEqual(tool.checked_plan(plan), plan['basis'])

    def test_schema_requires_complete_typed_coherent_measurements(self):
        candidate, state = fixture()
        for key in state:
            bad = deepcopy(state); del bad[key]
            with self.subTest(missing=key), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
        mutations = [('schema', 'old'), ('sequence', True), ('paused', 1), ('stacks', {}), ('tiles', None)]
        for key, value in mutations:
            bad = deepcopy(state); bad[key] = value
            with self.subTest(key=key), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
        bad = deepcopy(state); bad['asserted_selected_by_input'] = True
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)

    def test_expected_candidate_and_layout_are_separate_required_contracts(self):
        candidate, state = fixture()
        for key, value in (('sha256', 'b'*64), ('schema', 'old'), ('profile', 'classic'),
                           ('layout', 'guessed'), ('resolution', '01024x768'),
                           ('stage', 'stable'), ('resolution', '640x480')):
            bad = dict(candidate, **{key:value})
            with self.subTest(key=key, value=value), self.assertRaises(tool.PlanError):
                tool.plan_input(state, bad)
        bad = deepcopy(state); bad['context']['primary_extent'] = [1024, 767]
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)

    def test_castle_modal_nonhuman_and_other_native_ownership_fail_closed(self):
        candidate, state = fixture()
        for key, value in (('render_hook', 0x422020), ('render_hook', 0x4617A0),
                           ('map_active', 0), ('native_modal', 1), ('post_callback', 1),
                           ('lower_owner', 2), ('viewed_player', 1), ('turn_owner', 1),
                           ('map_vtable', 0), ('game_data', 0), ('join_mode', 1),
                           ('slot_flags', [1]+[0]*9), ('selected_stack', True)):
            bad = deepcopy(state); bad['context'][key] = value
            with self.subTest(key=key), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
        for key, value in (('human', False), ('human', 1), ('index', 1)):
            bad = deepcopy(state); bad['player'][key] = value
            with self.subTest(player=key), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)

    def test_stack_must_be_different_friendly_visible_unhidden_present_and_idle(self):
        candidate, state = fixture()
        for key, value in (('owner', 1), ('hidden', True), ('queue_count', 1),
                           ('index', 500), ('x', -1), ('y', 50)):
            bad = deepcopy(state); bad['stacks'][0][key] = value
            with self.subTest(key=key), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
        for key, value in (('occupant', 0x8000), ('occupant', 12), ('visible', False)):
            bad = deepcopy(state); bad['tiles'][0][key] = value
            with self.subTest(origin=key), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
        bad = deepcopy(state); bad['context']['selected_stack'] = 13
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)
        bad = deepcopy(state); bad['stacks'][0]['slots'][0]['type'] = -1
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)
        bad = deepcopy(state); bad['stacks'][0]['slots'][0]['type'] = 41
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)

    def test_empty_tile_is_not_enough_for_a_movement_plan(self):
        candidate, state = fixture()
        for key, value in (('occupant', 14), ('occupant', 0x8000), ('visible', False),
                           ('trap_mask', 1), ('trap_mask', 16), ('overlay_id', 0x2D8),
                           ('overlay_id', 0x2E3), ('road_id', 207), ('terrain_id', 1024),
                           ('terrain_profile', 8)):
            bad = deepcopy(state); bad['tiles'][1][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
        bad = deepcopy(state); bad['port'] = dict(x=11, y=11)
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)
        bad = deepcopy(state); bad['unit_profiles'][1]['costs'][2] = 0
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)
        bad = deepcopy(state); bad['stacks'][0]['slots'][0]['ap'] = 6
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)
        bad = deepcopy(state); bad['unit_profiles'].pop()
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)

    def test_diagonal_or_unmeasured_neighbor_is_not_assumed_reachable(self):
        candidate, state = fixture(destination=(11, 12))
        with self.assertRaises(tool.PlanError): tool.plan_input(state, candidate)
        candidate, state = fixture(); state['tiles'].pop(1)
        with self.assertRaises(tool.PlanError): tool.plan_input(state, candidate)

    def test_bridge_terrain_is_excluded_even_without_overlay_and_with_positive_water_cost(self):
        for terrain in (603, 610):
            candidate, state = fixture()
            state['tiles'][1].update(terrain_id=terrain, terrain_profile=5)
            for profile in state['unit_profiles']:
                profile['costs'][5] = 3
            with self.subTest(terrain=terrain), self.assertRaises(tool.PlanError):
                tool.plan_input(state, candidate)

    def test_origin_trap_site_and_port_routes_are_excluded_before_selection(self):
        candidate, state = fixture()
        for key, value in (('trap_mask', 1), ('trap_mask', 16), ('overlay_id', 0x2DA), ('overlay_id', 0x2E3)):
            bad = deepcopy(state); bad['tiles'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
        state['port'] = dict(x=9, y=10)
        with self.assertRaises(tool.PlanError): tool.plan_input(state, candidate)

    def test_ambush_neighborhood_must_be_complete_and_reject_hidden_enemy_occupants(self):
        candidate, state = fixture()
        for xy in ((10, 10), (12, 12)):
            bad = deepcopy(state)
            bad['tiles'] = [t for t in bad['tiles'] if (t['x'], t['y']) != xy]
            with self.subTest(missing=xy), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
            bad = deepcopy(state)
            neighbor = deepcopy(bad['stacks'][0]); neighbor.update(index=14, x=xy[0], y=xy[1], owner=1, hidden=True)
            bad['stacks'].append(neighbor)
            next(t for t in bad['tiles'] if (t['x'], t['y']) == xy)['occupant'] = 14
            with self.subTest(hidden_enemy=xy), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
            bad['stacks'].pop()
            with self.subTest(unknown_occupant=xy), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)

    def test_duplicate_measurements_and_conflicting_terrain_lookup_reject(self):
        candidate, state = fixture()
        for name in ('stacks', 'tiles', 'unit_profiles'):
            bad = deepcopy(state); bad[name].append(deepcopy(bad[name][0]))
            with self.subTest(name=name), self.assertRaises(tool.PlanError):
                tool.plan_input(bad, candidate)
        bad = deepcopy(state); bad['tiles'][1]['terrain_profile'] = 1
        with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)

    def test_frame_partial_tiles_minimap_actions_and_portraits_are_excluded(self):
        cases = [dict(origin=(6, 11), destination=(7, 11)),
                 dict(origin=(10, 3), destination=(11, 3), scroll=(0, 0), resolution='802x602'),
                 dict(origin=(11, 1), destination=(12, 1), scroll=(0, 0)),
                 dict(origin=(12, 9), destination=(12, 10), scroll=(0, 0)),
                 dict(origin=(2, 9), destination=(2, 10), scroll=(0, 0))]
        for args in cases:
            candidate, state = fixture(**args)
            with self.subTest(args=args), self.assertRaises(tool.PlanError):
                tool.plan_input(state, candidate)
        candidate, state = fixture()
        state['minimap'] = dict(left=260, top=220, width=40, height=40)
        with self.assertRaises(tool.PlanError): tool.plan_input(state, candidate, aim_tolerance=4)
        self.assertEqual(tool.plan_input(state, candidate, aim_tolerance=3)['selection']['point'], [256, 240])

    def test_measured_minimap_visibility_and_rectangle_cannot_be_invented(self):
        candidate, state = fixture()
        for mini in (dict(left=1020, top=16, width=214, height=214),
                     dict(left=0, top=0, width=0, height=0)):
            bad = deepcopy(state); bad['minimap'] = mini
            with self.assertRaises(tool.PlanError): tool.plan_input(bad, candidate)
        state['player']['minimap_visible'] = False
        state['minimap'] = dict(left=0, top=0, width=0, height=0)
        self.assertEqual(tool.plan_input(state, candidate)['selection']['stack_index'], 13)

    def test_exact_ap_budget_allows_one_step_without_refill_or_return_trip(self):
        candidate, state = fixture()
        state['stacks'][0]['slots'][1]['ap'] = 7
        plan = tool.plan_input(state, candidate)
        self.assertEqual(plan['movement']['ap_after'], [19, 0])
        state['stacks'][0]['slots'][1]['ap'] = 6
        with self.assertRaises(tool.PlanError): tool.plan_input(state, candidate)

    def test_rebased_native_owner_and_vtable_bind_to_measured_image(self):
        candidate, state = fixture()
        state['identity']['image_base'] += 0x100000
        with self.assertRaises(tool.PlanError): tool.plan_input(state, candidate)
        state['context']['render_hook'] += 0x100000
        state['context']['map_vtable'] += 0x100000
        self.assertEqual(tool.plan_input(state, candidate)['selection']['point'], [256, 240])

    def test_small_world_and_resolution_use_real_scroll_without_clamping(self):
        for resolution in ('800x600', '1024x768', '1280x720', '1920x1080', '3840x2160'):
            candidate, state = fixture(resolution=resolution, origin=(2, 3), destination=(3, 3), scroll=(0, 0))
            state['world'].update(width=8, height=8)
            plan = tool.plan_input(state, candidate)
            self.assertEqual(plan['selection']['point'], [192, 240])
            self.assertFalse(plan['reachability_proven'])
        candidate, state = fixture(); state['world']['scroll_x'] = 50
        with self.assertRaises(tool.PlanError): tool.plan_input(state, candidate)

    def test_deterministic_choice_and_unrelated_records_do_not_enter_binding(self):
        candidate, state = fixture()
        extra = deepcopy(state['stacks'][0]); extra.update(index=25, x=40, y=40, owner=1)
        state['stacks'].insert(0, extra)
        plan = tool.plan_input(state, candidate)
        self.assertEqual([s['index'] for s in plan['basis']['stacks']], [13])
        self.assertEqual(len(plan['basis']['tiles']), 12)
        fresh = deepcopy(state); fresh['sequence'] = 2; fresh['stacks'][0]['x'] = 41
        self.assertEqual(tool.revalidate_before_click(plan, fresh, 'select')['stack_index'], 13)


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.candidate, self.state = fixture()
        self.plan = tool.plan_input(self.state, self.candidate)
        self.before_select = deepcopy(self.state); self.before_select['sequence'] = 2
        self.after_select = selected(self.state, 3)
        self.before_move = selected(self.state, 4)
        self.after_move = moved(self.state, 5)

    def test_exact_planned_selection_and_complete_movement_transition(self):
        self.assertTrue(tool.verify_selection(self.plan, self.before_select, self.after_select)['selection_state_transition'])
        receipt = tool.revalidate_before_click(self.plan, self.before_move, 'move')
        self.assertEqual(receipt['point'], [320, 240])
        outcome = tool.verify_movement(self.plan, self.before_move, self.after_move)
        self.assertTrue(outcome['movement_state_transition'])
        self.assertEqual(outcome['charged_ap'], 7)
        self.assertIn('ordinary input', outcome['proof_scope'])

    def test_stale_preclick_identity_player_camera_stack_tile_and_overlay_reject(self):
        changes = [(('identity', 'pid'), 999), (('identity', 'creation_filetime'), 1),
                   (('identity', 'candidate_sha256'), 'b'*64), (('identity', 'image_base'), 0x500000),
                   (('world', 'scroll_x'), 8), (('context', 'game_data'), 0x2100000),
                   (('context', 'map_surface'), 0x3100000), (('context', 'current_player'), 1),
                   (('context', 'selected_stack'), 7), (('context', 'lower_owner'), 1),
                   (('minimap', 'top'), 17), (('port', 'x'), 10)]
        for (group, key), value in changes:
            fresh = deepcopy(self.before_select); fresh[group][key] = value
            with self.subTest(group=group, key=key), self.assertRaises(tool.PlanError):
                tool.revalidate_before_click(self.plan, fresh, 'select')
        for name, key, value in (('stacks', 'queue_count', 1), ('stacks', 'x', 9),
                                 ('tiles', 'occupant', 12), ('tiles', 'visible', False),
                                 ('tiles', 'overlay_id', 1)):
            fresh = deepcopy(self.before_select); fresh[name][0][key] = value
            with self.subTest(name=name, key=key), self.assertRaises(tool.PlanError):
                tool.revalidate_before_click(self.plan, fresh, 'select')
        with self.assertRaises(tool.PlanError): tool.revalidate_before_click(self.plan, self.state, 'select')

    def test_planned_points_costs_and_claims_cannot_be_changed(self):
        mutations = [('selection', 'point', [320, 365]), ('movement', 'point', [384, 430]),
                     ('movement', 'measured_cardinal_cost', 1), ('movement', 'ap_after', [25, 21]),
                     ('movement', 'one_click_may_execute', False)]
        for group, key, value in mutations:
            bad = deepcopy(self.plan); bad[group][key] = value
            with self.subTest(group=group, key=key), self.assertRaises(tool.PlanError):
                tool.revalidate_before_click(bad, self.before_select, 'select')
        bad = deepcopy(self.plan); bad['reachability_proven'] = True
        with self.assertRaises(tool.PlanError): tool.checked_plan(bad)
        bad = deepcopy(self.plan); bad['basis']['world']['scroll_x'] = 1
        with self.assertRaises(tool.PlanError): tool.checked_plan(bad)

    def test_any_selected_index_or_old_snapshot_cannot_pass_this_selection(self):
        for key, value in (('selected_stack', 12), ('panel_stack', 12), ('active_stack', 0),
                           ('lower_owner', 0), ('render_hook', 0x422020), ('previous_stack', 499)):
            after = deepcopy(self.after_select); after['context'][key] = value
            with self.subTest(key=key), self.assertRaises(tool.PlanError):
                tool.verify_selection(self.plan, self.before_select, after)
        after = deepcopy(self.after_select); after['sequence'] = 2
        with self.assertRaises(tool.PlanError): tool.verify_selection(self.plan, self.before_select, after)
        after = deepcopy(self.after_select); after['stacks'][0]['slots'][0]['ap'] -= 1
        with self.assertRaises(tool.PlanError): tool.verify_selection(self.plan, self.before_select, after)
        with self.assertRaises(tool.PlanError): tool.verify_selection(self.plan, self.before_move, self.after_move)

    def test_movement_requires_selection_and_both_real_occupancy_commits(self):
        with self.assertRaises(tool.PlanError): tool.verify_movement(self.plan, self.before_select, self.after_move)
        for which, occupant in ((0, 13), (1, 65535), (1, 12)):
            after = deepcopy(self.after_move); after['tiles'][which]['occupant'] = occupant
            with self.subTest(which=which, occupant=occupant), self.assertRaises(tool.PlanError):
                tool.verify_movement(self.plan, self.before_move, after)
        for key, value in (('x', 10), ('y', 12), ('queue_count', 1), ('owner', 1), ('hidden', True)):
            after = deepcopy(self.after_move); after['stacks'][0][key] = value
            with self.subTest(key=key), self.assertRaises(tool.PlanError):
                tool.verify_movement(self.plan, self.before_move, after)

    def test_queue_empty_ap_only_or_single_slot_charge_is_not_movement_success(self):
        after = selected(self.state, 5)
        with self.assertRaises(tool.PlanError): tool.verify_movement(self.plan, self.before_move, after)
        after['stacks'][0]['slots'][0]['ap'] = 19
        after['stacks'][0]['slots'][1]['ap'] = 15
        with self.assertRaises(tool.PlanError): tool.verify_movement(self.plan, self.before_move, after)
        for slot, ap in ((0, 26), (1, 22), (1, 14)):
            after = deepcopy(self.after_move); after['stacks'][0]['slots'][slot]['ap'] = ap
            with self.subTest(slot=slot, ap=ap), self.assertRaises(tool.PlanError):
                tool.verify_movement(self.plan, self.before_move, after)

    def test_missing_or_changed_movement_profile_and_post_owner_are_rejected(self):
        for state in (self.before_move, self.after_move):
            changed = deepcopy(state); changed['unit_profiles'][0]['costs'][2] = 4
            with self.assertRaises(tool.PlanError):
                tool.verify_movement(self.plan, changed if state is self.before_move else self.before_move,
                                     changed if state is self.after_move else self.after_move)
        after = deepcopy(self.after_move); after['context']['render_hook'] = 0x422020
        with self.assertRaises(tool.PlanError): tool.verify_movement(self.plan, self.before_move, after)
        after = deepcopy(self.after_move); after['context']['previous_stack'] = 499
        with self.assertRaises(tool.PlanError): tool.verify_movement(self.plan, self.before_move, after)

    def test_preclick_revalidates_retained_ambush_tiles_and_neighbor_records(self):
        candidate, state = fixture()
        neighbor = deepcopy(state['stacks'][0]); neighbor.update(index=14, x=10, y=10, owner=1, hidden=False)
        state['stacks'].append(neighbor)
        next(t for t in state['tiles'] if (t['x'], t['y']) == (10, 10))['occupant'] = 14
        plan = tool.plan_input(state, candidate)
        self.assertEqual([s['index'] for s in plan['basis']['stacks']], [13, 14])
        fresh = deepcopy(state); fresh['sequence'] = 2
        self.assertEqual(tool.revalidate_before_click(plan, fresh, 'select')['stack_index'], 13)
        fresh['stacks'][1]['hidden'] = True
        with self.assertRaises(tool.PlanError): tool.revalidate_before_click(plan, fresh, 'select')
        fresh = deepcopy(state); fresh['sequence'] = 2
        next(t for t in fresh['tiles'] if (t['x'], t['y']) == (12, 12))['occupant'] = 15
        with self.assertRaises(tool.PlanError): tool.revalidate_before_click(plan, fresh, 'select')


class SingleSquadTests(unittest.TestCase):
    def case(self, active=0):
        candidate, state = fixture()
        state['stacks'][0]['slots'][1]['type'] = -1
        state['context']['active_stack'] = active
        plan = tool.plan_input(state, candidate)
        before = deepcopy(state); before['sequence'] = 2
        after = selected(state, 3)
        before_move = selected(state, 4)
        after_move = selected(state, 5)
        after_move['stacks'][0].update(x=11, y=11)
        after_move['stacks'][0]['slots'][0]['ap'] = 21
        after_move['tiles'][0]['occupant'] = 65535
        after_move['tiles'][1]['occupant'] = 13
        return candidate, state, plan, before, after, before_move, after_move

    def test_native_single_squad_selection_and_movement_keep_dormant_pointer(self):
        for active in (0, 0x2100000):
            with self.subTest(active=active):
                _, _, plan, before, after, before_move, after_move = self.case(active)
                self.assertEqual(plan['movement']['measured_cardinal_cost'], 5)
                self.assertTrue(tool.verify_selection(plan, before, after)['selection_state_transition'])
                self.assertTrue(tool.verify_movement(plan, before_move, after_move)['movement_state_transition'])
                self.assertEqual((after['context']['lower_owner'], after['context']['panel_stack'],
                                  after['context']['active_stack']), (0, -1, active))

    def test_changed_dormant_pointer_rejects_at_every_action_boundary(self):
        for which in ('before', 'after', 'before_move', 'after_move'):
            _, _, plan, before, after, before_move, after_move = self.case(0x2100000)
            states = dict(before=before, after=after, before_move=before_move, after_move=after_move)
            states[which]['context']['active_stack'] = 0
            with self.subTest(boundary=which), self.assertRaises(tool.PlanError):
                if which in ('before', 'after'):
                    tool.verify_selection(plan, before, after)
                else:
                    tool.verify_movement(plan, before_move, after_move)

    def test_selected_count_requires_measured_nonempty_stack_even_with_valid_headers(self):
        for single in (False, True):
            candidate, state = fixture()
            if single:
                state['stacks'][0]['slots'][1]['type'] = -1
            state = selected(state, 3)
            for kind in ('missing', 'empty'):
                bad = deepcopy(state)
                if kind == 'missing':
                    bad['stacks'] = []
                else:
                    bad['stacks'][0]['slots'][0]['type'] = -1
                tool.inspect_header(bad, candidate)  # Bounds are not acceptance.
                with self.subTest(single=single, kind=kind), self.assertRaises(tool.PlanError):
                    tool.inspect(bad, candidate)

    def test_single_squad_cannot_claim_live_panel_and_multi_squad_cannot_omit_it(self):
        candidate, _, _, _, after, _, _ = self.case()
        for key, value in (('lower_owner', 1), ('panel_stack', 13), ('slot_flags', [1]+[0]*9)):
            bad = deepcopy(after); bad['context'][key] = value
            with self.subTest(key=key), self.assertRaises(tool.PlanError):
                tool.inspect(bad, candidate)
        candidate, state = fixture()
        state['context']['selected_stack'] = 13
        with self.assertRaises(tool.PlanError):
            tool.inspect(state, candidate)
        state['context'].update(selected_stack=-1, panel_stack=13)
        with self.assertRaises(tool.PlanError):
            tool.inspect(state, candidate)

    def test_count_stops_at_first_native_sentinel_not_later_stale_slot(self):
        candidate, state = fixture()
        state['stacks'][0]['slots'][1]['type'] = -1
        state['stacks'][0]['slots'][2] = dict(type=16, ap=0)
        plan = tool.plan_input(state, candidate)
        before = deepcopy(state); before['sequence'] = 2
        self.assertEqual(plan['movement']['ap_before'], [26])
        self.assertTrue(tool.verify_selection(plan, before, selected(state, 3))['selection_state_transition'])

    def test_prior_selected_measurement_is_retained_outside_planned_neighborhood(self):
        candidate, state = fixture()
        old = deepcopy(state['stacks'][0]); old.update(index=25, x=40, y=40)
        state['stacks'].append(old)
        state['context'].update(selected_stack=25, panel_stack=25, lower_owner=1,
                                active_stack=state['context']['game_data']+147174+725*25)
        plan = tool.plan_input(state, candidate)
        self.assertEqual([stack['index'] for stack in plan['basis']['stacks']], [13, 25])
        self.assertEqual(tool.checked_plan(plan), plan['basis'])
        before = deepcopy(state); before['sequence'] = 2
        after = selected(state, 3); after['context']['previous_stack'] = 25
        self.assertTrue(tool.verify_selection(plan, before, after)['selection_state_transition'])

    def test_state_verifier_preserves_legacy_408030_previous_index_contract(self):
        candidate, state = fixture()
        state['context']['previous_stack'] = 42
        plan = tool.plan_input(state, candidate)
        before = deepcopy(state); before['sequence'] = 2
        for previous in (42, -1):
            after = selected(state, 3); after['context']['previous_stack'] = previous
            with self.subTest(previous=previous):
                self.assertTrue(tool.verify_selection(plan, before, after)['selection_state_transition'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

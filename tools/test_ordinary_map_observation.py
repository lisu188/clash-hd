"""Sparse synthetic-memory fixtures; no process, runtime, files or dependencies."""
from copy import deepcopy
import struct
import unittest
from unittest.mock import patch

import ordinary_map_input_plan as planner
import ordinary_map_observation as tool


class Memory:
    def __init__(self):
        self.regions = {}
        self.calls = []
        self.hook = None

    def map(self, address, size):
        if any(base < address+size and address < base+len(raw) for base, raw in self.regions.items()):
            raise AssertionError('overlapping synthetic mappings')
        self.regions[address] = bytearray(size)

    def span(self, address, size):
        for base, raw in self.regions.items():
            if base <= address and address+size <= base+len(raw):
                return raw, address-base
        raise OSError('unmapped synthetic memory')

    def put(self, address, value):
        raw, offset = self.span(address, len(value))
        raw[offset:offset+len(value)] = value

    def pack(self, address, fmt, *values):
        self.put(address, struct.pack('<'+fmt, *values))

    def read(self, address, size):
        self.calls.append((address, size))
        if self.hook:
            self.hook(self, address, size)
        raw, offset = self.span(address, size)
        return bytes(raw[offset:offset+size])


def fixture(*, image_base=0x400000, gd=0x2000000, world=(50, 50),
            origin=(10, 11), scroll=(7, 8), current_player=0):
    memory = Memory()
    delta = image_base-0x400000
    surface = 0x3000000
    memory.map(gd, 586398)
    for address, size in ((0x5202E0, 16), (0x51D4C0, 4), (0x52698C, 12),
                          (0x511B58, 8), (0x514194, 4), (0x526F78, 44),
                          (0x523344, 8), (0x5199D8, 4), (0x527C24, 4),
                          (0x52456C, 4096), (0x512568, 41*88)):
        memory.map(address+delta, size)
    memory.map(surface, 188)
    memory.pack(0x5202E0+delta, '4I', surface, gd, 0, current_player)
    memory.pack(surface, 'HHI', 1024, 768, 0x4000000)
    memory.pack(surface+184, 'I', 0x50EE24+delta)
    memory.pack(0x51D4C0+delta, 'HH', 1024, 768)
    memory.pack(0x511B58+delta, '2i', -1, -1)
    memory.pack(0x514194+delta, 'i', -1)
    memory.pack(0x5199D8+delta, 'I', 0x40AD40+delta)
    memory.pack(0x527C24+delta, 'I', 1)
    memory.pack(0x523344+delta, '4H', 778, 16, 214, 214)
    memory.pack(gd+140000, '4i', *world, *scroll)
    memory.pack(gd+147139, '2I', current_player, current_player)
    player = gd+140024+1423*current_player
    memory.pack(player+23, '2I', 1, 1)
    memory.put(player+57, b'\xff'*1300)
    memory.pack(gd+586374, '2i', -1, -1)
    for index in range(500):
        memory.pack(gd+147174+725*index+6, 'h', -1)
    for x in range(100):
        for y in range(100):
            memory.pack(gd+1400*x+14*y, '3H', 13, 65535, 65535)
    memory.put(gd+556374, b'\xff'*20000)
    memory.pack(0x52456C+delta+4*13, 'I', 2)
    for unit_type in range(41):
        memory.put(0x512568+delta+88*unit_type+30, bytes((4, 6, 7, 7, 4, 0, 8, 0)))
    memory.put(0x512568+delta+88+30, bytes((4, 6, 5, 7, 4, 0, 8, 0)))
    put_stack(memory, gd, 13, *origin, owner=current_player)
    candidate = dict(schema=planner.CANDIDATE_SCHEMA, sha256='a'*64,
                     stage='synthetic-completehd-validation', profile='completehd',
                     resolution='1024x768', layout=planner.LAYOUT)
    identity = dict(pid=4321, creation_filetime=134349000000000000,
                    candidate_sha256='a'*64, image_base=image_base)
    lease = dict(schema=tool.LEASE_SCHEMA, lease_id='owned_session-01.read_01',
                 paused=True, **identity)
    return memory, candidate, identity, lease


def put_stack(memory, gd, index, x, y, *, owner=0, types=(1, 16), aps=(26, 22), hidden=0):
    address = gd+147174+725*index
    raw = bytearray(725)
    struct.pack_into('<hhB', raw, 0, x, y, owner)
    for slot in range(10):
        struct.pack_into('<h', raw, 6+31*slot, types[slot] if slot < len(types) else -1)
        raw[14+31*slot] = aps[slot] if slot < len(aps) else 255
    raw[720] = hidden
    memory.put(address, bytes(raw))
    memory.pack(gd+556374+200*x+2*y, 'H', index)


def observe(case, *, indices=(13,), sequence=1, check_lease=None, read=None):
    memory, candidate, identity, lease = case
    checks = []
    def check(value):
        checks.append((len(memory.calls), deepcopy(value)))
        if check_lease:
            check_lease(value)
    result = tool.observe(read or memory.read, candidate=candidate, identity=identity,
                          sequence=sequence, lease=lease, check_lease=check, stack_indices=indices)
    return result, checks


class DecoderTests(unittest.TestCase):
    def test_measured_native_fields_interoperate_with_planner(self):
        case = fixture()
        result, checks = observe(case)
        state, receipt = result['snapshot'], result['receipt']
        plan = planner.plan_input(state, case[1])
        self.assertEqual(plan['selection'], dict(stack_index=13, tile=[10, 11], point=[256, 240]))
        self.assertEqual(plan['movement']['destination'], [11, 11])
        self.assertEqual(plan['movement']['measured_cardinal_cost'], 7)
        self.assertEqual(state['context']['previous_stack'], -1)
        self.assertEqual(state['context']['panel_stack'], -1)
        self.assertEqual(state['stacks'][0]['slots'][2], dict(type=-1, ap=255))
        self.assertEqual(state['port'], dict(x=-1, y=-1))
        self.assertEqual(receipt['observation_sha256'], planner.digest(state))
        self.assertEqual(receipt['read_set_sha256'], planner.digest(receipt['read_set']))
        self.assertEqual(len(checks), 3)
        self.assertEqual(checks[0][0], 0)
        self.assertLess(checks[0][0], checks[1][0])
        self.assertLess(checks[1][0], checks[2][0])
        self.assertIn('caller/host', receipt['authentication_scope'])
        self.assertFalse(plan['runtime_executed'])

    def test_relocation_moves_only_image_globals_and_native_code_pointers(self):
        case = fixture(image_base=0x500000, gd=0x2300000)
        state = observe(case)[0]['snapshot']
        self.assertEqual(state['context']['game_data'], 0x2300000)
        self.assertEqual(state['context']['map_surface'], 0x3000000)
        self.assertEqual(state['context']['map_pixels'], 0x4000000)
        self.assertEqual(state['context']['render_hook'], 0x50AD40)
        self.assertEqual(state['context']['map_vtable'], 0x60EE24)
        self.assertEqual(planner.plan_input(state, case[1])['selection']['stack_index'], 13)
        self.assertIn((0x6202E0, 16), case[0].calls)
        self.assertIn((0x2300000+147174+725*13, 725), case[0].calls)
        self.assertNotIn((0x5202E0, 16), case[0].calls)
        self.assertNotIn((0x2400000+147174+725*13, 725), case[0].calls)

    def test_distinct_previous_and_panel_indices_use_signed_dwords(self):
        case = fixture()
        memory = case[0]
        memory.pack(0x511B58, '2i', 7, -1)
        memory.pack(0x514194, 'i', 7)
        memory.pack(0x526994, 'I', 1)
        memory.pack(0x526FA0, 'I', 0x2000000+147174+725*7)
        put_stack(memory, 0x2000000, 7, 5, 5)
        context = observe(case)[0]['snapshot']['context']
        self.assertEqual((context['selected_stack'], context['previous_stack'], context['panel_stack']), (7, -1, 7))
        memory.pack(0x511B5C, 'i', -2)
        with self.assertRaises(tool.ObservationError):
            observe(case)

    def test_native_nonzero_flags_use_full_dword_and_hidden_byte(self):
        case = fixture()
        memory, gd = case[0], 0x2000000
        memory.pack(gd+140024+23, '2I', 0x10000, 0x10000)
        memory.pack(gd+147174+725*13+720, 'B', 128)
        state = observe(case)[0]['snapshot']
        self.assertIs(state['player']['human'], True)
        self.assertIs(state['player']['minimap_visible'], True)
        self.assertIs(state['stacks'][0]['hidden'], True)
        with self.assertRaises(planner.PlanError):
            planner.plan_input(state, case[1])

    def test_high_byte_of_slot_flag_is_not_silently_discarded(self):
        case = fixture()
        case[0].pack(0x526F78+4*4, 'I', 0x10000)
        with self.assertRaises(tool.ObservationError):
            observe(case)

    def test_x_major_tiles_occupancy_and_visibility_use_fixed_native_strides(self):
        case = fixture(current_player=3)
        memory, gd = case[0], 0x2000000
        # Decoys at transposed coordinates must not affect (10,11).
        memory.pack(gd+1400*11+14*10, 'H', 22)
        memory.pack(0x52456C+4*22, 'I', 4)
        memory.pack(gd+576374+100*10+11, 'B', 128)
        player = gd+140024+1423*3
        memory.pack(player+57+13*11+(11>>3), 'B', 0xff ^ (1 << (11 & 7)))
        state = observe(case)[0]['snapshot']
        tiles = {(t['x'], t['y']): t for t in state['tiles']}
        self.assertEqual(tiles[10, 11]['terrain_id'], 13)
        self.assertEqual(tiles[11, 10]['terrain_id'], 22)
        self.assertEqual(tiles[10, 11]['occupant'], 13)
        self.assertEqual(tiles[10, 11]['trap_mask'], 128)
        self.assertTrue(tiles[10, 11]['visible'])
        self.assertFalse(tiles[11, 11]['visible'])
        self.assertEqual(state['context']['turn_owner'], 3)

    def test_small_world_neighborhoods_stay_inside_measured_world(self):
        case = fixture(world=(7, 5), origin=(2, 2), scroll=(0, 0))
        result = observe(case)[0]
        self.assertTrue(all(0 <= t['x'] < 7 and 0 <= t['y'] < 5 for t in result['snapshot']['tiles']))
        self.assertEqual(planner.plan_input(result['snapshot'], case[1])['movement']['destination'], [3, 2])
        self.assertLessEqual(len(result['snapshot']['tiles']), 21)

    def test_all500_default_is_one_bounded_stack_run_and_records_empty_sentinels(self):
        case = fixture()
        result = observe(case, indices=None)[0]
        receipt = result['receipt']
        self.assertEqual(receipt['measured_stack_indices'], [13])
        self.assertEqual(len(receipt['empty_stack_indices']), 499)
        self.assertEqual(receipt['requested_stack_indices'], list(range(500)))
        self.assertEqual(case[0].calls.count((0x2000000+147174, 362500)), 2)
        self.assertLess(receipt['unique_read_bytes'], 550000)
        self.assertLess(receipt['read_calls'], 100)
        self.assertEqual(receipt['complete_read_passes'], 2)
        self.assertEqual(receipt['additional_anchor_passes'], 2)

    def test_explicit_reads_add_and_reread_omitted_selected_stack(self):
        for types in ((1,), (1, 16)):
            with self.subTest(types=types):
                case = fixture(); memory, gd = case[0], 0x2000000
                put_stack(memory, gd, 7, 5, 5, types=types, aps=(26, 22))
                select(memory, 7)
                if len(types) == 1:
                    memory.pack(0x514194, 'i', -1)
                    memory.pack(0x526994, 'I', 0)
                    memory.pack(0x526FA0, 'I', 0x2100000)
                result = observe(case)[0]
                self.assertEqual(result['receipt']['requested_stack_indices'], [13])
                self.assertEqual(result['receipt']['added_selected_indices'], [7])
                self.assertEqual(result['receipt']['added_occupant_indices'], [])
                self.assertEqual(result['receipt']['measured_stack_indices'], [7, 13])
                self.assertEqual(memory.calls.count((gd+147174+725*7, 725)), 2)
                self.assertEqual(len(planner.occupied_slots(result['snapshot']['stacks'][0])), len(types))

    def test_missing_or_unreadable_selected_record_rejects_after_header_validation(self):
        for missing in ('empty', 'unreadable'):
            with self.subTest(missing=missing):
                case = fixture(); memory, gd = case[0], 0x2000000
                memory.pack(0x511B58, 'i', 7)
                address = gd+147174+725*7
                def read(start, size):
                    if missing == 'unreadable' and start == address:
                        raise OSError('selected record unavailable')
                    return memory.read(start, size)
                with self.assertRaises(tool.ObservationError):
                    observe(case, read=read)

    def test_omitted_selected_record_mutation_between_passes_rejects(self):
        case = fixture(); memory, gd = case[0], 0x2000000
        put_stack(memory, gd, 7, 5, 5, types=(1,))
        memory.pack(0x511B58, 'i', 7)
        address = gd+147174+725*7
        def change(memory, start, size):
            if start == address and memory.calls.count((address, 725)) == 2:
                memory.pack(address+14, 'B', 25)
        memory.hook = change
        with self.assertRaisesRegex(tool.ObservationError, 'changed'):
            observe(case)

    def test_native_single_squad_after_read_uses_dormant_panel_for_selection_and_move(self):
        for active in (0, 0x2100000):
            with self.subTest(active=active):
                case = fixture(); memory, gd = case[0], 0x2000000
                put_stack(memory, gd, 13, 10, 11, types=(1,), aps=(26,))
                memory.pack(0x526FA0, 'I', active)
                initial = observe(case)[0]['snapshot']
                plan = planner.plan_input(initial, case[1])
                before = observe(case, sequence=2)[0]['snapshot']
                memory.pack(0x511B58, 'i', 13)
                after = observe(case, sequence=3)[0]['snapshot']
                self.assertTrue(planner.verify_selection(plan, before, after)['selection_state_transition'])
                put_stack(memory, gd, 13, 11, 11, types=(1,), aps=(21,))
                memory.pack(gd+556374+200*10+2*11, 'H', 65535)
                moved = observe(case, sequence=4)[0]['snapshot']
                self.assertTrue(planner.verify_movement(plan, after, moved)['movement_state_transition'])

    def test_selected_count_panel_mismatch_rejects_for_both_native_branches(self):
        for single in (False, True):
            case = fixture(); memory = case[0]
            memory.pack(0x511B58, 'i', 13)
            if single:
                put_stack(memory, 0x2000000, 13, 10, 11, types=(1,))
                select(memory)
            with self.subTest(single=single), self.assertRaises(tool.ObservationError):
                observe(case)

    def test_explicit_indices_do_not_require_unrelated_stack_bytes(self):
        case = fixture()
        base = 0x2000000+147174
        def bounded(address, size):
            if base <= address < base+362500 and (address, size) != (base+725*13, 725):
                raise OSError('other army bytes intentionally unavailable')
            return case[0].read(address, size)
        result = observe(case, read=bounded)[0]
        self.assertEqual(result['receipt']['requested_stack_indices'], [13])
        self.assertEqual(result['receipt']['measured_stack_indices'], [13])

    def test_new_neighbor_occupants_are_discovered_without_recursive_expansion(self):
        case = fixture()
        put_stack(case[0], 0x2000000, 42, 12, 11, owner=2)
        result = observe(case)[0]
        self.assertEqual(result['receipt']['added_occupant_indices'], [42])
        self.assertEqual(result['receipt']['measured_stack_indices'], [13, 42])
        self.assertIn((0x2000000+147174+725*42, 725), case[0].calls)
        self.assertNotIn((14, 11), {(t['x'], t['y']) for t in result['snapshot']['tiles']})

    def test_nearby_hidden_enemy_remains_measured_and_planner_rejects(self):
        case = fixture()
        put_stack(case[0], 0x2000000, 42, 10, 12, owner=2, hidden=1)
        state = observe(case)[0]['snapshot']
        self.assertTrue(next(s for s in state['stacks'] if s['index'] == 42)['hidden'])
        with self.assertRaises(planner.PlanError):
            planner.plan_input(state, case[1])

    def test_occupant_coordinate_mismatch_unknown_and_duplicate_indices_fail(self):
        for value in (500, 0x8064, 0x7fff, 13):
            with self.subTest(value=value):
                case = fixture()
                case[0].pack(0x2000000+556374+200*11+2*11, 'H', value)
                with self.assertRaises(tool.ObservationError):
                    observe(case)
        case = fixture()
        case[0].pack(0x2000000+556374+200*11+2*11, 'H', 42)
        with self.assertRaises(tool.ObservationError):
            observe(case)  # Index42's first slot is empty.

    def test_building_and_empty_occupancy_are_preserved_without_fake_stack_reads(self):
        case = fixture()
        case[0].pack(0x2000000+556374+200*11+2*10, 'H', 0x8005)
        state = observe(case)[0]['snapshot']
        self.assertEqual(next(t for t in state['tiles'] if (t['x'], t['y']) == (11, 10))['occupant'], 0x8005)
        self.assertEqual([s['index'] for s in state['stacks']], [13])

    def test_duplicate_or_invalid_requested_indices_fail_before_reads(self):
        for indices in ([], [13, 13], [True], [-1], [500], {13}, '13'):
            with self.subTest(indices=indices):
                case = fixture()
                with self.assertRaises(tool.ObservationError):
                    observe(case, indices=indices)
                self.assertEqual(case[0].calls, [])

    def test_unmapped_short_mutable_and_nonbytes_results_fail(self):
        for replacement in (None, bytearray(16), b'\0'*15, b'\0'*17):
            with self.subTest(replacement=type(replacement).__name__):
                case = fixture()
                with self.assertRaises(tool.ObservationError):
                    observe(case, read=lambda address, size: replacement)
        case = fixture()
        del case[0].regions[0x3000000]
        with self.assertRaises(tool.ObservationError):
            observe(case)

    def test_invalid_runtime_pointer_rejects_before_large_reads(self):
        for value in (0, 0xffff, 0xffffffff):
            case = fixture()
            case[0].pack(0x5202E4, 'I', value)
            with self.assertRaises(tool.ObservationError):
                observe(case)
            self.assertEqual(case[0].calls, [(0x5202E0, 16)])

    def test_partial_alias_of_header_and_image_anchor_fails(self):
        case = fixture()
        case[0].pack(0x5202E0, 'I', 0x5202E4)
        with self.assertRaisesRegex(tool.ObservationError, 'overlapping'):
            observe(case)

    def test_changed_gd_or_surface_pointer_is_not_accepted_as_a_second_identity(self):
        for offset, replacement in ((4, 0x2100000), (0, 0x3100000)):
            case = fixture()
            def change(memory, address, size):
                if address == 0x5202E0 and memory.calls.count((address, size)) == 2:
                    memory.pack(address+offset, 'I', replacement)
            case[0].hook = change
            with self.assertRaisesRegex(tool.ObservationError, 'paused bytes changed'):
                observe(case)

    def test_repeat_pass_detects_nonanchor_army_or_tile_change(self):
        for address, size, offset in ((0x2000000+147174+725*13, 725, 14),
                                      (0x2000000, 140000, 1400*10+14*11)):
            case = fixture()
            def change(memory, where, count):
                if (where, count) == (address, size) and memory.calls.count((where, count)) == 2:
                    raw, base = memory.span(where, count)
                    raw[base+offset] ^= 1
            case[0].hook = change
            with self.assertRaisesRegex(tool.ObservationError, 'paused bytes changed'):
                observe(case)

    def test_final_anchor_pass_detects_change_after_full_comparison(self):
        case = fixture()
        def change(memory, address, size):
            if address == 0x5202E0 and memory.calls.count((address, size)) == 4:
                memory.pack(0x5202EC, 'I', 1)
        case[0].hook = change
        with self.assertRaisesRegex(tool.ObservationError, 'paused bytes changed'):
            observe(case)

    def test_lease_loss_at_each_boundary_prevents_a_receipt(self):
        for failed_check in (1, 2, 3):
            case = fixture()
            calls = []
            def check(lease):
                calls.append(lease['lease_id'])
                if len(calls) == failed_check:
                    raise RuntimeError('host lease expired')
            with self.assertRaisesRegex(tool.ObservationError, 'live paused lease'):
                observe(case, check_lease=check)
            self.assertEqual(len(calls), failed_check)
            if failed_check == 1:
                self.assertEqual(case[0].calls, [])

    def test_lease_shape_identity_and_mutation_reject(self):
        for key, value in (('paused', False), ('pid', 4322), ('pid', True),
                           ('image_base', 0x500000), ('candidate_sha256', 'b'*64),
                           ('lease_id', 'ambiguous path/file'), ('lease_id', 'x'*129),
                           ('lease_id', '\u00e9'), ('schema', 'old')):
            case = fixture()
            case[3][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(tool.ObservationError):
                observe(case)
            self.assertEqual(case[0].calls, [])
        case = fixture()
        def change(lease):
            lease['lease_id'] = 'new'
        with self.assertRaisesRegex(tool.ObservationError, 'mutated'):
            observe(case, check_lease=change)

    def test_lease_check_must_return_none_not_an_asserted_boolean(self):
        for value in (True, False, 'paused'):
            case = fixture()
            with self.subTest(value=value), self.assertRaisesRegex(tool.ObservationError, 'synchronously'):
                tool.observe(case[0].read, candidate=case[1], identity=case[2], sequence=1,
                             lease=case[3], check_lease=lambda lease: value, stack_indices=[13])
            self.assertEqual(case[0].calls, [])

    def test_async_lease_checker_is_rejected_without_reading_memory(self):
        case = fixture()
        executed = []
        async def check(lease):
            executed.append(lease)
        with self.assertRaisesRegex(tool.ObservationError, 'synchronously'):
            tool.observe(case[0].read, candidate=case[1], identity=case[2], sequence=1,
                         lease=case[3], check_lease=check, stack_indices=[13])
        self.assertEqual(executed, [])
        self.assertEqual(case[0].calls, [])

    def test_candidate_identity_and_sequence_reject_before_reads(self):
        for target, key, value in ((1, 'sha256', 'b'*64), (2, 'image_base', 0x400001),
                                    (2, 'creation_filetime', 0), (2, 'extra', 'unknown')):
            case = fixture()
            case[target][key] = value
            with self.subTest(key=key), self.assertRaises(tool.ObservationError):
                observe(case)
            self.assertEqual(case[0].calls, [])
        case = fixture()
        with self.assertRaises(tool.ObservationError):
            observe(case, sequence=True)
        self.assertEqual(case[0].calls, [])

    def test_byte_and_call_caps_fail_closed(self):
        for constant, limit in (('MAX_UNIQUE_BYTES', 100), ('MAX_READ_CALLS', 1), ('MAX_TOTAL_BYTES', 20)):
            case = fixture()
            with self.subTest(constant=constant), patch.object(tool, constant, limit):
                with self.assertRaisesRegex(tool.ObservationError, 'budget'):
                    observe(case)

    def test_signed_stack_coordinates_queue_and_type_are_not_truncated(self):
        for offset, fmt, value in ((0, 'h', -1), (316, 'i', -1), (316, 'i', 101), (6, 'h', -2)):
            case = fixture()
            case[0].pack(0x2000000+147174+725*13+offset, fmt, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(tool.ObservationError):
                observe(case)

    def test_costs_ap_and_terrain_lookup_are_measured_at_native_widths(self):
        case = fixture()
        case[0].put(0x512568+88+30, bytes((1, 2, 203, 4, 5, 6, 7, 8)))
        case[0].pack(0x2000000+147174+725*13+14, 'B', 255)
        state = observe(case)[0]['snapshot']
        self.assertEqual(state['unit_profiles'][0]['costs'][2], 203)
        self.assertEqual(state['stacks'][0]['slots'][0]['ap'], 255)
        case[0].pack(0x52456C+4*13, 'I', 0x10000002)
        with self.assertRaises(tool.ObservationError):
            observe(case)

    def test_same_index_different_army_is_not_a_valid_selection_transition(self):
        case = fixture()
        plan = planner.plan_input(observe(case)[0]['snapshot'], case[1])
        before = observe(case, sequence=2)[0]['snapshot']
        put_stack(case[0], 0x2000000, 13, 10, 11, types=(2, 16))
        select(case[0])
        after = observe(case, sequence=3)[0]['snapshot']
        self.assertEqual(before['stacks'][0]['index'], after['stacks'][0]['index'])
        with self.assertRaises(planner.PlanError):
            planner.verify_selection(plan, before, after)

    def test_opaque_army_change_changes_read_digest_even_when_projection_matches(self):
        case = fixture()
        first = observe(case)[0]
        case[0].pack(0x2000000+147174+725*13+724, 'B', 7)
        second = observe(case)[0]
        self.assertEqual(first['snapshot'], second['snapshot'])
        self.assertNotEqual(first['receipt']['read_set_sha256'], second['receipt']['read_set_sha256'])

    def test_exact_selection_and_one_click_movement_observations(self):
        case = fixture()
        initial = observe(case)[0]['snapshot']
        plan = planner.plan_input(initial, case[1])
        before = observe(case, sequence=2)[0]['snapshot']
        select(case[0])
        selected = observe(case, sequence=3)[0]['snapshot']
        self.assertTrue(planner.verify_selection(plan, before, selected)['selection_state_transition'])
        before_move = observe(case, sequence=4)[0]['snapshot']
        put_stack(case[0], 0x2000000, 13, 11, 11, aps=(19, 15))
        case[0].pack(0x2000000+556374+200*10+2*11, 'H', 65535)
        after_move = observe(case, sequence=5)[0]['snapshot']
        self.assertTrue(planner.verify_movement(plan, before_move, after_move)['movement_state_transition'])

    def test_adjacent_requested_records_coalesce_and_order_is_deterministic(self):
        case = fixture()
        put_stack(case[0], 0x2000000, 14, 18, 12)
        first = observe(case, indices=(14, 13))[0]
        second = observe(case, indices=(13, 14))[0]
        self.assertEqual(first, second)
        self.assertIn((0x2000000+147174+725*13, 1450), case[0].calls)
        self.assertEqual(first['receipt']['requested_stack_indices'], [13, 14])


def select(memory, index=13, *, gd=0x2000000):
    memory.pack(0x511B58, 'i', index)
    memory.pack(0x514194, 'i', index)
    memory.pack(0x526994, 'I', 1)
    memory.pack(0x526FA0, 'I', gd+147174+725*index)


if __name__ == '__main__':
    unittest.main()

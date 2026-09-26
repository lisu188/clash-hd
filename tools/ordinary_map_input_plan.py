"""Pure, measured plans for ordinary map selection and one cardinal move.

The caller supplies an independently authenticated candidate contract and a
coherent, paused, read-only observation. This module does not authenticate a
process, read memory, move a cursor, call native code, or launch anything.
The observation may contain only measured candidate stacks and their neighbors;
failure to find a pair is not proof that no other pair exists in the world.

Native evidence: 408030/4084A0 selection and tile dispatch; 40F060 visibility;
413920 merged slot costs; 414150 tile admission; 4147A0 pathfinding. Arrays in
game data are X-major, with fixed 100-cell strides, regardless of world size.
One adjacent click can execute immediately. A planned cost is a bounded native
cost calculation, not proof of runtime reachability or ordinary input dispatch.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.patcher.framed_viewport import FramedViewport, Rect, TILE_SIZE
from src.patcher.framed_army_viewport import FramedArmyViewport

OBSERVATION_SCHEMA = 'clash95_ordinary_map_observation_v1'
CANDIDATE_SCHEMA = 'clash95_ordinary_map_input_candidate_v1'
PLAN_SCHEMA = 'clash95_ordinary_map_input_plan_v1'
LAYOUT = 'framed_native_tiles_v1'
EMPTY = 0xFFFF
MAX_ADDRESS = 0x7FFE0000
CARDINALS = ((1, 0), (0, 1), (-1, 0), (0, -1))
# Reader wiring must read these native values; this table performs no reads.
NATIVE = dict(game_data=0x5202E4, current_player=0x5202EC,
              render_hook=0x5199D8, selected_stack=0x511B58,
              previous_stack=0x511B5C, panel_stack=0x514194,
              map_active=0x527C24, native_modal=0x52698C,
              post_callback=0x526990, lower_owner=0x526994,
              active_stack=0x526FA0, slot_flags=0x526F78,
              minimap_rect=0x523344, terrain_profiles=0x52456C,
              unit_metadata=0x512568, stack_table=147174, stack_stride=725,
              player_table=140024, player_stride=1423, visibility_offset=57,
              world_width=140000, world_height=140004,
              scroll_x=140008, scroll_y=140012, turn_owner=147139, viewed_player=147143,
              occupancy=556374, terrain_stride_x=1400, terrain_stride_y=14,
              trap_masks=576374, port_x=586374, port_y=586378)


class PlanError(ValueError):
    """A required measurement, identity, exclusion or transition did not match."""


def require(condition, message):
    if not condition:
        raise PlanError(message)


def integer(value, low, high, name):
    require(type(value) is int and low <= value <= high, name+' is out of bounds or not an integer')
    return value


def record(value, fields, name):
    require(type(value) is dict and set(value) == set(fields.split()), name+' has missing or unknown fields')
    return value


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def candidate_contract(candidate):
    record(candidate, 'schema sha256 stage profile resolution layout', 'candidate')
    require(candidate['schema'] == CANDIDATE_SCHEMA and candidate['layout'] == LAYOUT, 'unsupported candidate layout/schema')
    require(type(candidate['sha256']) is str and re.fullmatch('[0-9a-f]{64}', candidate['sha256']), 'candidate SHA-256 required')
    require(candidate['profile'] in ('completehd', 'modalwidgets'), 'profile has no authenticated framed/army layout adapter')
    require(type(candidate['stage']) is str and candidate['stage'].endswith('-validation'), 'explicit validation stage required')
    require(type(candidate['resolution']) is str and re.fullmatch('[1-9][0-9]*x[1-9][0-9]*', candidate['resolution']), 'canonical resolution required')
    width, height = map(int, candidate['resolution'].split('x'))
    try:
        framed = FramedViewport(width, height)
        army = FramedArmyViewport(width, height)
    except ValueError as error:
        raise PlanError('unsupported candidate dimensions: '+str(error)) from error
    return framed, army


def occupied_slots(stack):
    """Native slots are contiguous and stop at signed type -1; no writes."""
    occupied = []
    for slot in stack['slots']:
        if slot['type'] == -1:
            break
        require(0 <= slot['type'] <= 40, 'occupied slot type is outside native metadata')
        occupied.append(slot)
    require(bool(occupied), 'stack has no occupied first slot')
    return occupied


def inspect(snapshot, candidate):
    """Validate normalized measurements; caller remains responsible for provenance."""
    framed, army = candidate_contract(candidate)
    record(snapshot, 'schema sequence paused identity context world player minimap port stacks tiles unit_profiles', 'observation')
    require(snapshot['schema'] == OBSERVATION_SCHEMA and snapshot['paused'] is True, 'coherent paused observation required')
    integer(snapshot['sequence'], 0, 0x7FFFFFFF, 'observation sequence')
    identity = record(snapshot['identity'], 'pid creation_filetime candidate_sha256 image_base', 'identity')
    integer(identity['pid'], 1, 0xFFFFFFFF, 'PID')
    integer(identity['creation_filetime'], 1, 0x7FFFFFFFFFFFFFFF, 'process creation time')
    base = integer(identity['image_base'], 0x10000, MAX_ADDRESS-0x400000, 'image base')
    require(base % 0x10000 == 0 and identity['candidate_sha256'] == candidate['sha256'], 'candidate/process binding differs')
    delta = base-0x400000
    context = record(snapshot['context'], 'game_data render_hook map_active native_modal post_callback lower_owner map_surface map_pixels map_vtable map_extent primary_extent current_player turn_owner viewed_player selected_stack previous_stack panel_stack active_stack join_mode slot_flags', 'context')
    integer(context['game_data'], 0x10000, MAX_ADDRESS-586398, 'game data')
    integer(context['map_active'], 1, 0xFFFFFFFF, 'map active')
    require(type(context['render_hook']) is int and context['render_hook'] == 0x40AD40+delta, 'ordinary map does not own rendering')
    for name in ('native_modal', 'post_callback', 'join_mode'):
        require(type(context[name]) is int and context[name] == 0, name+' is active or unavailable')
    integer(context['lower_owner'], 0, 1, 'lower owner')
    integer(context['map_surface'], 0x10000, MAX_ADDRESS-188, 'map surface')
    integer(context['map_pixels'], 0x10000, MAX_ADDRESS-framed.width*framed.height, 'map pixels')
    require(type(context['map_vtable']) is int and context['map_vtable'] == 0x50EE24+delta, 'native map surface vtable differs')
    for name in ('map_extent', 'primary_extent'):
        require(type(context[name]) is list and all(type(v) is int for v in context[name])
                and context[name] == [framed.width, framed.height], name+' differs from executed candidate')
    for name in ('current_player', 'turn_owner', 'viewed_player'):
        integer(context[name], 0, 4, name)
    require(context['current_player'] == context['turn_owner'] == context['viewed_player'], 'human/view/turn player identities differ')
    for name in ('selected_stack', 'previous_stack', 'panel_stack'):
        integer(context[name], -1, 499, name)
    integer(context['active_stack'], 0, MAX_ADDRESS-725, 'active stack pointer')
    if context['selected_stack'] == -1:
        require(context['lower_owner'] == 0, 'unselected map has an active lower owner')
    else:
        require(context['lower_owner'] == 1 and context['panel_stack'] == context['selected_stack']
                and context['active_stack'] == context['game_data']+147174+725*context['selected_stack'],
                'selected map/panel ownership is incoherent')
    require(type(context['slot_flags']) is list and len(context['slot_flags']) == 10
            and all(type(v) is int and v == 0 for v in context['slot_flags']), 'whole-army zero slot flags required')
    world = record(snapshot['world'], 'width height scroll_x scroll_y', 'world')
    for size, scroll in (('width', 'scroll_x'), ('height', 'scroll_y')):
        integer(world[size], 1, 100, 'world '+size)
        integer(world[scroll], 0, world[size]-1, scroll)
    player = record(snapshot['player'], 'index human minimap_visible', 'player')
    require(type(player['index']) is int and player['index'] == context['current_player'], 'player record differs')
    require(player['human'] is True and type(player['minimap_visible']) is bool, 'measured human/minimap flags required')
    mini = record(snapshot['minimap'], 'left top width height', 'minimap')
    for name, high in (('left', framed.width), ('top', framed.height), ('width', framed.width), ('height', framed.height)):
        integer(mini[name], 0, high, 'minimap '+name)
    require(mini['left']+mini['width'] <= framed.width and mini['top']+mini['height'] <= framed.height, 'minimap exceeds primary')
    if player['minimap_visible']:
        require(mini['width'] > 0 and mini['height'] > 0, 'visible minimap rectangle unavailable')
    port = record(snapshot['port'], 'x y', 'port')
    integer(port['x'], -1, world['width']-1, 'port x')
    integer(port['y'], -1, world['height']-1, 'port y')
    if port['x'] != -1:
        require(0 <= port['y'] < world['height']-1 and port['x'] < world['width']-1, 'port footprint outside world')
    require(type(snapshot['stacks']) is list and len(snapshot['stacks']) <= 500, 'bounded measured stack list required')
    stacks = {}
    for stack in snapshot['stacks']:
        record(stack, 'index x y owner hidden queue_count slots', 'stack')
        index = integer(stack['index'], 0, 499, 'stack index')
        require(index not in stacks, 'duplicate stack record')
        for axis, extent in (('x', 'width'), ('y', 'height')):
            integer(stack[axis], 0, world[extent]-1, 'stack '+axis)
        integer(stack['owner'], 0, 4, 'stack owner')
        require(type(stack['hidden']) is bool, 'measured hidden flag required')
        integer(stack['queue_count'], 0, 100, 'queue count')
        require(type(stack['slots']) is list and len(stack['slots']) == 10, 'ten measured slot records required')
        for slot in stack['slots']:
            record(slot, 'type ap', 'slot')
            integer(slot['type'], -32768, 32767, 'signed slot type')
            integer(slot['ap'], 0, 255, 'slot AP')
        stacks[index] = stack
    require(type(snapshot['tiles']) is list and len(snapshot['tiles']) <= 10000, 'bounded measured tile list required')
    tiles, terrain_profiles = {}, {}
    for tile in snapshot['tiles']:
        record(tile, 'x y occupant visible terrain_id terrain_profile overlay_id road_id trap_mask', 'tile')
        for axis, extent in (('x', 'width'), ('y', 'height')):
            integer(tile[axis], 0, world[extent]-1, 'tile '+axis)
        key = tile['x'], tile['y']
        require(key not in tiles, 'duplicate tile measurement')
        for name in ('occupant', 'overlay_id', 'road_id'):
            integer(tile[name], 0, 65535, name)
        require(type(tile['visible']) is bool, 'measured visibility bit required')
        integer(tile['terrain_id'], 0, 1023, 'terrain ID')
        integer(tile['terrain_profile'], 0, 7, 'measured terrain profile')
        integer(tile['trap_mask'], 0, 255, 'trap mask')
        previous = terrain_profiles.setdefault(tile['terrain_id'], tile['terrain_profile'])
        require(previous == tile['terrain_profile'], 'inconsistent measured terrain lookup')
        tiles[key] = tile
    require(type(snapshot['unit_profiles']) is list and len(snapshot['unit_profiles']) <= 41, 'bounded measured unit profile list required')
    profiles = {}
    for profile in snapshot['unit_profiles']:
        record(profile, 'type costs', 'unit profile')
        unit_type = integer(profile['type'], 0, 40, 'unit profile type')
        require(unit_type not in profiles, 'duplicate unit profile')
        require(type(profile['costs']) is list and len(profile['costs']) == 8, 'eight measured terrain costs required')
        for value in profile['costs']:
            integer(value, 0, 255, 'unit terrain cost')
        profiles[unit_type] = profile
    return framed, army, stacks, tiles, profiles


def tile_point(snapshot, framed, army, x, y, tolerance):
    integer(tolerance, 0, 15, 'aim tolerance')
    world = snapshot['world']
    column, row = x-world['scroll_x'], y-world['scroll_y']
    require(column >= 0 and row >= 0, 'tile lies before camera origin')
    point = [framed.terrain.left+TILE_SIZE*column+TILE_SIZE//2,
             framed.terrain.top+TILE_SIZE*row+TILE_SIZE//2]
    area = Rect(point[0]-tolerance, point[1]-tolerance, point[0]+tolerance, point[1]+tolerance)
    require(framed.terrain.contains(area), 'tile center/tolerance intersects frame or lies outside viewport')
    # Exclude the panel prospectively: it appears after the planned selection.
    require(area.intersection(framed.action_bar) is None, 'aim intersects action bar')
    require(area.intersection(army.backing) is None, 'aim intersects army portraits')
    if snapshot['player']['minimap_visible']:
        mini = snapshot['minimap']
        # Native hit testing uses strict interiors. Excluding its outer bounds
        # too avoids relying on border pixels or aim rounding at that boundary.
        box = Rect(mini['left'], mini['top'], mini['left']+mini['width'], mini['top']+mini['height'])
        require(area.intersection(box) is None, 'aim intersects measured minimap')
    return point


def plain_endpoint(snapshot, tile):
    require(tile['trap_mask'] == 0 and not 0x2D8 <= tile['overlay_id'] <= 0x2E3, 'endpoint has trap or religious-site semantics')
    port = snapshot['port']
    require(port['x'] == -1 or not (port['x'] <= tile['x'] <= port['x']+1 and port['y'] <= tile['y'] <= port['y']+1), 'endpoint is inside port footprint')


def safe_cost(snapshot, stack, tile, profiles):
    require(tile['occupant'] == EMPTY and tile['visible'], 'destination is occupied or unrevealed')
    plain_endpoint(snapshot, tile)
    require(tile['road_id'] == EMPTY, 'road/bridge cost is outside this bounded planner')
    # Native 424370 recognizes bridge crossings by base terrain, independently
    # of the road overlay. Do not infer their cost from a water movement slot.
    require(not 603 <= tile['terrain_id'] <= 610, 'bridge terrain cost is outside this bounded planner')
    slots = occupied_slots(stack)
    require(all(slot['type'] in profiles for slot in slots), 'occupied slot lacks measured movement profile')
    costs = [profiles[slot['type']]['costs'][tile['terrain_profile']] for slot in slots]
    require(all(costs), 'native merged movement profile blocks this terrain')
    cost = max(costs)
    require(min(slot['ap'] for slot in slots) >= cost, 'insufficient current AP for cardinal cost')
    return cost


def ambush_neighborhood(snapshot, stack, destination, stacks, tiles):
    """444150 can attack adjacent hidden enemies before and after each step.

    Its twelve table entries cover the eight immediate neighbors plus repeats.
    Require both complete in-world 3x3 neighborhoods, preserving occupant
    records rather than interpreting absent measurements as empty ground.
    """
    world = snapshot['world']
    required = {(x+dx, y+dy) for x, y in ((stack['x'], stack['y']), (destination['x'], destination['y']))
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if 0 <= x+dx < world['width'] and 0 <= y+dy < world['height']}
    require(required <= tiles.keys(), 'complete measured ambush neighborhoods required')
    occupants = {stack['index']}
    for key in sorted(required):
        occupant = tiles[key]['occupant']
        if occupant == EMPTY or 0x8000 <= occupant < 0x8000+100:
            continue
        require(0 <= occupant < 500 and occupant in stacks, 'neighbor occupant has no bounded measured stack record')
        neighbor = stacks[occupant]
        require((neighbor['x'], neighbor['y']) == key, 'neighbor occupancy and stack coordinates differ')
        occupied_slots(neighbor)
        require(neighbor['owner'] == stack['owner'] or not neighbor['hidden'], 'hidden enemy can trigger native adjacent combat')
        occupants.add(occupant)
    return required, occupants


def _make(snapshot, candidate, tolerance, stack, origin, destination, cost, framed, army, neighborhood, occupants):
    types = {slot['type'] for slot in occupied_slots(stack)}
    basis = deepcopy(snapshot)
    basis['stacks'] = [deepcopy(stack)]+sorted((deepcopy(s) for s in snapshot['stacks']
        if s['index'] in occupants and s['index'] != stack['index']), key=lambda s:s['index'])
    endpoints = {(origin['x'], origin['y']), (destination['x'], destination['y'])}
    basis['tiles'] = [deepcopy(origin), deepcopy(destination)]+sorted((deepcopy(t) for t in snapshot['tiles']
        if (t['x'], t['y']) in neighborhood-endpoints), key=lambda t:(t['x'], t['y']))
    basis['unit_profiles'] = sorted((deepcopy(p) for p in snapshot['unit_profiles'] if p['type'] in types), key=lambda p:p['type'])
    ap = [slot['ap'] for slot in occupied_slots(stack)]
    return dict(schema=PLAN_SCHEMA, candidate=deepcopy(candidate), basis=basis,
                basis_sha256=digest(basis), aim_tolerance=tolerance,
                selection=dict(stack_index=stack['index'], tile=[stack['x'], stack['y']],
                               point=tile_point(snapshot, framed, army, stack['x'], stack['y'], tolerance)),
                movement=dict(stack_index=stack['index'], origin=[stack['x'], stack['y']],
                              destination=[destination['x'], destination['y']],
                              point=tile_point(snapshot, framed, army, destination['x'], destination['y'], tolerance),
                              measured_cardinal_cost=cost, ap_before=ap, ap_after=[value-cost for value in ap],
                              one_click_may_execute=True),
                reachability_proven=False, runtime_executed=False,
                proof_scope='pure measured plan; no process, input, route, render or lifecycle proof')


def plan_input(snapshot, candidate, aim_tolerance=4):
    """Choose one measured friendly stack and an eligible cardinal neighbor."""
    framed, army, stacks, tiles, profiles = inspect(snapshot, candidate)
    integer(aim_tolerance, 0, 15, 'aim tolerance')
    choices = []
    for index, stack in sorted(stacks.items()):
        if (index == snapshot['context']['selected_stack'] or stack['owner'] != snapshot['player']['index']
                or stack['hidden'] or stack['queue_count']):
            continue
        origin = tiles.get((stack['x'], stack['y']))
        if origin is None or origin['occupant'] != index or not origin['visible']:
            continue
        try:
            occupied_slots(stack)
            plain_endpoint(snapshot, origin)
            tile_point(snapshot, framed, army, stack['x'], stack['y'], aim_tolerance)
        except PlanError:
            continue
        for order, (dx, dy) in enumerate(CARDINALS):
            destination = tiles.get((stack['x']+dx, stack['y']+dy))
            if destination is None:
                continue
            try:
                tile_point(snapshot, framed, army, destination['x'], destination['y'], aim_tolerance)
                cost = safe_cost(snapshot, stack, destination, profiles)
                neighborhood, occupants = ambush_neighborhood(snapshot, stack, destination, stacks, tiles)
            except PlanError:
                continue
            choices.append((cost, index, order, stack, origin, destination, neighborhood, occupants))
    require(bool(choices), 'no eligible friendly stack/cardinal pair in the measured records')
    cost, _, _, stack, origin, destination, neighborhood, occupants = min(choices, key=lambda row:row[:3])
    return _make(snapshot, candidate, aim_tolerance, stack, origin, destination, cost, framed, army, neighborhood, occupants)


def checked_plan(plan):
    record(plan, 'schema candidate basis basis_sha256 aim_tolerance selection movement reachability_proven runtime_executed proof_scope', 'plan')
    require(plan['schema'] == PLAN_SCHEMA and digest(plan['basis']) == plan['basis_sha256'], 'plan basis differs')
    require(plan['reachability_proven'] is False and plan['runtime_executed'] is False,
            'a pure plan cannot assert runtime reachability or execution')
    expected = plan_input(plan['basis'], plan['candidate'], plan['aim_tolerance'])
    require(plan == expected, 'plan fields do not reproduce from measured basis')
    return plan['basis']


def _bound(before, after):
    """Stable native/input geometry; selection ownership is checked separately."""
    require(after['sequence'] > before['sequence'], 'fresh ordered observation required')
    for key in ('identity', 'world', 'player', 'minimap', 'port'):
        require(after[key] == before[key], key+' changed since planning')
    changing = {'selected_stack', 'previous_stack', 'panel_stack', 'active_stack', 'lower_owner'}
    for key, value in before['context'].items():
        if key not in changing:
            require(after['context'][key] == value, 'native context changed: '+key)


def _pair(plan, snapshot):
    _, _, stacks, tiles, profiles = inspect(snapshot, plan['candidate'])
    index = plan['selection']['stack_index']
    require(index in stacks, 'planned stack measurement missing')
    coordinates = [(tile['x'], tile['y']) for tile in plan['basis']['tiles']]
    require(all(key in tiles for key in coordinates), 'planned tile measurement missing')
    basis = plan['basis']
    for neighbor in basis['stacks'][1:]:
        require(stacks.get(neighbor['index']) == neighbor, 'neighboring stack record changed')
    for profile in basis['unit_profiles']:
        require(profiles.get(profile['type']) == profile, 'movement profile changed')
    return stacks[index], [tiles[key] for key in coordinates]


def _selected(plan, snapshot):
    index = plan['selection']['stack_index']
    context = snapshot['context']
    require(context['selected_stack'] == index and context['panel_stack'] == index
            and context['lower_owner'] == 1
            and context['active_stack'] == context['game_data']+147174+725*index,
            'planned whole army does not own selection/panel')


def revalidate_before_click(plan, fresh, action):
    """Check a fresh coherent pre-click read; the caller still validates cursor."""
    basis = checked_plan(plan)
    require(action in ('select', 'move'), 'action must be select or move')
    stack, tiles = _pair(plan, fresh)
    _bound(basis, fresh)
    require(stack == basis['stacks'][0] and tiles == basis['tiles'], 'stack or relevant tile records changed before click')
    if action == 'select':
        for key in ('selected_stack', 'previous_stack', 'panel_stack', 'active_stack', 'lower_owner'):
            require(fresh['context'][key] == basis['context'][key], 'selection context changed before click')
    else:
        _selected(plan, fresh)
    framed, army = candidate_contract(plan['candidate'])
    coordinate = plan['selection']['tile'] if action == 'select' else plan['movement']['destination']
    point = tile_point(fresh, framed, army, *coordinate, plan['aim_tolerance'])
    expected = plan['selection']['point'] if action == 'select' else plan['movement']['point']
    require(point == expected, 'planned engine coordinate changed')
    return dict(action=action, stack_index=stack['index'], point=point,
                observation_sequence=fresh['sequence'], observation_sha256=digest(fresh),
                proof_scope='measured pre-click state only; cursor and actual input remain unverified')


def verify_selection(plan, before, after):
    """Require this action's exact selection transition, not any selected unit."""
    revalidate_before_click(plan, before, 'select')
    stack, tiles = _pair(plan, after)
    _bound(before, after)
    _selected(plan, after)
    require(before['context']['selected_stack'] != stack['index'], 'planned stack was already selected')
    # 408030 preserves the previous index; the ordinary 4084A0 branch stores
    # the old selection. This state-only verifier supports either native path.
    require(after['context']['previous_stack'] in (before['context']['previous_stack'], before['context']['selected_stack']),
            'previous selection changed outside either native selection contract')
    require(stack == plan['basis']['stacks'][0] and tiles == plan['basis']['tiles'], 'selection also changed stack/tile state')
    return dict(selection_state_transition=True, stack_index=stack['index'],
                before_sha256=digest(before), after_sha256=digest(after),
                proof_scope='observed selection state transition; ordinary input callback and rendering are separate')


def verify_movement(plan, before, after):
    """Require coordinates, both occupancy cells, every occupied AP, and queue."""
    revalidate_before_click(plan, before, 'move')
    stack, tiles = _pair(plan, after)
    _bound(before, after)
    _selected(plan, after)
    require(after['context']['previous_stack'] == before['context']['previous_stack'], 'movement changed previous selection')
    expected_stack = deepcopy(plan['basis']['stacks'][0])
    expected_stack['x'], expected_stack['y'] = plan['movement']['destination']
    for slot, expected_ap in zip(expected_stack['slots'], plan['movement']['ap_after']):
        slot['ap'] = expected_ap
    expected_tiles = deepcopy(plan['basis']['tiles'])
    expected_tiles[0]['occupant'] = EMPTY
    expected_tiles[1]['occupant'] = stack['index']
    require(stack == expected_stack, 'movement coordinates, slots, AP or final queue differ')
    require(tiles == expected_tiles, 'movement occupancy or relevant terrain differs')
    return dict(movement_state_transition=True, stack_index=stack['index'],
                origin=plan['movement']['origin'], destination=plan['movement']['destination'],
                charged_ap=plan['movement']['measured_cardinal_cost'],
                before_sha256=digest(before), after_sha256=digest(after),
                proof_scope='observed movement state transition; native return, ordinary input, rendering and lifecycle are separate')

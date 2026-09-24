#!/usr/bin/env python3
"""Compile and validate the separate hidden modal packet; never launch or write.

Full validation authenticates original/candidate, the entire producer packet,
and the entire generated command file before accepting its ordered trace.
An accepted trace only authorizes the host to read the paused memory surface;
it is not a screenshot, cleanup, visible/input or promotion acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import modal_primary_barracks_probe as producer
import modal_primary_initial_trace as initial_map_paint_trace
from modal_primary_candidate_context import strict_json_object
from render_cdb_surface_probe import render_probe, BASE_PROBE

HARNESS = Path(__file__).resolve().parents[1] / "scripts/cdb/run_cdb_surface_dump.ps1"
H = r"[0-9a-fA-F]{1,8}"
I = r"-?[0-9]{1,10}"
S = r"[a-z0-9_-]+"
SHA = r"[0-9a-f]{64}"
IDENTITY = rf"tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H})"
TI = rf"tid=(?P<tid>{H}) esp=(?P<esp>{H})"
SIZE = r"size=\((?P<width>[0-9]{1,4}),(?P<height>[0-9]{1,4})\)"
PATTERNS = {
    "MCAP_BYTE_CONTRACT_PASS": rf"candidate_sha256=(?P<sha>{SHA}) route=(?P<route>{S})",
    "MCAP_CONTRACT": rf"stage=(?P<stage>{S}) resolution=(?P<resolution>[0-9]{{3,4}}x[0-9]{{3,4}}) candidate_sha256=(?P<sha>{SHA}) route=(?P<route>{S}) availability=(?P<availability>{S}) castle_index=(?P<index>[0-3]) protocol=(?P<protocol>{S}) runtime_acceptance=0",
    "MCAP_MAP_HANDOFF": rf"{IDENTITY} render_hook=(?P<render_hook>{H}) lower=(?P<lower>{H}) post=(?P<post>{H}) surface=(?P<surface>{H}) {SIZE}",
    "MCAP_CASTLE_STATE": rf"index=(?P<index>[0-3]) ptr=(?P<owner_ptr>{H}) owner=(?P<owner>[0-9]) xy=\((?P<x>{I}),(?P<y>{I})\) flags=\((?P<flag0>{H}),(?P<flag4>{H})\) style=(?P<style>{I})",
    "MCAP_AVAILABILITY_FORCED": rf"flags=\((?P<flag0>{H}),(?P<flag4>{H})\) isolated_fixture=1",
    "MCAP_FORCE_CALL": rf"route=(?P<route>{S}) availability=(?P<availability>{S}) entry=(?P<entry>{H}) index=(?P<index>[0-3]) tid=(?P<tid>{H}) original_esp=(?P<esp>{H}) return_sentinel=(?P<sentinel>{H}) forced=1",
    "MCAP_OVERVIEW_PROLOGUE": rf"{IDENTITY} index=(?P<index>[0-3]) after_replayed_pushes=5 saved_ebx=(?P<saved_ebx>{H}) return_sentinel=(?P<sentinel>{H})",
    "MCAP_ARTWORK_ENTRY": rf"{IDENTITY} caller=(?P<caller>{H}) target=(?P<target>{H}) castle=(?P<owner_ptr>{H}) mode=(?P<mode>{I}) mask=(?P<mask>{I}) variant_byte=(?P<variant_byte>{I}) folder_player=(?P<folder_player>{I})",
    "MCAP_ARTWORK_RETURN": rf"{IDENTITY} castle=(?P<owner_ptr>{H}) variant_byte=(?P<variant_byte>{I})",
    "MCAP_OVERVIEW_PRESENT_CALL": rf"{TI} cursor_active=(?P<cursor_active>{I})",
    "MCAP_OVERVIEW_PRESENT_RETURN": IDENTITY,
    "MCAP_FORCED_DISPATCH": rf"route=(?P<route>{S}) branch=(?P<branch>{H}) skip_input_loop=1 old_render=(?P<old_render>{H}) new_render=(?P<new_render>{H})",
    "MCAP_FLIP_GATE_FORCED": rf"{TI} original=(?P<original>{H}) forced=1 callback=(?P<callback>{H}) command=(?P<command>{I})",
    "MCAP_CALLBACK_CALL": rf"{TI} callback=(?P<callback>{H}) owner=(?P<owner_ptr>{H}) render_hook=(?P<render_hook>{H})",
    "MCAP_SCREEN_ENTRY": rf"route=(?P<route>{S}) {IDENTITY} owner=(?P<owner_ptr>{H})",
    "MCAP_PRESENT_CALL": rf"route=(?P<route>{S}) {IDENTITY} cursor_active=(?P<cursor_active>{I})",
    "MCAP_PRESENT_RETURN": rf"route=(?P<route>{S}) {IDENTITY}",
    "MCAP_SURFDUMP_READY": rf"route=(?P<route>{S}) {IDENTITY} surface=(?P<surface>{H}) {SIZE} base=(?P<base>{H}) bytes=(?P<bytes>[0-9]{{1,9}}) owner=(?P<owner_ptr>{H}) render=(?P<render>{H}) primary=0051d4c0 primary_size=\((?P<primary_width>[0-9]{{1,4}}),(?P<primary_height>[0-9]{{1,4}})\) primary_vtable=(?P<primary_vtable>{H}) capture=owned_physical_mirror manual_input_proof=0",
    "MCAP_SURFDUMP_HOST_READY": "",
    "MCAP_CANVAS": rf"event=(?P<event>[A-Z_]+) {IDENTITY} state=(?P<state>{H}) phase=(?P<phase>{I}) root_esp=(?P<root_esp>{H}) physical=(?P<physical>{H}) native=(?P<native>{H}) physical_pixels=(?P<physical_pixels>{H}) native_pixels=(?P<native_pixels>{H}) allocations=(?P<allocations>{I}) frees=(?P<frees>{I}) mirrors=(?P<mirrors>{I}) enter=(?P<enter_status>{I}) mirror=(?P<mirror_status>{I}) leave=(?P<leave_status>{I}) fault=(?P<fault>{I}) native_size=\((?P<native_width>[0-9]{{1,4}}),(?P<native_height>[0-9]{{1,4}})\) physical_size=\((?P<physical_width>[0-9]{{1,4}}),(?P<physical_height>[0-9]{{1,4}})\) native_com=(?P<native_com>{H}) eax=(?P<eax>{H}) caller=(?P<caller>{H})",
}
REGEX = {name: re.compile(name + (" " + tail if tail else "")) for name, tail in PATTERNS.items()}
HEX_FIELDS = {"tid", "eip", "esp", "render_hook", "lower", "post", "surface", "owner_ptr", "flag0", "flag4",
              "entry", "sentinel", "branch", "old_render", "new_render", "original", "callback", "base", "render", "primary_vtable", "saved_ebx",
              "state","root_esp","physical","native","physical_pixels","native_pixels","native_com","eax","caller","target"}
TEXT_FIELDS = {"sha", "route", "stage", "resolution", "availability", "event", "protocol"}
LIMITS = [
    "Four exact native checkpoint prefixes are separate from a completed first-present trace; the first contains zero slot copies and an unfinished native full-blit call.",
    "All initial-map PTILE records keep their primary stage and raw values. No inherited recipe or log is projected into another stage.",
    "Installed full-publish/cursor and placeholder calls are route observations, not pixel correctness; the selected-panel branch remains unexercised.",
    "Accepted source-bound trace permits a paused host memory read only; screenshot correctness and complete modal composition are unproven here.",
    "The original map READY/visibility snapshot is diagnostic, never the modal host-capture trigger.",
    "Forced native case dispatch and gate results are retained; existing flags do not establish natural availability or manual input.",
    "Primary-only layers, host deadline/process identity/cleanup, final wrapper composition, input and promotion require separate evidence.",
    "Every raw modal record, including malformed or rejected observations, is retained without deduplication.",
    "The capture is from the state-bound physical mirror while E0 remains native640; primary-only modal layers may be absent.",
    "The intentional phase1 first-present stop cannot establish native exit restoration, destructor execution or whole-lifecycle runtime correctness.",
    "The native artwork chain records both unconditional loads and the third iff castle byte4 equals1; the separate owner-player style observation is not used as that selector.",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Match the actual anchored debugger diagnostics recognized by the primary
# host. Quoted/echoed command source is not a debugger failure observation.
DEBUGGER_COMMAND_FAILURE = re.compile(
    r'(?i)^\s*(?:[0-9]+:[0-9]+>\s*)?(?:Unable to insert breakpoint\b|bp[0-9]+\s+at\s+[^\r\n]*\bfailed\b|(?:\^\s*)?Syntax error\b|Command file execution failed\b)')


def _startup_fragments():
    data = HARNESS.read_bytes()
    source = data.decode("utf-8-sig").replace("\r\n", "\n")
    block = re.search(r"elseif \(\$FastForwardStartAnims\) \{\n    @\(\n(.*?)\n    \) -join", source, re.S)
    if not block:
        raise ValueError("fixed startup-animation source block is missing")
    rows = re.findall(r"^        '([^\n]*)'$", block[1], re.M)
    if len(rows) != 6 or len([row for row in rows if row.startswith("bp ")]) != 5:
        raise ValueError("fixed five-breakpoint startup-animation recipe changed")
    pre = re.findall(r"^    '(ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__;[^\n]*)'$", source, re.M)
    if len(pre) != 1:
        raise ValueError("fixed ordinary pre-entry load-coordinate source is missing")
    return "\n".join(row.replace("''", "'") for row in rows), pre[0].replace("''", "'")


def compile_probe(packet: dict) -> str:
    """Assemble an authenticated producer packet using one fixed host recipe.

    Call full evaluate_trace before host capture. This compiler itself does
    not accept arbitrary packet content as source/candidate authentication.
    """
    fast, pre = _startup_fragments()
    text = packet["map_probe_template"].replace("\r\n", "\n")
    if text.count(producer.DUMP_TOKEN) != 1 or text.count("bc *\n") != 1 or len(re.findall(r"(?m)^g$", text)) != 1:
        raise ValueError("map template insertion contract differs")
    geometry = render_probe(BASE_PROBE.read_text(encoding="utf-8-sig"), packet["resolution"], producer.MAP_STAGE)["geometry"]
    replacements = {
        "__START_ANIMS_BP__": fast,
        "__PRE_ENTRY_LOAD_COORD_ACTION__": pre,
        "__LOAD_SLOT__": "0",
        "__LOAD_MOUSE_RAW_X__": f"{geometry['load_mouse'][0] << 6:08x}",
        "__LOAD_MOUSE_RAW_Y__": f"{geometry['load_mouse'][1] << 6:08x}",
        "__VISIBILITY_PLAYGAME_ACTION__": "",
        "__VISIBILITY_PATCH_ACTION__": "",
        producer.DUMP_TOKEN: packet["handoff_action"],
    }
    for old, new in replacements.items():
        if old not in text:
            raise ValueError(f"required canonical token missing: {old}")
        text = text.replace(old, new)
    text = text.replace("bc *\n", "bc *\n" + packet["byte_checks_before_first_breakpoint"])
    text = re.sub(r"(?m)^g$", lambda _: packet["startup_commands_before_final_g"] + "g", text)
    if re.search(r"__[A-Z0-9_]+__", text):
        raise ValueError("unresolved command-file substitution")
    if any(len(line) >= 4096 for line in text.splitlines()):
        raise ValueError("compiled command file exceeds CDB4096-byte line limit")
    # All explicit and implicit IDs/sites are inventoried after expansion.
    occupied, sites = set(), set()
    for line in text.splitlines():
        match = re.match(r'^bp\s*(?:(\d+)\s+)?([0-9a-fA-F]{8})\s+"', line)
        if match:
            number = int(match[1]) if match[1] else next(i for i in range(1000) if i not in occupied)
            va = int(match[2], 16)
            if number in occupied or va in sites:
                raise ValueError("compiled command-file breakpoint collision")
            occupied.add(number); sites.add(va)
    return text


def _validate_canvas(rows, packet, hand, ready, artwork, require, *, checkpoint=None, prior_base=None):
    """Literal native ABI deltas plus immutable allocation identity; no dedup."""
    name=packet['route']['name'];route=producer.ROUTES[name]
    width,height=map(int,packet['resolution'].split('x'))
    stack=hand.get('esp',0);tid=hand.get('tid')
    observers=packet.get('canvas_observer_vas',{})
    plan=[('ENTER',observers.get('root_after_replayed_pushes'),24,0),
          ('LOAD_CALL',0x4020A0,452,0),('OVERVIEW_LOAD_RETURN',0x4213C2,448,0),
          ('LOAD_CALL',0x4020A0,452,0),('OVERVIEW_SECOND_LOAD_RETURN',0x4214DC,448,0)]
    if artwork.get('variant_byte')==1:
        plan += [('LOAD_CALL',0x4020A0,452,0),('OVERVIEW_THIRD_LOAD_RETURN',0x42154A,448,0)]
    plan += [('BLIT_CALL',0x401E30,136,0),('OVERVIEW_BLIT_RETURN',0x4220C6,132,1),
             ('OVERVIEW_DRAW_RETURN',observers.get('overview_after_native_draw'),100,2)]
    # Root native ESP H-60; CALL wrapper plus PUSHAD plus draw adapter CALL
    # yields draw entry H-100. Its replayed five pushes+SUB8 and native CALL
    # yield blit H-136. Nested421240 saves312 additional bytes before loader.
    if name!='castle_overview':
        depth=64+route.local_stack_bytes
        plan += [('LOAD_CALL',0x4020A0,depth+4,2),
                 ('FACILITY_LOAD_RETURN',producer.LOAD_CALLS[name]+3,depth,2),
                 ('BLIT_CALL',0x401E30,depth+4,2),
                 ('FACILITY_BLIT_RETURN',producer.BLIT_CALLS[name]+3,depth,3)]
    plan += [('READY',route.stop_va,60 if name=='castle_overview' else 64+route.local_stack_bytes,
              2 if name=='castle_overview' else 3)]
    if checkpoint == 'full-published':
        plan = plan[:-2]  # facility BLIT_CALL has entered, return is still pending
    elif checkpoint in ('placeholder-before', 'placeholder-after'):
        plan = plan[:-1]  # native facility blit returned; final present is pending
    actual=[(r['values'] or {}).get('event') for r in rows]
    require(actual==[r[0] for r in plan],'canvas observations missing, repeated or out of order','MCAP_CANVAS')
    first=(rows[0].get('values') or {}) if rows else {}
    identities=tuple(first.get(k) for k in ('physical','native','physical_pixels','native_pixels'))
    require(identities[0]==hand.get('surface') and identities[2]==(prior_base if checkpoint not in (None,'final-ready') else ready.get('base')),
            'owned physical mirror differs from handoff/capture','MCAP_CANVAS')
    load_index=0
    for row, (event,eip,depth,mirrors) in zip(rows,plan):
        v=row.get('values') or {}
        require((v.get('event'),v.get('tid'),v.get('eip'),v.get('esp'),v.get('state'),v.get('root_esp'))
                ==(event,tid,eip,stack-depth,packet.get('canvas_state_va'),stack-4)
                and 0<stack-depth<=0xFFFFFFFF and (stack-depth)%4==0,
                f'{event} native thread/EIP/stack/state binding differs','MCAP_CANVAS')
        require((v.get('phase'),v.get('allocations'),v.get('frees'),v.get('enter_status'),v.get('leave_status'),v.get('fault'))
                ==(1,1,0,1,0,0) and v.get('mirrors')==mirrors and v.get('mirror_status')==(1 if mirrors else 0),
                f'{event} active ownership/counters/fault differ','MCAP_CANVAS')
        values=tuple(v.get(k) for k in ('physical','native','physical_pixels','native_pixels'))
        require(values==identities and all(type(x) is int and 0<x<=0xFFFFFFFF for x in values)
                and values[0]!=values[1],f'{event} canvas identity changed or aliased','MCAP_CANVAS')
        pp,np=v.get('physical_pixels',0),v.get('native_pixels',0)
        require(type(pp) is int and type(np) is int and 0<pp<=0x100000000-width*height
                and 0<np<=0x100000000-307200 and (pp+width*height<=np or np+307200<=pp),
                f'{event} pixel ranges wrap or overlap','MCAP_CANVAS')
        require((v.get('native_width'),v.get('native_height'),v.get('physical_width'),v.get('physical_height'),v.get('native_com'))
                ==(640,480,width,height,0),f'{event} native/physical dimensions or COM ownership differ','MCAP_CANVAS')
        if event=='ENTER':
            require(v.get('eax')==packet['castle_index'],'root index differs after replayed prologue','MCAP_CANVAS')
        if event in ('LOAD_CALL','BLIT_CALL'):
            current='castle_overview' if mirrors==0 else name
            if event=='LOAD_CALL' and mirrors==0:
                caller=producer.ARTWORK_CALLS[load_index]+3;load_index+=1
            else:caller=(producer.LOAD_CALLS if event=='LOAD_CALL' else producer.BLIT_CALLS)[current]+3
            require(v.get('eax')==v.get('native') and v.get('caller')==caller,
                    f'{event} is not the authenticated native-canvas call','MCAP_CANVAS')


def evaluate_sequence(log: str, packet: dict, *, checkpoint=None) -> dict:
    """Ordered-log diagnosis only, without authenticating any external bytes."""
    failures, rows = [], []
    debugger_records = []
    if checkpoint not in (None, 'full-published', 'placeholder-before', 'placeholder-after', 'final-ready'):
        return dict(sequence_passed=False, failures=['unsupported primary checkpoint'], raw_records=[], surface=None,
                    source_authenticated=False, ready_for_host_capture=False)
    def fail(message, line=None):
        failures.append((f"line {line}: " if line else "") + message)
    if not isinstance(packet,dict) or not isinstance(packet.get('route'),dict):
        return dict(sequence_passed=False, failures=["packet must contain a route object"], raw_records=rows, surface=None,
                    source_authenticated=False,ready_for_host_capture=False)
    name = packet["route"].get("name")
    route = producer.ROUTES.get(name)
    if name != 'barracks' or route is None or packet.get("stage") != producer.STAGE or packet.get('protocol_revision') != producer.PROTOCOL_REVISION:
        return dict(sequence_passed=False, failures=["unsupported route/stage/protocol packet"], raw_records=rows, surface=None,
                    source_authenticated=False,ready_for_host_capture=False)
    dimensions = re.fullmatch(r"([1-9][0-9]{2,3})x([1-9][0-9]{2,3})", packet.get("resolution", ""))
    if not dimensions:
        return dict(sequence_passed=False, failures=["invalid packet resolution"], raw_records=rows, surface=None,
                    source_authenticated=False,ready_for_host_capture=False)
    width,height=map(int,dimensions.groups())
    for number, text in enumerate(log.splitlines(), 1):
        if DEBUGGER_COMMAND_FAILURE.search(text):
            debugger_records.append(dict(line=number, text=text, classification='debugger_command_failure'))
            fail('debugger command failure', number)
        if re.search(r"AV_SURFDUMP|SURFDUMP_INVALID|PTILE_REJECT|MCAP_REJECT|MCANVAS_CONTRACT_FAIL|SLOTS_CONTRACT_FAIL|MPRIMARY_CONTRACT_FAIL|ARMY_CONTRACT_FAIL|\bMODAL_|syntax error|couldn't resolve", text, re.I):
            fail("runtime/probe rejection or debugger error", number)
        if re.search(r"MCAP_", text, re.I):
            marker = text.split(" ",1)[0]
            match = REGEX.get(marker)
            match = match.fullmatch(text) if match else None
            row = dict(line=number, marker=marker, text=text, values=None)
            if not match:
                fail("unknown, malformed or prefixed modal record",number)
            else:
                row["values"] = {key: value if key in TEXT_FIELDS else int(value,16 if key in HEX_FIELDS else 10)
                                 for key,value in match.groupdict().items()}
            rows.append(row)
        elif re.search(r"\bSURFDUMP_HOST_READY\b", text):
            fail("ordinary-map host-ready marker is forbidden in the modal lane",number)
    inherited_success=[dict(line=n,text=t) for n,t in enumerate(log.splitlines(),1)
                       if re.search(r'(?:SLOTS|ARMY|COMPLETEHD|MCANVAS)_CONTRACT_PASS',t,re.I)]
    for record in inherited_success:
        fail('inherited stage success marker is forbidden in primary lane',record['line'])
    state_va=packet.get('canvas_state_va')
    if type(state_va) is not int:
        fail('missing canvas state address');state_va=0
    loaded_contract=(f"MPRIMARY_CONTRACT_PASS stage={producer.STAGE} resolution={packet['resolution']} "
                     f"candidate_sha256={packet.get('candidate_sha256')} revision={producer.builder.REVISION}")
    loaded_scope="MPRIMARY_SCOPE owned_modal_primary primary_composition_proven=false manual_input_proof=false promotion_ready=false"
    # Admit every occurrence of the reserved startup namespace, including
    # prefixed/malformed records. Exact markers avoid treating the legitimate
    # protocol=primary_barracks_owned_canvas_v1 field as a startup record.
    canvas_startup=[(n,t) for n,t in enumerate(log.splitlines(),1) if re.search(r'MPRIMARY_',t,re.I)]
    if [t for _,t in canvas_startup] != [loaded_contract,loaded_scope]:
        fail('primary loaded contract/scope missing, repeated, malformed or mismatched')
    elif not rows or canvas_startup[-1][0]>=next((r['line'] for r in rows if r['marker']=='MCAP_CONTRACT'),0):
        fail('primary loaded contract must precede modal startup contract')
    elif next((r['line'] for r in rows if r['marker']=='MCAP_BYTE_CONTRACT_PASS'),10**9)>=canvas_startup[0][0]:
        fail('native-route byte contract must precede primary loaded contract')
    expected = ["MCAP_BYTE_CONTRACT_PASS","MCAP_CONTRACT","MCAP_MAP_HANDOFF","MCAP_CASTLE_STATE"]
    if packet.get("availability") == "construct_all": expected.append("MCAP_AVAILABILITY_FORCED")
    elif packet.get("availability") != "existing_flags": fail("invalid explicit availability option")
    artwork_rows=[row for row in rows if row['marker']=='MCAP_ARTWORK_ENTRY']
    artwork=(artwork_rows[0].get('values') or {}) if artwork_rows else {}
    expected += ["MCAP_FORCE_CALL","MCAP_OVERVIEW_PROLOGUE","MCAP_CANVAS","MCAP_ARTWORK_ENTRY"]
    expected += ["MCAP_CANVAS"]*(6 if artwork.get('variant_byte')==1 else 4)
    expected += ["MCAP_ARTWORK_RETURN"]+["MCAP_CANVAS"]*3+["MCAP_OVERVIEW_PRESENT_CALL","MCAP_OVERVIEW_PRESENT_RETURN"]
    if name != "castle_overview":
        expected += ["MCAP_FORCED_DISPATCH","MCAP_FLIP_GATE_FORCED","MCAP_CALLBACK_CALL","MCAP_SCREEN_ENTRY"] + ["MCAP_CANVAS"]*4 + ["MCAP_PRESENT_CALL","MCAP_PRESENT_RETURN"]
    expected += ["MCAP_CANVAS","MCAP_SURFDUMP_READY","MCAP_SURFDUMP_HOST_READY"]
    if checkpoint == 'full-published':
        expected = expected[:-6]  # through the facility BLIT_CALL, before its return
    elif checkpoint in ('placeholder-before', 'placeholder-after'):
        expected = expected[:-5]  # through FACILITY_BLIT_RETURN
    native_rows=[r for r in rows if not (r['marker']=='MCAP_CANVAS' and (r.get('values') or {}).get('event')=='CHECKPOINT')]
    if [row["marker"] for row in native_rows] != expected:
        fail("modal sequence is missing, duplicated, out of order or contains extra records")
    # First observations may aid diagnosis of a failed trace, but a duplicate
    # above remains a failure and every original row remains in raw_records.
    by_name = {}
    for row in rows:
        if row["values"] is not None: by_name.setdefault(row["marker"],row)
    def values(marker): return by_name.get(marker,{}).get("values",{})
    def require(condition,message,marker):
        if marker not in expected:
            return  # Later events are required only at their named native stop.
        if not condition: fail(message,by_name.get(marker,{}).get("line"))
    for marker in ("MCAP_BYTE_CONTRACT_PASS","MCAP_CONTRACT"):
        data=values(marker)
        require(data.get('sha')==packet.get('candidate_sha256') and data.get('route')==name,"loaded candidate/route contract differs",marker)
    contract=values('MCAP_CONTRACT')
    require(contract.get('protocol')==producer.PROTOCOL_REVISION,'native artwork protocol revision differs','MCAP_CONTRACT')
    require(all(contract.get(k)==packet.get(k) for k in ('stage','resolution','availability')) and contract.get('index')==packet.get('castle_index'),
            'stage/resolution/availability/castle contract differs','MCAP_CONTRACT')
    hand=values('MCAP_MAP_HANDOFF'); tid=hand.get('tid'); stack=hand.get('esp',0)
    require(tid and 0<stack<=0xFFFFFFFF and stack%4==0 and hand.get('eip')==0x406FA0,
            'map handoff site/thread/stack is invalid','MCAP_MAP_HANDOFF')
    require((hand.get('render_hook'),hand.get('lower'),hand.get('post'))==(0x40AD40,0,0)
            and (hand.get('width'),hand.get('height'))==(width,height) and hand.get('surface'),
            'map owner or physical surface differs','MCAP_MAP_HANDOFF')
    closes=[]
    for number,text in enumerate(log.splitlines(),1):
        if text.startswith('PTILE_TRACE_CLOSED'):
            match=re.fullmatch(rf'PTILE_TRACE_CLOSED {IDENTITY}',text)
            if match: closes.append((number,{k:int(v,16) for k,v in match.groupdict().items()}))
    require(len(closes)==1 and closes[0][1]==dict(tid=tid,eip=0x406FA0,esp=stack)
            and by_name.get('MCAP_CONTRACT',{}).get('line',10**9)<closes[0][0]<by_name.get('MCAP_MAP_HANDOFF',{}).get('line',0),
            'one matching completed map-trace closure must precede modal handoff','MCAP_MAP_HANDOFF')
    castle=values('MCAP_CASTLE_STATE'); owner=castle.get('owner_ptr')
    require(castle.get('index')==packet.get('castle_index') and owner and 0<owner<=0xFFFFFFFF-0x1A4
            and 0<=castle.get('owner',99)<=4 and 0<=castle.get('x',-1)<100 and 0<=castle.get('y',-1)<100
            and 0<=castle.get('flag0',999)<=255 and 0<=castle.get('flag4',999)<=255
            and -0x80000000<=castle.get('style',2**32)<=0x7FFFFFFF,
            'castle owner/state observation is invalid','MCAP_CASTLE_STATE')
    # The original map snapshot remains diagnostic, but its exact physical
    # identity and visibility observation must survive the handoff unchanged.
    prior=[(n,text) for n,text in enumerate(log.splitlines(),1) if text.startswith('SURFDUMP_READY')]
    prior_pattern=re.compile(rf'SURFDUMP_READY redraw_seq=4 surface=({H}) size=\(([0-9]{{1,4}}),([0-9]{{1,4}})\) base=({H}) bytes=([0-9]{{1,9}})')
    prior_match=prior_pattern.fullmatch(prior[0][1]) if len(prior)==1 else None
    if prior_match:
        surface,pw,ph,base,count=prior_match.groups()
        valid=(int(surface,16)==hand.get('surface') and (int(pw),int(ph),int(count))==(width,height,width*height)
               and 0<int(base,16)<=0x100000000-width*height and bool(closes) and prior[0][0]<closes[0][0])
    else: valid=False
    require(valid,'one exact prior map snapshot must precede trace closure','MCAP_MAP_HANDOFF')
    visibility=[(n,text) for n,text in enumerate(log.splitlines(),1) if text.startswith('SCROLL_VISDUMP')]
    visibility_pattern=re.compile(rf'SCROLL_VISDUMP player=0 screen0=\(32,16\) map0=\(([0-9]{{1,3}}),([0-9]{{1,3}})\) rows=([0-9]{{1,3}}) cols=([0-9]{{1,3}}) tile=\(64,64\) vis_base=({H}) dump_start=({H}) count=([0-9]{{1,5}})')
    vis_match=visibility_pattern.fullmatch(visibility[0][1]) if len(visibility)==1 else None
    if vis_match and owner:
        sx,sy,rows_count,cols,vis_base,dump,count=vis_match.groups()
        sx,sy,rows_count,cols,count=map(int,(sx,sy,rows_count,cols,count))
        expected_cols,expected_rows=(width-64+63)//64,(height-32+63)//64
        gd=owner-0x7C6EA-packet['castle_index']*467
        valid=(cols==expected_cols and rows_count==expected_rows and sx+cols<=100 and sy+rows_count<=100
               and gd>0 and int(vis_base,16)==gd+0x22331
               and int(dump,16)==int(vis_base,16)+sx*13+(sy>>3)
               and count==(cols-1)*13+((sy+rows_count-1)>>3)-(sy>>3)+1
               and bool(prior) and bool(closes) and prior[0][0]<visibility[0][0]<closes[0][0])
    else: valid=False
    require(valid,'prior ceiling-window visibility observation is missing or mismatched','MCAP_MAP_HANDOFF')
    if packet.get('availability')=='construct_all':
        flags=values('MCAP_AVAILABILITY_FORCED')
        require((flags.get('flag0'),flags.get('flag4'))==(31,1) and castle.get('flag0',255)&0xE0==0
                and castle.get('flag4',255)&0xFE==0,'constructed availability differs or overwrites unreviewed flags','MCAP_AVAILABILITY_FORCED')
    forced=values('MCAP_FORCE_CALL')
    require((forced.get('route'),forced.get('availability'),forced.get('entry'),forced.get('index'),forced.get('tid'),forced.get('esp'),forced.get('sentinel'))
            ==(name,packet.get('availability'),0x422180,packet.get('castle_index'),tid,stack,0x406FA1),
            'forced native call identity differs','MCAP_FORCE_CALL')
    identities = {
        'MCAP_OVERVIEW_PROLOGUE':(packet.get('canvas_observer_vas',{}).get('root_after_replayed_pushes'),stack-24),
        'MCAP_OVERVIEW_PRESENT_CALL':(None,stack-60),
        'MCAP_OVERVIEW_PRESENT_RETURN':(0x42239F,stack-60),
    }
    entry=values('MCAP_OVERVIEW_PROLOGUE')
    require(entry.get('index')==packet.get('castle_index') and entry.get('sentinel')==0x406FA1,
            'overview prologue index or return sentinel differs','MCAP_OVERVIEW_PROLOGUE')
    canvas_enter=next((r.get('values') or {} for r in rows if r['marker']=='MCAP_CANVAS'),{})
    require((artwork.get('tid'),artwork.get('eip'),artwork.get('esp'),artwork.get('caller'),
             artwork.get('target'),artwork.get('owner_ptr'),artwork.get('mode'),artwork.get('mask'))
            ==(tid,0x421240,stack-136,0x422043,canvas_enter.get('native'),owner,0,0)
            and 0<=artwork.get('variant_byte',-1)<=255 and 0<=artwork.get('folder_player',-1)<=4,
            'native artwork entry/caller/arguments/branch selector differs','MCAP_ARTWORK_ENTRY')
    returned=values('MCAP_ARTWORK_RETURN')
    require((returned.get('tid'),returned.get('eip'),returned.get('esp'),returned.get('owner_ptr'),returned.get('variant_byte'))
            ==(tid,0x422043,stack-132,owner,artwork.get('variant_byte')),
            'native artwork return/stack/branch selector differs','MCAP_ARTWORK_RETURN')
    if name != 'castle_overview':
        dispatch=values('MCAP_FORCED_DISPATCH')
        require(dispatch.get('route')==name and dispatch.get('branch')==route.branch_va and dispatch.get('new_render'),
                'forced native case branch differs','MCAP_FORCED_DISPATCH')
        gate=values('MCAP_FLIP_GATE_FORCED')
        require((gate.get('callback'),gate.get('command'))==(route.entry_va,route.command),'native gate command/callback differs','MCAP_FLIP_GATE_FORCED')
        call=values('MCAP_CALLBACK_CALL')
        require((call.get('callback'),call.get('owner_ptr'),call.get('render_hook'))==(route.entry_va,owner,0x4617A0),
                'native callback ABI/owner differs','MCAP_CALLBACK_CALL')
        require(values('MCAP_SCREEN_ENTRY').get('owner_ptr')==owner,'screen entry owner differs','MCAP_SCREEN_ENTRY')
        identities.update({
            'MCAP_FLIP_GATE_FORCED':(None,stack-60), 'MCAP_CALLBACK_CALL':(None,stack-60),
            'MCAP_SCREEN_ENTRY':(route.entry_va,stack-64),
            'MCAP_PRESENT_CALL':(route.present_call_va,stack-64-route.local_stack_bytes),
            'MCAP_PRESENT_RETURN':(route.stop_va,stack-64-route.local_stack_bytes),
        })
    capture_stack=stack-60 if name=='castle_overview' else stack-64-route.local_stack_bytes
    identities['MCAP_SURFDUMP_READY']=(route.stop_va,capture_stack)
    for marker,(eip,esp) in identities.items():
        data=values(marker)
        require(data.get('tid')==tid and data.get('esp')==esp and 0<esp<=0xFFFFFFFF and esp%4==0
                and (eip is None or data.get('eip')==eip),'native thread/EIP/returned stack differs',marker)
    for row in rows:
        data=row['values'] or {}
        if 'route' in data: require(data['route']==name,'record route differs',row['marker'])
    ready=values('MCAP_SURFDUMP_READY')
    require((ready.get('width'),ready.get('height'),ready.get('bytes'))==(width,height,width*height)
            and ready.get('surface')==hand.get('surface') and ready.get('owner_ptr')==owner
            and ready.get('base',0)>0 and ready.get('base',0)+width*height<=0x100000000,
            'final physical memory surface/dimensions/owner differ','MCAP_SURFDUMP_READY')
    require(bool(prior_match) and ready.get('base')==int(prior_match.group(4),16),
            'physical pixel identity differs from prior map snapshot','MCAP_SURFDUMP_READY')
    require((ready.get('primary_width'),ready.get('primary_height'),ready.get('primary_vtable'))==(width,height,0x50EEC4),
            'physical primary ABI observation differs','MCAP_SURFDUMP_READY')
    require(ready.get('render')==canvas_enter.get('native'),'final render device is not restored to native canvas','MCAP_SURFDUMP_READY')
    canvas_rows=[r for r in native_rows if r['marker']=='MCAP_CANVAS']
    _validate_canvas(canvas_rows,packet,hand,ready,artwork,require,checkpoint=checkpoint,
                     prior_base=int(prior_match.group(4),16) if prior_match else None)
    surface={key:ready.get(key) for key in ('surface','width','height','base','bytes','route','tid','eip','esp','owner_ptr')}
    surface['owner']=surface.pop('owner_ptr')
    result = dict(sequence_passed=not failures,source_authenticated=False,ready_for_host_capture=False,
                failures=failures,raw_records=rows,surface=surface if ready else None,
                forced_gate_original=values('MCAP_FLIP_GATE_FORCED').get('original'),
                manual_input_proof=False,promotion_ready=False,limits=LIMITS)
    if debugger_records:
        result['debugger_failure_records'] = debugger_records
    if inherited_success:
        result['forbidden_stage_records'] = inherited_success
    if [t for _,t in canvas_startup] != [loaded_contract,loaded_scope]:
        result['primary_startup_records'] = [dict(line=n,text=t) for n,t in canvas_startup]
    return result


def evaluate_slots(log,packet,sequence, *, checkpoint=None):
    """Twelve exact initial calls, preserving every malformed/extra observation."""
    rows=[];failures=[]
    pattern=re.compile(r"SCAP_SLOT_COPY tid=(?P<tid>[0-9a-fA-F]+) eip=(?P<eip>[0-9a-fA-F]+) esp=(?P<esp>[0-9a-fA-F]+) source=(?P<source>[0-9a-fA-F]+) x=(?P<x>-?[0-9]+) y=(?P<y>-?[0-9]+) right=(?P<right>-?[0-9]+) bottom=(?P<bottom>-?[0-9]+) dest_x=(?P<dest_x>-?[0-9]+) dest_y=(?P<dest_y>-?[0-9]+) return=(?P<return>[0-9a-fA-F]+) producer_return=(?P<producer_return>[0-9a-fA-F]+)")
    hexes={'tid','eip','esp','source','return','producer_return'}
    for number,line in enumerate(log.splitlines(),1):
        if 'SCAP_' not in line.upper():continue
        match=pattern.fullmatch(line);values=None
        if not match:failures.append(f'line {number}: malformed/unknown slot record')
        else:values={k:int(v,16 if k in hexes else 10) for k,v in match.groupdict().items()}
        rows.append(dict(line=number,text=line,values=values))
    count = 0 if checkpoint == 'full-published' else 12
    if len(rows)!=count:failures.append(f'exactly {count} slot-copy observations required at this stop; duplicates are failures')
    modal=sequence.get('raw_records',[])
    def event(marker,event=None):
        found=[r for r in modal if r['marker']==marker and (event is None or (r.get('values') or {}).get('event')==event)]
        return found[0] if len(found)==1 else {'line':0,'values':{}}
    hand=event('MCAP_MAP_HANDOFF');ready=event('MCAP_CANVAS','READY')
    before=event('MCAP_CANVAS','FACILITY_BLIT_RETURN')['line'];after=(len(log.splitlines())+1 if checkpoint in ('placeholder-before','placeholder-after') else event('MCAP_PRESENT_CALL')['line'])
    rect_lines=[n for n,line in enumerate(log.splitlines(),1) if line.startswith('MPCAP_CURSOR_RECT ')]
    if len(rect_lines)==1:after=min(after,rect_lines[0])
    hv=hand.get('values') or {};rv=ready.get('values') or {}
    if checkpoint in ('placeholder-before','placeholder-after'):
        entered=event('MCAP_CANVAS','ENTER');rv=entered.get('values') or {}
    for index,row in enumerate(rows):
        v=row['values'] or {};x=126+71*(index%6);y=75+131*(index//6)
        expected=dict(tid=hv.get('tid'),eip=packet.get('slot_entry_vas',{}).get('after_dirty_copy'),
            esp=hv.get('esp',0)-212,source=rv.get('native'),x=x,y=y,right=x+32,bottom=y+64,
            dest_x=x,dest_y=y,**{'return':0x432C10,'producer_return':0x432DE7})
        if v!=expected or not before<row['line']<after:
            failures.append(f"line {row['line']}: slot order/geometry/thread/stack/caller or native ownership differs")
    return dict(passed=not failures,raw_records=rows,failures=failures,primary_composition_proven=False)


CHECKPOINT_NAMES = ('full-published','placeholder-before','placeholder-after','final-ready')
PRIMARY_PATTERNS = {
    'MPCAP_PRIMARY_OBSERVERS_ARM': '',
    'MPCAP_EVENT': rf'event=(?P<event>[a-z-]+) {IDENTITY} full_esp=(?P<full_esp>{H}) route_state=(?P<route_state>[28]) cursor=(?P<cursor>{I}) eax=(?P<eax>{H}) caller=(?P<caller>{H}) parent=(?P<parent>{H})',
    'MPCAP_CHECKPOINT': rf'name=(?P<name>[a-z-]+) index=(?P<index>[0-3]) {IDENTITY} surface=(?P<surface>{H}) {SIZE} base=(?P<base>{H}) bytes=(?P<bytes>[0-9]{{1,9}}) owner=(?P<owner>{H}) render=(?P<render>{H}) cursor=(?P<cursor>{I})',
    'MPCAP_HOST_READY': r'name=(?P<name>[a-z-]+)',
    'MPCAP_CHECKPOINT_REQUEST': r'name=(?P<name>[a-z-]+)',
    'MPCAP_CURSOR_RECT': rf'{IDENTITY} eax=(?P<eax>{H}) x=(?P<x>{I}) right=(?P<right>{I}) y=(?P<y>{I}) bottom=(?P<bottom>{I}) caller=(?P<caller>{H}) cursor=(?P<cursor>{I})',
    'MPCAP_CURSOR_RECT_CONTEXT': rf'{IDENTITY} ebp=(?P<ebp>{H}) eax=(?P<eax>{H}) x=(?P<x>{I}) right=(?P<right>{I}) y=(?P<y>{I}) bottom=(?P<bottom>{I}) caller=(?P<caller>{H}) expected_tid=(?P<expected_tid>{H}) root_esp=(?P<root_esp>{H}) route_state=(?P<route_state>{I}) canvas_phase=(?P<canvas_phase>{I}) publish_phase=(?P<publish_phase>{I}) checkpoint_index=(?P<checkpoint_index>{I}) selected=(?P<selected>{H}) cursor=(?P<cursor>{I}) resource=(?P<resource>{H}) render=(?P<render>{H}) state_phase=(?P<state_phase>{I}) state_fault=(?P<state_fault>{I})',
    'MPCAP_REJECT': r'reason=(?P<reason>[a-z_]+)',
    'MPCAP_PLACEHOLDER': rf'{IDENTITY} primary=(?P<primary>{H}) vtable=(?P<vtable>{H}) sprite=(?P<sprite>{H}) resource=(?P<resource>{H}) index=(?P<index>25) x=(?P<x>{I}) y=(?P<y>{I}) {SIZE} parent=(?P<parent>{H}) args=\((?P<arg0>{H}),(?P<arg1>{H}),(?P<arg2>{H}),(?P<arg3>{H}),(?P<arg4>{H}),(?P<arg5>{H}),(?P<arg6>{H})\)',
}
PRIMARY_REGEX={k:re.compile(k+(' '+v if v else '')) for k,v in PRIMARY_PATTERNS.items()}
PRIMARY_HEX=HEX_FIELDS|{'full_esp','parent','owner','primary','vtable','sprite','resource','ebp','expected_tid','selected'}|{f'arg{i}' for i in range(7)}


def evaluate_primary_route(log,packet,sequence,*,checkpoint=None):
    """Observe exact installed branches and native calls; never infer later work."""
    failures=[];rows=[]
    def need(value,message):
        if not value:failures.append(message)
    for number,text in enumerate(log.splitlines(),1):
        if not re.search(r'MPCAP_',text,re.I):continue
        marker=text.split(' ',1)[0];rx=PRIMARY_REGEX.get(marker);match=rx.fullmatch(text) if rx else None
        row=dict(line=number,marker=marker,text=text,values=None);rows.append(row)
        if not match:failures.append(f'line {number}: malformed or unknown primary-route observation');continue
        row['values']={k:v if k in {'name','event','route','reason'} else int(v,16 if k in PRIMARY_HEX else 10)
                       for k,v in match.groupdict().items()}
        if marker=='MPCAP_REJECT':failures.append(f'line {number}: producer rejected native observation: '+row['values']['reason'])
        if marker=='MPCAP_CURSOR_RECT_CONTEXT':failures.append(f'line {number}: cursor rectangle rejection operands observed')
    modal=sequence.get('raw_records',[])
    def mr(marker,event=None):
        return [r for r in modal if r['marker']==marker and (event is None or (r.get('values') or {}).get('event')==event)]
    def one(marker):
        items=mr(marker);return (items[0].get('values') or {}) if len(items)==1 else {}
    hand=one('MCAP_MAP_HANDOFF');owner=one('MCAP_CASTLE_STATE').get('owner_ptr')
    tid=hand.get('tid');stack=hand.get('esp',0);w,h=map(int,packet['resolution'].split('x'))
    enters=mr('MCAP_CANVAS','ENTER');canvas=(enters[0].get('values') or {}) if enters else {}
    observers=packet.get('primary_observers',{})
    end=3 if checkpoint is None else CHECKPOINT_NAMES.index(checkpoint)
    cps=[r for r in rows if r['marker']=='MPCAP_CHECKPOINT'];hosts=[r for r in rows if r['marker']=='MPCAP_HOST_READY']
    canvases=mr('MCAP_CANVAS','CHECKPOINT')
    requests=[r for r in rows if r['marker']=='MPCAP_CHECKPOINT_REQUEST']
    need(len(cps)==len(hosts)==len(canvases)==len(requests)==end+1,'exact cumulative primary checkpoints and canvas records required')
    metadata=packet.get('checkpoints',[])
    need(len(metadata)==4 and [(r.get('name'),r.get('index')) for r in metadata]==list(zip(CHECKPOINT_NAMES,range(4))),
         'exact ordered checkpoint packet required')
    points=[]
    raw_lines=log.splitlines()
    for i,(cp,host,cr,request) in enumerate(zip(cps,hosts,canvases,requests)):
        v=cp['values'] or {};cv=cr['values'] or {};hv=host['values'] or {}
        name=CHECKPOINT_NAMES[i] if i<4 else None
        declared=metadata[i] if i<len(metadata) else {};allowed=declared.get('eips',[])
        allowed=allowed if isinstance(allowed,list) else [allowed]
        depth=(68+producer.ROUTES['barracks'].local_stack_bytes+4,188,160,64+producer.ROUTES['barracks'].local_stack_bytes)[i] if i<4 else 0
        need((v.get('name'),v.get('index'),v.get('tid'),v.get('esp'))==(name,i,tid,stack-depth)
             and v.get('eip') in allowed,'checkpoint name/order/native thread/EIP/stack differs')
        need((v.get('surface'),v.get('base'),v.get('width'),v.get('height'),v.get('bytes'),v.get('owner'))
             ==(canvas.get('physical'),canvas.get('physical_pixels'),w,h,w*h,owner)
             and v.get('render')==(0x51D4C0 if i in (1,2) else canvas.get('native')) and v.get('cursor') in (0,1)
             and (i!=0 or v.get('cursor')==0) and (i!=3 or v.get('cursor')==1),
             'checkpoint physical identity/geometry/owner/cursor differs')
        gap=host['line']-cp['line']
        adapter_line=(gap==2 and raw_lines[cp['line']].startswith('MPRI_CHECKPOINT '))
        need((hv.get('name'),cp['line']-cr['line'])==(name,1) and (gap==1 or adapter_line)
             and (request.get('values') or {}).get('name')==name and cr['line']==request['line']+1,
             'checkpoint request/canvas/record/optional primary observation/named host stop order differs')
        need(all(cv.get(k)==canvas.get(k) for k in ('state','root_esp','physical','native','physical_pixels','native_pixels',
                'native_width','native_height','physical_width','physical_height','native_com')),
             'checkpoint changed owned canvas identity or layout')
        need((cv.get('event'),cv.get('tid'),cv.get('eip'),cv.get('esp'),cv.get('phase'),cv.get('allocations'),cv.get('frees'),
              cv.get('mirrors'),cv.get('enter_status'),cv.get('mirror_status'),cv.get('leave_status'),cv.get('fault'))
             ==('CHECKPOINT',tid,v.get('eip'),v.get('esp'),1,1,0,3,1,1,0,0),'checkpoint native ownership/status/counters differ')
        points.append(dict(name=name,index=i,line=cp['line'],values=v,canvas=cv,host_ready_line=host['line']))
    if len(points)>2:
        present=mr('MCAP_PRESENT_CALL')
        need(points[1]['host_ready_line']<canvases[2]['line'], 'placeholder after precedes its before pause')
        if present:need(points[2]['host_ready_line']<present[0]['line'], 'placeholder after pause must precede final native present')
    if len(points)>3:
        final_hosts=mr('MCAP_SURFDUMP_HOST_READY')
        need(len(final_hosts)==1 and final_hosts[0]['line']<canvases[3]['line'], 'final primary pause must follow complete native readiness')
    # At each named pause there can be no later route record. Debugger prompt
    # and adapter-owned Lock/palette records are validated by the capture layer.
    if hosts:
        need(rows[-1] is hosts[-1],'primary-route record after requested paused host stop')
    arms=[r for r in rows if r['marker']=='MPCAP_PRIMARY_OBSERVERS_ARM'];screen=mr('MCAP_SCREEN_ENTRY')
    need(len(arms)==len(screen)==1 and arms[0]['line']==screen[0]['line']+1, 'one exact observer arm must follow facility entry')
    events=[r for r in rows if r['marker']=='MPCAP_EVENT'];groups=[]
    blits=mr('MCAP_CANVAS','BLIT_CALL')
    returns=mr('MCAP_CANVAS','OVERVIEW_BLIT_RETURN')+mr('MCAP_CANVAS','FACILITY_BLIT_RETURN')
    for route_index,route_name in enumerate(('overview','barracks')):
        group=[r for r in events if (r.get('values') or {}).get('route_state')==(2 if route_name=='overview' else 8)]
        first=(group[0].get('values') or {}) if group else {};active=first.get('cursor')
        need(active in (0,1),'full-entry cursor flag is not an observed native binary state')
        prefix=['full-entry']
        if active==1:prefix+=['remove-call','remove-entry','remove-return']
        prefix+=['publish-call','publish-entry','publish-return']
        if not (route_name=='barracks' and end==0):
            if active==1:prefix+=['draw-call','draw-entry','draw-return']
            prefix+=['full-return']
        need([(r.get('values') or {}).get('event') for r in group]==prefix,
             route_name+' installed full-publish/cursor native sequence missing, repeated or out of order')
        sp=stack-(136 if route_name=='overview' else 68+producer.ROUTES['barracks'].local_stack_bytes)
        parent=0x4220C6 if route_name=='overview' else producer.BLIT_CALLS['barracks']+3
        branch='cursor' if active==1 else 'direct'
        for row in group:
            v=row['values'] or {};event=v.get('event');key=event.replace('-','_')
            if event in ('publish-call','publish-return','full-return'):key+='_'+branch
            depths={'full-entry':0,'remove-call':36,'remove-entry':40,'remove-return':36,'publish-call':4,
                    'publish-entry':8,'publish-return':4,'draw-call':36,'draw-entry':40,'draw-return':36,'full-return':0}
            cursor=active if event in ('full-entry','full-return') else 1 if event in ('remove-call','remove-entry','draw-return') else 0
            need((v.get('tid'),v.get('eip'),v.get('esp'),v.get('full_esp'),v.get('parent'),v.get('cursor'))
                 ==(tid,observers.get(key),sp-depths.get(event,0),sp,parent,cursor),
                 route_name+' '+str(event)+' actual callsite/thread/stack/parent/cursor differs')
            target=canvas.get('native') if event in ('full-entry','full-return') else canvas.get('physical') if event in ('publish-call','publish-entry','publish-return') else 0x544CD8 if event in ('remove-call','remove-entry','draw-call','draw-entry') else None
            if target is not None:need(v.get('eax')==target,route_name+' '+str(event)+' native target EAX differs')
            if event in ('full-entry','full-return'):need(v.get('caller')==parent,'full native parent stack word differs')
            elif event.endswith('-entry'):
                caller_key=event.replace('-entry','_return')+('_'+branch if event=='publish-entry' else '')
                need(v.get('caller')==observers.get(caller_key),'native entry does not return to exact emitted call continuation')
        if route_index<len(blits) and group:
            need(blits[route_index]['line']<group[0]['line'],'installed full-entry precedes authenticated native blit call')
            matching=[r for r in returns if (r.get('values') or {}).get('event')==('OVERVIEW_BLIT_RETURN' if route_name=='overview' else 'FACILITY_BLIT_RETURN')]
            if matching:need(group[-1]['line']<matching[0]['line'],'native caller return precedes installed adapter return')
        groups.append(dict(route=route_name,cursor_initial=active,events=group,complete=not(route_name=='barracks' and end==0)))
    need([r for group in groups for r in group['events']]==events,'full-publish routes interleaved or unsupported')
    if points:
        pubs=[r for r in groups[-1]['events'] if (r.get('values') or {}).get('event')=='publish-return']
        need(len(pubs)==1 and pubs[0]['line']<canvases[0]['line']
             and all(points[0]['values'].get(k)==(pubs[0].get('values') or {}).get(k) for k in ('tid','eip','esp','cursor')),
             'first checkpoint must bind the actual facility HD publish return')
        later=[r for r in groups[-1]['events'] if (r.get('values') or {}).get('event') in ('draw-call','full-return')]
        if later:need(points[0]['host_ready_line']<later[0]['line'],'cursor redraw/native return happened before primary publish checkpoint')
    rects=[r for r in rows if r['marker']=='MPCAP_CURSOR_RECT'];placeholders=[r for r in rows if r['marker']=='MPCAP_PLACEHOLDER']
    rect_contexts=[r for r in rows if r['marker']=='MPCAP_CURSOR_RECT_CONTEXT']
    need(len(rects)==len(placeholders)==(0 if end==0 else 1),'placeholder route requires exactly one translated cursor rectangle and sprite call')
    if rects and placeholders and len(points)>1:
        r=rects[0]['values'] or {};p=placeholders[0]['values'] or {};ox,oy=(w-640)//2,(h-480)//2
        need((r.get('tid'),r.get('eip'),r.get('esp'),r.get('eax'),r.get('x'),r.get('y'),r.get('caller'))
             ==(tid,0x460BB0,stack-168,0x544CD8,220+ox,289+oy,0x432F61)
             and r.get('cursor') in (0,1) and (r.get('right'),r.get('bottom'))==(423+ox,409+oy),
             'placeholder native cursor rectangle/RET4 caller/translated bounds differ')
        need((p.get('tid'),p.get('eip'),p.get('esp'),p.get('primary'),p.get('vtable'),p.get('x'),p.get('y'),p.get('width'),p.get('height'),p.get('parent'))
             ==(tid,0x432F9E,stack-188,0x51D4C0,0x50EEC4,220+ox,289+oy,203,120,0x433E4E)
             and 0<p.get('sprite',0)<=0xFFFFFFFF-4 and 0<p.get('resource',0)<=0xFFFFFFFF-0x1010
             and [p.get(f'arg{i}') for i in range(7)]==[0xFFFFFFFF]*4+[0]*3,
             'placeholder primary/source sprite/index/geometry/native arguments differ')
        need(points[0]['host_ready_line']<rects[0]['line']<placeholders[0]['line']<canvases[1]['line'],
             'placeholder calls lie outside exact completed publish/before checkpoint order')
    return dict(passed=not failures,failures=failures,raw_records=rows,full_publish_routes=groups,checkpoints=points,
                placeholder=placeholders[0] if len(placeholders)==1 else None,
                cursor_rectangle=rects[0] if len(rects)==1 else None,
                cursor_rectangle_context=rect_contexts[0] if len(rect_contexts)==1 else None,
                coverage=dict(owned_full_publish=not failures,placeholder_arguments_observed=end>=1 and not failures,
                              placeholder_return_observed=end>=2 and not failures,
                              selected_panel='unexercised',selected_cursor_rectangle='unexercised'),
                primary_composition_proven=False,manual_input_proof=False,promotion_ready=False)

def evaluate_trace(log: str, *, original: bytes, candidate: bytes, packet: dict, generated_probe: bytes, checkpoint=None) -> dict:
    failures=[]
    authenticated=False
    initial=None
    sequence=None
    slot_trace=None
    primary_route=None
    source={"original_sha256":sha(original),"candidate_sha256":sha(candidate),"generated_probe_sha256":sha(generated_probe),
            "log_sha256":sha(log.encode('utf-8')),"startup_harness_sha256":sha(HARNESS.read_bytes()),
            "validator_sha256":sha(Path(__file__).read_bytes())}
    if not isinstance(packet,dict):
        packet={}
        failures.append('packet must be an object')
    try:
        rebuilt=producer.build_screen_probe(original,candidate,candidate_sha256=packet['candidate_sha256'],stage=packet['stage'],
            resolution=packet['resolution'],route=packet['route']['name'],availability=packet['availability'],
            castle_index=packet['castle_index'],candidate_manifest=Path(packet['candidate_manifest']['path']),minimap_viewport=True)
        extra=rebuilt['candidate_extra']
        if (json.dumps(rebuilt,sort_keys=True,separators=(',',':'),allow_nan=False)
                != json.dumps(packet,sort_keys=True,separators=(',',':'),allow_nan=False)):
            raise ValueError('packet differs from exact current source/candidate reconstruction')
        compiled=compile_probe(rebuilt)
        observed=generated_probe.decode('ascii').replace('\r\n','\n')
        source['generated_probe_canonical_lf_sha256']=sha(observed.encode('ascii'))
        if observed!=compiled: raise ValueError('whole generated probe differs from exact canonical modal compilation')
        authenticated=True
        sequence=evaluate_sequence(log,packet,checkpoint=checkpoint)
        failures.extend(sequence['failures'])
        slot_trace=evaluate_slots(log,packet,sequence,checkpoint=checkpoint)
        failures.extend(slot_trace['failures'])
        primary_route=evaluate_primary_route(log,packet,sequence,checkpoint=checkpoint)
        failures.extend(primary_route['failures'])
        initial=initial_map_paint_trace.evaluate_trace(log,extra,resolution=packet['resolution'],
                    candidate_sha256=packet['candidate_sha256'],stage=producer.STAGE)
        failures.extend('initial map trace: '+message for message in initial['failures'])
        contracts=[r for r in sequence['raw_records'] if r['marker']=='MCAP_CONTRACT']
        events=initial['event_integrity']['events']
        if len(contracts)!=1 or not events or contracts[0]['line']>=events[0]['line']:
            failures.append('modal startup contract must precede actual initial-map execution')
    except (KeyError,TypeError,ValueError,UnicodeError,OSError) as error:
        failures.append(str(error))
    passed=not failures
    points=(primary_route or {}).get('checkpoints',[])
    current=points[-1] if points else None
    observed=current['values'] if current else {}
    surface={key:observed.get(key) for key in ('surface','width','height','base','bytes','tid','eip','esp','owner')} if current else None
    if surface is not None:surface['route']='barracks'
    return dict(schema='clash95_modal_primary_trace_v1',passed=passed,source_authenticated=authenticated,ready_for_host_capture=passed,
        status='paused_modal_surface_observed' if passed else 'modal_trace_failed',
        stage=packet.get('stage'),resolution=packet.get('resolution'),protocol_revision=packet.get('protocol_revision'),
        route=packet.get('route',{}).get('name') if isinstance(packet.get('route'),dict) else None,
        candidate_sha256=sha(candidate),source=source,modal_sequence=sequence,initial_map_trace=initial,
        slot_trace=slot_trace, primary_route_sequence=primary_route, capture_checkpoint=current,
        surface=surface,failures=failures,
        complete=passed and checkpoint in (None,'final-ready'), requested_checkpoint=checkpoint,
        runtime_accepted=False,cleanup_verified=False,manual_input_proof=False,promotion_ready=False,limits=LIMITS)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--checkpoint', choices=('full-published','placeholder-before','placeholder-after','final-ready'))
    for name in ('original','candidate','log','packet','probe'):
        parser.add_argument('--'+name,type=Path,required=name in ('original','candidate'))
    for name in ('candidate-sha256','stage','resolution','route','availability'):
        parser.add_argument('--'+name)
    parser.add_argument('--castle-index',type=int)
    parser.add_argument('--minimap-viewport',action='store_true')
    parser.add_argument('--candidate-manifest',type=Path)
    args=parser.parse_args()
    try:
        original,candidate=args.original.read_bytes(),args.candidate.read_bytes()
        if args.prepare:
            if any(getattr(args,name) is None for name in ('candidate_sha256','stage','resolution','route','availability','castle_index')):
                raise ValueError('preparation requires SHA, stage, resolution, route, availability and castle index')
            if args.candidate_manifest is None: raise ValueError('preparation requires candidate manifest')
            packet=producer.build_screen_probe(original,candidate,candidate_sha256=args.candidate_sha256,stage=args.stage,
                resolution=args.resolution,route=args.route,availability=args.availability,castle_index=args.castle_index,
                candidate_manifest=args.candidate_manifest,minimap_viewport=True)
            compiled=compile_probe(packet)
            report=dict(prepared=True,runtime_ready=False,packet=packet,probe=compiled,probe_sha256=sha(compiled.encode('ascii')))
        else:
            if not all((args.log,args.packet,args.probe)): raise ValueError('validation requires --log --packet --probe')
            raw=args.log.read_bytes()
            report=evaluate_trace(raw.decode('utf-8-sig'),original=original,candidate=candidate,
                packet=strict_json_object(args.packet.read_bytes()),generated_probe=args.probe.read_bytes(),checkpoint=args.checkpoint)
            report['source']['log_raw_sha256']=sha(raw)
    except (OSError,UnicodeError,ValueError,TypeError,KeyError) as error:
        report=dict(passed=False,prepared=False,ready_for_host_capture=False,failures=[str(error)],
                    manual_input_proof=False,promotion_ready=False)
    print(json.dumps(report,indent=2))
    return 0 if report.get('prepared') or report.get('passed') else 2


if __name__=='__main__':
    raise SystemExit(main())

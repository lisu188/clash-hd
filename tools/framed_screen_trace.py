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

import framed_screen_probe as producer
import initial_map_paint_trace
from render_cdb_surface_probe import render_probe, BASE_PROBE

HARNESS = Path(__file__).resolve().parents[1] / "scripts/cdb/run_cdb_surface_dump.ps1"
HARNESS_SHA256 = "ae90b6930a287d4fdc12dc5506780b82af3fbbe1c6cbc49dcc2bc08d5e64e43b"
H = r"[0-9a-fA-F]{1,8}"
I = r"-?[0-9]{1,10}"
S = r"[a-z0-9_-]+"
SHA = r"[0-9a-f]{64}"
IDENTITY = rf"tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H})"
TI = rf"tid=(?P<tid>{H}) esp=(?P<esp>{H})"
SIZE = r"size=\((?P<width>[0-9]{1,4}),(?P<height>[0-9]{1,4})\)"
PATTERNS = {
    "MODAL_BYTE_CONTRACT_PASS": rf"candidate_sha256=(?P<sha>{SHA}) route=(?P<route>{S})",
    "MODAL_CONTRACT": rf"stage=(?P<stage>{S}) resolution=(?P<resolution>[0-9]{{3,4}}x[0-9]{{3,4}}) candidate_sha256=(?P<sha>{SHA}) route=(?P<route>{S}) availability=(?P<availability>{S}) castle_index=(?P<index>[0-3]) runtime_acceptance=0",
    "MODAL_MAP_HANDOFF": rf"{IDENTITY} render_hook=(?P<render_hook>{H}) lower=(?P<lower>{H}) post=(?P<post>{H}) surface=(?P<surface>{H}) {SIZE}",
    "MODAL_CASTLE_STATE": rf"index=(?P<index>[0-3]) ptr=(?P<owner_ptr>{H}) owner=(?P<owner>[0-9]) xy=\((?P<x>{I}),(?P<y>{I})\) flags=\((?P<flag0>{H}),(?P<flag4>{H})\) style=(?P<style>{I})",
    "MODAL_AVAILABILITY_FORCED": rf"flags=\((?P<flag0>{H}),(?P<flag4>{H})\) isolated_fixture=1",
    "MODAL_FORCE_CALL": rf"route=(?P<route>{S}) availability=(?P<availability>{S}) entry=(?P<entry>{H}) index=(?P<index>[0-3]) tid=(?P<tid>{H}) original_esp=(?P<esp>{H}) return_sentinel=(?P<sentinel>{H}) forced=1",
    "MODAL_OVERVIEW_PROLOGUE": rf"{IDENTITY} index=(?P<index>[0-3]) after_first_push=1 saved_ebx=(?P<saved_ebx>{H}) return_sentinel=(?P<sentinel>{H})",
    "MODAL_OVERVIEW_PRESENT_CALL": rf"{TI} cursor_active=(?P<cursor_active>{I})",
    "MODAL_OVERVIEW_PRESENT_RETURN": IDENTITY,
    "MODAL_FORCED_DISPATCH": rf"route=(?P<route>{S}) branch=(?P<branch>{H}) skip_input_loop=1 old_render=(?P<old_render>{H}) new_render=(?P<new_render>{H})",
    "MODAL_FLIP_GATE_FORCED": rf"{TI} original=(?P<original>{H}) forced=1 callback=(?P<callback>{H}) command=(?P<command>{I})",
    "MODAL_CALLBACK_CALL": rf"{TI} callback=(?P<callback>{H}) owner=(?P<owner_ptr>{H}) render_hook=(?P<render_hook>{H})",
    "MODAL_SCREEN_ENTRY": rf"route=(?P<route>{S}) {IDENTITY} owner=(?P<owner_ptr>{H})",
    "MODAL_PRESENT_CALL": rf"route=(?P<route>{S}) {IDENTITY} cursor_active=(?P<cursor_active>{I})",
    "MODAL_PRESENT_RETURN": rf"route=(?P<route>{S}) {IDENTITY}",
    "MODAL_SURFDUMP_READY": rf"route=(?P<route>{S}) {IDENTITY} surface=(?P<surface>{H}) {SIZE} base=(?P<base>{H}) bytes=(?P<bytes>[0-9]{{1,9}}) owner=(?P<owner_ptr>{H}) render=(?P<render>{H}) primary=0051d4c0 primary_size=\((?P<primary_width>[0-9]{{1,4}}),(?P<primary_height>[0-9]{{1,4}})\) primary_vtable=(?P<primary_vtable>{H}) capture=memory_map manual_input_proof=0",
    "MODAL_SURFDUMP_HOST_READY": "",
}
REGEX = {name: re.compile(name + (" " + tail if tail else "")) for name, tail in PATTERNS.items()}
HEX_FIELDS = {"tid", "eip", "esp", "render_hook", "lower", "post", "surface", "owner_ptr", "flag0", "flag4",
              "entry", "sentinel", "branch", "old_render", "new_render", "original", "callback", "base", "render", "primary_vtable", "saved_ebx"}
TEXT_FIELDS = {"sha", "route", "stage", "resolution", "availability"}
LIMITS = [
    "Accepted source-bound trace permits a paused host memory read only; screenshot correctness and complete modal composition are unproven here.",
    "The original map READY/visibility snapshot is diagnostic, never the modal host-capture trigger.",
    "Forced native case dispatch and gate results are retained; existing flags do not establish natural availability or manual input.",
    "Primary-only layers, host deadline/process identity/cleanup, final wrapper composition, input and promotion require separate evidence.",
    "Every raw modal record, including malformed or rejected observations, is retained without deduplication.",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _startup_fragments():
    data = HARNESS.read_bytes()
    if sha(data) != HARNESS_SHA256:
        raise ValueError("reviewed startup/load-substitution harness source changed")
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
    geometry = render_probe(BASE_PROBE.read_text(encoding="utf-8-sig"), packet["resolution"], producer.STAGE)["geometry"]
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


def evaluate_sequence(log: str, packet: dict) -> dict:
    """Ordered-log diagnosis only, without authenticating any external bytes."""
    failures, rows = [], []
    def fail(message, line=None):
        failures.append((f"line {line}: " if line else "") + message)
    if not isinstance(packet,dict) or not isinstance(packet.get('route'),dict):
        return dict(sequence_passed=False, failures=["packet must contain a route object"], raw_records=rows, surface=None,
                    source_authenticated=False,ready_for_host_capture=False)
    name = packet["route"].get("name")
    route = producer.ROUTES.get(name)
    if route is None or packet.get("stage") != producer.STAGE:
        return dict(sequence_passed=False, failures=["unsupported route/stage packet"], raw_records=rows, surface=None)
    dimensions = re.fullmatch(r"([1-9][0-9]{2,3})x([1-9][0-9]{2,3})", packet.get("resolution", ""))
    if not dimensions:
        return dict(sequence_passed=False, failures=["invalid packet resolution"], raw_records=rows, surface=None)
    width,height=map(int,dimensions.groups())
    for number, text in enumerate(log.splitlines(), 1):
        if re.search(r"AV_SURFDUMP|SURFDUMP_INVALID|PTILE_REJECT|MODAL_REJECT|syntax error|couldn't resolve", text, re.I):
            fail("runtime/probe rejection or debugger error", number)
        if re.search(r"\bMODAL_", text, re.I):
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
    expected = ["MODAL_BYTE_CONTRACT_PASS","MODAL_CONTRACT","MODAL_MAP_HANDOFF","MODAL_CASTLE_STATE"]
    if packet.get("availability") == "construct_all": expected.append("MODAL_AVAILABILITY_FORCED")
    elif packet.get("availability") != "existing_flags": fail("invalid explicit availability option")
    expected += ["MODAL_FORCE_CALL","MODAL_OVERVIEW_PROLOGUE","MODAL_OVERVIEW_PRESENT_CALL","MODAL_OVERVIEW_PRESENT_RETURN"]
    if name != "castle_overview":
        expected += ["MODAL_FORCED_DISPATCH","MODAL_FLIP_GATE_FORCED","MODAL_CALLBACK_CALL","MODAL_SCREEN_ENTRY","MODAL_PRESENT_CALL","MODAL_PRESENT_RETURN"]
    expected += ["MODAL_SURFDUMP_READY","MODAL_SURFDUMP_HOST_READY"]
    if [row["marker"] for row in rows] != expected:
        fail("modal sequence is missing, duplicated, out of order or contains extra records")
    # First observations may aid diagnosis of a failed trace, but a duplicate
    # above remains a failure and every original row remains in raw_records.
    by_name = {}
    for row in rows:
        if row["values"] is not None: by_name.setdefault(row["marker"],row)
    def values(marker): return by_name.get(marker,{}).get("values",{})
    def require(condition,message,marker):
        if not condition: fail(message,by_name.get(marker,{}).get("line"))
    for marker in ("MODAL_BYTE_CONTRACT_PASS","MODAL_CONTRACT"):
        data=values(marker)
        require(data.get('sha')==packet.get('candidate_sha256') and data.get('route')==name,"loaded candidate/route contract differs",marker)
    contract=values('MODAL_CONTRACT')
    require(all(contract.get(k)==packet.get(k) for k in ('stage','resolution','availability')) and contract.get('index')==packet.get('castle_index'),
            'stage/resolution/availability/castle contract differs','MODAL_CONTRACT')
    hand=values('MODAL_MAP_HANDOFF'); tid=hand.get('tid'); stack=hand.get('esp',0)
    require(tid and 0<stack<=0xFFFFFFFF and stack%4==0 and hand.get('eip')==0x406FA0,
            'map handoff site/thread/stack is invalid','MODAL_MAP_HANDOFF')
    require((hand.get('render_hook'),hand.get('lower'),hand.get('post'))==(0x40AD40,0,0)
            and (hand.get('width'),hand.get('height'))==(width,height) and hand.get('surface'),
            'map owner or physical surface differs','MODAL_MAP_HANDOFF')
    closes=[]
    for number,text in enumerate(log.splitlines(),1):
        if text.startswith('PTILE_TRACE_CLOSED'):
            match=re.fullmatch(rf'PTILE_TRACE_CLOSED {IDENTITY}',text)
            if match: closes.append((number,{k:int(v,16) for k,v in match.groupdict().items()}))
    require(len(closes)==1 and closes[0][1]==dict(tid=tid,eip=0x406FA0,esp=stack)
            and by_name.get('MODAL_CONTRACT',{}).get('line',10**9)<closes[0][0]<by_name.get('MODAL_MAP_HANDOFF',{}).get('line',0),
            'one matching completed map-trace closure must precede modal handoff','MODAL_MAP_HANDOFF')
    castle=values('MODAL_CASTLE_STATE'); owner=castle.get('owner_ptr')
    require(castle.get('index')==packet.get('castle_index') and owner and 0<owner<=0xFFFFFFFF-0x1A4
            and 0<=castle.get('owner',99)<=4 and 0<=castle.get('x',-1)<100 and 0<=castle.get('y',-1)<100
            and 0<=castle.get('flag0',999)<=255 and 0<=castle.get('flag4',999)<=255
            and -0x80000000<=castle.get('style',2**32)<=0x7FFFFFFF,
            'castle owner/state observation is invalid','MODAL_CASTLE_STATE')
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
    require(valid,'one exact prior map snapshot must precede trace closure','MODAL_MAP_HANDOFF')
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
    require(valid,'prior ceiling-window visibility observation is missing or mismatched','MODAL_MAP_HANDOFF')
    if packet.get('availability')=='construct_all':
        flags=values('MODAL_AVAILABILITY_FORCED')
        require((flags.get('flag0'),flags.get('flag4'))==(31,1) and castle.get('flag0',255)&0xE0==0
                and castle.get('flag4',255)&0xFE==0,'constructed availability differs or overwrites unreviewed flags','MODAL_AVAILABILITY_FORCED')
    forced=values('MODAL_FORCE_CALL')
    require((forced.get('route'),forced.get('availability'),forced.get('entry'),forced.get('index'),forced.get('tid'),forced.get('esp'),forced.get('sentinel'))
            ==(name,packet.get('availability'),0x422180,packet.get('castle_index'),tid,stack,0x406FA1),
            'forced native call identity differs','MODAL_FORCE_CALL')
    identities = {
        'MODAL_OVERVIEW_PROLOGUE':(0x422181,stack-8),
        'MODAL_OVERVIEW_PRESENT_CALL':(None,stack-60),
        'MODAL_OVERVIEW_PRESENT_RETURN':(0x42239F,stack-60),
    }
    entry=values('MODAL_OVERVIEW_PROLOGUE')
    require(entry.get('index')==packet.get('castle_index') and entry.get('sentinel')==0x406FA1,
            'overview prologue index or return sentinel differs','MODAL_OVERVIEW_PROLOGUE')
    if name != 'castle_overview':
        dispatch=values('MODAL_FORCED_DISPATCH')
        require(dispatch.get('route')==name and dispatch.get('branch')==route.branch_va and dispatch.get('new_render'),
                'forced native case branch differs','MODAL_FORCED_DISPATCH')
        gate=values('MODAL_FLIP_GATE_FORCED')
        require((gate.get('callback'),gate.get('command'))==(route.entry_va,route.command),'native gate command/callback differs','MODAL_FLIP_GATE_FORCED')
        call=values('MODAL_CALLBACK_CALL')
        require((call.get('callback'),call.get('owner_ptr'),call.get('render_hook'))==(route.entry_va,owner,0x4617A0),
                'native callback ABI/owner differs','MODAL_CALLBACK_CALL')
        require(values('MODAL_SCREEN_ENTRY').get('owner_ptr')==owner,'screen entry owner differs','MODAL_SCREEN_ENTRY')
        identities.update({
            'MODAL_FLIP_GATE_FORCED':(None,stack-60), 'MODAL_CALLBACK_CALL':(None,stack-60),
            'MODAL_SCREEN_ENTRY':(route.entry_va,stack-64),
            'MODAL_PRESENT_CALL':(route.present_call_va,stack-64-route.local_stack_bytes),
            'MODAL_PRESENT_RETURN':(route.stop_va,stack-64-route.local_stack_bytes),
        })
    capture_stack=stack-60 if name=='castle_overview' else stack-64-route.local_stack_bytes
    identities['MODAL_SURFDUMP_READY']=(route.stop_va,capture_stack)
    for marker,(eip,esp) in identities.items():
        data=values(marker)
        require(data.get('tid')==tid and data.get('esp')==esp and 0<esp<=0xFFFFFFFF and esp%4==0
                and (eip is None or data.get('eip')==eip),'native thread/EIP/returned stack differs',marker)
    for row in rows:
        data=row['values'] or {}
        if 'route' in data: require(data['route']==name,'record route differs',row['marker'])
    ready=values('MODAL_SURFDUMP_READY')
    require((ready.get('width'),ready.get('height'),ready.get('bytes'))==(width,height,width*height)
            and ready.get('surface')==hand.get('surface') and ready.get('owner_ptr')==owner
            and ready.get('base',0)>0 and ready.get('base',0)+width*height<=0x100000000,
            'final physical memory surface/dimensions/owner differ','MODAL_SURFDUMP_READY')
    surface={key:ready.get(key) for key in ('surface','width','height','base','bytes','route','tid','eip','esp','owner_ptr')}
    surface['owner']=surface.pop('owner_ptr')
    return dict(sequence_passed=not failures,source_authenticated=False,ready_for_host_capture=False,
                failures=failures,raw_records=rows,surface=surface if ready else None,
                forced_gate_original=values('MODAL_FLIP_GATE_FORCED').get('original'),
                manual_input_proof=False,promotion_ready=False,limits=LIMITS)


def evaluate_trace(log: str, *, original: bytes, candidate: bytes, packet: dict, generated_probe: bytes) -> dict:
    failures=[]
    initial=None
    sequence=None
    source={"original_sha256":sha(original),"candidate_sha256":sha(candidate),"generated_probe_sha256":sha(generated_probe),
            "log_sha256":sha(log.encode('utf-8')),"startup_harness_sha256":HARNESS_SHA256,
            "validator_sha256":sha(Path(__file__).read_bytes())}
    if not isinstance(packet,dict):
        packet={}
        failures.append('packet must be an object')
    try:
        _,_,extra,template=producer.canonical_template(original,packet['resolution'],minimap_viewport=packet['minimap_viewport'])
        rebuilt=producer.build_screen_probe(original,candidate,candidate_sha256=packet['candidate_sha256'],stage=packet['stage'],
            resolution=packet['resolution'],route=packet['route']['name'],availability=packet['availability'],
            castle_index=packet['castle_index'],rendered_probe=template,minimap_viewport=packet['minimap_viewport'])
        if rebuilt!=packet: raise ValueError('packet differs from exact current source/candidate reconstruction')
        compiled=compile_probe(rebuilt)
        observed=generated_probe.decode('ascii').replace('\r\n','\n')
        source['generated_probe_canonical_lf_sha256']=sha(observed.encode('ascii'))
        if observed!=compiled: raise ValueError('whole generated probe differs from exact canonical modal compilation')
        sequence=evaluate_sequence(log,packet)
        failures.extend(sequence['failures'])
        initial=initial_map_paint_trace.evaluate_trace(log,extra,resolution=packet['resolution'],
                    candidate_sha256=packet['candidate_sha256'],stage=packet['stage'])
        failures.extend('initial map trace: '+message for message in initial['failures'])
        contracts=[r for r in sequence['raw_records'] if r['marker']=='MODAL_CONTRACT']
        events=initial['event_integrity']['events']
        if len(contracts)!=1 or not events or contracts[0]['line']>=events[0]['line']:
            failures.append('modal startup contract must precede actual initial-map execution')
    except (KeyError,TypeError,ValueError,UnicodeError,OSError) as error:
        failures.append(str(error))
    passed=not failures
    return dict(schema='clash95_framed_screen_trace_v1',passed=passed,ready_for_host_capture=passed,
        status='paused_modal_surface_observed' if passed else 'modal_trace_failed',
        stage=packet.get('stage'),resolution=packet.get('resolution'),
        route=packet.get('route',{}).get('name') if isinstance(packet.get('route'),dict) else None,
        candidate_sha256=sha(candidate),source=source,modal_sequence=sequence,initial_map_trace=initial,
        surface=sequence.get('surface') if sequence else None,failures=failures,
        runtime_accepted=False,cleanup_verified=False,manual_input_proof=False,promotion_ready=False,limits=LIMITS)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    for name in ('original','candidate','log','packet','probe'):
        parser.add_argument('--'+name,type=Path,required=name in ('original','candidate'))
    for name in ('candidate-sha256','stage','resolution','route','availability'):
        parser.add_argument('--'+name)
    parser.add_argument('--castle-index',type=int)
    parser.add_argument('--minimap-viewport',action='store_true')
    args=parser.parse_args()
    try:
        original,candidate=args.original.read_bytes(),args.candidate.read_bytes()
        if args.prepare:
            if any(getattr(args,name) is None for name in ('candidate_sha256','stage','resolution','route','availability','castle_index')):
                raise ValueError('preparation requires SHA, stage, resolution, route, availability and castle index')
            _,_,_,template=producer.canonical_template(original,args.resolution,minimap_viewport=args.minimap_viewport)
            packet=producer.build_screen_probe(original,candidate,candidate_sha256=args.candidate_sha256,stage=args.stage,
                resolution=args.resolution,route=args.route,availability=args.availability,castle_index=args.castle_index,
                rendered_probe=template,minimap_viewport=args.minimap_viewport)
            compiled=compile_probe(packet)
            report=dict(prepared=True,runtime_ready=False,packet=packet,probe=compiled,probe_sha256=sha(compiled.encode('ascii')))
        else:
            if not all((args.log,args.packet,args.probe)): raise ValueError('validation requires --log --packet --probe')
            raw=args.log.read_bytes()
            report=evaluate_trace(raw.decode('utf-8-sig'),original=original,candidate=candidate,
                packet=json.loads(args.packet.read_text(encoding='utf-8-sig')),generated_probe=args.probe.read_bytes())
            report['source']['log_raw_sha256']=sha(raw)
    except (OSError,UnicodeError,ValueError,TypeError,KeyError) as error:
        report=dict(passed=False,prepared=False,ready_for_host_capture=False,failures=[str(error)],
                    manual_input_proof=False,promotion_ready=False)
    print(json.dumps(report,indent=2))
    return 0 if report.get('prepared') or report.get('passed') else 2


if __name__=='__main__':
    raise SystemExit(main())

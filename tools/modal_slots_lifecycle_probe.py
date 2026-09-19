#!/usr/bin/env python3
"""Prepare a separate, controlled slots-canvas exit diagnostic; never run it.

The first-present probe is reconstructed unchanged. A second command artifact
is admitted only at that probe's paused boundary. It requests native exit flags
and stops before the synthetic root return. Boundary observations are not a
healthy-paint, input, continuity, cleanup or release evaluator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import modal_slots_barracks_probe as inherited
import modal_slots_barracks_trace as inherited_trace
from src.patcher import framed_modal_canvas as canvas

ROOT = Path(__file__).resolve().parents[1]
REVISION = "slots_controlled_native_exit_boundaries_v1"
MODE = "controlled_native_exit_map_redraw"
STOP = 0x4224B7
SOURCES = ("tools/modal_slots_lifecycle_probe.py", "tools/modal_slots_barracks_probe.py",
           "tools/modal_slots_barracks_trace.py", "tools/modal_slots_candidate_context.py",
           "src/patcher/framed_modal_canvas.py")
LIMITS = [
    "No runtime host is supplied. The unchanged first-present prefix must pass its complete inherited evaluator before continuation.",
    "The inherited synthetic root entry, forced case dispatch and flipping-gate result remain disclosed controlled diagnostics.",
    "Two explicit debugger memory writes request native exit: 00532148 and 00526E80, each only after observing zero.",
    "No Back descriptor, hit-test, callback, human input or natural root caller is exercised by those writes.",
    "The stop at 004224B7 follows the restored-map call but precedes the unsafe synthetic root return to 00406FA1.",
    "Strict boundary ordering does not evaluate restored terrain coverage, visibility, pixels, primary composition or control health.",
    "Whole lifecycle acceptance remains incomplete; runtime, cleanup, continuity and release eligibility always remain false.",
]

# Source-native spans, checked independently against the known original and the
# reconstructed candidate. The two intentionally patched CALLs are separate.
NATIVE = {
    0x433E77: "b8d84c5400e80fd10200b8d84c5400e815d00200b8d84c5400baf03b4300e806d0020031c08b35306a5200a3482153008915306a5200bfd84c540031ede837fdffff89ea89f8e80ec70200b800515100b9c0d45100e87fa40100b8c04f5100890d30125100e8df5efeff",
    0x433EE9: "3b2d4821530074c3b8442153008935306a5200e81f1afdff",
    0x433F8E: "5d5f5a59c3",
    0x4340F0: "8b88b8000000ba02000000ff115d5f5a59c3",
    0x42262C: "ffd18b0dd8995100",
    0x422679: "a1686a5200",
    0x4226D3: "e8c8e70300e9e4fcffff",
    0x4223D3: "b8d84c5400",
    STOP: "833d846e520000",
    0x403E50: "535189c189d3f6c3047533c780b800000024ee50008b4004ba01000000e86b0207008d4108c7410400000000e85ff406008d48f8f6c302751989c8595bc3ba20f05000e893f20600e8aff2060089c8595bc389c8e8c7dd050089c8595bc3",
    0x461C70: "e968240100",
    0x4740DD: "5351525689c685c00f84f1000000",
    0x40AD40: "535152b8c0d45100",
    0x40AD8D: "e86ed90000b807000000",
    0x40ADE0: "c3",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _call(site, target):
    return b"\xe8" + struct.pack("<i", target - site - 5)


def _span(original, candidate, va, old, installed=None):
    installed = old if installed is None else installed
    if inherited._read(original, va, len(old))[1] != old:
        raise ValueError(f"lifecycle native bytes differ at {va:08x}")
    offset, actual = inherited._read(candidate, va, len(installed))
    if actual != installed:
        raise ValueError(f"lifecycle installed bytes differ at {va:08x}")
    return dict(va=va, rva=va-0x400000, offset=offset,
                original_hex=old.hex(), candidate_hex=installed.hex())


def _binding(original, candidate, base):
    if base["canvas_state_offsets"] != canvas.STATE:
        raise ValueError("unknown modal state layout")
    entries, observers = base["canvas_entry_vas"], base["canvas_observer_vas"]
    leave, after = entries["leave_before_map"], observers["before_restored_map_redraw"]
    if after != leave + 13:
        raise ValueError("unknown leave wrapper layout")
    start, end = entries["try_leave"], entries["is_active"]
    if not 0 < end-start < 4096:
        raise ValueError("unbounded try_leave implementation")
    code = inherited._read(candidate, start, end-start)[1]
    calls = [start+i for i in range(len(code)-4)
             if code[i] == 0xE8 and start+i+5+struct.unpack_from("<i", code, i+1)[0] == canvas.DTOR]
    if len(calls) != 1 or code[calls[0]-start-5:calls[0]-start] != bytes.fromhex("ba02000000"):
        raise ValueError("unique owned scalar destructor call is missing")
    records = [_span(original, candidate, va, bytes.fromhex(value)) for va,value in sorted(NATIVE.items())]
    records += [_span(original, candidate, 0x422674, _call(0x422674, 0x422020), _call(0x422674, 0x51B6D0)),
                _span(original, candidate, 0x4224B2, _call(0x4224B2, 0x40AD40), _call(0x4224B2, leave))]
    expected = bytes.fromhex("9c608d442424") + _call(leave+6, start) + bytes.fromhex("619d")
    expected += b"\xe9" + struct.pack("<i", 0x40AD40-after-5)
    if inherited._read(candidate, leave, len(expected))[1] != expected:
        raise ValueError("unknown leave-wrapper instruction contract")
    # These generated spans are authenticated by the entire slots rebuild,
    # then checked byte-for-byte again in the loaded image before continuation.
    for va,data in ((start,code), (leave,expected)):
        offset,_ = inherited._read(candidate,va,len(data))
        records.append(dict(va=va,rva=va-0x400000,offset=offset,
                            original_hex=None,candidate_hex=data.hex(),origin="exact_slots_rebuild"))
    return dict(state_va=base["canvas_state_va"], leave_va=leave, try_leave_va=start,
                before_map_va=after, destructor_call_va=calls[0], byte_spans=records)


# Every event has an exact instruction boundary and root-relative stack. The
# alternative barracks RETs are one event, never two separately accepted exits.
def event_specs(binding):
    b = binding
    rows = [
        ("BEGIN", (0x433E77,), -84, "active"),
        ("PRESENT2_CALL", (0x433E86,), -84, "active"),
        ("PRESENT2_RETURN", (0x433E8B,), -84, "active"),
        ("PRESENT3_CALL", (0x433E95,), -84, "active"),
        ("PRESENT3_RETURN", (0x433E9A,), -84, "active"),
        ("BARRACKS_REQUEST", (0x433EE9,), -84, "active"),
        ("BARRACKS_EXIT", (0x433EF1,), -84, "active"),
        ("LOWER_RESTORED", (0x433EFC,), -84, "active"),
        ("BARRACKS_RETURN", (0x433F92, 0x434101), -60, "active"),
        ("FACILITY_RETURN", (0x42262E,), -56, "active"),
        ("OVERVIEW_DRAW_CALL", (0x422674,), -56, "active"),
        ("OVERVIEW_DRAW_RETURN", (0x422679,), -56, "active"),
        ("OVERVIEW_PRESENT_CALL", (0x4226D3,), -56, "active"),
        ("OVERVIEW_REQUEST", (0x4226D8,), -56, "active"),
        ("ROOT_EXIT", (0x4223D3,), -56, "active"),
        ("LEAVE_CALL", (0x4224B2,), -56, "active"),
        ("LEAVE_ENTRY", (b["leave_va"],), -60, "active"),
        ("TRY_LEAVE_ENTRY", (b["try_leave_va"],), -100, "active"),
        ("DESTRUCTOR_CALL", (b["destructor_call_va"],), -136, "detached"),
        ("DESTRUCTOR_ENTRY", (0x403E50,), -140, "detached"),
        ("PIXEL_FREE_CALL", (0x403E6D,), -148, "detached"),
        ("PIXEL_FREE_ENTRY", (0x4740DD,), -152, "detached"),
        ("PIXEL_FREE_RETURN", (0x403E72,), -148, "detached"),
        ("HEADER_FREE_CALL", (0x403EA4,), -148, "detached"),
        ("HEADER_FREE_ENTRY", (0x461C70,), -152, "detached"),
        ("HEADER_HEAP_ENTRY", (0x4740DD,), -152, "detached"),
        ("HEADER_FREE_RETURN", (0x403EA9,), -148, "detached"),
        ("DESTRUCTOR_RETURN", (0x403EAD,), -140, "detached"),
        ("OWNED_DESTROYED", (b["destructor_call_va"]+5,), -136, "detached"),
        ("BEFORE_MAP", (b["before_map_va"],), -60, "released"),
        ("MAP_ENTRY", (0x40AD40,), -60, "released"),
        ("FULL_MAP_CALL", (0x40AD8D,), -72, "released"),
        ("FULL_MAP_RETURN", (0x40AD92,), -72, "released"),
        ("MAP_RETURN", (0x40ADE0,), -60, "released"),
        ("SAFE_STOP", (STOP,), -56, "released"),
    ]
    return [dict(event=name,vas=list(vas),stack_delta=delta,ownership=ownership)
            for name,vas,delta,ownership in rows]


def _printf(fmt, *args):
    return inherited._printf(fmt,*args)


def _guard(condition, body, reason):
    return (f".if ({condition}) {{ {body} }} .else {{ "
            + _printf(f"LCAP_REJECT reason={reason} ordinal=%d tid=%x eip=%p esp=%p", "@$t0","@$tid","@eip","@esp") + "; q }")


FIELDS = ("ordinal","tid","eip","esp","caller","eax","edx","ecx","root","native","physical",
          "native_pixels","physical_pixels","saved_render","saved_lower","phase","state_native","state_physical",
          "state_root","owner_tid","state_native_pixels","state_physical_pixels","state_saved_render",
          "allocations","frees","fault","leave","pending_header","pending_pixels","e0","render",
          "barracks_exit","overview_exit","destructive_exit","lower","hitmap")


def _expressions(binding):
    state = binding["state_va"]
    at = lambda name: f"poi({state+canvas.STATE[name]:08x})"
    return dict(zip(FIELDS, (
        "@$t0","@$tid","@eip","@esp","poi(@esp)","@eax","@edx","@ecx","@$t4","@$t5","@$t6",
        "@$t7","@$t8","@$t9","@$t12",at("phase"),at("native"),at("physical"),at("root_esp"),
        at("owner_tid"),at("native_pixels"),at("physical_pixels"),at("saved_render"),at("allocations"),
        at("frees"),at("fault"),at("leave_status"),at("pending_header"),at("pending_pixels"),
        "poi(005202e0)","poi(00511230)","poi(00532148)","poi(00526e80)","poi(00526e84)",
        "poi(00526a30)","poi(00526a68)")))


def _record(binding, event):
    expressions = _expressions(binding)
    return _printf("LCAP_EVENT event="+event+" "+" ".join(name+"=%x" for name in FIELDS),
                   *(expressions[name] for name in FIELDS))


def _ownership(binding, kind):
    x = _expressions(binding)
    checks = [f"({x[name]} == 0)" for name in ("fault","pending_header","pending_pixels")]
    checks += [f"({x['allocations']} == 1)",f"({x['frees']} == {1 if kind=='released' else 0})",
               f"({x['phase']} == {1 if kind=='active' else 0})",f"({x['leave']} == {1 if kind=='released' else 0})",
               "(@$t5 != 0)","(@$t6 != 0)","(@$t5 != @$t6)","(@$t7 != 0)","(@$t8 != 0)"]
    for name,value in (("state_native","@$t5" if kind=="active" else "0"),
                       ("state_physical","@$t6"),("state_root","@$t4"),("owner_tid","@$t2"),
                       ("state_native_pixels","@$t7"),("state_physical_pixels","@$t8"),("state_saved_render","@$t9")):
        checks.append(f"({x[name]} == {'0' if kind=='released' else value})")
    checks.append(f"({x['e0']} == {'@$t5' if kind=='active' else '@$t6'})")
    if kind=="detached": checks.append(f"({x['render']} == @$t9)")
    return " & ".join(checks)


def _specific(binding, name):
    """Extra native call identities. Never dereference an already freed header."""
    extra = []
    if name.endswith("_CALL") and name.startswith(("PRESENT", "OVERVIEW_PRESENT")):
        extra.append("@eax == 00544cd8")
    if name == "BARRACKS_REQUEST":
        extra += ["poi(00532148) == 0", "@ebp == 0", "poi(00526a30) == 00433bf0", "@esi == @$t12"]
    if name in ("BARRACKS_EXIT", "LOWER_RESTORED", "BARRACKS_RETURN", "FACILITY_RETURN"):
        extra.append("poi(00532148) == 1")
    if name == "LOWER_RESTORED": extra.append("poi(00526a30) == @$t12")
    if name == "BARRACKS_RETURN": extra.append("poi(@esp) == 0042262e")
    if name == "OVERVIEW_DRAW_CALL":
        extra += ["poi(00526a68) != 0", "poi(00526a68) != @$t5", "poi(00526a68) != @$t6"]
    if name in ("OVERVIEW_DRAW_RETURN","OVERVIEW_PRESENT_CALL","OVERVIEW_REQUEST"):
        extra.append("poi(00526a68) == @$t13")
    if name == "OVERVIEW_REQUEST": extra.append("poi(00526e80) == 0")
    if name in ("ROOT_EXIT","LEAVE_CALL","LEAVE_ENTRY","TRY_LEAVE_ENTRY"):
        extra.append("poi(00526e80) == 1")
    if name in ("LEAVE_CALL","LEAVE_ENTRY"): extra.append("poi(005199d8) == 0040ad40")
    if name in ("LEAVE_ENTRY","BEFORE_MAP","MAP_ENTRY","MAP_RETURN"):
        extra.append("poi(@esp) == 004224b7")
    if name == "TRY_LEAVE_ENTRY":
        extra += ["@eax == (@$t4-0n60)", f"poi(@esp) == {binding['leave_va']+11:08x}"]
    if name in ("DESTRUCTOR_CALL","DESTRUCTOR_ENTRY"):
        extra += ["@eax == @$t5","@edx == 2"]
    if name in ("DESTRUCTOR_ENTRY","DESTRUCTOR_RETURN"):
        extra.append(f"poi(@esp) == {binding['destructor_call_va']+5:08x}")
    if name in ("PIXEL_FREE_CALL","PIXEL_FREE_ENTRY"):
        extra += ["@eax == @$t7", "@edx == 1", "@ecx == @$t5"]
    if name == "PIXEL_FREE_ENTRY": extra.append("poi(@esp) == 00403e72")
    if name in ("PIXEL_FREE_RETURN","HEADER_FREE_CALL","HEADER_FREE_RETURN"):
        extra.append("@ecx == @$t5")
    if name in ("HEADER_FREE_CALL","HEADER_FREE_ENTRY","HEADER_HEAP_ENTRY"):
        extra.append("@eax == @$t5")
    if name in ("HEADER_FREE_ENTRY","HEADER_HEAP_ENTRY"):
        extra.append("poi(@esp) == 00403ea9")
    if name == "FULL_MAP_CALL": extra += ["@eax == 1","poi(00511230) == @$t6"]
    if name in ("FULL_MAP_RETURN","MAP_RETURN","SAFE_STOP"):
        extra.append("poi(00511230) == @$t6")
    extra.append("poi(00526e84) == 0")
    return " & ".join("("+item+")" for item in extra)


def _loaded_checks(records):
    terms = [f"(by({row['va']+index:08x}) != 0x{value:02x})"
             for row in records for index,value in enumerate(bytes.fromhex(row['candidate_hex']))]
    return "\n".join(".if ("+" | ".join(terms[i:i+40])+") { .echo LCAP_REJECT loaded_bytes; q }"
                     for i in range(0,len(terms),40)) + "\n"


def _inventory(text):
    occupied,sites = set(),set()
    for line in text.splitlines():
        match = re.match(r'^bp\s*(?:(\d+)\s+)?([0-9a-fA-F]{8})\s+"',line)
        if not match: continue
        number = int(match[1]) if match[1] else next(i for i in range(1000) if i not in occupied)
        va = int(match[2],16)
        if number in occupied or va in sites:
            raise ValueError("duplicate inherited breakpoint ID or site")
        occupied.add(number);sites.add(va)
    return occupied,sites


def _continuation(base, binding, initial):
    # Keep all inherited failure guards at first present. The continuation
    # retires that interval only after a separate evaluator accepted its prefix.
    ids,sites = _inventory(initial)
    expected_ids = {int(key) for key in base['breakpoint_commands']}
    if expected_ids != set(range(80,103)) or {i for i in ids if i>=80} != expected_ids:
        raise ValueError("unknown inherited modal breakpoint IDs")
    expected_return=inherited._guard('@eip == 0042262e',inherited._reject('unexpected_callback_return'),
                                    'breakpoint_eip',expected_eip=0x42262E)
    if base['breakpoint_commands']['90'] != dict(va=0x42262E,body=expected_return):
        raise ValueError("unknown inherited callback-return failure boundary")
    specs = event_specs(binding)
    by_va = {}
    for ordinal,spec in enumerate(specs[1:],1):
        for va in spec['vas']: by_va.setdefault(va,[]).append((ordinal,spec))
    new_ids = set(range(120,120+len(by_va)))
    if new_ids & ids or (set(by_va) & sites) != {0x42262E}:
        raise ValueError("lifecycle breakpoint ID/site collision")
    x = _expressions(binding)
    start = ("(@eip == 00433e77) & (@esp == (@$t4-0n84)) & (@$tid == @$t2) & "
             "(@$t0 == 0n10) & (@$t9 == 0n15) & (poi(@$t4) == 00406fa1)")
    body = (f"r @$t5={x['state_native']}; r @$t6={x['state_physical']}; "
            f"r @$t7={x['state_native_pixels']}; r @$t8={x['state_physical_pixels']}; "
            f"r @$t9={x['state_saved_render']}; r @$t12=poi(00526a30); r @$t0=0; "
            + _guard(_ownership(binding,'active')+" & (poi(00526e84) == 0)",
                     _record(binding,'BEGIN'),"begin_ownership"))
    begin = _guard(start,body,'not_inherited_paused_boundary')
    # CDB quoted BP bodies need escaped quotes/newlines; top-level commands do
    # not. This function never modifies EIP, ESP or a return address.
    top = lambda value: value.replace(r'\"','"').replace(r'\\n',r'\n')
    lines = [_loaded_checks(binding['byte_spans']),
             f".echo LCAP_CONTRACT protocol={REVISION} mode={MODE} candidate_sha256={base['candidate_sha256']} stage={base['stage']} resolution={base['resolution']} acceptance=0",
             top(begin), "bd " + " ".join(str(i) for i in sorted(ids-{80})), "bc 90"]
    for number,(va,variants) in enumerate(by_va.items(),120):
        commands = []
        for ordinal,spec in variants:
            name,delta = spec['event'],spec['stack_delta']
            tests = (f"(@$t0 == 0n{ordinal-1}) & (@$tid == @$t2) & (@eip == {va:08x}) & "
                     f"(@esp == (@$t4-0n{-delta})) & "+_ownership(binding,spec['ownership'])+" & "+_specific(binding,name))
            actions = []
            if name in ('BARRACKS_REQUEST','OVERVIEW_REQUEST'):
                target=0x532148 if name=='BARRACKS_REQUEST' else 0x526E80
                actions += [_printf(f'LCAP_WRITE event={name} tid=%x eip=%p esp=%p va={target:08x} old=%x new=1',
                                    '@$tid','@eip','@esp',f'poi({target:08x})'),f'ed {target:08x} 1']
            if name == 'OVERVIEW_DRAW_CALL': actions.append('r @$t13=poi(00526a68)')
            actions += [f'r @$t0=0n{ordinal}',_record(binding,name)]
            actions.append('.echo LCAP_SAFE_STOP' if name=='SAFE_STOP' else 'gc')
            guarded = _guard(tests,'; '.join(actions),'boundary_'+name.lower())
            # Shared native destructor/free routines also handle unrelated
            # game allocations. Filter solely by the latched owned identity;
            # a second use of either owned address remains a rejecting event.
            if va in (0x403E50,0x461C70): selector='@eax == @$t5'
            elif va == 0x4740DD: selector='@eax == '+('@$t7' if name=='PIXEL_FREE_ENTRY' else '@$t5')
            elif va in (0x403E6D,0x403E72,0x403EA4,0x403EA9): selector='@ecx == @$t5'
            elif va == 0x403EAD: selector=f'poi(@esp) == {binding["destructor_call_va"]+5:08x}'
            else: selector=None
            if selector: commands.append((selector,guarded))
            else: commands.append((None,guarded))
        if commands[0][0] is None:
            if len(commands)!=1: raise ValueError('unmatched shared observer')
            command = commands[0][1]
        else:
            command='gc'
            for selector,guarded in reversed(commands):
                command=f'.if ({selector}) {{ {guarded} }} .else {{ {command} }}'
        lines.append(f'bp{number} {va:08x} "{command}"')
    lines += ['g','']
    text='\n'.join(lines)
    if any(len(line)>=4096 for line in text.splitlines()):
        raise ValueError('lifecycle command exceeds CDB line bound')
    _inventory('\n'.join(line for line in initial.splitlines() if not re.match(r'^bp90\s',line))+'\n'+text)
    return text


def prepare(original, candidate, *, mode, **kwargs):
    if mode != MODE:
        raise ValueError('explicit controlled_native_exit_map_redraw mode required')
    sources = {name:sha((ROOT/name).read_bytes()) for name in SOURCES}
    base = inherited.build_screen_probe(original,candidate,**kwargs)
    initial = inherited_trace.compile_probe(base)
    binding = _binding(original,candidate,base)
    continuation = _continuation(base,binding,initial)
    if sources != {name:sha((ROOT/name).read_bytes()) for name in SOURCES}:
        raise ValueError('lifecycle source changed during preparation')
    packet = dict(schema='clash95_modal_slots_lifecycle_packet_v1',revision=REVISION,mode=MODE,
                  inherited_packet=base,binding=binding,events=event_specs(binding),
                  source_hashes=sources,
                  initial_probe_sha256=sha(initial.encode('ascii')),
                  continuation_probe_sha256=sha(continuation.encode('ascii')),
                  prepared=True,runtime_ready=False,evaluator_complete=False,stop_va=STOP,
                  forced_exit_request_writes=[dict(va=0x532148,old=0,new=1,boundary_va=0x433EE9),
                                              dict(va=0x526E80,old=0,new=1,boundary_va=0x4226D8)],
                  forced_os_input=False,manual_input_proof=False,callback_proof=False,
                  continuity_proven=False,promotion_ready=False,limits=LIMITS)
    return dict(packet=packet,initial_probe=initial,continuation_probe=continuation,
                prepared=True,runtime_ready=False,evaluator_complete=False)


def reconstruct(original,candidate,packet,initial_probe,continuation_probe):
    """Authenticate the entire packet and both artifacts, never arbitrary CDB."""
    base=packet['inherited_packet']
    rebuilt=prepare(original,candidate,mode=packet['mode'],candidate_sha256=base['candidate_sha256'],
        stage=base['stage'],resolution=base['resolution'],route=base['route']['name'],
        availability=base['availability'],castle_index=base['castle_index'],
        candidate_manifest=Path(base['candidate_manifest']['path']),minimap_viewport=True)
    if rebuilt['packet'] != packet:
        raise ValueError('whole lifecycle packet differs from exact reconstruction')
    for name,actual in (('initial_probe',initial_probe),('continuation_probe',continuation_probe)):
        if actual != rebuilt[name].encode('ascii'):
            raise ValueError(name+' differs from exact canonical bytes')
    return rebuilt


def acceptance_status(*, inherited_failures=(), lifecycle_failures=()):
    """No placeholder evaluator may convert a complete report into acceptance."""
    return dict(passed=False,evaluator_complete=False,runtime_ready=False,
        runtime_accepted=False,healthy_map_redraw_proven=False,cleanup_verified=False,
        manual_input_proof=False,callback_proof=False,continuity_proven=False,promotion_ready=False,
        failures=[*inherited_failures,*lifecycle_failures,
                  'complete lifecycle evaluator and restored-map evidence are not implemented'],limits=LIMITS)


def evaluate_boundary_sequence(log, packet):
    """Strict diagnostic records only; no source or whole-lifecycle acceptance.

    Every malformed, duplicate and unmatched lifecycle line is retained. This
    verifies the exposed boundary contract but cannot prove healthy map pixels.
    The source-bound entry point additionally preserves the inherited prefix.
    """
    failures,raw,events,writes=[],[],[],[]
    base=packet['inherited_packet'];binding=packet['binding'];specs=event_specs(binding)
    contract=(f"LCAP_CONTRACT protocol={REVISION} mode={MODE} candidate_sha256={base['candidate_sha256']} "
              f"stage={base['stage']} resolution={base['resolution']} acceptance=0")
    pattern=re.compile(r'LCAP_EVENT event=(?P<event>[A-Z0-9_]+) '+
        ' '.join(name+rf'=(?P<{name}>[0-9a-fA-F]{{1,8}})' for name in FIELDS))
    write_pattern=re.compile(r'LCAP_WRITE event=(?P<event>BARRACKS_REQUEST|OVERVIEW_REQUEST) '+
        ' '.join(name+rf'=(?P<{name}>[0-9a-fA-F]{{1,8}})' for name in ('tid','eip','esp','va','old','new')))
    controls=[]
    for number,line in enumerate(log.splitlines(),1):
        if re.search(r'LCAP_|MCAP_|SCAP_|PTILE_',line,re.I) is None: continue
        row=dict(line=number,text=line);raw.append(row)
        match=pattern.fullmatch(line)
        if match:
            row['values']={key:(value if key=='event' else int(value,16)) for key,value in match.groupdict().items()}
            events.append(row);controls.append('event')
        elif write_pattern.fullmatch(line):
            match=write_pattern.fullmatch(line)
            row['values']={key:(value if key=='event' else int(value,16)) for key,value in match.groupdict().items()}
            writes.append(row);controls.append('write')
        elif line == contract: controls.append('contract')
        elif line == 'LCAP_SAFE_STOP': controls.append('stop')
        else:
            controls.append('invalid');failures.append(f'malformed, rejected or unexpected lifecycle record at line {number}')
    expected_controls=['contract']
    for spec in specs:
        if spec['event'] in ('BARRACKS_REQUEST','OVERVIEW_REQUEST'): expected_controls.append('write')
        expected_controls.append('event')
    if controls != expected_controls+['stop']:
        failures.append('lifecycle records missing, duplicated, unmatched or reordered')
    if [row['values']['event'] for row in events] != [row['event'] for row in specs]:
        failures.append('exact native boundary sequence differs')
    first=events[0]['values'] if events else {}
    for row,ordinal,target in zip(writes,(5,13),(0x532148,0x526E80)):
        v=row['values'];spec=specs[ordinal]
        if (not first or v['event']!=spec['event'] or v['old']!=0 or v['new']!=1 or v['va']!=target or
                v['tid']!=first['tid'] or v['eip']!=spec['vas'][0] or v['esp']!=first['root']+spec['stack_delta']):
            failures.append(f"line {row['line']}: controlled request old/new or call identity differs")
    immutable=('tid','root','native','physical','native_pixels','physical_pixels','saved_render','saved_lower')
    for ordinal,(row,spec) in enumerate(zip(events,specs)):
        v=row['values'];name=spec['event'];kind=spec['ownership'];problems=[]
        def require(condition,label):
            if not condition: problems.append(label)
        require(v['ordinal']==ordinal and v['eip'] in spec['vas'],'ordinal/instruction')
        require(0 < first['root']+spec['stack_delta'] <= 0xFFFFFFFF and
                v['esp']==first['root']+spec['stack_delta'],'root-relative stack')
        require(all(v[key]==first[key] for key in immutable),'immutable thread/allocation identity')
        require(all(v[key] != 0 for key in ('tid','root','native','physical','native_pixels','physical_pixels'))
                and v['native']!=v['physical'],'null or shared owner')
        require(v['fault']==v['pending_header']==v['pending_pixels']==v['destructive_exit']==0,'fault/pending/destructive exit')
        require(v['allocations']==1 and v['frees']==int(kind=='released'),'allocation/destruction counts')
        require(v['phase']==int(kind=='active') and v['leave']==int(kind=='released'),'phase/leave state')
        expected={'state_native':v['native'] if kind=='active' else 0,'state_physical':v['physical'],
                  'state_root':v['root'],'owner_tid':v['tid'],'state_native_pixels':v['native_pixels'],
                  'state_physical_pixels':v['physical_pixels'],'state_saved_render':v['saved_render']}
        if kind=='released': expected={key:0 for key in expected}
        require(all(v[key]==value for key,value in expected.items()),'owned state restoration')
        require(v['e0']==v['native' if kind=='active' else 'physical'],'map surface ownership')
        if kind=='detached': require(v['render']==v['saved_render'],'restore before destruction')
        if 5<=ordinal: require(v['barracks_exit']==1,'controlled barracks request')
        if 13<=ordinal: require(v['overview_exit']==1,'controlled overview request')
        if name in ('BARRACKS_RETURN',): require(v['caller']==0x42262E,'barracks native caller')
        if name=='LOWER_RESTORED': require(v['lower']==v['saved_lower'],'lower callback restoration')
        if name in ('LEAVE_ENTRY','BEFORE_MAP','MAP_ENTRY','MAP_RETURN'):
            require(v['caller']==STOP,'restored-map caller')
        if name=='TRY_LEAVE_ENTRY':
            require(v['caller']==binding['leave_va']+11 and v['eax']==v['root']-60,'try_leave call identity')
        if name in ('DESTRUCTOR_ENTRY','DESTRUCTOR_RETURN'):
            require(v['caller']==binding['destructor_call_va']+5,'owned destructor caller')
        if name in ('DESTRUCTOR_CALL','DESTRUCTOR_ENTRY'):
            require(v['eax']==v['native'] and v['edx']==2,'scalar native destructor')
        if name in ('PIXEL_FREE_CALL','PIXEL_FREE_ENTRY'):
            require(v['eax']==v['native_pixels'] and v['edx']==1 and v['ecx']==v['native'],'owned pixel release')
        if name=='PIXEL_FREE_ENTRY': require(v['caller']==0x403E72,'pixel free caller')
        if name in ('PIXEL_FREE_RETURN','HEADER_FREE_CALL','HEADER_FREE_RETURN'):
            require(v['ecx']==v['native'],'destructor owner register')
        if name in ('HEADER_FREE_CALL','HEADER_FREE_ENTRY','HEADER_HEAP_ENTRY'):
            require(v['eax']==v['native'],'owned header release')
        if name in ('HEADER_FREE_ENTRY','HEADER_HEAP_ENTRY'): require(v['caller']==0x403EA9,'header free caller')
        if name.endswith('_CALL') and name.startswith(('PRESENT','OVERVIEW_PRESENT')):
            require(v['eax']==0x544CD8,'native present object')
        if name=='FULL_MAP_CALL': require(v['eax']==1,'native full-map present flag')
        if name in ('FULL_MAP_CALL','FULL_MAP_RETURN','MAP_RETURN','SAFE_STOP'):
            require(v['render']==v['physical'],'restored render surface')
        if name=='OVERVIEW_DRAW_CALL':
            require(v['hitmap'] not in (0,v['native'],v['physical']),'separate overview hit-map owner')
        if name in ('OVERVIEW_DRAW_RETURN','OVERVIEW_PRESENT_CALL','OVERVIEW_REQUEST') and len(events)>10:
            require(v['hitmap']==events[10]['values']['hitmap'],'overview hit-map continuity')
        if problems: failures.append(f"line {row['line']} {name}: "+', '.join(problems))
    return dict(boundary_sequence_passed=not failures,source_authenticated=False,evaluator_complete=False,
                failures=failures,raw_records=raw,events=events,writes=writes,healthy_map_redraw_proven=False,
                runtime_accepted=False,manual_input_proof=False,promotion_ready=False)


def evaluate_trace(log, *, original, candidate, packet, initial_probe, continuation_probe):
    """Retain every inherited failure; always return incomplete acceptance."""
    prefix_report=boundary_report=None;failures=[];authenticated=False
    try:
        reconstruct(original,candidate,packet,initial_probe,continuation_probe)
        authenticated=True
        lines=log.splitlines(keepends=True)
        indices=[index for index,line in enumerate(lines) if line.rstrip('\r\n')=='MCAP_SURFDUMP_HOST_READY']
        if len(indices)!=1: raise ValueError('exactly one inherited first-present boundary required')
        split=indices[0]+1
        prefix_report=inherited_trace.evaluate_trace(''.join(lines[:split]),original=original,candidate=candidate,
            packet=packet['inherited_packet'],generated_probe=initial_probe)
        failures.extend(prefix_report['failures'])
        boundary_report=evaluate_boundary_sequence(''.join(lines[split:]),packet)
        ready=[row['values'] for row in (prefix_report.get('modal_sequence') or {}).get('raw_records',[])
               if row.get('marker')=='MCAP_CANVAS' and row.get('values',{}).get('event')=='READY']
        if len(ready)!=1 or not boundary_report['events']:
            boundary_report['failures'].append('missing inherited owned-canvas readiness identity')
        else:
            begin=boundary_report['events'][0]['values']
            pairs={'tid':'tid','root':'root_esp','native':'native','physical':'physical',
                   'native_pixels':'native_pixels','physical_pixels':'physical_pixels'}
            if any(begin[key]!=ready[0].get(source) for key,source in pairs.items()):
                boundary_report['failures'].append('lifecycle begin differs from inherited owned-canvas identity')
        boundary_report['boundary_sequence_passed']=not boundary_report['failures']
        failures.extend(boundary_report['failures'])
    except (KeyError,TypeError,ValueError,OSError,UnicodeError) as exc:
        failures.append(str(exc))
    result=acceptance_status(lifecycle_failures=failures)
    result.update(source_authenticated=authenticated,inherited_report=prefix_report,boundary_report=boundary_report,
                  log_sha256=sha(log.encode('utf-8')))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('original','candidate','candidate-manifest'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('candidate-sha256','stage','resolution'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--mode',choices=(MODE,),required=True)
    parser.add_argument('--availability',choices=('existing_flags','construct_all'),required=True)
    parser.add_argument('--castle-index',type=int,required=True)
    args=parser.parse_args()
    try:
        result=prepare(args.original.read_bytes(),args.candidate.read_bytes(),mode=args.mode,
            candidate_manifest=args.candidate_manifest,candidate_sha256=args.candidate_sha256,
            stage=args.stage,resolution=args.resolution,route='barracks',availability=args.availability,
            castle_index=args.castle_index,minimap_viewport=True)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        parser.exit(2,f'lifecycle preparation refused: {exc}\n')
    print(json.dumps(result,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

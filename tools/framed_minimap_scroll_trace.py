#!/usr/bin/env python3
"""Strict offline scroll trace and actual paired-buffer erasure verification.

No runtime/host acceptance is granted. Commands, source bytes, phase order and
pixel provenance are independently checked before a bounded pixel claim.
"""
from __future__ import annotations

import math
from pathlib import Path
import re

import framed_minimap_scroll_probe as producer
import initial_map_paint_trace as initial
import minimap_viewport_audit as pixels

H = r"[0-9a-fA-F]{1,8}"
D = r"-?[0-9]{1,10}"
ID = rf"tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H})"
TAIL = {
    "BYTE_SEGMENT_PASS": "", "POINTERS_BOUND": "", "OBJECTS_BOUND": "", "CONTINUE_BOUND": "",
    "BOUND": r"stage=(?P<stage>[a-z0-9_-]+) resolution=(?P<resolution>[0-9]{3,4}x[0-9]{3,4}) candidate_sha256=(?P<sha>[a-f0-9]{64}) target=\((?P<request_x>[0-9]{1,2}),(?P<request_y>[0-9]{1,2})\)",
    "BEGIN": ID,
    "STATE": ID + rf" phase=(?P<phase>before|after) gd=(?P<gd>{H}) world=\((?P<world_x>{D}),(?P<world_y>{D})\) scroll=\((?P<scroll_x>{D}),(?P<scroll_y>{D})\) scale=(?P<scale>{D}) origin=\((?P<origin_x>{D}),(?P<origin_y>{D})\) shift=(?P<shift>{D}) mouse=\((?P<mouse_x>{H}),(?P<mouse_y>{H})\)",
    "SURFACE": rf"phase=(?P<phase>before|after) map=(?P<map>{H}) size=\((?P<width>{D}),(?P<height>{D})\) base=(?P<base>{H}) vtable=(?P<vtable>{H}) backing=(?P<backing>{H}) bsize=\((?P<bwidth>{D}),(?P<bheight>{D})\) bbase=(?P<bbase>{H}) bvtable=(?P<bvtable>{H}) render=(?P<render>{H})",
    "CONTEXT": rf"phase=(?P<phase>before|after) owner=(?P<owner>{H}) tile=(?P<tile>{H}) post=(?P<post>{H}) lower=(?P<lower>{H}) player=(?P<player>{D}) selector=(?P<selector>{D}) enabled=(?P<enabled>{D})",
    "HOST_READY": r"phase=(?P<phase>before|after)",
    "DISPATCH": ID + rf" requested=\((?P<request_x>{D}),(?P<request_y>{D})\) expected=\((?P<expected_x>{D}),(?P<expected_y>{D})\) old_mouse=\((?P<old_x>{H}),(?P<old_y>{H})\) new_mouse=\((?P<new_x>{H}),(?P<new_y>{H})\) call=0040b0e0 forced=1 manual_input_proof=0",
    "ENTRY": ID + rf" caller=(?P<caller>{H})",
    "GATE": ID + rf" observed=(?P<observed>{D}) replacement=1 forced=1 manual_input_proof=0",
    "FULL_CALL": ID + rf" scroll=\((?P<scroll_x>{D}),(?P<scroll_y>{D})\) present=1",
    "REPAIR_CALL": ID + rf" source=(?P<source>{H}) target=(?P<target>{H}) rect=\((?P<left>{D}),(?P<top>{D}),(?P<right>{D}),(?P<bottom>{D})\) dest=\((?P<dest_x>{D}),(?P<dest_y>{D})\)",
    "REPAIR_RETURN": ID,
    "DRAW_CALL": ID + rf" target=(?P<target>{H}) rect=\((?P<left>{D}),(?P<top>{D}),(?P<right>{D}),(?P<bottom>{D})\) color=(?P<color>{H}) scroll=\((?P<scroll_x>{D}),(?P<scroll_y>{D})\)",
    "DRAW_RETURN": ID + rf" status=(?P<status>{D})",
    "FULL_STATUS": ID + rf" hook=(?P<hook>full_converge|full_present) status=(?P<status>{D})",
    "FULL_RETURN": ID + rf" repair_count=(?P<repair_count>{D}) draw_count=(?P<draw_count>{D})",
    "CALLBACK_RETURN": ID + rf" scroll=\((?P<scroll_x>{D}),(?P<scroll_y>{D})\) result=(?P<result>{H})",
    "MOUSE_RESTORED": rf"values=\((?P<mouse_x>{H}),(?P<mouse_y>{H})\)",
}
PATTERNS = {name: re.compile("MMSC_"+name+(" "+tail if tail else "")) for name, tail in TAIL.items()}
HEX_FIELDS = set("tid eip esp gd mouse_x mouse_y old_x old_y new_x new_y map base vtable backing bbase bvtable render owner tile post lower caller source target color result".split())
TEXT_FIELDS = {"phase", "hook", "stage", "resolution", "sha"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parse_records(log: bytes):
    if type(log) is not bytes or len(log) > 16*1024*1024:
        return [], ["actual log bytes within the 16-MiB diagnostic bound are required"]
    rows, errors, offset = [], [], 0
    for number, raw in enumerate(log.splitlines(keepends=True), 1):
        offset += len(raw)
        try:
            line = raw.decode("utf-8-sig").rstrip("\r\n")
        except UnicodeError:
            errors.append(f"line {number}: invalid UTF-8 in preserved log bytes")
            continue
        if re.search(r"AV_SURFDUMP|SURFDUMP_APP_REQUEST_QUIT|access violation|syntax error|couldn.t resolve", line, re.I):
            errors.append(f"line {number}: runtime/debugger failure: {line}")
        if not re.search(r"MMSC_", line, re.I):
            continue
        row = dict(line=number, prefix_bytes=offset, text=line, marker=None)
        rows.append(row)
        matches = [(name, regex.fullmatch(line)) for name, regex in PATTERNS.items() if regex.fullmatch(line)]
        if len(matches) != 1 or not raw.endswith(b"\n"):
            errors.append(f"line {number}: malformed, unknown, rejected or unfinished scroll record")
            continue
        name, match = matches[0]
        row["marker"] = name
        row.update({k: v if k in TEXT_FIELDS else int(v, 16 if k in HEX_FIELDS else 10) for k, v in match.groupdict().items()})
    return rows, errors


def evaluate_sequence(log: bytes, packet: dict, *, phase="after") -> dict:
    """Ordered diagnosis only. No packet/source or snapshot provenance is assumed."""
    rows, failures = parse_records(log)
    states, surfaces, contexts, boundaries, repairs, draws = {}, {}, {}, {}, [], []
    try:
        require(phase in ("before", "after"), "unknown requested capture phase")
        require(not failures, "malformed input prevents phase acceptance")
        cursor = 0
        def take(name):
            nonlocal cursor
            require(cursor < len(rows), f"missing {name}")
            row = rows[cursor]; cursor += 1
            require(row["marker"] == name, f"line {row['line']}: expected {name}, got {row['marker']}")
            return row
        count = sum(math.ceil(row["size"]/48) for row in packet["native_spans"])
        for _ in range(count):
            take("BYTE_SEGMENT_PASS")
        bound = take("BOUND")
        require((bound["stage"], bound["resolution"], bound["sha"], bound["request_x"], bound["request_y"]) ==
                (packet["stage"], packet["resolution"], packet["candidate_sha256"], *packet["requested_scroll"]), "startup binding differs")
        begin = take("BEGIN")
        thread, caller_sp = begin["tid"], begin["esp"]
        require(thread > 0 and 65536 <= caller_sp < 0x7ffff000 and caller_sp % 4 == 0 and begin["eip"] == 0x406FA0, "invalid initial native pause")
        def ident(row, eip, esp):
            require((row["tid"], row["eip"], row["esp"]) == (thread, eip, esp), f"line {row['line']}: native thread/EIP/ESP mismatch")
        take("POINTERS_BOUND"); take("OBJECTS_BOUND")
        def capture(which):
            state, surface, context = take("STATE"), take("SURFACE"), take("CONTEXT")
            ready = take("HOST_READY")
            require(all(r["phase"] == which for r in (state, surface, context, ready)), "capture phase differs")
            ident(state, 0x406FA0 if which == "before" else 0x40B0E5, caller_sp)
            width, height = map(int, packet["resolution"].split("x"))
            wx, wy, sx, sy, scale = [state[k] for k in ("world_x", "world_y", "scroll_x", "scroll_y", "scale")]
            require(0 < state["gd"] < 0xfff00000 and 0 <= state["shift"] <= 8 and
                    scale == (4 if wx*wy <= 2500 else 2), "invalid game data/shift/source scale")
            require((surface["width"], surface["height"], surface["vtable"], surface["bvtable"]) == (width, height, 0x50EE24, 0x50EE24), "native surface header differs")
            require(len({surface["map"], surface["backing"], 0x51D4C0}) == 3 and
                    surface["render"] in (surface["map"], 0x51D4C0), "surface alias or unsupported render device")
            for ptr, size in ((surface["map"], 188), (surface["backing"], 188),
                              (surface["base"], width*height), (surface["bbase"], surface["bwidth"]*surface["bheight"])):
                require(65536 <= ptr < ptr+size <= 0x100000000 and 0 < size <= 67108864, "unbounded native surface")
            require(surface["base"]+width*height <= surface["bbase"] or
                    surface["bbase"]+surface["bwidth"]*surface["bheight"] <= surface["base"], "pixel buffers alias")
            require([context[k] for k in ("owner", "tile", "post", "lower", "player", "selector", "enabled")] == [0x40AD40, 0, 0, 0, 0, 0, 1], "ordinary player-0 map context differs")
            require(wx >= (width-64)//64 and wy >= (height-32)//64, "world too small for current full-render admission")
            geometry = pixels.expected_outline(width, height, scale=scale, world=(wx, wy), scroll=(sx, sy),
                minimap_origin=(state["origin_x"], state["origin_y"]), minimap_size=(surface["bwidth"], surface["bheight"]))
            states[which] = state; surfaces[which] = surface; contexts[which] = context
            boundaries[which] = dict(prefix_bytes=ready["prefix_bytes"], prefix_sha256=producer.sha(log[:ready["prefix_bytes"]]), geometry=geometry)
        capture("before")
        if phase == "after":
            take("CONTINUE_BOUND")
            dispatch = take("DISPATCH"); ident(dispatch, 0x406FA0, caller_sp)
            b = states["before"]; sf = surfaces["before"]
            requested = packet["requested_scroll"]
            maxima = (b["world_x"]-(sf["width"]-64)//64, b["world_y"]-(sf["height"]-32)//64)
            require(all(0 <= n < world and n <= maximum+1 for n, world, maximum in zip(requested, (b["world_x"], b["world_y"]), maxima)), "requested target exceeds controlled clamp lane")
            expected = tuple(min(n, m) for n, m in zip(requested, maxima))
            require(expected != (b["scroll_x"], b["scroll_y"]), "unchanged scroll is not a pan")
            new_mouse = tuple((origin+7+n*b["scale"]) << b["shift"] for origin,n in zip((b["origin_x"], b["origin_y"]), requested))
            require(tuple(dispatch[k] for k in ("request_x", "request_y", "expected_x", "expected_y", "old_x", "old_y", "new_x", "new_y")) ==
                    (*requested, *expected, b["mouse_x"], b["mouse_y"], *new_mouse), "dispatch does not bind the source-derived mouse/target")
            entry=take("ENTRY"); ident(entry,0x40DC10,caller_sp-4)
            require(entry["caller"] == 0x40B0E5, "native callback return address differs")
            gate=take("GATE"); ident(gate,0x40DC1F,caller_sp-24)
            require(gate["observed"] in (0,1), "invalid real gate observation")
            full=take("FULL_CALL"); ident(full,0x40DCEC,caller_sp-24)
            require((full["scroll_x"],full["scroll_y"]) == expected, "native stored scroll did not reach target")
            after_geometry=pixels.expected_outline(sf["width"],sf["height"],scale=b["scale"],world=(b["world_x"],b["world_y"]),scroll=expected,
                minimap_origin=(b["origin_x"],b["origin_y"]),minimap_size=(sf["bwidth"],sf["bheight"]))
            full_hooks=[]; pending_repair=None; pending_draw=None
            while cursor < len(rows) and rows[cursor]["marker"] != "FULL_RETURN":
                row=rows[cursor]; cursor+=1; name=row["marker"]
                require(row.get("tid") == thread, f"line {row['line']}: foreign thread during redraw")
                if name == "REPAIR_CALL":
                    require(pending_repair is None and pending_draw is None and row["eip"] == 0x40D62E, "overlapping or wrong repair call")
                    require(row["source"] == sf["backing"] and row["target"] == sf["map"], "repair does not target the captured memory map")
                    l,t,r,bt=[row[k] for k in ("left","top","right","bottom")]
                    require(0 <= l <= r < sf["bwidth"] and 0 <= t <= bt < sf["bheight"], "repair source exceeds backing")
                    require((row["dest_x"],row["dest_y"]) == (b["origin_x"]+l,b["origin_y"]+t), "repair source/destination translation differs")
                    pending_repair=row
                elif name == "REPAIR_RETURN":
                    require(pending_repair is not None, "repair return lacks a fresh call")
                    ident(row,0x40D633,pending_repair["esp"]+16)
                    repairs.append(pending_repair); pending_repair=None
                elif name == "DRAW_CALL":
                    require(pending_repair is None and pending_draw is None and row["eip"] == packet["minimap_contract"]["observers"]["memory"], "overlapping or wrong native outline call")
                    require(row["target"] == sf["map"] and row["color"] == 0x4C and
                            [row[k] for k in ("left","top","right","bottom")] == after_geometry["rect"] and
                            (row["scroll_x"],row["scroll_y"]) == expected, "native drawn rectangle/target/scroll differs")
                    pending_draw=row
                elif name == "DRAW_RETURN":
                    require(pending_draw is not None and row["status"] == 1, "draw return lacks a fresh successful call")
                    ident(row,packet["minimap_contract"]["afterdraw_status"],pending_draw["esp"]+12)
                    draws.append(pending_draw); pending_draw=None
                elif name == "FULL_STATUS":
                    require(pending_repair is None and pending_draw is None and len(full_hooks) < 2, "full status overlaps or repeats")
                    wanted=("full_converge","full_present")[len(full_hooks)]
                    require(row["hook"] == wanted and row["status"] == 1, "full convergence/presentation order or admission differs")
                    bp="89" if wanted == "full_converge" else "90"
                    ident(row,packet["breakpoint_commands"][bp]["va"],caller_sp-172)
                    full_hooks.append(row)
                else:
                    raise ValueError(f"line {row['line']}: unexpected {name} during redraw")
                require(len(repairs) <= 1024 and len(draws) <= 1024, "redraw event limit exceeded")
            result=take("FULL_RETURN"); ident(result,0x40DCF1,caller_sp-24)
            require(pending_repair is None and pending_draw is None and len(full_hooks) == 2 and repairs and draws and
                    (result["repair_count"],result["draw_count"]) == (len(repairs),len(draws)), "redraw was incomplete or counts differed")
            returned=take("CALLBACK_RETURN"); ident(returned,0x40B0E5,caller_sp)
            require((returned["scroll_x"],returned["scroll_y"]) == expected, "callback did not return with expected stored scroll")
            restored=take("MOUSE_RESTORED")
            require((restored["mouse_x"],restored["mouse_y"]) == (b["mouse_x"],b["mouse_y"]), "native mouse restoration differs")
            capture("after")
            for key in ("gd","world_x","world_y","scale","origin_x","origin_y","shift","mouse_x","mouse_y"):
                require(states["after"][key] == b[key], f"after state changed {key}")
            require((states["after"]["scroll_x"],states["after"]["scroll_y"]) == expected, "after capture scroll differs")
            for key in ("map","width","height","base","vtable","backing","bwidth","bheight","bbase","bvtable"):
                require(surfaces["after"][key] == sf[key], f"after surface identity changed {key}")
        require(cursor == len(rows), "unexpected/repeated records after the requested pause")
    except (ValueError,KeyError,TypeError,IndexError) as error:
        failures.append(str(error))
    return dict(sequence_passed=not failures, failures=failures, raw_records=rows, states=states, surfaces=surfaces,
                contexts=contexts, boundaries=boundaries, repairs=repairs, draws=draws,
                source_authenticated=False,runtime_ready=False,manual_input_proof=False,promotion_ready=False)


def evaluate_trace(log: bytes, *, original: bytes, candidate: bytes, packet: dict,
                   initial_probe: bytes, before_commands: bytes, continue_commands: bytes, phase="after") -> dict:
    failures=[]; sequence=None; initial_report=None
    try:
        require(type(log) is bytes and len(log) <= 16*1024*1024 and type(packet) is dict,"bounded raw log bytes and object packet required")
        rebuilt=producer.build_packet(original,candidate,candidate_sha256=packet["candidate_sha256"],stage=packet["stage"],
                                      resolution=packet["resolution"],requested_scroll=packet["requested_scroll"])
        require(rebuilt == packet,"packet differs from exact current source/candidate reconstruction")
        for name,data in (("initial_probe",initial_probe),("before_commands",before_commands),("continue_commands",continue_commands)):
            require(data == packet[name].encode("ascii"),f"whole {name} differs from the reconstructed file")
        sequence=evaluate_sequence(log,packet,phase=phase); failures.extend(sequence["failures"])
        extra=producer.builder.build_candidate(original,packet["resolution"],minimap_viewport=True)[2]
        initial_report=initial.evaluate_trace(log.decode("utf-8-sig"),extra,resolution=packet["resolution"],candidate_sha256=producer.sha(candidate),stage=packet["stage"])
        failures.extend("initial trace: "+value for value in initial_report["failures"])
        rows=sequence["raw_records"]
        begin=next(row for row in rows if row["marker"] == "BEGIN")
        closes=[(i,line) for i,line in enumerate(log.decode("utf-8-sig").splitlines(),1) if line.startswith("PTILE_TRACE_CLOSED")]
        require(len(closes) == 1 and closes[0][0] < begin["line"],"new phase must follow the one completed initial trace")
        close=re.fullmatch(rf"PTILE_TRACE_CLOSED tid=({H}) eip=({H}) esp=({H})",closes[0][1])
        require(close and tuple(int(v,16) for v in close.groups()) == (begin["tid"],begin["eip"],begin["esp"]),"initial close/new phase identity differs")
        prior=log[:sum(len(line) for line in log.splitlines(keepends=True)[:begin["line"]-1])].decode("utf-8-sig")
        ready=re.findall(rf"(?m)^SURFDUMP_READY redraw_seq=4 surface=({H}) size=\(([0-9]+),([0-9]+)\) base=({H}) bytes=([0-9]+)\r?$",prior)
        require(len(ready) == 1 and len(re.findall(r"(?m)^SURFDUMP_HOST_READY\r?$",prior)) == 1,"missing unique original paused map readiness")
        sf=sequence["surfaces"]["before"]
        require((int(ready[0][0],16),int(ready[0][1]),int(ready[0][2]),int(ready[0][3],16),int(ready[0][4])) ==
                (sf["map"],sf["width"],sf["height"],sf["base"],sf["width"]*sf["height"]),"before surface differs from original map pause")
        bound=next(row for row in rows if row["marker"] == "BOUND")
        events=initial_report["event_integrity"]["events"]
        require(events and bound["line"] < events[0]["line"],"source checks must precede initial native execution")
    except (ValueError,KeyError,TypeError,UnicodeError,StopIteration) as error:
        failures.append(str(error))
    return dict(schema="clash95_framed_minimap_scroll_trace_v1",passed=not failures,phase=phase,failures=failures,
                sequence=sequence,initial_trace=initial_report,source_authenticated=not failures,
                packet_sha256=producer.packet_hash(packet),log_sha256=producer.sha(log),candidate_sha256=producer.sha(candidate),
                runtime_ready=False,host_integration_implemented=False,manual_input_proof=False,promotion_ready=False,
                evaluator_sha256=producer.sha(Path(__file__).read_bytes()),limits=producer.LIMITS)


def audit_erasure(log: bytes, *, original: bytes, candidate: bytes, packet: dict,
                 initial_probe: bytes, before_commands: bytes, continue_commands: bytes,
                 before_frame: bytes, after_frame: bytes, before_backing: bytes, after_backing: bytes,
                 receipts: dict) -> dict:
    report=evaluate_trace(log,original=original,candidate=candidate,packet=packet,initial_probe=initial_probe,
                          before_commands=before_commands,continue_commands=continue_commands)
    failures=list(report["failures"]); evidence={}
    try:
        require(report["passed"],"full bound trace must pass before pixel evaluation")
        seq=report["sequence"]
        require(type(receipts) is dict and set(receipts) == {"before","after"},"both exact snapshot receipts are required")
        for phase,frame,backing in (("before",before_frame,before_backing),("after",after_frame,after_backing)):
            require(type(frame) is bytes and type(backing) is bytes,"actual captured buffers are required")
            s=seq["surfaces"][phase]; state=seq["states"][phase]; bound=seq["boundaries"][phase]
            expected=dict(phase=phase,packet_sha256=report["packet_sha256"],candidate_sha256=report["candidate_sha256"],
                initial_probe_sha256=packet["initial_probe_sha256"],before_commands_sha256=packet["before_commands_sha256"],
                continue_commands_sha256=packet["continue_commands_sha256"],log_prefix_bytes=bound["prefix_bytes"],log_prefix_sha256=bound["prefix_sha256"],
                tid=state["tid"],eip=state["eip"],esp=state["esp"],map=s["map"],base=s["base"],backing=s["backing"],bbase=s["bbase"],
                width=s["width"],height=s["height"],pitch=s["width"],bwidth=s["bwidth"],bheight=s["bheight"],bpitch=s["bwidth"],
                frame_sha256=producer.sha(frame),backing_sha256=producer.sha(backing))
            receipt=receipts[phase]
            require(type(receipt) is dict and receipt == expected and all(type(receipt[k]) is type(v) for k,v in expected.items()),f"{phase} receipt differs from actual source/trace/buffers")
            require(len(frame) == s["width"]*s["height"] and len(backing) == s["bwidth"]*s["bheight"],"captured byte counts differ")
        require(before_backing == after_backing,"clean backing changed between pauses; no unchanged-backing erasure claim")
        s=seq["surfaces"]["after"]; st=seq["states"]["after"]
        old=set(pixels.perimeter(seq["boundaries"]["before"]["geometry"]["rect"]))
        new=set(pixels.perimeter(seq["boundaries"]["after"]["geometry"]["rect"]))
        old_only=old-new; width=s["width"]; bw=s["bwidth"]; mx,my=st["origin_x"],st["origin_y"]
        require(old_only,"no old-only border pixels to test")
        old_bad=[(x,y) for x,y in old if before_frame[y*width+x] != 0x4C]
        new_bad=[(x,y) for x,y in new if after_frame[y*width+x] != 0x4C]
        informative=[(x,y) for x,y in old_only if after_backing[(y-my)*bw+x-mx] != 0x4C]
        erased_bad=[(x,y) for x,y in old_only if after_frame[y*width+x] != after_backing[(y-my)*bw+x-mx]]
        coverage=set()
        for row in seq["repairs"]:
            coverage.update((x,y) for x,y in old_only if row["dest_x"] <= x <= row["dest_x"]+row["right"]-row["left"] and
                            row["dest_y"] <= y <= row["dest_y"]+row["bottom"]-row["top"])
        evidence=dict(before_perimeter=len(old),after_perimeter=len(new),old_only_pixels=len(old_only),
                      informative_old_only_pixels=len(informative),repaired_old_only_pixels=len(coverage),
                      before_mismatches=old_bad[:20],after_mismatches=new_bad[:20],erasure_mismatches=erased_bad[:20],
                      unchanged_backing_sha256=producer.sha(after_backing))
        require(not old_bad and not new_bad,"before or after native perimeter pixels differ")
        require(informative,"all old-only pixels are naturally4C; erasure is inconclusive")
        require(coverage == old_only,"observed native repairs do not cover the old-only border")
        require(not erased_bad,"old-only border did not return to clean backing pixels")
    except (ValueError,KeyError,TypeError,IndexError) as error:
        failures.append(str(error))
    return dict(schema="clash95_framed_minimap_scroll_erasure_v1",passed=not failures,failures=failures,evidence=evidence,
                trace=report,runtime_ready=False,manual_input_proof=False,promotion_ready=False,
                limits=producer.LIMITS+["Exact stable backing and indexed border erasure only; this does not establish manual scrolling or host cleanup."])

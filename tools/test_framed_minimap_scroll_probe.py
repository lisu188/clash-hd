#!/usr/bin/env python3
"""Synthetic CDB command, strict trace and actual-buffer oracle fixtures.

No game/debugger is run and no candidate/asset/capture file is written.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import unittest

import framed_minimap_scroll_probe as probe
import framed_minimap_scroll_trace as trace
from test_framed_screen_probe import Memory, run, write
import test_initial_map_paint_trace as initial_fixture

ORIGINAL = Path("C:/Clash/clash95.exe")


def command_fixture(packet, *, stop_before=False, gate_value=0, world=100, scale=2, mutations=()):
    width,height=map(int,packet["resolution"].split("x"))
    memory=Memory(); gd=0x10000000; surface=0x20000000; backing=0x22000000
    for addr,value,size in (
        (0x5202E4,gd,4),(0x5202E0,surface,4),(0x52334C,backing,4),(0x5199D8,0x40AD40,4),
        (0x52698C,0,4),(0x526990,0,4),(0x526994,0,4),(0x5202EC,0,4),(0x511230,surface,4),
        (gd+0x23EC7,0,4),(gd+0x2230F,1,4),(gd+0x22313,1,4),(gd+0x222E0,world,4),(gd+0x222E4,world,4),
        (gd+0x222E8,10,4),(gd+0x222EC,17,4),(surface,width,2),(surface+2,height,2),(surface+4,0x21000000,4),(surface+0xB8,0x50EE24,4),
        (backing,214,2),(backing+2,214,2),(backing+4,0x23000000,4),(backing+0xB8,0x50EE24,4),
        (0x523348,214,2),(0x52334A,214,2),(0x523344,width-246,2),(0x523346,16,2),(0x523F54,scale,1),
        (0x54512C,6,1),(0x544CFC,320<<6,4),(0x544D00,240<<6,4)):
        write(memory,addr,value,size)
    regs={"$tid":0xABC,"esp":0x100100,"eip":0x406FA0,"$t14":1,"$t13":4,"$t7":1,"eax":99,
          "ebx":0,"ecx":0,"edx":0,"esi":0,"edi":0,"ebp":0}
    observed=[]; enabled=set(); snapshots={}
    for kind,key,value in mutations:
        if kind == "register": regs[key]=value
        else: write(memory,key,value)
    # Before/continue action strings are the same actual commands, represented
    # with the single breakpoint-escaping layer understood by the test parser.
    result=run(packet["before_action"],memory,regs,enabled,observed)
    if mutations:
        return result,memory,regs,observed
    if result is not None:
        raise AssertionError((result,observed))
    if stop_before:
        return observed,memory,regs,snapshots
    result=run(packet["continue_action"],memory,regs,enabled,observed)
    if result is not None:
        raise AssertionError((result,observed))
    caller_sp=regs["$t1"]
    def hit(number,**changes):
        regs.update(changes)
        command=packet["breakpoint_commands"][str(number)]
        regs["eip"]=command["va"]
        snapshots[number]=(Memory(memory),regs.copy())
        return run(command["body"],memory,regs,enabled,observed)
    # The real source CALL, five native pushes, gate CALL/return and full redraw
    # are simulated here; these observations are explicitly synthetic fixtures.
    regs["esp"]=caller_sp-4; write(memory,regs["esp"],0x40B0E5)
    assert hit(82) == "gc"
    assert hit(83,esp=caller_sp-24,eax=gate_value) == "gc"
    write(memory,gd+0x222E8,regs["$t12"]); write(memory,gd+0x222EC,regs["$t13"])
    assert hit(84,eax=1) == "gc"
    sp=caller_sp-256
    for address,value in ((sp,213),(sp+4,213),(sp+8,width-246),(sp+12,16)):
        write(memory,address,value)
    assert hit(85,esp=sp,eax=backing,edx=surface,ebx=0,ecx=0) == "gc"
    assert hit(86,esp=sp+16) == "gc"
    geometry=trace.pixels.expected_outline(width,height,scale=scale,world=(world,world),scroll=(regs["$t12"],regs["$t13"]),
                 minimap_origin=(width-246,16),minimap_size=(214,214))
    left,top,right,bottom=geometry["rect"]
    sp=caller_sp-512;write(memory,sp,bottom);write(memory,sp+4,0x4C)
    assert hit(87,esp=sp,eax=surface,edx=left,ebx=top,ecx=right) == "gc"
    assert hit(88,esp=sp+12,eax=1) == "gc"
    assert hit(89,esp=caller_sp-172,eax=1) == "gc"
    assert hit(90) == "gc"
    assert hit(91,esp=caller_sp-24) == "gc"
    assert hit(92,esp=caller_sp,eax=0xDEADBEEF) is None
    return observed,memory,regs,snapshots


def complete_log(packet, *, stop_before=False):
    events=initial_fixture.initial_events(packet["resolution"],framed=True)
    initial_log,_=initial_fixture.fixture(events,resolution=packet["resolution"],stage=probe.STAGE,close="")
    initial_log=initial_log.replace(initial_fixture.SHA,packet["candidate_sha256"])
    # Bind the synthetic trace's EIPs to the actual emitted extra, without
    # asserting this temporary log is runtime evidence.
    for number,va in re.findall(r'^bp(7[0-7]) ([0-9a-f]{8}) ',packet["initial_probe"],re.M|re.I):
        initial_log=initial_log.replace(f"eip={initial_fixture.SITES[int(number)]:08x}",f"eip={int(va,16):08x}")
    count=sum((row["size"]+47)//48 for row in packet["native_spans"])
    start=["MMSC_BYTE_SEGMENT_PASS"]*count+[f"MMSC_BOUND stage={packet['stage']} resolution={packet['resolution']} candidate_sha256={packet['candidate_sha256']} target=({packet['requested_scroll'][0]},{packet['requested_scroll'][1]})"]
    width,height=map(int,packet["resolution"].split("x"))
    old=[f"SURFDUMP_READY redraw_seq=4 surface=20000000 size=({width},{height}) base=21000000 bytes={width*height}",
         "PTILE_TRACE_CLOSED tid=abc eip=00406fa0 esp=00100100","SURFDUMP_HOST_READY"]
    rows=command_fixture(packet,stop_before=stop_before)[0]
    return ("\n".join(start)+"\n"+initial_log+"\n".join(old+rows)+"\n").encode("ascii")


class ScrollProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes()
        cls.candidates={};cls.packets={}
        for resolution,target in (("1024x768",(11,17)),("802x602",(90,93))):
            candidate=probe.builder.build_candidate(cls.original,resolution,minimap_viewport=True)[0]
            cls.candidates[resolution]=candidate
            cls.packets[resolution]=probe.build_packet(cls.original,candidate,candidate_sha256=probe.sha(candidate),
                stage=probe.STAGE,resolution=resolution,requested_scroll=target)

    def kwargs(self, resolution="1024x768"):
        packet=self.packets[resolution]
        return dict(original=self.original,candidate=self.candidates[resolution],packet=packet,
                    **{key:packet[key].encode("ascii") for key in ("initial_probe","before_commands","continue_commands")})

    def test_actual_image_source_and_whole_command_reconstruction(self):
        for resolution,packet in self.packets.items():
            self.assertFalse(packet["runtime_ready"])
            self.assertFalse(packet["manual_input_proof"])
            for field in ("initial_probe","before_commands","continue_commands"):
                self.assertEqual(probe.sha(packet[field].encode("ascii")),packet[field+"_sha256"])
                self.assertLess(max(map(len,packet[field].splitlines())),4096)
            self.assertIn("bd *\n",packet["before_commands"])
            self.assertNotIn(r'.printf \"MMSC_BEGIN',packet["before_commands"].split("bd 93\n")[-1])
            self.assertIn('.printf "MMSC_BEGIN',packet["before_commands"])
            self.assertNotIn("r eip=0040dc10",packet["continue_commands"])
            self.assertIn("r eip=0040b0e0",packet["continue_commands"])
            self.assertNotIn("ed 005202e4",packet["continue_commands"])
            self.assertNotIn("SendInput",packet["continue_commands"])
            self.assertEqual(packet["breakpoint_commands"]["82"]["va"],0x40DC10)

    def test_wrong_original_candidate_stage_resolution_and_targets_reject(self):
        candidate=self.candidates["1024x768"]
        base=dict(candidate_sha256=probe.sha(candidate),stage=probe.STAGE,resolution="1024x768",requested_scroll=(11,17))
        for change in ({"stage":probe.STAGE+"-unknown"},{"resolution":"800x600"},{"candidate_sha256":"a"*64},
                       {"requested_scroll":(True,17)},{"requested_scroll":(-1,17)},{"requested_scroll":(11,100)}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                probe.build_packet(self.original,candidate,**(base|change))
        changed=bytearray(candidate);changed[0xD0B2]^=1
        with self.assertRaises(ValueError):
            probe.build_packet(self.original,bytes(changed),**(base|{"candidate_sha256":probe.sha(changed)}))
        with self.assertRaises(ValueError):
            probe.build_packet(bytes([self.original[0]^1])+self.original[1:],candidate,**base)

    def test_actual_emitted_commands_and_strict_whole_trace(self):
        for resolution,packet in self.packets.items():
            for phase in ("before","after"):
                log=complete_log(packet,stop_before=phase=="before")
                result=trace.evaluate_trace(log,**self.kwargs(resolution),phase=phase)
                self.assertTrue(result["passed"],result["failures"])
                self.assertFalse(result["runtime_ready"])
            rows,memory,regs,_=command_fixture(packet)
            self.assertEqual(trace.producer.sha(self.candidates[resolution]),packet["candidate_sha256"])
            self.assertEqual(int.from_bytes(bytes(memory[0x544CFC+i] for i in range(4)),"little"),320<<6)
            self.assertEqual(int.from_bytes(bytes(memory[0x544D00+i] for i in range(4)),"little"),240<<6)
            self.assertIn("result=deadbeef",next(row for row in rows if row.startswith("MMSC_CALLBACK_RETURN")))
            self.assertEqual(rows[-1],"MMSC_HOST_READY phase=after")

    def test_every_native_command_rejects_wrong_phase_thread_or_stack(self):
        packet=self.packets["1024x768"]
        _,_,_,snapshots=command_fixture(packet)
        for number,(memory,regs) in snapshots.items():
            for key,delta in (("$t0",99),("$tid",1),("esp",16),("eip",1)):
                with self.subTest(bp=number,key=key):
                    mem=Memory(memory);reg=regs.copy();reg[key]+=delta
                    for index in range(20):
                        mem.setdefault(reg["esp"]+index,0)
                    observed=[]
                    result=run(packet["breakpoint_commands"][str(number)]["body"],mem,reg,set(),observed)
                    # Repair/draw entry SP is native-call dependent: only its
                    # exact return, not an invented absolute entry SP, is bound.
                    if key == "esp" and number in (85,87):
                        continue
                    self.assertEqual(result,"q",observed)

    def test_preflight_rejects_before_native_input_write_and_scale4_is_source_selected(self):
        packet=self.packets["1024x768"]
        cases=(("register","eip",0x406FA1),("register","$t13",3),("memory",0x5202E4,0),
               ("memory",0x5202E0,0),("memory",0x52334C,0),("memory",0x200000B8,0x50EEC4),
               ("memory",0x5199D8,0x4617A0),("memory",0x52698C,1),("memory",0x10023EC7,5),
               ("memory",0x1002230F,0),("memory",0x100222E0,10),("memory",0x100222E8,99),
               ("memory",0x523F54,4),("memory",0x54512C,9))
        for mutation in cases:
            with self.subTest(mutation=mutation):
                result,memory,_,rows=command_fixture(packet,mutations=(mutation,))
                self.assertEqual(result,"q",rows)
                self.assertFalse(any("MMSC_HOST_READY" in row for row in rows))
                self.assertEqual(int.from_bytes(bytes(memory[0x544CFC+i] for i in range(4)),"little"),320<<6)
        rows,_,_,_=command_fixture(packet,world=50,scale=4,gate_value=1)
        self.assertIn("scale=4",next(row for row in rows if row.startswith("MMSC_STATE")))
        self.assertIn("observed=1 replacement=1",next(row for row in rows if row.startswith("MMSC_GATE")))

    def test_missing_duplicate_reordered_malformed_and_case_changed_rows_fail(self):
        packet=self.packets["1024x768"];log=complete_log(packet);lines=log.splitlines(keepends=True)
        indices=[i for i,line in enumerate(lines) if line.startswith(b"MMSC_")]
        for index in indices:
            with self.subTest(missing=index):
                report=trace.evaluate_sequence(b"".join(lines[:index]+lines[index+1:]),packet)
                self.assertFalse(report["sequence_passed"])
            with self.subTest(duplicate=index):
                report=trace.evaluate_sequence(b"".join(lines[:index]+[lines[index]]+lines[index:]),packet)
                self.assertFalse(report["sequence_passed"])
                self.assertEqual(len(report["raw_records"]),len(indices)+1)
        for suffix in (b"MMSC_GATE invalid\n",b"mmsc_host_ready phase=after\n",b"MMSC_HOST_READY phase=after",b"AV_SURFDUMP\n"):
            self.assertFalse(trace.evaluate_sequence(log+suffix,packet)["sequence_passed"])
        for left,right in zip(indices,indices[1:]):
            if lines[left] == lines[right]:
                continue
            swapped=lines.copy();swapped[left],swapped[right]=swapped[right],swapped[left]
            self.assertFalse(trace.evaluate_sequence(b"".join(swapped),packet)["sequence_passed"])

    def test_control_identity_geometry_and_restore_mutations_fail(self):
        packet=self.packets["1024x768"];log=complete_log(packet)
        changes=((b"observed=0",b"observed=2"),(b"replacement=1",b"replacement=0"),(b"forced=1",b"forced=0"),
                 (b"expected=(11,17)",b"expected=(12,17)"),(b"caller=0040b0e5",b"caller=0040b0e6"),
                 (b"color=4c",b"color=4d"),(b"repair_count=1",b"repair_count=2"),(b"draw_count=1",b"draw_count=0"),
                 (b"MMSC_GATE tid=abc",b"MMSC_GATE tid=abd"),(b"map=20000000",b"map=0051d4c0"),(b"scale=2",b"scale=4"))
        for old,new in changes:
            with self.subTest(change=old):
                self.assertIn(old,log)
                self.assertFalse(trace.evaluate_sequence(log.replace(old,new,1),packet)["sequence_passed"])
        bad=log.replace(b"MMSC_MOUSE_RESTORED values=(5000,3c00)",b"MMSC_MOUSE_RESTORED values=(5001,3c00)")
        self.assertNotEqual(log,bad)
        self.assertFalse(trace.evaluate_sequence(bad,packet)["sequence_passed"])

    def test_whole_packet_commands_and_initial_trace_fail_closed(self):
        packet=self.packets["1024x768"];log=complete_log(packet)
        for key in ("initial_probe","before_commands","continue_commands"):
            args=self.kwargs();args[key]+=b".echo unauthorized\n"
            self.assertFalse(trace.evaluate_trace(log,**args)["passed"])
        args=self.kwargs();args["packet"]=copy.deepcopy(packet);args["packet"]["requested_scroll"]=[12,17]
        self.assertFalse(trace.evaluate_trace(log,**args)["passed"])
        for bad in (log.replace(b"PTILE_STATUS hook=full_converge status=1",b"PTILE_STATUS hook=full_converge status=0",1),
                    log.replace(b"PTILE_TRACE_CLOSED tid=abc",b"PTILE_TRACE_CLOSED tid=abd"),
                    log.replace(b"SURFDUMP_HOST_READY\n",b"",1),
                    log.replace(b"SURFDUMP_READY redraw_seq=4",b"SURFDUMP_READY redraw_seq=3")):
            self.assertFalse(trace.evaluate_trace(bad,**self.kwargs())["passed"])
        late=next(line for line in log.splitlines() if line.startswith(b"PTILE_EVENT"))
        self.assertFalse(trace.evaluate_trace(log+late+b"\n",**self.kwargs())["passed"])
        self.assertFalse(trace.evaluate_sequence(log+b"\xff\n",packet)["sequence_passed"])

    def pixel_fixture(self,resolution="1024x768",*,backing_value=17):
        packet=self.packets[resolution];log=complete_log(packet)
        sequence=trace.evaluate_sequence(log,packet)
        self.assertTrue(sequence["sequence_passed"],sequence["failures"])
        width,height=map(int,resolution.split("x"));mx=width-246;my=16
        backing=bytes([backing_value])*214*214
        frame=bytearray(width*height)
        for y in range(214):
            frame[(my+y)*width+mx:(my+y)*width+mx+214]=backing[y*214:(y+1)*214]
        before=bytearray(frame);after=bytearray(frame)
        rectangles=((804,56,835,80),(806,56,837,80)) if resolution == "1024x768" else ((582,56,607,75),(740,206,763,223))
        for buffer,rect in zip((before,after),rectangles):
            left,top,right,bottom=rect
            for x in range(left,right+1):
                buffer[top*width+x]=76;buffer[bottom*width+x]=76
            for y in range(top,bottom+1):
                buffer[y*width+left]=76;buffer[y*width+right]=76
        kwargs=self.kwargs(resolution)|dict(before_frame=bytes(before),after_frame=bytes(after),before_backing=backing,after_backing=backing,receipts={})
        for which,buffer in (("before",before),("after",after)):
            s=sequence["surfaces"][which];state=sequence["states"][which];boundary=sequence["boundaries"][which]
            kwargs["receipts"][which]=dict(phase=which,packet_sha256=probe.packet_hash(packet),candidate_sha256=packet["candidate_sha256"],
                initial_probe_sha256=packet["initial_probe_sha256"],before_commands_sha256=packet["before_commands_sha256"],
                continue_commands_sha256=packet["continue_commands_sha256"],log_prefix_bytes=boundary["prefix_bytes"],log_prefix_sha256=boundary["prefix_sha256"],
                tid=state["tid"],eip=state["eip"],esp=state["esp"],map=s["map"],base=s["base"],backing=s["backing"],bbase=s["bbase"],
                width=width,height=height,pitch=width,bwidth=214,bheight=214,bpitch=214,frame_sha256=probe.sha(buffer),backing_sha256=probe.sha(backing))
        return log,kwargs

    def test_actual_buffers_verify_erasure_and_fractional_far_edge(self):
        for resolution in self.packets:
            log,args=self.pixel_fixture(resolution)
            result=trace.audit_erasure(log,**args)
            self.assertTrue(result["passed"],result["failures"])
            self.assertGreater(result["evidence"]["informative_old_only_pixels"],0)
            self.assertEqual(result["evidence"]["old_only_pixels"],result["evidence"]["repaired_old_only_pixels"])
            self.assertFalse(result["runtime_ready"])

    def test_stale_outline_forged_receipts_changed_backing_and_inconclusive_white_fail(self):
        log,args=self.pixel_fixture()
        cases=[]
        for key,value in (("frame_sha256","f"*64),("candidate_sha256","f"*64),("packet_sha256","f"*64),
                          ("log_prefix_bytes",1),("log_prefix_sha256","f"*64),("pitch",1023),("base",0),("tid",1)):
            bad=copy.deepcopy(args);bad["receipts"]["after"][key]=value;cases.append((key,bad))
        stale=copy.deepcopy(args);buffer=bytearray(stale["after_frame"]);buffer[56*1024+804]=76
        stale["after_frame"]=bytes(buffer);stale["receipts"]["after"]["frame_sha256"]=probe.sha(buffer);cases.append(("stale_old_border",stale))
        missing=copy.deepcopy(args);missing["receipts"].pop("before");cases.append(("missing_before_receipt",missing))
        backing=copy.deepcopy(args);raw=bytes([18])+backing["after_backing"][1:];backing["after_backing"]=raw
        backing["receipts"]["after"]["backing_sha256"]=probe.sha(raw);cases.append(("changed_backing",backing))
        for name,bad in cases:
            with self.subTest(name=name):
                self.assertFalse(trace.audit_erasure(log,**bad)["passed"])
        white_log,white=self.pixel_fixture(backing_value=76)
        report=trace.audit_erasure(white_log,**white)
        self.assertFalse(report["passed"])
        self.assertTrue(any("inconclusive" in failure for failure in report["failures"]))

    def test_actual_repair_coverage_required_even_when_after_pixels_look_clean(self):
        log,args=self.pixel_fixture()
        narrow=log.replace(b"rect=(0,0,213,213) dest=(778,16)",b"rect=(0,0,0,0) dest=(778,16)")
        sequence=trace.evaluate_sequence(narrow,args["packet"])
        self.assertTrue(sequence["sequence_passed"],sequence["failures"])
        for which in ("before","after"):
            boundary=sequence["boundaries"][which]
            args["receipts"][which]["log_prefix_bytes"]=boundary["prefix_bytes"]
            args["receipts"][which]["log_prefix_sha256"]=boundary["prefix_sha256"]
        report=trace.audit_erasure(narrow,**args)
        self.assertFalse(report["passed"])
        self.assertTrue(any("repairs do not cover" in failure for failure in report["failures"]))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline source/stack fixtures for the explicitly synthetic layout probe.

No game/debugger/process is launched and no current evidence is written.
Native references in the user-owned clash95.asm: sub_40A400 lines 15337-15361,
sub_40A460 lines 15384-15399, sub_419D60 lines 40260-40274, and sub_419DC0
lines 40330-40407. The setup return is reached independently of the input
branch at 40B119-40B12B. This probe proves geometry only, never native input.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct

import hd_layout_summary as layout
import test_hd_layout_summary as old_fixtures

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "probes/cdb/ui/clash95_combined_layout_geometry_extra.cdb"
HISTORICAL_PROBE = ROOT / "probes/cdb/ui/clash95_hd_layout_extra.cdb"
ORIGINAL_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"


def command_at(text: str, address: str) -> str:
    rows = [line for line in text.splitlines() if re.match(rf"bp(?: /1)? {address} ", line)]
    assert len(rows) == 1, (address, rows)
    return rows[0]


def test_setup_return_is_the_verified_native_insertion_point() -> None:
    # Complete native instructions at the insertion point and its continuations.
    instructions = {
        0x40A42C: bytes.fromhex("e8 cf e2 00 00 89 c8 c3"),
        0x40A460: bytes.fromhex("a1 e0 02 52 00 a3 30 12 51 00 b8 40 1d 51 00 e8 4c f9 00 00"),
        0x419D60: bytes.fromhex("51 89 c1 81 38 80 02 00 00 7c 02 59 c3 ff 51 1c 59 c3"),
        0x419B88: bytes.fromhex("a1 fc 4c 54 00 8a 0d 2c 51 54 00 8b 13 d3 f8 31 f6 39 d0 0f 8c 5c 01 00 00"),
    }
    setup = instructions[0x40A42C]
    assert 0x40A42C + 5 + struct.unpack_from("<i", setup, 1)[0] == 0x418700
    assert setup[5:] == b"\x89\xc8\xc3"  # MOV EAX,ECX; RET, not an instruction interior.
    scan = instructions[0x40A460]
    assert 0x40A46F + 5 + struct.unpack_from("<i", scan, 16)[0] == 0x419DC0
    # The redraw helper preserves ECX and reaches its real draw only when x<clip.
    assert instructions[0x419D60][9:13] == bytes.fromhex("7c 02 59 c3")
    assert instructions[0x419D60][13:] == bytes.fromhex("ff 51 1c 59 c3")
    # X below the first descriptor branches outside before the click gate.
    outside = instructions[0x419B88]
    assert 0x419B9B + 6 + struct.unpack_from("<i", outside, 21)[0] == 0x419CFD
    original = Path(r"C:\Clash\clash95.exe")
    if not original.is_file():
        print("native byte references: original unavailable; synthetic instruction checks retained")
        return
    data = original.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ORIGINAL_SHA256
    for address, expected in instructions.items():
        assert data[address-0x400C00:address-0x400C00+len(expected)] == expected, hex(address)


def test_bounded_context_and_neutral_geometry_boundary() -> None:
    text = PROBE.read_text(encoding="utf-8")
    trigger, resume = command_at(text, "0040A431"), command_at(text, "0040A433")
    assert trigger.startswith("bp /1 ") and resume.startswith("bp /1 ")
    assert "bp /1 0040A460" not in text
    assert "proof_class=forced_geometry_only input_proof=false visible_proof=false promotion_ready=false" in text
    for clause in (
        "(@$t14 != 0)", "(poi(0052030c) != 0)", "(wo(poi(005202e0)) == 0n800)",
        "(wo(poi(005202e0)+2) == 0n600)", "(poi(00511230) == poi(005202e0))",
        "(poi(00419d65) == 0n800)", "(poi(00419d8e) == 0n800)",
        "(poi(00511e65) == 004191f0)", "((poi(00544cfc)>>by(0054512c)) < 0n608)",
        "(poi(00544d04) == 0)", "(by(005451c0) == 0)", "(@$t6 == 0)", "(@$t18 == 0)",
    ):
        assert clause in trigger, clause
    writes = re.findall(r"(?:^|[;{}])\s*(e[bwdq]\s+[^;{}]+)", text, re.MULTILINE)
    assert [write.strip() for write in writes] == ["ed @esp 0040a460", "ed @esp+4 0040a433"], writes
    assert not re.search(r"\.call\b|^\s*g\s*$|HDLAYOUT_INPUT_|SendInput|PostMessage", text, re.MULTILINE)
    assert not re.search(r"r\s+@\$t(?:6|7|10|11|12|13|14|15|16|17|18|19)\s*=", text)
    # Geometry telemetry is byte-for-byte the same as the historical probe.
    historical = HISTORICAL_PROBE.read_text(encoding="utf-8")
    for address in ("0040B7AE", "0040892B", "0040A400", "00419DA7", "00419D60", "00419D6D", "00419DC0"):
        assert command_at(text, address) == command_at(historical, address)


def test_synthetic_call_stack_restores_original_mov_result_and_context() -> None:
    text = PROBE.read_text(encoding="utf-8")
    trigger, resume = command_at(text, "0040A431"), command_at(text, "0040A433")
    saves = dict(re.findall(r"r @\$t(\d+) = @(eax|ebx|ecx|edx|esi|edi|ebp|efl);", trigger))
    restores = dict(re.findall(r"r (eax|ebx|ecx|edx|esi|edi|ebp|efl)=@\$t(\d+);", resume))
    # Execute the captured data flow with distinct values; helpers may clobber
    # every general register. The displaced MOV overwrites EAX with saved ECX.
    original = {name: 0x100 + index * 0x101 for index, name in enumerate(("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "efl"))}
    saved = {slot: original[register] for slot, register in saves.items()}
    restored = {register: saved[slot] for register, slot in restores.items()}
    expected = {**original, "eax": original["ecx"]}
    assert restored == expected
    assert "r esp=@esp-8; ed @esp 0040a460; ed @esp+4 0040a433;" in trigger
    original_esp = 0x0010FF00
    memory = {original_esp - 8: 0x40A460, original_esp - 4: 0x40A433, original_esp: 0x40B7B3}
    esp = original_esp - 8
    # 419D60's ECX push/pop and native 40A460->419DC0 frame balance internally.
    assert memory[esp] == 0x40A460; esp += 4
    assert memory[esp] == 0x40A433; esp += 4
    assert esp == original_esp and memory[esp] == 0x40B7B3
    assert "r eip=00419d60" in trigger and "r @$t0 = 0;" in resume


def test_existing_geometry_parser_keeps_independent_missing_evidence_failures() -> None:
    prefix = "HDLAYOUT_SYNTHETIC_GEOMETRY proof_class=forced_geometry_only input_proof=false\n"
    invoke = "HDLAYOUT_PANEL_REDRAW_INVOKE desc=00511e49 x=736 y=560 helper=00419d60 return=0040a460\n"
    allowed = "HDLAYOUT_PANEL_REDRAW_ALLOWED desc=00511e49 x=736 y=560 clip=800 draw=004191f0 render=0a30eeb0 map_surface=0a30eeb0\n"
    source = prefix + old_fixtures.PASS_LOG + invoke + allowed
    def summarize(value):
        return layout.build_summary(Path("synthetic-fixture-only.log"), layout.parse_text(value))
    report = summarize(source)
    assert report["passed"] and report["redraw_clip_proved"]
    assert not summarize(source.replace(allowed, ""))["passed"]
    assert not summarize(source.replace("clip=800 draw=", "clip=640 draw="))["passed"]
    assert not summarize("\n".join(line for line in source.splitlines() if "PANEL_HITSCAN" not in line))["passed"]
    assert not summarize(source.replace(invoke, ""))["redraw_clip_proved"]
    assert not summarize(source + "AV_SURFDUMP\n")["passed"]


if __name__ == "__main__":
    test_setup_return_is_the_verified_native_insertion_point()
    test_bounded_context_and_neutral_geometry_boundary()
    test_synthetic_call_stack_restores_original_mov_result_and_context()
    test_existing_geometry_parser_keeps_independent_missing_evidence_failures()
    print("combined layout synthetic geometry probe tests: PASS (offline only)")

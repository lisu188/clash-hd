"""Source tests for the disclosed continuity extras of the hidden successor session."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import hd_multires_route_extras as extras

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / extras.FORCED_SAVE_TEMPLATE).read_bytes()


def spec(load_slot=0, save_slot=7):
    return extras.prepare({"name": "forced-save", "load_slot": load_slot, "save_slot": save_slot},
                          route="map-idle", duration=120)


def log(*, load_slot=0, save_slot=7, eax="1", extra_loads=1, call_first=False):
    load = (f"HDSESSION_LOADSAVE selected_arg={load_slot} selected_global={load_slot} accept=1 choice=5 "
            "gd=03f30030")
    call = (f"HDCONT_SAVE_CALL slot={save_slot} load_slot={load_slot} gd=03f30030 player=0 scroll=(10,17) "
            "tick=13047100")
    returned = f"HDCONT_SAVE_RETURNED slot={save_slot} eax={eax} tick=13047104"
    rows = [load] * extra_loads + [call, returned]
    if call_first:
        rows = [call, returned, load]
    return "\r\n".join(["EXACT_CANONICAL_PASS", *rows, "SOAK_ROUTE_START route_ticks=7680"]) + "\r\n"


class ForcedSaveTests(unittest.TestCase):
    def test_prepare_fixes_route_slots_mechanism_and_files(self):
        prepared = spec()
        self.assertEqual(prepared["mechanisms"], {"save": "cdb_forced_save_game"})
        self.assertEqual(prepared["sites"], ["0040B0C1"])
        self.assertEqual((prepared["pre_files"], prepared["post_files"]), (["save/0.dat"], ["save/7.dat"]))
        self.assertEqual(spec(7, 8)["pre_files"], ["save/7.dat"])
        for request, message in (
                ({"name": "forced-save", "load_slot": 0}, "exactly"),
                ({"name": "other", "load_slot": 0, "save_slot": 7}, "exactly"),
                ({"name": "forced-save", "load_slot": 0, "save_slot": 7, "extra": 1}, "exactly"),
                ({"name": "forced-save", "load_slot": 0, "save_slot": 0}, "save_slot"),
                ({"name": "forced-save", "load_slot": 7, "save_slot": 7}, "overwrite"),
                ({"name": "forced-save", "load_slot": 10, "save_slot": 7}, "load_slot"),
                ({"name": "forced-save", "load_slot": True, "save_slot": 7}, "load_slot"),
                ({"name": "forced-save", "load_slot": 0, "save_slot": 7.0}, "save_slot")):
            with self.assertRaisesRegex(ValueError, message):
                extras.prepare(request, route="map-idle", duration=120)
        for route, duration in (("map-idle", 600), ("map-pan", 600), ("menu-idle", 120)):
            with self.assertRaisesRegex(ValueError, "120 s map-idle"):
                extras.prepare({"name": "forced-save", "load_slot": 0, "save_slot": 7}, route=route, duration=duration)

    def test_compose_substitutes_slots_on_its_one_declared_site_and_restores_registers(self):
        text = extras.compose(spec(7, 8), TEMPLATE)
        lines = text.split("\r\n")
        self.assertEqual(extras.breakpoint_sites(text), ["0040B0C1"])
        self.assertNotRegex(text, r"__[A-Z0-9_]+__")
        call = [line for line in lines if line.startswith("bp 0040B0C1 ")][0]
        self.assertIn("r eax=0n8; r edx=00543d28; r eip=004443E0", call)
        self.assertIn("ed @esp 0040B0C1", call)
        self.assertIn("HDCONT_SAVE_CALL slot=8 load_slot=7", call)
        self.assertIn("r @$t16 = @eax; r @$t17 = @edx", call)
        self.assertIn("r eax=@$t16; r edx=@$t17", call)
        self.assertTrue(call.endswith('; gc"'))
        for forbidden in ("SendInput", "PostMessage", "005451c0", "00544cfc", "00544d04", "$t14", "$t18", "$t19"):
            self.assertNotIn(forbidden, text)
        self.assertEqual([line for line in lines if line.startswith("r @$t")],
                         ["r @$t15 = 0", "r @$t16 = 0", "r @$t17 = 0"])
        for mutated, message in ((TEMPLATE.replace(b"__SAVE_SLOT__", b"8"), "__SAVE_SLOT__"),
                                 (TEMPLATE + b"g\n", "resume"),
                                 (TEMPLATE.replace(b"r @$t15 = 0\n", b"r @$t15 = 0\n\n"), "blank"),
                                 (TEMPLATE + b"bp 0040B0C3 \"gc\"\n", "declared sites"),
                                 (TEMPLATE + b".echo __OTHER__\n", "placeholder"),
                                 (TEMPLATE + "é".encode(), "ASCII"),
                                 (b"x" * (extras.MAX_TEMPLATE_BYTES + 1), "bound")):
            with self.assertRaisesRegex(ValueError, message):
                extras.compose(spec(), mutated)

    def test_state_digest_masks_only_the_code_derived_pointer_fields(self):
        # The two record arrays are contiguous and their pointer is each record's trailing dword.
        (first, first_stride, first_count, first_field), (second, second_stride, second_count, second_field) = \
            extras.POINTER_FIELDS
        self.assertEqual(first + first_count * first_stride, second)
        self.assertEqual(second + second_count * second_stride, 0x87D56)
        self.assertEqual((first_field + 4, second_field + 4), (first_stride, second_stride))
        self.assertEqual(extras.SAVE_BYTES, 586414)
        save = bytes((index * 13) % 253 for index in range(extras.SAVE_BYTES))
        digest = extras.state_digest(save)

        def flipped(offset):
            return save[:offset] + bytes([save[offset] ^ 0xFF]) + save[offset + 1:]

        masked = [extras.SAVE_HEADER_BYTES + base + index * stride + field + byte
                  for base, stride, count, field in extras.POINTER_FIELDS for index in (0, count - 1) for byte in (0, 3)]
        for offset in masked:
            self.assertEqual(extras.state_digest(flipped(offset)), digest, offset)
        for offset in (0, 15, extras.SAVE_HEADER_BYTES, masked[0] - 1, masked[1] + 1, extras.SAVE_BYTES - 1):
            self.assertNotEqual(extras.state_digest(flipped(offset)), digest, offset)
        for size in (extras.SAVE_BYTES - 1, extras.SAVE_BYTES + 1):
            with self.assertRaisesRegex(ValueError, "16-byte name"):
                extras.state_digest(bytes(size))

    def test_markers_bind_the_requested_slots_order_and_native_success(self):
        fields, failures = extras.observe(spec(), log(extra_loads=3))
        self.assertEqual(failures, [])
        self.assertEqual(fields["save_call"], dict(slot=7, load_slot=0, gd=0x03F30030, player=0, scroll=[10, 17],
                                                   tick=13047100))
        self.assertEqual(fields["save_returned"], dict(slot=7, eax=1, tick=13047104))
        self.assertEqual(len(fields["loads"]), 3)
        self.assertEqual(extras.observe(spec(7, 8), log(load_slot=7, save_slot=8))[1], [])
        for text, message in ((log(eax="0"), "success"),
                              (log(save_slot=8), "another slot"),
                              (log(load_slot=1), "requested slot"),
                              (log(extra_loads=0), "requested slot"),
                              (log(call_first=True), "follow"),
                              (log().replace("HDCONT_SAVE_RETURNED", "HDCONT_SAVE_MISSING"), "exactly one call"),
                              (log() + log().split("\r\n", 3)[2] + "\r\n", "exactly one call")):
            self.assertTrue(any(message in failure for failure in extras.observe(spec(), text)[1]), message)
        # The echoed command text carries format strings, never a printed marker.
        echoed = "0:000> " + extras.compose(spec(), TEMPLATE).split("\r\n")[-1] + "\r\n"
        self.assertTrue(extras.observe(spec(), echoed)[1])


if __name__ == "__main__":
    unittest.main()

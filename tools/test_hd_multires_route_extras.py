"""Source tests for the disclosed continuity extras of the hidden successor session."""
from __future__ import annotations

from pathlib import Path
import re
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


TURN_TEMPLATE = (ROOT / extras.FORCED_TURN_TEMPLATE).read_bytes()
TURN_REQUEST = {"name": "forced-turn", "load_slot": 0, "before_slot": 5, "after_slot": 6}


def turn_spec():
    return extras.prepare(dict(TURN_REQUEST), route="map-idle", duration=120)


def turn_log(*, players=(1, 2, 3, 0), day=1, banner=None, release=None, fail=None, after_eax="1", done=True):
    """One day of forced turns as the template prints it, with optional disclosed overrides."""
    rows = [f"HDTURN_START player=0 day={day} gd=07ee0030 tick=1000 active=(1,1,1,1,0)",
            "HDTURN_SAVE_CALL slot=5 player=0 day=1", "HDTURN_SAVE_RETURNED slot=5 eax=1"]
    for advance, player in enumerate(players, 1):
        before = players[advance - 2] if advance > 1 else 0
        rows.append(f"HDTURN_NEXT_CALL advance={advance} player={before} day={day} tick={1000 + 128 * advance}")
        if player == 0:
            rows += [f"HDTURN_DAY_INCREMENT advance={advance} player=0 day={day + 1}",
                     *([banner] if banner else []), f"HDTURN_BANNER_EXIT player=0 day={day + 1} polls=8",
                     "HDTURN_RELEASE_WAIT_ENTRY wait=1 player=0 day=2", *([release] if release else []),
                     "HDTURN_RELEASE_RETURN player=0 day=2 left=8 right=1"]
        rows.append(f"HDTURN_NEXT_RETURN advance={advance} player={player} day={day + (player == 0)} "
                    f"tick={1040 + 128 * advance}")
    rows += [f"HDTURN_FULL_DAY_RETURNED initial_day={day} final_day={day + 1} player=0 advances={len(players)}",
             "HDTURN_SAVE_CALL slot=6 player=0 day=2", f"HDTURN_SAVE_RETURNED slot=6 eax={after_eax}"]
    if done:
        rows.append(f"HDTURN_DONE player=0 day={day + 1} advances={len(players)}")
    if fail:
        rows.append(f"HDTURN_FAIL {fail}")
    return "\r\n".join(["EXACT_CANONICAL_PASS", *rows]) + "\r\n"


class ForcedTurnTests(unittest.TestCase):
    def test_prepare_fixes_route_slots_mechanisms_and_sites(self):
        spec = turn_spec()
        self.assertEqual(spec["mechanisms"], {"turn": "cdb_forced_next_player", "save": "cdb_forced_save_game",
                                              "turn_input": "cdb_bounded_stale_button_result_overrides"})
        self.assertEqual((spec["pre_files"], spec["post_files"]), (["save/0.dat"], ["save/5.dat", "save/6.dat"]))
        self.assertNotIn("save_slot", spec)
        # The forced-save spec is unchanged by the turn extra.
        self.assertEqual(sorted(spec_save := extras.prepare({"name": "forced-save", "load_slot": 0, "save_slot": 7},
                                                            route="map-idle", duration=120)),
                         ["load_slot", "mechanisms", "name", "post_files", "pre_files", "request", "save_slot",
                          "sites", "template"])
        self.assertEqual(spec_save["sites"], ["0040B0C1"])
        for request, message in ((dict(TURN_REQUEST, before_slot=6), "distinct"),
                                 (dict(TURN_REQUEST, after_slot=0), "after_slot"),
                                 (dict(TURN_REQUEST, extra=1), "exactly"),
                                 ({key: TURN_REQUEST[key] for key in ("name", "load_slot", "before_slot")}, "exactly")):
            with self.assertRaisesRegex(ValueError, message):
                extras.prepare(request, route="map-idle", duration=120)
        with self.assertRaisesRegex(ValueError, "120 s map-idle"):
            extras.prepare(dict(TURN_REQUEST), route="map-pan", duration=600)

    def test_compose_restores_registers_around_every_forced_call_on_declared_sites(self):
        text = extras.compose(turn_spec(), TURN_TEMPLATE)
        self.assertEqual(sorted(extras.breakpoint_sites(text)), sorted(extras.TURN_SITES))
        self.assertNotRegex(text, r"__[A-Z0-9_]+__")
        driver = [line for line in text.split("\r\n") if line.startswith("bp 0040B0C8 ")][0]
        # Three forced calls (before save, nextPlayer, after save) each save all registers; one restore serves all.
        self.assertEqual(driver.count("r @$t6 = @eax; r @$t8 = @ebx; r @$t9 = @ecx; r @$t10 = @edx; r @$t11 = @esi; "
                                      "r @$t15 = @edi; r @$t16 = @ebp; r @$t17 = @efl; ed 004003cc @esp;"), 3)
        self.assertEqual(driver.count("r eax=@$t6; r ebx=@$t8; r ecx=@$t9; r edx=@$t10; r esi=@$t11; r edi=@$t15; "
                                      "r ebp=@$t16; r efl=@$t17"), 1)
        self.assertIn("r eax=0n5; r edx=00543d28; r eip=004443E0", driver)
        self.assertIn("r eax=0n6; r edx=00543d28; r eip=004443E0", driver)
        self.assertIn("r eax=0; r edx=5; r ecx=0; r eip=0040AA60", driver)
        self.assertLess(len(driver), 4096)
        # Scratch stays inside the header padding free in every candidate.
        for address in {int(value, 16) for value in re.findall(r"\b(004003[0-9a-f]{2})\b", text)}:
            self.assertTrue(0x4003C0 <= address <= 0x4003FC, hex(address))
        for forbidden in ("$t7", "$t13", "$t14", "$t18", "$t19", "00400040", "005451c0 ", "SendInput"):
            self.assertNotIn(forbidden, text)

    def test_markers_bind_the_day_cycle_saves_and_disclosed_overrides(self):
        fields, failures = extras.observe(turn_spec(), turn_log())
        self.assertEqual(failures, [])
        self.assertEqual([row[1] for row in fields["returns"]], [1, 2, 3, 0])
        self.assertEqual(fields["full_day"], dict(initial_day=1, final_day=2, player=0, advances=4))
        self.assertEqual(fields["overrides"], dict(banner=0, left=0, right=0))
        self.assertEqual([(save["slot"], save["eax"]) for save in fields["saves"]], [(5, 1), (6, 1)])
        overridden = extras.observe(turn_spec(), turn_log(
            banner="HDTURN_FORCED_BANNER_ACK poll=8 value=1",
            release="HDTURN_FORCED_RELEASE button=left poll=8 value=0"))[0]["overrides"]
        self.assertEqual(overridden, dict(banner=1, left=1, right=0))
        for text, message in ((turn_log(fail="release_return_stack"), "release_return_stack"),
                              (turn_log(after_eax="0"), "after save"),
                              (turn_log(done=False), "one completion"),
                              (turn_log().replace("HDTURN_NEXT_RETURN advance=2", "HDTURN_NEXT_RETURN advance=9"),
                               "numbered return"),
                              (turn_log().replace("HDTURN_DAY_INCREMENT", "HDTURN_DAY_MISSING"), "day increment"),
                              (turn_log().replace("final_day=2", "final_day=3"), "exactly one new day"),
                              (turn_log().replace("HDTURN_START player=0", "HDTURN_START player=1"), "player 0"),
                              (turn_log().replace("HDTURN_RELEASE_RETURN", "HDTURN_RELEASE_LOST"), "release wait")):
            self.assertTrue(any(message in failure for failure in extras.observe(turn_spec(), text)[1]), message)
        echoed = "0:000> " + [line for line in extras.compose(turn_spec(), TURN_TEMPLATE).split("\r\n")
                              if line.startswith("bp 0040B0C8")][0] + "\r\n"
        self.assertTrue(extras.observe(turn_spec(), echoed)[1])


if __name__ == "__main__":
    unittest.main()

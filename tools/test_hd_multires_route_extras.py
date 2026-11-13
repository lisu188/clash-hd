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


CAMPAIGN_TEMPLATE = (ROOT / extras.FORCED_CAMPAIGN_TEMPLATE).read_bytes()
CAMPAIGN_REQUEST = {"name": "forced-campaign", "load_slot": 0, "before_slot": 3, "after_slot": 4, "days": 3}


def campaign_spec(**changes):
    return extras.prepare(dict(CAMPAIGN_REQUEST, **changes), route="map-idle", duration=120)


def campaign_log(days=3, *, returned=None, final=None, done_days=None):
    """``days`` forced day transitions as the campaign template prints them."""
    rows = [f"HDCAMP_START days={days} player=0 day=1 gd=07ee0030 tick=1000 active=(1,1,1,1,0)",
            "HDCAMP_SAVE_CALL slot=3 player=0 day=1", "HDCAMP_SAVE_RETURNED slot=3 eax=1"]
    advance = 0
    for day in range(1, (returned if returned is not None else days) + 1):
        for player in (1, 2, 3, 0):
            advance += 1
            rows.append(f"HDCAMP_NEXT_CALL advance={advance} player={(player - 1) % 4} day={day} tick={1000 + 128 * advance}")
            if player == 0:
                rows += [f"HDCAMP_DAY_INCREMENT advance={advance} player=0 day={day + 1}",
                         f"HDCAMP_BANNER_EXIT player=0 day={day + 1} polls=2",
                         f"HDCAMP_RELEASE_WAIT_ENTRY wait={day} player=0 day={day + 1}",
                         f"HDCAMP_RELEASE_RETURN player=0 day={day + 1} left=3 right=1"]
            rows.append(f"HDCAMP_NEXT_RETURN advance={advance} player={player} day={day + (player == 0)} "
                        f"tick={1040 + 128 * advance}")
            if player == 0:
                rows.append(f"HDCAMP_DAY_RETURNED days={day} day={day + 1} player=0 advances={advance}")
    final_day = final if final is not None else 1 + days
    rows += [f"HDCAMP_FULL_DAY_RETURNED initial_day=1 final_day={final_day} player=0 advances={advance}",
             "HDCAMP_SAVE_CALL slot=4 player=0 day=4", "HDCAMP_SAVE_RETURNED slot=4 eax=1",
             f"HDCAMP_DONE player=0 day={final_day} advances={advance} days={done_days if done_days is not None else days}"]
    return "\r\n".join(["EXACT_CANONICAL_PASS", *rows]) + "\r\n"


class ForcedCampaignTests(unittest.TestCase):
    def test_prepare_bounds_days_and_reuses_the_turn_mechanisms_and_sites(self):
        spec = campaign_spec()
        self.assertEqual((spec["name"], spec["days"], spec["template"]), ("forced-campaign", 3, extras.FORCED_CAMPAIGN_TEMPLATE))
        self.assertEqual((spec["mechanisms"], spec["sites"]), (extras.TURN_MECHANISMS, list(extras.TURN_SITES)))
        self.assertEqual(spec["post_files"], ["save/3.dat", "save/4.dat"])
        self.assertEqual(campaign_spec(days=2)["days"], 2)
        for changes, message in ((dict(days=1), "2 or 3 days"), (dict(days=4), "2 or 3 days"),
                                 (dict(days=True), "2 or 3 days"), (dict(after_slot=3), "distinct")):
            with self.assertRaisesRegex(ValueError, message):
                campaign_spec(**changes)
        with self.assertRaisesRegex(ValueError, "exactly"):
            extras.prepare({key: CAMPAIGN_REQUEST[key] for key in ("name", "load_slot", "before_slot", "after_slot")},
                           route="map-idle", duration=120)

    def test_compose_substitutes_days_on_the_turn_sites_within_free_scratch(self):
        text = extras.compose(campaign_spec(), CAMPAIGN_TEMPLATE)
        self.assertEqual(sorted(extras.breakpoint_sites(text)), sorted(extras.TURN_SITES))
        self.assertNotRegex(text, r"__[A-Z0-9_]+__")
        driver = [line for line in text.split("\r\n") if line.startswith("bp 0040B0C8 ")][0]
        self.assertIn(".if (poi(004003f0) == 0n3)", driver)
        self.assertIn("(0n5 * 0n3)", driver)
        self.assertLess(len(driver), 4096)
        for address in {int(value, 16) for value in re.findall(r"\b(004003[0-9a-f]{2})\b", text)}:
            self.assertTrue(0x4003C0 <= address <= 0x4003FC, hex(address))
        right = [line for line in text.split("\r\n") if line.startswith("bp 004609FC ")][0]
        # The right override belongs to the loop's eighth iteration, which the left test counts.
        self.assertIn(".if ((poi(004003dc) == 0n8) & (@eax != 0))", right)

    def test_markers_bind_every_requested_day_and_the_final_return(self):
        fields, failures = extras.observe(campaign_spec(), campaign_log())
        self.assertEqual(failures, [])
        self.assertEqual([row[0] for row in fields["days_returned"]], [1, 2, 3])
        self.assertEqual(fields["full_day"], dict(initial_day=1, final_day=4, player=0, advances=12))
        self.assertEqual((fields["banner_exits"], fields["release_waits"], fields["release_returns"]), (3, 3, 3))
        for text, message in ((campaign_log(returned=2, final=4), "every requested day needs"),
                              (campaign_log(final=3), "requested new days"),
                              (campaign_log(done_days=2), "requested new days"),
                              (campaign_log().replace("HDCAMP_START days=3", "HDCAMP_START days=2"), "requested days on")):
            self.assertTrue(any(message in failure for failure in extras.observe(campaign_spec(), text)[1]), message)
        # Turn and campaign markers never stand in for each other.
        self.assertTrue(extras.observe(turn_spec(), campaign_log())[1])
        self.assertTrue(extras.observe(campaign_spec(), turn_log())[1])


class NeutralMouseTests(unittest.TestCase):
    def test_requests_without_the_key_keep_their_exact_spec(self):
        neutral = extras.prepare(dict(TURN_REQUEST, neutral_mouse=True), route="map-idle", duration=120)
        base = turn_spec()
        self.assertEqual({key: value for key, value in neutral.items()
                          if key not in ("request", "neutral_mouse", "sites", "mechanisms")},
                         {key: value for key, value in base.items() if key not in ("request", "sites", "mechanisms")})
        self.assertEqual(neutral["sites"], base["sites"] + ["0047C02C"])
        self.assertEqual(neutral["mechanisms"], dict(base["mechanisms"], mouse_state="cdb_neutral_failed_mouse_reads"))
        self.assertNotIn("neutral_mouse", base)
        for value in (False, 1, "true"):
            with self.assertRaisesRegex(ValueError, "exactly true"):
                extras.prepare(dict(TURN_REQUEST, neutral_mouse=value), route="map-idle", duration=120)

    def test_failed_reads_alone_are_zeroed_and_must_be_observed(self):
        spec = extras.prepare({"name": "forced-save", "load_slot": 4, "save_slot": 2, "neutral_mouse": True},
                              route="map-idle", duration=120)
        text = extras.compose(spec, TEMPLATE)
        self.assertEqual(sorted(extras.breakpoint_sites(text)), ["0040B0C1", "0047C02C"])
        neutral = [line for line in text.split("\r\n") if line.startswith("bp 0047C02C ")][0]
        self.assertIn(".if ((@eax & 0x80000000) != 0) { ed @esp+0x50 0; ed @esp+0x54 0; ed @esp+0x58 0; "
                      "ed @esp+0x5c 0;", neutral)
        self.assertNotIn("0047C02C", extras.compose(spec_without := extras.prepare(
            {"name": "forced-save", "load_slot": 4, "save_slot": 2}, route="map-idle", duration=120), TEMPLATE))
        log = ("HDSESSION_LOADSAVE selected_arg=4 selected_global=4 accept=1 choice=5 gd=03f30030\r\n"
               "HDCONT_SAVE_CALL slot=2 load_slot=4 gd=03f30030 player=0 scroll=(10,17) tick=5\r\n"
               "HDCONT_SAVE_RETURNED slot=2 eax=1 tick=6\r\n")
        self.assertEqual(extras.observe(spec_without, log)[1], [])
        self.assertTrue(any("neutralized" in item for item in extras.observe(spec, log)[1]))
        fields, failures = extras.observe(spec, log + "HDNEUTRAL_MOUSE_READ hresult=8007000c\r\n")
        self.assertEqual((fields["neutral_mouse_reads"], failures), (1, []))
        self.assertNotIn("neutral_mouse_reads", extras.observe(spec_without, log)[0])
        self.assertTrue(extras.observe(spec, log + "HDNEUTRAL_MOUSE_READ hresult=00000000\r\n")[1])



PAN_RETRY_TEMPLATE = (ROOT / extras.PAN_RETRY_TEMPLATE).read_bytes()


def pan_retry_spec(duration=7200, **request):
    return extras.prepare({"name": "pan-retry", **request}, route="map-pan", duration=duration)


class PanRetryTests(unittest.TestCase):
    def test_prepare_fixes_the_soak_pan_routes_mechanism_sites_and_untouched_slot(self):
        for duration in (600, 1800, 7200):
            spec = pan_retry_spec(duration)
            self.assertEqual((spec["name"], spec["load_slot"], spec["pre_files"], spec["post_files"]),
                             ("pan-retry", 0, ["save/0.dat"], []))
            self.assertEqual(spec["sites"], ["00407D4A", "00407D57", "00407D69", "00407E95"])
            self.assertEqual(spec["mechanisms"], {"pan_retry": "cdb_soak_pan_step_rearmed_when_handler_declines"})
        for route, duration in (("map-idle", 7200), ("map-idle", 120), ("map-pan", 120), ("menu-idle", 600)):
            with self.subTest(route=route, duration=duration), self.assertRaisesRegex(ValueError, "map-pan route"):
                extras.prepare({"name": "pan-retry"}, route=route, duration=duration)
        with self.assertRaisesRegex(ValueError, "exactly"):
            pan_retry_spec(load_slot=0)
        self.assertEqual(pan_retry_spec(neutral_mouse=True)["sites"],
                         ["00407D4A", "00407D57", "00407D69", "00407E95", "0047C02C"])

    def test_compose_rearms_only_the_soak_held_step_at_each_declining_branch(self):
        text = extras.compose(pan_retry_spec(neutral_mouse=True), PAN_RETRY_TEMPLATE)
        self.assertEqual(extras.breakpoint_sites(text), ["00407D4A", "00407D57", "00407D69", "00407E95", "0047C02C"])
        branches = {line.split()[1]: line for line in text.split("\r\n") if line.startswith("bp 00407")}
        # At the join the soak's key is still held and the scroll is exactly the previous step's position.
        unmoved = ("(poi(poi(005202e4)+0n140008) == ((poi(00400058) + (((((poi(00400050)+3) & 3) == 1) | "
                   "(((poi(00400050)+3) & 3) == 2)) * poi(00400068))) & 0xffffffff)) & "
                   "(poi(poi(005202e4)+0n140012) == ((poi(0040005c) + (((((poi(00400050)+3) & 3) == 2) | "
                   "(((poi(00400050)+3) & 3) == 3)) * poi(0040006c))) & 0xffffffff))")
        for site, condition in (("00407D4A", "(@eax <= @edx)"), ("00407D57", "(@eax != 0)"),
                                ("00407D69", "(@eax != 0)"), ("00407E95", unmoved)):
            line = branches[site]
            # Only while the soak holds its key, and only when the native branch is about to decline it.
            self.assertTrue(line.startswith(f'bp {site} ".if ((poi(00400040) == 6) & {condition}) {{'), site)
            # The soak's own step state and this extra's header-padding scratch are the only writes.
            self.assertEqual(set(re.findall(r"\b(?:ed|eb|ew) (\S+)", line)),
                             {"004003c0", "004003c4", "004003c8", "004003cc", "00400040"}, site)
            self.assertIn("ed 00400040 5;", line)
            self.assertIn("(poi(004003c8) < 0n64)", line)
            self.assertIn("(poi(004003cc) < 0n32)", line)
            self.assertTrue(line.endswith('}; gc"'), site)
        # No scroll field, keyboard state, register or native variable is written by the extra.
        self.assertNotRegex(text, r"\b(?:ed|eb|ew) (?:0054|0052|poi)|\br e[a-z]x=|005451cc")

    def test_no_template_echoes_a_line_that_begins_with_a_marker_name(self):
        # CDB prints each .echo text as its own log line; one that began with a soak or extra
        # marker name could read as a malformed row or a marker.
        token = re.compile(r"[A-Z][A-Z0-9]*_[A-Z0-9_]+(?:\s|$)")
        for template in extras.SOURCES:
            with self.subTest(template=template):
                lines = (ROOT / template).read_text(encoding="ascii").replace("\r\n", "\n").split("\n")
                echoed = [line[len(".echo "):] for line in lines if line.startswith(".echo ")]
                self.assertTrue(echoed)
                self.assertEqual([line for line in echoed if token.match(line)], [])

    def test_markers_bind_bounded_rearms_and_fail_at_the_limit(self):
        spec = pan_retry_spec(neutral_mouse=True)
        reads = "HDNEUTRAL_MOUSE_READ hresult=8007000c\r\n"
        self.assertEqual(extras.observe(spec, reads), ({"rearms": [], "limits": [], "neutral_mouse_reads": 1}, []))
        rows = ("\r\nHDPAN_REARM reason=rate_limit step=41 count=1 total=1 value=3\r\n"
                "\r\nHDPAN_REARM reason=input_flag step=41 count=2 total=2 value=1\r\n"
                "\r\nHDPAN_REARM reason=alt_held step=90 count=1 total=3 value=80\r\n"
                "\r\nHDPAN_REARM reason=not_taken step=91 count=1 total=4 value=8000\r\n")
        fields, failures = extras.observe(spec, reads + rows)
        self.assertEqual(failures, [])
        self.assertEqual([(row["reason"], row["step"], row["count"], row["total"], row["value"])
                          for row in fields["rearms"]],
                         [("rate_limit", 41, 1, 1, 3), ("input_flag", 41, 2, 2, 1), ("alt_held", 90, 1, 3, 0x80),
                          ("not_taken", 91, 1, 4, 0x8000)])
        many = "".join(f"HDPAN_REARM reason=rate_limit step={n} count=1 total={n + 1} value=1\r\n" for n in range(33))
        for text, message in ((rows + "HDPAN_REARM_LIMIT step=41\r\n", "exhausted"),
                              (rows.replace("total=2", "total=5"), "running log"),
                              (rows.replace("count=1 total=1", "count=65 total=1"), "running log"),
                              (many, "running log")):
            with self.subTest(message=message):
                self.assertTrue(any(message in item for item in extras.observe(spec, reads + text)[1]))
        # Echoed commands are not markers.
        echoed = '0:000> .printf "HDPAN_REARM reason=rate_limit step=1 count=1 total=1 value=1"\r\n'
        self.assertEqual(extras.observe(spec, reads + echoed)[0]["rearms"], [])



PAN_PRESS_TEMPLATE = (ROOT / extras.PAN_PRESS_TEMPLATE).read_bytes()


class PanPressTests(unittest.TestCase):
    def test_prepare_shares_the_retry_routes_and_slot_with_its_own_sites(self):
        for duration in (600, 1800, 7200):
            spec = extras.prepare({"name": "pan-press"}, route="map-pan", duration=duration)
            self.assertEqual((spec["name"], spec["load_slot"], spec["pre_files"], spec["post_files"], spec["template"]),
                             ("pan-press", 0, ["save/0.dat"], [], extras.PAN_PRESS_TEMPLATE))
            self.assertEqual(spec["sites"], ["00406FA2", "00407D26", "00407D4A", "00407D57", "00407D69", "00407E95"])
            self.assertEqual(spec["mechanisms"], {"pan_press": "cdb_extra_pressed_soak_pan_key_until_taken"})
        for route, duration in (("map-idle", 7200), ("map-pan", 120)):
            with self.assertRaisesRegex(ValueError, "map-pan route"):
                extras.prepare({"name": "pan-press"}, route=route, duration=duration)
        with self.assertRaisesRegex(ValueError, "exactly"):
            extras.prepare({"name": "pan-press", "load_slot": 0}, route="map-pan", duration=600)
        # pan-retry keeps its exact spec.
        self.assertEqual(extras.prepare({"name": "pan-retry"}, route="map-pan", duration=600)["sites"],
                         ["00407D4A", "00407D57", "00407D69", "00407E95"])

    def test_each_breakpoint_acts_on_only_the_one_state_it_expects(self):
        spec = extras.prepare({"name": "pan-press", "neutral_mouse": True}, route="map-pan", duration=7200)
        text = extras.compose(spec, PAN_PRESS_TEMPLATE)
        self.assertEqual(extras.breakpoint_sites(text), spec["sites"])
        lines = {line.split()[1]: line for line in text.split("\r\n") if line.startswith("bp ")}
        held = "(((by(00545294) | by(00545297) | by(00545299) | by(0054529c)) & 0x80) != 0)"
        # The redraw takeover: a due soak step (5) becomes the private state 8, nothing else.
        self.assertEqual(lines["00406FA2"],
                         'bp 00406FA2 ".if (poi(00400040) == 5) { ed 00400040 8; ed 004003d0 (poi(004003d0)+1) }; gc"')
        # The press: only state 8; clears the four arrows, presses toward the target, hands back state 6.
        press = lines["00407D26"]
        self.assertTrue(press.startswith('bp 00407D26 ".if (poi(00400040) == 8) { eb 00545294 00; eb 00545297 00; '
                                         'eb 00545299 00; eb 0054529c 00; '), press)
        self.assertTrue(press.endswith('; ed 00400040 6 }; gc"'), press)
        self.assertEqual(sorted(set(__import__("re").findall(r"eb (005452\w\w) 80", press))),
                         ["00545294", "00545297", "00545299", "0054529c"])
        # Re-arms: only state 6 with a held key, back to the private state.
        for site in ("00407D4A", "00407D57", "00407D69"):
            self.assertTrue(lines[site].startswith(f'bp {site} ".if ((poi(00400040) == 6) & {held} & '), site)
        # The join re-arms an unmoved held key and otherwise releases it after the move.
        join = lines["00407E95"]
        self.assertTrue(join.startswith(f'bp 00407E95 ".if ((poi(00400040) == 6) & {held}) {{ .if (('), join)
        self.assertTrue(join.endswith('.else { eb 00545294 00; eb 00545297 00; eb 00545299 00; eb 0054529c 00 } }; gc"'),
                        join)
        for site in ("00407D4A", "00407D57", "00407D69", "00407E95"):
            self.assertIn("ed 00400040 8;", lines[site])
            self.assertNotIn("ed 00400040 5", lines[site])
        # No breakpoint ever hands the soak its own due state, and nothing writes scroll fields.
        self.assertNotIn("ed 00400040 5", text)
        self.assertNotRegex(text, r"\b(?:ed|eb|ew) (?:0052|poi)|\br e[a-z]x=")

    def test_markers_share_the_retry_grammar(self):
        spec = extras.prepare({"name": "pan-press", "neutral_mouse": True}, route="map-pan", duration=600)
        log = ("HDNEUTRAL_MOUSE_READ hresult=8007000c\r\n"
               "\r\nHDPAN_REARM reason=not_taken step=91 count=1 total=1 value=8000\r\n")
        fields, failures = extras.observe(spec, log)
        self.assertEqual((failures, [row["reason"] for row in fields["rearms"]]), ([], ["not_taken"]))
        self.assertTrue(extras.observe(spec, log + "HDPAN_REARM_LIMIT step=91\r\n")[1])


PAN_STEADY_TEMPLATE = (ROOT / extras.PAN_STEADY_TEMPLATE).read_bytes()


def pan_steady_spec(duration=7200):
    return extras.prepare({"name": "pan-steady", "neutral_mouse": True}, route="map-pan", duration=duration)


class PanSteadyTests(unittest.TestCase):
    def test_prepare_keeps_the_press_sites_and_discloses_both_additions(self):
        for duration in (600, 1800, 7200):
            spec = extras.prepare({"name": "pan-steady"}, route="map-pan", duration=duration)
            self.assertEqual((spec["name"], spec["load_slot"], spec["pre_files"], spec["post_files"], spec["template"]),
                             ("pan-steady", 0, ["save/0.dat"], [], extras.PAN_STEADY_TEMPLATE))
            self.assertEqual(spec["sites"], ["00406FA2", "00407D26", "00407D4A", "00407D57", "00407D69", "00407E95"])
            self.assertEqual(spec["mechanisms"], {
                "pan_press": "cdb_extra_pressed_soak_pan_key_until_taken",
                "pan_schedule": "cdb_extra_logged_pan_step_at_its_slot_within_128_ticks",
                "debug_output": "cdb_newline_after_each_debuggee_debug_string"})
        self.assertIn(extras.PAN_STEADY_TEMPLATE, extras.SOURCES)
        for route, duration in (("map-idle", 7200), ("map-pan", 120), ("menu-idle", 120)):
            with self.assertRaisesRegex(ValueError, "map-pan route"):
                extras.prepare({"name": "pan-steady"}, route=route, duration=duration)
        for request in ({"name": "pan-steady", "load_slot": 0}, {"name": ["pan-steady"]}, {"name": "pan-steadier"}):
            with self.assertRaisesRegex(ValueError, "exactly"):
                extras.prepare(request, route="map-pan", duration=600)
        # The earlier pan extras keep their exact specs.
        self.assertEqual(extras.prepare({"name": "pan-press"}, route="map-pan", duration=600)["mechanisms"],
                         {"pan_press": "cdb_extra_pressed_soak_pan_key_until_taken"})
        self.assertEqual(extras.prepare({"name": "pan-retry"}, route="map-pan", duration=600)["mechanisms"],
                         {"pan_retry": "cdb_soak_pan_step_rearmed_when_handler_declines"})

    def test_takeover_slots_a_step_only_on_time_off_a_heartbeat_and_in_sequence(self):
        spec = pan_steady_spec()
        text = extras.compose(spec, PAN_STEADY_TEMPLATE)
        self.assertEqual(extras.breakpoint_sites(text), spec["sites"])
        lines = text.split("\r\n")
        sites = {line.split()[1]: line for line in lines if line.startswith("bp ")}
        # The press, the re-arms, the release and the neutral mouse are pan-press's own lines.
        press = extras.compose(extras.prepare({"name": "pan-press", "neutral_mouse": True}, route="map-pan",
                                              duration=7200), PAN_PRESS_TEMPLATE)
        press_sites = {line.split()[1]: line for line in press.split("\r\n") if line.startswith("bp ")}
        for site in ("00407D26", "00407D4A", "00407D57", "00407D69", "00407E95", "0047C02C"):
            self.assertEqual(sites[site], press_sites[site], site)
        # The interval is the session's and the allowance the legacy grader's; the soak restarts
        # each interval at its redraw tick, logs that tick and prints heartbeats on this mask.
        interval, allowance = extras.PAN_INTERVAL_TICKS, extras.PAN_SLOT_ALLOWANCE_TICKS
        self.assertEqual((interval, allowance, extras.SOAK_HEARTBEAT_MASK), (640, 128, 0x7FF))
        self.assertIn("\nMAP_PAN_INTERVAL_SEC = 10\n",
                      (ROOT / "tools/hd_multires_hidden_session.py").read_text(encoding="utf-8"))
        self.assertIn("maximum_gap = interval_ticks + 2 * 64",
                      (ROOT / "tools/hd_soak_report.py").read_text(encoding="utf-8"))
        soak = (ROOT / "probes/cdb/soak/clash95_hidden_soak_route_extra.cdb").read_text(encoding="ascii")
        for assumed in ("(poi(00400048) & 0x7ff) == 0", "ed 00400054 poi(0040004c); ed 00400040 5;",
                        "poi(00400054)-poi(00400044)", "ed 00400054 poi(00400044);"):
            self.assertIn(assumed, soak)
        takeover = sites["00406FA2"]
        # Only a due soak step (5) is taken over; step 0 starts from the route's own start tick.
        self.assertTrue(takeover.startswith('bp 00406FA2 ".if (poi(00400040) == 5) { ed 00400040 8; '
                                            '.if (poi(00400050) == 0) { ed 004003d0 0; ed 004003d4 poi(00400044) }; '),
                        takeover)
        # The slot: in sequence, off a heartbeat redraw, and from the interval to the allowance late.
        slotted = ("(poi(004003d0) == poi(00400050)) & ((poi(00400048) & 0x7ff) != 0) & "
                   f"(poi(00400054) >= (poi(004003d4) + 0n{interval})) & "
                   f"(poi(00400054) <= (poi(004003d4) + 0n{interval + allowance}))")
        self.assertIn(f".if ({slotted}) {{ ed 00400054 (poi(004003d4) + 0n{interval}); "
                      "ed 004003d8 (poi(004003d8)+1) } .else { ed 004003dc (poi(004003dc)+1); "
                      ".if (poi(004003e0) < 0n32) {", takeover)
        self.assertIn(r'.printf \"\\nHDPAN_TICK_KEPT step=%d expected=%d beat=%d late=%d count=%d\\n\", '
                      "poi(00400050), poi(004003d0), ((poi(00400048) & 0x7ff) == 0), "
                      f"(poi(00400054) - poi(004003d4) - 0n{interval}), poi(004003dc)", takeover)
        # Either way the logged tick becomes the next slot's base and the next step is expected.
        self.assertTrue(takeover.endswith('; ed 004003d4 poi(00400054); ed 004003d0 (poi(00400050)+1) }; gc"'), takeover)
        # It writes the soak's step state and last-pan tick and its own header-padding scratch only.
        self.assertEqual(set(re.findall(r"\b(?:ed|eb|ew) (\S+)", takeover)),
                         {"00400040", "00400054", "004003d0", "004003d4", "004003d8", "004003dc", "004003e0"})
        self.assertEqual(extras.PAN_KEPT_LOGGED, 32)
        for address in {int(value, 16) for value in re.findall(r"\b(004003[0-9a-f]{2})\b", text)}:
            self.assertTrue(0x4003C0 <= address <= 0x4003FC, hex(address))
        # No breakpoint hands the soak its own due state; no scroll field or register is written.
        self.assertNotIn("ed 00400040 5", text)
        self.assertNotRegex(text, r"\b(?:ed|eb|ew) (?:0052|poi)|\br e[a-z]x=")

    def test_every_debug_string_line_is_ended_and_nothing_is_filtered(self):
        lines = extras.compose(pan_steady_spec(600), PAN_STEADY_TEMPLATE).split("\r\n")
        # One event handler for every debuggee string, set before any breakpoint: an empty echo
        # ends the string's line, then execution continues as it was.
        self.assertEqual([line for line in lines if line.startswith(("sxe", "sxd", "sxn", "sxi", "sxr"))],
                         ['sxe -c ".echo; gc" out'])
        self.assertLess(lines.index('sxe -c ".echo; gc" out'),
                        min(index for index, line in enumerate(lines) if line.startswith("bp ")))
        self.assertFalse([line for line in lines if not line.startswith(".echo ") and ".ofilter" in line])
        # The earlier pan extras do not handle debug strings at all.
        for template in (PAN_RETRY_TEMPLATE, PAN_PRESS_TEMPLATE):
            self.assertNotIn(b"\nsxe ", template)

    def test_kept_tick_rows_are_a_bounded_running_log_with_a_reason_each(self):
        spec = pan_steady_spec(600)
        reads = "HDNEUTRAL_MOUSE_READ hresult=8007000c\r\n"
        self.assertEqual(extras.observe(spec, reads),
                         ({"rearms": [], "limits": [], "ticks_kept": [], "neutral_mouse_reads": 1}, []))
        rows = ("\r\nHDPAN_TICK_KEPT step=12 expected=12 beat=1 late=3 count=1\r\n"
                "\r\nHDPAN_TICK_KEPT step=40 expected=39 beat=0 late=-640 count=2\r\n"
                "\r\nHDPAN_TICK_KEPT step=77 expected=77 beat=0 late=129 count=3\r\n"
                "\r\nHDPAN_REARM reason=not_taken step=91 count=1 total=1 value=8000\r\n")
        fields, failures = extras.observe(spec, reads + rows)
        self.assertEqual(failures, [])
        self.assertEqual([(row["step"], row["expected"], row["beat"], row["late"], row["count"])
                          for row in fields["ticks_kept"]],
                         [(12, 12, 1, 3, 1), (40, 39, 0, -640, 2), (77, 77, 0, 129, 3)])
        self.assertEqual([row["reason"] for row in fields["rearms"]], ["not_taken"])
        many = "".join(f"HDPAN_TICK_KEPT step={n} expected={n} beat=1 late=1 count={n + 1}\r\n" for n in range(33))
        for text, message in ((rows.replace("count=2", "count=5"), "kept-tick"),
                              # A repeated step, and a row that shows no reason to keep its tick.
                              (rows.replace("step=40 expected=39", "step=12 expected=11"), "kept-tick"),
                              (rows.replace("beat=0 late=129", "beat=0 late=128"), "kept-tick"),
                              (many, "kept-tick"),
                              (rows + "HDPAN_REARM_LIMIT step=91\r\n", "exhausted")):
            with self.subTest(text=text[:60]):
                self.assertTrue(any(message in item for item in extras.observe(spec, reads + text)[1]))
        # pan-press observations keep their shape, and echoed commands are not markers.
        press = extras.prepare({"name": "pan-press", "neutral_mouse": True}, route="map-pan", duration=600)
        self.assertNotIn("ticks_kept", extras.observe(press, reads + rows)[0])
        echoed = '0:000> .printf "HDPAN_TICK_KEPT step=1 expected=1 beat=1 late=0 count=1"\r\n'
        self.assertEqual(extras.observe(spec, reads + echoed)[0]["ticks_kept"], [])


if __name__ == "__main__":
    unittest.main()

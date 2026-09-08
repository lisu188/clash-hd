"""Offline full-paint progress byte/stack/sequence fixtures; no CDB execution."""
from __future__ import annotations

import copy
from pathlib import Path
import unittest

import framed_full_progress_probe as diagnostic
from complete_hd_runtime_context import complete
from test_framed_minimap_integration import synthetic_main

ORIGINAL = Path("C:/Clash/clash95.exe")


class SequenceTests(unittest.TestCase):
    sites = dict(entry=0x418700, post_store=0x5638D1, returning=0x563A3D)

    def records(self, present=0, entry_sp=0x200000, seq=10):
        caller_ebp = 0xBAD
        rows = []
        for marker, eip, esp, ebp, value in (
            (diagnostic.MARKERS[0], self.sites["entry"], entry_sp, caller_ebp, present),
            (diagnostic.MARKERS[1], self.sites["post_store"], entry_sp-144, present, 1),
            (diagnostic.MARKERS[2], self.sites["returning"], entry_sp-52, caller_ebp, 0xDEADBEEF),
        ):
            rows.append(f"{marker} tid=1234 eip={eip:08x} esp={esp:08x} entry_esp={entry_sp:08x} "
                        f"caller=004167aa saved_ebp={ebp:08x} value={value:x} trace_seq={seq}")
        return rows

    def evaluate(self, records):
        return diagnostic.analyze_progress("\n".join(["PTILE_MAP_READY fixture", *records, "PTILE_TRACE_CLOSED fixture"]), self.sites)

    def test_native_eax_becomes_saved_ebp_and_return_restores_caller_frame(self):
        for present in (0, 1):
            report = self.evaluate(self.records(present))
            self.assertTrue(report["observation_sequence_complete"], report["failures"])
            call = report["calls"][0]
            self.assertEqual(call["posts"][0]["saved_ebp"], call["entry"]["value"])
            self.assertEqual(call["returns"][0]["saved_ebp"], call["entry"]["saved_ebp"])
            self.assertEqual(call["returns"][0]["value"], 0xDEADBEEF)
            self.assertFalse(report["acceptance"])

    def test_sequential_native_calls_can_reuse_stack_after_observed_return(self):
        records = self.records(0, seq=97) + self.records(1, seq=98)
        report = self.evaluate(records)
        self.assertTrue(report["observation_sequence_complete"], report["failures"])
        self.assertEqual(len(report["calls"]), 2)
        self.assertEqual([call["posts"][0]["saved_ebp"] for call in report["calls"]], [0, 1])

    def test_repeats_unmatched_progress_and_stack_or_flag_disagreements_fail(self):
        rows = self.records(0)
        for bad in (rows[:1]+rows, rows[:2]+rows[1:], rows[1:], rows[:-1],
                    [rows[0], rows[1].replace("001fff70", "001fff74"), rows[2]],
                    [rows[0], rows[1].replace("saved_ebp=00000000", "saved_ebp=00000001"), rows[2]],
                    [rows[0], rows[1], rows[2].replace("caller=004167aa", "caller=004167bb")]):
            report = self.evaluate(bad)
            self.assertFalse(report["observation_sequence_complete"], bad)
            self.assertEqual(len(report["records"]), len(bad), "do not deduplicate failures")


@unittest.skipUnless(ORIGINAL.is_file(), "user-owned original required; bytes stay in memory")
class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.image, cls.manifest, cls.extra = complete.build_candidate(cls.original, "800x600")
        cls.main = synthetic_main(cls.extra)
        cls.arguments = dict(candidate_sha256=complete.sha256(cls.image), stage=complete.STAGE,
                             resolution="800x600", rendered_probe=cls.main, candidate_manifest=cls.manifest)

    def test_bound_observer_keeps_every_existing_command_and_records_native_flags(self):
        report = diagnostic.build_diagnostic(self.original, self.image, **self.arguments)
        self.assertEqual(report["breakpoint_ids"], [83, 84, 85])
        self.assertFalse(report["acceptance"])
        self.assertEqual(report["observation_sites"]["post_store"], self.manifest["predecessor"]["base_candidate"]["base_candidate"]["status_vas"]["full_converge"]+4)
        self.assertIn("@esp+0n144", report["snippet"])
        self.assertIn("poi(@esp+8)", report["snippet"])
        self.assertIn("@ebp+0n36", report["snippet"])
        self.assertIn("@ebp, @eax, @$t9", report["snippet"])
        self.assertNotIn("PTILE_", report["snippet"])
        self.assertNotRegex(report["snippet"], r"(?:^|[;{}])\s*(?:e[bdwq]|r\s|b[dec]\s)")
        self.assertEqual(self.main.count(self.extra.strip()), 1)
        self.assertEqual(self.original, ORIGINAL.read_bytes())

    def test_unknown_candidate_manifest_or_occupied_id_and_site_rejected(self):
        for kwargs in (dict(stage=complete.STAGE+"-other"), dict(candidate_sha256="0"*64),
                       dict(first_breakpoint_id=82), dict(resolution="1024x768")):
            with self.assertRaises(ValueError):
                diagnostic.build_diagnostic(self.original, self.image, **(self.arguments | kwargs))
        for suffix in ('bp83 00401234 "gc"', 'bp84 00401234 "gc"', 'bp85 00401234 "gc"', 'bp86 00418700 "gc"'):
            modified = self.main.rstrip()[:-1] + suffix + "\ng\n"
            with self.assertRaises(ValueError):
                diagnostic.build_diagnostic(self.original, self.image, **(self.arguments | dict(rendered_probe=modified)))

    def test_changed_observation_instruction_or_wrapper_stack_contract_rejected(self):
        framed = self.manifest["predecessor"]["base_candidate"]["base_candidate"]
        sites = diagnostic.observation_sites(self.image, framed)
        for span in sites["spans"]:
            changed = bytearray(self.image); changed[span["offset"]] ^= 1
            with self.assertRaisesRegex(ValueError, "observation bytes differ"):
                diagnostic.observation_sites(bytes(changed), framed)
        changed = copy.deepcopy(framed); changed["layout_contract"]["full_entry_extra_stack_bytes"] = 56
        with self.assertRaisesRegex(ValueError, "stack contract differs"):
            diagnostic.observation_sites(self.image, changed)


if __name__ == "__main__":
    unittest.main()

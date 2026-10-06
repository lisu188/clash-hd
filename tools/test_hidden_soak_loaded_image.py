#!/usr/bin/env python3
"""Pure synthetic raw-read fixtures; optional original-backed work is in RAM.

No native adapters, game/debugger, file outputs, capture or acceptance is used.
Synthetic seams exercise comparisons only and cannot admit production recipes.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src" / "patcher"))
sys.path.insert(0, str(ROOT))
import hidden_soak_loaded_image as tool
import pe_extension as pe
import test_pe_extension as fixture

ORIGINAL = Path("C:/Clash/clash95.exe")
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def contract(candidate=None):
    return tool._make_contract(fixture.synthetic_pe() if candidate is None else candidate,
                              '["dict",[]]', b"synthetic preferred-only probe, never executed\n",
                              "classic", "800x600", "synthetic-source-comparison-only", "synthetic-v1",
                              {"fixture": digest(b"synthetic, no canonical production authority")}, pe)


def authority(bound, base=0x400000):
    plan = bound.plan()
    return tool.LoaderAuthority("1" * 32, plan["profile"], plan["resolution"], plan["stage"],
        plan["recipe_revision"], digest(bound.candidate), digest(bound.canonical_probe),
        plan["source_closure_sha256"],
        tool.Generation(100, 1000, "C:/tools/controller.exe", digest(b"controller")),
        tool.Generation(101, 2000, "C:/tools/cdb.exe", digest(b"debugger")),
        tool.Generation(102, 3000, "C:/ClashTests/isolated/candidate.exe", digest(bound.candidate)),
        "2" * 32, 1000, "3" * 32, 2000, base, 0x7ffd0000, 103, 0, 0)


def observations(bound, owned):
    """Independent complete loader model; never calls oracle expected bytes."""
    memory, _, fixups, _ = fixture.independent_image(bound.candidate)
    base_field = int.from_bytes(bound.candidate[60:64], "little") + 24 + 28
    preferred = int.from_bytes(memory[base_field:base_field + 4], "little")
    memory = fixture.rebase(memory, fixups, owned.image_base - preferred)
    chunks = [(owned.peb_address + 8, struct.pack("<I", owned.image_base))]
    for row in bound.plan()["immutable_scope"]["chunks"]:
        chunks.append((owned.image_base + row["rva"], bytes(memory[row["rva"]:row["rva"] + row["size"]])))
    reads = []
    for ordinal, (address, raw) in enumerate(chunks):
        stamp = owned.checkpoint_start_ns + ordinal * 10
        reads.append(tool.RawRead(ordinal, address, len(raw), len(raw), 0, raw, stamp + 1, stamp + 2,
                                  tool._phase(owned, stamp), tool._phase(owned, stamp + 3)))
    return tuple(reads)


class LoadedImageTests(unittest.TestCase):
    def setUp(self):
        self.bound = contract()
        self.owned = authority(self.bound)
        self.reads = observations(self.bound, self.owned)

    def compare(self, bound=None, owned=None, reads=None):
        result = tool._compare(self.bound if bound is None else bound, self.owned if owned is None else owned,
                               self.reads if reads is None else reads, pe)
        for name in tool.FALSE_CLAIMS:
            self.assertIs(result.report()[name], False, name)
        return result

    def rejected(self, *, bound=None, owned=None, reads=None):
        result = self.compare(bound, owned, reads)
        self.assertFalse(result.report()["source_comparison_passed"], result.report())
        self.assertTrue(result.report()["failures"])
        if reads is not None:
            self.assertIs(result.original_reads, reads)
        return result

    def test_complete_preferred_and_positive_negative_modulo_rebases(self):
        candidate = bytearray(fixture.synthetic_pe())
        struct.pack_into("<I", candidate, 0x401, 0xfffffff0)
        bound = contract(bytes(candidate))
        for base in (0x400000, 0x500000, 0x300000, 0x21000000):
            with self.subTest(base=base):
                owned = authority(bound, base)
                reads = observations(bound, owned)
                result = self.compare(bound, owned, reads)
                self.assertTrue(result.report()["source_comparison_passed"], result.report())
                self.assertIs(result.original_reads, reads)
                self.assertEqual(bound.plan()["immutable_scope"]["selected_highlow_rvas"], [0x1001, 0x1009, 0x1011])
                self.assertEqual(result.report()["observations"][2]["raw_sha256"], digest(reads[2].raw))

    def test_scope_is_complete_headers_and_executable_not_rw_or_whole_image(self):
        scope = self.bound.plan()["immutable_scope"]
        self.assertEqual(scope["ranges"], [dict(kind="headers", rva=0, size=0x400, file_offset=0, section=None),
             dict(kind="executable_raw", rva=0x1000, size=0x200, file_offset=0x400, section=0)])
        self.assertEqual(scope["checked_bytes"], 0x600)
        self.assertEqual(scope["excluded_nonexecutable_sections"],
                         [dict(rva=0x2000, size=0x1000, section=1), dict(rva=0x3000, size=0x200, section=2)])
        self.assertEqual(scope["excluded_unchecked_image_intervals"],
                         [dict(rva=0x400, size=0xc00), dict(rva=0x1200, size=0x2e00)])
        result = self.compare()
        self.assertIn("nonexecutable", result.report()["scope"])
        self.assertIn("readonly constants", result.report()["unverified_gaps"])

    def test_every_executable_zero_tail_is_required_and_never_normalized(self):
        data = bytearray(fixture.synthetic_pe())
        struct.pack_into("<I", data, 0x88 + 224 + 8, 0x600)
        bound = contract(bytes(data)); owned = authority(bound)
        reads = observations(bound, owned)
        self.assertEqual(bound.plan()["immutable_scope"]["ranges"][-1],
                         dict(kind="executable_zero_tail", rva=0x1200, size=0x400, file_offset=None, section=0))
        self.assertTrue(self.compare(bound, owned, reads).report()["source_comparison_passed"])
        raw = bytearray(reads[-1].raw); raw[0x211] = 1
        self.rejected(bound=bound, owned=owned, reads=reads[:-1] + (replace(reads[-1], raw=bytes(raw)),))
        self.rejected(bound=bound, owned=owned, reads=reads[:-1])

    def test_all_interior_bytes_and_header_imagebase_are_strict(self):
        for index, offset in ((1, 0x200), (1, 0xa4), (2, 0x133)):
            with self.subTest(index=index, offset=offset):
                raw = bytearray(self.reads[index].raw); raw[offset] ^= 1
                rows = list(self.reads); rows[index] = replace(rows[index], raw=bytes(raw))
                self.rejected(reads=tuple(rows))
        owned = authority(self.bound, 0x500000); reads = observations(self.bound, owned)
        raw = bytearray(reads[1].raw); struct.pack_into("<I", raw, 0x88 + 28, owned.image_base)
        self.rejected(owned=owned, reads=reads[:1] + (replace(reads[1], raw=bytes(raw)),) + reads[2:])

    def test_missing_duplicated_reordered_extra_and_rehashed_records_fail(self):
        attacks = [self.reads[:-1], self.reads[1:], self.reads + (self.reads[-1],),
                   (self.reads[0], self.reads[2], self.reads[1]),
                   (self.reads[0], self.reads[1], replace(self.reads[1], ordinal=2))]
        for rows in attacks:
            with self.subTest(ordinals=[row.ordinal for row in rows]): self.rejected(reads=rows)
        plan = self.bound.plan(); plan["immutable_scope"]["chunks"].pop()
        self.rejected(bound=replace(self.bound, plan_json=tool._canonical(plan)), reads=self.reads[:-1])

    def test_partial_native_failure_and_incompatible_counts_retain_exact_original(self):
        for changes in (dict(hresult=0x8000000d, returned_bytes=17, raw=self.reads[2].raw[:17]),
                        dict(returned_bytes=0), dict(raw=self.reads[2].raw[:-1]), dict(returned_bytes=9999)):
            with self.subTest(changes=list(changes)):
                row = replace(self.reads[2], **changes); rows = self.reads[:2] + (row,)
                result = self.rejected(reads=rows)
                self.assertIs(result.original_reads[-1], row)
                self.assertEqual(result.report()["observations"][-1]["returned_bytes"], row.returned_bytes)

    def test_phase_generation_architecture_probe_breakpoint_and_selection_fail(self):
        changes = [dict(system_pid=99), dict(system_tid=99), dict(engine_pid=1), dict(engine_tid=1),
                   dict(image_base=0x500000), dict(execution_status=1), dict(pointer64_hresult=0),
                   dict(probe_sequence=1), dict(breakpoint_sequence=1), dict(clock_epoch="4" * 32),
                   dict(run_id="5" * 32), dict(checkpoint_id="6" * 32),
                   dict(target=replace(self.owned.target, creation_filetime=3001)),
                   dict(debugger=replace(self.owned.debugger, image_sha256=digest(b"changed debugger"))),
                   dict(controller=replace(self.owned.controller, image_path="C:/other/controller.exe"))]
        for changeset in changes:
            with self.subTest(fields=list(changeset)):
                bad = replace(self.reads[1], phase_after=replace(self.reads[1].phase_after, **changeset))
                self.rejected(reads=self.reads[:1] + (bad,) + self.reads[2:])

    def test_clock_epoch_origin_order_and_hold_deadline_fail(self):
        for changes in (dict(begin_ns=self.reads[1].end_ns + 1), dict(end_ns=self.reads[1].begin_ns - 1),
                        dict(phase_before=replace(self.reads[1].phase_before, monotonic_ns=2000)),
                        dict(phase_after=replace(self.reads[1].phase_after, monotonic_ns=2000 + tool.MAX_HOLD_NS + 1))):
            with self.subTest(changes=list(changes)):
                self.rejected(reads=self.reads[:1] + (replace(self.reads[1], **changes),) + self.reads[2:])
        self.rejected(owned=replace(self.owned, clock_origin_ns=1500, checkpoint_start_ns=2500))

    def test_failed_native_phase_queries_reject_matching_stale_values_and_retain_original(self):
        original = self.reads[1]
        for receipt_side in ("phase_before", "phase_after"):
            phase = getattr(original, receipt_side)
            for index, query in enumerate(phase.native_queries):
                with self.subTest(side=receipt_side, query=query.name):
                    queries = list(phase.native_queries); queries[index] = replace(query, hresult=0x80004005)
                    bad = replace(original, **{receipt_side: replace(phase, native_queries=tuple(queries))})
                    reads = self.reads[:1] + (bad,) + self.reads[2:]
                    result = self.rejected(reads=reads)
                    self.assertEqual(result.report()["observations"][1][receipt_side + "_queries"][index]["hresult"], 0x80004005)
                    self.assertIs(result.original_reads[1], bad)
            for queries in (phase.native_queries[:-1], phase.native_queries[::-1], (),
                            (phase.native_queries[0],) * len(phase.native_queries)):
                self.rejected(reads=self.reads[:1] + (replace(original, **{receipt_side: replace(phase, native_queries=queries)}),) + self.reads[2:])
        with self.assertRaises(ValueError): replace(original.phase_before.native_queries[0], hresult=True)
        with self.assertRaises(ValueError): replace(original.phase_before, native_queries=list(original.phase_before.native_queries))

    def test_raw_pointer_request_ordinal_and_peb_value_fail(self):
        for changes in (dict(address=self.reads[1].address + 1), dict(requested_bytes=16), dict(ordinal=2)):
            with self.subTest(changes=list(changes)):
                self.rejected(reads=self.reads[:1] + (replace(self.reads[1], **changes),) + self.reads[2:])
        self.rejected(reads=(replace(self.reads[0], raw=struct.pack("<I", 0x500000)),) + self.reads[1:])
        self.rejected(owned=replace(self.owned, peb_address=0x401000))
        self.rejected(owned=replace(self.owned, image_base=0x7ffd0000))

    def test_independent_recipe_candidate_probe_and_source_authority_fail(self):
        for changes in (dict(profile="framed"), dict(resolution="802x602"), dict(stage="forged"),
                        dict(recipe_revision="forged"), dict(probe_sha256=digest(b"substituted")),
                        dict(source_closure_sha256=digest(b"substituted"))):
            with self.subTest(changes=list(changes)): self.rejected(owned=replace(self.owned, **changes))
        mutated = bytearray(self.bound.candidate); mutated[0x543] ^= 1
        self.rejected(bound=replace(self.bound, candidate=bytes(mutated)))
        self.rejected(bound=replace(self.bound, canonical_probe=b"forged probe\n"))
        with self.assertRaises(ValueError):
            replace(self.owned, candidate_sha256=digest(b"different candidate"))

    def test_typed_receipts_reject_json_booleans_coercion_and_invented_proof(self):
        self.rejected(owned=asdict(self.owned))
        self.rejected(reads=tuple(asdict(row) for row in self.reads))
        self.rejected(reads=list(self.reads))
        for changes in (dict(ordinal=True), dict(address="4194304"), dict(hresult=-(1 << 31) - 1), dict(raw=bytearray(b"a"))):
            with self.subTest(changes=list(changes)), self.assertRaises(ValueError): replace(self.reads[0], **changes)
        for changes in (dict(pid=True), dict(creation_filetime="3000"), dict(image_path="C:/../x.exe"), dict(image_path="C:/x.exe:stream")):
            with self.subTest(changes=list(changes)), self.assertRaises(ValueError): replace(self.owned.target, **changes)
        with self.assertRaises(TypeError): tool.LoaderAuthority(**asdict(self.owned), passed=True)
        for text in ('{"x":1,"x":1}', '{"x": NaN}', '{ "x":1}', '{"x":1.0}'):
            if text == '{"x":1.0}': continue  # JSON floats are rejected by native typed fields, not a generic parser.
            with self.subTest(text=text), self.assertRaises(ValueError): tool._json(text)

    def test_invalid_pe_wx_unbacked_overlay_nonpe_and_relocations_fail(self):
        mutations = [dict(offset=0x74, raw=struct.pack("<H", 0x8664)),
                     dict(offset=0x88 + 224 + 36, raw=struct.pack("<I", 0xe0000020)),
                     dict(offset=0x88 + 224 + 20, raw=struct.pack("<I", 0)),
                     dict(offset=0x608, raw=struct.pack("<H", 0x5001)),
                     dict(offset=0x60a, raw=struct.pack("<H", 0x3001)),
                     dict(offset=0x608, raw=struct.pack("<H", 0x31ff)),
                     dict(offset=0x608, raw=struct.pack("<H", 0x3fff))]
        for changes in mutations:
            data = bytearray(fixture.synthetic_pe()); at, raw = changes.values(); data[at:at + len(raw)] = raw
            with self.subTest(offset=at, raw=raw.hex()), self.assertRaises(Exception): tool._derive_plan(bytes(data), pe)
        for data in (b"invented accepted", fixture.synthetic_pe() + b"overlay"):
            with self.assertRaises(Exception): tool._derive_plan(data, pe)

    def test_fixed_chunks_keep_complete_cross_page_and_chunk_highlow_fields(self):
        payload = bytearray(b"\x90" * (tool.CHUNK_BYTES + 123))
        struct.pack_into("<I", payload, tool.CHUNK_BYTES - 1, 0x402008)
        records = (pe.CodeRelocation(tool.CHUNK_BYTES - 1, "abs32", 0x402008, "boundary fixture"),)
        candidate = pe._extend_verified_image(fixture.synthetic_pe(), code=bytes(payload), code_va=0x404000,
                    relocations=records, binding={"fixture": "pure"}).image
        bound = contract(candidate); owned = authority(bound, 0x500000)
        chunks = bound.plan()["immutable_scope"]["chunks"]
        new_chunks = [row for row in chunks if row["rva"] >= 0x4000]
        self.assertEqual(new_chunks[0]["size"], tool.CHUNK_BYTES + 3)
        self.assertEqual(new_chunks[1]["rva"], 0x4000 + tool.CHUNK_BYTES + 3)
        reads = observations(bound, owned)
        self.assertTrue(self.compare(bound, owned, reads).report()["source_comparison_passed"])
        self.rejected(bound=bound, owned=owned, reads=reads[:-1])

    def test_rw_gap_and_caller_exemptions_cannot_join_checked_scope(self):
        for rva in (0x800, 0x2000, 0x3000):
            bad = replace(self.reads[-1], ordinal=len(self.reads), address=self.owned.image_base + rva)
            self.rejected(reads=self.reads + (bad,))
        for field, value in (("ranges", []), ("selected_highlow_rvas", []), ("header_imagebase_policy", "mask"),
                             ("excluded_unchecked_image_intervals", [])):
            plan = self.bound.plan(); plan["immutable_scope"][field] = value
            self.rejected(bound=replace(self.bound, plan_json=tool._canonical(plan)))

    def test_public_admission_rejects_synthetic_legacy_recipe_and_own_report(self):
        for profile, resolution in (("classic", "800x600"), ("castle", "800x600"),
                                     ("small_world", "802x602"), ("modal_widgets", "1920x1080")):
            with self.subTest(profile=profile), self.assertRaises(Exception):
                tool.prepare_contract(fixture.synthetic_pe(), profile, resolution, candidate=self.bound.candidate,
                                      metadata={"passed": True}, canonical_probe=self.bound.canonical_probe)
        result = tool.replay_loaded_image(fixture.synthetic_pe(), self.bound, self.owned, self.reads)
        self.assertFalse(result.report()["source_comparison_passed"])
        self.assertIs(result.original_reads, self.reads)
        for name in tool.FALSE_CLAIMS: self.assertIs(result.report()[name], False)
        self.assertFalse(tool.replay_loaded_image(fixture.synthetic_pe(), result.report(), self.owned, self.reads).report()["source_comparison_passed"])

    def test_source_pin_failure_retains_raw_observations_and_cannot_pass(self):
        with patch.object(tool, "_read_source", side_effect=ValueError("changed canonical source")):
            result = tool.replay_loaded_image(fixture.synthetic_pe(), self.bound, self.owned, self.reads)
        self.assertFalse(result.report()["source_comparison_passed"])
        self.assertIs(result.original_reads, self.reads)
        self.assertIn("changed canonical source", result.report()["failures"][0])

    def test_source_read_identity_reparse_and_digest_changes_reject(self):
        source = ROOT / tool.PE
        data = source.read_bytes()
        with patch.object(Path, "read_bytes", return_value=data + b"# change\n"):
            with self.assertRaises(ValueError): tool._read_source(tool.PE, tool.PINNED[tool.PE])
        with patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaises(ValueError): tool._read_source(tool.PE, tool.PINNED[tool.PE])
        snapshot = tool._snapshot()
        with patch.object(tool, "_snapshot", return_value={**snapshot, tool.PE: (data + b"# change\n", snapshot[tool.PE][1])}):
            with self.assertRaises(ValueError): tool._unchanged(snapshot)

    def test_strict_caps_pointer_and_parent_generation_boundaries(self):
        for changes in (dict(image_base=0x400001), dict(image_base=0x100000000), dict(peb_address=0x7ffe0000),
                        dict(controller=self.owned.target), dict(debugger=replace(self.owned.debugger, creation_filetime=4000)),
                        dict(clock_origin_ns=(1 << 63) - 1)):
            with self.subTest(changes=list(changes)), self.assertRaises(ValueError): replace(self.owned, **changes)
        with self.assertRaises(ValueError): replace(self.reads[0], requested_bytes=tool.CHUNK_BYTES + 4)
        with patch.object(tool, "MAX_READ_TOTAL", 1024):
            with self.assertRaises(ValueError): tool._derive_plan(self.bound.candidate, pe)
        with patch.object(tool, "MAX_READS", 2):
            with self.assertRaises(ValueError): tool._derive_plan(self.bound.candidate, pe)
        with patch.object(tool, "MAX_IMAGE_BYTES", 4096):
            with self.assertRaisesRegex(ValueError, "mapped image"): tool._derive_plan(self.bound.candidate, pe)

    def test_exact_contract_schema_rejects_invented_passes_and_resealed_source_inventory(self):
        for field, value in (("accepted", True), ("expected_bytes", []), ("exemptions", [])):
            plan = self.bound.plan(); plan[field] = value
            self.rejected(bound=replace(self.bound, plan_json=tool._canonical(plan)))
        for changes in (dict(schema="legacy"), dict(claims={"passed": True}), dict(source_closure_sha256="0" * 64)):
            plan = self.bound.plan(); plan.update(changes)
            self.rejected(bound=replace(self.bound, plan_json=tool._canonical(plan)))

    def test_original_signed_unsigned_hresult_failures_are_unchanged_and_rejected(self):
        row = self.reads[1]
        for code in (-(1 << 31), -2147467259, -1, 0x80004005, 0xffffffff):
            with self.subTest(code=code):
                bad = replace(row, hresult=code)
                reads = self.reads[:1] + (bad,) + self.reads[2:]
                result = self.rejected(reads=reads)
                self.assertEqual(result.report()["observations"][1]["hresult"], code)
                for receipt_side in ("phase_before", "phase_after"):
                    phase = getattr(row, receipt_side)
                    bad = replace(row, **{receipt_side: replace(phase, pointer64_hresult=code)})
                    reads = self.reads[:1] + (bad,) + self.reads[2:]
                    result = self.rejected(reads=reads)
                    self.assertEqual(result.report()["observations"][1][receipt_side + "_pointer64_hresult"], code)
                    for index, query in enumerate(phase.native_queries):
                        queries = list(phase.native_queries); queries[index] = replace(query, hresult=code)
                        bad = replace(row, **{receipt_side: replace(phase, native_queries=tuple(queries))})
                        reads = self.reads[:1] + (bad,) + self.reads[2:]
                        result = self.rejected(reads=reads)
                        self.assertEqual(result.report()["observations"][1][receipt_side + "_queries"][index]["hresult"], code)
                        self.assertIs(result.original_reads[1], bad)
        for code in (-(1 << 31) - 1, 1 << 32, True, "-1"):
            with self.subTest(invalid=code), self.assertRaises(ValueError): replace(row, hresult=code)


def original_backed(cases=None):
    """Five exact parent bundles and hostile public aliases, entirely in RAM."""
    import battle_profile_context as context
    from src.patcher import classic_all_presets_candidate as classic
    from src.patcher import framed_all_presets_candidate as framed
    from src.patcher import complete_hd_all_presets_candidate as complete
    from src.patcher import modal_widgets_all_presets_candidate as modal
    from src.patcher import pe_extension as public_pe
    raw = ORIGINAL.read_bytes()
    if digest(raw) != ORIGINAL_SHA: raise AssertionError("exact original SHA differs")
    own_source, fixture_source = digest((ROOT / tool.SOURCE).read_bytes()), digest(Path(__file__).read_bytes())
    cases = cases or (("classic", "1024x768"), ("classic", "1366x768"), ("framed", "1366x768"),
                      ("completehd", "1366x768"), ("modalwidgets", "1366x768"))
    def poison(*args, **kwargs): raise AssertionError("public alias used as producer authority")
    for profile, resolution in cases:
        parent = context.build_parent_context(raw, profile, resolution)
        metadata = context._restore_metadata(tool._json(parent.parent_metadata_json))
        expected = tool.prepare_contract(raw, profile, resolution, candidate=parent.candidate,
                                          metadata=metadata, canonical_probe=parent.canonical_probe.encode("utf-8"))
        with patch.object(context, "authenticate_parent", poison), patch.object(context, "build_parent_context", poison), \
             patch.object(pe, "inspect_pe", poison), patch.object(public_pe, "inspect_pe", poison), patch.object(tool, "_derive_plan", poison), \
             patch.object(tool, "_compare", poison), patch.object(classic, "build_candidate", poison), \
             patch.object(framed, "build_candidate", poison), \
             patch.object(complete, "build_candidate", poison), \
             patch.object(modal, "build_candidate", poison):
            bound = tool.prepare_contract(raw, profile, resolution, candidate=parent.candidate,
                                           metadata=metadata, canonical_probe=parent.canonical_probe.encode("utf-8"))
            assert bound.plan_json == expected.plan_json
            owned = authority(bound)
            reads = observations(bound, owned)
            result = tool.replay_loaded_image(raw, bound, owned, reads)
            assert result.report()["source_comparison_passed"], result.report()
            assert all(result.report()[key] is False for key in tool.FALSE_CLAIMS)
        for changes in (dict(canonical_probe=bound.canonical_probe + b".echo fake\n"),
                        dict(candidate=bound.candidate[:-1] + bytes([bound.candidate[-1] ^ 1]))):
            bad = replace(bound, **changes)
            rejected = tool.replay_loaded_image(raw, bad, owned, reads)
            assert not rejected.report()["source_comparison_passed"], rejected.report()
            assert rejected.original_reads is reads
        plan = bound.plan(); plan["accepted"] = True
        assert not tool.replay_loaded_image(raw, replace(bound, plan_json=tool._canonical(plan)), owned, reads).report()["source_comparison_passed"]
        if profile == "classic" and resolution == "1024x768":
            # A substituted bundle cannot authorize its own consistently
            # resealed metadata, contract, process and observed raw bytes.
            mutated = bytearray(bound.candidate); mutated[0x543] ^= 1; mutated = bytes(mutated)
            changed_metadata = dict(metadata); changed_metadata["candidate_sha256"] = digest(mutated)
            plan = bound.plan(); plan["candidate_sha256"] = digest(mutated)
            substituted = replace(bound, candidate=mutated, typed_metadata_json=context._typed_canonical(changed_metadata),
                                  plan_json=tool._canonical(plan))
            foreign = replace(owned, candidate_sha256=digest(mutated), target=replace(owned.target, image_sha256=digest(mutated)))
            assert not tool.replay_loaded_image(raw, substituted, foreign, observations(substituted, foreign)).report()["source_comparison_passed"]
            plan = bound.plan(); probe = bound.canonical_probe + b".echo substituted\n"
            plan["canonical_probe_sha256"] = digest(probe)
            changed_metadata = dict(metadata); changed_metadata["probe_sha256"] = digest(probe)
            substituted = replace(bound, canonical_probe=probe, typed_metadata_json=context._typed_canonical(changed_metadata),
                                  plan_json=tool._canonical(plan))
            assert not tool.replay_loaded_image(raw, substituted, replace(owned, probe_sha256=digest(probe)), reads).report()["source_comparison_passed"]
            # Change actual source bytes only in the read adapter's returned
            # observation after comparison; no source file is written.
            actual_read, own_reads = Path.read_bytes, 0
            def changed_source(path):
                nonlocal own_reads
                data = actual_read(path)
                if path == ROOT / tool.SOURCE:
                    own_reads += 1
                    if own_reads >= 3: return data + b"\n# changed after raw replay\n"
                return data
            with patch.object(Path, "read_bytes", changed_source):
                changed = tool.replay_loaded_image(raw, bound, owned, reads)
            assert own_reads >= 3 and not changed.report()["source_comparison_passed"], changed.report()
            assert changed.original_reads is reads
        print(f"original-backed {profile} {resolution} executable/header comparison PASS; native/runtime claims false", flush=True)
    assert digest(ORIGINAL.read_bytes()) == ORIGINAL_SHA
    assert digest((ROOT / tool.SOURCE).read_bytes()) == own_source
    assert digest(Path(__file__).read_bytes()) == fixture_source


if __name__ == "__main__":
    requested = "--original-backed" in sys.argv
    if requested: sys.argv.remove("--original-backed")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LoadedImageTests))
    if not result.wasSuccessful(): raise SystemExit(1)
    if requested: original_backed()

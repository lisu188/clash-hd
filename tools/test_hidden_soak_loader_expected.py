#!/usr/bin/env python3
"""Portable source/payload models; optional all36 original reconstruction in RAM.

No candidate/payload files, native adapters, compiler, game or debugger runs.
"""
from __future__ import annotations

import builtins
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "src" / "patcher")]
import hidden_soak_loader_expected as tool
import hidden_soak_loaded_image as oracle
import pe_extension as pe
import test_hidden_soak_loaded_image as image_fixture
import test_pe_extension as pe_fixture


def digest(raw): return hashlib.sha256(raw).hexdigest()


def authority(): return tool.PayloadAuthority("1" * 32, "2" * 32, "3" * 32, 100, 10**7, 1000, 1000)


def wire(metadata, chunks, fixups, raw, **prefix_changes):
    """Independent serializer for deliberately resealed adversarial streams."""
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    values = dict(magic=b"CLHDLE1\0", version=1, meta_size=len(encoded), count=len(chunks), fixup_count=len(fixups),
        raw_size=len(raw), preferred=metadata["preferred_base"], image_size=metadata["image_size"],
        headers_size=metadata["headers_size"], base_field=metadata["header_imagebase_offset"], flags=0)
    values.update(prefix_changes)
    body = struct.pack("<8s10I", *values.values()) + encoded
    body += b"".join(struct.pack("<8I", *row) for row in chunks)
    body += b"".join(struct.pack("<I", at) for at in fixups) + raw
    return body + hashlib.sha256(body).digest()


def independent_chunks(bound, base):
    memory, _, fixups, _ = pe_fixture.independent_image(bound.candidate)
    preferred = int.from_bytes(memory[int.from_bytes(memory[60:64], "little") + 24 + 28:][:4], "little")
    memory = pe_fixture.rebase(memory, fixups, base - preferred)
    return tuple((base + row["rva"], bytes(memory[row["rva"]:row["rva"] + row["size"]]))
                 for row in bound.plan()["immutable_scope"]["chunks"])


class ExpectedPayloadTests(unittest.TestCase):
    def setUp(self):
        self.bound, self.owned = image_fixture.contract(), authority()
        self.check = lambda: None
        # This isolated factory is an explicit synthetic seam. Public production
        # functions remain unchanged and independently reject this marked PE.
        def prepare(original, contract, imported):
            state = tool._build_state(contract, oracle=oracle, pe=pe, issuer_sha256=digest(imported), check_sources=self.check)
            return state[0], state[1], state[2], lambda owned: tool._encode(state, owned), tool._decode, tool._model, self.check
        self.prepare, self.issue, self.inspect, self.model, self.replay = tool._api_factory(_preparation=prepare)
        self.plan = self.prepare(b"synthetic no production authority", self.bound)
        self.payload = self.issue(self.plan, self.owned)
        self.facts = self.inspect(self.payload)
        self.metadata, self.chunks, self.fixups, self.raw = tool._decode(self.facts.payload_bytes)

    def reject(self, raw, bound=None, owned=None, base=0x400000):
        result = self.replay(b"synthetic", bound or self.bound, owned or self.owned, raw, base)
        self.assertFalse(result.report()["source_payload_replay_passed"], result.report())
        self.assertTrue(result.report()["failures"])
        self.assertIs(result.original_payload, raw)
        self.assertFalse(result.modeled_chunks)
        for key in tool.FALSE_CLAIMS: self.assertIs(result.report()[key], False)
        return result

    def reseal(self, *, metadata=None, chunks=None, fixups=None, raw=None, **prefix):
        return wire(self.metadata if metadata is None else metadata, self.chunks if chunks is None else chunks,
                    self.fixups if fixups is None else fixups, self.raw if raw is None else raw, **prefix)

    def test_preferred_positive_negative_and_modulo32_bases_match_independent_loader(self):
        data = bytearray(pe_fixture.synthetic_pe()); struct.pack_into("<I", data, 0x401, 0xfffffff0)
        bound = image_fixture.contract(bytes(data)); payload = self.issue(self.prepare(b"synthetic", bound), self.owned)
        for base in (0x400000, 0x500000, 0x300000, 0x21000000):
            with self.subTest(base=base):
                model = self.model(payload, base)
                self.assertEqual(model.modeled_chunks, independent_chunks(bound, base))
                self.assertTrue(model.report()["modeled_source_bytes_derived"])
                self.assertFalse(model.report()["native_base_observed"])
                for key in tool.FALSE_CLAIMS: self.assertIs(model.report()[key], False)

    def test_all36_declared_profiles_presets_models_and_limits(self):
        import battle_profile_context as context
        count = 0
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    plan = self.bound.plan(); plan.update(profile=profile, resolution=resolution,
                        stage="synthetic-" + profile + "-" + resolution)
                    bound = replace(self.bound, plan_json=oracle._canonical(plan))
                    payload = self.issue(self.prepare(b"synthetic", bound), self.owned)
                    facts = self.inspect(payload)
                    self.assertLessEqual(len(facts.payload_bytes), tool.MAX_PAYLOAD)
                    for base in (0x400000, 0x300000, 0x500000):
                        self.assertEqual(self.model(payload, base).modeled_chunks, independent_chunks(bound, base))
                    count += 1
        self.assertEqual(count, 36)

    def test_strict_header_imagebase_peb_exclusion_and_scope_gaps(self):
        model = self.model(self.payload, 0x500000)
        header = model.modeled_chunks[0][1]
        self.assertEqual(struct.unpack_from("<I", header, self.metadata["header_imagebase_offset"])[0], 0x400000)
        self.assertEqual(len(self.chunks) + 1, self.metadata["required_read_count"])
        self.assertIn("PEB.ImageBaseAddress4", self.metadata["mandatory_extra_read"])
        self.assertTrue(self.metadata["excluded_nonexecutable_sections"])
        self.assertTrue(self.metadata["excluded_unchecked_image_intervals"])
        self.assertEqual(tuple(self.fixups), (0x1001, 0x1009, 0x1011))

    def test_complete_zero_tail_and_interior_byte_resealing_reject(self):
        data = bytearray(pe_fixture.synthetic_pe()); struct.pack_into("<I", data, 0x88 + 224 + 8, 0x600)
        bound = image_fixture.contract(bytes(data)); payload = self.issue(self.prepare(b"synthetic", bound), self.owned)
        facts = self.inspect(payload); meta, chunks, fixups, raw = tool._decode(facts.payload_bytes)
        self.assertEqual(chunks[-1][-1], 2)
        self.assertEqual(self.model(payload, 0x500000).modeled_chunks, independent_chunks(bound, 0x500000))
        changed = bytearray(raw); changed[-0x111] = 1; changed = bytes(changed)
        meta["expected_raw_sha256"] = digest(changed)
        self.reject(wire(meta, chunks, fixups, changed), bound=bound)
        self.reject(wire(meta, chunks[:-1], fixups, changed), bound=bound)

    def test_complete_original_truncations_trailer_extra_and_oversize_retained(self):
        original = self.facts.payload_bytes
        for at in (0, 7, 47, 49, len(original) // 2, len(original) - 33, len(original) - 1):
            with self.subTest(cut=at): self.reject(original[:at])
        self.reject(original + b"unexpected exact EOF")
        changed = bytearray(original); changed[-1] ^= 1; self.reject(bytes(changed))
        with patch.object(tool, "MAX_PAYLOAD", len(original) - 1): self.reject(original)
        self.reject(bytearray(original))

    def test_order_duplicate_omission_raw_offsets_and_scope_alias_reject(self):
        attacks = (self.chunks[::-1], self.chunks[:-1], self.chunks + (self.chunks[-1],),
            (self.chunks[0], (1, 0, *self.chunks[1][2:])),
            (self.chunks[0], self.chunks[1][:3] + (self.chunks[1][3] + 1,) + self.chunks[1][4:]))
        for chunks in attacks:
            with self.subTest(chunks=chunks): self.reject(self.reseal(chunks=chunks))

    def test_complete_selected_fixups_split_duplicate_missing_reordered_header_and_zero_reject(self):
        for fixups in (self.fixups[:-1], self.fixups + (self.fixups[-1],), self.fixups[::-1],
                       (self.fixups[0], self.fixups[0] + 1, self.fixups[-1]), (0x11ff,),
                       (self.metadata["header_imagebase_offset"],), (0x3000,)):
            meta = dict(self.metadata); meta["selected_highlow_rvas_sha256"] = digest(tool._canonical(list(fixups)))
            self.reject(self.reseal(metadata=meta, fixups=fixups))

    def test_relocation_safe_chunk_crossing_and_all_relocations_authentication(self):
        code = bytearray(b"\x90" * 65544); struct.pack_into("<I", code, 65535, 0x402008)
        allocation = pe._extend_verified_image(pe_fixture.synthetic_pe(), code=bytes(code), code_va=0x404000,
            relocations=(pe.CodeRelocation(65535, "abs32", 0x402008, "synthetic crossing"),), binding={"fixture": "synthetic"})
        bound = image_fixture.contract(allocation.image); payload = self.issue(self.prepare(b"synthetic", bound), self.owned)
        facts = self.inspect(payload); meta, chunks, fixups, raw = tool._decode(facts.payload_bytes)
        self.assertTrue(any(row[2] == 65539 for row in chunks))
        self.assertEqual(meta["all_highlow_count"], len(bound.plan()["immutable_scope"]["all_highlow_rvas"]))
        for base in (0x400000, 0x500000, 0x300000):
            self.assertEqual(self.model(payload, base).modeled_chunks, independent_chunks(bound, base))
        crossing = next(index for index, row in enumerate(chunks) if row[2] == 65539)
        rows = list(chunks); rows[crossing] = rows[crossing][:2] + (65536,) + rows[crossing][3:]
        self.reject(wire(meta, rows, fixups, raw), bound=bound)

    def test_resealed_all_interior_raw_header_and_imagebase_substitutions_fail(self):
        for at in (0x200, self.metadata["header_imagebase_offset"], len(self.raw) - 0x111):
            raw = bytearray(self.raw); raw[at] ^= 1; raw = bytes(raw)
            metadata = dict(self.metadata); metadata["expected_raw_sha256"] = digest(raw)
            self.reject(self.reseal(metadata=metadata, raw=raw))

    def test_unknown_fields_false_claim_coercion_authority_and_header_policy_fail(self):
        for changes in (dict(accepted=True), dict(header_imagebase_policy="normalized actual base"),
                        dict(claims={key: 0 for key in tool.FALSE_CLAIMS}), dict(claims=dict(tool.FALSE_CLAIMS, passed=True)),
                        dict(authority=dict(asdict(self.owned), controller_pid=True))):
            meta = dict(self.metadata); meta.update(changes)
            self.reject(self.reseal(metadata=meta))
        meta = dict(self.metadata); del meta["mandatory_extra_read"]; self.reject(self.reseal(metadata=meta))

    def test_candidate_probe_source_identity_and_profile_resealing_fail(self):
        for field in ("candidate_sha256", "probe_sha256", "source_closure_sha256", "issuer_source_sha256",
                      "typed_metadata_sha256", "immutable_scope_sha256"):
            meta = dict(self.metadata); meta[field] = digest(b"substituted")
            self.reject(self.reseal(metadata=meta))
        for field, value in (("profile", "framed"), ("resolution", "802x602"), ("stage", "forged"), ("recipe_revision", "forged")):
            meta = dict(self.metadata); meta[field] = value
            self.reject(self.reseal(metadata=meta))

    def test_wire_counts_caps_magic_flags_and_scalars_reject(self):
        for changes in (dict(version=2), dict(magic=b"CLHDLE2\0"), dict(flags=1), dict(meta_size=65537),
                        dict(count=512), dict(fixup_count=65537), dict(raw_size=16 * 1024**2),
                        dict(image_size=0xffffffff), dict(preferred=0x7fff0000), dict(headers_size=0xffffffff)):
            self.reject(self.reseal(**changes))

    def test_authority_types_and_stale_run_checkpoint_epoch_clock_fail(self):
        for name, value in (("controller_pid", True), ("frequency_hz", 0), ("origin_tick", -1),
                            ("origin_ns", 0), ("run_id", "A" * 32)):
            with self.subTest(name=name), self.assertRaises(ValueError): replace(self.owned, **{name: value})
        for name in asdict(self.owned):
            value = "4" * 32 if name.endswith("id") and name != "controller_pid" else getattr(self.owned, name) + 1
            self.reject(self.facts.payload_bytes, owned=replace(self.owned, **{name: value}))
        with self.assertRaises(ValueError): self.issue(self.plan, asdict(self.owned))

    def test_modeled_base_type_alignment_and_full_extent_overflow_fail(self):
        for base in (True, 0, 0x400001, 0x7ffd0000, 0xffffffff):
            with self.subTest(base=base):
                if base == 0x7ffd0000: continue  # This small synthetic image fits there.
                with self.assertRaises(ValueError): self.model(self.payload, base)
        with self.assertRaises(ValueError): self.model(self.payload, 0x7ffe0000)

    def test_public_payload_plan_clones_bindings_and_fact_objects_are_not_authority(self):
        with self.assertRaises(ValueError): self.issue(tool.ExpectedReadPlan(self.plan.binding_json), self.owned)
        with self.assertRaises(ValueError): self.inspect(tool.ExpectedPayload(self.payload.binding_json))
        with self.assertRaises(ValueError): self.model(self.facts, 0x400000)
        with self.assertRaises(ValueError): tool.issue_expected_payload(self.plan, self.owned)
        with self.assertRaises(ValueError): tool.inspect_expected_payload(self.payload)
        object.__setattr__(self.payload, "binding_json", "{}")
        with self.assertRaises(ValueError): self.inspect(self.payload)

    def test_fresh_replay_retains_original_and_checks_every_byte(self):
        result = self.replay(b"synthetic", self.bound, self.owned, self.facts.payload_bytes, 0x500000)
        self.assertTrue(result.report()["source_payload_replay_passed"], result.report())
        self.assertIs(result.original_payload, self.facts.payload_bytes)
        self.assertEqual(result.modeled_chunks, independent_chunks(self.bound, 0x500000))
        for key in tool.FALSE_CLAIMS: self.assertIs(result.report()[key], False)

    def test_imported_source_changed_before_admission_retains_original(self):
        actual = Path.read_bytes
        def changed(path):
            raw = actual(path)
            return raw + b"\n# supplied changed source only\n" if path == ROOT / tool.SOURCE else raw
        with patch.object(Path, "read_bytes", changed):
            with self.assertRaises(ValueError): self.prepare(b"synthetic", self.bound)
            with self.assertRaises(ValueError): self.inspect(self.payload)
            self.reject(self.facts.payload_bytes)

    def test_source_change_during_encode_model_or_fresh_replay_stops(self):
        def failed(): raise ValueError("retained source identity changed")
        self.check = failed
        with self.assertRaises(ValueError): self.prepare(b"synthetic", self.bound)
        self.reject(self.facts.payload_bytes)
        # New issued closures use the exact callback held at preparation.
        calls = 0
        def expires():
            nonlocal calls
            calls += 1
            if calls >= 3: raise ValueError("source changed during encoding")
        self.check = expires; plan = self.prepare(b"synthetic", self.bound)
        with self.assertRaises(ValueError): self.issue(plan, self.owned)

    def test_post_model_source_failure_publishes_no_derived_chunks(self):
        calls = 0
        def expires():
            nonlocal calls
            calls += 1
            if calls == 6: raise ValueError("post-model source mutation")
        self.check = expires
        with patch.object(tool, "_model", wraps=tool._model) as modeled:
            result = self.reject(self.facts.payload_bytes)
        self.assertEqual(calls, 6)
        self.assertEqual(modeled.call_count, 1)
        self.assertIn("post-model", result.report()["failures"][0])

    def test_public_path_hash_module_and_source_aliases_cannot_execute_substitution(self):
        # The source failure here is the marked synthetic original, after the
        # genuine frozen oracle is loaded. The substituted source must never
        # reach compile/exec, even if public digest/path aliases are hostile.
        compiled, actual_compile = [], builtins.compile
        forbidden_path = ROOT / "tools/test_hidden_soak_loader_expected.py"
        def observed(source, filename, *args, **kwargs):
            compiled.append(str(filename))
            if str(filename) == str(forbidden_path): raise AssertionError("substituted oracle source executed")
            return actual_compile(source, filename, *args, **kwargs)
        with patch.object(tool, "ORACLE", "tools/test_hidden_soak_loader_expected.py"), \
             patch.object(tool, "ROOT", Path("Z:/forged-root")), patch.object(tool, "SOURCE", "forged.py"), \
             patch.object(tool, "_sha", lambda raw: tool.ORACLE_SHA256), patch.object(tool, "types", object()), \
             patch.object(tool, "sys", object()), patch.object(tool, "uuid", object()), \
             patch.object(tool, "_private_preparation", lambda *args: (_ for _ in ()).throw(AssertionError("public admission used"))), \
             patch.object(builtins, "compile", observed):
            with self.assertRaises(ValueError): tool.prepare_expected_plan(pe_fixture.synthetic_pe(), self.bound)
        self.assertIn(str(ROOT / tool.ORACLE), compiled)
        self.assertNotIn(str(forbidden_path), compiled)

    def test_admission_ast_removes_only_exact_unique_terminal_assignment(self):
        source = (ROOT / tool.SOURCE).read_bytes(); path = ROOT / tool.SOURCE
        self.assertTrue(callable(tool._closed_preparation(source, path)))
        for changed in (source + b"\n_api_factory()\n", source.replace(b" = _api_factory()", b" = _api_factory(1)"),
                        source.replace(b"model_loaded_chunks, replay_expected_payload =", b"model_loaded_chunks, forged =")):
            with self.subTest(bytes=len(changed)), self.assertRaises(ValueError): tool._closed_preparation(changed, path)

    def test_rw_executable_unbacked_and_arbitrary_caller_ranges_fail(self):
        for at, value in ((0x88 + 224 + 36, 0xe0000020), (0x88 + 224 + 20, 0)):
            data = bytearray(pe_fixture.synthetic_pe()); struct.pack_into("<I", data, at, value)
            with self.assertRaises(ValueError): image_fixture.contract(bytes(data))
        plan = self.bound.plan(); plan["immutable_scope"]["chunks"] = plan["immutable_scope"]["chunks"][:-1]
        with self.assertRaises(ValueError): self.prepare(b"synthetic", replace(self.bound, plan_json=oracle._canonical(plan)))

    def test_exact_wire_budget_includes_prefix_trailer_atomic_and_full_archive_copy(self):
        cost = tool.retention_budget()
        self.assertEqual(tool.PREFIX.size, 48); self.assertEqual(tool.DESCRIPTOR.size, 32)
        self.assertEqual(cost["maximum_payload_bytes"], 17_121_324)
        self.assertEqual(cost["additional_payload_peak_bytes"], 34_242_648)
        self.assertEqual(cost["existing_native_journal_peak_bytes"], 35_717_123)
        self.assertEqual(cost["separate_complete_native_archive_copy_bytes"], 26_279_939)
        self.assertEqual(cost["combined_known_peak_bytes"], 96_239_710)
        self.assertEqual(len(self.facts.payload_bytes), 48 + len(self.facts.metadata_json.encode("ascii")) +
                         len(self.chunks) * 32 + len(self.fixups) * 4 + len(self.raw) + 32)
        for cap in ("MAX_METADATA", "MAX_CHUNKS", "MAX_FIXUPS", "MAX_RAW"):
            with self.subTest(cap=cap), patch.object(tool, cap, 1), self.assertRaises(ValueError):
                self.issue(self.prepare(b"synthetic", self.bound), self.owned)

    def test_public_production_cannot_admit_synthetic_or_forged_capabilities(self):
        with self.assertRaises(ValueError): tool.prepare_expected_plan(pe_fixture.synthetic_pe(), self.bound)
        with self.assertRaises(ValueError): tool.issue_expected_payload(tool.ExpectedReadPlan("{}"), self.owned)
        with self.assertRaises(ValueError): tool.inspect_expected_payload(tool.ExpectedPayload("{}"))


def original_backed(cases=None):
    """All36 source reconstructions and independent modeled bases, RAM only."""
    import battle_profile_context as context
    from src.patcher import classic_all_presets_candidate, framed_all_presets_candidate
    from src.patcher import complete_hd_all_presets_candidate, modal_widgets_all_presets_candidate
    original = image_fixture.ORIGINAL.read_bytes(); before = digest(original)
    assert before == image_fixture.ORIGINAL_SHA
    source_hashes = {path: digest((ROOT / path).read_bytes()) for path in (tool.SOURCE, tool.ORACLE,
        "tools/hidden_soak_loader_native.py", "tools/hidden_soak_loader_native_adapter.py",
        "tools/test_hidden_soak_loader_native.py", "tools/test_hidden_soak_loader_native_engine.py")}
    fixture_sha = digest(Path(__file__).read_bytes())
    def poison(*args, **kwargs): raise AssertionError("public alias cannot issue canonical bytes")
    largest_payload = largest_fixups = largest_chunks = 0
    count = 0
    for profile in context.PROFILES:
        for resolution in context.RESOLUTIONS:
            if cases is not None and (profile, resolution) not in cases: continue
            parent = context.build_parent_context(original, profile, resolution)
            metadata = context._restore_metadata(oracle._json(parent.parent_metadata_json))
            bound = oracle.prepare_contract(original, profile, resolution, candidate=parent.candidate,
                metadata=metadata, canonical_probe=parent.canonical_probe.encode("utf-8"))
            owned = authority()  # Original typed caller snapshot precedes hostile aliases.
            with patch.object(context, "build_parent_context", poison), patch.object(context, "authenticate_parent", poison), \
                 patch.object(oracle, "_derive_plan", poison), patch.object(pe, "inspect_pe", poison), \
                 patch.object(tool, "_build_state", poison), patch.object(tool, "_encode", poison), \
                 patch.object(tool, "_decode", poison), patch.object(tool, "_model", poison), \
                 patch.object(tool, "ORACLE", "tools/test_hidden_soak_loader_expected.py"), \
                 patch.object(tool, "_sha", poison), patch.object(tool, "types", object()), \
                 patch.object(tool, "sys", object()), patch.object(tool, "uuid", object()), \
                 patch.object(classic_all_presets_candidate, "build_candidate", poison), \
                 patch.object(framed_all_presets_candidate, "build_candidate", poison), \
                 patch.object(complete_hd_all_presets_candidate, "build_candidate", poison), \
                 patch.object(modal_widgets_all_presets_candidate, "build_candidate", poison):
                plan = tool.prepare_expected_plan(original, bound)
                payload = tool.issue_expected_payload(plan, owned); facts = tool.inspect_expected_payload(payload)
                for base in (bound.plan()["immutable_scope"]["preferred_base"], 0x300000, 0x500000):
                    result = tool.model_loaded_chunks(payload, base)
                    assert result.modeled_chunks == independent_chunks(bound, base)
                    assert all(result.report()[key] is False for key in tool.FALSE_CLAIMS)
                if profile == "classic" and resolution == "1024x768":
                    replay = tool.replay_expected_payload(original, bound, owned, facts.payload_bytes, 0x500000)
                    assert replay.report()["source_payload_replay_passed"], replay.report()
                    assert replay.original_payload is facts.payload_bytes
            largest_payload = max(largest_payload, len(facts.payload_bytes))
            largest_fixups = max(largest_fixups, len(facts.selected_highlow_rvas))
            largest_chunks = max(largest_chunks, len(facts.descriptors))
            if profile == "classic" and resolution == "1024x768":
                for changes in (dict(candidate=bound.candidate[:-1] + bytes([bound.candidate[-1] ^ 1])),
                                dict(canonical_probe=bound.canonical_probe + b".echo fake\n")):
                    rejected = tool.replay_expected_payload(original, replace(bound, **changes), authority(), facts.payload_bytes, 0x400000)
                    assert not rejected.report()["source_payload_replay_passed"]
                    assert rejected.original_payload is facts.payload_bytes
                mutated = bytearray(bound.candidate); mutated[0x543] ^= 1; mutated = bytes(mutated)
                for candidate, probe in ((mutated, bound.canonical_probe),
                                         (bound.candidate, bound.canonical_probe + b".echo consistently resealed fake\n")):
                    changed_metadata = dict(metadata)
                    changed_metadata.update(candidate_sha256=digest(candidate), probe_sha256=digest(probe))
                    plan_json = bound.plan()
                    plan_json.update(candidate_sha256=digest(candidate), canonical_probe_sha256=digest(probe),
                                     immutable_scope=oracle._derive_plan(candidate, pe))
                    forged = replace(bound, candidate=candidate, canonical_probe=probe,
                        typed_metadata_json=context._typed_canonical(changed_metadata), plan_json=oracle._canonical(plan_json))
                    state = tool._build_state(forged, oracle=oracle, pe=pe,
                        issuer_sha256=digest((ROOT / tool.SOURCE).read_bytes()), check_sources=lambda: None)
                    _, resealed = tool._encode(state, authority())
                    rejected = tool.replay_expected_payload(original, forged, authority(), resealed, 0x500000)
                    assert not rejected.report()["source_payload_replay_passed"], rejected.report()
                    assert rejected.original_payload is resealed and not rejected.modeled_chunks
            count += 1
            print(f"original-backed {profile} {resolution} payload/chunks PASS; all native/runtime claims false", flush=True)
    assert digest(image_fixture.ORIGINAL.read_bytes()) == before
    assert {path: digest((ROOT / path).read_bytes()) for path in source_hashes} == source_hashes
    assert digest(Path(__file__).read_bytes()) == fixture_sha
    assert count == (36 if cases is None else len(cases))
    print(f"source cases={count} maximum payload={largest_payload}, selectedHIGHLOW={largest_fixups}, chunks={largest_chunks}; original/source unchanged", flush=True)


if __name__ == "__main__":
    requested = "--original-backed" in sys.argv
    if requested: sys.argv.remove("--original-backed")
    representatives = "--original-representatives" in sys.argv
    if representatives: sys.argv.remove("--original-representatives")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExpectedPayloadTests))
    if not result.wasSuccessful(): raise SystemExit(1)
    if requested or representatives:
        original_backed(None if requested else (("classic", "1024x768"), ("classic", "1366x768"),
            ("framed", "1366x768"), ("completehd", "1366x768"), ("modalwidgets", "1366x768")))

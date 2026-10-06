#!/usr/bin/env python3
"""Portable V2 framing/replay negatives; no native or filesystem adapters."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hidden_soak_loader_compare_native_adapter as adapter
import hidden_soak_loader_compare_native as native
import hidden_soak_loader_expected as expected
import hidden_soak_loaded_image as image
import hidden_soak_loader_native as v1
import test_hidden_soak_loader_native as legacy
import hidden_soak_loaded_read_session as session
import pe_extension as pe


def packet(sequence, operation, data, raw=b"", *, io=None, metadata=None):
    meta = adapter._canonical(dict(sequence=sequence, operation=operation, data=data)) if metadata is None else metadata
    requested = 8 + len(meta) + len(raw)
    footer = (1, 0, requested, requested, 1, 0) if io is None else io
    return struct.pack("<II", len(meta), len(raw)) + meta + raw + adapter.IO_FOOTER.pack(*footer)


class FramingTests(unittest.TestCase):
    def reject(self, raw, *, prefix=None):
        with self.assertRaises(adapter.ArchiveError) as caught:
            adapter.parse_frames(raw)
        self.assertIs(caught.exception.original_archive, raw)
        if prefix is not None:
            self.assertEqual(len(caught.exception.frames), prefix)
        return caught.exception

    def test_exact_original_packet_and_main_footer_remain_separate(self):
        raw = adapter.MAGIC + packet(1, "counter", {"tick": 7})
        rows = adapter.parse_frames(raw)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.offset, len(adapter.MAGIC))
        self.assertEqual(row.data(), {"tick": 7})
        self.assertEqual(row.raw, b"")
        self.assertEqual(row.footer, raw[-24:])
        adapter._io(row.io(), 8 + len(row.metadata))

    def test_failed_full_requested_capacity_is_preserved_without_prefix_projection(self):
        capacity = b"original\x00tail"
        data = dict(ordinal=0, address=0x200008, requested_bytes=len(capacity),
                    hresult=-2147467259, returned_bytes=3)
        raw = adapter.MAGIC + packet(1, "read_virtual_capacity", data, capacity)
        row = adapter.parse_frames(raw)[0]
        self.assertEqual(row.raw, capacity)
        self.assertEqual(row.data()["returned_bytes"], 3)
        self.assertEqual(row.data()["hresult"], -2147467259)
        self.assertNotEqual(len(row.raw), row.data()["returned_bytes"])

    def test_failed_native_full_file_buffer_is_retained(self):
        capacity = b"ABCDEFGH"
        raw = adapter.MAGIC + packet(1, "native_failure", dict(api_name="ReadFile", requested_bytes=8,
                    returned_bytes=3, native_return=0, native_error=5, detail_hex=""), capacity)
        row = adapter.parse_frames(raw)[0]
        self.assertEqual(row.raw, capacity)
        self.assertEqual(row.data()["returned_bytes"], 3)

    def test_original_negative_bool_and_stale_success_error_are_not_normalized(self):
        meta = adapter._canonical(dict(sequence=1, operation="counter", data={}))
        requested = 8 + len(meta)
        raw = adapter.MAGIC + packet(1, "counter", {}, io=(-1, 123, requested, requested, -1, 456))
        row = adapter.parse_frames(raw)[0]
        self.assertEqual(row.io()["write_return"], -1)
        self.assertEqual(row.io()["write_error"], 123)
        self.assertEqual(row.io()["flush_error"], 456)
        adapter._io(row.io(), requested)

    def test_failed_short_or_foreign_main_io_cannot_be_eligible(self):
        meta = adapter._canonical(dict(sequence=1, operation="counter", data={}))
        requested = 8 + len(meta)
        for io in ((0, 5, requested, requested, 1, 0), (1, 0, requested, requested - 1, 1, 0),
                   (1, 0, requested + 1, requested + 1, 1, 0), (1, 0, requested, requested, 0, 5)):
            with self.subTest(io=io):
                raw = adapter.MAGIC + packet(1, "counter", {}, io=io)
                row = adapter.parse_frames(raw)[0]
                with self.assertRaises(ValueError):
                    adapter._io(row.io(), requested)
                self.assertEqual(row.footer, adapter.IO_FOOTER.pack(*io))

    def test_truncation_at_every_boundary_retains_complete_original_and_prefix(self):
        first = packet(1, "counter", {"tick": 1})
        second = packet(2, "read_virtual_capacity", {"tick": 2}, b"original")
        raw = adapter.MAGIC + first + second
        for end in (0, 7, 8, 9, len(adapter.MAGIC) + len(first) - 1,
                    len(adapter.MAGIC) + len(first) + 1, len(raw) - 1):
            with self.subTest(end=end):
                self.reject(raw[:end])
        self.assertEqual(len(self.reject(raw[:-1]).frames), 1)

    def test_old_magic_duplicate_reordered_or_unknown_top_fields_fail(self):
        self.reject(b"CLHDLR1\0" + packet(1, "counter", {}))
        for sequence in (0, 2, True, -1):
            with self.subTest(sequence=sequence):
                meta = adapter._canonical(dict(sequence=sequence, operation="counter", data={}))
                self.reject(adapter.MAGIC + packet(1, "counter", {}, metadata=meta))
        self.reject(adapter.MAGIC + packet(1, "counter", {}) + packet(1, "counter", {}), prefix=1)
        meta = adapter._canonical(dict(sequence=1, operation="counter", data={}, approved=True))
        self.reject(adapter.MAGIC + packet(1, "counter", {}, metadata=meta))

    def test_noncanonical_duplicate_nonfinite_and_nonascii_json_fail(self):
        for meta in (b'{"sequence":1,"sequence":1,"operation":"counter","data":{}}',
                     b'{ "data":{},"operation":"counter","sequence":1}',
                     b'{"data":{"tick":NaN},"operation":"counter","sequence":1}',
                     b'{"data":{"text":"\xff"},"operation":"counter","sequence":1}'):
            with self.subTest(meta=meta):
                self.reject(adapter.MAGIC + packet(1, "counter", {}, metadata=meta))

    def test_exact_comparison_record_preserves_all_thirteen_fields_and_signed_ticks(self):
        original = adapter.COMPARISON_RECORD.pack(1, 0, 0xffffffff, 3, 4, 4, 2, 0, 0xffffffff, 0,
                                                   0x200008, 100, -7)
        data = dict(read_sequence=3, before_sequence=4, comparison_called=True, post_qpc_called=True, post_qpc={})
        raw = adapter.MAGIC + packet(1, "comparison_result", data, original)
        row = adapter.parse_frames(raw)[0]
        values = adapter.decode_comparison_record(row.raw)
        self.assertEqual(len(values), 13)
        self.assertEqual(values["address"], 0x200008)
        self.assertEqual(values["after_tick"], -7)
        self.assertEqual(values["descriptor_index"], 0xffffffff)
        self.assertEqual(row.raw, original)
        for wrong in (original[:-1], original + b"\x00"):
            self.reject(adapter.MAGIC + packet(1, "comparison_result", data, wrong), prefix=1)

    def test_unexpected_raw_or_excessive_original_packet_cannot_be_ignored(self):
        self.reject(adapter.MAGIC + packet(1, "counter", {}, b"unexpected"), prefix=1)
        self.reject(adapter.MAGIC + struct.pack("<II", adapter.MAX_FRAME_METADATA + 1, 0))
        self.reject(adapter.MAGIC + struct.pack("<II", 1, adapter.MAX_FRAME_RAW + 1))
        meta = adapter._canonical(dict(sequence=1, operation="comparison_counter", data={"text": "x" * 4096}))
        self.reject(adapter.MAGIC + packet(1, "comparison_counter", {}, metadata=meta), prefix=1)

    def test_caps_include_footer_failure_tail_and_do_not_issue_storage_or_runtime_claims(self):
        self.assertEqual(adapter.IO_FOOTER.size, 24)
        self.assertEqual(adapter.COMPARISON_RECORD.size, 64)
        self.assertEqual(adapter.MAX_TOTAL_METADATA, 13910040)
        self.assertEqual(adapter.MAX_FAILURE_METADATA, 14958616)
        self.assertEqual(adapter.MAX_TOTAL_RAW, 16809984)
        self.assertEqual(adapter.MAX_ARCHIVE, 31834139)
        self.assertTrue(all(value is False for value in adapter.FALSE_CLAIMS.values()))


def encode(rows):
    output, raw_bytes, metadata_bytes = bytearray(adapter.MAGIC), 0, 8
    for sequence, (operation, data, raw) in enumerate(rows, 1):
        original = packet(sequence, operation, data, raw)
        output.extend(original)
        raw_bytes += len(raw)
        metadata_bytes += len(original) - len(raw)
    output.extend(packet(len(rows) + 1, "finish", dict(status="complete", frame_count=len(rows),
        raw_bytes=raw_bytes, metadata_bytes=metadata_bytes, comparison_scope=adapter.SCOPE)))
    return bytes(output)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.base = legacy.NativeArchiveTests()
        self.base.setUp()
        self.paths = (Path(adapter.__file__), Path(native.__file__))
        self.snapshots = tuple(path.read_bytes() for path in self.paths)
        self.check_count, self.model_reached, self.fail_check = 0, False, None
        def check():
            self.check_count += 1
            if tuple(path.read_bytes() for path in self.paths) != self.snapshots or self.fail_check == self.check_count:
                raise ValueError("original supplied fixture source changed")
        self.check = check
        def preparation(original, contract, imported):
            state = expected._build_state(contract, oracle=image, pe=pe,
                issuer_sha256=adapter._sha(Path(expected.__file__).read_bytes()), check_sources=check)
            def issue(authority):
                metadata, payload = expected._encode(state, authority)
                decoded, descriptors, fixups, raw = expected._decode(payload)
                def model(base):
                    self.model_reached = True
                    check()
                    result = expected._model(payload, base)
                    check()
                    return result
                return decoded, payload, descriptors, fixups, raw, model, adapter._sha(imported)
            return issue, v1.HARNESS, check, adapter._sha(imported), adapter._sha(self.snapshots[0])
        prepare, issue, inspect = native._factory(_preparation=preparation)
        owned = self.base.owned
        self.anchor = self.base.anchor
        authority = expected.PayloadAuthority(owned.run_id, owned.checkpoint_id, owned.clock_epoch,
            owned.controller.pid, self.anchor.frequency_hz, self.anchor.origin_tick, self.anchor.origin_ns)
        self.request = issue(prepare(b"explicit synthetic fixture only", self.base.bound), authority)
        self.facts = inspect(self.request)
        self.inspect = inspect
        self.metadata = json.loads(self.facts.metadata_json)
        _, _, _, self.parse, self.replay, self.fixture = adapter._api_factory(_inspector=inspect)
        self.rows = self.make_rows()
        self.model_reached = False

    def qpc(self, tick):
        return self.base.qpc(tick)

    def make_rows(self):
        facts, metadata = self.facts, self.metadata
        raw = facts.expected_payload
        meta_size = struct.unpack_from("<I", raw, 12)[0]
        hashes = ((facts.request_bytes, adapter._sha(facts.request_bytes)),
                  (facts.request_bytes[:-32], facts.request_bytes[-32:].hex()),
                  (raw, adapter._sha(raw)), (raw[:-32], raw[-32:].hex()))
        binding = dict(request_sha256=metadata["request_sha256"], expected_payload_sha256=metadata["expected_payload_sha256"],
            metadata_hex=raw[48:48 + meta_size].hex(), request_path_utf16le="C:/fixture/request.bin\0".encode("utf-16-le").hex(),
            payload_path_utf16le="C:/fixture/expected.bin\0".encode("utf-16-le").hex(), payload_bytes=len(raw),
            chunk_count=len(facts.descriptors), highlow_count=len(facts.fixups),
            hash_receipts=[dict(input_bytes=len(data), open_status=0, hash_status=0, close_status=0, digest_hex=digest)
                           for data, digest in hashes])
        self.base.metadata = metadata
        startup = self.base.startup()
        startup[0][1]["comparison_scope"] = adapter.SCOPE
        rows = [("archive_magic_io", dict(write_return=1, write_error=0, requested=8, returned=8, flush_return=1, flush_error=0), b""),
                ("expected_binding", binding, b"")] + startup[:1] + [("comparison_begin", dict(
                    expected_payload_sha256=metadata["expected_payload_sha256"], read_count=len(facts.descriptors) + 1,
                    scope=adapter.IMMUTABLE_SCOPE), b"")] + startup[1:]
        exception = next(index + 1 for index, row in enumerate(rows) if row[0] == "callback_exception")
        next(row[1] for row in rows if row[0] == "held")["initial_exception_sequence"] = exception
        owned = self.base.owned
        owner = deepcopy(next(row[1] for row in rows if row[0] == "startup_owner"))
        owner.update(native_owner_tid=987, current_native_tid=987)
        for row in rows:
            if row[0] == "startup_owner":
                row[1].update(native_owner_tid=987, current_native_tid=987)
        tick = 1002
        def emit(op, data, original=b""):
            rows.append((op, data, original))
            return len(rows)
        def counter():
            nonlocal tick
            tick += 1
            emit("counter", self.qpc(tick))
        def phase():
            emit("owner", deepcopy(owner)); counter()
            for name, value in zip(image.PHASE_QUERY_NAMES, (6, owned.target.pid, owned.primary_tid, owned.engine_pid, owned.engine_tid)):
                counter(); emit("query", dict(name=name, hresult=0, value=value)); counter()
            counter(); emit("GetNumberBreakpoints", dict(hresult=0, count=0)); counter()
            counter(); emit("pointer64", dict(hresult=1)); counter(); emit("owner", deepcopy(owner))
        counter()
        chunks = ((owned.peb_address + 8, struct.pack("<I", owned.image_base)),) + facts.model_chunks(owned.image_base)
        for ordinal, (address, original) in enumerate(chunks):
            phase(); counter()
            read_sequence = emit("read_virtual_capacity", dict(ordinal=ordinal, address=address,
                requested_bytes=len(original), hresult=0, returned_bytes=len(original)), original)
            counter(); phase(); tick += 1
            before = tick
            before_sequence = emit("comparison_counter", dict(ordinal=ordinal, qpc=self.qpc(tick)))
            tick += 1
            record = adapter.COMPARISON_RECORD.pack(1, ordinal, ordinal - 1 if ordinal else 0xffffffff,
                read_sequence, len(original), len(original), 0, 0, 0xffffffff,
                facts.descriptors[ordinal - 1][5] if ordinal else 0, address, before, tick)
            emit("comparison_result", dict(read_sequence=read_sequence, before_sequence=before_sequence,
                comparison_called=True, post_qpc_called=True, post_qpc=self.qpc(tick)), record)
        phase()
        emit("comparison_complete", dict(read_count=len(chunks), result_count=len(chunks),
            compared_bytes=sum(len(data) for address, data in chunks), expected_payload_sha256=metadata["expected_payload_sha256"]))
        counter()
        self.base.recorder.tick = tick
        rows.extend(self.base.ending())
        return rows

    def authority(self, raw, **changes):
        metadata = self.metadata
        values = {name: metadata[name] for name in adapter.ArchiveAuthority.__dataclass_fields__
                  if name in metadata}
        values.update(candidate_file_sha256=metadata["candidate_sha256"], host_file_sha256=self.base.owned.debugger.image_sha256,
                      archive_sha256=adapter._sha(raw), archive_size=len(raw), native_exit_code=0)
        values.update(changes)
        return adapter.ArchiveAuthority(**values)

    def reject(self, rows, *, authority=None):
        raw = encode(rows)
        with self.assertRaises(adapter.ArchiveError) as caught:
            self.parse(raw, authority or self.authority(raw), self.request)
        self.assertIs(caught.exception.original_archive, raw)
        return caught.exception

    def index(self, op):
        return next(index for index, row in enumerate(self.rows) if row[0] == op)

    def test_complete_source_bound_fixture_replays_without_broad_claims(self):
        raw = encode(self.rows)
        parsed = self.parse(raw, self.authority(raw), self.request)
        result = self.replay(parsed, self.base.owned, self.anchor)
        self.assertTrue(result.report()["immutable_comparison_replay_passed"])
        self.assertTrue(result.report()["fixture_only"])
        self.assertTrue(all(result.report()[name] is False for name in adapter.FALSE_CLAIMS))
        self.assertIs(result.original_archive, raw)
        self.assertTrue(self.model_reached)
        self.assertTrue(self.fixture(raw, self.facts, self.authority(raw)).report()["fixture_only"])

    def test_failed_partial_read_original_capacity_and_signed_hresult_are_retained(self):
        for name, value in (("hresult", -2147467259), ("returned_bytes", 3), ("returned_bytes", 5)):
            rows = deepcopy(self.rows); index = self.index("read_virtual_capacity")
            rows[index][1][name] = value
            error = self.reject(rows)
            self.assertEqual(error.frames[index].raw, rows[index][2])
            self.assertEqual(error.frames[index].data()[name], value)

    def test_missing_duplicate_or_reordered_required_operations_fail(self):
        for op in ("expected_binding", "comparison_begin", "owner", "query", "read_virtual_capacity",
                   "comparison_counter", "comparison_result", "comparison_complete", "stop", "cleanup"):
            index = self.index(op)
            for kind in ("missing", "duplicate", "reordered"):
                with self.subTest(op=op, kind=kind):
                    rows = deepcopy(self.rows)
                    if kind == "missing":
                        del rows[index]
                    elif kind == "duplicate":
                        rows.insert(index, deepcopy(rows[index]))
                    else:
                        other = index + 1 if index + 1 < len(rows) else index - 1
                        rows[index], rows[other] = rows[other], rows[index]
                    self.reject(rows)

    def test_result_fields_are_recomputed_not_report_booleans(self):
        index = self.index("comparison_result")
        for field, value in (("version", 2), ("ordinal", 1), ("descriptor_index", 0), ("read_frame_sequence", 1),
                             ("requested_bytes", 3), ("returned_bytes", 3), ("comparison_status", 2),
                             ("mismatch_count", 1), ("first_mismatch", 0), ("applied_highlow_count", 1),
                             ("address", 1), ("before_tick", -1), ("after_tick", -7)):
            with self.subTest(field=field):
                rows = deepcopy(self.rows)
                values = adapter.decode_comparison_record(rows[index][2]); values[field] = value
                rows[index] = (rows[index][0], rows[index][1], adapter.COMPARISON_RECORD.pack(*(values[name] for name in adapter.RESULT_FIELDS)))
                self.reject(rows)

    def test_wrong_peb_base_candidate_bytes_and_fixup_count_fail(self):
        for index in (self.index("read_virtual_capacity"), next(i for i, row in enumerate(self.rows)
                     if row[0] == "read_virtual_capacity" and row[1]["ordinal"] == 1)):
            rows = deepcopy(self.rows); raw = bytearray(rows[index][2]); raw[0] ^= 1
            rows[index] = (rows[index][0], rows[index][1], bytes(raw)); self.reject(rows)

    def test_correctly_reported_byte_mismatch_is_still_a_failed_comparison(self):
        rows = deepcopy(self.rows)
        index = next(i for i, row in enumerate(rows) if row[0] == "read_virtual_capacity" and row[1]["ordinal"] == 1)
        changed = bytearray(rows[index][2]); changed[0] ^= 1
        rows[index] = (rows[index][0], rows[index][1], bytes(changed))
        result_index = next(i for i, row in enumerate(rows) if row[0] == "comparison_result"
                            and adapter.decode_comparison_record(row[2])["ordinal"] == 1)
        result = adapter.decode_comparison_record(rows[result_index][2])
        result.update(comparison_status=1, mismatch_count=1, first_mismatch=0)
        rows[result_index] = (rows[result_index][0], rows[result_index][1],
                             adapter.COMPARISON_RECORD.pack(*(result[name] for name in adapter.RESULT_FIELDS)))
        error = self.reject(rows)
        self.assertIn("immutable byte mismatch", str(error))
        self.assertEqual(error.frames[index].raw, bytes(changed))

    def test_qpc_phase_owner_generation_and_thread_failures_cannot_complete(self):
        variants = (("comparison_counter", ("qpc", "counter_native_return"), 0),
                    ("comparison_result", ("post_qpc", "tick"), 1000),
                    ("comparison_result", ("comparison_called",), False),
                    ("comparison_result", ("read_sequence",), 1),
                    ("owner", ("current_native_tid",), 988), ("owner", ("native_owner_tid",), 0),
                    ("owner", ("target", "creation_filetime"), 99), ("owner", ("probe_sequence",), False),
                    ("query", ("hresult",), -2147467259), ("pointer64", ("hresult",), 0))
        for operation, path, value in variants:
            with self.subTest(operation=operation, path=path):
                rows = deepcopy(self.rows); data = rows[self.index(operation)][1]
                for name in path[:-1]: data = data[name]
                data[path[-1]] = value
                self.reject(rows)

    def test_hash_receipts_must_be_original_complete_ordered_and_successful(self):
        index = self.index("expected_binding")
        for field, value in (("input_bytes", 3), ("open_status", -1), ("hash_status", -2147467259),
                             ("close_status", -1), ("digest_hex", "0" * 64)):
            rows = deepcopy(self.rows); rows[index][1]["hash_receipts"][0][field] = value
            self.reject(rows)
        rows = deepcopy(self.rows); hashes = rows[index][1]["hash_receipts"]; hashes[0], hashes[1] = hashes[1], hashes[0]
        self.reject(rows)

    def test_external_bindings_unknown_flags_and_exit_failure_fail(self):
        raw = encode(self.rows)
        for name in ("candidate_file_sha256", "request_sha256", "expected_payload_sha256", "probe_sha256",
                     "contract_sha256", "source_closure_sha256", "producer_source_closure_sha256",
                     "host_file_sha256", "host_source_sha256", "native_source_sha256", "adapter_source_sha256"):
            with self.subTest(name=name), self.assertRaises(adapter.ArchiveError):
                self.parse(raw, self.authority(raw, **{name: "f" * 64}), self.request)
        rows = deepcopy(self.rows); rows[self.index("invocation")][1]["passed"] = True; self.reject(rows)
        with self.assertRaises(adapter.ArchiveError):
            self.parse(raw, self.authority(raw, native_exit_code=1), self.request)

    def test_private_fixture_requests_and_parsed_clones_have_no_production_authority(self):
        raw = encode(self.rows)
        with self.assertRaises(adapter.ArchiveError):
            adapter.parse_archive(raw, self.authority(raw), self.request)
        parsed = self.parse(raw, self.authority(raw), self.request)
        clone = type(parsed)(parsed.original_archive, parsed.frames)
        with self.assertRaises(adapter.ArchiveError):
            self.replay(clone, self.base.owned, self.anchor)

    def test_parsed_archive_mutation_retains_issued_original_and_supplied_bytes(self):
        raw = encode(self.rows)
        parsed = self.parse(raw, self.authority(raw), self.request)
        changed = raw + b"mutated capability bytes"
        object.__setattr__(parsed, "original_archive", changed)
        with self.assertRaises(adapter.ArchiveError) as caught:
            self.replay(parsed, self.base.owned, self.anchor)
        self.assertIs(caught.exception.original_archive, raw)
        self.assertIs(caught.exception.original_observation, changed)

    def test_parsed_frame_mutation_rejects_the_unchanged_raw_archive(self):
        raw = encode(self.rows)
        parsed = self.parse(raw, self.authority(raw), self.request)
        row = parsed.frames[self.index("comparison_result")]
        object.__setattr__(row, "raw", b"\0" * 64)
        with self.assertRaises(adapter.ArchiveError) as caught:
            self.replay(parsed, self.base.owned, self.anchor)
        self.assertIs(caught.exception.original_archive, raw)

    def test_public_helper_aliases_cannot_execute_or_supply_validator_authority(self):
        raw = encode(self.rows)
        external = self.authority(raw)
        executed = []
        def poison(*args, **kwargs):
            executed.append((args, kwargs))
            raise AssertionError("public authority helper executed")
        with patch.multiple(adapter, V1_ADAPTER=Path("C:/foreign/validator.py"),
                            GENERATOR=Path("C:/foreign/generator.py"),
                            _sha=poison, _source_helpers=poison, _protocol=poison,
                            types=object(), sys=object(), uuid=object(),
                            ArchiveAuthority=object(), ArchiveError=object()), \
             patch.multiple(image, _path=poison, Generation=poison,
                            PHASE_QUERY_NAMES=("invented",)), \
             patch.multiple(native, _factory=poison, _closed_preparation=poison,
                            _private_preparation=poison, _render=poison, _sha=poison,
                            inspect_comparison_request=poison), \
             patch.multiple(session, QpcSample=poison, project=poison, _clone=poison):
            _, _, _, parse, replay, fixture = adapter._api_factory(_inspector=self.inspect)
            parsed = parse(raw, external, self.request)
            result = replay(parsed, self.base.owned, self.anchor)
            self.assertTrue(result.report()["immutable_comparison_replay_passed"])
        self.assertEqual(executed, [])

    def test_main_packet_write_and_flush_failures_remain_original_sticky_debt(self):
        raw = encode(self.rows)
        row = adapter.parse_frames(raw)[self.index("comparison_result")]
        original = tuple(adapter.IO_FOOTER.unpack(row.footer))
        for slot, value in ((0, 0), (2, original[2] + 1), (3, original[3] - 1), (4, 0)):
            with self.subTest(slot=slot):
                footer = list(original); footer[slot] = value
                offset = row.offset + 8 + len(row.metadata) + len(row.raw)
                failed = raw[:offset] + adapter.IO_FOOTER.pack(*footer) + raw[offset + 24:]
                with self.assertRaises(adapter.ArchiveError) as caught:
                    self.parse(failed, self.authority(failed), self.request)
                self.assertIs(caught.exception.original_archive, failed)
                self.assertEqual(caught.exception.frames[row.sequence - 1].footer,
                                 adapter.IO_FOOTER.pack(*footer))

    def test_magic_write_failure_and_magic_flush_failure_retain_distinct_originals(self):
        for failure in (dict(write_return=0, write_error=5, requested=8, returned=3,
                             flush_return=0, flush_error=6),
                        dict(write_return=1, write_error=123, requested=8, returned=8,
                             flush_return=0, flush_error=112)):
            with self.subTest(failure=failure):
                rows = deepcopy(self.rows); rows[0] = ("archive_magic_io", failure, b"")
                error = self.reject(rows)
                self.assertEqual(error.frames[0].data(), failure)
                self.assertEqual(error.frames[0].data()["flush_error"], failure["flush_error"])
        # A magic-write failure may leave no framed journal at all. These
        # supplied original bytes remain failure diagnostics, never a receipt.
        for original in (b"", adapter.MAGIC[:3], adapter.MAGIC):
            with self.assertRaises(adapter.ArchiveError) as caught:
                adapter.parse_frames(original)
            self.assertIs(caught.exception.original_archive, original)

    def test_source_drift_before_private_compile_rejects_before_any_execution(self):
        source = Path(adapter.__file__).resolve()
        read = Path.read_bytes
        original = source.read_bytes()
        before = {name for name in sys.modules if name.startswith("_clash_compare_")}
        def altered(path):
            return original + b"\n# changed\n" if path.resolve() == source else read(path)
        with patch.object(Path, "read_bytes", altered), self.assertRaisesRegex(ValueError, "before private compilation"):
            adapter._api_factory(_inspector=self.inspect)
        self.assertEqual({name for name in sys.modules if name.startswith("_clash_compare_")}, before)

    def test_fixed_dependency_drift_rejects_and_cleans_private_namespaces(self):
        read = Path.read_bytes
        dependency = Path(image.__file__).resolve()
        original = dependency.read_bytes()
        before = {name for name in sys.modules if name.startswith("_clash_compare_")}
        def altered(path):
            return original + b"\n# changed\n" if path.resolve() == dependency else read(path)
        with patch.object(Path, "read_bytes", altered), self.assertRaisesRegex(ValueError, "dependency source changed"):
            adapter._api_factory(_inspector=self.inspect)
        self.assertEqual({name for name in sys.modules if name.startswith("_clash_compare_")}, before)

    def test_source_drift_after_model_cannot_publish_a_result(self):
        raw = encode(self.rows)
        external = self.authority(raw)
        source, original, read = Path(adapter.__file__).resolve(), self.snapshots[0], Path.read_bytes
        completed = []
        def model(base):
            value = self.facts.model_chunks(base)
            completed.append(True)
            return value
        def altered(path):
            return original + b"\n# after model\n" if completed and path.resolve() == source else read(path)
        facts = replace(self.facts, model_chunks=model)
        with patch.object(Path, "read_bytes", altered), self.assertRaises(adapter.ArchiveError) as caught:
            self.fixture(raw, facts, external)
        self.assertEqual(completed, [True])
        self.assertIs(caught.exception.original_archive, raw)
        self.assertEqual(len(caught.exception.frames), len(self.rows) + 1)

    def test_sole_terminal_factory_ast_rejects_an_additional_factory_before_exec(self):
        source = Path(adapter.__file__).resolve()
        original = source.read_bytes()
        terminal = b"prepare_comparison_plan, prepare_comparison_request, inspect_comparison_request, parse_archive, replay_archive, replay_fixture_archive = _api_factory()"
        modified = original.replace(terminal, b"_api_factory()\n" + terminal)
        self.assertNotEqual(modified, original)
        read = Path.read_bytes
        def altered(path):
            return modified if path.resolve() == source else read(path)
        before = {name for name in sys.modules if name.startswith("_clash_compare_")}
        with patch.object(Path, "read_bytes", altered), self.assertRaisesRegex(ValueError, "sole exact terminal"):
            adapter._api_factory(_inspector=self.inspect, _raw=modified)
        self.assertEqual({name for name in sys.modules if name.startswith("_clash_compare_")}, before)

    def test_generator_ast_rejects_a_second_issuance_call_before_execution(self):
        source = Path(native.__file__).resolve()
        original = source.read_bytes()
        terminal = b"prepare_comparison_plan, prepare_comparison_request, inspect_comparison_request = _factory()"
        modified = original.replace(terminal, b"_factory()\n" + terminal)
        self.assertNotEqual(modified, original)
        read = Path.read_bytes
        def altered(path):
            return modified if path.resolve() == source else read(path)
        before = {name for name in sys.modules if name.startswith("_clash_compare_")}
        with patch.object(Path, "read_bytes", altered), self.assertRaisesRegex(ValueError, "sole exact terminal generator"):
            adapter._api_factory(_inspector=self.inspect, _generator_raw=modified)
        self.assertEqual({name for name in sys.modules if name.startswith("_clash_compare_")}, before)

    def test_generator_drift_and_other_registry_capabilities_reject_before_inspection(self):
        raw = encode(self.rows)
        external = self.authority(raw)
        source = Path(native.__file__).resolve()
        original, read = source.read_bytes(), Path.read_bytes
        def altered(path):
            return original + b"\n# drift\n" if path.resolve() == source else read(path)
        with patch.object(Path, "read_bytes", altered), self.assertRaises(adapter.ArchiveError) as caught:
            adapter.parse_archive(raw, external, self.request)
        self.assertIs(caught.exception.original_archive, raw)
        self.assertEqual(caught.exception.frames, ())
        for foreign in (self.request, native.ComparisonRequest(self.request.binding_json),
                        type(self.request)(self.request.binding_json)):
            with self.assertRaises(ValueError):
                adapter.inspect_comparison_request(foreign)
            with self.assertRaises(adapter.ArchiveError):
                adapter.parse_archive(raw, external, foreign)
        self.assertNotEqual(adapter.inspect_comparison_request, native.inspect_comparison_request)

    def test_reused_private_issuance_apis_check_adapter_source_before_preparation(self):
        source = Path(adapter.__file__).resolve()
        original, read = source.read_bytes(), Path.read_bytes
        def altered(path):
            return original + b"\n# drift\n" if path.resolve() == source else read(path)
        with patch.object(Path, "read_bytes", altered):
            for operation, arguments in ((adapter.prepare_comparison_plan, (b"not an original", self.base.bound)),
                                         (adapter.prepare_comparison_request, (object(), object())),
                                         (adapter.inspect_comparison_request, (self.request,))):
                with self.assertRaisesRegex(ValueError, "before private issuance"):
                    operation(*arguments)

    def test_supplied_validator_helpers_cannot_attach_to_the_production_registry(self):
        with self.assertRaisesRegex(ValueError, "explicit fixture registries"):
            adapter._api_factory(_helpers=(object(), ()))

    def test_complete_original_output_packets_are_transparent_but_not_replacements(self):
        rows = deepcopy(self.rows)
        rows.insert(self.index("stop"), ("output", dict(mask=1, text_hex=b"original debugger output\0".hex()), b""))
        raw = encode(rows)
        self.assertTrue(self.fixture(raw, self.facts, self.authority(raw)).report()["immutable_comparison_replay_passed"])
        for text in (b"missing terminator", b"extra\0text\0"):
            failed = deepcopy(rows); failed[self.index("stop")] = ("output", dict(mask=1, text_hex=text.hex()), b"")
            self.reject(failed)

    def test_native_failure_cannot_be_overruled_by_later_complete_cleanup_and_finish(self):
        rows = deepcopy(self.rows)
        capacity = b"ABCDEFGH"
        rows.insert(self.index("stop"), ("native_failure", dict(api_name="ReadFile", requested_bytes=8,
            returned_bytes=3, native_return=0, native_error=5, detail_hex=""), capacity))
        error = self.reject(rows)
        self.assertIn("sticky native failure", str(error))
        failure = next(row for row in error.frames if row.operation == "native_failure")
        self.assertEqual(failure.raw, capacity)
        self.assertEqual(failure.data()["returned_bytes"], 3)


if __name__ == "__main__":
    unittest.main()

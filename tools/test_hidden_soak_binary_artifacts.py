#!/usr/bin/env python3
"""RAM-authored selected-patch fixtures; never retail or native execution proof.

The fixture constructor seals an inventory once, before test mutations. Only
the production reader boundary is replaced inside explicit test contexts. Real
patch selection, byte observations, JSON checks and provenance policy execute.
"""

from __future__ import annotations

import copy
import hashlib
import json
import struct
import tempfile
import unittest
from functools import lru_cache
from pathlib import Path, PureWindowsPath
from unittest import mock

import hidden_soak_binary_artifacts as binaries
import hidden_soak_probe_composition as composition
import patch_stage_report


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2).encode("ascii")


def _minimal_pe(size: int, *, dll: bool = False) -> bytearray:
    data = bytearray(max(size, 512))
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", data, 0x84, 0x14C, 1)
    struct.pack_into("<HH", data, 0x94, 224, 0x2102 if dll else 0x0102)
    struct.pack_into("<H", data, 0x98, 0x10B)
    struct.pack_into("<I", data, 0x98 + 28, 0x400000)
    data[0x178:0x180] = b".fixture"
    struct.pack_into("<IIII", data, 0x180, len(data) - 512, 0x1000, len(data) - 512, 512)
    return data


@lru_cache(maxsize=1)
def _synthetic_candidate() -> bytes:
    patcher = patch_stage_report.load_patcher()
    selected = patcher.select_patches(binaries.PROTECTED_STAGE)
    data = _minimal_pe(max(patch.offset + len(patch.new) for patch in selected))
    for patch in selected:
        data[patch.offset:patch.offset + len(patch.new)] = patch.new
    return bytes(data)


def synthetic_binary_inventory(payload: dict, *, candidate_variant: int = 0) -> tuple[dict, dict[str, bytes]]:
    """Seal a deep-copied canonical report and fixed, synthetic byte inventory.

    Call only before mutations. This constructor does not authenticate or read
    the original executable, manufacture its hash preimage, write binaries, or
    stub the production patch policy. Its candidate contains source-defined
    selected.new records in an independently authored PE envelope; all other
    bytes are zero. Passing means selected-patch consistency only.
    """
    result = copy.deepcopy(payload)
    inventory: dict[str, bytes] = {}
    if type(candidate_variant) is not int or candidate_variant not in (0, 1):
        raise ValueError("synthetic candidate_variant must be integer 0 or 1")
    candidate = _synthetic_candidate()
    if candidate_variant:
        # Independently authored, unselected DOS-stub byte: it changes the
        # retained candidate identity without altering any selected patch or
        # PE header observation. This is not an original-backed variant.
        varied = bytearray(candidate)
        varied[0x40] = 1
        candidate = bytes(varied)
    result["candidate_sha256"] = _sha(candidate)
    inventory[result["candidate"]] = candidate
    result["patch_stage_report"] = str(PureWindowsPath(result["output_directory"]) / "patch-stage.json")
    patch = patch_stage_report.build_report(
        binaries._RetainedCandidate(result["candidate"], candidate), binaries.PROTECTED_STAGE, "800x600")
    inventory[result["patch_stage_report"]] = _json(patch)

    proxy = result["proxy"]
    proxy_bytes = bytes(_minimal_pe(1024, dll=True))
    inventory[proxy["path"]] = proxy_bytes
    proxy["sha256"] = _sha(proxy_bytes)
    proxy["used"] = True
    proxy["present_enabled"] = False
    manifest = {
        "generated_by": "clash-hd-surface-dump-proxy", "output": proxy["path"],
        "output_sha256": _sha(proxy_bytes), "build_log": proxy["build_log"],
        "built_at": "synthetic-fixture-not-a-build", "vcvars32": "not-executed",
    }
    for field, (path, sha_field) in binaries._SOURCE_PINS.items():
        inventory[str(path)] = path.read_bytes()
        manifest[field] = str(path)
        manifest[sha_field] = _sha(inventory[str(path)])
    inventory[proxy["build_manifest"]] = _json(manifest)
    inventory[proxy["log"]] = b"ddraw_surfdump_proxy loaded present_enabled=0\r\n"
    inventory[proxy["build_log"]] = b"synthetic fixture only; compiler never invoked\r\n"
    for role, path in binaries._PROBE_PINS.items():
        result[role] = str(path)
        inventory[str(path)] = path.read_bytes()
    # The runner's canonical composition of the pinned templates; never executed.
    parameters = {"route": result.get("route"), "duration_sec": result.get("duration_sec"),
                  "pan_interval_sec": result.get("pan_interval_sec") or 10, "load_slot": result.get("load_slot"),
                  "raw_path": str(PureWindowsPath(result["output_directory"]) / "frames" / "surface.raw")}
    result["probe_composition"] = {"schema": "hidden_soak_probe_composition_v1",
                                   "composer_sha256": composition.composer_sha256(), "parameters": parameters}
    inventory[result["generated_probe"]] = composition.compose_probe(
        inventory[result["probe_template"]], inventory[result["soak_probe_template"]], **parameters)
    for role in ("patch_stage_report", "generated_probe", *binaries._PROBE_PINS):
        data = inventory[result[role]]
        result[f"{role}_sha256"] = _sha(data)
        result[f"{role}_size"] = len(data)
    for role in ("build_manifest", "log", "build_log"):
        data = inventory[proxy[role]]
        proxy[f"{role}_sha256"] = _sha(data)
        proxy[f"{role}_size"] = len(data)
    return result, inventory


def _key(path: str) -> str:
    return str(PureWindowsPath(path)).casefold() if len(path) > 2 and path[1:3] in (":\\", ":/") else path


def reader_from_inventory(inventory: dict[str, bytes]):
    """Freeze this inventory; lookups never repair receipts or report changes."""
    frozen = {_key(path): data for path, data in inventory.items()}

    def read(path: str, maximum: int) -> bytes:
        try:
            data = frozen[_key(path)]
        except KeyError as exc:
            raise FileNotFoundError(f"not in fixed RAM inventory: {path}") from exc
        if len(data) > maximum:
            raise ValueError("fixed RAM artifact exceeds maximum")
        return data

    return read


def _payload() -> dict:
    candidate_run = PureWindowsPath(r"C:\ClashTests\hd-soak\hidden\binary-fixture")
    output = PureWindowsPath(r"C:\ClashCaptures\hd-soak\hidden\binary-fixture")
    return {
        "environment": "hidden_cdb_host", "stage": binaries.PROTECTED_STAGE,
        "input_exe": r"C:\Clash\clash95.exe", "input_sha256": binaries.EXPECTED_BASE_SHA256,
        "workdir": r"C:\Clash", "candidate": str(candidate_run / "candidate.exe"),
        "output_directory": str(output), "cdb_log": str(output / "cdb.log"),
        "generated_probe": str(output / "probe.generated.cdb"), "load_slot": 2,
        "route": "map-pan", "duration_sec": 120, "pan_interval_sec": 10,
        "proxy": {
            "path": str(candidate_run / "ddraw.dll"),
            "build_manifest": str(candidate_run / "ddraw_surfdump_proxy.build.json"),
            "log": str(candidate_run / "ddraw_surfdump_proxy.log"),
            "build_log": str(output / "build" / "build.log"),
        },
    }


class RetainedBinaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload, self.inventory = synthetic_binary_inventory(_payload())

    def evaluate(self, payload=None, inventory=None):
        with mock.patch.object(binaries, "_read_retained_file", side_effect=reader_from_inventory(
                self.inventory if inventory is None else inventory)):
            return binaries.validate_retained_binaries(self.payload if payload is None else payload)

    def assert_rejected(self, payload=None, inventory=None, fragment=None):
        summary, failures = self.evaluate(payload, inventory)
        self.assertFalse(summary["retained_bytes_consistent"])
        self.assertTrue(failures)
        if fragment:
            self.assertIn(fragment, "; ".join(failures))

    def replace_receipted(self, role: str, data: bytes) -> None:
        owner = self.payload["proxy"] if role.startswith("proxy.") else self.payload
        field = role.removeprefix("proxy.")
        self.inventory[owner[field]] = data
        owner[f"{field}_sha256"] = _sha(data)
        owner[f"{field}_size"] = len(data)

    def test_positive_uses_real_patch_policy_without_original_authentication(self):
        summary, failures = self.evaluate()
        self.assertEqual(failures, [])
        self.assertTrue(summary["retained_bytes_consistent"])
        self.assertGreater(summary["candidate_patch_report"]["patch_count"], 100)
        self.assertEqual(summary["candidate_patch_report"]["status_counts"],
                         {"patched": summary["candidate_patch_report"]["patch_count"]})
        for field in ("original_file_authenticated", "loaded_image_authenticated", "native_execution_authenticated"):
            self.assertIs(summary[field], False)
        self.assertIs(summary["canonical_probe_regeneration_authenticated"], True)
        self.assertIs(summary["probe_composition"]["same_composer_source"], True)
        self.assertNotIn(self.payload["input_exe"], self.inventory)
        with mock.patch.object(binaries, "_read_retained_file", side_effect=reader_from_inventory(self.inventory)) as reader:
            patch, error = binaries.read_retained_patch(self.payload)
            self.assertIsNone(error)
            self.assertEqual(patch["exe_sha256"].lower(), self.payload["candidate_sha256"])
            self.assertEqual(reader.call_count, 1)

    def test_distinct_synthetic_candidate_identities_use_real_patch_regrades(self):
        variant, inventory = synthetic_binary_inventory(_payload(), candidate_variant=1)
        self.assertNotEqual(variant["candidate_sha256"], self.payload["candidate_sha256"])
        summary, failures = self.evaluate(variant, inventory)
        self.assertEqual(failures, [])
        self.assertEqual(summary["candidate_patch_report"]["exe_sha256"].lower(), variant["candidate_sha256"])
        for invalid in (True, 2, -1, "1"):
            with self.assertRaises(ValueError):
                synthetic_binary_inventory(_payload(), candidate_variant=invalid)

    def test_windows_case_slash_and_digest_case_are_normalized(self):
        payload = copy.deepcopy(self.payload)
        for field in ("input_exe", "workdir", "candidate", "output_directory", "cdb_log",
                      "generated_probe", "patch_stage_report"):
            payload[field] = payload[field].upper().replace("\\", "/")
        for field in ("path", "build_manifest", "log", "build_log"):
            payload["proxy"][field] = payload["proxy"][field].upper().replace("\\", "/")
        payload["candidate_sha256"] = payload["candidate_sha256"].upper()
        payload["proxy"]["sha256"] = payload["proxy"]["sha256"].upper()
        summary, failures = self.evaluate(payload)
        self.assertEqual(failures, [])
        self.assertTrue(summary["retained_bytes_consistent"])

    def test_missing_or_changed_artifacts_revoke_receipts(self):
        for path in self.inventory:
            with self.subTest(path=path, mode="missing"):
                altered = dict(self.inventory)
                del altered[path]
                self.assert_rejected(inventory=altered, fragment="retained read failed")
            with self.subTest(path=path, mode="drift"):
                altered = dict(self.inventory)
                altered[path] += b"\n"
                self.assert_rejected(inventory=altered, fragment="SHA-256 differs")

    def test_receipt_types_and_lengths_fail_closed(self):
        for role in ("patch_stage_report", "generated_probe", "probe_template", "soak_probe_template",
                     "proxy.build_manifest", "proxy.log", "proxy.build_log"):
            for suffix, bad in (("sha256", None), ("sha256", "z" * 64), ("sha256", 3),
                                ("size", None), ("size", True), ("size", -1), ("size", 1.0), ("size", 0)):
                with self.subTest(role=role, suffix=suffix, value=bad):
                    payload = copy.deepcopy(self.payload)
                    owner = payload["proxy"] if role.startswith("proxy.") else payload
                    owner[f"{role.removeprefix('proxy.')}_{suffix}"] = bad
                    self.assert_rejected(payload, fragment="receipt")

    def test_patch_manifest_requires_actual_candidate_regrade(self):
        patch = json.loads(self.inventory[self.payload["patch_stage_report"]])
        for field, value in (("patch_count", 1), ("stage", "another-stage"), ("resolution", "640x480"),
                             ("status_counts", {"patched": True}), ("exe", r"C:\other.exe")):
            with self.subTest(field=field):
                changed = copy.deepcopy(patch)
                changed[field] = value
                self.replace_receipted("patch_stage_report", _json(changed))
                self.assert_rejected(fragment="patch_stage_report")
        self.replace_receipted("patch_stage_report", _json(patch))
        data = bytearray(self.inventory[self.payload["candidate"]])
        data[patch["patches"][0]["offset"]] ^= 1
        self.inventory[self.payload["candidate"]] = bytes(data)
        self.payload["candidate_sha256"] = _sha(bytes(data))
        self.assert_rejected(fragment="not every selected")
        # Even an honestly rebuilt negative patch manifest cannot manufacture
        # selected-stage acceptance from an unpatched candidate.
        actual = patch_stage_report.build_report(binaries._RetainedCandidate(self.payload["candidate"], bytes(data)),
                                               binaries.PROTECTED_STAGE, "800x600")
        self.replace_receipted("patch_stage_report", _json(actual))
        self.assert_rejected(fragment="not every selected")

    def test_proxy_manifest_binds_exact_sources_and_paths(self):
        original = json.loads(self.inventory[self.payload["proxy"]["build_manifest"]])
        fields = {"generated_by": "another-builder", "output": r"C:\other\ddraw.dll",
                  "output_sha256": "0" * 64, "build_log": r"C:\other\build.log"}
        for field, (_, sha_field) in binaries._SOURCE_PINS.items():
            fields[field] = "unrelated-source"
            fields[sha_field] = "0" * 64
        for field, value in fields.items():
            with self.subTest(field=field):
                manifest = dict(original)
                manifest[field] = value
                self.replace_receipted("proxy.build_manifest", _json(manifest))
                self.assert_rejected(fragment="proxy.")

    def test_runtime_log_observation_is_exact_single_disabled_row(self):
        for data in (b"startup prose ddraW\n", b"startup ddraw_surfdump_proxy loaded present_enabled=0\n",
                     b"startup\vddraw_surfdump_proxy loaded present_enabled=0\n",
                     "startup\u2028ddraw_surfdump_proxy loaded present_enabled=0\n".encode("utf-8"),
                     b"ddraw_surfdump_proxy loaded present_enabled=1\n",
                     b"ddraw_surfdump_proxy loaded present_enabled=0\n" * 2,
                     b"ddraw_surfdump_proxy loaded present_enabled=0\nddraw_surfdump_proxy loaded present_enabled=2\n",
                     b"ddraw_surfdump_proxy loaded present_enabled=0\nPROXY_PRESENT_WINDOW created\n", b"\xff"):
            with self.subTest(data=data):
                self.replace_receipted("proxy.log", data)
                self.assert_rejected(fragment="proxy.log")

    def test_proxy_pe_rejects_malformed_or_non_x86_dll(self):
        original = self.inventory[self.payload["proxy"]["path"]]
        edits = ((0, b"XX"), (0x80, b"PX\0\0"), (0x84, struct.pack("<H", 0x8664)),
                 (0x96, struct.pack("<H", 0x0102)), (0x98, struct.pack("<H", 0x20B)),
                 (0x86, struct.pack("<H", 0)), (0x3C, struct.pack("<I", 0xFFFFFFFF)))
        for offset, value in edits:
            with self.subTest(offset=offset):
                data = bytearray(original)
                data[offset:offset + len(value)] = value
                self.inventory[self.payload["proxy"]["path"]] = bytes(data)
                self.payload["proxy"]["sha256"] = _sha(bytes(data))
                manifest = json.loads(self.inventory[self.payload["proxy"]["build_manifest"]])
                manifest["output_sha256"] = _sha(bytes(data))
                self.replace_receipted("proxy.build_manifest", _json(manifest))
                self.assert_rejected(fragment="proxy:")

    def test_empty_or_truncated_artifacts_fail_closed(self):
        for role in ("patch_stage_report", "generated_probe", "probe_template", "soak_probe_template",
                     "proxy.build_manifest", "proxy.log", "proxy.build_log"):
            with self.subTest(role=role):
                payload, inventory = synthetic_binary_inventory(_payload())
                owner = payload["proxy"] if role.startswith("proxy.") else payload
                field = role.removeprefix("proxy.")
                inventory[owner[field]] = b""
                owner[f"{field}_sha256"], owner[f"{field}_size"] = _sha(b""), 0
                self.assert_rejected(payload, inventory)
        self.inventory[self.payload["candidate"]] = b"MZ"
        self.payload["candidate_sha256"] = _sha(b"MZ")
        self.assert_rejected(fragment="candidate")

    def test_malformed_retained_json_and_duplicate_keys(self):
        for role in ("patch_stage_report", "proxy.build_manifest"):
            for data in (b"[]", b'{"x":1,"x":2}', b'{"x":NaN}', b"\xff", b"{"):
                with self.subTest(role=role, data=data):
                    self.replace_receipted(role, data)
                    self.assert_rejected(fragment="invalid retained JSON")

    def test_canonical_patch_path_and_layout_fail_before_unrelated_reads(self):
        for bad in (r"C:\ClashCaptures\hd-soak\hidden\other\patch-stage.json",
                    r"C:\ClashCaptures\hd-soak\hidden\binary-fixture\nested\patch-stage.json", [], "bad\0path"):
            payload = copy.deepcopy(self.payload)
            payload["patch_stage_report"] = bad
            self.assert_rejected(payload, fragment="canonical")
        payload = copy.deepcopy(self.payload)
        payload["candidate"] = r"C:\unrelated\candidate.exe"
        with mock.patch.object(binaries, "_read_retained_file") as reader:
            summary, failures = binaries.validate_retained_binaries(payload)
            self.assertTrue(failures)
            self.assertFalse(summary["retained_bytes_consistent"])
            reader.assert_not_called()
        for value in (None, [], 3):
            self.assertIsNotNone(binaries.read_retained_patch(value)[1])
            self.assert_rejected(value if value is not None else [], fragment="object")
        payload = copy.deepcopy(self.payload)
        payload["environment"] = "host_visible"
        with mock.patch.object(binaries, "_read_retained_file") as reader:
            self.assertIsNotNone(binaries.read_retained_patch(payload)[1])
            reader.assert_not_called()

    def test_probe_pins_load_slot_and_explicit_proxy_flags(self):
        for field, bad in (("probe_template", "unrelated.cdb"), ("soak_probe_template", None),
                           ("load_slot", "2"), ("load_slot", True), ("load_slot", -1), ("load_slot", 10),
                           ("environment", "host_visible"), ("stage", "another-stage"), ("input_sha256", "a" * 64)):
            with self.subTest(field=field):
                payload = copy.deepcopy(self.payload)
                payload[field] = bad
                self.assert_rejected(payload, fragment=field if field != "stage" else "stage")
        for field, bad in (("used", False), ("present_enabled", True), ("present_enabled", 0.0),
                           ("sha256", None)):
            payload = copy.deepcopy(self.payload)
            payload["proxy"][field] = bad
            self.assert_rejected(payload, fragment="proxy")

    def test_generated_probe_must_be_the_canonical_composition_of_the_retained_templates(self):
        templates = {role: self.inventory[self.payload[role]] for role in binaries._PROBE_PINS}
        parameters = self.payload["probe_composition"]["parameters"]
        other = composition.compose_probe(templates["probe_template"], templates["soak_probe_template"],
                                          **(parameters | {"duration_sec": 600}))
        for data in (self.inventory[self.payload["generated_probe"]] + b"gc\r\n", other):
            with self.subTest(generated=len(data)):
                self.setUp()
                self.replace_receipted("generated_probe", data)  # Receipts match; only the rebuild differs.
                self.assert_rejected(fragment="canonical composition")
        self.setUp()
        self.replace_receipted("soak_probe_template", templates["soak_probe_template"] + b".echo changed template\r\n")
        self.assert_rejected(fragment="canonical composition")
        self.setUp()
        self.replace_receipted("soak_probe_template", templates["soak_probe_template"].replace(b"__SOAK_PAN__", b"1"))
        self.assert_rejected(fragment="missing required placeholders")
        self.setUp()
        for record in (None, "composed", {}, {"schema": "hidden_soak_probe_composition_v1"},
                       {"schema": "other", "parameters": parameters},
                       {"schema": "hidden_soak_probe_composition_v1", "parameters": parameters | {"extra": 1}},
                       {"schema": "hidden_soak_probe_composition_v1",
                        "parameters": {k: v for k, v in parameters.items() if k != "raw_path"}}):
            with self.subTest(record=record):
                payload = copy.deepcopy(self.payload)
                payload["probe_composition"] = record
                self.assert_rejected(payload, fragment="probe_composition must record")
        for field, value in (("route", "map-idle"), ("duration_sec", 600), ("duration_sec", 120.0),
                             ("load_slot", 3), ("pan_interval_sec", 11), ("raw_path", 'C:\\"quoted"')):
            with self.subTest(field=field, value=value):
                payload = copy.deepcopy(self.payload)
                payload["probe_composition"]["parameters"][field] = value
                summary, failures = self.evaluate(payload)
                self.assertFalse(summary["canonical_probe_regeneration_authenticated"])
                self.assertTrue(any("probe_composition" in failure or "canonical composition" in failure
                                    for failure in failures), failures)
        payload = copy.deepcopy(self.payload)
        payload["probe_composition"]["composer_sha256"] = "0" * 64  # Informational: the bytes decide.
        summary, failures = self.evaluate(payload)
        self.assertEqual(failures, [])
        self.assertIs(summary["canonical_probe_regeneration_authenticated"], True)
        self.assertIs(summary["probe_composition"]["same_composer_source"], False)

    def test_private_reader_default_performs_actual_small_file_io(self):
        # This is actual physical IO, not a fixture path escape in the public
        # validator. The lower-level reader is exercised with a tiny temp file.
        with tempfile.TemporaryDirectory(prefix="clash-retained-binary-reader-") as directory:
            path = Path(directory) / "tiny.txt"
            path.write_bytes(b"physical-byte-check")
            artifacts, failures = {}, []
            data = binaries._read("tiny", str(path), 40, artifacts, failures,
                                  expected_sha=_sha(b"physical-byte-check"), expected_size=19, require_receipt=True)
            self.assertEqual(data, b"physical-byte-check")
            self.assertEqual(failures, [])
            binaries._read("tiny", str(path), 40, {}, failures, expected_sha="0" * 64, require_receipt=False)
            self.assertTrue(failures)


def run_tests() -> None:
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(RetainedBinaryTests))
    if not result.wasSuccessful() or result.skipped:
        raise RuntimeError("retained binary artifact tests did not pass completely")


if __name__ == "__main__":
    run_tests()

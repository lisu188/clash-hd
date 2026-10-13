"""Test-only, RAM-backed retained artifacts for the source soak suites.

Adapter pattern::

    with fixture_artifact_reads():
        baseline = seal_fixture(build_complete_unsealed_baseline())
        assert real_production_validator(baseline)
        baseline["frame_samples"][0]["Hash"] = "0" * 64
        assert not real_production_validator(baseline)

Seal only at the end of a baseline builder, after its duration/route setup.
Never seal a negative mutation or wrap the production validator in a sealing
adapter. Each baseline gets unique canonical run paths; its immutable bytes
are registered once. The only mocks are the three private retained-file reader
aliases. Production validators, hashing and the actual patch reporter remain
active. Full indexed8 frames and synthetic binaries stay in RAM. Source-report
JSON may still be written to tiny task-owned temporary files by the caller.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import math
import re
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from pathlib import Path, PureWindowsPath
from types import MappingProxyType
from typing import Any, Iterator
from unittest import mock

from hidden_soak_artifact_layout import HIDDEN_CANDIDATE_ROOT, HIDDEN_OUTPUT_ROOT
from hidden_soak_retained_files import RetainedFileError


_ACTIVE: ContextVar[_FixtureRegistry | None] = ContextVar("hidden_soak_test_artifact_registry", default=None)
_READER_MODULES = (
    ("hidden_soak_retained_files", "_read_retained_file"),
    ("hidden_soak_binary_artifacts", "_read_retained_file"),
    ("hidden_soak_log_observations", "_reader"),
)


def _path_key(path: str) -> str:
    if type(path) is not str or not path:
        raise ValueError("fixture artifact path must be a nonempty string")
    return str(PureWindowsPath(path)).casefold() if re.match(r"^[A-Za-z]:[\\/]", path) else path


class _FixtureRegistry:
    def __init__(self) -> None:
        self._inventory: dict[str, bytes] = {}
        self._overlays: list[dict[str, bytes | None]] = []
        self._sealed: dict[int, dict[str, Any]] = {}
        self._frames: dict[tuple[Any, ...], bytes] = {}
        self._counter = 0
        self._reads: list[tuple[str, int]] = []

    @property
    def inventory(self):
        return MappingProxyType(self._inventory)

    @property
    def reads(self) -> tuple[tuple[str, int], ...]:
        return tuple(self._reads)

    def register(self, inventory: dict[str, bytes]) -> None:
        admitted = {}
        for path, data in inventory.items():
            key = _path_key(path)
            if type(data) is not bytes:
                raise TypeError("fixture artifact backing must be immutable bytes")
            if key in admitted and admitted[key] != data:
                raise ValueError(f"conflicting fixture spellings: {path}")
            if key in self._inventory and self._inventory[key] != data:
                raise ValueError(f"fixture artifact was already sealed with different bytes: {path}")
            admitted[key] = data
        self._inventory.update(admitted)

    def read(self, path: str, max_bytes: int) -> bytes:
        key = _path_key(path)
        self._reads.append((path, max_bytes))
        data = self._inventory.get(key)
        for overlay in self._overlays:
            if key in overlay:
                data = overlay[key]
        if data is None:
            error = FileNotFoundError(f"not in the fixed synthetic retained inventory: {path}")
            raise RetainedFileError("synthetic retained read failed", (error,)) from error
        if type(max_bytes) is not int or max_bytes <= 0 or len(data) > max_bytes:
            error = ValueError(f"synthetic retained bytes exceed requested capacity: {path}")
            raise RetainedFileError("synthetic retained read failed", (error,)) from error
        return data


def _registry() -> _FixtureRegistry:
    registry = _ACTIVE.get()
    if registry is None:
        raise RuntimeError("seal/read fixture artifacts only inside fixture_artifact_reads()")
    return registry


@contextmanager
def fixture_artifact_reads() -> Iterator[_FixtureRegistry]:
    """Scope only private IO aliases; nested suite wrappers share the registry."""
    current = _ACTIVE.get()
    if current is not None:
        yield current
        return
    registry = _FixtureRegistry()
    with ExitStack() as stack:
        for module_name, reader_name in _READER_MODULES:
            module = importlib.import_module(module_name)
            stack.enter_context(mock.patch.object(module, reader_name, side_effect=registry.read))
        token = _ACTIVE.set(registry)
        try:
            yield registry
        finally:
            _ACTIVE.reset(token)


def retained_bytes(path: str) -> bytes:
    """Return original sealed bytes, never a temporary negative-test overlay."""
    registry = _registry()
    key = _path_key(path)
    if key not in registry._inventory:
        raise KeyError(f"artifact has no sealed baseline: {path}")
    return registry._inventory[key]


@contextmanager
def replace_retained_bytes(path: str, data: bytes | None) -> Iterator[None]:
    """Explicit test-only IO fault overlay; never mutate or regenerate backing.

    ``None`` represents a missing retained file. On context exit all reads use
    the unchanged original bytes again. Only already registered paths qualify.
    """
    registry = _registry()
    key = _path_key(path)
    if key not in registry._inventory:
        raise KeyError(f"cannot overlay an unregistered fixture artifact: {path}")
    if data is not None and type(data) is not bytes:
        raise TypeError("fixture replacement must be immutable bytes or None")
    overlay = {key: data}
    registry._overlays.append(overlay)
    try:
        yield
    finally:
        if registry._overlays[-1] is not overlay:
            raise RuntimeError("fixture artifact overlays exited out of order")
        registry._overlays.pop()


def _rebind_paths(value: Any, old_candidate: PureWindowsPath, old_output: PureWindowsPath,
                  candidate: PureWindowsPath, output: PureWindowsPath) -> Any:
    if type(value) is dict:
        return {key: _rebind_paths(item, old_candidate, old_output, candidate, output) for key, item in value.items()}
    if type(value) is list:
        return [_rebind_paths(item, old_candidate, old_output, candidate, output) for item in value]
    if type(value) is str and re.match(r"^[A-Za-z]:[\\/]", value):
        path = PureWindowsPath(value)
        for before, after in ((old_candidate, candidate), (old_output, output)):
            if path == before or before in path.parents:
                return str(after / path.relative_to(before))
    return value


def _frame_bytes(row: dict[str, Any], registry: _FixtureRegistry) -> bytes:
    original_hash, nonblack, colors = row.get("Hash"), row.get("NonblackPercent"), row.get("UniqueSampleColors")
    if type(original_hash) is not str or type(nonblack) not in (int, float) or not 0 <= nonblack <= 100 or not math.isfinite(nonblack):
        raise ValueError("seal only a complete valid frame baseline, before negative mutations")
    if type(colors) is not int or not 1 <= colors <= 256:
        raise ValueError("fixture baseline must declare 1..256 indexed colors")
    key = (original_hash, nonblack, colors)
    if key in registry._frames:
        return registry._frames[key]
    nonzero_count = round(nonblack * 4800)
    zero_present = nonzero_count < 480000
    nonzero_colors = colors - int(zero_present)
    if (nonzero_count == 0) != (nonzero_colors == 0) or nonzero_count < nonzero_colors or nonzero_colors > 255:
        raise ValueError("fixture baseline nonblack/color metrics cannot describe indexed8 bytes")
    if nonzero_colors:
        pattern = bytes(range(1, nonzero_colors + 1))
        nonzero = (pattern * ((nonzero_count + len(pattern) - 1) // len(pattern)))[:nonzero_count]
        data = bytearray(nonzero + b"\0" * (480000 - nonzero_count))
        # Give different declared hash groups independent actual bytes without
        # changing counts or dropping the complete color inventory at the tail.
        seed = hashlib.sha256(original_hash.encode("utf-8")).digest()
        if nonzero_colors > 1 and nonzero_count >= nonzero_colors + len(seed):
            data[:len(seed)] = bytes(1 + number % nonzero_colors for number in seed)
        elif zero_present and nonzero_count >= len(seed) and 480000 - nonzero_count >= len(seed):
            for index, number in enumerate(seed):
                if number & 1:
                    data[index], data[nonzero_count + index] = data[nonzero_count + index], data[index]
        result = bytes(data)
    else:
        result = b"\0" * 480000
    registry._frames[key] = result
    return result


def seal_fixture(payload: dict[str, Any], *, candidate_variant: int = 0) -> dict[str, Any]:
    """Create one pre-mutation baseline and append its immutable RAM artifacts.

    Existing suites must call this at the end of their baseline constructor.
    Builders that extend a report (for example map-pan) first request an
    unsealed parent, finish all setup, then seal once. A second seal of either
    input or returned object is rejected, including after negative mutations.
    """
    registry = _registry()
    if type(payload) is not dict or id(payload) in registry._sealed:
        raise ValueError("fixture must be a fresh baseline object and may only be sealed once")
    baseline = copy.deepcopy(payload)
    old_output = PureWindowsPath(baseline["output_directory"])
    old_candidate = PureWindowsPath(baseline["candidate"]).parent
    if old_output.parent != HIDDEN_OUTPUT_ROOT or old_candidate.parent != HIDDEN_CANDIDATE_ROOT:
        raise ValueError("fixture baseline must start with canonical immediate hidden run roots")
    if old_output.name.startswith("fixture-sealed-") or old_candidate.name.startswith("fixture-sealed-"):
        raise ValueError("copied or mutated sealed fixture reports cannot regenerate their backing")
    registry._counter += 1
    run_name = f"fixture-sealed-{registry._counter:06d}"
    candidate, output = HIDDEN_CANDIDATE_ROOT / run_name, HIDDEN_OUTPUT_ROOT / run_name
    baseline = _rebind_paths(baseline, old_candidate, old_output, candidate, output)
    inventory: dict[str, bytes] = {}
    rows = baseline.get("frame_samples")
    if type(rows) is not list or not rows:
        raise ValueError("fixture baseline needs its complete frame_samples before sealing")
    for index, row in enumerate(rows, 1):
        if type(row) is not dict or row.get("Width") != 800 or row.get("Height") != 600:
            raise ValueError("fixture baseline frames must already use 800x600")
        data = _frame_bytes(row, registry)
        row["Name"] = f"frame-{index:04d}"
        row["RawPath"] = str(output / "frames" / f"{row['Name']}.raw")
        row["Hash"] = hashlib.sha256(data).hexdigest()
        row["NonblackPercent"] = round(((len(data) - data.count(0)) * 100.0 / len(data)) * 1000.0) / 1000.0
        row["UniqueSampleColors"] = len(set(data))
        inventory[row["RawPath"]] = data
    hashes = {row["Hash"] for row in rows}
    summary_fields = {
        "frame_sample_count": len(rows), "frame_hash_unique_count": len(hashes),
        "frame_stability_class": "stable_idle" if len(hashes) == 1 else "progressing",
        "nonblack_percent_min": min(row["NonblackPercent"] for row in rows),
        "nonblack_percent_max": max(row["NonblackPercent"] for row in rows),
        "unique_sample_colors_min": min(row["UniqueSampleColors"] for row in rows),
        "unique_sample_colors_max": max(row["UniqueSampleColors"] for row in rows),
    }
    for field, value in summary_fields.items():
        if field in baseline:
            baseline[field] = value
    # Test helpers author retained bytes; production checking is never mocked.
    from test_hidden_soak_binary_artifacts import synthetic_binary_inventory
    from test_hidden_soak_log_observations import canonical_log_inventory
    baseline, binaries = synthetic_binary_inventory(baseline, candidate_variant=candidate_variant)
    baseline, logs = canonical_log_inventory(baseline)
    for additional in (binaries, logs):
        for path, data in additional.items():
            if path in inventory and inventory[path] != data:
                raise ValueError(f"fixture producers disagree on retained bytes: {path}")
            inventory[path] = data
    registry.register(inventory)
    # Strong references prevent object-id reuse from confusing once-only seals.
    registry._sealed[id(payload)] = payload
    registry._sealed[id(baseline)] = baseline
    return baseline


class ArtifactFixtureRegistryTests(unittest.TestCase):
    def baseline(self, directory: str) -> dict[str, Any]:
        # Reuse the explicit valid report constructor, not a production grader
        # adapter. _seal=False avoids any nested or grade-time reissuance.
        from test_hd_soak_report import passing_hidden_report
        return passing_hidden_report(Path(directory), _seal=False)

    def test_real_validators_accept_fixed_ram_baseline_and_reject_metadata_mutation(self):
        from hidden_soak_binary_artifacts import validate_retained_binaries
        from hidden_soak_log_observations import validate_retained_log
        from hidden_soak_retained_files import validate_retained_frames
        with tempfile.TemporaryDirectory(prefix="hidden-registry-tiny-") as directory, fixture_artifact_reads() as registry:
            baseline = seal_fixture(self.baseline(directory))
            for validator in (validate_retained_binaries, validate_retained_log, validate_retained_frames):
                self.assertEqual(validator(baseline)[1], [])
            original = retained_bytes(baseline["frame_samples"][0]["RawPath"])
            changed = copy.deepcopy(baseline)
            changed["frame_samples"][0]["Hash"] = "0" * 64
            self.assertTrue(validate_retained_frames(changed)[1])
            self.assertIs(retained_bytes(baseline["frame_samples"][0]["RawPath"]), original)
            self.assertTrue(registry.reads)
            with self.assertRaises(TypeError):
                registry.inventory["unregistered"] = b"not mutable"

    def test_original_returned_and_copied_sealed_reports_cannot_be_resealed(self):
        with tempfile.TemporaryDirectory(prefix="hidden-registry-tiny-") as directory, fixture_artifact_reads():
            original = self.baseline(directory)
            baseline = seal_fixture(original)
            for value in (original, baseline, copy.deepcopy(baseline)):
                value["frame_samples"][0]["Hash"] = "0" * 64
                with self.assertRaises(ValueError):
                    seal_fixture(value)

    def test_explicit_missing_and_byte_fault_overlays_restore_unchanged_backing(self):
        from hidden_soak_retained_files import validate_retained_frames
        with tempfile.TemporaryDirectory(prefix="hidden-registry-tiny-") as directory, fixture_artifact_reads():
            baseline = seal_fixture(self.baseline(directory))
            path = baseline["frame_samples"][0]["RawPath"]
            original = retained_bytes(path)
            changed = bytes([original[0] ^ 1]) + original[1:]
            for replacement in (None, changed):
                with replace_retained_bytes(path, replacement):
                    self.assertTrue(validate_retained_frames(baseline)[1])
                    self.assertIs(retained_bytes(path), original)
                self.assertEqual(validate_retained_frames(baseline)[1], [])

    def test_unknown_paths_capacity_nested_scope_and_separate_runner_reset(self):
        with tempfile.TemporaryDirectory(prefix="hidden-registry-tiny-") as directory:
            with fixture_artifact_reads() as first:
                baseline = seal_fixture(self.baseline(directory))
                with fixture_artifact_reads() as nested:
                    self.assertIs(first, nested)
                with self.assertRaises(RetainedFileError):
                    first.read(r"C:\ClashCaptures\unregistered.raw", 480000)
                with self.assertRaises(RetainedFileError):
                    first.read(baseline["frame_samples"][0]["RawPath"], 1)
            with fixture_artifact_reads() as second:
                self.assertEqual(dict(second.inventory), {})
                with self.assertRaises(RetainedFileError):
                    second.read(baseline["frame_samples"][0]["RawPath"], 480000)
            with self.assertRaises(RuntimeError):
                seal_fixture(self.baseline(directory))

    def test_public_dispatcher_fails_default_reads_outside_fixture_scope(self):
        from hd_soak_report import evaluate_report_for_environment
        modules = [(importlib.import_module(name), attribute) for name, attribute in _READER_MODULES]
        original_readers = [getattr(module, attribute) for module, attribute in modules]
        with tempfile.TemporaryDirectory(prefix="hidden-registry-tiny-") as directory:
            with fixture_artifact_reads():
                baseline = seal_fixture(self.baseline(directory))
                inside = evaluate_report_for_environment(baseline)
                self.assertTrue(inside["overall"], inside["failures"])
            for (module, attribute), original in zip(modules, original_readers):
                self.assertIs(getattr(module, attribute), original)
            outside = evaluate_report_for_environment(baseline)
            self.assertFalse(outside["overall"])
            for name in ("retained_binary_bytes", "retained_frame_bytes", "retained_log_bytes"):
                self.assertFalse(outside["checks"][name]["passed"], name)


def run_tests() -> None:
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(ArtifactFixtureRegistryTests))
    if not result.wasSuccessful() or result.skipped:
        raise RuntimeError("artifact fixture registry tests did not pass completely")


if __name__ == "__main__":
    run_tests()

"""Offline, unregistered consistency replay of a NEW paused surface protocol.

No current capture producer emits this protocol. Original native output buffers
are required; older summary timestamps/booleans cannot fill their absence. A
consistent supplied journal is not authenticated native execution. This slice
does not rebuild the candidate or canonical probe, audit artwork, or register a
geometry verifier. Every acceptance/authority flag therefore remains false.
The sole representation is the existing controlled stack-3 Army redraw stop,
not a generic coherent map state. The legacy SHSEL token "prior" observes
panel_stack at0x514194; previous_stack at0x511B5C is not observed here.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any

MANIFEST_SCHEMA = "clash95_paused_surface_triple_manifest_v1"
JOURNAL_SCHEMA = "clash95_paused_surface_triple_native_journal_v1"
REPRESENTATION = "complete_hd_selected_stack3_physical_e0_v1"
PHASE = "controlled_selected_stack3_redraw_stopped"
STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
         "presentbounds-minimapright-dynvswitch-completehd-validation")
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
               "1920x1080", "2560x1440", "3440x1440", "3840x2160", "802x602")
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 96 * 1024 * 1024
MAX_JSON_DEPTH = 64
STATE = {"selected_stack": (0x511B58, 3), "panel_stack": (0x514194, 3),
         "lower": (0x526994, 1), "owner": (0x5199D8, 0x40AD40)}
CORE_ROLES = ("e0_before", "header_before", "pixels", "e0_after", "header_after")
READ_ROLES = tuple("state_before_" + k for k in STATE) + CORE_ROLES + tuple("state_after_" + k for k in STATE)
DEBTS = (
    "No capture producer currently emits this versioned native journal.",
    "Candidate, recipe, producer sources and canonical probe are not reconstructed or authenticated here.",
    "Supplied native buffers and times are checked for consistency, not independently authenticated execution.",
    "Only controlled selected_stack3/panel_stack3 Army redraw stop consistency is covered; previous_stack at0x511B5C and general map-state coherence are unobserved.",
    "Complete loaded-candidate contract and all-profile/all-preset coverage remain unverified.",
    "Frame/footer, partial tiles, minimap viewport, full selected panel, modal/centered screens and healthy map return remain unverified.",
    "No final-wrapper, ordinary/manual input, endurance, live cleanup, release or promotion proof is supplied.",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def keys(value: Any, expected: tuple | set, label: str) -> dict:
    require(type(value) is dict and set(value) == set(expected), label + ": exact object fields required")
    return value


def integer(value: Any, low: int, high: int, label: str) -> int:
    require(type(value) is int and low <= value <= high, label + ": bounded integer required")
    return value


def digest(value: Any, label: str) -> str:
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, label + ": lowercase SHA-256 required")
    return value


def parse_json(data: bytes) -> dict:
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, "duplicate JSON key: " + key)
            out[key] = value
        return out

    def finite(token):
        result = float(token)
        require(math.isfinite(result), "non-finite JSON number")
        return result

    def invalid(token):
        raise ValueError("invalid JSON numeric constant: " + token)

    require(type(data) is bytes and len(data) <= MAX_FILE_BYTES, "bounded original JSON bytes required")
    try:
        result = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique,
                            parse_float=finite, parse_constant=invalid)
    except RecursionError as error:
        raise ValueError("JSON parser nesting exceeded") from error
    pending = [(iter((result,)), 0)]
    while pending:
        iterator, depth = pending[-1]
        try:
            item = next(iterator)
        except StopIteration:
            pending.pop()
            continue
        if type(item) in (dict, list):
            require(depth < MAX_JSON_DEPTH, "JSON container nesting exceeds64")
            pending.append((iter(item.values() if type(item) is dict else item), depth + 1))
    require(type(result) is dict, "JSON root object required")
    return result


def checked_path(value: Any) -> Path:
    require(type(value) is str and value and "\x00" not in value, "absolute literal artifact path required")
    path = Path(value)
    require(path.is_absolute(), "relative artifact path forbidden")
    require(".." not in path.parts, "parent traversal forbidden")
    for part in (path, *path.parents):
        info = part.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400),
                "reparse/symbolic artifact path forbidden")
    return path.resolve(strict=True)


def file_stamp(info) -> tuple:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns,
            getattr(info, "st_file_attributes", 0))


def bounded_file_read(path: Path, before, size: int) -> bytes:
    """Reject changed opened-file identity before a bounded original read."""
    with path.open("rb") as stream:
        require(file_stamp(os.fstat(stream.fileno())) == file_stamp(before),
                "opened artifact identity differs before read")
        data = stream.read(size + 1)
        require(len(data) == size and file_stamp(os.fstat(stream.fileno())) == file_stamp(before),
                "artifact size/identity changed during bounded read")
    require(file_stamp(path.lstat()) == file_stamp(before), "artifact path changed during bounded read")
    return data


class FileArtifacts:
    """Bounded original reads, unique physical files and final identity/byte check."""

    def __init__(self):
        self.loaded = {}
        self.identities = {}
        self.total = 0

    def reference(self, row: dict, role: str) -> bytes:
        keys(row, ("path", "bytes", "sha256"), role)
        size = integer(row["bytes"], 0, MAX_FILE_BYTES, role + " bytes")
        expected = digest(row["sha256"], role)
        path = checked_path(row["path"])
        require(path not in self.loaded, "artifact path reused across original roles: " + role)
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and before.st_size == size, role + ": original size/type differs")
        identity = (before.st_dev, before.st_ino)
        require(identity not in self.identities, "hardlink/physical artifact alias: " + role)
        require(self.total + size <= MAX_TOTAL_BYTES, "aggregate artifact budget exceeded")
        data = bounded_file_read(path, before, size)
        require(len(data) == size and sha(data) == expected, role + ": original hash/bytes differ")
        self.loaded[path] = (data, file_stamp(before), role)
        self.identities[identity] = path
        self.total += size
        return data

    def unchanged(self) -> None:
        for path, (data, stamp, _) in self.loaded.items():
            require(checked_path(str(path)) == path and file_stamp(path.lstat()) == stamp,
                    "artifact path/identity changed before final rehash")
            current = bounded_file_read(path, path.lstat(), len(data))
            require(current == data and file_stamp(path.lstat()) == stamp,
                    "artifact bytes/identity changed at final rehash")

    def receipts(self) -> list:
        return [dict(path=str(path), bytes=len(data), sha256=sha(data), role=role)
                for path, (data, _, role) in self.loaded.items()]


def references(value: Any, role: str):
    """Iterate a bounded parsed document; do not follow JSON reference graphs."""
    pending = [(iter(((role, value),)), 0)]
    while pending:
        iterator, depth = pending[-1]
        try:
            name, item = next(iterator)
        except StopIteration:
            pending.pop()
            continue
        if type(item) is dict:
            if "path" in item or "sha256" in item:
                yield name, item
            else:
                require(depth < MAX_JSON_DEPTH, "document container nesting exceeds64")
                pending.append((iter((name + "." + key, val) for key, val in item.items()), depth + 1))
        elif type(item) is list:
            require(depth < MAX_JSON_DEPTH, "document container nesting exceeds64")
            pending.append((iter((name + "." + str(index), val) for index, val in enumerate(item)), depth + 1))


def raw(data: dict, row: dict, count: int, label: str) -> bytes:
    keys(row, ("path", "bytes", "sha256"), label)
    require(type(row["bytes"]) is int and row["bytes"] == count, label + ": full original output required")
    result = data[row["path"]]
    require(len(result) == count and sha(result) == row["sha256"], label + ": original buffer differs")
    return result


def word(data: dict, row: dict, count: int, label: str) -> int:
    return int.from_bytes(raw(data, row, count, label), "little", signed=False)


def qpc(data: dict, value: Any, label: str) -> int:
    value = keys(value, ("return", "error", "counter"), label)
    # BOOL success is any nonzero raw DWORD; retain the original bits.
    # https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancecounter
    require(word(data, value["return"], 4, label) != 0, label + ": native QPC failed")
    word(data, value["error"], 4, label + " retained error")  # success may retain a stale last-error
    return integer(word(data, value["counter"], 8, label), 1, 0x7FFFFFFFFFFFFFFF, label)


def process(data: dict, value: Any, identity: dict, label: str) -> tuple:
    value = keys(value, ("handle", "pid_return", "pid_error", "times_return", "times_error", "filetimes", "wait_return", "wait_error", "qpc"), label)
    require(type(value["handle"]) is int and value["handle"] == identity["handle"], label + ": retained handle differs")
    require(word(data, value["pid_return"], 4, label) == identity["process_id"], label + ": native PID differs")
    word(data, value["pid_error"], 4, label + " retained PID error")
    require(word(data, value["times_return"], 4, label) != 0, label + ": native GetProcessTimes failed")
    word(data, value["times_error"], 4, label + " retained error")
    created, _undefined_live_exit, kernel, user = struct.unpack("<QQQQ", raw(data, value["filetimes"], 32, label))
    # For a live process lpExitTime is undefined. Preserve all32 raw bytes,
    # bind creation, and use the actual wait result below for lifetime state.
    # https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes
    require(created == identity["creation_filetime"], label + ": creation lifetime differs")
    require(word(data, value["wait_return"], 4, label) == 258, label + ": retained process is not alive")
    word(data, value["wait_error"], 4, label + " retained wait error")
    return qpc(data, value["qpc"], label + " timestamp"), kernel, user


def ready_line(state: dict) -> bytes:
    # Frozen SHSEL's label 'prior' reads0x514194 (panel_stack), not0x511B5C.
    return ("SHSEL_READY tid={tid:x} eip={eip:08x} esp={esp:08x} selected={selected_stack} prior={panel_stack} "
            "lower={lower} owner={owner:08x} surface={surface:08x} base={base:08x} width={width} height={height} vtable={vtable:08x}").format(**state).encode("ascii")


def new_report() -> dict:
    return dict(schema="clash95_paused_surface_triple_diagnostic_v1", passed=False,
        diagnostic_representation=REPRESENTATION, diagnostic_phase=PHASE,
        raw_artifact_contract_valid=False, input_cohort_consistent=False, candidate_authenticated=False,
        canonical_probe_verified=False, source_authenticated=False, native_provenance_verified=False,
        release_evidence_verified=False, geometry_evidence_verified=False, runtime_proof=False,
        manual_input_proof=False, ordinary_input_proof=False, visible_composition_proof=False,
        live_cleanup_verified=False, endurance_proof=False, promotion_ready=False,
        remaining_debts=list(DEBTS), failures=[], observed_reads=[], frames=[], artifacts=[])


def replay(document: dict, artifacts) -> dict:
    """Injected reader is a diagnostic/fixture boundary, never native authority."""
    report = new_report()
    data = {}

    def retain(value, label):
        for name, reference in references(value, label):
            try:
                require(reference.get("path") not in data, "one original path reused across roles: " + name)
                data[reference["path"]] = artifacts.reference(reference, name)
            except (OSError, ValueError, TypeError, KeyError) as error:
                report["failures"].append(str(error))

    try:
        keys(document, ("schema", "evidence_class", "binding", "artifacts"), "manifest")
        require(document["schema"] == MANIFEST_SCHEMA, "unsupported manifest schema; older captures are not upgraded")
        require(document["evidence_class"] in ("synthetic_fixture", "recorded_native_diagnostic"), "unknown diagnostic evidence class")
        report["evidence_class"] = document["evidence_class"]
        binding = keys(document["binding"], ("profile", "stage", "recipe", "representation", "phase", "resolution", "candidate_sha256", "original_sha256", "probe_sha256", "producer_sha256"), "binding")
        require(binding["profile"] == "Complete HD" and binding["stage"] == STAGE and binding["recipe"] == "complete_hd_v1"
                and binding["representation"] == REPRESENTATION and binding["phase"] == PHASE,
                "only the reviewed Complete controlled stack3 physical E0 representation/phase is supported; Modal/MCAP rejected")
        require(binding["resolution"] in RESOLUTIONS, "unsupported diagnostic resolution")
        width, height = map(int, binding["resolution"].split("x"))
        for name in ("candidate_sha256", "original_sha256", "probe_sha256", "producer_sha256"):
            digest(binding[name], name)
        refs = keys(document["artifacts"], ("commands", "debugger_prefix", "debugger_final", "journal"), "manifest artifacts")
        retain(refs, "manifest artifacts")
        require(not report["failures"], "original artifact retention failed")
        journal = parse_json(data[refs["journal"]["path"]])
        retain(journal, "native journal")
        require(not report["failures"], "native original retention failed; retained failures remain sticky")
        keys(journal, ("schema", "evidence_class", "host_architecture", "binding", "identity", "frequency", "pause", "cohorts", "completion"), "journal")
        require(journal["schema"] == JOURNAL_SCHEMA and journal["binding"] == binding and journal["evidence_class"] == document["evidence_class"], "journal protocol/binding differs")
        require(journal["host_architecture"] == "x64", "journal SIZE_T output ABI must be the source-owned x64 host")
        completion = keys(journal["completion"], ("status", "failures", "missing_originals"), "completion")
        require(completion == {"status": "complete", "failures": [], "missing_originals": []}, "failed/partial journal cannot become consistent")
        commands = data[refs["commands"]["path"]]
        require(sha(commands) == binding["probe_sha256"] and commands.count(b".echo SHSEL_HOST_READY") == 1, "recorded commands/hash/stop marker differ; canonical reconstruction is still absent")
        prefix, final = data[refs["debugger_prefix"]["path"]], data[refs["debugger_final"]["path"]]
        require(prefix == final, "debugger log changed across stopped triple; continuation/cleanup tails need a separate protocol")
        identity = keys(journal["identity"], ("process_id", "creation_filetime", "handle"), "identity")
        integer(identity["process_id"], 1, 0xFFFFFFFF, "process ID")
        integer(identity["creation_filetime"], 1, 0x7FFFFFFFFFFFFFFF, "creation FILETIME")
        integer(identity["handle"], 1, 0xFFFFFFFFFFFFFFFF, "retained handle")
        frequency = keys(journal["frequency"], ("return", "error", "frequency"), "QPC frequency")
        # https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancefrequency
        require(word(data, frequency["return"], 4, "frequency") != 0, "native QPC frequency failed")
        word(data, frequency["error"], 4, "frequency retained error")
        integer(word(data, frequency["frequency"], 8, "frequency"), 1, 0x7FFFFFFFFFFFFFFF, "QPC frequency")
        pause = keys(journal["pause"], ("epoch", "state", "prefix_sha256", "begin", "end"), "pause")
        require(type(pause["epoch"]) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", pause["epoch"]), "bounded pause epoch required")
        require(pause["prefix_sha256"] == sha(prefix), "pause prefix differs")
        state = keys(pause["state"], ("tid", "eip", "esp", "selected_stack", "panel_stack", "lower", "owner", "surface", "base", "width", "height", "vtable"), "paused native state")
        require(all(type(value) is int for value in state.values()), "native state requires exact integers")
        require((state["eip"], state["width"], state["height"], state["vtable"]) == (0x406FA1, width, height, 0x50EE24), "paused state PC/dimensions/vtable differ")
        integer(state["tid"], 1, 0xFFFFFFFF, "stopped native TID")
        integer(state["esp"], 0x10000, 0xFFFFFFFC, "stopped native ESP")
        require(state["esp"] % 4 == 0, "stopped native ESP alignment differs")
        integer(state["surface"], 0x10000, 0xFFFFFF44, "surface range")
        require(state["surface"] != 0x51D4C0, "fixed primary surface is not this representation")
        integer(state["base"], 0x10000, 0x100000000 - width * height, "pixel range")
        for name, (_, expected) in STATE.items():
            require(state[name] == expected, "paused selection state differs: " + name)
        lines = [line.rstrip(b"\r") for line in prefix.splitlines() if line.strip()]
        require(len(lines) >= 2 and lines[-2:] == [ready_line(state), b"SHSEL_HOST_READY"]
                and sum(b"SHSEL_READY" in line for line in lines) == 1
                and sum(b"SHSEL_HOST_READY" in line for line in lines) == 1,
                "exact ordered stopped markers/native state required")
        require(not re.search(rb"\b(?:\w*REJECT|\w*FAIL(?:URE)?|MCAP_\w*|MODAL_\w*)\b", prefix), "debugger rejected or incompatible marker retained")
        start, finish = qpc(data, pause["begin"], "pause begin"), qpc(data, pause["end"], "pause end")
        require(start <= finish, "pause clock reversed")
        require(type(journal["cohorts"]) is list and len(journal["cohorts"]) == 3, "exactly3 independent cohorts required")
        previous, previous_cpu = start, (0, 0)
        header_pair, frames = None, []
        ordinal = 0
        for index, cohort in enumerate(journal["cohorts"], 1):
            keys(cohort, ("index", "pause_epoch", "reads"), "cohort")
            require(type(cohort["index"]) is int and cohort["index"] == index and cohort["pause_epoch"] == pause["epoch"], "cohort index/pause ownership differs")
            require(type(cohort["reads"]) is list and len(cohort["reads"]) == len(READ_ROLES), "full state/core read cohort required")
            observed = {}
            for role, read in zip(READ_ROLES, cohort["reads"]):
                ordinal += 1
                keys(read, ("ordinal", "role", "api", "handle", "address", "requested", "identity_before", "qpc_begin", "native_return", "native_error", "returned_count", "buffer", "qpc_end", "identity_after"), "read")
                require(type(read["ordinal"]) is int and read["ordinal"] == ordinal and read["role"] == role and read["api"] == "ReadProcessMemory", "read order/API/ordinal differs")
                require(type(read["handle"]) is int and read["handle"] == identity["handle"], "read retained handle differs")
                if role.startswith("state_"):
                    field = role.split("_", 2)[2]
                    address, count = STATE[field][0], 4
                elif role.startswith("e0_"):
                    address, count = 0x5202E0, 4
                elif role.startswith("header_"):
                    address, count = state["surface"], 188
                else:
                    address, count = state["base"], width * height
                require(type(read["address"]) is int and read["address"] == address and type(read["requested"]) is int and read["requested"] == count, "read address/requested range differs")
                before, kernel, user = process(data, read["identity_before"], identity, "before " + role)
                began, ended = qpc(data, read["qpc_begin"], "read begin"), qpc(data, read["qpc_end"], "read end")
                after, next_kernel, next_user = process(data, read["identity_after"], identity, "after " + role)
                require(previous <= before <= began <= ended <= after <= finish, "per-read native QPC order/bounds differ")
                require(previous_cpu[0] <= kernel <= next_kernel and previous_cpu[1] <= user <= next_user, "process CPU times reversed")
                # https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory
                require(word(data, read["native_return"], 4, role) != 0, "native ReadProcessMemory failed: " + role)
                word(data, read["native_error"], 4, role + " retained error")
                require(word(data, read["returned_count"], 8, role) == count, "native ReadProcessMemory short/extra count: " + role)
                buffer = raw(data, read["buffer"], count, role)
                observed[role] = buffer
                previous, previous_cpu = after, (next_kernel, next_user)
                report["observed_reads"].append(dict(ordinal=ordinal, cohort=index, role=role, qpc_begin=began, qpc_end=ended, bytes=count, sha256=sha(buffer)))
            for name, (_, expected) in STATE.items():
                require(observed["state_before_" + name] == observed["state_after_" + name] == struct.pack("<I", expected), "native selection state changed: " + name)
            e0, header = observed["e0_before"], observed["header_before"]
            require(e0 == observed["e0_after"] and header == observed["header_after"], "E0/full188-byte header changed within cohort")
            require(struct.unpack("<I", e0)[0] == state["surface"] and struct.unpack_from("<HHI", header) == (width, height, state["base"])
                    and struct.unpack_from("<I", header, 184)[0] == 0x50EE24, "raw native E0/header differs from stopped state")
            require(header_pair is None or header_pair == (e0, header), "E0/full188-byte header changed across cohorts")
            header_pair = e0, header
            frames.append(observed["pixels"])
            report["frames"].append(dict(index=index, bytes=len(frames[-1]), sha256=sha(frames[-1])))
        require(all(frame == frames[0] for frame in frames), "three full raw frames differ")
        artifacts.unchanged()
        report.update(raw_artifact_contract_valid=True, input_cohort_consistent=True)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, struct.error, RecursionError, OverflowError) as error:
        report["failures"].append(str(error))
        # Even failures retain already loaded originals; never report a pass.
        try:
            artifacts.unchanged()
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, struct.error, RecursionError, OverflowError) as drift:
            report["failures"].append(str(drift))
    report["artifacts"] = artifacts.receipts()
    if report["failures"]:
        report["remaining_debts"].append("Failed/partial input cohort; see retained originals and failures.")
    return report


def replay_manifest(path: str | Path) -> dict:
    """Read-only file entrypoint. No module, API or parser is selected by reports."""
    artifacts = FileArtifacts()
    try:
        resolved = checked_path(str(path))
        before = resolved.lstat()
        size = before.st_size
        require(stat.S_ISREG(before.st_mode) and size <= MAX_FILE_BYTES, "manifest exceeds original JSON type/budget")
        original = bounded_file_read(resolved, before, size)
        reference = dict(path=str(resolved), bytes=size, sha256=sha(original))
        document = parse_json(artifacts.reference(reference, "manifest"))
        return replay(document, artifacts)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as error:
        report = new_report()
        report["failures"].append(str(error))
        report["remaining_debts"].append("Manifest unavailable/invalid; no complete input cohort was evaluated.")
        report["artifacts"] = artifacts.receipts()
        return report

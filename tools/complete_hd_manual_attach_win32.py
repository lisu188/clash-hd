"""Lazy, read-only Win32 boundary for an approved existing-process observer.

Importing this module calls no Windows API. The session never launches,
terminates, focuses, moves, suspends, or writes to another process.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def image_contract(data: bytes, load_base: int, probe: str | None = None) -> dict:
    """Prepare exact headers and immutable executable bytes for a PE32 image.

Writable runtime state and loader-resolved import tables are deliberately not
compared to their prelaunch contents. No whole-loaded-image SHA is claimed.
"""
    if len(data) < 256 or len(data) > 64 * 1024 * 1024 or data[:2] != b"MZ":
        raise ValueError("bounded PE image required")
    pe = struct.unpack_from("<I", data, 60)[0]
    if pe + 248 > len(data) or data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("invalid PE header")
    machine, count = struct.unpack_from("<HH", data, pe + 4)
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    if machine != 0x14c or not 1 <= count <= 32 or optional_size < 224 or struct.unpack_from("<H", data, opt)[0] != 0x10b:
        raise ValueError("bounded x86 PE32 required")
    preferred = struct.unpack_from("<I", data, opt + 28)[0]
    image_size, headers_size = struct.unpack_from("<II", data, opt + 56)
    table = opt + optional_size
    if (table + count * 40 > headers_size or not 1 <= headers_size <= min(len(data), 65536)
            or not headers_size < image_size <= 64 * 1024 * 1024
            or type(load_base) is not int or load_base < 65536 or load_base + image_size > 0x100000000):
        raise ValueError("invalid PE allocation")
    sections = []
    memory = bytearray(image_size)
    memory[:headers_size] = data[:headers_size]
    occupied = [(0, headers_size)]
    for index in range(count):
        at = table + index * 40
        virtual, rva, raw_size, raw = struct.unpack_from("<IIII", data, at + 8)
        flags = struct.unpack_from("<I", data, at + 36)[0]
        size = max(virtual, raw_size)
        if (not size or rva + size > image_size or rva < headers_size
                or any(rva < end and start < rva + size for start, end in occupied)
                or (raw and (raw < headers_size or raw + raw_size > len(data)))):
            raise ValueError("invalid or overlapping PE sections")
        if raw:
            memory[rva:rva + raw_size] = data[raw:raw + raw_size]
        occupied.append((rva, rva + size))
        sections.append({"name": data[at:at + 8].rstrip(b"\0").decode("ascii"),
                         "rva": rva, "size": size, "flags": flags})
    preferred_memory = bytes(memory)
    delta = load_base - preferred
    relocation_rva, relocation_size = struct.unpack_from("<II", data, opt + 96 + 5 * 8)
    if relocation_size and (not relocation_rva or relocation_rva + relocation_size > image_size):
        raise ValueError("invalid relocation directory")
    if delta and not relocation_size:
        raise ValueError("relocated image lacks relocation directory")
    pos, end, fields = relocation_rva, relocation_rva + relocation_size, set()
    while pos < end:
        if pos + 8 > end:
            raise ValueError("truncated relocation block")
        page, size = struct.unpack_from("<II", memory, pos)
        if size < 8 or size % 2 or pos + size > end:
            raise ValueError("invalid relocation block")
        for offset in range(pos + 8, pos + size, 2):
            item = struct.unpack_from("<H", memory, offset)[0]
            kind, target = item >> 12, page + (item & 4095)
            if kind == 0:
                continue
            if kind != 3 or target < headers_size or target + 4 > image_size or target in fields:
                raise ValueError("unsupported or repeated PE relocation")
            fields.add(target)
            struct.pack_into("<I", memory, target, (struct.unpack_from("<I", memory, target)[0] + delta) & 0xffffffff)
        pos += size
    ranges = [{"name": "headers", "rva": 0, "size": headers_size}]
    ranges += [{"name": row["name"], "rva": row["rva"], "size": row["size"]}
               for row in sections if row["flags"] & 0x20000000 and not row["flags"] & 0x80000000]
    if len(ranges) == 1 or any(row["flags"] & 0x20000000 and row["flags"] & 0x80000000 for row in sections):
        raise ValueError("image requires immutable executable sections")
    guards = {"immutable_checked": 0, "runtime_state_excluded": 0}
    if probe is not None:
        reads = re.findall(r"\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)", probe)
        if not reads:
            raise ValueError("canonical probe lacks known exact-byte guards")
        for kind, address, value in reads:
            rva, size = int(address, 16) - preferred, 2 if kind == "wo" else 1
            if rva < 0 or rva + size > image_size:
                raise ValueError("canonical guard outside candidate image")
            # Probe literals use the preferred base. Compare them before any
            # rebasing; runtime reads use the relocated section byte contract.
            expected = preferred_memory[rva:rva + size]
            if int.from_bytes(expected, "little") != int(value, 16):
                raise ValueError("canonical probe guard disagrees with candidate")
            if any(row["rva"] <= rva and rva + size <= row["rva"] + row["size"] for row in ranges):
                guards["immutable_checked"] += 1
            elif any(row["rva"] <= rva and rva + size <= row["rva"] + row["size"] and row["flags"] & 0x80000000 for row in sections):
                guards["runtime_state_excluded"] += 1
            else:
                # Canonical read-only data guards are safe to add individually;
                # avoid whole loader-modified read-only data sections.
                ranges.append({"name": "canonical_readonly_guard", "rva": rva, "size": size})
                guards["immutable_checked"] += 1
    return {"memory": memory, "ranges": ranges, "image_size": image_size,
            "preferred_base": preferred, "load_base": load_base, "guards": guards}


def verify_image(contract: dict, read) -> dict:
    records = []
    for row in contract["ranges"]:
        expected = bytes(contract["memory"][row["rva"]:row["rva"] + row["size"]])
        actual = read(contract["load_base"] + row["rva"], row["size"])
        if actual != expected:
            raise ValueError(f"loaded immutable bytes differ: {row['name']} RVA {row['rva']:#x}")
        records.append({**row, "sha256": sha(actual)})
    return {"load_base": contract["load_base"], "image_size": contract["image_size"],
            "ranges": records, "canonical_guards": contract["guards"],
            "scope": "exact headers, immutable executable sections and read-only canonical guards; mutable runtime state excluded"}


class WindowsAttachment:
    """Only instantiated after the external approval record has been verified."""

    def __init__(self, plan: dict):
        import ctypes as c
        from ctypes import wintypes as w
        from hd_layout_observation_manifest import WindowsSession
        self.c, self.w = c, w
        self.session = WindowsSession()
        self.kernel = self.session.kernel
        self.session.user.IsWindow.argtypes = [w.HWND]
        self.session.user.IsWindow.restype = w.BOOL
        self.kernel.ReadProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
        self.kernel.ReadProcessMemory.restype = w.BOOL
        self.kernel.GetProcessId.argtypes = [w.HANDLE]
        self.kernel.GetProcessId.restype = w.DWORD
        self.plan, self.handle, self.pulse = plan, None, None
        self.handle = self.kernel.OpenProcess(0x1000 | 0x100000 | 0x10, False, plan["attachment"]["pid"])
        if not self.handle:
            raise OSError("cannot open the exact existing candidate for query/read")
        try:
            # This import initializes capture coordinates but performs no capture
            # or input. WindowsSession already required per-monitor awareness.
            import menu_pulse_click
            self.pulse = menu_pulse_click
            self.session.enable_native_capture_coordinates()
        except BaseException:
            self.close()
            raise

    def identity(self) -> dict:
        c, w = self.c, self.w
        if self.kernel.WaitForSingleObject(self.handle, 0) != 0x102:
            raise ValueError("retained candidate process has exited")
        buffer, size = c.create_unicode_buffer(32768), w.DWORD(32768)
        times = [w.FILETIME() for _ in range(4)]
        if (not self.kernel.QueryFullProcessImageNameW(self.handle, 0, buffer, c.byref(size))
                or not self.kernel.GetProcessTimes(self.handle, *(c.byref(t) for t in times))):
            raise OSError("cannot remeasure retained process identity")
        return {"pid": int(self.kernel.GetProcessId(self.handle)), "path": str(Path(buffer.value).resolve()),
                "creation_filetime": (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime}

    def modules(self) -> list[dict]:
        c, w = self.c, self.w
        class Entry(c.Structure):
            _fields_ = [("dwSize", w.DWORD), ("th32ModuleID", w.DWORD), ("th32ProcessID", w.DWORD),
                        ("GlblcntUsage", w.DWORD), ("ProccntUsage", w.DWORD), ("modBaseAddr", c.c_void_p),
                        ("modBaseSize", w.DWORD), ("hModule", w.HMODULE), ("szModule", w.WCHAR * 256),
                        ("szExePath", w.WCHAR * 260)]
        self.kernel.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
        self.kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
        self.kernel.Module32FirstW.argtypes = [w.HANDLE, c.POINTER(Entry)]
        self.kernel.Module32NextW.argtypes = [w.HANDLE, c.POINTER(Entry)]
        snapshot = self.kernel.CreateToolhelp32Snapshot(0x8 | 0x10, self.plan["attachment"]["pid"])
        if snapshot == c.c_void_p(-1).value:
            raise OSError("cannot enumerate the exact candidate's loaded modules")
        rows = []
        try:
            entry = Entry(); entry.dwSize = c.sizeof(entry)
            valid = self.kernel.Module32FirstW(snapshot, c.byref(entry))
            while valid:
                rows.append({"path": str(Path(entry.szExePath).resolve()), "base": int(entry.modBaseAddr), "size": int(entry.modBaseSize)})
                if len(rows) > 256:
                    raise ValueError("unexpected module inventory size")
                valid = self.kernel.Module32NextW(snapshot, c.byref(entry))
            if self.c.get_last_error() != 18:
                raise OSError("incomplete loaded module inventory")
        finally:
            self.kernel.CloseHandle(snapshot)
        return rows

    def read(self, address: int, size: int) -> bytes:
        c = self.c
        buffer, read = c.create_string_buffer(size), c.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle, address, buffer, size, c.byref(read)) or read.value != size:
            raise OSError("cannot read the complete immutable loaded image range")
        return buffer.raw

    def placement(self, points: list[list[int]]) -> dict:
        attachment = self.plan["attachment"]
        hwnd, pid = attachment["hwnd"], attachment["pid"]
        # live_hwnd performs one fallback search even with attempts=0. This
        # attachment must check only the approved handle, with no reacquisition.
        owner = self.w.DWORD()
        if (not self.session.user.IsWindow(hwnd)
                or not self.session.user.GetWindowThreadProcessId(hwnd, self.c.byref(owner))
                or owner.value != pid or not self.session.user.IsWindowVisible(hwnd)):
            raise ValueError("approved HWND is stale or belongs to a different process")
        dimensions = tuple(self.plan["client_size"])
        if self.session.window(pid, dimensions) != hwnd:
            raise ValueError("approved HWND is absent, resized or ambiguous")
        self.session.process_dpi_awareness({"handle": self.handle})
        awareness = self.session.window_dpi_awareness(hwnd)
        return {"hwnd": hwnd, "client": list(self.pulse.client_geometry(hwnd)), "dpi_awareness": awareness,
                "targets": [self.pulse.target_accessibility(hwnd, tuple(point), dimensions) for point in points]}

    def capture(self, *, before_attempt):
        # Reuse the original-client ROI and ImageGrab backend, with a single
        # attempt. The historical grab_image retry loop cannot enforce this
        # attachment's deadline between retries, so it is not called here.
        x, y, width, height = self.pulse.client_geometry(self.plan["attachment"]["hwnd"])
        if [x, y, width, height] != [*self.plan["attachment"]["client_origin"], *self.plan["client_size"]]:
            raise ValueError("approved client changed at the native capture boundary")
        before_attempt()
        return self.pulse.ImageGrab.grab(bbox=(x, y, x + width, y + height), all_screens=True).convert("RGB")

    def close(self) -> bool:
        if self.handle:
            if not self.kernel.CloseHandle(self.handle):
                raise OSError("cannot close retained observation handle")
            self.handle = None
        return True

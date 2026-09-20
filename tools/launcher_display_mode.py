"""Temporarily use an enumerated Windows display mode on an isolated test runner."""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
import os
import struct


def mode_values(data):
    if type(data) is not bytes or len(data) != 220:
        raise ValueError('Exact DEVMODEW byte extent required')
    size, extra = struct.unpack_from('<HH', data, 68)
    if size != 220 or extra != 0:
        raise ValueError('Unsupported DEVMODEW size or private driver data')
    depth, width, height, flags, frequency = struct.unpack_from('<5I', data, 168)
    orientation = struct.unpack_from('<I', data, 84)[0]
    return dict(width=width, height=height, depth=depth, frequency=frequency, flags=flags, orientation=orientation)


def select_mode(modes, width, height):
    if type(width) is not int or type(height) is not int or not 800 <= width <= 3840 or not 600 <= height <= 2160:
        raise ValueError('Bounded requested physical resolution required')
    suitable = []
    for index, row in enumerate(modes):
        if not isinstance(row, dict) or any(type(row.get(key)) is not int for key in
            ('width', 'height', 'depth', 'frequency', 'orientation', 'flags')):
            raise ValueError('Malformed enumerated display mode')
        if (width <= row['width'] <= 8192 and height <= row['height'] <= 4320
                and row['depth'] == 32 and row['orientation'] == 0):
            suitable.append((row['width']*row['height'], abs(row['frequency']-60), index))
    return min(suitable)[2] if suitable else None


class NativeModes:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('Native Windows display enumeration required')
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.user.SetProcessDPIAware()
        self.user.EnumDisplaySettingsW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_void_p]
        self.user.EnumDisplaySettingsW.restype = ctypes.c_int
        self.user.ChangeDisplaySettingsExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
        self.user.ChangeDisplaySettingsExW.restype = ctypes.c_long

    def read(self, index):
        buffer = ctypes.create_string_buffer(220)
        struct.pack_into('<H', buffer, 68, 220)
        if not self.user.EnumDisplaySettingsW(None, index & 0xFFFFFFFF, buffer):
            return None
        data = buffer.raw
        mode_values(data)
        return data

    def apply(self, data, flags):
        mode_values(data)
        if flags not in (0, 2):
            raise ValueError('Only test or temporary no-registry display changes are allowed')
        buffer = ctypes.create_string_buffer(data, len(data))
        return self.user.ChangeDisplaySettingsExW(None, buffer, None, flags, None)


@contextmanager
def temporary_display(width, height, *, api=None):
    select_mode([], width, height)
    api = NativeModes() if api is None else api
    before = api.read(-1)
    if before is None:
        raise OSError('Current display mode unavailable')
    values = mode_values(before)
    report = dict(requested=[width, height], before=values, changed=False, adequate=False,
                  restored=False, registry_modified=False, modes=[])
    selected = None
    try:
        if values['width'] >= width and values['height'] >= height and values['depth'] == 32:
            report['adequate'] = True
        else:
            buffers = []
            for index in range(4096):
                data = api.read(index)
                if data is None:
                    break
                buffers.append(data)
                report['modes'].append(mode_values(data))
            else:
                raise ValueError('Display enumeration exceeds bounded inventory')
            index = select_mode(report['modes'], width, height)
            if index is not None:
                selected = buffers[index]
                report['selected'] = report['modes'][index]
                report['test_result'] = api.apply(selected, 2)
                if report['test_result'] == 0:
                    report['apply_result'] = api.apply(selected, 0)
                    report['changed'] = report['apply_result'] == 0
                    after = api.read(-1)
                    report['after'] = mode_values(after) if after is not None else None
                    report['adequate'] = report['changed'] and report['after'] is not None and all(
                        report['after'][key] == report['selected'][key] for key in ('width', 'height', 'depth', 'orientation'))
            else:
                report['limitation'] = 'No enumerated 32-bit display mode contains the requested surface'
        yield report
    finally:
        if report['changed']:
            report['restore_result'] = api.apply(before, 0)
            current = api.read(-1)
            report['restored'] = report['restore_result'] == 0 and current is not None and all(
                mode_values(current)[key] == values[key] for key in ('width', 'height', 'depth', 'orientation', 'frequency'))
            if not report['restored']:
                raise OSError('Failed to restore the exact previous display mode')
        else:
            report['restored'] = api.read(-1) == before
            if not report['restored']:
                raise OSError('Display state changed unexpectedly during the observation')

"""Fail-closed PE section construction for the battle HD validation stage.

The original executable has an unused, zero-filled eighth section-header slot.
Append code at EOF rather than consuming or extending existing game data caves.
"""

from collections import Counter
import struct


SOURCE_SIZE = 0x12CE00
SECTION_VA = 0x562000
SECTION_RVA = SECTION_VA - 0x400000
SECTION_SIZE = 0x10000
CORE_CAPACITY = 0x4000
HUD_RELATIVE_OFFSET = 0x4000
HUD_CAPACITY = 0x8000
SECTION_GROUP = "battle-hd-section"


def section_records(core_code: bytes, hud_code: bytes) -> tuple[tuple, ...]:
    if not core_code or len(core_code) > CORE_CAPACITY:
        raise ValueError("battle HD core code is empty or exceeds its reserved section slice")
    if not hud_code or len(hud_code) > HUD_CAPACITY:
        raise ValueError("battle HD HUD code is empty or exceeds its reserved section slice")
    payload = bytearray(SECTION_SIZE)
    payload[:len(core_code)] = core_code
    payload[HUD_RELATIVE_OFFSET:HUD_RELATIVE_OFFSET + len(hud_code)] = hud_code
    header = struct.pack(
        "<8sIIIIIIHHI", b".btlhd\0\0", SECTION_SIZE, SECTION_RVA,
        SECTION_SIZE, SOURCE_SIZE, 0, 0, 0, 0, 0xE0000020,
    )
    return (
        (SECTION_GROUP, 0x76, "0700", "0800", "PE NumberOfSections 7 -> 8; reserved zero eighth header"),
        (SECTION_GROUP, 0x8C, "008a0e00", "008a0f00", "PE SizeOfCode includes the new 0x10000-byte .btlhd section"),
        (SECTION_GROUP, 0xC0, "00201600", "00201700", "PE SizeOfImage 0x162000 -> 0x172000 for .btlhd RVA 0x162000"),
        (SECTION_GROUP, 0x280, "00" * 40, header.hex(), "PE eighth section .btlhd: VA 0x562000, RVA 0x162000, EOF raw 0x12CE00, size 0x10000, code/read/write"),
        (SECTION_GROUP, SOURCE_SIZE, "", bytes(payload).hex(), "Append .btlhd at verified original EOF; core VA 0x562000 and HUD VA 0x566000; empty old bytes mean EOF, never an unchecked cave"),
    )


def validate_spans(patches) -> None:
    """Reject conflicts and malformed writes before any output mutation."""
    spans = []
    for patch in patches:
        old, new = patch.old, patch.new
        append = patch.group == SECTION_GROUP and patch.offset == SOURCE_SIZE
        if append:
            if old or len(new) != SECTION_SIZE:
                raise ValueError("battle HD section append must be exactly 64 KiB at original EOF")
        elif not old or len(old) != len(new):
            raise ValueError(f"unequal or empty guarded patch at 0x{patch.offset:X}")
        if patch.offset < 0 or (not append and patch.offset + len(new) > SOURCE_SIZE):
            raise ValueError(f"patch outside original file at 0x{patch.offset:X}")
        spans.append((patch.offset, patch.offset + len(new), patch.group))
    spans.sort()
    for left, right in zip(spans, spans[1:]):
        if left[1] > right[0]:
            raise ValueError(f"overlapping battle HD patches: {left} and {right}")


def validate_installation(patches, required_records) -> None:
    """Require the complete audited stage before installing any battle HD hook.

    A valid append by itself is insufficient: its headers and all inherited HD
    display/surface/input prerequisites must match too. The caller supplies the
    canonical full stage, keeping this module independent of the root patcher.
    Notes are descriptive metadata and do not affect patch identity.
    """
    patches = tuple(patches)
    required_records = tuple(required_records)
    validate_spans(patches)
    validate_spans(required_records)
    identity = lambda patch: (patch.group, patch.offset, patch.old, patch.new)
    actual = Counter(map(identity, patches))
    expected = Counter(map(identity, required_records))
    if actual != expected:
        missing = sum((expected - actual).values())
        unexpected = sum((actual - expected).values())
        raise ValueError(
            "battle HD installation requires the complete audited 1280x720 stage "
            f"including inherited display/surface patches: {missing} missing and "
            f"{unexpected} unexpected patch record(s)"
        )

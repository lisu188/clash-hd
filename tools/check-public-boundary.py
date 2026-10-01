from pathlib import Path
import subprocess
import sys

blocked_prefixes = ("captures/", "cloud/fixtures/", "runtime/", "retail/", "reference/")
blocked_suffixes = (
    ".exe", ".dll", ".res", ".avi", ".wav", ".mp3", ".ogg", ".flac",
    ".iso", ".img", ".dat", ".fac", ".sav", ".sg", ".dmp", ".dump",
    ".idb", ".i64", ".id0", ".id1", ".nam", ".til", ".gpr", ".rep",
    ".png", ".bmp", ".pcx", ".gif", ".jpg", ".jpeg"
)
blocked_path_markers = ("ghidra-out/", "selected_decompilation")
blocked_text_markers = (
    "repository: lisu188/clash-assets",
    "git lfs pull --include='runtime/gog-32003",
)

tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
violations = []

for raw in tracked:
    if not raw:
        continue
    path = raw.replace("\\", "/")
    lower = path.lower()
    if path.startswith(blocked_prefixes):
        violations.append(f"blocked evidence/runtime path: {path}")
        continue
    if lower.endswith(blocked_suffixes):
        violations.append(f"blocked proprietary/rendered payload: {path}")
        continue
    if any(marker in lower for marker in blocked_path_markers):
        violations.append(f"blocked reverse-engineering export path: {path}")
        continue
    if path == "tools/check-public-boundary.py":
        continue
    file = Path(raw)
    if not file.is_file() or file.stat().st_size > 2_000_000:
        continue
    try:
        text = file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for marker in blocked_text_markers:
        if marker in text:
            violations.append(f"blocked public runtime dependency {marker!r}: {path}")

if violations:
    print("\n".join(violations), file=sys.stderr)
    sys.exit(1)

print("PUBLIC_BOUNDARY_OK")

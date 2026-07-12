#!/usr/bin/env python3
"""Per-user launcher settings and single-instance lock.

State lives under ``%LOCALAPPDATA%\\ClashHD`` (never inside the repository or
``C:\\ClashTests``, which is disposable test space). Corrupt or missing
settings silently reset to defaults. Repo-only file handling; starts no
process and opens no window.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable


SETTINGS_SCHEMA = 1
DEFAULT_SETTINGS: dict[str, Any] = {
    "schema": SETTINGS_SCHEMA,
    "last_resolution": "800x600",
    "scaling_mode": "integer",
    "clash_dir": "C:\\Clash",
    "candidates_root": "C:\\ClashTests\\launcher",
    "window_geometry": "",
}


def settings_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    return Path(base) / "ClashHD"


def settings_path() -> Path:
    return settings_dir() / "settings.json"


def lock_path() -> Path:
    return settings_dir() / "launcher.lock"


def load_settings(path: Path | None = None) -> dict[str, Any]:
    path = path if path is not None else settings_path()
    data = dict(DEFAULT_SETTINGS)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return data
    if not isinstance(raw, dict) or raw.get("schema") != SETTINGS_SCHEMA:
        return data
    for key in DEFAULT_SETTINGS:
        if key in raw and isinstance(raw[key], type(DEFAULT_SETTINGS[key])):
            data[key] = raw[key]
    return data


def save_settings(data: dict[str, Any], path: Path | None = None) -> None:
    path = path if path is not None else settings_path()
    payload = dict(DEFAULT_SETTINGS)
    payload.update({key: data[key] for key in DEFAULT_SETTINGS if key in data})
    payload["schema"] = SETTINGS_SCHEMA
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def acquire_lock(
    path: Path | None = None,
    pid: int | None = None,
    pid_alive: Callable[[int], bool] | None = None,
) -> bool:
    """Create the single-instance lock; True on success.

    A stale lock (the recorded PID is no longer alive per ``pid_alive``) is
    replaced. Without a ``pid_alive`` callback an existing lock is respected.
    """
    path = path if path is not None else lock_path()
    pid = pid if pid is not None else os.getpid()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        stale = False
        if pid_alive is not None:
            try:
                old_pid = int(path.read_text(encoding="utf-8").strip() or "0")
            except (OSError, ValueError):
                old_pid = 0
            stale = old_pid <= 0 or not pid_alive(old_pid)
        if not stale:
            return False
        try:
            path.unlink()
            handle = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            return False
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(f"{pid}\n")
    return True


def release_lock(path: Path | None = None, pid: int | None = None) -> None:
    path = path if path is not None else lock_path()
    pid = pid if pid is not None else os.getpid()
    try:
        recorded = int(path.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return
    if recorded == pid:
        try:
            path.unlink()
        except OSError:
            pass

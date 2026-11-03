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
PROFILES = ("classic", "framed", "completehd", "modalwidgets")
DEFAULT_SETTINGS: dict[str, Any] = {
    "schema": SETTINGS_SCHEMA,
    "last_profile": "classic",
    "last_resolution": "800x600",
    "profile_resolutions": {profile: "800x600" for profile in PROFILES},
    "scaling_mode": "integer",
    "clash_dir": "C:\\Clash",
    "candidates_root": "C:\\ClashTests\\launcher",
    "window_geometry": "",
}


def defaults() -> dict[str, Any]:
    return {**DEFAULT_SETTINGS, "profile_resolutions": dict(DEFAULT_SETTINGS["profile_resolutions"])}


def resolution_for_profile(data: dict[str, Any], profile: str) -> str:
    if profile not in PROFILES:
        raise ValueError("Unknown launcher profile.")
    # The historical Classic field remains authoritative for existing settings.
    if profile == "classic":
        return data.get("last_resolution", "800x600")
    return data.get("profile_resolutions", {}).get(profile, "800x600")


def remember_selection(data: dict[str, Any], profile: str, resolution: str) -> None:
    if profile not in PROFILES or type(resolution) is not str or not resolution:
        raise ValueError("A known profile and resolution are required.")
    data["last_profile"] = profile
    data["profile_resolutions"] = {**DEFAULT_SETTINGS["profile_resolutions"],
                                   **data.get("profile_resolutions", {}), profile: resolution}
    if profile == "classic":
        data["last_resolution"] = resolution


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
    data = defaults()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return data
    if not isinstance(raw, dict) or raw.get("schema") != SETTINGS_SCHEMA:
        return data
    for key in DEFAULT_SETTINGS:
        if key != "profile_resolutions" and key in raw and type(raw[key]) is type(DEFAULT_SETTINGS[key]):
            data[key] = raw[key]
    if data["last_profile"] not in PROFILES:
        data["last_profile"] = "classic"
    stored = raw.get("profile_resolutions")
    if type(stored) is dict:
        data["profile_resolutions"].update({profile: stored[profile] for profile in PROFILES
            if type(stored.get(profile)) is str and stored[profile]})
    data["profile_resolutions"]["classic"] = data["last_resolution"]
    return data


def save_settings(data: dict[str, Any], path: Path | None = None) -> None:
    path = path if path is not None else settings_path()
    payload = defaults()
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

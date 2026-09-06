#!/usr/bin/env python3
"""Tkinter GUI for the Clash95 HD launcher.

All widget code lives here; the patch/deploy/launch logic is in ``core``.
The game starts only from the Play button handler, which is the explicit
user action that passes ``confirmed=True`` to ``core.launch_game``.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import core
import framed
import ini as ini_mod
import presets
import settings as settings_mod


STATUS_BADGES = {
    "stable": ("Stable", "#1a7f37"),
    "validated": ("Validated", "#0969da"),
    "experimental": ("Experimental", "#9a6700"),
}
EXPERIMENTAL_WARNING = (
    "Experimental resolutions may crash or render incorrectly. The candidate "
    "is isolated under C:\\ClashTests\\launcher and your original game files "
    "are untouched. Continue?"
)
WRAPPER_HELP = (
    "No DirectDraw wrapper (ddraw.dll) was found in the game directory.\n\n"
    "The launcher never ships or downloads DLLs. Install your preferred "
    "DirectDraw wrapper (for example dgVoodoo2 or a dxcfg-based wrapper) "
    "into C:\\Clash so the launcher can copy it next to the patched "
    "candidate, then press Refresh."
)


class LauncherApp:
    def __init__(self, root: tk.Tk, initial_profile: str = "classic") -> None:
        if initial_profile not in ("classic", "framed"):
            raise core.LauncherError("Unknown launcher profile.")
        if initial_profile == "framed" and getattr(sys, "frozen", False):
            raise core.LauncherError("The framed profile requires the source-tree launcher.")
        self.root = root
        self.settings = settings_mod.load_settings()
        self.manifest = presets.load_manifest()
        self.options = presets.load_options(self.manifest)
        self.environment: core.EnvironmentReport | None = None
        self.experimental_warned = False

        root.title("Clash95 HD Launcher")
        root.minsize(560, 660)
        if self.settings.get("window_geometry"):
            try:
                root.geometry(self.settings["window_geometry"])
            except tk.TclError:
                pass

        saved_resolution = self.settings.get(
            "last_resolution", presets.default_key(self.manifest)
        )
        if saved_resolution not in {option.key for option in self.options}:
            saved_resolution = presets.default_key(self.manifest)
        self.profile_var = tk.StringVar(value=initial_profile)
        self.resolution_var = tk.StringVar(value=saved_resolution)
        self._build_widgets()
        self.on_profile_change()
        self.refresh_environment()

    # -- layout -----------------------------------------------------------

    def _build_widgets(self) -> None:
        pad = {"padx": 8, "pady": 4}

        env_frame = ttk.LabelFrame(self.root, text="Environment")
        env_frame.pack(fill="x", **pad)
        self.env_labels: dict[str, ttk.Label] = {}
        for key, title in (
            ("base_exe", "Game executable"),
            ("wrapper_dll", "DirectDraw wrapper"),
            ("candidates_root", "Candidates folder"),
            ("running_processes", "Running game processes"),
        ):
            row = ttk.Frame(env_frame)
            row.pack(fill="x")
            ttk.Label(row, text=f"{title}:", width=24).pack(side="left")
            label = ttk.Label(row, text="…")
            label.pack(side="left")
            self.env_labels[key] = label
        ttk.Button(env_frame, text="Refresh", command=self.refresh_environment).pack(
            anchor="e", padx=4, pady=2
        )

        profile_frame = ttk.LabelFrame(self.root, text="Renderer profile")
        profile_frame.pack(fill="x", **pad)
        ttk.Radiobutton(profile_frame, text="Classic (existing profiles)", value="classic",
                        variable=self.profile_var, command=self.on_profile_change).pack(anchor="w", padx=6)
        ttk.Radiobutton(profile_frame, text="Framed + minimap correction [Experimental]", value="framed",
                        variable=self.profile_var, command=self.on_profile_change,
                        state="disabled" if getattr(sys, "frozen", False) else "normal").pack(anchor="w", padx=6)
        self.profile_label = ttk.Label(profile_frame, wraplength=520)
        self.profile_label.pack(fill="x", padx=6, pady=4)
        self.resolution_buttons = []

        res_frame = ttk.LabelFrame(self.root, text="Game resolution")
        res_frame.pack(fill="x", **pad)
        default = presets.default_key(self.manifest)
        supports_multi = presets.patcher_supports_resolutions(core.patch_clash95_hd)
        for option in self.options:
            badge, colour = STATUS_BADGES[option.status]
            text = f"{option.key}  [{badge}]"
            state = "normal"
            if option.key != default and not supports_multi:
                text += "  (awaiting patcher support)"
                state = "disabled"
            button = ttk.Radiobutton(
                res_frame,
                text=text,
                value=option.key,
                variable=self.resolution_var,
                state=state,
            )
            button.pack(anchor="w", padx=6)
            self.resolution_buttons.append((button, option))

        custom_row = ttk.Frame(res_frame)
        custom_row.pack(anchor="w", padx=6, pady=2)
        custom_state = "normal" if supports_multi else "disabled"
        ttk.Radiobutton(
            custom_row,
            text="Custom:",
            value="custom",
            variable=self.resolution_var,
            state=custom_state,
        ).pack(side="left")
        self.custom_width_var = tk.StringVar(value="")
        self.custom_height_var = tk.StringVar(value="")
        ttk.Entry(
            custom_row, textvariable=self.custom_width_var, width=6, state=custom_state
        ).pack(side="left", padx=2)
        ttk.Label(custom_row, text="x").pack(side="left")
        ttk.Entry(
            custom_row, textvariable=self.custom_height_var, width=6, state=custom_state
        ).pack(side="left", padx=2)
        ttk.Label(custom_row, text="[Experimental]", foreground="#9a6700").pack(
            side="left", padx=6
        )

        scale_frame = ttk.LabelFrame(
            self.root, text="Window scaling (wrapper; does not change game pixels)"
        )
        scale_frame.pack(fill="x", **pad)
        verified = sorted(ini_mod.VERIFIED_SCALING_MODES)
        self.scaling_var = tk.StringVar(
            value=self.settings.get("scaling_mode", ini_mod.DEFAULT_SCALING_MODE)
        )
        if len(verified) > 1:
            ttk.Combobox(
                scale_frame,
                textvariable=self.scaling_var,
                values=verified,
                state="readonly",
            ).pack(anchor="w", padx=6, pady=2)
        else:
            self.scaling_var.set(verified[0])
            ttk.Label(
                scale_frame,
                text=f"{verified[0]} (from the tracked dxcfg_windowed.ini template)",
            ).pack(anchor="w", padx=6, pady=2)

        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", **pad)
        self.play_button = ttk.Button(action_frame, text="Play", command=self.on_play)
        self.play_button.pack(side="left", padx=4)
        ttk.Button(
            action_frame, text="Open candidate folder", command=self.on_open_folder
        ).pack(side="left", padx=4)
        ttk.Button(
            action_frame, text="Clean candidates", command=self.on_clean
        ).pack(side="left", padx=4)

        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

    # -- helpers ----------------------------------------------------------

    def log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.root.update_idletasks()

    def refresh_environment(self) -> None:
        self.environment = core.check_environment()
        report = self.environment.to_dict()
        texts = {
            "base_exe": (
                "OK (SHA verified)"
                if report["base_exe"]["passed"]
                else report["base_exe"].get("error", "SHA-256 mismatch — refusing to patch")
            ),
            "wrapper_dll": (
                "found in C:\\Clash"
                if report["wrapper_dll"]["passed"]
                else "missing (needed before Play)"
            ),
            "candidates_root": (
                "writable"
                if report["candidates_root"]["passed"]
                else report["candidates_root"].get("error", "low disk space")
            ),
            "running_processes": (
                "none"
                if report["running_processes"]["passed"]
                else f"{len(report['running_processes']['matches'])} found"
            ),
        }
        for key, label in self.env_labels.items():
            ok = report[key]["passed"]
            label.configure(
                text=("✓ " if ok else "✗ ") + texts[key],
                foreground="#1a7f37" if ok else "#cf222e",
            )

    def _current_resolution_key(self) -> str:
        selected = self.resolution_var.get()
        if selected != "custom":
            return selected
        width_text = self.custom_width_var.get().strip()
        height_text = self.custom_height_var.get().strip()
        if not width_text.isdigit() or not height_text.isdigit():
            raise core.LauncherError(
                "Custom resolution needs numeric width and height."
            )
        width, height = int(width_text), int(height_text)
        errors = presets.validate_custom_resolution(width, height, self.manifest)
        if errors:
            raise core.LauncherError(" ".join(errors))
        return f"{width}x{height}"

    def _backend(self):
        return framed if self.profile_var.get() == "framed" else core

    def on_profile_change(self) -> None:
        experimental = self.profile_var.get() == "framed"
        self.experimental_warned = False
        self.profile_label.configure(text=framed.WARNING if experimental else "Existing resolution evidence and stable defaults are unchanged.")
        for button, option in self.resolution_buttons:
            badge = "Experimental" if experimental else STATUS_BADGES[option.status][0]
            button.configure(text=f"{option.key}  [{badge}]")

    def _selected_plan(self) -> core.CandidatePlan:
        return self._backend().plan_candidate(
            resolution=self._current_resolution_key(),
            scaling_mode=self.scaling_var.get(),
            manifest=self.manifest,
        )

    def _selected_option(self) -> presets.ResolutionOption | None:
        for option in self.options:
            if option.key == self.resolution_var.get():
                return option
        return None

    # -- actions ----------------------------------------------------------

    def on_play(self) -> None:
        self.play_button.configure(state="disabled")
        try:
            self._play_sequence()
        except core.LauncherError as exc:
            self.log(f"ERROR: {exc}")
            messagebox.showerror("Clash95 HD Launcher", str(exc))
        except presets.ManifestError as exc:
            self.log(f"ERROR: {exc}")
            messagebox.showerror("Clash95 HD Launcher", str(exc))
        finally:
            self.play_button.configure(state="normal")

    def _play_sequence(self) -> None:
        self.refresh_environment()
        assert self.environment is not None
        if not self.environment.base_exe.passed:
            raise core.LauncherError(
                "The base game executable is missing or does not match the "
                "expected SHA-256. The launcher refuses to patch unknown "
                "builds and offers no override.\n"
                f"Expected: {core.patch_clash95_hd.EXPECTED_SHA256}"
            )

        option = self._selected_option()
        is_experimental = self.profile_var.get() == "framed" or option is None or option.is_experimental
        if is_experimental and not self.experimental_warned:
            warning = framed.WARNING + " Continue?" if self.profile_var.get() == "framed" else EXPERIMENTAL_WARNING
            if not messagebox.askokcancel("Experimental profile or resolution", warning):
                self.log("Cancelled experimental launch.")
                return
            self.experimental_warned = True

        if not self.environment.running_processes.passed:
            if not messagebox.askokcancel(
                "Game already running",
                "A Clash95 or CDB process is already running. Starting a second "
                "instance is usually a mistake. Continue anyway?",
            ):
                self.log("Cancelled: game process already running.")
                return

        plan = self._selected_plan()
        self.log(f"Stage: {plan.stage}")
        self.log(f"Resolution: {plan.resolution}  Scaling: {plan.scaling_mode}")
        backend = self._backend()
        result = backend.ensure_candidate(plan, progress=self.log)
        deploy = backend.deploy_runtime_files(plan, result, progress=self.log)
        if deploy["wrapper"] != "copied":
            messagebox.showwarning("DirectDraw wrapper missing", WRAPPER_HELP)
            self.log("Launch blocked: wrapper ddraw.dll missing in C:\\Clash.")
            return

        if backend is framed:
            framed.verify_launch(plan)
        process = core.launch_game(plan, confirmed=True)
        self.log(f"Launched PID {process.pid}: {plan.candidate_exe}")
        self._save_settings()

    def on_open_folder(self) -> None:
        try:
            plan = self._selected_plan()
        except core.LauncherError as exc:
            messagebox.showerror("Clash95 HD Launcher", str(exc))
            return
        plan.candidate_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(plan.candidate_dir))  # noqa: S606 - user-clicked folder open

    def on_clean(self) -> None:
        try:
            plan = self._selected_plan()
        except core.LauncherError as exc:
            messagebox.showerror("Clash95 HD Launcher", str(exc))
            return
        if not messagebox.askokcancel(
            "Clean candidates",
            f"Delete the launcher-owned folder {plan.candidate_dir}?",
        ):
            return
        removed = core.clean_candidate_dir(plan)
        self.log(f"Removed {len(removed)} candidate file(s).")

    def _save_settings(self) -> None:
        if self.profile_var.get() == "framed":
            return
        try:
            self.settings["last_resolution"] = self._current_resolution_key()
        except core.LauncherError:
            self.settings["last_resolution"] = presets.default_key(self.manifest)
        self.settings["scaling_mode"] = self.scaling_var.get()
        try:
            self.settings["window_geometry"] = self.root.geometry()
        except tk.TclError:
            pass
        settings_mod.save_settings(self.settings)

    def on_close(self) -> None:
        self._save_settings()
        settings_mod.release_lock()
        self.root.destroy()


def start_gui(initial_profile: str = "classic") -> int:
    if not settings_mod.acquire_lock(pid_alive=core.pid_alive):
        print("Another Clash95 HD launcher instance is already running.")
        return 1
    try:
        root = tk.Tk()
        app = LauncherApp(root, initial_profile=initial_profile)
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        root.mainloop()
    finally:
        settings_mod.release_lock()
    return 0


def widget_selftest() -> str:
    """Construct and destroy the widget tree without entering the main loop."""
    root = tk.Tk()
    root.withdraw()
    try:
        app = LauncherApp(root)
        app.log("selftest: widgets constructed")
        root.update_idletasks()
    finally:
        root.destroy()
    return "ok"

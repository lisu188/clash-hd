#!/usr/bin/env python3
"""Tkinter GUI for the Clash95 HD launcher.

All widget code lives here; the patch/deploy/launch logic is in ``core``.
The game starts only from the Play button handler, which is the explicit
user action that passes ``confirmed=True`` to ``core.launch_game``.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

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


PROFILE_NAMES = {"classic": "Classic", "framed": "Framed + minimap"}
TAB_NAMES = ("Main settings", "Launcher settings", "Information", "Diagnostics")


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

        self._busy = False
        self._plan_valid = False
        self.ui_scale = float(root.tk.call("tk", "scaling")) / (96 / 72)
        root.title("Clash HD Launcher")
        self._configure_style()
        root.geometry(f"{self._px(730)}x{self._px(650)}")
        root.minsize(self._px(710), self._px(650))
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
        for variable in (self.resolution_var, self.custom_width_var, self.custom_height_var, self.scaling_var):
            variable.trace_add("write", self.refresh_display_plan)
        self.on_profile_change()
        self.refresh_environment()

    def _px(self, value: int) -> int:
        return round(value * self.ui_scale)

    def _configure_style(self) -> None:
        self.style = ttk.Style(self.root)
        if sys.platform != "win32":
            self.style.theme_use("clam")
        tkfont.nametofont("TkDefaultFont").configure(size=9)
        tkfont.nametofont("TkTextFont").configure(size=9)
        self.style.configure("TFrame", background="#efefed")
        self.style.configure("TLabel", background="#efefed")
        self.style.configure("TLabelframe", background="#efefed")
        self.style.configure("TLabelframe.Label", background="#efefed")
        self.style.configure("TNotebook", background="#efefed")
        self.style.configure("TNotebook.Tab", padding=(self._px(10), self._px(4)))
        self.style.configure("TButton", padding=(self._px(6), self._px(3)))
        family = tkfont.nametofont("TkDefaultFont").actual("family")
        self.style.configure("Play.TButton", font=(family, 9, "bold"))
        self.style.configure("Heading.TLabel", font=(family, 10, "bold"))
        self.root.configure(background="#efefed")

    def _draw_banner(self, event=None) -> None:
        canvas = self.banner
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 20 or height < 20:
            return
        canvas.delete("all")
        for y in range(height):
            t = y / max(1, height - 1)
            color = "#%02x%02x%02x" % (int(12 + 9 * t), int(43 + 27 * t), int(48 + 29 * t))
            canvas.create_line(0, y, width, y, fill=color)
        for x in range(-height, width, self._px(36)):
            canvas.create_line(x, height, x + height, 0, fill="#21565b")
            canvas.create_line(x + self._px(4), height, x + height + self._px(4), 0, fill="#19474c")
        for inset, color in ((1, "#4b3613"), (2, "#dfc478"), (4, "#8b6e35"), (6, "#dfc478"), (7, "#192c29")):
            d = self._px(inset)
            canvas.create_rectangle(d, d, width - d - 1, height - d - 1, outline=color)
        for x, y, sx, sy in ((10, 10, 1, 1), (width/self.ui_scale-10, 10, -1, 1),
                              (10, height/self.ui_scale-10, 1, -1),
                              (width/self.ui_scale-10, height/self.ui_scale-10, -1, -1)):
            points = [(x + sx*dx, y + sy*dy) for dx, dy in ((0, 0), (23, 0), (16, 6), (9, 6), (6, 9), (6, 16), (0, 23))]
            canvas.create_polygon(*(self._px(v) for point in points for v in point), fill="#a08442", outline="#e8ce88")
        family = "Times New Roman" if sys.platform == "win32" else "Liberation Serif"
        title = (family, 40, "bold")
        x, y = self._px(35), height // 2 - self._px(6)
        canvas.create_text(x+self._px(2), y+self._px(3), text="CLASH HD", font=title, fill="#101b1b", anchor="w")
        canvas.create_text(x-self._px(1), y-self._px(1), text="CLASH HD", font=title, fill="#f6e8b7", anchor="w")
        canvas.create_text(x, y, text="CLASH HD", font=title, fill="#d3b56a", anchor="w")
        canvas.create_text(x+self._px(2), height-self._px(20), text="HIGH-DEFINITION MOD FOR CLASH95",
                           font=(family, 9), fill="#e2d4a1", anchor="w")
        canvas.create_text(width-self._px(25), height//2, text="HD LAUNCHER",
                           font="TkDefaultFont", fill="#d6c58b", anchor="e")

    def _build_widgets(self) -> None:
        pad = self._px(8)
        self.shell = ttk.Frame(self.root, padding=pad)
        self.shell.pack(fill="both", expand=True)
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(2, weight=1)
        self.banner = tk.Canvas(self.shell, height=self._px(94), highlightthickness=0, takefocus=0)
        self.banner.grid(row=0, column=0, sticky="ew", pady=(0, pad))
        self.banner.bind("<Configure>", self._draw_banner)

        actions = ttk.Frame(self.shell)
        actions.grid(row=1, column=0, sticky="ew", pady=(0, pad))
        actions.columnconfigure(0, weight=1)
        self.executable_combo = ttk.Combobox(actions, values=(core.BASE_EXE_NAME,), state="readonly", width=18)
        self.executable_combo.set(core.BASE_EXE_NAME)
        self.executable_combo.grid(row=0, column=0, sticky="ew", padx=(0, pad))
        self.folder_button = ttk.Button(actions, text="Open folder", command=self.on_open_folder, width=14)
        self.folder_button.grid(row=0, column=1, padx=(0, pad))
        self.prepare_button = ttk.Button(actions, text="Create HD exe", command=self.on_prepare, width=16)
        self.prepare_button.grid(row=0, column=2, padx=(0, pad))
        self.play_button = ttk.Button(actions, text="Play", command=self.on_play, width=16, style="Play.TButton")
        self.play_button.grid(row=0, column=3)

        self.notebook = ttk.Notebook(self.shell)
        self.notebook.grid(row=2, column=0, sticky="nsew")
        self.tabs = {}
        for name in TAB_NAMES:
            tab = ttk.Frame(self.notebook, padding=pad)
            self.notebook.add(tab, text=name)
            self.tabs[name] = tab
        self.notebook.enable_traversal()
        self._build_main_tab()
        self._build_settings_tab()
        self._build_information_tab()
        self._build_diagnostics_tab()

        footer = ttk.Frame(self.shell)
        footer.grid(row=3, column=0, sticky="ew", pady=(pad, 0))
        footer.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(footer, text="Checking installation...", wraplength=self._px(540))
        self.status_label.grid(row=0, column=0, sticky="w")
        ttk.Button(footer, text="Exit", command=self.on_close, width=14).grid(row=0, column=1, sticky="e")
        self.resolution_buttons = []

    def _build_main_tab(self) -> None:
        tab, gap = self.tabs["Main settings"], self._px(8)
        tab.columnconfigure(0, weight=1, uniform="main")
        tab.columnconfigure(1, weight=1, uniform="main")
        tab.rowconfigure(1, weight=1)
        language = ttk.LabelFrame(tab, text="Launcher", padding=gap)
        language.grid(row=0, column=0, sticky="ew", padx=(0, gap), pady=(0, gap))
        language.columnconfigure(1, weight=1)
        ttk.Label(language, text="Language:", width=12).grid(row=0, column=0, sticky="w")
        ttk.Label(language, text="English").grid(row=0, column=1, sticky="w")
        status = ttk.LabelFrame(tab, text="Profile status", padding=gap)
        status.grid(row=0, column=1, sticky="nsew", pady=(0, gap))
        self.profile_badge = ttk.Label(status, style="Heading.TLabel")
        self.profile_badge.pack(anchor="w")

        graphics = ttk.LabelFrame(tab, text="Graphics", padding=gap)
        graphics.grid(row=1, column=0, sticky="nsew", padx=(0, gap))
        graphics.columnconfigure(1, weight=1)
        self.renderer_choice = tk.StringVar(value=PROFILE_NAMES[self.profile_var.get()])
        names = (PROFILE_NAMES["classic"],) if getattr(sys, "frozen", False) else tuple(PROFILE_NAMES.values())
        self.renderer_combo = ttk.Combobox(graphics, textvariable=self.renderer_choice, values=names, state="readonly", width=21)
        self.renderer_combo.bind("<<ComboboxSelected>>", self._choose_renderer)
        self.resolution_combo = ttk.Combobox(graphics, textvariable=self.resolution_var, state="readonly", width=21)
        self.scaling_var = tk.StringVar(value=self.settings.get("scaling_mode", ini_mod.DEFAULT_SCALING_MODE))
        self.scaling_combo = ttk.Combobox(graphics, textvariable=self.scaling_var,
                                        values=tuple(sorted(ini_mod.VERIFIED_SCALING_MODES)), state="readonly", width=21)
        for row, label, widget in ((0, "Renderer:", self.renderer_combo), (1, "Source size:", self.resolution_combo),
                                   (3, "Scaling:", self.scaling_combo)):
            ttk.Label(graphics, text=label, width=12).grid(row=row, column=0, sticky="w", pady=self._px(3))
            widget.grid(row=row, column=1, sticky="ew", pady=self._px(3))
        self.custom_row = ttk.Frame(graphics)
        self.custom_row.grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Label(self.custom_row, text="Custom size:", width=12).pack(side="left")
        self.custom_width_var = tk.StringVar()
        self.custom_height_var = tk.StringVar()
        ttk.Entry(self.custom_row, textvariable=self.custom_width_var, width=7).pack(side="left")
        ttk.Label(self.custom_row, text=" x ").pack(side="left")
        ttk.Entry(self.custom_row, textvariable=self.custom_height_var, width=7).pack(side="left")
        self.custom_row.grid_remove()
        ttk.Label(graphics, text="Mode:", width=12).grid(row=4, column=0, sticky="w", pady=self._px(3))
        ttk.Label(graphics, text="Windowed / DirectDraw wrapper").grid(row=4, column=1, sticky="w", pady=self._px(3))

        components = ttk.LabelFrame(tab, text="Profile components", padding=gap)
        components.grid(row=1, column=1, sticky="nsew")
        components.columnconfigure(0, weight=1)
        components.rowconfigure(0, weight=1)
        self.component_list = tk.Listbox(components, height=6, borderwidth=1, relief="sunken", highlightthickness=0,
                                        activestyle="none", exportselection=False, font="TkDefaultFont", takefocus=0)
        self.component_list.grid(row=0, column=0, sticky="nsew")
        ttk.Label(components, text="Included by the selected recipe; not plugins.", wraplength=self._px(295)).grid(
            row=1, column=0, sticky="w", pady=(gap, 0))
        view = ttk.LabelFrame(tab, text="Next-launch viewport", padding=gap)
        view.grid(row=2, column=0, sticky="nsew", padx=(0, gap), pady=(gap, 0))
        self.viewport_label = ttk.Label(view, wraplength=self._px(295))
        self.viewport_label.pack(anchor="w")
        validation = ttk.LabelFrame(tab, text="Validation", padding=gap)
        validation.grid(row=2, column=1, sticky="nsew", pady=(gap, 0))
        self.validation_label = ttk.Label(validation, wraplength=self._px(295))
        self.validation_label.pack(anchor="w")
        ttk.Button(validation, text="View diagnostics", command=lambda: self.notebook.select(self.tabs["Diagnostics"])).pack(anchor="w", pady=(gap, 0))

    def _build_settings_tab(self) -> None:
        tab, gap = self.tabs["Launcher settings"], self._px(8)
        folders = ttk.LabelFrame(tab, text="Local installation", padding=gap)
        folders.pack(fill="x")
        folders.columnconfigure(1, weight=1)
        self.game_dir_var = tk.StringVar(value=self.settings["clash_dir"])
        self.candidates_dir_var = tk.StringVar(value=self.settings["candidates_root"])
        for row, (label, variable) in enumerate((("Game folder:", self.game_dir_var), ("Candidates:", self.candidates_dir_var))):
            ttk.Label(folders, text=label).grid(row=row, column=0, sticky="w", padx=(0, gap), pady=gap)
            ttk.Entry(folders, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=gap)
            ttk.Button(folders, text="Browse...", command=lambda v=variable: self._browse_folder(v)).grid(
                row=row, column=2, padx=(gap, 0), pady=gap)
        self.apply_button = ttk.Button(folders, text="Apply folders", command=self.on_apply_folders)
        self.apply_button.grid(row=2, column=2, sticky="e")
        ttk.Label(tab, text="The original clash95.exe is never overwritten. Generated candidates must live outside the game folder and the repository.",
                  wraplength=self._px(650)).pack(anchor="w", pady=gap)
        ttk.Label(tab, text="Renderer selection is session-only. Framed sessions do not replace your saved Classic resolution.",
                  wraplength=self._px(650)).pack(anchor="w", pady=gap)
        cleanup = ttk.LabelFrame(tab, text="Selected candidate", padding=gap)
        cleanup.pack(fill="x", pady=gap)
        ttk.Label(cleanup, text="Clean removes only the selected profile/resolution directory.", wraplength=self._px(650)).pack(anchor="w")
        self.clean_button = ttk.Button(cleanup, text="Clean candidate...", command=self.on_clean)
        self.clean_button.pack(anchor="w", pady=(gap, 0))

    def _build_information_tab(self) -> None:
        tab, gap = self.tabs["Information"], self._px(8)
        ttk.Label(tab, text="Clash HD", style="Heading.TLabel").pack(anchor="w", pady=(0, gap))
        ttk.Label(tab, text="High-resolution patches for the original Clash95 game.", wraplength=self._px(650)).pack(anchor="w")
        self.profile_label = ttk.Label(tab, wraplength=self._px(650))
        self.profile_label.pack(anchor="w", pady=gap)
        ttk.Label(tab, text="Create HD exe prepares and verifies a local candidate without starting the game. Play is the only game-launch button.",
                  wraplength=self._px(650)).pack(anchor="w", pady=gap)
        ttk.Label(tab, text="Game files and a compatible DirectDraw wrapper are required locally. The launcher never ships or downloads them.",
                  wraplength=self._px(650)).pack(anchor="w", pady=gap)
        ttk.Separator(tab).pack(fill="x", pady=gap)
        ttk.Label(tab, text="Interface layout inspired by the Heroes III HD Mod launcher. Clash HD is a separate project; no Heroes artwork is bundled.",
                  wraplength=self._px(650)).pack(anchor="w", pady=gap)

    def _build_diagnostics_tab(self) -> None:
        tab, gap = self.tabs["Diagnostics"], self._px(8)
        env_frame = ttk.LabelFrame(tab, text="Installation checks", padding=gap)
        env_frame.pack(fill="x")
        env_frame.columnconfigure(1, weight=1)
        self.env_labels = {}
        for row, (key, title) in enumerate((("base_exe", "Game executable"), ("wrapper_dll", "DirectDraw wrapper"),
                                          ("candidates_root", "Candidates folder"), ("running_processes", "Running game processes"))):
            ttk.Label(env_frame, text=title+":", width=23).grid(row=row, column=0, sticky="nw", pady=2)
            label = ttk.Label(env_frame, text="Checking...", wraplength=self._px(435))
            label.grid(row=row, column=1, sticky="w", pady=2)
            self.env_labels[key] = label
        ttk.Button(env_frame, text="Refresh", command=self.refresh_environment).grid(row=4, column=1, sticky="e")
        self.display_label = ttk.Label(tab, wraplength=self._px(650))
        self.display_label.pack(fill="x", pady=gap)
        log_frame = ttk.LabelFrame(tab, text="Activity log", padding=self._px(4))
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=5, state="disabled", wrap="word", font="TkTextFont", borderwidth=1, relief="sunken")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

    def _choose_renderer(self, _event=None) -> None:
        self.profile_var.set(next(key for key, name in PROFILE_NAMES.items() if name == self.renderer_choice.get()))
        self.on_profile_change()

    def _browse_folder(self, variable) -> None:
        folder = filedialog.askdirectory(parent=self.root, initialdir=variable.get(), mustexist=True)
        if folder:
            variable.set(folder)

    def on_apply_folders(self) -> None:
        try:
            game, candidates = self.game_dir_var.get().strip(), self.candidates_dir_var.get().strip()
            if not game or not candidates:
                raise core.LauncherError("Both folder paths are required.")
            self._backend().plan_candidate(resolution=self._current_resolution_key(), scaling_mode=self.scaling_var.get(),
                                           manifest=self.manifest, clash_dir=Path(game), candidates_root=Path(candidates))
            updated = dict(self.settings, clash_dir=game, candidates_root=candidates)
            settings_mod.save_settings(updated)
            self.settings = updated
            self.refresh_display_plan()
            self.refresh_environment()
            self.log("Updated local folder settings.")
        except (core.LauncherError, presets.ManifestError, OSError) as exc:
            messagebox.showerror("Clash HD Launcher", str(exc))

    def _set_action_state(self) -> None:
        valid = self._plan_valid and not getattr(self, "_busy", False)
        environment = getattr(self, "environment", None)
        ready = environment is None or environment.ready_to_patch
        wrapper = environment is None or environment.wrapper_dll.passed
        self.play_button.configure(state="normal" if valid and ready and wrapper else "disabled")
        if hasattr(self, "prepare_button"):
            self.prepare_button.configure(state="normal" if valid and ready else "disabled")

    # -- helpers ----------------------------------------------------------

    def log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.root.update_idletasks()

    def refresh_environment(self) -> None:
        self.environment = core.check_environment(
            clash_dir=Path(self.settings["clash_dir"]), candidates_root=Path(self.settings["candidates_root"]))
        report = self.environment.to_dict()
        texts = {
            "base_exe": (
                "OK (SHA verified)"
                if report["base_exe"]["passed"]
                else report["base_exe"].get("error", "SHA-256 mismatch — refusing to patch")
            ),
            "wrapper_dll": (
                "found in the selected game directory"
                if report["wrapper_dll"]["passed"]
                else "missing (needed before Play)"
            ),
            "candidates_root": (
                "sufficient free space"
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
        if hasattr(self, "status_label"):
            if not self.environment.base_exe.passed:
                status = "Game executable missing or unrecognized. See Diagnostics."
            elif not self.environment.candidates_root.passed:
                status = "Candidate folder check failed. See Diagnostics."
            elif not self.environment.running_processes.passed:
                status = "Game or debugger detected. Close it before preparing a candidate."
            elif not self.environment.wrapper_dll.passed:
                status = "DirectDraw wrapper missing. Create HD exe is still available."
            else:
                status = "Installation checks passed. No game has been launched by this check."
            self.status_label.configure(text=status)
            self._set_action_state()

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
        if hasattr(self, "renderer_choice"):
            self.renderer_choice.set(PROFILE_NAMES[self.profile_var.get()])
            self.resolution_combo.configure(values=tuple(option.key for option in presets.load_options(self.manifest, self.profile_var.get())) + ("custom",))
            components = (("Four-sided adventure frame", "Clipped edge tiles", "Minimap viewport correction", "Native fallback on other screens")
                          if experimental else ("Classic adventure-map layout", "Centered main menu", "Right-anchored minimap", "Existing stable patch recipe"))
            self.component_list.delete(0, "end")
            for component in components:
                self.component_list.insert("end", component)
        self.refresh_display_plan()

    def refresh_display_plan(self, *_args) -> None:
        if not hasattr(self, "display_label"):
            return
        self.experimental_warned = False
        if hasattr(self, "custom_row"):
            if self.resolution_var.get() == "custom":
                self.custom_row.grid()
            else:
                self.custom_row.grid_remove()
        try:
            renderer = self.profile_var.get()
            for button, option in self.resolution_buttons:
                info = presets.resolution_info(option.key, renderer=renderer, manifest=self.manifest)
                badge = STATUS_BADGES[info["status"]][0] if info["recipe_eligible"] else "Unavailable"
                button.configure(text=f"{option.key}  [{badge}]", state="normal" if info["recipe_eligible"] else "disabled")
            plan = self._selected_plan()
            display = core.display_for_plan(plan)
            info = presets.resolution_info(plan.resolution, renderer=renderer, stage=plan.stage, manifest=self.manifest)
            left, top, right, bottom = display.terrain
            detail = (f"Terrain {right-left+1}x{bottom-top+1} pixels; full tiles "
                      f"{display.full_tiles[0]}x{display.full_tiles[1]}; coverage "
                      f"{display.coverage_tiles[0]}x{display.coverage_tiles[1]}. "
                      f"Current full renderer needs a world of at least {display.full_tiles[0]}x{display.full_tiles[1]} tiles.")
            if not display.map_geometry_available:
                detail = "Diagnostic stage: expanded map geometry is not established by this patch selection."
            self.display_label.configure(text=f"Next launch: {renderer} {plan.resolution} [{info['status']}]. " + detail)
            self._plan_valid = True
            if hasattr(self, "viewport_label"):
                self.viewport_label.configure(text=f"Terrain: {right-left+1} x {bottom-top+1} pixels\n"
                    f"Full tiles: {display.full_tiles[0]} x {display.full_tiles[1]}\n"
                    f"Coverage: {display.coverage_tiles[0]} x {display.coverage_tiles[1]} (with edges)")
                badge, color = STATUS_BADGES[info["status"]]
                self.profile_badge.configure(text=f"{PROFILE_NAMES[renderer]}  /  {badge}", foreground=color)
                self.validation_label.configure(text=f"Minimum map: {display.full_tiles[0]} x {display.full_tiles[1]} tiles.\n"
                    + ("Runtime and input checks are still pending." if info["status"] == "experimental" else "Existing Classic evidence; not rechecked."))
                if not display.map_geometry_available:
                    self.viewport_label.configure(text="Diagnostic recipe: no expanded-map contract.")
                    self.validation_label.configure(text="Only source recipe selection has been checked.")
            self._set_action_state()
        except (core.LauncherError, presets.ManifestError, core.DisplayPlanError) as exc:
            self._plan_valid = False
            self.display_label.configure(text=f"Next launch unavailable: {exc}")
            if hasattr(self, "viewport_label"):
                self.viewport_label.configure(text="No valid viewport selected.")
                self.profile_badge.configure(text="Unavailable", foreground="#cf222e")
                self.validation_label.configure(text=str(exc))
            self._set_action_state()

    def _selected_plan(self) -> core.CandidatePlan:
        return self._backend().plan_candidate(
            resolution=self._current_resolution_key(),
            scaling_mode=self.scaling_var.get(),
            manifest=self.manifest,
            clash_dir=Path(self.settings["clash_dir"]),
            candidates_root=Path(self.settings["candidates_root"]),
        )

    def _selected_option(self) -> presets.ResolutionOption | None:
        for option in self.options:
            if option.key == self.resolution_var.get():
                return option
        return None

    # -- actions ----------------------------------------------------------

    def on_prepare(self) -> None:
        if getattr(self, "_busy", False):
            return
        self._busy = True
        self._set_action_state()
        try:
            self.refresh_environment()
            if not self.environment.ready_to_patch:
                raise core.LauncherError("The original executable and candidate folder must pass their checks before preparation.")
            if not self.environment.running_processes.passed:
                raise core.LauncherError("Close the game or debugger before preparing a candidate.")
            plan = self._selected_plan()
            info = presets.resolution_info(plan.resolution, renderer=plan.renderer, stage=plan.stage, manifest=self.manifest)
            if info["status"] == "experimental" and not messagebox.askokcancel(
                    "Experimental candidate", "Create this experimental HD executable? This action will not start the game."):
                return
            backend = self._backend()
            result = backend.ensure_candidate(plan, progress=self.log)
            deployment = backend.deploy_runtime_files(plan, result, progress=self.log)
            status = "HD executable prepared. No game was launched."
            if deployment["wrapper"] != "copied":
                status += " Add a DirectDraw wrapper before Play."
            self.log(status)
            self.status_label.configure(text=status)
        except (core.LauncherError, presets.ManifestError, OSError) as exc:
            self.log(f"ERROR: {exc}")
            messagebox.showerror("Clash HD Launcher", str(exc))
        finally:
            self._busy = False
            self.refresh_display_plan()

    def on_play(self) -> None:
        if getattr(self, "_busy", False):
            return
        self._busy = True
        self.play_button.configure(state="disabled")
        if hasattr(self, "prepare_button"):
            self.prepare_button.configure(state="disabled")
        try:
            self._play_sequence()
        except core.LauncherError as exc:
            self.log(f"ERROR: {exc}")
            messagebox.showerror("Clash95 HD Launcher", str(exc))
        except presets.ManifestError as exc:
            self.log(f"ERROR: {exc}")
            messagebox.showerror("Clash95 HD Launcher", str(exc))
        finally:
            self._busy = False
            self.refresh_display_plan()

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

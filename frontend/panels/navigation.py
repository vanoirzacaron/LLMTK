"""
Navigation Panel (for GNOME 46+)

This panel provides a UI for viewing and switching between GNOME workspaces.
It uses gdbus for modern GNOME versions and falls back to wmctrl for compatibility.

Key Features:
- Fetches and displays a list of current workspaces.
- Indicates the currently active workspace.
- Allows switching to a different workspace by clicking a button.
- Periodically refreshes to stay in sync with the desktop environment.
- Includes a button to set custom workspace names.
"""

import tkinter as tk
from tkinter import ttk
import subprocess
import re
import json

# --- Constants ---
PANEL_TITLE = "Workspaces"

# --- Logging ---
def log(launcher, message, level="info"):
    """A centralized logging helper."""
    log_message = f"[Navigation] {message}"
    print(log_message)
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(PANEL_TITLE, message)

# --- Workspace Controller ---
class GnomeWorkspaceController:
    """Handles all workspace operations with GNOME Shell."""
    
    def __init__(self, launcher, panel):
        self.launcher = launcher
        self.panel = panel # Reference to the Navigation panel UI for refreshing
        self.method = None
        self.working_js_pattern = None
        self._detect_method()
        log(self.launcher, f"Using method: {self.method}")
    
    def _detect_method(self):
        js_variants = [
            "global.display.get_workspace_manager().",
            "global.workspace_manager.",
            "global.screen."
        ]
        for js_base in js_variants:
            try:
                result = subprocess.run(
                    ["gdbus", "call", "--session", "--dest", "org.gnome.Shell",
                     "--object-path", "/org/gnome/Shell", "--method", "org.gnome.Shell.Eval",
                     f"{js_base}get_n_workspaces()"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0 and "(true," in result.stdout:
                    self.method = "gdbus"
                    self.working_js_pattern = js_base
                    log(self.launcher, f"✓ Using JavaScript API: {js_base}")
                    return
            except Exception:
                continue
        try:
            if subprocess.run(["which", "wmctrl"], capture_output=True, timeout=1).returncode == 0:
                self.method = "wmctrl"
                log(self.launcher, "✓ Using wmctrl as fallback")
                return
        except Exception:
            pass
        self.method = "none"
        log(self.launcher, "✗ No working workspace manager found", "error")
    
    def get_workspaces(self):
        if self.method == "gdbus":
            return self._get_workspaces_gdbus()
        elif self.method == "wmctrl":
            return self._get_workspaces_wmctrl()
        return None

    def _parse_workspace_name(self, name):
        """Removes resolution strings like ' 1920x1080' and trims whitespace."""
        # FIX: Use a more robust regex to find and remove the resolution string.
        cleaned_name = re.sub(r'\s+\d+x\d+$', '', name)
        return cleaned_name.strip()

    def _get_workspaces_gdbus(self):
        if not self.working_js_pattern:
            return self._get_workspaces_wmctrl()
        try:
            names_js = self.working_js_pattern + "get_workspace_names()"
            names_result = subprocess.run(
                ["gdbus", "call", "--session", "--dest", "org.gnome.Shell", "--object-path",
                 "/org/gnome/Shell", "--method", "org.gnome.Shell.Eval", names_js],
                capture_output=True, text=True, timeout=2
            )
            
            workspace_names = []
            if names_result.returncode == 0 and "(true," in names_result.stdout:
                match = re.search(r"\(true, '(.+)'\)", names_result.stdout.strip())
                if match:
                    try:
                        raw_names = json.loads(match.group(1))
                        workspace_names = [self._parse_workspace_name(n) for n in raw_names]
                    except (json.JSONDecodeError, TypeError):
                        return self._get_workspaces_wmctrl()
                else: return self._get_workspaces_wmctrl()
            else: return self._get_workspaces_wmctrl()

            active_js = self.working_js_pattern + "get_active_workspace_index()"
            active_result = subprocess.run(
                ["gdbus", "call", "--session", "--dest", "org.gnome.Shell", "--object-path",
                 "/org/gnome/Shell", "--method", "org.gnome.Shell.Eval", active_js],
                capture_output=True, text=True, timeout=2
            )
            
            active_index = -1
            if active_result.returncode == 0 and "(true," in active_result.stdout:
                match = re.search(r"'(\d+)'", active_result.stdout)
                if match: active_index = int(match.group(1))

            return [
                {"name": name, "index": i, "active": i == active_index}
                for i, name in enumerate(workspace_names)
            ]
        except Exception: return self._get_workspaces_wmctrl()
    
    def _get_workspaces_wmctrl(self):
        try:
            result = subprocess.run(["wmctrl", "-d"], capture_output=True, text=True, timeout=2)
            if result.returncode != 0: return None
            workspaces = []
            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 2:
                    raw_name = ' '.join(parts[8:]) if len(parts) >= 9 else f"Workspace {int(parts[0]) + 1}"
                    workspaces.append({
                        "name": self._parse_workspace_name(raw_name),
                        "index": int(parts[0]),
                        "active": parts[1] == '*'
                    })
            return workspaces
        except Exception as e: log(self.launcher, f"Error getting workspaces via wmctrl: {e}", "error"); return None

    def switch_to_workspace(self, index):
        if self.method == "gdbus": self._switch_workspace_gdbus(index)
        elif self.method == "wmctrl": self._switch_workspace_wmctrl(index)
    
    def _switch_workspace_gdbus(self, index):
        if not self.working_js_pattern: self._switch_workspace_wmctrl(index); return
        try:
            switch_js = f"{self.working_js_pattern}get_workspace_by_index({index}).activate(global.get_current_time())"
            result = subprocess.run(
                ["gdbus", "call", "--session", "--dest", "org.gnome.Shell", "--object-path",
                 "/org/gnome/Shell", "--method", "org.gnome.Shell.Eval", switch_js],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode != 0 or "(true," not in result.stdout: self._switch_workspace_wmctrl(index)
        except Exception: self._switch_workspace_wmctrl(index)
    
    def _switch_workspace_wmctrl(self, index):
        try: subprocess.run(["wmctrl", "-s", str(index)], timeout=1)
        except Exception as e: log(self.launcher, f"Error switching workspace: {e}", "error")

    def set_custom_workspace_names(self):
        """Executes a gsettings command and then triggers a UI refresh."""
        try:
            command = ["gsettings", "set", "org.gnome.desktop.wm.preferences", "workspace-names",
                       "['Home', 'Infrasven', 'Mindfield', 'Up', 'Side job']"]
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=2)
            log(self.launcher, "Successfully set custom workspace names.")
            # FIX: Trigger a refresh via the panel reference for better reliability.
            self.panel.after(200, self.panel.update_workspaces)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            log(self.launcher, f"Failed to set workspace names: {e}", level="error")

# --- UI Panel ---
class Navigation(ttk.Frame):
    def __init__(self, parent, launcher=None):
        super().__init__(parent, padding="10")
        self.launcher = launcher
        self._is_running = True
        # FIX: Pass the panel instance to the controller for callbacks.
        self.controller = GnomeWorkspaceController(launcher, self)
        self.grid_columnconfigure(0, weight=1)
        
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(header_frame, text=PANEL_TITLE, font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        
        set_names_button = ttk.Button(header_frame, text="Set Names", command=self.controller.set_custom_workspace_names)
        set_names_button.grid(row=0, column=1, sticky="e", padx=5)

        ttk.Button(header_frame, text="🔄", width=3, command=self.update_workspaces).grid(row=0, column=2, sticky="e")

        self.workspace_frame = ttk.Frame(self)
        self.workspace_frame.grid(row=1, column=0, sticky="nsew")
        self.workspace_frame.grid_columnconfigure(0, weight=1)

        if self.controller.method != "none": self.update_workspaces()
        else: self._display_error_state("No workspace manager found.\nInstall: sudo apt install wmctrl")

    def update_workspaces(self):
        if not self._is_running or not self.winfo_exists(): return
        workspaces = self.controller.get_workspaces()
        existing_buttons = self.workspace_frame.winfo_children()
        
        if workspaces is None:
            if not existing_buttons: self._display_error_state("Could not fetch workspaces.")
        elif not workspaces:
            if not existing_buttons: ttk.Label(self.workspace_frame, text="No workspaces found.").grid(row=0, column=0, sticky="ew", pady=2)
        else:
            for i, ws in enumerate(workspaces):
                btn_text = f"{'● ' if ws['active'] else '○ '}{ws['name']}"
                style = "Active.TButton" if ws["active"] else "TButton"
                if i < len(existing_buttons) and isinstance(existing_buttons[i], ttk.Button):
                    existing_buttons[i].configure(text=btn_text, style=style, command=lambda idx=ws["index"]: self._on_workspace_click(idx))
                else:
                    btn = ttk.Button(self.workspace_frame, text=btn_text, style=style, command=lambda idx=ws["index"]: self._on_workspace_click(idx))
                    btn.grid(row=ws["index"], column=0, sticky="ew", pady=2)
            
            for widget in existing_buttons[len(workspaces):]: widget.destroy()
        
        self.after(5000, self.update_workspaces)

    def _on_workspace_click(self, index):
        self.controller.switch_to_workspace(index)
        self.after(100, self.update_workspaces)

    def _display_error_state(self, message):
        for widget in self.workspace_frame.winfo_children(): widget.destroy()
        ttk.Label(self.workspace_frame, text=message, style="Error.TLabel", justify="center").grid(row=0, column=0, sticky="ew", pady=10)

    def stop(self):
        log(self.launcher, "Stopping navigation panel update loop.")
        self._is_running = False

# --- Factory Function ---
def create_panel(parent, launcher):
    style = ttk.Style()
    style.configure("Active.TButton", font=("Arial", 10, "bold"), foreground="#0078d4")
    style.configure("Error.TLabel", foreground="red", font=("Arial", 9))
    panel = Navigation(parent, launcher=launcher)
    return panel

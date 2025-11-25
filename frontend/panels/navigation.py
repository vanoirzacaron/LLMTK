"""
Navigation Panel (for GNOME 46+)

This panel provides a UI for viewing and switching between GNOME workspaces.
It uses gdbus for modern GNOME versions and falls back to wmctrl for compatibility.

Key Features:
- Fetches and displays a list of current workspaces.
- Shows open windows/apps in each workspace.
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
        self.panel = panel
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

    def get_windows(self):
        """Fetches all windows and their workspace assignments."""
        try:
            result = subprocess.run(
                ["wmctrl", "-l", "-x"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode != 0:
                return {}
            
            windows_by_workspace = {}
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    window_id = parts[0]
                    workspace_idx = int(parts[1])
                    wm_class = parts[2]
                    window_title = parts[3] if len(parts) > 3 else "Untitled"
                    
                    # Extract app name from WM_CLASS (format: instance.class)
                    app_name = wm_class.split('.')[-1] if '.' in wm_class else wm_class
                    
                    # Filter out "zacaron-V1-0" from title
                    window_title = window_title.replace("zacaron-V1-0", "").strip()
                    # Clean up any double spaces
                    window_title = re.sub(r'\s+', ' ', window_title)
                    
                    # Skip desktop windows
                    if workspace_idx == -1:
                        continue
                    
                    if workspace_idx not in windows_by_workspace:
                        windows_by_workspace[workspace_idx] = []
                    
                    windows_by_workspace[workspace_idx].append({
                        'id': window_id,
                        'app': app_name,
                        'title': window_title
                    })
            
            return windows_by_workspace
        except Exception as e:
            log(self.launcher, f"Error fetching windows: {e}", "error")
            return {}

    def _parse_workspace_name(self, name):
        """Removes resolution strings like ' 1920x1080' and trims whitespace."""
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

    def focus_window(self, window_id):
        """Brings focus to a specific window."""
        try:
            subprocess.run(["wmctrl", "-i", "-a", window_id], timeout=1)
        except Exception as e:
            log(self.launcher, f"Error focusing window: {e}", "error")

    def set_custom_workspace_names(self):
        """Executes a gsettings command and then triggers a UI refresh."""
        try:
            command = ["gsettings", "set", "org.gnome.desktop.wm.preferences", "workspace-names",
                       "['Home', 'Infrasven', 'Mindfield', 'Up', 'Side job']"]
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=2)
            log(self.launcher, "Successfully set custom workspace names.")
            self.panel.after(200, self.panel.update_workspaces)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            log(self.launcher, f"Failed to set workspace names: {e}", level="error")

# --- UI Panel ---
class Navigation(ttk.Frame):
    def __init__(self, parent, launcher=None):
        super().__init__(parent, padding="10")
        self.launcher = launcher
        self._is_running = True
        self.controller = GnomeWorkspaceController(launcher, self)
        self.workspace_widgets = {}  # Store widgets for reuse
        self.grid_columnconfigure(0, weight=1)
        
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(header_frame, text=PANEL_TITLE, font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        
        set_names_button = ttk.Button(header_frame, text="Set Names", command=self.controller.set_custom_workspace_names)
        set_names_button.grid(row=0, column=1, sticky="e", padx=5)

        ttk.Button(header_frame, text="🔄", width=3, command=self.update_workspaces).grid(row=0, column=2, sticky="e")

        # Scrollable frame for workspaces
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.workspace_frame = ttk.Frame(canvas)
        
        self.workspace_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.workspace_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        
        self.grid_rowconfigure(1, weight=1)
        self.workspace_frame.grid_columnconfigure(0, weight=1)

        if self.controller.method != "none": self.update_workspaces()
        else: self._display_error_state("No workspace manager found.\nInstall: sudo apt install wmctrl")

    def update_workspaces(self):
        if not self._is_running or not self.winfo_exists(): 
            return
        
        workspaces = self.controller.get_workspaces()
        windows_by_workspace = self.controller.get_windows()
        
        if workspaces is None:
            self._display_error_state("Could not fetch workspaces.")
            return
        elif not workspaces:
            if not self.workspace_frame.winfo_children():
                ttk.Label(self.workspace_frame, text="No workspaces found.").grid(row=0, column=0, sticky="ew", pady=2)
            return
        
        # Build a unique key for current state
        current_state = []
        for ws in workspaces:
            windows = windows_by_workspace.get(ws["index"], [])
            ws_key = (ws["index"], ws["name"], ws["active"], tuple((w['id'], w['app'], w['title']) for w in windows))
            current_state.append(ws_key)
        
        # Only rebuild UI if state changed
        if hasattr(self, '_last_state') and self._last_state == current_state:
            self.after(5000, self.update_workspaces)
            return
        
        self._last_state = current_state
        
        # Clear and rebuild
        for widget in self.workspace_frame.winfo_children():
            widget.destroy()
        
        row = 0
        for ws in workspaces:
            # Workspace button
            windows = windows_by_workspace.get(ws["index"], [])
            window_count = len(windows)
            
            btn_text = f"{'● ' if ws['active'] else '○ '}{ws['name']}"
            if window_count > 0:
                btn_text += f" ({window_count})"
            
            style = "Active.TButton" if ws["active"] else "TButton"
            btn = ttk.Button(
                self.workspace_frame,
                text=btn_text,
                style=style,
                command=lambda idx=ws["index"]: self._on_workspace_click(idx)
            )
            btn.grid(row=row, column=0, sticky="ew", pady=2)
            
            row += 1
            
            # Show windows
            if windows:
                window_frame = ttk.Frame(self.workspace_frame)
                window_frame.grid(row=row, column=0, sticky="ew", padx=(15, 0), pady=(0, 5))
                window_frame.grid_columnconfigure(0, weight=1)
                
                for i, win in enumerate(windows):
                    # Truncate long titles
                    title = win['title'][:45] + "..." if len(win['title']) > 45 else win['title']
                    
                    # Create clickable frame for entire window item
                    win_item_frame = tk.Frame(
                        window_frame,
                        bg="#f0f0f0",
                        relief="raised",
                        bd=1,
                        cursor="hand2"
                    )
                    win_item_frame.grid(row=i, column=0, sticky="ew", pady=1)
                    win_item_frame.grid_columnconfigure(0, weight=1)
                    
                    # App name (bold)
                    app_label = tk.Label(
                        win_item_frame,
                        text=win['app'],
                        font=("Arial", 9, "bold"),
                        anchor="w",
                        bg="#f0f0f0",
                        fg="#000000"
                    )
                    app_label.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 0))
                    app_label.bind("<Button-1>", lambda e, wid=win['id']: self._on_window_click(wid))
                    
                    # Window title (regular)
                    title_label = tk.Label(
                        win_item_frame,
                        text=title,
                        font=("Arial", 8),
                        anchor="w",
                        bg="#f0f0f0",
                        fg="#555555"
                    )
                    title_label.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
                    title_label.bind("<Button-1>", lambda e, wid=win['id']: self._on_window_click(wid))
                    
                    # Make entire frame clickable
                    win_item_frame.bind("<Button-1>", lambda e, wid=win['id']: self._on_window_click(wid))
                
                row += 1
        
        self.after(5000, self.update_workspaces)

    def _toggle_workspace(self, index):
        """Toggle expanded state for a workspace."""
        if index in self.expanded_workspaces:
            self.expanded_workspaces.remove(index)
        else:
            self.expanded_workspaces.add(index)
        self.update_workspaces()

    def _on_workspace_click(self, index):
        self.controller.switch_to_workspace(index)
        self.after(100, self.update_workspaces)

    def _on_window_click(self, window_id):
        """Focus a specific window when clicked."""
        self.controller.focus_window(window_id)
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
    style.configure("Window.TButton", font=("Arial", 9), foreground="#555555")
    style.configure("Error.TLabel", foreground="red", font=("Arial", 9))
    panel = Navigation(parent, launcher=launcher)
    return panel
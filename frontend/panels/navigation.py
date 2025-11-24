"""
Navigation Panel (for GNOME 46+)

This panel provides a UI for viewing and switching between GNOME workspaces.
It communicates directly with the GNOME Shell desktop environment via its D-Bus API, 
providing a more reliable and native experience than legacy command-line tools.

Key Features:
- Fetches and displays a list of current workspaces.
- Indicates the currently active workspace.
- Allows switching to a different workspace by clicking a button.
- Periodically refreshes to stay in sync with the desktop environment.
- Gracefully handles D-Bus connection errors.
"""

import tkinter as tk
from tkinter import ttk
import subprocess
import re

# --- Constants ---
PANEL_TITLE = "Workspaces"

# --- Logging ---

def log(launcher, message, level="info"):
    """A centralized logging helper."""
    log_message = f"[Navigation] {message}"
    print(log_message)  # For console debugging
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(PANEL_TITLE, message)

# --- Workspace Controller ---

class GnomeWorkspaceController:
    """Handles all workspace operations with GNOME Shell."""
    
    def __init__(self, launcher):
        self.launcher = launcher
        self.method = None
        self.working_js_pattern = None
        self._detect_method()
        log(self.launcher, f"Using method: {self.method}")
    
    def _detect_method(self):
        """Detect which method to use for workspace management."""
        # Try to find a working JavaScript pattern first
        js_variants = [
            "global.display.get_workspace_manager().get_n_workspaces()",
            "global.workspace_manager.get_n_workspaces()",
            "global.screen.get_n_workspaces()"
        ]
        
        for js_code in js_variants:
            try:
                result = subprocess.run(
                    ["gdbus", "call", "--session",
                     "--dest", "org.gnome.Shell",
                     "--object-path", "/org/gnome/Shell",
                     "--method", "org.gnome.Shell.Eval",
                     js_code],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0 and "(true," in result.stdout:
                    count_match = re.search(r"'(\d+)'", result.stdout)
                    if count_match:
                        self.method = "gdbus"
                        self.working_js_pattern = js_code.replace("get_n_workspaces()", "")
                        log(self.launcher, f"✓ Using JavaScript API: {js_code}")
                        return
            except Exception:
                continue
        
        # If gdbus didn't work, try wmctrl
        try:
            result = subprocess.run(["which", "wmctrl"], capture_output=True, timeout=1)
            if result.returncode == 0:
                self.method = "wmctrl"
                log(self.launcher, "✓ Using wmctrl as fallback")
                return
        except Exception:
            pass
        
        self.method = "none"
        log(self.launcher, "✗ No working workspace manager found", "error")
    
    def get_workspaces(self):
        """Fetches the list of workspaces."""
        if self.method == "gdbus":
            return self._get_workspaces_gdbus()
        elif self.method == "wmctrl":
            return self._get_workspaces_wmctrl()
        else:
            return None
    
    def _get_workspaces_gdbus(self):
        """Get workspaces using gdbus and the detected working JavaScript pattern."""
        if not self.working_js_pattern:
            return self._get_workspaces_wmctrl()
        
        try:
            # Get workspace count using the known working pattern
            result = subprocess.run(
                ["gdbus", "call", "--session",
                 "--dest", "org.gnome.Shell",
                 "--object-path", "/org/gnome/Shell",
                 "--method", "org.gnome.Shell.Eval",
                 self.working_js_pattern + "get_n_workspaces()"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0 or "(true," not in result.stdout:
                return self._get_workspaces_wmctrl()
            
            count_match = re.search(r"'(\d+)'", result.stdout)
            if not count_match:
                return self._get_workspaces_wmctrl()
            
            workspace_count = int(count_match.group(1))
            
            # Get active workspace using the same pattern
            result = subprocess.run(
                ["gdbus", "call", "--session",
                 "--dest", "org.gnome.Shell",
                 "--object-path", "/org/gnome/Shell",
                 "--method", "org.gnome.Shell.Eval",
                 self.working_js_pattern + "get_active_workspace_index()"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            active_index = 0
            if result.returncode == 0 and "(true," in result.stdout:
                active_match = re.search(r"'(\d+)'", result.stdout)
                if active_match:
                    active_index = int(active_match.group(1))
            
            # Build workspace list
            workspaces = []
            for i in range(workspace_count):
                workspaces.append({
                    "name": f"Workspace {i + 1}",
                    "index": i,
                    "active": i == active_index
                })
            
            return workspaces
            
        except subprocess.TimeoutExpired:
            return self._get_workspaces_wmctrl()
        except Exception as e:
            log(self.launcher, f"Error getting workspaces: {e}", "error")
            return self._get_workspaces_wmctrl()
    
    def _get_workspaces_wmctrl(self):
        """Get workspaces using wmctrl (fallback method)."""
        try:
            result = subprocess.run(
                ["wmctrl", "-d"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                return None
            
            workspaces = []
            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 2:
                    index = int(parts[0])
                    active = parts[1] == '*'
                    # Try to get workspace name if available
                    name = f"Workspace {index + 1}"
                    if len(parts) >= 9:
                        name = ' '.join(parts[8:])
                    
                    workspaces.append({
                        "name": name,
                        "index": index,
                        "active": active
                    })
            
            return workspaces
            
        except Exception as e:
            log(self.launcher, f"Error getting workspaces via wmctrl: {e}", "error")
            return None
    
    def switch_to_workspace(self, index):
        """Switch to a specific workspace."""
        if self.method == "gdbus":
            self._switch_workspace_gdbus(index)
        elif self.method == "wmctrl":
            self._switch_workspace_wmctrl(index)
    
    def _switch_workspace_gdbus(self, index):
        """Switch workspace using gdbus."""
        if not self.working_js_pattern:
            self._switch_workspace_wmctrl(index)
            return
        
        try:
            switch_js = (
                f"{self.working_js_pattern}get_workspace_by_index({index})"
                f".activate(global.get_current_time())"
            )
            
            result = subprocess.run(
                ["gdbus", "call", "--session",
                 "--dest", "org.gnome.Shell",
                 "--object-path", "/org/gnome/Shell",
                 "--method", "org.gnome.Shell.Eval",
                 switch_js],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0 and "(true," in result.stdout:
                log(self.launcher, f"Switched to workspace {index + 1}")
            else:
                self._switch_workspace_wmctrl(index)
                
        except Exception as e:
            log(self.launcher, f"Error switching workspace: {e}", "error")
            self._switch_workspace_wmctrl(index)
    
    def _switch_workspace_wmctrl(self, index):
        """Switch workspace using wmctrl."""
        try:
            subprocess.run(["wmctrl", "-s", str(index)], timeout=1)
            log(self.launcher, f"Switched to workspace {index + 1}")
        except Exception as e:
            log(self.launcher, f"Error switching workspace: {e}", "error")

# --- UI Panel ---

class Navigation(ttk.Frame):
    def __init__(self, parent, launcher=None):
        super().__init__(parent, padding="10")
        self.launcher = launcher
        self._is_running = True
        self.controller = GnomeWorkspaceController(launcher)

        self.grid_columnconfigure(0, weight=1)
        
        # Header
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(
            header_frame, 
            text=PANEL_TITLE, 
            font=("Arial", 12, "bold")
        ).grid(row=0, column=0, sticky="w")
        
        # Refresh button
        ttk.Button(
            header_frame,
            text="🔄",
            width=3,
            command=self.update_workspaces
        ).grid(row=0, column=1, sticky="e")

        # Workspace display area
        self.workspace_frame = ttk.Frame(self)
        self.workspace_frame.grid(row=1, column=0, sticky="nsew")
        self.workspace_frame.grid_columnconfigure(0, weight=1)

        # Initial update
        if self.controller.method != "none":
            self.update_workspaces()
        else:
            self._display_error_state(
                "No workspace manager found.\n"
                "Install: sudo apt install wmctrl"
            )

    def update_workspaces(self):
        """Update the workspace display."""
        if not self._is_running or not self.winfo_exists():
            return

        workspaces = self.controller.get_workspaces()
        
        # Get existing buttons to avoid flickering
        existing_buttons = self.workspace_frame.winfo_children()
        
        if workspaces is None:
            # Only clear and show error if we don't have existing buttons
            if not existing_buttons:
                self._display_error_state("Could not fetch workspaces.")
        elif not workspaces:
            # Only clear and show message if we don't have existing buttons
            if not existing_buttons:
                ttk.Label(
                    self.workspace_frame, 
                    text="No workspaces found."
                ).grid(row=0, column=0, sticky="ew", pady=2)
        else:
            # Update existing buttons or create new ones
            # This prevents flickering by reusing widgets when possible
            for i, ws in enumerate(workspaces):
                btn_text = f"{'● ' if ws['active'] else '○ '}{ws['name']}"
                style = "Active.TButton" if ws["active"] else "TButton"
                
                # Update existing button if it exists
                if i < len(existing_buttons) and isinstance(existing_buttons[i], ttk.Button):
                    existing_buttons[i].configure(text=btn_text, style=style)
                else:
                    # Create new button
                    btn = ttk.Button(
                        self.workspace_frame,
                        text=btn_text,
                        style=style,
                        command=lambda idx=ws["index"]: self._on_workspace_click(idx)
                    )
                    btn.grid(row=ws["index"], column=0, sticky="ew", pady=2)
            
            # Remove extra buttons if workspace count decreased
            if len(existing_buttons) > len(workspaces):
                for widget in existing_buttons[len(workspaces):]:
                    widget.destroy()
        
        # Schedule next update (5 seconds)
        self.after(5000, self.update_workspaces)

    def _on_workspace_click(self, index):
        """Handle workspace button click."""
        self.controller.switch_to_workspace(index)
        # Immediate visual feedback
        self.after(100, self.update_workspaces)

    def _display_error_state(self, message):
        """Display an error message in the panel."""
        for widget in self.workspace_frame.winfo_children():
            widget.destroy()
        
        error_label = ttk.Label(
            self.workspace_frame,
            text=message,
            style="Error.TLabel",
            justify="center"
        )
        error_label.grid(row=0, column=0, sticky="ew", pady=10)

    def stop(self):
        """Stop the update loop."""
        log(self.launcher, "Stopping navigation panel update loop.")
        self._is_running = False

# --- Factory Function ---

def create_panel(parent, launcher):
    """Factory function to create and configure the navigation panel."""
    style = ttk.Style()
    
    # Configure button styles
    style.configure(
        "Active.TButton",
        font=("Arial", 10, "bold"),
        foreground="#0078d4"
    )
    
    style.configure(
        "Error.TLabel",
        foreground="red",
        font=("Arial", 9)
    )
    
    panel = Navigation(parent, launcher=launcher)
    return panel
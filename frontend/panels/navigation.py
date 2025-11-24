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
import dbus

# --- Constants ---
PANEL_TITLE = "Workspaces"
DBUS_INTERFACE = 'org.gnome.Shell'
DBUS_PATH = '/org/gnome/Shell'

# --- Logging ---

def log(launcher, message, level="info"):
    """A centralized logging helper.

    Sends log messages to the application's global log panel and prints to the console.

    Args:
        launcher: The main application instance, used to access the global logger.
        message (str): The message to log.
        level (str): The severity of the message (e.g., 'info', 'error').
    """
    log_message = f"[Navigation] {message}"
    print(log_message) # For console debugging
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(PANEL_TITLE, message)

# --- D-Bus Controller ---

class GnomeWorkspaceController:
    """Handles all D-Bus communication with the GNOME Shell.
    
    This class abstracts the complexities of the D-Bus API, providing simple methods
    for the UI to call.
    """
    def __init__(self, launcher):
        """Initializes the D-Bus connection."""
        self.launcher = launcher
        self.shell = None
        try:
            # Connect to the user's session bus (the standard bus for desktop apps)
            session_bus = dbus.SessionBus()
            # Get a proxy object for the GNOME Shell
            shell_obj = session_bus.get_object(DBUS_INTERFACE, DBUS_PATH)
            # Create an interface to interact with the shell's methods
            self.shell = dbus.Interface(shell_obj, DBUS_INTERFACE)
            log(self.launcher, "Successfully connected to GNOME Shell via D-Bus.")
        except dbus.exceptions.DBusException as e:
            log(self.launcher, f"CRITICAL: Could not connect to GNOME Shell D-Bus. Is this a GNOME desktop? Error: {e}", level="error")

    def get_workspaces(self):
        """Fetches the list of workspaces from GNOME Shell.
        
        Returns:
            list: A list of dicts, where each dict represents a workspace.
                  Returns None if a D-Bus error occurs.
        """
        if not self.shell:
            return None
        try:
            # The Eval method executes a JavaScript string within the GNOME Shell process.
            # This is a powerful way to access internal GNOME state.
            workspace_names_js = "global.workspace_manager.workspace_names"
            active_index_js = "global.workspace_manager.get_active_workspace().index()"
            
            # The result from Eval is a GVariant, which dbus-python converts.
            # We get a tuple: (success_flag, json_string_result)
            _, names_json = self.shell.Eval(workspace_names_js)
            _, active_json = self.shell.Eval(active_index_js)
            
            # dbus-python may return a list of strings directly or json
            workspace_names = names_json if isinstance(names_json, list) else eval(names_json)
            active_index = active_json if isinstance(active_json, int) else eval(active_json)

            return [
                {"name": name, "index": i, "active": i == active_index}
                for i, name in enumerate(workspace_names)
            ]
        except dbus.exceptions.DBusException as e:
            log(self.launcher, f"D-Bus error while fetching workspaces: {e}", level="error")
            return None # Signal to the caller that an error occurred

    def switch_to_workspace(self, index):
        """Sends a command to GNOME Shell to switch to a specific workspace."""
        if not self.shell:
            log(self.launcher, "Cannot switch workspace, no D-Bus connection.", level="error")
            return
        try:
            # Construct and execute JS to activate the workspace by its index.
            switch_js = f"global.workspace_manager.get_workspace_by_index({index}).activate(global.get_current_time())"
            self.shell.Eval(switch_js)
            log(self.launcher, f"Switched to workspace {index}.")
        except dbus.exceptions.DBusException as e:
            log(self.launcher, f"Failed to switch workspace: {e}", level="error")

# --- UI Panel ---

class Navigation(ttk.Frame):
    """The UI panel for workspace navigation."""
    def __init__(self, parent, launcher=None):
        super().__init__(parent, padding="10")
        self.launcher = launcher
        self._is_running = True # Flag to control the update loop
        self.controller = GnomeWorkspaceController(launcher)

        self.grid_columnconfigure(0, weight=1)
        ttk.Label(self, text=PANEL_TITLE, font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.workspace_frame = ttk.Frame(self)
        self.workspace_frame.grid(row=1, column=0, sticky="nsew")

        if self.controller.shell:
            # Start the periodic update loop
            self.update_workspaces()
        else:
            self._display_error_state("GNOME D-Bus connection failed.")

    def update_workspaces(self):
        """Periodically refreshes the list of workspaces in the UI.
        
        This method is the heart of the panel's update loop. It fetches data,
        rebuilds the UI, and schedules itself to run again.
        """
        # Stop the loop if the panel is being destroyed
        if not self._is_running or not self.winfo_exists():
            return

        workspaces = self.controller.get_workspaces()
        
        # Clear any existing widgets from the frame
        for widget in self.workspace_frame.winfo_children():
            widget.destroy()

        if workspaces is None:
            # This indicates a D-Bus error occurred during the fetch
            self._display_error_state("Lost connection to GNOME Shell.")
        else:
            # Rebuild the workspace buttons
            for ws in workspaces:
                style = "Active.TButton" if ws["active"] else "TButton"
                btn = ttk.Button(
                    self.workspace_frame,
                    text=ws["name"],
                    style=style,
                    command=lambda index=ws["index"]: self.controller.switch_to_workspace(index)
                )
                btn.grid(row=ws["index"], column=0, sticky="ew", pady=2)
        
        # Reschedule the next update
        self.after(2000, self.update_workspaces)

    def _display_error_state(self, message):
        """Clears the panel and displays a single error message."""
        for widget in self.workspace_frame.winfo_children():
            widget.destroy()
        ttk.Label(self.workspace_frame, text=message, style="Error.TLabel").pack()

    def stop(self):
        """Cleanly stops the panel's update loop before the widget is destroyed."""
        log(self.launcher, "Stopping navigation panel update loop.")
        self._is_running = False

# --- Factory Function ---

def create_panel(parent, launcher):
    """Creates and configures the Navigation panel and its styles."""
    # Define custom styles for the panel's widgets
    style = ttk.Style()
    style.configure("Active.TButton", font=("Arial", 10, "bold"), foreground="#ffffff", background="#0078d4")
    style.configure("Error.TLabel", foreground="red")
    
    panel = Navigation(parent, launcher=launcher)
    return panel

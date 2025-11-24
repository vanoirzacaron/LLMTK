"""
This is a boilerplate for creating a new tab in the LLM Services Launcher.

To use this template:
1.  Copy this file to the 'frontend/tabs/' directory.
2.  Rename the file to something descriptive (e.g., 'my_feature_tab.py').
3.  Search and replace "Boilerplate" with the name of your feature (e.g., "MyFeature").
4.  Update the constants in the '--- CONFIGURATION ---' section.
5.  Implement your service-specific logic in the 'start_service' function.
"""

import tkinter as tk
from tkinter import ttk
import os
import signal
from pathlib import Path
from utils import (create_log_widget, run_command, create_monitor_frame, 
                   get_log_file_path, load_logs, clear_log_file_and_widget)

# --- CONFIGURATION -------------------------------------------------------------------
# TODO: Update these constants for your specific service.

# The title of the tab in the UI.
TAB_TITLE = "Boilerplate"

# A unique identifier for the service. Used for process management and logging.
SERVICE_ID = "BoilerplateService"

# The command to execute when the 'Start' button is pressed.
# - This is a dummy command that prints numbers every second for demonstration.
# - Use 'python3 -u' for unbuffered output to see logs in real-time.
COMMAND_TO_RUN = 'python3 -u -c "import time; print(\'Boilerplate service started...\'); [print(f\'Processing item {i}...\') or time.sleep(1) for i in range(1000)]"'

# Optional: Set a specific working directory for the command.
# If None, it defaults to the directory where the main script is run.
WORKING_DIRECTORY = None

# --- LOGGING ------------------------------------------------------------------------

# The name of the log file where output will be persistently stored.
LOG_FILE = get_log_file_path(f"{SERVICE_ID}.log")

def log(message, log_widget, launcher):
    """A centralized logging function.

    This function handles logging to multiple destinations:
    1.  The console (for debugging).
    2.  The log widget in the tab's UI.
    3.  A persistent log file.
    4.  The global log panel.
    """
    print(f"[{SERVICE_ID}] {message}")  # Console log
    
    # Update the UI widget
    if log_widget:
        log_widget.config(state=tk.NORMAL)
        log_widget.insert(tk.END, message + '\n')
        log_widget.see(tk.END)
        log_widget.config(state=tk.DISABLED)
    
    # Write to the persistent log file
    with open(LOG_FILE, "a") as f:
        f.write(message + '\n')
        
    # Send to global log panel
    if launcher and launcher.global_log_panel:
        launcher.log_to_global(TAB_TITLE, message)

# --- UI AND LOGIC -------------------------------------------------------------------

def create_tab(notebook, launcher):
    """Creates and configures the UI for the tab."""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text=TAB_TITLE)

    # --- Layout Configuration ---
    tab.columnconfigure(0, weight=1)  # Main content column
    tab.columnconfigure(1, weight=0)  # Monitor sidebar (fixed width)
    tab.rowconfigure(2, weight=1)     # Log area row (expands vertically)

    # --- UI Elements ---
    left_frame = ttk.Frame(tab)
    left_frame.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))
    left_frame.columnconfigure(0, weight=1)
    left_frame.rowconfigure(2, weight=1)

    # 1. Information Section
    info_frame = ttk.LabelFrame(left_frame, text="Service Information", padding="10")
    info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ttk.Label(info_frame, text=f"Service: {TAB_TITLE}").pack(anchor="w")
    ttk.Label(info_frame, text=f"Log File: {LOG_FILE}").pack(anchor="w")

    # 2. Controls Section
    button_frame = ttk.Frame(left_frame)
    button_frame.grid(row=1, column=0, pady=(0, 10), sticky="w")

    ui_controls = {
        "start": ttk.Button(button_frame, text="▶ Start", width=12),
        "stop": ttk.Button(button_frame, text="⏹ Stop", state=tk.DISABLED, width=12),
        "kill": ttk.Button(button_frame, text="⚠️ Kill", state=tk.DISABLED, width=12),
        "clear": ttk.Button(button_frame, text="🗑️ Clear Log", width=12)
    }
    
    ui_controls["start"].pack(side="left", padx=5)
    ui_controls["stop"].pack(side="left", padx=5)
    ui_controls["kill"].pack(side="left", padx=5)
    ui_controls["clear"].pack(side="left", padx=5)

    # 3. Log Section
    log_frame = ttk.LabelFrame(left_frame, text="Log Output", padding="5")
    log_frame.grid(row=2, column=0, sticky="nsew")
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    log_widget = create_log_widget(log_frame)
    log_widget.grid(row=0, column=0, sticky="nsew")

    # --- Monitor Section (Right Sidebar) ---
    monitor_frame = create_monitor_frame(tab, SERVICE_ID, launcher)
    monitor_frame.grid(row=0, column=1, sticky="new")

    # --- Event Handlers and Callbacks ---
    def on_service_exit(return_code):
        """Callback function for when the service process exits."""
        log(f"Service process exited with return code: {return_code}", log_widget, launcher)
        ui_controls["start"].config(state=tk.NORMAL)
        ui_controls["stop"].config(state=tk.DISABLED)
        ui_controls["kill"].config(state=tk.DISABLED)

    # --- Bind Commands to Buttons ---
    ui_controls["start"].config(command=lambda:
        start_service(launcher, log_widget, ui_controls, on_service_exit))
    
    ui_controls["stop"].config(command=lambda:
        stop_service(launcher, log_widget))

    ui_controls["kill"].config(command=lambda:
        kill_service(launcher, log_widget))

    ui_controls["clear"].config(command=lambda:
        clear_log_file_and_widget(log_widget, LOG_FILE, lambda m: log(m, log_widget, launcher)))

    # --- Final Initialization ---
    load_logs(log_widget, LOG_FILE) # Load previous logs on startup
    log(f"{TAB_TITLE} tab loaded.", log_widget, launcher)

def start_service(launcher, log_widget, ui_controls, on_exit_callback):
    """Handles the logic for starting the service."""
    log("Attempting to start service...", log_widget, launcher)
    ui_controls["start"].config(state=tk.DISABLED)
    ui_controls["stop"].config(state=tk.NORMAL)
    ui_controls["kill"].config(state=tk.NORMAL)
    
    # The core command execution.
    run_command(
        launcher=launcher,
        service_id=SERVICE_ID,
        command=COMMAND_TO_RUN,
        log_widget=log_widget,
        on_exit=on_exit_callback,
        cwd=WORKING_DIRECTORY
    )

def stop_service(launcher, log_widget):
    """Sends a graceful SIGTERM signal to the service process."""
    if SERVICE_ID in launcher.processes:
        log("Sending SIGTERM to gracefully stop the service...", log_widget, launcher)
        try:
            # Use os.killpg to terminate the entire process group
            os.killpg(os.getpgid(launcher.processes[SERVICE_ID].pid), signal.SIGTERM)
        except Exception as e:
            log(f"Error during graceful stop: {e}", log_widget, launcher)
            # Fallback to simple terminate if process group fails
            try: launcher.processes[SERVICE_ID].terminate()
            except: pass

def kill_service(launcher, log_widget):
    """Forcibly kills the service process with SIGKILL."""
    if SERVICE_ID in launcher.processes:
        log("⚠️ Sending SIGKILL to forcefully terminate the service...", log_widget, launcher)
        try:
            os.killpg(os.getpgid(launcher.processes[SERVICE_ID].pid), signal.SIGKILL)
        except Exception as e:
            log(f"Error during force kill: {e}", log_widget, launcher)
            # Fallback to simple kill
            try: launcher.processes[SERVICE_ID].kill()
            except: pass

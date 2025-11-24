"""
OpenHands Tab

This tab provides a user interface for managing the OpenHands agent, a 
long-running background service. It allows the user to start, stop, and 
force-kill the agent, while also providing a real-time log view and easy 
access to the agent's web documentation.

Key Features:
- Process control (Start, Stop, Kill) for the agent.
- Pre-start cleanup of old Docker containers.
- Real-time log display within the tab.
- A clickable link to the agent's documentation, with error handling.
- System resource monitoring for the agent process.
- Centralized logging for all actions and errors.
"""

import tkinter as tk
from tkinter import ttk
import os
import signal
import subprocess
import webbrowser
import shutil
from pathlib import Path

# Assuming utils provides these helper functions. If not, they would need to be defined.
from utils import create_log_widget, log_to_widget, clear_log, run_command, create_monitor_frame

# --- Configuration ---
# These values are centralized for easy modification.
TAB_TITLE = "OpenHands"
# Path to the OpenHands project. IMPORTANT: This may need to be adjusted based on the user's setup.
AGENT_WORKING_DIR = "../OpenHands"
# The command to start the agent. It will be run from the AGENT_WORKING_DIR.
AGENT_START_COMMAND = "uvx --python 3.12 openhands serve"
# The web URL for the agent's documentation/frontend.
AGENT_DOCS_URL = "http://localhost:3000"

# --- Logging Utility ---
def log(launcher, widget, message, level="info"):
    """A centralized logging helper for this tab.

    Args:
        launcher: The main application instance to access the global logger.
        widget: The local log widget to display the message.
        message (str): The log message.
        level (str): The log level ('info', 'warn', 'error').
    """
    log_message = f"[{TAB_TITLE}] {message}"
    print(log_message) # Always print to console for debugging.
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(TAB_TITLE, message)
    if widget:
        log_to_widget(widget, message)

# --- Core Actions ---

def open_docs_url(launcher, widget):
    """Safely opens the agent's documentation URL in a web browser."""
    log(launcher, widget, f"Attempting to open documentation at: {AGENT_DOCS_URL}")
    try:
        if not webbrowser.open(AGENT_DOCS_URL):
            raise webbrowser.Error("No browser found to open URL.")
        log(launcher, widget, "Successfully opened documentation in browser.")
    except webbrowser.Error as e:
        error_msg = f"Could not open web browser: {e}"
        log(launcher, widget, error_msg, "error")

def start_service(launcher, log_fn, widget, buttons):
    """Validates environment and starts the OpenHands agent process."""
    start_btn, stop_btn, kill_btn = buttons

    # 1. Check if the working directory exists
    agent_path = Path(AGENT_WORKING_DIR)
    if not agent_path.is_dir():
        log_fn(f"Error: Working directory not found at '{agent_path.resolve()}'. Cannot start agent.", "error")
        return

    # 2. Clean up any stale Docker containers before starting.
    if shutil.which("docker"):
        log_fn("🧹 Cleaning up any stale 'openhands-app' containers...")
        try:
            # This runs 'docker rm -f openhands-app' to remove the container if it exists.
            subprocess.run(
                ["docker", "rm", "-f", "openhands-app"], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                check=False, # Don't raise an exception if the container doesn't exist.
                cwd=str(agent_path)
            )
            log_fn("✅ Docker cleanup complete.")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            log_fn(f"⚠️ Warning: Docker container cleanup failed: {e}", "warn")
    else:
        log_fn("docker command not found, skipping container cleanup.", "warn")

    # 3. Update UI and launch the process using the utility function.
    start_btn.config(state=tk.DISABLED)
    stop_btn.config(state=tk.NORMAL)
    kill_btn.config(state=tk.NORMAL)
    
    log_fn(f"Starting agent with command: '{AGENT_START_COMMAND}' in '{agent_path.resolve()}'")
    run_command(launcher, TAB_TITLE, AGENT_START_COMMAND, log_fn, widget, 
                start_btn, stop_btn, kill_btn, cwd=str(agent_path))

def stop_service(launcher, log_fn):
    """Sends a graceful SIGTERM signal to the agent process group."""
    if TAB_TITLE not in launcher.processes:
        log_fn("Agent process not found. Nothing to stop.", "warn")
        return

    log_fn("Attempting graceful shutdown (sending SIGTERM)...")
    try:
        # Get the process group ID (pgid) to terminate the entire process tree.
        pgid = os.getpgid(launcher.processes[TAB_TITLE].pid)
        os.killpg(pgid, signal.SIGTERM)
        log_fn("SIGTERM signal sent to process group.")
    except ProcessLookupError:
        log_fn("Process already terminated.", "warn")
        launcher.processes.pop(TAB_TITLE, None)
    except Exception as e:
        log_fn(f"Error during graceful stop: {e}. Consider a force kill.", "error")

def kill_service(launcher, log_fn):
    """Forcibly terminates the agent process group with SIGKILL."""
    if TAB_TITLE not in launcher.processes:
        log_fn("Agent process not found. Nothing to kill.", "warn")
        return

    log_fn("⚠️ Forcibly terminating process (sending SIGKILL)...")
    try:
        pgid = os.getpgid(launcher.processes[TAB_TITLE].pid)
        os.killpg(pgid, signal.SIGKILL)
        log_fn("SIGKILL signal sent. The process has been terminated.")
    except ProcessLookupError:
        log_fn("Process already terminated.", "warn")
        launcher.processes.pop(TAB_TITLE, None)
    except Exception as e:
        log_fn(f"Error during force kill: {e}", "error")

# --- UI Setup ---
def create_tab(notebook, launcher):
    """Creates and lays out the OpenHands tab and its widgets."""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text=TAB_TITLE)
    
    # --- Layout Configuration ---
    tab.columnconfigure(0, weight=1) # Main content column
    tab.columnconfigure(1, weight=0) # Monitor column (fixed width)
    tab.rowconfigure(2, weight=1)    # Log area row
    
    # --- Left Frame (Info, Controls, Logs) ---
    left_frame = ttk.Frame(tab)
    left_frame.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))
    left_frame.columnconfigure(0, weight=1)
    left_frame.rowconfigure(2, weight=1)

    # --- Log Widget ---
    log_frame = ttk.LabelFrame(left_frame, text="Agent Log", padding="5")
    log_frame.grid(row=2, column=0, sticky="nsew")
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    log_widget = create_log_widget(log_frame)
    log_widget.grid(row=0, column=0, sticky="nsew")

    # Create a specific logger instance for this tab
    log_fn = lambda message, level="info": log(launcher, log_widget, message, level)

    # --- Info Section ---
    info_frame = ttk.LabelFrame(left_frame, text="Agent Information", padding="10")
    info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ttk.Label(info_frame, text="Framework: OpenHands Agent").pack(anchor="w")
    # Clickable URL label
    url_label = ttk.Label(info_frame, text=AGENT_DOCS_URL, cursor="hand2", foreground="blue")
    url_label.bind("<Button-1>", lambda e: open_docs_url(launcher, log_widget))
    url_label.pack(anchor="w")

    # --- Control Buttons ---
    button_frame = ttk.Frame(left_frame)
    button_frame.grid(row=1, column=0, pady=(0, 10))
    
    start_btn = ttk.Button(button_frame, text="▶ Start Agent", width=15)
    stop_btn = ttk.Button(button_frame, text="⏹ Stop Agent", state=tk.DISABLED, width=15)
    kill_btn = ttk.Button(button_frame, text="⚠️ Force Kill", state=tk.DISABLED, width=15)
    clear_btn = ttk.Button(button_frame, text="🗑️ Clear Log", width=12)

    start_btn.pack(side=tk.LEFT, padx=5)
    stop_btn.pack(side=tk.LEFT, padx=5)
    kill_btn.pack(side=tk.LEFT, padx=5)
    clear_btn.pack(side=tk.LEFT, padx=5)

    # Button commands
    buttons = (start_btn, stop_btn, kill_btn)
    start_btn.config(command=lambda: start_service(launcher, log_fn, log_widget, buttons))
    stop_btn.config(command=lambda: stop_service(launcher, log_fn))
    kill_btn.config(command=lambda: kill_service(launcher, log_fn))
    clear_btn.config(command=lambda: clear_log(log_widget))
    
    # --- Right Frame (System Monitor) ---
    monitor_frame = create_monitor_frame(tab, TAB_TITLE, launcher)
    monitor_frame.grid(row=0, column=1, sticky="new")
    
    log_fn("OpenHands tab initialized and ready.")

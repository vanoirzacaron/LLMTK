"""
vLLM Server Tab

This tab provides a user interface for managing a local vLLM (Very Large Language Model)
server. It allows the user to start and stop the server, monitor its resource usage,
and view its real-time logs.

Key Features:
- Simple Start/Stop/Kill controls for the vLLM server process.
- Centralized and well-documented configuration for server parameters (model, host, port, etc.).
- Pre-start validation to ensure the vLLM directory and virtual environment are correctly set up.
- Robust process management using process groups to ensure clean shutdowns.
- Real-time log display and system resource monitoring.
"""

import tkinter as tk
from tkinter import ttk
import os
import signal
from pathlib import Path

# Assuming utils provides these helper functions. If not, they would need to be defined.
from utils import create_log_widget, log_to_widget, clear_log, run_command, create_monitor_frame

# --- Configuration ---
# All server settings are centralized here for easy modification.
# Users on different systems can easily adjust these paths and parameters.
TAB_TITLE = "vLLM Server"

# --- Path and Environment ---
# IMPORTANT: This is the main directory where vLLM is installed.
VLLM_INSTALL_DIR = Path.home() / "LLMTK" / "vllm"

# --- Server & Model Parameters ---
MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
HOST = "0.0.0.0"
PORT = 8000
API_KEY = "sk-vllm-local-abc123xyz789-qwen-coder"
QUANTIZATION = "awq_marlin"
GPU_MEMORY_UTILIZATION = 0.65
MAX_MODEL_LEN = 8192
DTYPE = "float16"

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
    print(log_message)
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(TAB_TITLE, message)
    if widget:
        log_to_widget(widget, message)

# --- Core Actions ---

def start_service(launcher, log_fn, widget, buttons):
    """Performs pre-start checks and then launches the vLLM server.

    This function validates the necessary directories and scripts before attempting
    to start the server, providing clear error messages if a check fails.
    """
    start_btn, stop_btn, kill_btn = buttons

    # 1. Validate the installation directory.
    if not VLLM_INSTALL_DIR.is_dir():
        log_fn(f"Error: vLLM installation directory not found at '{VLLM_INSTALL_DIR}'.", "error")
        return

    # 2. Validate the virtual environment.
    venv_path = VLLM_INSTALL_DIR / ".venv"
    if not venv_path.is_dir():
        log_fn(f"Error: Python virtual environment not found inside '{VLLM_INSTALL_DIR}'.", "error")
        return

    # 3. Validate the activate script.
    activate_script = venv_path / "bin" / "activate"
    if not activate_script.is_file():
        log_fn(f"Error: 'activate' script not found in '{activate_script.parent}'.", "error")
        return

    # 4. Construct the full command to be executed.
    # This is a multi-line shell command that first activates the virtual environment
    # and then starts the vLLM server with all specified parameters.
    command = f"""
source {activate_script}
echo "Virtual environment activated. Starting vLLM server..."
vllm serve {MODEL_NAME} \
  --host {HOST} \
  --port {PORT} \
  --quantization {QUANTIZATION} \
  --gpu-memory-utilization {GPU_MEMORY_UTILIZATION} \
  --max-model-len {MAX_MODEL_LEN} \
  --dtype {DTYPE} \
  --api-key {API_KEY}
"""
    
    log_fn(f"Starting vLLM server in '{VLLM_INSTALL_DIR}'...")
    
    # Update UI state and run the command.
    start_btn.config(state=tk.DISABLED)
    stop_btn.config(state=tk.NORMAL)
    kill_btn.config(state=tk.NORMAL)
    run_command(launcher, TAB_TITLE, command, log_fn, widget, start_btn, 
                stop_btn, kill_btn, cwd=str(VLLM_INSTALL_DIR))

def stop_service(launcher, log_fn):
    """Sends a graceful SIGTERM signal to the server process group."""
    if TAB_TITLE not in launcher.processes:
        log_fn("Server process not found. Nothing to stop.", "warn")
        return

    log_fn("Attempting graceful shutdown (sending SIGTERM)...")
    try:
        # Terminate the entire process group to ensure child processes are also stopped.
        pgid = os.getpgid(launcher.processes[TAB_TITLE].pid)
        os.killpg(pgid, signal.SIGTERM)
        log_fn("SIGTERM signal sent to process group.")
    except ProcessLookupError:
        log_fn("Process already terminated.", "warn")
        launcher.processes.pop(TAB_TITLE, None)
    except Exception as e:
        log_fn(f"Error during graceful stop: {e}. Consider a force kill.", "error")

def kill_service(launcher, log_fn):
    """Forcibly terminates the server process group with SIGKILL."""
    if TAB_TITLE not in launcher.processes:
        log_fn("Server process not found. Nothing to kill.", "warn")
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
    """Creates and lays out the vLLM Server tab and its widgets."""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text=TAB_TITLE)
    
    # --- Layout Configuration ---
    tab.columnconfigure(0, weight=1)
    tab.columnconfigure(1, weight=0)
    tab.rowconfigure(2, weight=1)
    
    # --- Left Frame (Info, Controls, Logs) ---
    left_frame = ttk.Frame(tab)
    left_frame.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))
    left_frame.columnconfigure(0, weight=1)
    left_frame.rowconfigure(2, weight=1)

    # --- Log Widget ---
    log_frame = ttk.LabelFrame(left_frame, text="Server Log", padding="5")
    log_frame.grid(row=2, column=0, sticky="nsew")
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    log_widget = create_log_widget(log_frame)
    log_widget.grid(row=0, column=0, sticky="nsew")

    # Create a specific logger instance for this tab
    log_fn = lambda message, level="info": log(launcher, log_widget, message, level)

    # --- Info Section ---
    info_frame = ttk.LabelFrame(left_frame, text="Server Configuration", padding="10")
    info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    # Display key configuration details from the constants defined above.
    ttk.Label(info_frame, text=f"Model: {MODEL_NAME}").pack(anchor="w")
    ttk.Label(info_frame, text=f"Host: {HOST}:{PORT}").pack(anchor="w")
    ttk.Label(info_frame, text=f"API Key: {API_KEY}").pack(anchor="w")

    # --- Control Buttons ---
    button_frame = ttk.Frame(left_frame)
    button_frame.grid(row=1, column=0, pady=(0, 10))
    
    start_btn = ttk.Button(button_frame, text="▶ Start Server", width=15)
    stop_btn = ttk.Button(button_frame, text="⏹ Stop Server", state=tk.DISABLED, width=15)
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
    
    log_fn("vLLM Server tab initialized and ready.")

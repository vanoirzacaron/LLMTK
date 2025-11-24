"""
Boilerplate Tab
Use this as a template to create new features.
Find/Replace "Boilerplate" with your feature name.
"""

import tkinter as tk
from tkinter import ttk
import os
import signal
from utils import create_log_widget, log_to_widget, clear_log, run_command, create_monitor_frame

# --- CONFIGURATION ---
TAB_TITLE = "Boiler Tab"
SERVICE_ID = "BoilerService" # Unique ID for process tracking

def create_tab(notebook, launcher):
    """Create and configure the tab interface"""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text=TAB_TITLE)
    
    # Configure Grid Layout
    tab.columnconfigure(0, weight=1) # Main content
    tab.columnconfigure(1, weight=0) # Monitor sidebar
    tab.rowconfigure(2, weight=1)    # Log area expands
    
    # --- Left Side (Controls & Logs) ---
    left_frame = ttk.Frame(tab)
    left_frame.grid(row=0, column=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
    left_frame.columnconfigure(0, weight=1)
    left_frame.rowconfigure(2, weight=1)
    
    # 1. Info Section
    info_frame = ttk.LabelFrame(left_frame, text="Service Information", padding="10")
    info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    
    # TODO: Add your specific service details here
    ttk.Label(info_frame, text="Status: Ready").pack(anchor=tk.W)
    ttk.Label(info_frame, text="Configuration: Default").pack(anchor=tk.W)
    ttk.Label(info_frame, text="Path: /path/to/your/service").pack(anchor=tk.W)
    
    # 2. Control Buttons
    button_frame = ttk.Frame(left_frame)
    button_frame.grid(row=1, column=0, pady=(0, 10), sticky=tk.W)
    
    start_btn = ttk.Button(
        button_frame,
        text="▶ Start Service",
        command=lambda: start_service(launcher, log_widget, start_btn, stop_btn, kill_btn),
        width=15
    )
    start_btn.pack(side=tk.LEFT, padx=5)
    
    stop_btn = ttk.Button(
        button_frame,
        text="⏹ Stop Service",
        command=lambda: stop_service(launcher, log_widget),
        state=tk.DISABLED,
        width=15
    )
    stop_btn.pack(side=tk.LEFT, padx=5)
    
    kill_btn = ttk.Button(
        button_frame,
        text="⚠️ Force Kill",
        command=lambda: kill_service(launcher, log_widget),
        state=tk.DISABLED,
        width=15
    )
    kill_btn.pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        button_frame,
        text="🗑️ Clear Log",
        command=lambda: clear_log(log_widget),
        width=12
    ).pack(side=tk.LEFT, padx=5)
    
    # 3. Log Section
    log_frame = ttk.LabelFrame(left_frame, text="Service Log", padding="5")
    log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    log_widget = create_log_widget(log_frame)
    log_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # --- Right Side (Process Monitor) ---
    # This monitors the specific process ID of this service
    monitor_frame = create_monitor_frame(tab, SERVICE_ID, launcher)
    monitor_frame.grid(row=0, column=1, sticky=(tk.N, tk.E, tk.W))
    
    log_to_widget(log_widget, f"{TAB_TITLE} loaded successfully.")

def start_service(launcher, log_widget, start_btn, stop_btn, kill_btn):
    """Start the service"""
    
    # TODO: Define your command here. 
    # This is a dummy command that counts to 100 so you can see it working.
    command = 'python3 -u -c "import time; print(\'Service started...\'); [print(f\'Working hard {i}...\') or time.sleep(1) for i in range(1000)]"'
    
    # Optional: Set working directory
    # cwd = "/path/to/working/dir"
    cwd = None 

    # Update UI state
    start_btn.configure(state=tk.DISABLED)
    stop_btn.configure(state=tk.NORMAL)
    kill_btn.configure(state=tk.NORMAL)
    
    # Execute
    run_command(launcher, SERVICE_ID, command, log_widget, start_btn, 
                stop_btn, kill_btn, cwd=cwd)

def stop_service(launcher, log_widget):
    """Stop service gracefully"""
    if SERVICE_ID in launcher.processes:
        log_to_widget(log_widget, "Sending SIGTERM (graceful shutdown)...")
        try:
            # Kill the process group to ensure child processes die
            os.killpg(os.getpgid(launcher.processes[SERVICE_ID].pid), signal.SIGTERM)
        except Exception as e:
            log_to_widget(log_widget, f"Error stopping: {e}")
            try:
                launcher.processes[SERVICE_ID].terminate()
            except:
                pass

def kill_service(launcher, log_widget):
    """Force kill service"""
    if SERVICE_ID in launcher.processes:
        log_to_widget(log_widget, "⚠️ FORCE KILLING PROCESS...")
        try:
            os.killpg(os.getpgid(launcher.processes[SERVICE_ID].pid), signal.SIGKILL)
        except:
            try:
                launcher.processes[SERVICE_ID].kill()
            except:
                pass
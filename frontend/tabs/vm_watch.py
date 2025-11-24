"""
VM Watch Tab
Feature to monitor and manage virtual machines.
"""

import tkinter as tk
from tkinter import ttk
import os
import signal
from tabs.utils import create_log_widget, log_to_widget, clear_log, run_command, create_monitor_frame

# --- CONFIGURATION ---

TAB_TITLE = "VM Watch"
SERVICE_ID = "VMWatchService" # Unique ID for process tracking

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
    info_frame = ttk.LabelFrame(left_frame, text="Available VMs", padding="10")
    info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

    # Text widget to display VMs
    vm_list_widget = tk.Text(info_frame, height=10, relief=tk.FLAT, background=tab.cget('bg'))
    vm_list_widget.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
    vm_list_widget.insert(tk.END, "VMs will be listed here...")
    vm_list_widget.config(state=tk.DISABLED)

    # 2. Control Buttons
    button_frame = ttk.Frame(left_frame)
    button_frame.grid(row=1, column=0, pady=(0, 10), sticky=tk.W)

    play_btn = ttk.Button(
        button_frame,
        text="▶ Play",
        state=tk.DISABLED,
        width=15
    )
    play_btn.pack(side=tk.LEFT, padx=5)

    stop_btn = ttk.Button(
        button_frame,
        text="⏹ Stop",
        state=tk.DISABLED,
        width=15
    )
    stop_btn.pack(side=tk.LEFT, padx=5)

    force_stop_btn = ttk.Button(
        button_frame,
        text="⚠️ Force Stop",
        state=tk.DISABLED,
        width=15
    )
    force_stop_btn.pack(side=tk.LEFT, padx=5)
    
    reset_btn = ttk.Button(
        button_frame,
        text="🔄 Reset",
        state=tk.DISABLED,
        width=12
    )
    reset_btn.pack(side=tk.LEFT, padx=5)

    refresh_btn = ttk.Button(
        button_frame,
        text="🔄 Refresh",
        command=lambda: list_vms(launcher, log_widget, vm_list_widget),
        width=12
    )
    refresh_btn.pack(side=tk.LEFT, padx=5)

    # 3. Log Section
    log_frame = ttk.LabelFrame(left_frame, text="Service Log", padding="5")
    log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)

    log_widget = create_log_widget(log_frame)
    log_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # --- Right Side (Process Monitor) ---
    monitor_frame = create_monitor_frame(tab, SERVICE_ID, launcher)
    monitor_frame.grid(row=0, column=1, sticky=(tk.N, tk.E, tk.W))

    log_to_widget(log_widget, f"{TAB_TITLE} loaded successfully.")
    # Initial VM list
    list_vms(launcher, log_widget, vm_list_widget)

def list_vms(launcher, log_widget, vm_list_widget):
    """List all virtual machines"""
    command = 'virsh list --all'
    
    def on_success(output):
        vm_list_widget.config(state=tk.NORMAL)
        vm_list_widget.delete("1.0", tk.END)
        vm_list_widget.insert(tk.END, output)
        vm_list_widget.config(state=tk.DISABLED)
        log_to_widget(log_widget, "Successfully listed VMs.")

    def on_error(error):
        log_to_widget(log_widget, f"Error listing VMs: {error}")

    run_command(launcher, SERVICE_ID, command, log_widget, on_success=on_success, on_error=on_error)

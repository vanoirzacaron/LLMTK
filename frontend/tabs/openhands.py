"""
OpenHands Tab
Manages the OpenHands agent process with monitoring
"""

import tkinter as tk
from tkinter import ttk
import os
import signal
from utils import create_log_widget, log_to_widget, clear_log, run_command, create_monitor_frame

def create_tab(notebook, launcher):
    """Create and configure the OpenHands tab"""
    oh_tab = ttk.Frame(notebook, padding="10")
    notebook.add(oh_tab, text="OpenHands")
    
    oh_tab.columnconfigure(0, weight=1)
    oh_tab.columnconfigure(1, weight=0)
    oh_tab.rowconfigure(2, weight=1)
    
    # Left side - Info and logs
    left_frame = ttk.Frame(oh_tab)
    left_frame.grid(row=0, column=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
    left_frame.columnconfigure(0, weight=1)
    left_frame.rowconfigure(2, weight=1)
    
    # Info section
    info_frame = ttk.LabelFrame(left_frame, text="Agent Information", padding="10")
    info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    
    ttk.Label(info_frame, text="Framework: OpenHands Agent").pack(anchor=tk.W)
    ttk.Label(info_frame, text="Python Version: 3.12").pack(anchor=tk.W)
    l = ttk.Label(info_frame, text="http://localhost:3000", cursor="hand2", foreground="blue"); l.bind("<Button-1>", lambda e: __import__("webbrowser").open("http://localhost:3000")); l.pack(anchor=tk.W)

    # Control buttons
    button_frame = ttk.Frame(left_frame)
    button_frame.grid(row=1, column=0, pady=(0, 10))
    
    oh_start_btn = ttk.Button(
        button_frame,
        text="▶ Start Agent",
        command=lambda: start_openhands(launcher, oh_log, oh_start_btn, oh_stop_btn, oh_kill_btn),
        width=15
    )
    oh_start_btn.pack(side=tk.LEFT, padx=5)
    
    oh_stop_btn = ttk.Button(
        button_frame,
        text="⏹ Stop Agent",
        command=lambda: stop_openhands(launcher, oh_log),
        state=tk.DISABLED,
        width=15
    )
    oh_stop_btn.pack(side=tk.LEFT, padx=5)
    
    oh_kill_btn = ttk.Button(
        button_frame,
        text="⚠️ Force Kill",
        command=lambda: kill_openhands(launcher, oh_log),
        state=tk.DISABLED,
        width=15
    )
    oh_kill_btn.pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        button_frame,
        text="🗑️ Clear Log",
        command=lambda: clear_log(oh_log),
        width=12
    ).pack(side=tk.LEFT, padx=5)
    
    # Log section
    log_frame = ttk.LabelFrame(left_frame, text="Agent Log", padding="5")
    log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    oh_log = create_log_widget(log_frame)
    oh_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Right side - Monitor
    oh_monitor = create_monitor_frame(oh_tab, "OpenHands", launcher)
    oh_monitor.grid(row=0, column=1, sticky=(tk.N, tk.E, tk.W))
    
    log_to_widget(oh_log, "OpenHands ready to start")

def start_openhands(launcher, log_widget, start_btn, stop_btn, kill_btn):
    """Start OpenHands"""
    
    # --- START FIX: Cleanup old container before starting ---
    log_to_widget(log_widget, "🧹 Cleaning up any stale 'openhands-app' containers...")
    try:
        # This runs 'docker rm -f openhands-app' silently
        subprocess.run(
            ["docker", "rm", "-f", "openhands-app"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            check=False # Don't crash if container doesn't exist
        )
        log_to_widget(log_widget, "✅ Cleanup complete.")
    except Exception as e:
        log_to_widget(log_widget, f"⚠️ Warning: Container cleanup failed: {e}")
    # --- END FIX ---

    command = "uvx --python 3.12 openhands serve"
    
    start_btn.configure(state=tk.DISABLED)
    stop_btn.configure(state=tk.NORMAL)
    kill_btn.configure(state=tk.NORMAL)
    run_command(launcher, "OpenHands", command, log_widget, start_btn,
                stop_btn, kill_btn)

def stop_openhands(launcher, log_widget):
    """Stop OpenHands gracefully"""
    
    # Optional: Also ensure the container is killed on stop
    try:
        subprocess.run(["docker", "rm", "-f", "openhands-app"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    if "OpenHands" in launcher.processes:
        log_to_widget(log_widget, "Sending SIGTERM (graceful shutdown)...")
        try:
            os.killpg(os.getpgid(launcher.processes["OpenHands"].pid), signal.SIGTERM)
        except:
            launcher.processes["OpenHands"].terminate()

def kill_openhands(launcher, log_widget):
    """Force kill OpenHands"""
    
    # Optional: Force kill the container directly here too
    try:
        subprocess.run(["docker", "rm", "-f", "openhands-app"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    if "OpenHands" in launcher.processes:
        log_to_widget(log_widget, "⚠️ FORCE KILLING PROCESS...")
        try:
            os.killpg(os.getpgid(launcher.processes["OpenHands"].pid), signal.SIGKILL)
        except:
            launcher.processes["OpenHands"].kill()
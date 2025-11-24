"""
Process Monitor Tab

This tab provides a comprehensive, real-time view of all running processes on the system.
It allows users to monitor resource usage (CPU, RAM, VRAM), search for specific processes,
and terminate them securely.

Key Features:
- Real-time process listing with CPU, RAM, and NVIDIA GPU VRAM usage.
- Robust process termination using process groups (os.killpg) to ensure child processes are also ended.
- Efficient, non-blocking UI updates with a clean shutdown mechanism.
- Search/filter functionality to quickly find processes by name.
- Clickable column headers for sorting.
- Centralized logging for all actions and potential errors.
"""

import tkinter as tk
from tkinter import ttk
import psutil
import os
import signal
import subprocess
import shutil

# --- Constants & Configuration ---
TAB_TITLE = "Process Monitor"
UPDATE_INTERVAL_MS = 2000  # 2-second refresh interval for the process list.

# --- Logging Utility ---
def log(launcher, message, level="info"):
    """Centralized logging helper for the Process Monitor tab."""
    log_message = f"[{TAB_TITLE}] {message}"
    print(log_message) # For direct console feedback.
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(TAB_TITLE, message)

# --- Data Fetching Logic ---

def get_vram_usage(launcher):
    """Fetches VRAM usage for running processes using nvidia-smi.

    Returns:
        dict: A mapping of {pid: vram_mb} for processes using the GPU.
    """
    vram_map = {}
    if not shutil.which("nvidia-smi"):
        return vram_map # Return empty dict if nvidia-smi is not installed.

    try:
        cmd = ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
        
        for line in output.splitlines():
            if "," in line:
                parts = line.split(",")
                try:
                    pid, mem_mb = int(parts[0].strip()), int(parts[1].strip())
                    vram_map[pid] = mem_mb
                except (ValueError, IndexError):
                    continue
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log(launcher, f"nvidia-smi command failed: {e}", "warn")
    return vram_map

def fetch_process_data(launcher, filter_str=""):
    """Gathers data for all running processes.
    
    This function is compatible with older versions of psutil by avoiding the 'pgid' attribute
    in process_iter and using os.getpgid() instead.
    """
    data = []
    vram_map = get_vram_usage(launcher)
    cpu_count = psutil.cpu_count()

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            pinfo = proc.info
            pid = pinfo['pid']
            name = pinfo['name']
            
            if filter_str and filter_str.lower() not in name.lower():
                continue
            
            try:
                pgid = os.getpgid(pid)
            except (PermissionError, ProcessLookupError):
                pgid = pid

            cpu = pinfo['cpu_percent'] / cpu_count
            mem_mb = pinfo['memory_info'].rss / (1024 * 1024)
            
            data.append((pid, name, cpu, mem_mb, vram_map.get(pid, 0), pgid))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return data

# --- Core UI & Process Management Class ---

class ProcessMonitorTab(ttk.Frame):
    """Manages the UI, data updates, and user actions for the Process Monitor."""
    def __init__(self, parent, launcher):
        super().__init__(parent, padding="10")
        self.launcher = launcher
        self._is_running = True
        self.sort_state = {col: False for col in ("pid", "name", "cpu", "mem", "vram")}

        self._setup_ui()
        self.log("Process Monitor initialized.")
        self.update_process_list() # Start the update loop.

    def log(self, message, level="info"):
        log(self.launcher, message, level)

    def _setup_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        table_frame = ttk.LabelFrame(self, text="Running Processes", padding="5")
        table_frame.grid(row=0, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("pid", "name", "cpu", "mem", "vram")
        headers = {"pid": "PID", "name": "Name", "cpu": "CPU %", "mem": "RAM (MB)", "vram": "VRAM (CUDA)"}
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        for col, text in headers.items():
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=80 if col != "name" else 200, anchor="center" if col != "name" else "w")

        bottom_frame = ttk.Frame(self)
        bottom_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=1)

        action_frame = ttk.LabelFrame(bottom_frame, text="Actions", padding="10")
        action_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.refresh_var = tk.BooleanVar(value=True)
        self.btn_pause = ttk.Button(action_frame, text="⏸ Pause Updates", command=self.toggle_refresh)
        self.btn_pause.pack(fill="x", pady=5)
        ttk.Label(action_frame, text="Search Name:").pack(anchor="w")
        self.entry_filter = ttk.Entry(action_frame)
        self.entry_filter.pack(fill="x", pady=5)
        self.entry_filter.bind("<KeyRelease>", lambda e: self.update_process_list(force=True))

        kill_frame = ttk.LabelFrame(bottom_frame, text="Termination", padding="10")
        kill_frame.grid(row=0, column=1, sticky="nsew")
        self.lbl_selected = ttk.Label(kill_frame, text="Selected: None", wraplength=180)
        self.lbl_selected.pack(pady=5, anchor="w")
        self.btn_kill = ttk.Button(kill_frame, text="💀 Kill Selected Process Group", command=self.kill_selected_process)
        self.btn_kill.pack(fill="x", pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def toggle_refresh(self):
        if self.refresh_var.get():
            self.update_process_list()
            self.btn_pause.config(text="⏸ Pause Updates")
            self.log("Resumed process updates.")
        else:
            self.btn_pause.config(text="▶ Resume Updates")
            self.log("Paused process updates.")

    def on_select(self, event=None):
        if self.tree.selection():
            item = self.tree.item(self.tree.selection()[0])
            pid, name = item['values'][0], item['values'][1]
            self.lbl_selected.config(text=f"PID: {pid}\nName: {name}")
        else:
            self.lbl_selected.config(text="Selected: None")

    def update_process_list(self, force=False):
        if not self._is_running or not self.winfo_exists(): return
        if not self.refresh_var.get() and not force:
            self.after(500, self.update_process_list)
            return

        filter_str = self.entry_filter.get()
        process_data = fetch_process_data(self.launcher, filter_str)
        
        existing_pids = {self.tree.item(item_id)['values'][0]: item_id for item_id in self.tree.get_children()}
        current_pids = set()

        for item in process_data:
            pid, name, cpu, mem, vram, pgid = item
            current_pids.add(pid)
            display_vals = (pid, name, f"{cpu:.1f}", f"{mem:.0f}", f"{vram}" if vram > 0 else "-")
            
            if pid in existing_pids:
                self.tree.item(existing_pids[pid], values=display_vals, tags=(pgid,))
            else:
                self.tree.insert("", "end", values=display_vals, tags=(pgid,))

        pids_to_remove = set(existing_pids.keys()) - current_pids
        for pid in pids_to_remove:
            self.tree.delete(existing_pids[pid])

        if self.refresh_var.get():
            self.after(UPDATE_INTERVAL_MS, self.update_process_list)

    def kill_selected_process(self):
        selection = self.tree.selection()
        if not selection: return

        item = self.tree.item(selection[0])
        pid, name = item['values'][0], item['values'][1]
        pgid_tag = item['tags'][0] if item['tags'] else None

        if not pgid_tag:
            self.log(f"Cannot kill process {name} (PID: {pid}) - no PGID tag found.", "error")
            return

        try:
            pgid_to_kill = int(pgid_tag)
            self.log(f"Attempting to kill process group {name} (PGID: {pgid_to_kill})...")
            os.killpg(pgid_to_kill, signal.SIGKILL)
            self.log(f"Successfully sent SIGKILL to PGID {pgid_to_kill}.")
        except (ProcessLookupError, PermissionError) as e:
            self.log(f"Failed to kill process group {pgid_to_kill}: {e}", "error")
        except ValueError:
            self.log(f"Invalid PGID '{pgid_tag}' for process {name}. Cannot kill.", "error")

    def sort_treeview(self, col):
        reverse = self.sort_state[col] = not self.sort_state[col]
        
        def convert(val):
            if val == "-": return -1.0
            try: return float(val)
            except ValueError: return str(val).lower()

        data = [(convert(self.tree.set(k, col)), k) for k in self.tree.get_children('')]
        data.sort(key=lambda t: t[0], reverse=reverse)

        for index, (val, k) in enumerate(data):
            self.tree.move(k, '', index)

    def stop(self):
        self.log("Stopping process monitor.")
        self._is_running = False

# --- Factory Function ---
def create_tab(notebook, launcher):
    """Creates the ProcessMonitorTab and adds it to the notebook."""
    tab = ProcessMonitorTab(notebook, launcher)
    notebook.add(tab, text=TAB_TITLE) # FIX: The tab must be added to the notebook.
    return tab

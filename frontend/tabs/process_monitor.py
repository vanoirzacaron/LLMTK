"""
Process Monitor Tab (Fixed)
- Fixes sorting crash on "-" VRAM values
- Clarifies VRAM column is for Compute/CUDA only
- Optimizes refresh rate
"""

import tkinter as tk
from tkinter import ttk
import psutil
import os
import signal
import subprocess
import shutil
from utils import log_to_widget, create_log_widget, clear_log

# --- CONFIGURATION ---
UPDATE_INTERVAL_MS = 2000  # Refresh rate (2 seconds)

def create_tab(notebook, launcher):
    """Create and configure the Process Monitor tab"""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text="Process Monitor")
    
    # Layout: Top (Table), Bottom (Controls/Log)
    tab.columnconfigure(0, weight=1)
    tab.rowconfigure(0, weight=1) # Table expands
    tab.rowconfigure(1, weight=0) # Actions are fixed

    # --- Top: Process Table ---
    table_frame = ttk.LabelFrame(tab, text="Running Processes", padding="5")
    table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    table_frame.columnconfigure(0, weight=1)
    table_frame.rowconfigure(0, weight=1)

    # Columns configuration
    columns = ("pid", "name", "cpu", "mem", "vram")
    headers = {
        "pid": "PID", 
        "name": "Name", 
        "cpu": "CPU %", 
        "mem": "RAM (MB)", 
        "vram": "VRAM (CUDA)"
    }
    
    # Create Treeview
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
    tree.grid(row=0, column=0, sticky="nsew")
    
    # Add Scrollbar
    scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky="ns")
    
    # Configure Columns
    tree.column("pid", width=60, anchor="center")
    tree.column("name", width=200, anchor="w")
    tree.column("cpu", width=80, anchor="center")
    tree.column("mem", width=100, anchor="center")
    tree.column("vram", width=100, anchor="center")

    # State storage for sorting
    sort_state = {col: False for col in columns}

    # Bind Headers for Sorting
    for col in columns:
        tree.heading(col, text=headers[col], 
                     command=lambda c=col: sort_treeview(tree, c, sort_state))

    # --- Bottom: Actions and Log ---
    bottom_frame = ttk.Frame(tab)
    bottom_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
    bottom_frame.columnconfigure(0, weight=1)
    bottom_frame.columnconfigure(1, weight=1)

    action_frame = ttk.LabelFrame(bottom_frame, text="Actions", padding="10")
    action_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    
    log_frame = ttk.LabelFrame(bottom_frame, text="Action Log", padding="5")
    log_frame.grid(row=0, column=1, sticky="nsew")
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    log_widget = create_log_widget(log_frame)
    log_widget.grid(row=0, column=0, sticky="nsew")
    
    def log_message(message):
        log_to_widget(log_widget, message)
        launcher.log_to_global("Process Monitor", message)

    # Action Controls
    refresh_var = tk.BooleanVar(value=True)
    
    def toggle_refresh():
        if refresh_var.get():
            update_loop(tree, refresh_var, sort_state, log_message)
            btn_pause.config(text="⏸ Pause Updates")
            log_message("Resumed process updates.")
        else:
            btn_pause.config(text="▶ Resume Updates")
            log_message("Paused process updates.")

    btn_pause = ttk.Button(action_frame, text="⏸ Pause Updates", command=lambda: [refresh_var.set(not refresh_var.get()), toggle_refresh()])
    btn_pause.pack(fill="x", pady=5)

    ttk.Separator(action_frame, orient="horizontal").pack(fill="x", pady=10)
    
    lbl_selected = ttk.Label(action_frame, text="Selected: None", wraplength=150)
    lbl_selected.pack(pady=5)

    def on_select(event):
        selected = tree.selection()
        if selected:
            item = tree.item(selected[0])
            pid = item['values'][0]
            name = item['values'][1]
            lbl_selected.config(text=f"PID: {pid}\n{name}")
        else:
            lbl_selected.config(text="Selected: None")

    tree.bind("<<TreeviewSelect>>", on_select)

    btn_kill = ttk.Button(
        action_frame, 
        text="💀 Kill Selected", 
        command=lambda: kill_selected_process(tree, log_message)
    )
    btn_kill.pack(fill="x", pady=5)
    
    ttk.Separator(action_frame, orient="horizontal").pack(fill="x", pady=10)
    ttk.Label(action_frame, text="Search Name:").pack(anchor="w")
    entry_filter = ttk.Entry(action_frame)
    entry_filter.pack(fill="x", pady=5)
    entry_filter.bind("<KeyRelease>", lambda e: update_loop(tree, refresh_var, sort_state, log_message, force_update=True))
    
    tree.filter_text = entry_filter

    # Start Loop
    log_message("Process Monitor initialized.")
    update_loop(tree, refresh_var, sort_state, log_message)

def get_vram_usage():
    vram_map = {}
    if shutil.which("nvidia-smi"):
        try:
            cmd = ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
            
            for line in output.splitlines():
                if "," in line:
                    parts = line.split(",")
                    try:
                        pid = int(parts[0].strip())
                        mem = int(parts[1].strip())
                        vram_map[pid] = mem
                    except (ValueError, IndexError):
                        pass
        except subprocess.CalledProcessError:
            pass
    return vram_map

def fetch_process_data(filter_str=""):
    data = []
    vram_map = get_vram_usage()
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            pinfo = proc.info
            name = pinfo['name']
            
            if filter_str and filter_str.lower() not in name.lower():
                continue
                
            pid = pinfo['pid']
            cpu = pinfo['cpu_percent'] / psutil.cpu_count()
            mem = pinfo['memory_info'].rss / (1024 * 1024)
            vram = vram_map.get(pid, 0)
            
            data.append((pid, name, cpu, mem, vram))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    return data

def sort_treeview(tree, col, sort_state):
    reverse = sort_state[col] = not sort_state[col]
    
    data_list = [(tree.set(k, col), k) for k in tree.get_children('')]
    
    def convert(val):
        if val == "-": return -1.0
        try: return float(val)
        except ValueError: return str(val).lower()

    data_list.sort(key=lambda t: convert(t[0]), reverse=reverse)

    for index, (val, k) in enumerate(data_list):
        tree.move(k, '', index)
        
    for c in sort_state:
        char = " ▼" if sort_state.get(c) else " ▲"
        clean_text = tree.heading(c, "text").replace(" ▲", "").replace(" ▼", "")
        tree.heading(c, text=f"{clean_text}{char}" if c == col else clean_text)

def update_loop(tree, refresh_var, sort_state, log_fn, force_update=False):
    if not tree.winfo_exists(): return
    if not refresh_var.get() and not force_update: 
        tree.after(500, lambda: update_loop(tree, refresh_var, sort_state, log_fn, force_update))
        return

    selected_pid = None
    if tree.selection():
        try: selected_pid = tree.item(tree.selection()[0])['values'][0]
        except IndexError: pass

    filter_str = tree.filter_text.get()
    data = fetch_process_data(filter_str)
    
    current_selection_id = None
    existing_pids = {tree.item(item_id)['values'][0]: item_id for item_id in tree.get_children()}

    new_pids = set()
    for item in data:
        pid = item[0]
        new_pids.add(pid)
        display_vals = (pid, item[1], f"{item[2]:.1f}", f"{item[3]:.0f}", f"{item[4]}" if item[4] > 0 else "-")
        
        if pid in existing_pids:
            tree.item(existing_pids[pid], values=display_vals)
        else:
            existing_pids[pid] = tree.insert("", "end", values=display_vals)
        
        if pid == selected_pid:
            current_selection_id = existing_pids[pid]

    for pid, item_id in list(existing_pids.items()):
        if pid not in new_pids:
            tree.delete(item_id)
    
    if current_selection_id:
        tree.selection_set(current_selection_id)
        tree.see(current_selection_id)
    
    # Re-sort if a column header is active
    for col, is_rev in sort_state.items():
        if tree.heading(col, 'text').endswith(("▲", "▼")):
            sort_treeview(tree, col, {c: (not r if c==col else r) for c,r in sort_state.items()}) # Toggle and sort
            break

    if refresh_var.get():
        tree.after(UPDATE_INTERVAL_MS, lambda: update_loop(tree, refresh_var, sort_state, log_fn))

def kill_selected_process(tree, log_fn):
    if not tree.selection():
        log_fn("No process selected to kill.")
        return

    item = tree.item(tree.selection()[0])
    pid, name = item['values'][0], item['values'][1]
    
    try:
        process = psutil.Process(pid)
        process.terminate()
        log_fn(f"Sent SIGTERM to process {name} (PID: {pid}).")
    except psutil.NoSuchProcess:
        log_fn(f"Error: Process {name} (PID: {pid}) not found.")
    except psutil.AccessDenied:
        log_fn(f"Error: Access denied to kill {name} (PID: {pid}).")
    except Exception as e:
        log_fn(f"An unexpected error occurred: {e}")
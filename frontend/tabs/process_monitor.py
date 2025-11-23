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
from tabs.utils import log_to_widget, create_log_widget

# --- CONFIGURATION ---
UPDATE_INTERVAL_MS = 2000  # Refresh rate (2 seconds)

def create_tab(notebook, launcher):
    """Create and configure the Process Monitor tab"""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text="Process Monitor")
    
    # Layout: Left (Table), Right (Controls)
    tab.columnconfigure(0, weight=1)
    tab.columnconfigure(1, weight=0)
    tab.rowconfigure(0, weight=1)
    
    # --- Left Side: Process Table ---
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
        "vram": "VRAM (CUDA)" # Renamed for clarity
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

    # --- Right Side: Actions ---
    action_frame = ttk.LabelFrame(tab, text="Actions", padding="10")
    action_frame.grid(row=0, column=1, sticky="nsew")
    
    # 1. Auto-Refresh Toggle
    refresh_var = tk.BooleanVar(value=True)
    
    def toggle_refresh():
        if refresh_var.get():
            update_loop(tree, refresh_var, sort_state, launcher)
            btn_pause.config(text="⏸ Pause Updates")
        else:
            btn_pause.config(text="▶ Resume Updates")

    btn_pause = ttk.Button(action_frame, text="⏸ Pause Updates", command=lambda: [refresh_var.set(not refresh_var.get()), toggle_refresh()])
    btn_pause.pack(fill="x", pady=5)

    # 2. Kill Button
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
        command=lambda: kill_selected_process(tree, lbl_selected)
    )
    btn_kill.pack(fill="x", pady=5)
    
    # 3. Filter
    ttk.Separator(action_frame, orient="horizontal").pack(fill="x", pady=10)
    ttk.Label(action_frame, text="Search Name:").pack(anchor="w")
    entry_filter = ttk.Entry(action_frame)
    entry_filter.pack(fill="x", pady=5)
    
    tree.filter_text = entry_filter

    # Start Loop
    update_loop(tree, refresh_var, sort_state, launcher)

def get_vram_usage():
    """
    Returns a dict {pid: vram_mb} using nvidia-smi.
    Targets Compute Apps only (AI/LLMs).
    """
    vram_map = {}
    if shutil.which("nvidia-smi"):
        try:
            cmd = ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"]
            # Suppress stderr to keep console clean
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
            
            for line in output.splitlines():
                if "," in line:
                    parts = line.split(",")
                    try:
                        pid = int(parts[0].strip())
                        mem = int(parts[1].strip())
                        vram_map[pid] = mem
                    except ValueError:
                        pass
        except:
            pass
    return vram_map

def fetch_process_data(filter_str=""):
    """Fetches system processes and formats them for the table."""
    data = []
    vram_map = get_vram_usage()
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            pinfo = proc.info
            name = pinfo['name']
            
            if filter_str and filter_str.lower() not in name.lower():
                continue
                
            pid = pinfo['pid']
            cpu = pinfo['cpu_percent']
            mem = pinfo['memory_info'].rss / (1024 * 1024) # MB
            
            # VRAM logic
            vram = vram_map.get(pid, 0)
            
            data.append((pid, name, cpu, mem, vram))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    return data

def sort_treeview(tree, col, sort_state):
    """Sorts the treeview contents safely"""
    reverse = sort_state[col] = not sort_state[col]
    
    data_list = [(tree.set(k, col), k) for k in tree.get_children('')]
    
    def convert(val):
        # Helper to handle "-" vs Numbers safely
        if val == "-":
            return -1.0
        try:
            return float(val)
        except ValueError:
            return val.lower()

    # Sort using the safe converter
    data_list.sort(key=lambda t: convert(t[0]), reverse=reverse)

    for index, (val, k) in enumerate(data_list):
        tree.move(k, '', index)
        
    for c in sort_state:
        char = " ▼" if sort_state[c] else " ▲"
        clean_text = tree.heading(c, "text").replace(" ▲", "").replace(" ▼", "")
        if c == col:
            tree.heading(c, text=f"{clean_text}{char}")
        else:
            tree.heading(c, text=clean_text)

def update_loop(tree, refresh_var, sort_state, launcher):
    """Main update loop"""
    if not tree.winfo_exists() or not refresh_var.get():
        return

    selected_items = tree.selection()
    selected_pid = None
    if selected_items:
        try:
            selected_pid = tree.item(selected_items[0])['values'][0]
        except: pass

    filter_str = tree.filter_text.get()
    data = fetch_process_data(filter_str)
    
    # Pre-sort data based on current sort state
    sorted_col = None
    is_reverse = False
    headers = ["pid", "name", "cpu", "mem", "vram"]
    
    for col, rev in sort_state.items():
        if tree.heading(col, "text").endswith(("▲", "▼")):
            sorted_col = col
            is_reverse = rev
            break
    
    if sorted_col:
        idx = headers.index(sorted_col)
        data.sort(key=lambda x: x[idx], reverse=is_reverse)
    else:
        # Default: Sort by CPU usage
        data.sort(key=lambda x: x[2], reverse=True)

    tree.delete(*tree.get_children())
    
    for item in data:
        display_vals = (
            item[0], 
            item[1], 
            f"{item[2]:.1f}", 
            f"{item[3]:.0f}", 
            f"{item[4]}" if item[4] > 0 else "-"
        )
        item_id = tree.insert("", "end", values=display_vals)
        
        if selected_pid and item[0] == selected_pid:
            tree.selection_set(item_id)
            tree.see(item_id)

    tree.after(UPDATE_INTERVAL_MS, lambda: update_loop(tree, refresh_var, sort_state, launcher))

def kill_selected_process(tree, lbl_status):
    """Kills selected process"""
    selected = tree.selection()
    if not selected:
        return

    item = tree.item(selected[0])
    pid = item['values'][0]
    name = item['values'][1]
    
    try:
        process = psutil.Process(pid)
        process.terminate()
        lbl_status.config(text=f"Sent SIGTERM to {name} ({pid})", foreground="orange")
    except psutil.NoSuchProcess:
        lbl_status.config(text=f"Process {pid} already gone.", foreground="red")
    except psutil.AccessDenied:
        lbl_status.config(text=f"Access Denied killing {pid}.", foreground="red")
    except Exception as e:
        lbl_status.config(text=f"Error: {e}", foreground="red")
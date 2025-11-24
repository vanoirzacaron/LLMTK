'''
VM Watch Tab
Feature to monitor and manage virtual machines.
'''

import tkinter as tk
from tkinter import ttk
import os
import signal
import psutil
import shutil
from utils import create_log_widget, log_to_widget, clear_log, run_command

# --- CONFIGURATION ---

TAB_TITLE = "VM Watch"
SERVICE_ID = "VMWatchService"
REFRESH_INTERVAL_MS = 5000  # 5 seconds

def get_launched_vms():
    """Check for running virt-viewer processes and return a set of VM names."""
    launched_vms = set()
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] == 'virt-viewer' and proc.info['cmdline']:
                launched_vms.add(proc.info['cmdline'][-1])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return launched_vms

def create_tab(notebook, launcher):
    """Create and configure the tab interface"""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text=TAB_TITLE)

    tab.columnconfigure(0, weight=1)
    tab.rowconfigure(0, weight=1)

    main_frame = ttk.Frame(tab)
    main_frame.grid(row=0, column=0, sticky="nsew")
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(0, weight=0)  # Table row (fixed)
    main_frame.rowconfigure(1, weight=0)  # Button row (fixed)
    main_frame.rowconfigure(2, weight=1)  # Log row (expands)

    # --- Logger Setup ---
    log_frame = ttk.LabelFrame(main_frame, text="Service Log", padding="5")
    log_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    log_widget = create_log_widget(log_frame)
    log_widget.grid(row=0, column=0, sticky="nsew")

    def log_message(message):
        log_to_widget(log_widget, message)
        launcher.log_to_global(TAB_TITLE, message)

    # --- VM Table ---
    table_frame = ttk.LabelFrame(main_frame, text="Available VMs", padding="5")
    table_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
    table_frame.columnconfigure(0, weight=1)
    table_frame.rowconfigure(0, weight=1)

    columns = ("id", "name", "state", "launched")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", height=8)
    tree.grid(row=0, column=0, sticky="nsew")

    scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.grid(row=0, column=1, sticky="ns")

    tree.column("id", width=60, anchor="center")
    tree.heading("id", text="ID")
    tree.column("name", width=200, anchor="w")
    tree.heading("name", text="Name")
    tree.column("state", width=150, anchor="w")
    tree.heading("state", text="State")
    tree.column("launched", width=80, anchor="center")
    tree.heading("launched", text="Launched")

    # --- Control Buttons ---
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=1, column=0, pady=(0, 10), sticky="ew")

    play_btn = ttk.Button(button_frame, text="▶ Play", state=tk.DISABLED, width=12)
    play_btn.pack(side=tk.LEFT, padx=5)

    stop_btn = ttk.Button(button_frame, text="⏹ Stop", state=tk.DISABLED, width=12)
    stop_btn.pack(side=tk.LEFT, padx=5)

    force_stop_btn = ttk.Button(button_frame, text="⚠️ Force Stop", state=tk.DISABLED, width=15)
    force_stop_btn.pack(side=tk.LEFT, padx=5)
    
    reset_btn = ttk.Button(button_frame, text="🔄 Reset", state=tk.DISABLED, width=12)
    reset_btn.pack(side=tk.LEFT, padx=5)

    launch_btn = ttk.Button(button_frame, text="🚀 Launch", state=tk.DISABLED, width=12)
    launch_btn.pack(side=tk.LEFT, padx=5)

    def on_vm_select(event):
        selected = tree.selection()
        if selected:
            item = tree.item(selected[0])
            values = item['values']
            if not values: return
            vm_state = values[2]
            is_launched = values[3] == "Yes"
            is_running = "running" in vm_state

            play_btn.config(state=tk.NORMAL if not is_running else tk.DISABLED)
            stop_btn.config(state=tk.NORMAL if is_running else tk.DISABLED)
            force_stop_btn.config(state=tk.NORMAL if is_running else tk.DISABLED)
            reset_btn.config(state=tk.NORMAL if is_running else tk.DISABLED)
            launch_btn.config(state=tk.NORMAL if is_running else tk.DISABLED)
            launch_btn.config(text="✨ Focus" if is_launched else "🚀 Launch")
        else:
            for btn in [play_btn, stop_btn, force_stop_btn, reset_btn, launch_btn]:
                btn.config(state=tk.DISABLED)
            launch_btn.config(text="🚀 Launch")

    tree.bind("<<TreeviewSelect>>", on_vm_select)

    play_btn.config(command=lambda: vm_action(launcher, log_message, tree, 'virsh start {vm_name}'))
    stop_btn.config(command=lambda: vm_action(launcher, log_message, tree, 'virsh shutdown {vm_name}'))
    force_stop_btn.config(command=lambda: vm_action(launcher, log_message, tree, 'virsh destroy {vm_name}'))
    reset_btn.config(command=lambda: vm_action(launcher, log_message, tree, 'virsh reset {vm_name}'))
    launch_btn.config(command=lambda: launch_or_focus_vm(launcher, log_message, tree))

    log_message(f"{TAB_TITLE} loaded. Initializing VM list...")
    # Delay initial load to prevent blocking UI thread
    tab.after(1000, lambda: update_loop(launcher, log_message, tree, notebook))

def update_loop(launcher, log_fn, tree, notebook):
    is_visible = False
    try:
        # Check if the tab is currently selected
        is_visible = notebook.winfo_exists() and notebook.tab(notebook.select(), "text") == TAB_TITLE
    except tk.TclError:
        # This can happen if no tab is selected yet during startup
        is_visible = False

    if tree.winfo_exists():
        if is_visible:
            list_vms(launcher, log_fn, tree)
            # Schedule next update when visible
            tree.after(REFRESH_INTERVAL_MS, lambda: update_loop(launcher, log_fn, tree, notebook))
        else:
            # Check again sooner if not visible
            tree.after(500, lambda: update_loop(launcher, log_fn, tree, notebook))

def list_vms(launcher, log_fn, tree):
    selected_id = tree.item(tree.selection()[0])['values'][0] if tree.selection() else None

    def on_success(output):
        if not tree.winfo_exists(): return
        launched_vms = get_launched_vms()
        current_items = {tree.item(item)["values"][1]: item for item in tree.get_children()}
        vms_from_virsh = set()

        for line in output.strip().split('\n')[2:]:
            parts = line.strip().split()
            if len(parts) >= 3:
                vm_id, vm_name, vm_state = parts[0], parts[1], ' '.join(parts[2:])
                vms_from_virsh.add(vm_name)
                is_launched = "Yes" if vm_name in launched_vms else "No"
                values = (vm_id, vm_name, vm_state, is_launched)

                if vm_name in current_items:
                    item_id = current_items.pop(vm_name)
                    if tree.item(item_id)['values'] != list(values):
                        tree.item(item_id, values=values)
                    if str(vm_id) == str(selected_id):
                        tree.selection_set(item_id)
                else:
                    item_id = tree.insert("", "end", values=values)
                    if str(vm_id) == str(selected_id):
                        tree.selection_set(item_id)

        for vm_name in list(current_items.keys()):
            tree.delete(current_items[vm_name])

        if not tree.selection() and selected_id is not None:
            # If the previously selected item is gone, clear button states
            tree.event_generate("<<TreeviewSelect>>")
        elif tree.selection():
            tree.event_generate("<<TreeviewSelect>>")

    run_command(launcher, SERVICE_ID, 'virsh list --all', log_fn, 
                on_success=on_success, 
                on_error=lambda e: log_fn(f"Error listing VMs: {e}"))

def vm_action(launcher, log_fn, tree, command_template):
    if not tree.selection(): return
    vm_name = tree.item(tree.selection()[0])['values'][1]
    command = command_template.format(vm_name=vm_name)
    log_fn(f"Executing: {command}")
    run_command(launcher, f"{command.split()[0]}_{vm_name}", command, log_fn, 
                on_success=lambda out: log_fn(out) or list_vms(launcher, log_fn, tree),
                on_error=lambda err: log_fn(err))

def launch_or_focus_vm(launcher, log_fn, tree):
    if not tree.selection(): return
    item = tree.item(tree.selection()[0])
    vm_name, is_launched = item['values'][1], item['values'][3] == "Yes"

    if is_launched:
        if shutil.which("wmctrl"):
            command = f'wmctrl -a "{vm_name}"'
            log_fn(f"Focusing on VM window: {vm_name}")
            run_command(launcher, f"focus_{vm_name}", command, log_fn, on_error=lambda e: log_fn(f"Error focusing: {e}"))
        else:
            log_fn("wmctrl not found. Cannot focus window.")
    else:
        command = f'virt-viewer --domain-name {vm_name}'
        log_fn(f"Launching VM: {vm_name}")
        # We run this detached as it's a GUI app
        run_command(launcher, f"launch_{vm_name}", command, log_fn, on_error=lambda e: log_fn(f"Error launching: {e}"))

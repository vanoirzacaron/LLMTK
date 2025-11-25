#!/usr/bin/env python3
"""
LLM Services Launcher - Modular Architecture

A robust GUI to start, monitor, and manage LLM services. This launcher dynamically
loads all tabs and panels from their respective directories, allowing for easy 
extension and customization.
"""

import tkinter as tk
from tkinter import ttk
import importlib
import sys
from pathlib import Path
import traceback # Import traceback for better error logging

class LLMLauncher:
    """The main application class that builds and manages the GUI."""

    # --- Tab Ordering System ---
    TAB_ORDER = {
    "vm_watch": 11,
        "vllm": 10,
        "process_monitor": 5,
    }

    def __init__(self, root):
        self.root = root
        self.root.title("LLM Services Launcher")
        self.root.geometry("1146x1411")
        self.root.resizable(True, True)

        self.processes = {}
        self.monitors = {}
        self.monitor_threads = {}
        self.monitoring_active = {}
        self.panels = []
        self.global_log_panel = None

        self._setup_main_layout()
        self.load_tabs()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_main_layout(self):
        """Configures the primary frames of the application window."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # FIX: Swapped column weights and order to move the navigation panel to the right.
        main_frame.columnconfigure(0, weight=1)  # Left content area (expands)
        main_frame.columnconfigure(1, weight=0)  # Right navigation panel (fixed width)
        main_frame.rowconfigure(0, weight=1)

        # --- Content Area (Now on the Left) ---
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(2, weight=1)  # Notebook row should expand

        ttk.Label(content_frame, text="🚀 LLM Services Launcher", font=('Arial', 16, 'bold')).grid(row=0, column=0, pady=(0, 10))
        
        panel_frame = ttk.Frame(content_frame)
        panel_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.load_panels(panel_frame)

        self.notebook = ttk.Notebook(content_frame)
        self.notebook.grid(row=2, column=0, sticky="nsew")
        
        # --- Load Navigation Panel (Now on the Right) ---
        self.load_navigation_panel(main_frame)

    def _load_module_from_file(self, module_name, file_path, namespace):
        """Helper function to load a Python module from a specific file path."""
        try:
            spec = importlib.util.spec_from_file_location(f"{namespace}.{module_name}", file_path)
            if spec is None: return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{namespace}.{module_name}"] = module
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            print(f"Error loading module {module_name} from {file_path}: {e}")
            traceback.print_exc()
            return None

    def load_navigation_panel(self, parent):
        """Loads the specific navigation panel and places it on the right side."""
        nav_file = Path(__file__).parent / "panels" / "navigation.py"
        if not nav_file.exists():
            print("Warning: navigation.py not found.")
            return

        module = self._load_module_from_file(nav_file.stem, nav_file, "panels")
        if module and hasattr(module, 'create_panel'):
            print(f"Loading panel: {nav_file.stem}")
            # FIX: Grid the panel into column 1 to place it on the right.
            panel_widget = module.create_panel(parent, self)
            panel_widget.grid(row=0, column=1, sticky="nsw") 
            self.panels.append(panel_widget)
        elif module:
            print(f"Warning: {nav_file.stem}.py is missing the create_panel() function.")

    def load_panels(self, parent):
        """Dynamically loads all non-navigation panels from the 'panels' directory."""
        panels_dir = Path(__file__).parent / "panels"
        if not panels_dir.exists(): return

        for panel_file in sorted(panels_dir.glob("*.py")):
            if panel_file.name.startswith("_") or panel_file.stem == "navigation": continue

            module = self._load_module_from_file(panel_file.stem, panel_file, "panels")
            if module and hasattr(module, 'create_panel'):
                print(f"Loading panel: {panel_file.stem}")
                panel_widget = module.create_panel(parent, self)
                panel_widget.pack(side="top", fill="x", expand=True, padx=2, pady=2)
                self.panels.append(panel_widget)

                if panel_file.stem == "global_log":
                    self.global_log_panel = panel_widget
            elif module:
                print(f"Warning: {panel_file.stem}.py is missing the create_panel() function.")

    def log_to_global(self, source_tab, message):
        if self.global_log_panel and hasattr(self.global_log_panel, 'add_log'):
            self.global_log_panel.add_log(source_tab, message)

    def load_tabs(self):
        """Dynamically loads all tab modules, respecting the priority in TAB_ORDER."""
        tabs_dir = Path(__file__).parent / "tabs"
        if not tabs_dir.is_dir(): return

        def sort_key(file_path):
            module_name = file_path.stem
            priority = self.TAB_ORDER.get(module_name, 0)
            return (-priority, module_name)

        sorted_tab_files = sorted([f for f in tabs_dir.glob("*.py") if not f.name.startswith("_")], key=sort_key)

        for tab_file in sorted_tab_files:
            module_name = tab_file.stem
            module = self._load_module_from_file(module_name, tab_file, "tabs")
            if module and hasattr(module, 'create_tab'):
                print(f"Loading tab: {module_name} (Priority: {self.TAB_ORDER.get(module_name, 0)})")
                module.create_tab(self.notebook, self)
            elif module:
                print(f"Warning: {module_name}.py is missing the create_tab() function.")

    def on_closing(self):
        """Handles the application shutdown, ensuring all child processes are terminated."""
        print("Shutting down application...")
        
        for panel in self.panels:
            if hasattr(panel, 'stop'):
                panel.stop()
        for name in list(self.monitoring_active.keys()):
            self.monitoring_active[name] = False
        for name, process in list(self.processes.items()):
            if process.poll() is None:
                try:
                    print(f"Terminating process: {name}")
                    process.terminate()
                    process.wait(timeout=5)
                except Exception as e:
                    print(f"Error terminating {name}: {e}. Trying to kill...")
                    try: process.kill()
                    except Exception as ke: print(f"Failed to kill {name}: {ke}")
        
        self.root.destroy()

def main():
    root = tk.Tk()
    app = LLMLauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main()

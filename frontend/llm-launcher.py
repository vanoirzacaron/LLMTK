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
    # Define the display order for tabs. Higher numbers have higher priority (appear first).
    # Tabs not listed here will be given a default priority of 0 and will appear after
    # the prioritized tabs, sorted alphabetically.
    # For example:
    #   - 'testing' (priority 99) will be the first tab.
    #   - 'vllm' (priority 10) will come after 'testing'.
    #   - 'openhands' and 'infrasven' (both priority 0) will come last, alphabetically.
    TAB_ORDER = {
        #"testing": 99,         # Highest priority, appears first
        "vllm": 10,            # High priority
        "process_monitor": 5,  # Medium priority
        # 'openhands': 0,    # Explicitly setting to 0 is same as not listing it
        # 'infrasven': 0,      # Explicitly setting to 0 is same as not listing it
    }

    def __init__(self, root):
        self.root = root
        self.root.title("LLM Services Launcher")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        self.processes = {}
        self.monitors = {}
        self.monitor_threads = {}
        self.monitoring_active = {}
        self.panels = []
        self.global_log_panel = None

        self._setup_main_layout()
        self.load_tabs()

        # Register the shutdown handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_main_layout(self):
        """Configures the primary frames of the application window."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame.columnconfigure(0, weight=0)  # Left navigation panel (fixed width)
        main_frame.columnconfigure(1, weight=1)  # Right content area (expands)
        main_frame.rowconfigure(0, weight=1)

        # --- Load Panels ---
        # Panels are persistent UI elements outside the main notebook.
        self.load_navigation_panel(main_frame)

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(2, weight=1)  # Notebook row should expand

        ttk.Label(right_frame, text="🚀 LLM Services Launcher", font=('Arial', 16, 'bold')).grid(row=0, column=0, pady=(0, 10))
        
        panel_frame = ttk.Frame(right_frame)
        panel_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.load_panels(panel_frame)

        # --- Notebook for Tabs ---
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.grid(row=2, column=0, sticky="nsew")

    def _load_module_from_file(self, module_name, file_path, namespace):
        """Helper function to load a Python module from a specific file path."""
        try:
            spec = importlib.util.spec_from_file_location(f"{namespace}.{module_name}", file_path)
            if spec is None:
                print(f"Error: Could not create module spec for {file_path}")
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{namespace}.{module_name}"] = module
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            print(f"Error loading module {module_name} from {file_path}: {e}")
            traceback.print_exc()
            return None

    def load_navigation_panel(self, parent):
        """Loads the specific navigation panel from the 'panels' directory."""
        nav_file = Path(__file__).parent / "panels" / "navigation.py"
        if not nav_file.exists():
            print("Warning: navigation.py not found.")
            return

        module = self._load_module_from_file(nav_file.stem, nav_file, "panels")
        if module and hasattr(module, 'create_panel'):
            print(f"Loading panel: {nav_file.stem}")
            panel_widget = module.create_panel(parent, self)
            panel_widget.grid(row=0, column=0, sticky="nsw")
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
                    self.global_log_panel = panel_widget # Store a reference to the global logger
            elif module:
                print(f"Warning: {panel_file.stem}.py is missing the create_panel() function.")

    def log_to_global(self, source_tab, message):
        """Sends a log message to the global log panel if it exists."""
        if self.global_log_panel and hasattr(self.global_log_panel, 'add_log'):
            self.global_log_panel.add_log(source_tab, message)

    def load_tabs(self):
        """Dynamically loads all tab modules, respecting the priority in TAB_ORDER."""
        tabs_dir = Path(__file__).parent / "tabs"
        if not tabs_dir.is_dir():
            print(f"Warning: 'tabs' directory not found at {tabs_dir}")
            return

        # 1. Discover all valid tab files
        tab_files = [f for f in tabs_dir.glob("*.py") if not f.name.startswith("_")]

        # 2. Sort the files based on the TAB_ORDER priority and then alphabetically
        #    - The key is a tuple: (priority, module_name)
        #    - Higher priority numbers come first (hence the negative)
        #    - For ties in priority, it sorts alphabetically by module name
        def sort_key(file_path):
            module_name = file_path.stem
            priority = self.TAB_ORDER.get(module_name, 0) # Default to 0 if not in dict
            return (-priority, module_name)

        sorted_tab_files = sorted(tab_files, key=sort_key)

        # 3. Load the sorted tabs
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
        
        # Stop all background threads and processes
        for panel in self.panels:
            if hasattr(panel, 'stop'):
                panel.stop()
        for name in list(self.monitoring_active.keys()):
            self.monitoring_active[name] = False
        for name, process in list(self.processes.items()):
            if process.poll() is None: # If the process is still running
                try:
                    print(f"Terminating process: {name}")
                    process.terminate()
                    process.wait(timeout=5)
                except Exception as e:
                    print(f"Error terminating {name}: {e}. Trying to kill...")
                    try:
                        process.kill()
                    except Exception as ke:
                        print(f"Failed to kill {name}: {ke}")
        
        self.root.destroy()

def main():
    """Initializes the Tkinter root and starts the main application loop."""
    root = tk.Tk()
    app = LLMLauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main()

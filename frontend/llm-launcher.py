#!/usr/bin/env python3
"""
LLM Services Launcher - Modular Architecture
A robust GUI to start, monitor, and manage LLM services
"""

import tkinter as tk
from tkinter import ttk
import importlib
import sys
from pathlib import Path

class LLMLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("LLM Services Launcher")
        self.root.geometry("1000x800")
        self.root.resizable(True, True)
        
        # Store process references and monitors
        self.processes = {}
        self.monitors = {}
        self.monitor_threads = {}
        self.monitoring_active = {}
        self.panels = []
        
        # Main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # Update main_frame row configuration for the new layout
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1) # Notebook is now at row 2, so it gets the weight
        
        # 1. Title (Row 0)
        title = ttk.Label(main_frame, text="🚀 LLM Services Launcher", font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, pady=(0, 10))
        
        # 2. Panels container (Row 1)
        panel_frame = ttk.Frame(main_frame)
        panel_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.load_panels(panel_frame)

        # 3. Create notebook/tabs (Row 2 - Moved down)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Load all tabs dynamically
        self.load_tabs()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_panels(self, parent):
        """Dynamically load all panel modules from the panels directory"""
        panels_dir = Path(__file__).parent / "panels"
        
        if not panels_dir.exists():
            print(f"Warning: panels directory not found at {panels_dir}")
            return
            
        panel_files = sorted(panels_dir.glob("*.py"))
        
        for panel_file in panel_files:
            if panel_file.name.startswith("_"):
                continue
            
            module_name = panel_file.stem
            
            try:
                spec = importlib.util.spec_from_file_location(
                    f"panels.{module_name}", 
                    panel_file
                )
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"panels.{module_name}"] = module
                spec.loader.exec_module(module)
                
                if hasattr(module, 'create_panel'):
                    print(f"Loading panel: {module_name}")
                    panel_widget = module.create_panel(parent, self)
                    panel_widget.pack(side="top", fill="x", expand=True, padx=2, pady=2)
                    self.panels.append(panel_widget)
                else:
                    print(f"Warning: {module_name}.py missing create_panel() function")
                    
            except Exception as e:
                print(f"Error loading panel {module_name}: {e}")
                import traceback
                traceback.print_exc()

    def load_tabs(self):
        """Dynamically load all tab modules from the tabs directory"""
        tabs_dir = Path(__file__).parent / "tabs"
        
        if not tabs_dir.exists():
            print(f"Warning: tabs directory not found at {tabs_dir}")
            return
        
        # Find all Python files in tabs directory
        tab_files = sorted(tabs_dir.glob("*.py"))
        
        for tab_file in tab_files:
            if tab_file.name.startswith("_"):
                continue  # Skip private modules
            
            module_name = tab_file.stem
            
            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(
                    f"tabs.{module_name}", 
                    tab_file
                )
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"tabs.{module_name}"] = module
                spec.loader.exec_module(module)
                
                # Look for a create_tab function in the module
                if hasattr(module, 'create_tab'):
                    print(f"Loading tab: {module_name}")
                    module.create_tab(self.notebook, self)
                else:
                    print(f"Warning: {module_name}.py missing create_tab() function")
                    
            except Exception as e:
                print(f"Error loading tab {module_name}: {e}")
                import traceback
                traceback.print_exc()
    
    def on_closing(self):
        """Clean shutdown of all processes"""
        # Stop panels
        for panel in self.panels:
            if hasattr(panel, 'stop'):
                panel.stop()

        # Stop monitoring
        for name in list(self.monitoring_active.keys()):
            self.monitoring_active[name] = False
        
        # Terminate all processes
        for name, process in list(self.processes.items()):
            try:
                if process.poll() is None:  # Process still running
                    process.terminate()
                    process.wait(timeout=5)
            except:
                pass
        
        self.root.destroy()

def main():
    root = tk.Tk()
    app = LLMLauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main()
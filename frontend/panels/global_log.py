"""
Global Log Panel
A panel to display logs from all services.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext

class GlobalLog(ttk.Frame):
    def __init__(self, parent, launcher=None):
        super().__init__(parent, padding="2")
        self.launcher = launcher
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- UI LAYOUT ---
        self.log_widget = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=8, font=("Consolas", 8))
        self.log_widget.grid(row=0, column=0, sticky="nsew")
        self.log_widget.config(state='disabled')

    def add_log(self, source, message):
        """Adds a log message from a source tab, ensuring it's called on the main thread."""
        log_line = f"[{source}] {message}\n"
        
        def _insert_log():
            self.log_widget.config(state='normal')
            self.log_widget.insert(tk.END, log_line)
            self.log_widget.config(state='disabled')
            self.log_widget.see(tk.END)
        
        # Schedule the UI update to run in the main thread
        self.launcher.root.after(0, _insert_log)

def create_panel(parent, launcher):
    """Creates the GlobalLog panel."""
    panel = GlobalLog(parent, launcher=launcher)
    return panel

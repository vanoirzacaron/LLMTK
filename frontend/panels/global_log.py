"""
Global Log Panel
A panel to display logs from all services.
"""

import tkinter as tk
from tkinter import ttk

class GlobalLog(ttk.Frame):
    def __init__(self, parent, launcher=None):
        super().__init__(parent, padding="10")
        self.launcher = launcher
        
        # --- UI LAYOUT ---
        label = ttk.Label(self, text="TODO: Global Log will be implemented here.", font=('Arial', 12))
        label.pack(fill=tk.BOTH, expand=True)

def create_panel(parent, launcher):
    """Creates the GlobalLog panel."""
    panel = GlobalLog(parent, launcher=launcher)
    return panel

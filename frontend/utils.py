
import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
import frontend.tabs.openhands as openhands
import frontend.tabs.process_monitor as process_monitor
import frontend.tabs.vllm as vllm
import frontend.tabs.vm_watch as vm_watch
from frontend.process_launcher import ProcessLauncher

class Application(ThemedTk):
    def __init__(self):
        super().__init__(theme="black")
        self.title("DevOps Dashboard")
        self.geometry("1200x800")

        self.launcher = ProcessLauncher()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        openhands.create_tab(self.notebook, self.launcher)
        vllm.create_tab(self.notebook, self.launcher)
        process_monitor.create_tab(self.notebook, self.launcher)
        vm_watch.create_tab(self.notebook, self.launcher)  # Add the new tab

if __name__ == "__main__":
    app = Application()
    app.mainloop()

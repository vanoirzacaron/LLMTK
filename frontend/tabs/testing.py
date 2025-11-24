"""
Sanity Check & Diagnostics Tab

This tab provides a suite of diagnostic tests to verify that the application's 
dependencies and environment are set up correctly. It is designed to be the first 
place a user looks if a feature is not working as expected.

Key Features:
- A single "Run All Tests" button to perform a full system check.
- Color-coded results (PASS, WARN, FAIL) for easy-to-read feedback.
- Tests for essential system commands (browsers, docker, nvidia-smi).
- Checks for desktop environment integration (GNOME D-Bus for workspace panel).
- Verifies application-specific requirements (e.g., OpenHands directory).
- Performs an integrity check on all tab/panel modules to ensure they are loadable.
"""

import tkinter as tk
from tkinter import ttk
import subprocess
import shutil
import os
from pathlib import Path
import importlib.util

# --- Constants & Configuration ---
TAB_TITLE = "Sanity Check"

# --- Main Tab Class ---

class SanityCheckTab(ttk.Frame):
    """Manages the UI and test execution for the diagnostics tab."""
    def __init__(self, parent, launcher):
        super().__init__(parent, padding="10")
        self.launcher = launcher
        self._setup_ui()

    def _setup_ui(self):
        """Create and arrange the widgets for the tab."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # --- Controls ---
        control_frame = ttk.Frame(self)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        run_button = ttk.Button(control_frame, text="🔍 Run All Sanity Checks", command=self.run_all_tests)
        run_button.pack(side="left")

        # --- Results Log ---
        log_frame = ttk.LabelFrame(self, text="Test Results", padding="5")
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_widget = tk.Text(log_frame, wrap="word", borderwidth=0, highlightthickness=0, state="disabled")
        self.log_widget.grid(row=0, column=0, sticky="nsew")
        # Configure tags for color-coding
        self.log_widget.tag_configure("PASS", foreground="#4caf50") # Green
        self.log_widget.tag_configure("WARN", foreground="#ff9800") # Orange
        self.log_widget.tag_configure("FAIL", foreground="#f44336") # Red
        self.log_widget.tag_configure("HEADER", font=("TkDefaultFont", 10, "bold"))

        self.log_result([("INFO", "Ready to run diagnostics...")])

    def log_result(self, results):
        """Logs the result of a test to the text widget with color-coding."""
        self.log_widget.config(state="normal")
        for status, message in results:
            self.log_widget.insert(tk.END, f"[{status}] ", (status,))
            self.log_widget.insert(tk.END, f"{message}\n")
            # Also log to global logger for a complete trace
            if self.launcher and hasattr(self.launcher, 'log_to_global'):
                self.launcher.log_to_global(TAB_TITLE, f"[{status}] {message}")
        self.log_widget.config(state="disabled")
        self.log_widget.see(tk.END) # Scroll to the bottom

    def run_all_tests(self):
        """Executes all diagnostic tests in sequence and logs the results."""
        self.log_widget.config(state="normal")
        self.log_widget.delete('1.0', tk.END)
        self.log_widget.config(state="disabled")

        self.log_result([("HEADER", "--- Running All Sanity Checks ---")])
        self.log_result(self._test_essential_commands())
        self.log_result(self._test_python_modules())
        self.log_result(self._test_gnome_integration())
        self.log_result(self._test_browser_profiles())
        self.log_result(self._test_project_structure())
        self.log_result(self._test_module_factories())
        self.log_result([("HEADER", "--- Diagnostics Complete ---")])

    def _test_essential_commands(self):
        """Check for presence of essential command-line tools."""
        results = [("HEADER", "1. Testing for Essential System Commands...")]
        commands_to_check = {
            "firefox": "WARN", # Infrasven Tab
            "google-chrome": "WARN", # Infrasven Tab
            "docker": "WARN", # OpenHands Tab
            "nvidia-smi": "WARN", # System/Process Monitor Panels
            "gnome-terminal": "WARN", # Infrasven Tab
        }
        for cmd, level in commands_to_check.items():
            if shutil.which(cmd):
                results.append(("PASS", f"'{cmd}' command is available in PATH."))
            else:
                results.append((level, f"'{cmd}' command not found. Related features may fail."))
        return results

    def _test_python_modules(self):
        """Check for optional but useful Python modules."""
        results = [("HEADER", "2. Testing for Optional Python Modules...")]
        modules_to_check = {
            "GPUtil": "WARN", # For GPU stats in System Monitor
        }
        for module, level in modules_to_check.items():
            try:
                importlib.import_module(module)
                results.append(("PASS", f"Python module '{module}' is installed."))
            except ImportError:
                results.append((level, f"Python module '{module}' not found. Some GPU metrics may be unavailable."))
        return results

    def _test_gnome_integration(self):
        """Check if the GNOME Desktop D-Bus interface is accessible."""
        results = [("HEADER", "3. Testing GNOME Integration (for Navigation Panel)...")]
        try:
            # FIX: Use the 'Eval' method, which is what the Navigation panel actually uses.
            # This makes the test more accurate. We run a harmless JS snippet that the panel relies on.
            cmd = ["gdbus", "call", "--session", "--dest", "org.gnome.Shell", "--object-path", "/org/gnome/Shell", "--method", "org.gnome.Shell.Eval", "global.workspace_manager.workspace_names"]
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=3)
            results.append(("PASS", "Successfully connected to GNOME D-Bus. Navigation panel should work."))
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            results.append(("WARN", f"Could not connect to GNOME D-Bus. Navigation panel will be disabled. Error: {e}"))
        return results

    def _test_browser_profiles(self):
        """Check for the existence of browser profile configuration files."""
        results = [("HEADER", "4. Testing Browser Profile Discovery (for Infrasven Tab)...")]
        # Firefox check
        ff_profiles = Path.home() / ".mozilla/firefox/profiles.ini"
        if ff_profiles.exists():
            results.append(("PASS", f"Firefox profiles file found at: {ff_profiles}"))
        else:
            results.append(("WARN", f"Firefox profiles.ini not found. Firefox profiles cannot be launched."))
        # Chrome check
        chrome_profiles = Path.home() / ".config/google-chrome"
        if chrome_profiles.exists():
            results.append(("PASS", f"Google Chrome config directory found at: {chrome_profiles}"))
        else:
            results.append(("WARN", f"Google Chrome directory not found. Chrome profiles cannot be launched."))
        return results

    def _test_project_structure(self):
        """Check for external project directories this app depends on."""
        results = [("HEADER", "5. Testing Dependent Project Directories...")]
        openhands_dir = Path("../OpenHands")
        if openhands_dir.is_dir():
            results.append(("PASS", f"OpenHands directory found at '{openhands_dir.resolve()}'. OpenHands tab should work."))
        else:
            results.append(("FAIL", f"OpenHands directory NOT found at '{openhands_dir.resolve()}'. OpenHands tab will fail."))
        return results

    def _test_module_factories(self):
        """Dynamically import all tabs/panels and check for their factory functions."""
        results = [("HEADER", "6. Testing Application Module Integrity...")]
        base_dir = Path(__file__).parent.parent
        module_dirs = [base_dir / "tabs", base_dir / "panels"]
        for mod_dir in module_dirs:
            for filename in os.listdir(mod_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    module_path = mod_dir / filename
                    try:
                        spec = importlib.util.spec_from_file_location(f"module.{filename[:-3]}", module_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        factory_func = "create_tab" if mod_dir.name == "tabs" else "create_panel"
                        if hasattr(module, factory_func):
                            results.append(("PASS", f"Module '{mod_dir.name}/{filename}' is valid and has '{factory_func}'."))
                        else:
                            results.append(("FAIL", f"Module '{mod_dir.name}/{filename}' is MISSING the required '{factory_func}' function."))
                    except Exception as e:
                        results.append(("FAIL", f"Failed to import or validate module '{mod_dir.name}/{filename}'. Error: {e}"))
        return results

# --- Factory Function ---
def create_tab(notebook, launcher):
    """Creates the SanityCheckTab and adds it to the notebook."""
    tab = SanityCheckTab(notebook, launcher)
    notebook.add(tab, text=TAB_TITLE) 
    return tab

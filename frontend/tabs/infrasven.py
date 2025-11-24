"""
Infrasven Tab

This tab provides a convenient interface for launching web browser profiles and 
pre-configured SSH connections. It is designed to streamline the developer's 
workflow by providing quick access to different browsing contexts and remote servers.

Key Features:
- Auto-discovery of Firefox and Google Chrome profiles.
- One-click launching of specific browser profiles.
- One-click launching of a terminal for a specific SSH connection.
- Robust error handling for missing applications (browsers, terminal) or configuration files.
- Centralized logging for all actions and errors.
"""

import tkinter as tk
from tkinter import ttk
import os
import shutil
import configparser
from pathlib import Path
import subprocess

# --- Constants ---
TAB_TITLE = "Infrasven"
SSH_CONNECTION_STRING = "ssh -i ~/.ssh/0906hostingerinfra -p 65002 u442402519@147.79.95.137"

# --- Logging ---
def log(launcher, message, level="info"):
    """Centralized logging helper for the Infrasven tab."""
    log_message = f"[{TAB_TITLE}] {message}"
    print(log_message) # For direct console feedback.
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(TAB_TITLE, message)

# --- Profile Discovery Functions ---

def find_firefox_profiles(launcher):
    """Finds Firefox profiles by safely parsing the profiles.ini file."""
    profiles = []
    try:
        profiles_ini_path = Path.home() / ".mozilla/firefox/profiles.ini"
        if not profiles_ini_path.exists():
            log(launcher, "Firefox profiles.ini not found.", "warn")
            return profiles

        config = configparser.ConfigParser()
        config.read(profiles_ini_path)

        for section in config.sections():
            if section.startswith('Profile') and 'Name' in config[section]:
                profiles.append(config[section]['Name'])
        log(launcher, f"Found Firefox profiles: {profiles}")
    except (configparser.Error, IOError) as e:
        log(launcher, f"Error parsing Firefox profiles.ini: {e}", "error")
    return profiles

def find_chrome_profiles(launcher):
    """Finds Google Chrome profiles by scanning the configuration directory."""
    profiles = []
    try:
        chrome_config_path = Path.home() / ".config/google-chrome"
        if not chrome_config_path.exists():
            log(launcher, "Google Chrome config directory not found.", "warn")
            return profiles

        # The "Default" profile is always present.
        profiles.append("Default")

        # Other profiles are in directories named "Profile N".
        for item in chrome_config_path.iterdir():
            if item.is_dir() and item.name.startswith("Profile "):
                profiles.append(item.name)
        log(launcher, f"Found Chrome profiles: {profiles}")
    except OSError as e:
        log(launcher, f"Error scanning for Chrome profiles: {e}", "error")
    return profiles

# --- Core Action Functions ---

def launch_browser(launcher, browser_cmd, profile_arg, profile_name):
    """Launches a browser with a specific profile in a detached process."""
    try:
        command = [browser_cmd, profile_arg, profile_name]
        log(launcher, f"Executing command: {' '.join(command)}")
        # Use Popen to launch the browser as a detached, non-blocking process.
        subprocess.Popen(command, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log(launcher, f"Successfully launched {browser_cmd} with profile '{profile_name}'.")
    except (FileNotFoundError, OSError) as e:
        error_message = f"Failed to launch {browser_cmd}: {e}. Please ensure it is installed and in your PATH."
        log(launcher, error_message, "error")
        # Optionally, show a user-facing error message.
        # from tkinter import messagebox
        # messagebox.showerror("Launch Error", error_message)

def launch_ssh_in_terminal(launcher):
    """Launches the pre-configured SSH command in a new gnome-terminal window."""
    if not shutil.which("gnome-terminal"):
        error_message = "gnome-terminal is not installed. Cannot launch SSH session."
        log(launcher, error_message, "error")
        return

    try:
        # This command opens a new terminal and runs the SSH command.
        # The `exec bash` ensures the terminal stays open after the SSH command exits.
        command = ["gnome-terminal", "--", "bash", "-c", f"{SSH_CONNECTION_STRING}; exec bash"]
        log(launcher, f"Executing command: {' '.join(command)}")
        subprocess.Popen(command, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log(launcher, "Successfully launched SSH session in new terminal.")
    except (FileNotFoundError, OSError) as e:
        error_message = f"Failed to launch gnome-terminal: {e}."
        log(launcher, error_message, "error")

# --- UI Setup ---

def create_tab(notebook, launcher):
    """Creates and configures the UI for the Infrasven tab."""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text=TAB_TITLE)

    tab.columnconfigure(0, weight=1)
    tab.columnconfigure(1, weight=1)

    # --- Firefox Profiles Section ---
    firefox_frame = ttk.LabelFrame(tab, text="Firefox Profiles", padding="10")
    firefox_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 10))
    firefox_frame.columnconfigure(0, weight=1)

    if shutil.which("firefox"):
        ff_profiles = find_firefox_profiles(launcher)
        if ff_profiles:
            for i, p_name in enumerate(ff_profiles):
                btn = ttk.Button(firefox_frame, text=f"Launch '{p_name}'", 
                                 command=lambda p=p_name: launch_browser(launcher, "firefox", "-P", p))
                btn.grid(row=i, column=0, sticky="ew", pady=2)
        else:
            ttk.Label(firefox_frame, text="No Firefox profiles found.").pack()
    else:
        ttk.Label(firefox_frame, text="Firefox executable not found.").pack()

    # --- Chrome Profiles Section ---
    chrome_frame = ttk.LabelFrame(tab, text="Chrome Profiles", padding="10")
    chrome_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 10))
    chrome_frame.columnconfigure(0, weight=1)

    if shutil.which("google-chrome"):
        ch_profiles = find_chrome_profiles(launcher)
        if ch_profiles:
            for i, p_dir in enumerate(ch_profiles):
                btn = ttk.Button(chrome_frame, text=f"Launch '{p_dir}'", 
                                 command=lambda d=p_dir: launch_browser(launcher, "google-chrome", "--profile-directory", d))
                btn.grid(row=i, column=0, sticky="ew", pady=2)
        else:
            ttk.Label(chrome_frame, text="No Chrome profiles found.").pack()
    else:
        ttk.Label(chrome_frame, text="Google Chrome executable not found.").pack()

    # --- SSH Launcher Section ---
    ssh_frame = ttk.LabelFrame(tab, text="SSH Connections", padding="10")
    ssh_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ssh_frame.columnconfigure(0, weight=1)

    ssh_button = ttk.Button(ssh_frame, text="Connect to Hostinger Infra", command=lambda: launch_ssh_in_terminal(launcher))
    ssh_button.grid(row=0, column=0, sticky="ew", pady=5)
